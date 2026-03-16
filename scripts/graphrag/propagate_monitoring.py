"""Propagate MONITORED_BY edges from member drugs to parent DrugClass nodes.

If a Drug has MONITORED_BY→Lab edges but its parent DrugClass doesn't,
this script copies those edges to the DrugClass. This enables class-level
monitoring inheritance (e.g., Eplerenone→MRA→MONITORED_BY→Potassium).

Usage:
    source .env
    uv run python scripts/graphrag/propagate_monitoring.py --dry-run
    uv run python scripts/graphrag/propagate_monitoring.py
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from open_medicine.graphrag.graph.connection import GraphConnection


def _connect() -> GraphConnection:
    uri = os.environ.get("GRAPHRAG_NEO4J_URI", os.environ.get("NEO4J_URI", ""))
    user = os.environ.get("GRAPHRAG_NEO4J_USER", os.environ.get("NEO4J_USER", ""))
    password = os.environ.get("GRAPHRAG_NEO4J_PASSWORD", os.environ.get("NEO4J_PASSWORD", ""))

    if not uri or not user or not password:
        print("ERROR: Set GRAPHRAG_NEO4J_URI, GRAPHRAG_NEO4J_USER, GRAPHRAG_NEO4J_PASSWORD")
        sys.exit(1)

    if "neo4j+s://" in uri:
        uri = uri.replace("neo4j+s://", "neo4j+ssc://")

    return GraphConnection(uri, user, password)


def find_missing_class_monitoring(conn: GraphConnection) -> list[dict]:
    """Find DrugClass nodes missing MONITORED_BY edges that their members have."""
    rows = conn.execute_read(
        "MATCH (d:Drug)-[:MEMBER_OF]->(dc:DrugClass) "
        "MATCH (d)-[r:MONITORED_BY]->(l:Lab) "
        "WHERE NOT EXISTS { (dc)-[:MONITORED_BY]->(l) } "
        "RETURN DISTINCT dc.id AS class_id, dc.name AS class_name, "
        "l.id AS lab_id, l.name AS lab_name, "
        "d.name AS source_drug, "
        "r.frequency AS frequency, r.threshold_alert AS alert, "
        "r.threshold_stop AS stop",
    )
    return rows


def propagate(conn: GraphConnection, rows: list[dict]) -> None:
    """Create MONITORED_BY edges on DrugClass nodes."""
    for row in rows:
        conn.execute_write(
            "MATCH (dc:DrugClass {id: $class_id}), (l:Lab {id: $lab_id}) "
            "MERGE (dc)-[r:MONITORED_BY]->(l) "
            "ON CREATE SET r.frequency = $freq, r.threshold_alert = $alert, "
            "r.threshold_stop = $stop, r._source = 'propagated'",
            {
                "class_id": row["class_id"],
                "lab_id": row["lab_id"],
                "freq": row.get("frequency"),
                "alert": row.get("alert"),
                "stop": row.get("stop"),
            },
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Propagate MONITORED_BY to DrugClass nodes")
    parser.add_argument("--dry-run", action="store_true", help="Print missing edges without changing graph")
    args = parser.parse_args()

    conn = _connect()
    try:
        print("Scanning for missing DrugClass MONITORED_BY edges...")
        missing = find_missing_class_monitoring(conn)

        if not missing:
            print("No missing edges found. All DrugClass monitoring is in sync.")
            return

        print(f"\nFound {len(missing)} missing edges:\n")
        for m in missing:
            print(f"  {m['class_name']} -MONITORED_BY-> {m['lab_name']}  (from {m['source_drug']})")

        if args.dry_run:
            print(f"\nDry run complete. {len(missing)} edges would be created.")
            return

        print(f"\nCreating {len(missing)} edges...")
        propagate(conn, missing)
        print("Done.")

        remaining = find_missing_class_monitoring(conn)
        if remaining:
            print(f"WARNING: {len(remaining)} edges still missing.")
        else:
            print("Verification passed: all DrugClass monitoring edges propagated.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

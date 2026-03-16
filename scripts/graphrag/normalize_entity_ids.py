"""One-time migration: re-ID graph nodes to match terminology IDs.

For each Drug/DrugClass/Disease/Lab/Procedure/Device node in the graph,
looks up its name in the terminology database. If the terminology ID
differs from the graph node's current ID, renames the node by creating
a new node with the correct ID, copying all edges, and deleting the old.

Usage:
    source .env
    uv run python scripts/graphrag/normalize_entity_ids.py --dry-run
    uv run python scripts/graphrag/normalize_entity_ids.py
"""

from __future__ import annotations

import argparse
import os
import sys

# Add src to path so imports work when running as a script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from open_medicine.graphrag.graph.connection import GraphConnection
from open_medicine.graphrag.ingestion.linker_v2 import link_entity

# Label → entity_type mapping
LABEL_TO_TYPE: dict[str, str] = {
    "Drug": "drug",
    "DrugClass": "drug_class",
    "Disease": "disease",
    "Lab": "lab",
    "Procedure": "procedure",
    "Device": "device",
}


def _connect() -> GraphConnection:
    """Connect to Neo4j using environment variables."""
    uri = os.environ.get("GRAPHRAG_NEO4J_URI", os.environ.get("NEO4J_URI", ""))
    user = os.environ.get("GRAPHRAG_NEO4J_USER", os.environ.get("NEO4J_USER", ""))
    password = os.environ.get("GRAPHRAG_NEO4J_PASSWORD", os.environ.get("NEO4J_PASSWORD", ""))

    if not uri or not user or not password:
        print("ERROR: Set GRAPHRAG_NEO4J_URI, GRAPHRAG_NEO4J_USER, GRAPHRAG_NEO4J_PASSWORD")
        sys.exit(1)

    # SSL workaround for Neo4j Aura on macOS
    if "neo4j+s://" in uri:
        uri = uri.replace("neo4j+s://", "neo4j+ssc://")

    return GraphConnection(uri, user, password)


def find_mismatches(conn: GraphConnection) -> list[dict]:
    """Find all nodes whose graph ID doesn't match the terminology ID."""
    mismatches: list[dict] = []

    for label, entity_type in LABEL_TO_TYPE.items():
        rows = conn.execute_read(
            f"MATCH (n:{label}) RETURN n.id AS id, n.name AS name",
        )

        for row in rows:
            graph_id = row.get("id", "")
            name = row.get("name", "")
            if not name:
                continue

            linked = link_entity(name, entity_type)
            if linked is None:
                continue

            if linked.node_id != graph_id:
                mismatches.append({
                    "label": label,
                    "name": name,
                    "old_id": graph_id,
                    "new_id": linked.node_id,
                })

    return mismatches


def rename_node(conn: GraphConnection, label: str, old_id: str, new_id: str) -> None:
    """Rename a node by creating a new one, copying edges, and deleting the old.

    Steps:
    1. Copy all properties from old node to new node (MERGE by new ID)
    2. Copy all outgoing relationships to new node
    3. Copy all incoming relationships to new node
    4. Delete old node
    """
    # Step 1: Create new node with all properties from old
    conn.execute_write(
        f"MATCH (old:{label} {{id: $old_id}}) "
        f"MERGE (new:{label} {{id: $new_id}}) "
        "SET new += properties(old), new.id = $new_id, "
        "new._prev_id = $old_id",
        {"old_id": old_id, "new_id": new_id},
    )

    # Step 2: Copy outgoing relationships
    conn.execute_write(
        f"MATCH (old:{label} {{id: $old_id}})-[r]->(target) "
        f"MATCH (new:{label} {{id: $new_id}}) "
        "CALL {{ "
        "  WITH old, new, r, target "
        "  WITH new, target, type(r) AS rtype, properties(r) AS rprops "
        "  CALL apoc.create.relationship(new, rtype, rprops, target) YIELD rel "
        "  RETURN rel "
        "}} "
        "RETURN count(*) AS copied",
        {"old_id": old_id, "new_id": new_id},
    )

    # Step 3: Copy incoming relationships
    conn.execute_write(
        f"MATCH (source)-[r]->(old:{label} {{id: $old_id}}) "
        f"MATCH (new:{label} {{id: $new_id}}) "
        "CALL {{ "
        "  WITH source, old, new, r "
        "  WITH source, new, type(r) AS rtype, properties(r) AS rprops "
        "  CALL apoc.create.relationship(source, rtype, rprops, new) YIELD rel "
        "  RETURN rel "
        "}} "
        "RETURN count(*) AS copied",
        {"old_id": old_id, "new_id": new_id},
    )

    # Step 4: Delete old node and its relationships
    conn.execute_write(
        f"MATCH (old:{label} {{id: $old_id}}) DETACH DELETE old",
        {"old_id": old_id},
    )


def rename_node_no_apoc(conn: GraphConnection, label: str, old_id: str, new_id: str) -> None:
    """Rename a node without APOC — uses pure Cypher with explicit edge types.

    Falls back to this approach if APOC is not available (e.g., Neo4j Aura free tier).
    Sets the new ID on the existing node rather than creating a new one.
    """
    conn.execute_write(
        f"MATCH (n:{label} {{id: $old_id}}) "
        "SET n.id = $new_id, n._prev_id = $old_id",
        {"old_id": old_id, "new_id": new_id},
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize graph entity IDs to match terminology")
    parser.add_argument("--dry-run", action="store_true", help="Print mismatches without changing graph")
    parser.add_argument("--use-apoc", action="store_true", help="Use APOC for edge copying (requires APOC plugin)")
    args = parser.parse_args()

    conn = _connect()
    try:
        print("Scanning graph for entity ID mismatches...")
        mismatches = find_mismatches(conn)

        if not mismatches:
            print("No mismatches found. All entity IDs match terminology.")
            return

        print(f"\nFound {len(mismatches)} mismatches:\n")
        for m in mismatches:
            print(f"  [{m['label']}] {m['name']}: {m['old_id']} → {m['new_id']}")

        if args.dry_run:
            print(f"\nDry run complete. {len(mismatches)} nodes would be renamed.")
            return

        print(f"\nApplying {len(mismatches)} renames...")
        rename_fn = rename_node if args.use_apoc else rename_node_no_apoc
        for i, m in enumerate(mismatches, 1):
            print(f"  [{i}/{len(mismatches)}] {m['old_id']} → {m['new_id']}")
            rename_fn(conn, m["label"], m["old_id"], m["new_id"])

        print("\nDone. All entity IDs normalized.")

        # Verify
        remaining = find_mismatches(conn)
        if remaining:
            print(f"\nWARNING: {len(remaining)} mismatches still remain:")
            for m in remaining:
                print(f"  [{m['label']}] {m['name']}: {m['old_id']} → {m['new_id']}")
        else:
            print("Verification passed: no mismatches remain.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

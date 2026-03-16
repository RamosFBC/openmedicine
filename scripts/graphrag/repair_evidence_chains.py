"""Repair broken SOURCED_FROM edges between Recommendations and EvidenceChunks.

Root cause: The consolidated JSONL used during loading had `source_text` but
no `source_chunk_id`. The loader only creates SOURCED_FROM when
source_chunk_id is present, so all 536 Recommendations are missing evidence.

This script:
1. Deletes orphaned EvidenceChunks (from a previous chunking run, no edges)
2. Creates new EvidenceChunks from each Recommendation's source_text
3. Creates SOURCED_FROM edges from Recommendations to their source chunks
4. Deduplicates: identical source_text creates one shared EvidenceChunk

Usage:
    source .env
    uv run python scripts/graphrag/repair_evidence_chains.py --dry-run
    uv run python scripts/graphrag/repair_evidence_chains.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

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


def _text_to_chunk_id(text: str) -> str:
    """Deterministic chunk ID from text content."""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Repair SOURCED_FROM edges using source_text from consolidated JSONL"
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--consolidated", type=Path,
        default=Path("data/cache/graphrag/aha_acc_hf_2022/consolidated.jsonl"),
        help="Consolidated JSONL file with source_text",
    )
    args = parser.parse_args()

    # Load consolidated JSONL
    rec_to_text: dict[str, str] = {}
    for line in args.consolidated.read_text(encoding="utf-8").strip().split("\n"):
        if not line:
            continue
        obj = json.loads(line)
        if obj.get("_type") == "metadata":
            continue
        rec_id = obj.get("rec_id", "")
        source_text = obj.get("source_text", "")
        if rec_id and source_text:
            rec_to_text[rec_id] = source_text

    print(f"Loaded {len(rec_to_text)} extractions with source_text")

    # Deduplicate: group rec_ids by identical source_text
    text_to_chunk_id: dict[str, str] = {}
    chunk_texts: dict[str, str] = {}  # chunk_id → text
    rec_to_chunk: dict[str, str] = {}  # rec_id → chunk_id

    for rec_id, text in rec_to_text.items():
        if text not in text_to_chunk_id:
            chunk_id = _text_to_chunk_id(text)
            text_to_chunk_id[text] = chunk_id
            chunk_texts[chunk_id] = text
        rec_to_chunk[rec_id] = text_to_chunk_id[text]

    print(f"Unique EvidenceChunks to create: {len(chunk_texts)}")
    print(f"SOURCED_FROM edges to create: {len(rec_to_chunk)}")

    conn = _connect()
    try:
        # Check current state
        r = conn.execute_read("MATCH (rec:Recommendation) RETURN count(rec) AS total")
        total_recs = r[0]["total"]

        r = conn.execute_read(
            "MATCH (rec:Recommendation)-[:SOURCED_FROM]->(:EvidenceChunk) "
            "RETURN count(DISTINCT rec) AS cnt"
        )
        current_with_evidence = r[0]["cnt"]

        r = conn.execute_read(
            "MATCH (ec:EvidenceChunk) WHERE NOT EXISTS { (ec)--() } "
            "RETURN count(ec) AS cnt"
        )
        orphan_chunks = r[0]["cnt"]

        print(f"\nCurrent graph state:")
        print(f"  Recommendations: {total_recs}")
        print(f"  With SOURCED_FROM: {current_with_evidence}")
        print(f"  Orphaned EvidenceChunks: {orphan_chunks}")

        if current_with_evidence == total_recs:
            print("\nAll Recommendations already have evidence. Nothing to repair.")
            return

        if args.dry_run:
            print(f"\nDry run — would:")
            print(f"  Delete {orphan_chunks} orphaned EvidenceChunks")
            print(f"  Create {len(chunk_texts)} EvidenceChunks from source_text")
            print(f"  Create {len(rec_to_chunk)} SOURCED_FROM edges")
            return

        # Step 1: Delete orphaned EvidenceChunks
        if orphan_chunks > 0:
            print(f"\nStep 1: Deleting {orphan_chunks} orphaned EvidenceChunks...")
            conn.execute_write(
                "MATCH (ec:EvidenceChunk) WHERE NOT EXISTS { (ec)--() } DELETE ec"
            )

        # Step 2: Create EvidenceChunks from source_text
        print(f"Step 2: Creating {len(chunk_texts)} EvidenceChunks...")
        batch = []
        for chunk_id, text in chunk_texts.items():
            batch.append((
                "MERGE (ec:EvidenceChunk {id: $id}) "
                "ON CREATE SET ec.text = $text, ec._source = 'repair'",
                {"id": chunk_id, "text": text},
            ))
        conn.execute_write_tx(batch)

        # Step 3: Create SOURCED_FROM edges
        print(f"Step 3: Creating {len(rec_to_chunk)} SOURCED_FROM edges...")
        batch = []
        for rec_id, chunk_id in rec_to_chunk.items():
            batch.append((
                "MATCH (rec:Recommendation {id: $rec_id}), (ec:EvidenceChunk {id: $chunk_id}) "
                "MERGE (rec)-[r:SOURCED_FROM]->(ec) "
                "ON CREATE SET r._source = 'repair'",
                {"rec_id": rec_id, "chunk_id": chunk_id},
            ))
        conn.execute_write_tx(batch)

        # Verify
        r = conn.execute_read(
            "MATCH (rec:Recommendation)-[:SOURCED_FROM]->(:EvidenceChunk) "
            "RETURN count(DISTINCT rec) AS cnt"
        )
        new_with_evidence = r[0]["cnt"]
        r = conn.execute_read("MATCH (ec:EvidenceChunk) RETURN count(ec) AS cnt")
        total_chunks = r[0]["cnt"]

        print(f"\nDone.")
        print(f"  Recommendations with SOURCED_FROM: {new_with_evidence}/{total_recs}")
        print(f"  Total EvidenceChunks: {total_chunks}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()

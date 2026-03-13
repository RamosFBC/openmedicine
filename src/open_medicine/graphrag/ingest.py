"""CLI for ingesting guideline markdown files into the Neo4j knowledge graph."""
from __future__ import annotations
import argparse
import logging
from pathlib import Path

from open_medicine.graphrag.config import get_settings
from open_medicine.graphrag.graph.connection import GraphConnection
from open_medicine.graphrag.graph.indexes import get_constraint_statements, get_index_statements
from open_medicine.graphrag.graph.schema import Guideline
from open_medicine.graphrag.ingestion.parser import parse_markdown
from open_medicine.graphrag.ingestion.chunker import chunk_document
from open_medicine.graphrag.ingestion.extractor import extract_logic_nodes
from open_medicine.graphrag.ingestion.loader import LoadableGuideline, load_guideline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ensure_indexes(conn: GraphConnection) -> None:
    for stmt in get_constraint_statements():
        try:
            conn.execute_write(stmt)
        except Exception as e:
            logger.debug("Constraint may already exist: %s", e)
    for stmt in get_index_statements():
        try:
            conn.execute_write(stmt)
        except Exception as e:
            logger.debug("Index may already exist: %s", e)


def ingest_file(conn: GraphConnection, path: Path, guideline_id: str, doi: str, title: str = "", year: int = 2024, org: str = "") -> None:
    logger.info("Parsing %s", path)
    doc = parse_markdown(path, guideline_id=guideline_id)
    if title:
        doc.title = title

    logger.info("Chunking: %d sections", len(doc.sections))
    chunks = chunk_document(doc)
    logger.info("Created %d chunks", len(chunks))

    logger.info("Extracting logic nodes...")
    all_extractions = []
    child_chunks = [c for c in chunks if c.parent_chunk_id is not None]
    for i, chunk in enumerate(child_chunks):
        parent = next((p for p in chunks if p.id == chunk.parent_chunk_id), None)
        parent_ctx = parent.text[:200] if parent else ""
        results = extract_logic_nodes(chunk.text, parent_ctx, guideline_id, page=0)
        for r in results:
            r.source_chunk_id = chunk.id
        all_extractions.extend(results)
        if (i + 1) % 10 == 0:
            logger.info("  Processed %d/%d chunks, %d nodes extracted", i + 1, len(child_chunks), len(all_extractions))

    logger.info("Extracted %d logic nodes total", len(all_extractions))

    guideline = Guideline(
        id=guideline_id, title=doc.title, doi=doi,
        year=year, organization=org, total_pages=0,
    )
    loadable = LoadableGuideline(guideline=guideline, chunks=chunks, extractions=all_extractions)

    logger.info("Loading into Neo4j...")
    load_guideline(conn, loadable)
    logger.info("Done: %s loaded with %d nodes", guideline_id, len(all_extractions))


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a guideline into GraphRAG")
    parser.add_argument("--file", type=Path, required=True, help="Path to markdown file")
    parser.add_argument("--id", required=True, help="Guideline ID")
    parser.add_argument("--doi", required=True, help="Guideline DOI")
    parser.add_argument("--title", default="", help="Guideline title")
    parser.add_argument("--year", type=int, default=2024, help="Publication year")
    parser.add_argument("--org", default="", help="Organization")
    args = parser.parse_args()

    settings = get_settings()
    with GraphConnection(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password) as conn:
        ensure_indexes(conn)
        ingest_file(conn, args.file, args.id, args.doi, args.title, args.year, args.org)


if __name__ == "__main__":
    main()

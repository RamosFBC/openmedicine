"""CLI for loading agentic extraction JSONL into Neo4j using v2 schema.

This is the loader side of the agentic ingestion pipeline. The extraction
is done by Claude Code subagents (graphrag-section-extractor), producing
JSONL files. This script loads those into Neo4j.

Pipeline: /ingest-guideline skill → section-extractor agents → normalizer → this loader
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from open_medicine.graphrag.config import get_settings
from open_medicine.graphrag.graph.connection import GraphConnection
from open_medicine.graphrag.graph.indexes_v2 import (
    get_constraint_statements,
    get_index_statements,
)
from open_medicine.graphrag.graph.schema_v2 import Guideline
from open_medicine.graphrag.ingestion.chunker import chunk_document
from open_medicine.graphrag.ingestion.extractor_v2 import (
    ConceptRef,
    ExtractedRelationship,
    ExtractionResult,
)
from open_medicine.graphrag.ingestion.loader_v2 import LoadableGuideline, load_guideline
from open_medicine.graphrag.ingestion.parser import parse_markdown

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ensure_indexes(conn: GraphConnection) -> None:
    """Create v2 constraints and indexes (idempotent)."""
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


def load_extractions_from_jsonl(jsonl_path: Path, guideline_id: str) -> list[ExtractionResult]:
    """Load ExtractionResult objects from a consolidated JSONL file.

    Each line is a JSON object with v2 extraction fields. The last line
    may be metadata (has "_type": "metadata") — skip it.
    """
    results: list[ExtractionResult] = []
    for line in jsonl_path.read_text(encoding="utf-8").strip().split("\n"):
        if not line:
            continue
        obj = json.loads(line)
        if obj.get("_type") == "metadata":
            continue

        concepts = [
            ConceptRef(
                name=c["name"],
                type=c["type"],
                role=c.get("role", "subject"),
            )
            for c in obj.get("concepts", [])
        ]
        relationships = [
            ExtractedRelationship(
                rel_type=r["rel_type"],
                source_name=r["source_name"],
                source_type=r["source_type"],
                target_name=r["target_name"],
                target_type=r["target_type"],
                properties=r.get("properties", {}),
            )
            for r in obj.get("relationships", [])
        ]
        results.append(
            ExtractionResult(
                rec_id=obj["rec_id"],
                rec_type=obj["rec_type"],
                action=obj["action"],
                action_detail=obj.get("action_detail", ""),
                strength=obj["strength"],
                evidence_quality=obj["evidence_quality"],
                conditions=obj.get("conditions", []),
                concepts=concepts,
                relationships=relationships,
                source_chunk_id=obj.get("source_chunk_id", ""),
                guideline_id=obj.get("guideline_id", guideline_id),
                page=obj.get("page", 0),
            )
        )
    return results


def load_from_jsonl(
    conn: GraphConnection,
    jsonl_path: Path,
    md_path: Path,
    guideline_id: str,
    doi: str,
    title: str = "",
    year: int = 2024,
    org: str = "",
) -> None:
    """Load a guideline from agentic extraction JSONL + markdown source."""
    logger.info("Loading extractions from %s", jsonl_path)
    extractions = load_extractions_from_jsonl(jsonl_path, guideline_id)
    logger.info("Loaded %d extractions", len(extractions))

    # Parse + chunk the markdown for EvidenceChunk nodes
    logger.info("Parsing %s for chunks", md_path)
    doc = parse_markdown(md_path, guideline_id=guideline_id)
    if title:
        doc.title = title
    chunks = chunk_document(doc)
    logger.info("Created %d chunks", len(chunks))

    guideline = Guideline(
        id=guideline_id,
        title=title or doc.title,
        doi=doi,
        year=year,
        organization=org,
    )
    loadable = LoadableGuideline(
        guideline=guideline, chunks=chunks, extractions=extractions
    )

    logger.info("Loading into Neo4j (v2 schema)...")
    load_guideline(conn, loadable)
    logger.info(
        "Done: %s loaded with %d recommendations", guideline_id, len(extractions)
    )


def clear_graph(conn: GraphConnection) -> None:
    """Delete all nodes and relationships from the graph."""
    logger.info("Clearing entire graph...")
    conn.execute_write("MATCH (n) DETACH DELETE n")
    logger.info("Graph cleared.")


def validate_graph(conn: GraphConnection) -> dict:
    """Run quality checks on the graph and return a report."""
    checks: dict = {}

    for label in [
        "Drug", "DrugClass", "Disease", "Symptom", "Lab", "Procedure", "Device",
        "Guideline", "Recommendation", "EvidenceChunk", "PatientVariable",
    ]:
        result = conn.execute_read(f"MATCH (n:{label}) RETURN count(n) AS cnt")
        checks[f"node_{label}"] = result[0]["cnt"] if result else 0

    for rel in [
        "INDICATED_FOR", "CONTRAINDICATED_IN", "DOSED_FOR", "MONITORED_BY",
        "INTERACTS_WITH", "MEMBER_OF", "RECOMMENDS", "SOURCED_FROM", "DEFINED_BY",
        "FOR_CONDITION", "EVALUATES", "MEASURES", "CONFLICTS_WITH",
    ]:
        result = conn.execute_read(
            f"MATCH ()-[r:{rel}]->() RETURN count(r) AS cnt"
        )
        checks[f"edge_{rel}"] = result[0]["cnt"] if result else 0

    # Orphan check
    result = conn.execute_read(
        "MATCH (n) WHERE NOT exists { (n)--() } "
        "RETURN labels(n)[0] AS label, count(n) AS cnt"
    )
    checks["orphan_nodes"] = {r["label"]: r["cnt"] for r in result}

    # Recommendations without evidence
    result = conn.execute_read(
        "MATCH (rec:Recommendation) "
        "WHERE NOT exists { (rec)-[:SOURCED_FROM]->() } "
        "RETURN count(rec) AS cnt"
    )
    checks["recs_without_evidence"] = result[0]["cnt"] if result else 0

    # Recommendations without guideline
    result = conn.execute_read(
        "MATCH (rec:Recommendation) "
        "WHERE NOT exists { (rec)-[:DEFINED_BY]->() } "
        "RETURN count(rec) AS cnt"
    )
    checks["recs_without_guideline"] = result[0]["cnt"] if result else 0

    return checks


def print_report(checks: dict) -> None:
    """Pretty-print the validation report."""
    print("\n" + "=" * 60)
    print("GraphRAG v2 Validation Report")
    print("=" * 60)

    print("\n--- Node Counts ---")
    total_clinical = 0
    for key, val in checks.items():
        if key.startswith("node_"):
            label = key[5:]
            print(f"  {label:20s} {val:>5d}")
            if label not in ("Guideline", "Recommendation", "EvidenceChunk", "PatientVariable"):
                total_clinical += val
    print(f"  {'Total Clinical':20s} {total_clinical:>5d}")

    print("\n--- Edge Counts ---")
    for key, val in checks.items():
        if key.startswith("edge_"):
            rel = key[5:]
            print(f"  {rel:25s} {val:>5d}")

    print("\n--- Quality Checks ---")
    orphans = checks.get("orphan_nodes", {})
    if orphans:
        print("  Orphan nodes (no relationships):")
        for label, cnt in orphans.items():
            print(f"    {label}: {cnt}")
    else:
        print("  Orphan nodes: NONE (good)")

    recs_no_ev = checks.get("recs_without_evidence", 0)
    recs_no_gl = checks.get("recs_without_guideline", 0)
    print(f"  Recommendations without evidence: {recs_no_ev}")
    print(f"  Recommendations without guideline: {recs_no_gl}")

    if total_clinical > 0:
        print("\n--- Distribution (clinical entities) ---")
        for label in ["Drug", "DrugClass", "Disease", "Symptom", "Lab", "Procedure", "Device"]:
            count = checks.get(f"node_{label}", 0)
            pct = count / total_clinical * 100
            print(f"  {label:20s} {count:>5d} ({pct:5.1f}%)")

    print("=" * 60)


def generate_scenarios(
    jsonl_path: Path,
    output_path: Path,
    terminology_dir: Path = Path("src/open_medicine/graphrag/terminology"),
) -> list[dict]:
    """Generate clinical test scenarios from a consolidated JSONL file.

    Derives scenarios from the extractions themselves:
    - treatment_selection → expect drug INDICATED_FOR disease
    - contraindication → expect drug CONTRAINDICATED_IN disease
    - monitoring → expect drug MONITORED_BY lab
    - dosing → expect drug DOSED_FOR disease
    - negative tests → first-line drugs should NOT be contraindicated

    Only includes concepts that exist in terminology files (matching what
    the loader will actually create nodes for).
    """
    from collections import defaultdict

    # Load valid concept names from terminology
    valid_names: set[str] = set()
    for fname in [
        "drugs.json", "drug_classes.json", "diseases.json", "labs.json",
        "procedures.json", "devices.json", "symptoms.json",
    ]:
        fpath = terminology_dir / fname
        if not fpath.exists():
            continue
        data = json.loads(fpath.read_text(encoding="utf-8"))
        for canonical, entry in data.items():
            valid_names.add(canonical)
            for alias in entry.get("aliases", []):
                valid_names.add(alias)

    def _in_terminology(name: str) -> bool:
        return name in valid_names or name.lower() in {v.lower() for v in valid_names}

    recs: list[dict] = []
    for line in jsonl_path.read_text(encoding="utf-8").strip().split("\n"):
        if not line:
            continue
        obj = json.loads(line)
        if obj.get("_type") == "metadata":
            continue
        recs.append(obj)

    # --- Collect data by rec_type ---

    # Meta-concepts that shouldn't generate standalone scenarios
    META_CONCEPTS = {
        "guideline-directed medical therapy", "gdmt", "medical therapy",
        "pharmacological therapy", "optimal medical therapy",
    }

    def _is_meta(name: str) -> bool:
        return name.lower() in META_CONCEPTS

    # treatment: disease → [(drug_name, strength)]
    treatments: dict[str, list[tuple[str, str]]] = defaultdict(list)
    # contraindication: drug → [disease_name] (drugs/drug_classes only, not devices)
    contras: dict[str, list[str]] = defaultdict(list)
    # monitoring: drug → [lab_name] (specific drugs only, not drug_classes)
    monitors: dict[str, list[str]] = defaultdict(list)
    # dosing: (drug, disease) pairs
    dosing_pairs: list[tuple[str, str]] = []
    # track which drugs are indicated for which diseases (for negative tests)
    indicated: dict[str, set[str]] = defaultdict(set)  # drug → {diseases}

    for rec in recs:
        rt = rec.get("rec_type", "")
        concepts = rec.get("concepts", [])
        strength = rec.get("strength", "")

        subjects = [c for c in concepts if c.get("role") == "subject"]
        targets = [c for c in concepts if c.get("role") == "target"]
        monitor_labs = [c for c in concepts if c.get("role") == "monitor"]

        drug_subjects = [
            c for c in subjects
            if c["type"] in ("drug", "drug_class", "procedure", "device")
            and not _is_meta(c["name"])
            and _in_terminology(c["name"])
        ]
        disease_targets = [
            c for c in targets
            if c["type"] == "disease" and _in_terminology(c["name"])
        ]

        if rt == "treatment_selection":
            for dis in disease_targets:
                for drug in drug_subjects:
                    treatments[dis["name"]].append((drug["name"], strength))
                    indicated[drug["name"]].add(dis["name"])

        elif rt == "contraindication":
            # Only drugs/drug_classes get CONTRAINDICATED_IN edges, not devices
            contra_subjects = [c for c in drug_subjects if c["type"] in ("drug", "drug_class")]
            for drug in contra_subjects:
                for dis in disease_targets:
                    contras[drug["name"]].append(dis["name"])

        elif rt == "monitoring":
            # MONITORED_BY edges are on specific drugs, not drug_classes
            lab_names = [c["name"] for c in monitor_labs if _in_terminology(c["name"])]
            for drug in [
                c for c in subjects
                if c["type"] == "drug" and _in_terminology(c["name"])
            ]:
                for lab in lab_names:
                    if lab not in monitors[drug["name"]]:
                        monitors[drug["name"]].append(lab)

        elif rt == "dosing":
            for drug in [c for c in subjects if c["type"] == "drug"]:
                for dis in disease_targets:
                    pair = (drug["name"], dis["name"])
                    if pair not in dosing_pairs:
                        dosing_pairs.append(pair)

    # --- Build scenarios ---
    scenarios: list[dict] = []

    # 1. Treatment scenarios: top diseases by rec count
    STRENGTH_ORDER = {"strong_for": 0, "moderate_for": 1, "weak_for": 2}
    # Prefer drugs/drug_classes over procedures/devices as expected entities
    TYPE_PRIORITY = {"drug": 0, "drug_class": 1, "procedure": 2, "device": 3}

    # Track concept types from the JSONL
    concept_types: dict[str, str] = {}
    for rec in recs:
        for c in rec.get("concepts", []):
            concept_types[c["name"]] = c["type"]

    for disease, drug_list in sorted(
        treatments.items(), key=lambda x: len(x[1]), reverse=True
    ):
        if len(drug_list) < 2:
            continue
        # Pick strongest drugs/drug_classes as expected entities (up to 3)
        # Sort by: strength first, then prefer drugs over procedures
        sorted_drugs = sorted(
            drug_list,
            key=lambda x: (
                STRENGTH_ORDER.get(x[1], 9),
                TYPE_PRIORITY.get(concept_types.get(x[0], ""), 9),
            ),
        )
        seen: set[str] = set()
        expect: list[str] = []
        for name, _ in sorted_drugs:
            if name not in seen:
                seen.add(name)
                expect.append(name)
            if len(expect) >= 4:
                break
        scenarios.append({
            "name": f"{disease} treatments",
            "description": f"Treatments indicated for {disease}",
            "intent": "treatment_selection",
            "concepts": [disease],
            "expect_entities": expect,
            "expect_edge": "INDICATED_FOR",
            "expect_min_results": min(len(seen), 3),
        })

    # 2. Contraindication scenarios: each drug with contraindications
    for drug, diseases in sorted(contras.items()):
        unique_diseases = list(dict.fromkeys(diseases))
        scenarios.append({
            "name": f"{drug} contraindications",
            "description": f"{drug} contraindicated in: {', '.join(unique_diseases[:3])}",
            "intent": "contraindication",
            "concepts": [drug],
            "expect_entities": unique_diseases[:3],
            "expect_edge": "CONTRAINDICATED_IN",
            "expect_min_results": 1,
        })

    # 3. Monitoring scenarios: each drug with monitored labs
    for drug, labs in sorted(monitors.items()):
        if not labs:
            continue
        scenarios.append({
            "name": f"{drug} monitoring",
            "description": f"{drug} monitored by: {', '.join(labs)}",
            "intent": "monitoring",
            "concepts": [drug],
            "expect_entities": labs,
            "expect_edge": "MONITORED_BY",
            "expect_min_results": 1,
        })

    # 4. Dosing scenarios: each drug-disease pair
    for drug, disease in dosing_pairs[:15]:  # cap at 15
        scenarios.append({
            "name": f"{drug} dosing for {disease}",
            "description": f"{drug} has dosing info for {disease}",
            "intent": "dosing",
            "concepts": [drug, disease],
            "expect_entities": [disease],
            "expect_edge": "DOSED_FOR",
            "expect_min_results": 1,
        })

    # 5. Negative tests: strong_for drugs should NOT be contraindicated
    #    for their indicated diseases
    contra_set: dict[str, set[str]] = defaultdict(set)
    for drug, diseases in contras.items():
        for d in diseases:
            contra_set[drug].add(d)

    for drug, diseases in indicated.items():
        # Only create negative tests for drugs that are strong_for
        strong_diseases = set()
        for dis, drug_list in treatments.items():
            for dname, strength in drug_list:
                if dname == drug and strength == "strong_for":
                    strong_diseases.add(dis)
        if not strong_diseases:
            continue
        # Check: is this drug also contraindicated for any of its indicated diseases?
        if drug in contra_set and contra_set[drug] & strong_diseases:
            continue  # skip — clinically valid edge case
        # Pick main diseases for the absent check
        absent_diseases = sorted(strong_diseases)[:2]
        scenarios.append({
            "name": f"{drug} NOT contraindicated in {absent_diseases[0]}",
            "description": f"{drug} is first-line — must NOT appear as contraindicated",
            "intent": "contraindication",
            "concepts": [drug],
            "expect_absent": absent_diseases,
            "expect_edge": "CONTRAINDICATED_IN",
            "expect_min_results": 0,
        })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(scenarios, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    logger.info(
        "Generated %d scenarios (%d treatment, %d contraindication, %d monitoring, "
        "%d dosing, %d negative) -> %s",
        len(scenarios),
        sum(1 for s in scenarios if s["intent"] == "treatment_selection" and "expect_absent" not in s),
        sum(1 for s in scenarios if s["intent"] == "contraindication" and "expect_absent" not in s),
        sum(1 for s in scenarios if s["intent"] == "monitoring"),
        sum(1 for s in scenarios if s["intent"] == "dosing"),
        sum(1 for s in scenarios if "expect_absent" in s),
        output_path,
    )
    return scenarios


def run_scenarios(conn: GraphConnection, scenarios_path: Path) -> dict:
    """Run clinical test scenarios against the graph via ReasoningEngine.

    Returns a report dict with pass/fail per scenario and totals.
    """
    from open_medicine.graphrag.reasoning.engine_v2 import ReasoningEngine
    from open_medicine.graphrag.reasoning.types_v2 import ClinicalQuery

    scenarios = json.loads(scenarios_path.read_text(encoding="utf-8"))
    engine = ReasoningEngine(conn)

    results: list[dict] = []
    passed = 0
    failed = 0

    for s in scenarios:
        query = ClinicalQuery(
            intent=s["intent"],
            concepts=s["concepts"],
            patient_vars=s.get("patient_vars", {}),
            include_evidence=s.get("include_evidence", False),
        )
        result = engine.query(query)
        matches = result.semantic_matches
        entity_names_lower = [m.entity_name.lower() for m in matches]
        edge_types = [m.edge_type for m in matches]

        issues: list[str] = []

        expect_min = s.get("expect_min_results", 0)
        if len(matches) < expect_min:
            issues.append(f"got {len(matches)} results, expected >={expect_min}")

        for ent in s.get("expect_entities", []):
            if not any(ent.lower() in n for n in entity_names_lower):
                issues.append(f"missing entity: {ent}")

        expect_edge = s.get("expect_edge", "")
        if expect_edge and expect_edge not in edge_types and len(matches) > 0:
            issues.append(f"no {expect_edge} edge found")

        for ent in s.get("expect_absent", []):
            if any(ent.lower() in n for n in entity_names_lower):
                issues.append(f"unexpected entity present: {ent}")

        status = "FAIL" if issues else "PASS"
        if issues:
            failed += 1
        else:
            passed += 1

        results.append({
            "name": s["name"],
            "status": status,
            "result_count": len(matches),
            "issues": issues,
            "found_entities": [m.entity_name for m in matches[:10]],
        })

    return {"scenarios": results, "passed": passed, "failed": failed, "total": len(scenarios)}


def print_scenario_report(report: dict) -> None:
    """Pretty-print the scenario validation report."""
    print("\n" + "=" * 60)
    print("GraphRAG Scenario Validation")
    print("=" * 60)

    for s in report["scenarios"]:
        tag = s["status"]
        print(f"\n[{tag}] \"{s['name']}\" ({s['result_count']} results)")
        if s["issues"]:
            for issue in s["issues"]:
                print(f"       {issue}")
        if s["found_entities"] and tag == "PASS":
            print(f"       found: {', '.join(s['found_entities'][:8])}")

    print("\n" + "=" * 60)
    total = report["total"]
    passed = report["passed"]
    failed = report["failed"]
    print(f"Results: {passed}/{total} passed, {failed} failed")
    if failed == 0:
        print("Status: ALL SCENARIOS PASSED")
    else:
        print(f"Status: {failed} SCENARIO(S) FAILED — review issues above")
    print("=" * 60)


def embed_chunks(conn: GraphConnection) -> int:
    """Generate embeddings for all EvidenceChunks that don't have them."""
    import os

    api_key = os.environ.get("VOYAGE_API_KEY", "")
    if not api_key:
        print("VOYAGE_API_KEY not set — skipping embedding generation")
        return 0

    from open_medicine.graphrag.ingestion.embeddings import embed_texts
    from open_medicine.graphrag.graph.queries_v2 import LoaderQueries

    # Fetch chunks without embeddings
    rows = conn.execute_read(
        "MATCH (ec:EvidenceChunk) WHERE ec.embedding IS NULL "
        "RETURN ec.id AS id, ec.text AS text",
        {},
    )
    if not rows:
        print("All chunks already have embeddings")
        return 0

    chunk_ids = [r["id"] for r in rows]
    texts = [r["text"] for r in rows]
    print(f"Embedding {len(texts)} chunks...")

    embeddings = embed_texts(texts, api_key=api_key)

    for chunk_id, embedding in zip(chunk_ids, embeddings):
        cypher, params = LoaderQueries.set_embedding(chunk_id, embedding)
        conn.execute_write(cypher, params)

    print(f"Embedded {len(embeddings)} chunks")
    return len(embeddings)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load agentic extractions into GraphRAG (v2 schema)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # Load command (from agentic JSONL)
    load_cmd = sub.add_parser("load", help="Load consolidated JSONL into Neo4j")
    load_cmd.add_argument("--jsonl", type=Path, required=True, help="Consolidated JSONL file")
    load_cmd.add_argument("--file", type=Path, required=True, help="Source markdown file (for chunks)")
    load_cmd.add_argument("--id", required=True, help="Guideline ID")
    load_cmd.add_argument("--doi", required=True, help="Guideline DOI")
    load_cmd.add_argument("--title", default="", help="Guideline title")
    load_cmd.add_argument("--year", type=int, default=2024, help="Publication year")
    load_cmd.add_argument("--org", default="", help="Organization")

    # Clear command
    sub.add_parser("clear", help="Clear entire graph (destructive)")

    # Validate command
    sub.add_parser("validate", help="Run quality checks on current graph")

    # Generate scenarios command
    gen_cmd = sub.add_parser("generate-scenarios", help="Generate test scenarios from consolidated JSONL")
    gen_cmd.add_argument("--jsonl", type=Path, required=True, help="Consolidated JSONL file")
    gen_cmd.add_argument("--output", type=Path, required=True, help="Output test scenarios JSON file")
    gen_cmd.add_argument(
        "--terminology-dir", type=Path,
        default=Path("src/open_medicine/graphrag/terminology"),
        help="Terminology directory (default: src/open_medicine/graphrag/terminology)",
    )

    # Scenarios command
    scenarios_cmd = sub.add_parser("scenarios", help="Run clinical test scenarios against the graph")
    scenarios_cmd.add_argument("--file", type=Path, required=True, help="Test scenarios JSON file")

    # Embed command
    sub.add_parser("embed", help="Generate embeddings for EvidenceChunks (requires VOYAGE_API_KEY)")

    # Migrate command (clear + load)
    migrate_cmd = sub.add_parser("migrate", help="Clear graph and load (full migration)")
    migrate_cmd.add_argument("--jsonl", type=Path, required=True, help="Consolidated JSONL file")
    migrate_cmd.add_argument("--file", type=Path, required=True, help="Source markdown file")
    migrate_cmd.add_argument("--id", required=True, help="Guideline ID")
    migrate_cmd.add_argument("--doi", required=True, help="Guideline DOI")
    migrate_cmd.add_argument("--title", default="", help="Guideline title")
    migrate_cmd.add_argument("--year", type=int, default=2024, help="Publication year")
    migrate_cmd.add_argument("--org", default="", help="Organization")

    args = parser.parse_args()

    # Commands that don't need Neo4j
    if args.command == "generate-scenarios":
        scenarios = generate_scenarios(args.jsonl, args.output, args.terminology_dir)
        print(f"Generated {len(scenarios)} test scenarios -> {args.output}")
        return

    settings = get_settings()

    with GraphConnection(
        settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password
    ) as conn:
        if args.command == "clear":
            clear_graph(conn)

        elif args.command == "validate":
            checks = validate_graph(conn)
            print_report(checks)

        elif args.command == "scenarios":
            report = run_scenarios(conn, args.file)
            print_scenario_report(report)
            if report["failed"] > 0:
                raise SystemExit(1)

        elif args.command == "embed":
            embed_chunks(conn)

        elif args.command in ("load", "migrate"):
            if args.command == "migrate":
                clear_graph(conn)

            ensure_indexes(conn)
            load_from_jsonl(
                conn, args.jsonl, args.file,
                args.id, args.doi, args.title, args.year, args.org,
            )

            checks = validate_graph(conn)
            print_report(checks)


if __name__ == "__main__":
    main()

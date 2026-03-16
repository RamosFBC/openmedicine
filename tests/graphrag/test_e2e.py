"""End-to-end integration test. Requires running Neo4j.
Run with: NEO4J_URI=bolt://localhost:7687 uv run python -m pytest tests/graphrag/test_e2e.py -v
"""
import os
import json
import pytest
from pathlib import Path

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        not os.environ.get("NEO4J_URI"),
        reason="NEO4J_URI not set — skipping integration tests",
    ),
]


@pytest.fixture(scope="module")
def conn():
    from open_medicine.graphrag.graph.connection import GraphConnection
    uri = os.environ["NEO4J_URI"]
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "openmedicine")
    c = GraphConnection(uri, user, password)
    yield c
    c.close()


@pytest.fixture(scope="module", autouse=True)
def setup_graph(conn):
    """Load synthetic test guideline into Neo4j."""
    from open_medicine.graphrag.graph.indexes import get_constraint_statements, get_index_statements
    from open_medicine.graphrag.graph.schema import Guideline, LogicNode, LogicNodeType, Condition
    from open_medicine.graphrag.ingestion.chunker import Chunk
    from open_medicine.graphrag.ingestion.extractor import ExtractionResult, ConceptRef
    from open_medicine.graphrag.ingestion.loader import LoadableGuideline, load_guideline
    from open_medicine.graphrag.ingest import ensure_indexes

    ensure_indexes(conn)

    guideline = Guideline(
        id="test_syn_001", title="Synthetic Test Guideline",
        doi="10.1234/synthetic", year=2024, organization="TEST", total_pages=5,
    )
    chunks = [
        Chunk(id="syn_parent_1", text="Section on ACE inhibitor dosing in renal impairment.", guideline_id="test_syn_001", section="dosing"),
        Chunk(id="syn_child_1", text="Lisinopril should be reduced to 2.5-5mg in patients with eGFR < 30.", guideline_id="test_syn_001", section="dosing", parent_chunk_id="syn_parent_1"),
    ]
    extractions = [
        ExtractionResult(
            logic_node=LogicNode(
                id="ln_syn_001", type=LogicNodeType.DOSING,
                conditions=[Condition(variable="eGFR", operator="<", threshold=30, unit="mL/min")],
                action="dose_adjust", action_detail="Reduce lisinopril to 2.5-5mg daily",
                strength="Strong/A", guideline_id="test_syn_001", page=3,
            ),
            concepts=[ConceptRef("lisinopril", "drug")],
            source_chunk_id="syn_child_1",
        ),
        ExtractionResult(
            logic_node=LogicNode(
                id="ln_syn_002", type=LogicNodeType.CONTRAINDICATION,
                conditions=[Condition(variable="pregnancy", operator="==", threshold="true")],
                action="contraindicated", action_detail="ACE inhibitors are contraindicated in pregnancy",
                strength="Strong/A", guideline_id="test_syn_001", page=4,
            ),
            concepts=[ConceptRef("lisinopril", "drug")],
            source_chunk_id="syn_child_1",
        ),
    ]
    loadable = LoadableGuideline(guideline=guideline, chunks=chunks, extractions=extractions)
    load_guideline(conn, loadable)

    yield

    # Cleanup
    conn.execute_write("MATCH (n) WHERE n.guideline_id = 'test_syn_001' DETACH DELETE n")
    conn.execute_write("MATCH (g:Guideline {id: 'test_syn_001'}) DETACH DELETE g")


class TestE2E:
    def test_dosing_query_matches(self, conn):
        from open_medicine.graphrag.reasoning.engine import ReasoningEngine
        from open_medicine.graphrag.reasoning.types import ClinicalQuery

        engine = ReasoningEngine(conn)
        q = ClinicalQuery(intent="dosing", concepts=["lisinopril"], patient_vars={"eGFR": 20})
        result = engine.query(q)
        assert result.source == "graph_traversal"
        assert len(result.matches) > 0
        assert result.matches[0].conditions_met is True
        assert "2.5-5mg" in result.matches[0].action_detail

    def test_contraindication_query(self, conn):
        from open_medicine.graphrag.reasoning.engine import ReasoningEngine
        from open_medicine.graphrag.reasoning.types import ClinicalQuery

        engine = ReasoningEngine(conn)
        q = ClinicalQuery(intent="contraindication", concepts=["lisinopril"], patient_vars={"pregnancy": "true"})
        result = engine.query(q)
        assert len(result.matches) > 0
        assert result.matches[0].action == "contraindicated"

    def test_no_match_low_confidence(self, conn):
        from open_medicine.graphrag.reasoning.engine import ReasoningEngine
        from open_medicine.graphrag.reasoning.types import ClinicalQuery

        engine = ReasoningEngine(conn)
        q = ClinicalQuery(intent="dosing", concepts=["nonexistent_drug"])
        result = engine.query(q)
        assert result.confidence == "low"
        assert len(result.matches) == 0

    def test_evidence_chunk_retrievable(self, conn):
        from open_medicine.graphrag.graph.queries import ReasoningQueries
        cypher, params = ReasoningQueries.get_evidence_chunk("syn_child_1")
        rows = conn.execute_read(cypher, params)
        assert len(rows) == 1
        assert "Lisinopril" in rows[0]["text"]
        assert rows[0]["doi"] == "10.1234/synthetic"

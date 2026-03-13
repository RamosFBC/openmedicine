from unittest.mock import MagicMock, call
from open_medicine.graphrag.ingestion.loader import load_guideline, LoadableGuideline
from open_medicine.graphrag.ingestion.chunker import Chunk
from open_medicine.graphrag.ingestion.extractor import ExtractionResult, ConceptRef
from open_medicine.graphrag.graph.schema import (
    LogicNode, LogicNodeType, Condition, Guideline,
)


def _make_loadable() -> LoadableGuideline:
    return LoadableGuideline(
        guideline=Guideline(
            id="test_001", title="Test", doi="10.1234/test",
            year=2024, organization="TEST", total_pages=10,
        ),
        chunks=[
            Chunk(id="parent_1", text="Full section text", guideline_id="test_001", section="S1"),
            Chunk(id="child_1", text="Child text", guideline_id="test_001", section="S1", parent_chunk_id="parent_1"),
        ],
        extractions=[
            ExtractionResult(
                logic_node=LogicNode(
                    id="ln_001", type=LogicNodeType.CONTRAINDICATION,
                    conditions=[Condition(variable="pregnancy", operator="==", threshold="true")],
                    action="contraindicated", action_detail="Do not use in pregnancy",
                    strength="Strong/A", guideline_id="test_001", page=1,
                ),
                concepts=[ConceptRef("lisinopril", "drug")],
            ),
        ],
    )


class TestLoader:
    def test_calls_execute_write_tx(self):
        conn = MagicMock()
        loadable = _make_loadable()
        load_guideline(conn, loadable)
        conn.execute_write_tx.assert_called()

    def test_generates_cypher_for_guideline_node(self):
        conn = MagicMock()
        loadable = _make_loadable()
        load_guideline(conn, loadable)
        queries = conn.execute_write_tx.call_args[0][0]
        cypher_strs = [q[0] for q in queries]
        assert any("Guideline" in s for s in cypher_strs)

    def test_generates_cypher_for_chunks(self):
        conn = MagicMock()
        loadable = _make_loadable()
        load_guideline(conn, loadable)
        queries = conn.execute_write_tx.call_args[0][0]
        cypher_strs = [q[0] for q in queries]
        assert any("EvidenceChunk" in s for s in cypher_strs)

    def test_generates_cypher_for_logic_nodes(self):
        conn = MagicMock()
        loadable = _make_loadable()
        load_guideline(conn, loadable)
        queries = conn.execute_write_tx.call_args[0][0]
        cypher_strs = [q[0] for q in queries]
        assert any("LogicNode" in s for s in cypher_strs)

    def test_generates_cypher_for_concepts(self):
        conn = MagicMock()
        loadable = _make_loadable()
        load_guideline(conn, loadable)
        queries = conn.execute_write_tx.call_args[0][0]
        cypher_strs = [q[0] for q in queries]
        assert any("Concept" in s for s in cypher_strs)

from unittest.mock import MagicMock, patch
from open_medicine.graphrag.ingestion.loader import load_guideline, LoadableGuideline, detect_conflicts
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
                source_chunk_id="child_1",
            ),
        ],
    )


class TestLoader:
    def test_calls_execute_write_tx(self):
        conn = MagicMock()
        load_guideline(conn, _make_loadable())
        conn.execute_write_tx.assert_called()

    def test_generates_sourced_from_edge(self):
        conn = MagicMock()
        load_guideline(conn, _make_loadable())
        queries = conn.execute_write_tx.call_args[0][0]
        cypher_strs = [q[0] for q in queries]
        assert any("SOURCED_FROM" in s for s in cypher_strs)

    def test_generates_evaluates_edge(self):
        conn = MagicMock()
        load_guideline(conn, _make_loadable())
        queries = conn.execute_write_tx.call_args[0][0]
        cypher_strs = [q[0] for q in queries]
        assert any("EVALUATES" in s for s in cypher_strs)

    def test_generates_patient_variable_node(self):
        conn = MagicMock()
        load_guideline(conn, _make_loadable())
        queries = conn.execute_write_tx.call_args[0][0]
        cypher_strs = [q[0] for q in queries]
        assert any("PatientVariable" in s for s in cypher_strs)

    def test_generates_all_edge_types(self):
        conn = MagicMock()
        load_guideline(conn, _make_loadable())
        queries = conn.execute_write_tx.call_args[0][0]
        cypher_strs = [q[0] for q in queries]
        for edge in ["BELONGS_TO", "CHILD_OF", "DEFINED_BY", "PARTICIPATES_IN", "SOURCED_FROM", "EVALUATES"]:
            assert any(edge in s for s in cypher_strs), f"Missing {edge} edge"

    def test_generates_guideline_and_chunks_and_logic_nodes(self):
        conn = MagicMock()
        load_guideline(conn, _make_loadable())
        queries = conn.execute_write_tx.call_args[0][0]
        cypher_strs = [q[0] for q in queries]
        for node in ["Guideline", "EvidenceChunk", "LogicNode", "Concept"]:
            assert any(node in s for s in cypher_strs), f"Missing {node} node"


class TestConflictDetection:
    def test_contradictory_actions_detected(self):
        extractions = [
            ExtractionResult(
                logic_node=LogicNode(
                    id="ln_a", type=LogicNodeType.DOSING,
                    conditions=[], action="initiate", action_detail="Start drug",
                    strength="Weak/C", guideline_id="g_old", page=1,
                ),
                concepts=[ConceptRef("apixaban", "drug")],
                source_chunk_id="c1",
            ),
            ExtractionResult(
                logic_node=LogicNode(
                    id="ln_b", type=LogicNodeType.DOSING,
                    conditions=[], action="contraindicated", action_detail="Do not use",
                    strength="Strong/A", guideline_id="g_new", page=1,
                ),
                concepts=[ConceptRef("apixaban", "drug")],
                source_chunk_id="c2",
            ),
        ]
        conflicts = detect_conflicts(extractions)
        assert len(conflicts) == 1
        assert conflicts[0][0] in ("ln_a", "ln_b")
        assert conflicts[0][1] in ("ln_a", "ln_b")

    def test_same_action_no_conflict(self):
        extractions = [
            ExtractionResult(
                logic_node=LogicNode(
                    id="ln_a", type=LogicNodeType.DOSING,
                    conditions=[], action="initiate", action_detail="Start",
                    strength="Strong/A", guideline_id="g1", page=1,
                ),
                concepts=[ConceptRef("apixaban", "drug")],
                source_chunk_id="c1",
            ),
            ExtractionResult(
                logic_node=LogicNode(
                    id="ln_b", type=LogicNodeType.DOSING,
                    conditions=[], action="initiate", action_detail="Also start",
                    strength="Moderate/B", guideline_id="g2", page=1,
                ),
                concepts=[ConceptRef("apixaban", "drug")],
                source_chunk_id="c2",
            ),
        ]
        conflicts = detect_conflicts(extractions)
        assert len(conflicts) == 0

    def test_different_types_no_conflict(self):
        extractions = [
            ExtractionResult(
                logic_node=LogicNode(
                    id="ln_a", type=LogicNodeType.DOSING,
                    conditions=[], action="initiate", action_detail="Start",
                    strength="Strong/A", guideline_id="g1", page=1,
                ),
                concepts=[ConceptRef("apixaban", "drug")],
                source_chunk_id="c1",
            ),
            ExtractionResult(
                logic_node=LogicNode(
                    id="ln_b", type=LogicNodeType.MONITORING,
                    conditions=[], action="monitor", action_detail="Check INR",
                    strength="Strong/A", guideline_id="g1", page=2,
                ),
                concepts=[ConceptRef("apixaban", "drug")],
                source_chunk_id="c2",
            ),
        ]
        conflicts = detect_conflicts(extractions)
        assert len(conflicts) == 0

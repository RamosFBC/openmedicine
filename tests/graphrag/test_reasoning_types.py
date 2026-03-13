import pytest
from open_medicine.graphrag.reasoning.types import (
    ClinicalQuery, GraphRAGResult, LogicNodeMatch, EvidenceCitation,
)


class TestClinicalQuery:
    def test_valid_query(self):
        q = ClinicalQuery(
            intent="dosing",
            concepts=["apixaban"],
            patient_vars={"eGFR": 20, "age": 80},
        )
        assert q.intent == "dosing"

    def test_patient_vars_optional(self):
        q = ClinicalQuery(intent="contraindication", concepts=["lisinopril"])
        assert q.patient_vars == {}


class TestGraphRAGResult:
    def test_graph_traversal_result(self):
        r = GraphRAGResult(
            source="graph_traversal",
            matches=[
                LogicNodeMatch(
                    logic_node_id="ln_001",
                    type="dosing",
                    action="contraindicated",
                    action_detail="Do not use",
                    strength="Strong/A",
                    conditions_met=True,
                    missing_variables=[],
                ),
            ],
            synthesis=None,
            evidence=[
                EvidenceCitation(
                    chunk_id="c1", text="Source text",
                    guideline_title="Test", doi="10.1234/test",
                    section="S1", page=1,
                ),
            ],
            confidence="high",
            missing_variables=[],
        )
        assert r.source == "graph_traversal"
        assert len(r.matches) == 1

    def test_llm_synthesis_result(self):
        r = GraphRAGResult(
            source="llm_synthesis",
            matches=[],
            synthesis="Based on the guidelines...",
            evidence=[],
            confidence="medium",
            missing_variables=["weight_kg"],
        )
        assert r.synthesis is not None

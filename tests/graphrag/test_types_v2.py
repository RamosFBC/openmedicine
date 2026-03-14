"""Tests for GraphRAG reasoning types v2."""

from open_medicine.graphrag.reasoning.types_v2 import (
    ClinicalQuery,
    EvidenceCitation,
    GraphRAGResult,
    RecommendationMatch,
    SemanticMatch,
)


class TestClinicalQuery:
    def test_defaults(self):
        q = ClinicalQuery(intent="treatment_selection", concepts=["HFrEF"])
        assert q.patient_vars == {}
        assert q.guideline_filter is None
        assert q.include_evidence is True

    def test_full_query(self):
        q = ClinicalQuery(
            intent="dosing",
            concepts=["Sacubitril/Valsartan", "HFrEF"],
            patient_vars={"LVEF": 30, "eGFR": 45.0},
            guideline_filter="acc_aha_hf_2022",
            include_evidence=False,
        )
        assert q.intent == "dosing"
        assert len(q.concepts) == 2
        assert q.patient_vars["LVEF"] == 30
        assert q.include_evidence is False


class TestSemanticMatch:
    def test_defaults(self):
        m = SemanticMatch(
            entity_id="drug_sacubitril",
            entity_name="Sacubitril/Valsartan",
            entity_type="Drug",
            edge_type="INDICATED_FOR",
            strength="strong_for",
            evidence_quality="high",
        )
        assert m.conditions_met is True
        assert m.missing_variables == []
        assert m.conditions_json is None

    def test_with_conditions(self):
        m = SemanticMatch(
            entity_id="d1",
            entity_name="DrugA",
            entity_type="Drug",
            edge_type="INDICATED_FOR",
            strength="moderate_for",
            evidence_quality="moderate",
            conditions_json='[{"variable":"LVEF","operator":"<=","threshold":40}]',
            conditions_met=False,
            missing_variables=["eGFR"],
        )
        assert m.conditions_met is False
        assert m.missing_variables == ["eGFR"]


class TestRecommendationMatch:
    def test_defaults(self):
        m = RecommendationMatch(
            rec_id="rec_001",
            rec_type="treatment_selection",
            action="Prescribe ARNi",
            action_detail="ARNi for HFrEF",
            strength="strong_for",
            evidence_quality="high",
        )
        assert m.conditions_met is True
        assert m.missing_variables == []


class TestEvidenceCitation:
    def test_defaults(self):
        e = EvidenceCitation(chunk_id="chunk_1", text="ARNi is recommended...")
        assert e.guideline_title == ""
        assert e.doi == ""
        assert e.section == ""

    def test_full(self):
        e = EvidenceCitation(
            chunk_id="c1",
            text="Some text",
            guideline_title="AHA HF 2022",
            doi="10.1234/test",
            section="Treatment",
        )
        assert e.doi == "10.1234/test"


class TestGraphRAGResult:
    def test_defaults(self):
        r = GraphRAGResult(source="graph_traversal")
        assert r.semantic_matches == []
        assert r.recommendation_matches == []
        assert r.evidence == []
        assert r.confidence == "low"
        assert r.missing_variables == []
        assert r.synthesis is None

    def test_with_matches(self):
        r = GraphRAGResult(
            source="graph_traversal",
            semantic_matches=[
                SemanticMatch(
                    entity_id="d1",
                    entity_name="D",
                    entity_type="Drug",
                    edge_type="INDICATED_FOR",
                    strength="strong_for",
                    evidence_quality="high",
                )
            ],
            confidence="high",
        )
        assert len(r.semantic_matches) == 1
        assert r.confidence == "high"

    def test_source_literal(self):
        r1 = GraphRAGResult(source="graph_traversal")
        r2 = GraphRAGResult(source="llm_synthesis")
        assert r1.source == "graph_traversal"
        assert r2.source == "llm_synthesis"

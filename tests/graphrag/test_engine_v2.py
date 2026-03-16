"""Tests for GraphRAG Reasoning Engine v2."""

import json
from unittest.mock import MagicMock, patch

from open_medicine.graphrag.reasoning.engine_v2 import (
    OPS,
    STRENGTH_RANK,
    VECTOR_SIMILARITY_THRESHOLD,
    ReasoningEngine,
)
from open_medicine.graphrag.reasoning.types_v2 import (
    ClinicalQuery,
    GraphRAGResult,
    SemanticMatch,
)

# Shared mock for link_entity results
_MOCK_LINKED = MagicMock()
_MOCK_LINKED.node_id = "drug_sacubitril_valsartan"
_MOCK_LINKED.node_label = "Drug"


def _make_engine():
    conn = MagicMock()
    conn.execute_read.return_value = []
    return ReasoningEngine(conn), conn


class TestSemanticMatchEdgeProperties:
    """Verify SemanticMatch carries edge properties."""

    def test_edge_properties_default_empty(self):
        m = SemanticMatch(
            entity_id="x", entity_name="X", entity_type="Drug",
            edge_type="DOSED_FOR", strength="", evidence_quality="",
        )
        assert m.edge_properties == {}

    def test_edge_properties_carries_dosing(self):
        m = SemanticMatch(
            entity_id="x", entity_name="X", entity_type="Drug",
            edge_type="DOSED_FOR", strength="", evidence_quality="",
            edge_properties={
                "starting_dose": "12.5 mg",
                "target_dose": "50 mg",
                "max_dose": "50 mg",
                "frequency": "once daily",
            },
        )
        assert m.edge_properties["starting_dose"] == "12.5 mg"
        assert m.edge_properties["frequency"] == "once daily"

    def test_edge_properties_carries_severity(self):
        m = SemanticMatch(
            entity_id="x", entity_name="X", entity_type="Drug",
            edge_type="INTERACTS_WITH", strength="", evidence_quality="",
            edge_properties={"severity": "MAJOR", "mechanism": "hyperkalemia"},
        )
        assert m.edge_properties["severity"] == "MAJOR"

    def test_edge_properties_carries_monitoring(self):
        m = SemanticMatch(
            entity_id="x", entity_name="X", entity_type="Lab",
            edge_type="MONITORED_BY", strength="", evidence_quality="",
            edge_properties={
                "frequency": "within 1 week, then monthly",
                "threshold_alert": "K+ >= 5.5 mEq/L",
                "threshold_stop": "K+ >= 6.0 mEq/L",
            },
        )
        assert m.edge_properties["threshold_stop"] == "K+ >= 6.0 mEq/L"

    def test_edge_properties_serializes_to_json(self):
        m = SemanticMatch(
            entity_id="x", entity_name="X", entity_type="Drug",
            edge_type="DOSED_FOR", strength="", evidence_quality="",
            edge_properties={"starting_dose": "10 mg"},
        )
        data = m.model_dump()
        assert data["edge_properties"] == {"starting_dose": "10 mg"}


class TestStrengthRank:
    def test_strong_ranks_lowest(self):
        assert STRENGTH_RANK["strong_for"] < STRENGTH_RANK["moderate_for"]
        assert STRENGTH_RANK["strong_for"] < STRENGTH_RANK["weak_for"]

    def test_strong_against_ranks_same_as_strong_for(self):
        assert STRENGTH_RANK["strong_against"] == STRENGTH_RANK["strong_for"]


class TestOps:
    def test_all_operators(self):
        assert OPS["<"](1, 2) is True
        assert OPS["<="](2, 2) is True
        assert OPS[">"](3, 2) is True
        assert OPS[">="](2, 2) is True
        assert OPS["=="](1, 1) is True
        assert OPS["!="](1, 2) is True


class TestIntentRouting:
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity", return_value=None)
    def test_unknown_intent_uses_generic(self, _mock_link):
        engine, conn = _make_engine()
        q = ClinicalQuery(intent="some_unknown", concepts=["X"])
        result = engine.query(q)
        assert result.source == "graph_traversal"
        assert result.confidence == "low"

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity", return_value=None)
    def test_treatment_intent_routes(self, _mock_link):
        engine, conn = _make_engine()
        q = ClinicalQuery(intent="treatment_selection", concepts=["HFrEF"])
        result = engine.query(q)
        assert result.source == "graph_traversal"

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity", return_value=None)
    def test_each_intent_routes_without_error(self, mock_link):
        engine, _ = _make_engine()
        for intent in [
            "treatment_selection",
            "contraindication",
            "interaction",
            "dosing",
            "monitoring",
        ]:
            q = ClinicalQuery(intent=intent, concepts=["test"])
            result = engine.query(q)
            assert result.source == "graph_traversal"


class TestQueryTreatments:
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_no_entity_match(self, mock_link):
        mock_link.return_value = None
        engine, conn = _make_engine()
        conn.execute_read.return_value = []  # vector fallback returns nothing
        q = ClinicalQuery(intent="treatment_selection", concepts=["Unknown"])
        result = engine.query(q)
        assert result.semantic_matches == []

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_returns_semantic_matches(self, mock_link):
        linked = MagicMock()
        linked.node_id = "disease_hfref"
        mock_link.return_value = linked

        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {
                "entity_id": "drug_sacubitril",
                "entity_name": "Sacubitril/Valsartan",
                "entity_type": "Drug",
                "strength": "strong_for",
                "evidence_quality": "high",
                "conditions": None,
            }
        ]
        q = ClinicalQuery(
            intent="treatment_selection",
            concepts=["HFrEF"],
            include_evidence=False,
        )
        result = engine.query(q)
        assert len(result.semantic_matches) == 1
        assert result.semantic_matches[0].entity_name == "Sacubitril/Valsartan"
        assert result.semantic_matches[0].edge_type == "INDICATED_FOR"
        assert result.confidence == "high"

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_guideline_filter_passed(self, mock_link):
        linked = MagicMock()
        linked.node_id = "disease_hf"
        mock_link.return_value = linked

        engine, conn = _make_engine()
        conn.execute_read.return_value = []
        q = ClinicalQuery(
            intent="treatment_selection",
            concepts=["HF"],
            guideline_filter="acc_aha_hf_2022",
            include_evidence=False,
        )
        engine.query(q)
        # Check the first call (Layer 1 treatment query) includes guideline filter
        first_call = conn.execute_read.call_args_list[0]
        cypher, params = first_call[0]
        assert "gfilter" in params
        assert params["gfilter"] == "acc_aha_hf_2022"


class TestQueryContraindications:
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_tries_drug_then_drug_class(self, mock_link):
        # First call (drug) returns None, second (drug_class) returns match
        drug_class = MagicMock()
        drug_class.node_id = "class_acei"
        drug_class.node_label = "DrugClass"
        mock_link.side_effect = [None, drug_class]

        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {
                "disease_id": "disease_pregnancy",
                "disease_name": "Pregnancy",
                "strength": "strong_against",
                "conditions": None,
            }
        ]
        q = ClinicalQuery(intent="contraindication", concepts=["ACEi"])
        result = engine.query(q)
        assert len(result.semantic_matches) == 1
        assert result.semantic_matches[0].edge_type == "CONTRAINDICATED_IN"
        assert result.semantic_matches[0].entity_type == "Disease"

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_stops_after_first_match(self, mock_link):
        drug = MagicMock()
        drug.node_id = "drug_lisinopril"
        drug.node_label = "Drug"
        mock_link.return_value = drug

        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {"disease_id": "d1", "disease_name": "X", "strength": "s", "conditions": None}
        ]
        q = ClinicalQuery(intent="contraindication", concepts=["Lisinopril"], include_evidence=False)
        engine.query(q)
        # Should only call execute_read once (drug found, no need for drug_class)
        assert conn.execute_read.call_count == 1

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_evidence_quality_propagated_from_graph(self, mock_link):
        """C2: evidence_quality should be read from graph row, not hardcoded."""
        drug = MagicMock()
        drug.node_id = "drug_lisinopril"
        drug.node_label = "Drug"
        mock_link.return_value = drug

        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {
                "disease_id": "d1",
                "disease_name": "Pregnancy",
                "strength": "strong_against",
                "severity": "absolute",
                "evidence_quality": "high",
                "conditions": None,
            }
        ]
        q = ClinicalQuery(intent="contraindication", concepts=["Lisinopril"], include_evidence=False)
        result = engine.query(q)
        assert len(result.semantic_matches) == 1
        assert result.semantic_matches[0].evidence_quality == "high"


class TestQueryInteractions:
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_returns_interactions(self, mock_link):
        linked = MagicMock()
        linked.node_id = "drug_warfarin"
        linked.node_label = "Drug"
        mock_link.return_value = linked

        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {"entity_id": "drug_aspirin", "entity_name": "Aspirin", "entity_type": "Drug"}
        ]
        q = ClinicalQuery(intent="interaction", concepts=["Warfarin"])
        result = engine.query(q)
        assert len(result.semantic_matches) == 1
        assert result.semantic_matches[0].edge_type == "INTERACTS_WITH"
        assert result.semantic_matches[0].entity_type == "Drug"

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_evidence_quality_propagated_from_graph(self, mock_link):
        """C2: evidence_quality should be read from graph row, not hardcoded."""
        linked = MagicMock()
        linked.node_id = "drug_warfarin"
        linked.node_label = "Drug"
        mock_link.return_value = linked

        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {
                "entity_id": "drug_aspirin",
                "entity_name": "Aspirin",
                "entity_type": "Drug",
                "severity": "major",
                "evidence_quality": "moderate",
                "mechanism": "antiplatelet",
                "clinical_effect": "increased bleeding",
            }
        ]
        q = ClinicalQuery(intent="interaction", concepts=["Warfarin"])
        result = engine.query(q)
        assert len(result.semantic_matches) == 1
        assert result.semantic_matches[0].evidence_quality == "moderate"

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_tries_drug_class_when_drug_not_found(self, mock_link):
        """If concept is not a drug, try drug_class (e.g., 'ACE Inhibitor')."""
        drug_class = MagicMock()
        drug_class.node_id = "atc:C09A"
        drug_class.node_label = "DrugClass"
        # First call (drug) → None, second call (drug_class) → match
        mock_link.side_effect = [None, drug_class]

        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {"entity_id": "atc:C09DX", "entity_name": "ARNi", "entity_type": "DrugClass"}
        ]
        q = ClinicalQuery(intent="interaction", concepts=["ACE Inhibitor"])
        result = engine.query(q)
        assert len(result.semantic_matches) == 1
        assert result.semantic_matches[0].entity_name == "ARNi"

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_drug_found_skips_drug_class(self, mock_link):
        """When drug is found, don't try drug_class."""
        drug = MagicMock()
        drug.node_id = "rxnorm:11289"
        drug.node_label = "Drug"
        mock_link.return_value = drug

        engine, conn = _make_engine()
        conn.execute_read.return_value = []
        q = ClinicalQuery(intent="interaction", concepts=["Warfarin"])
        engine.query(q)
        # link_entity called once (drug found), not twice
        mock_link.assert_called_once_with("Warfarin", "drug")


class TestQueryDosing:
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_empty_concepts(self, mock_link):
        engine, _ = _make_engine()
        q = ClinicalQuery(intent="dosing", concepts=[])
        result = engine.query(q)
        assert result.confidence == "low"

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_drug_only(self, mock_link):
        drug = MagicMock()
        drug.node_id = "drug_sacubitril"
        mock_link.return_value = drug

        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {
                "disease_id": "disease_hfref",
                "disease": "HFrEF",
                "conditions": None,
            }
        ]
        q = ClinicalQuery(
            intent="dosing", concepts=["Sacubitril/Valsartan"], include_evidence=False
        )
        result = engine.query(q)
        assert len(result.semantic_matches) == 1
        assert result.semantic_matches[0].edge_type == "DOSED_FOR"

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_drug_and_disease(self, mock_link):
        drug = MagicMock()
        drug.node_id = "drug_sacubitril"
        disease = MagicMock()
        disease.node_id = "disease_hfref"
        mock_link.side_effect = [drug, disease]

        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {"disease": "HFrEF", "conditions": None}
        ]
        q = ClinicalQuery(
            intent="dosing",
            concepts=["Sacubitril/Valsartan", "HFrEF"],
            include_evidence=False,
        )
        result = engine.query(q)
        # Verify disease_id was passed to query
        call_args = conn.execute_read.call_args
        _, params = call_args[0]
        assert "dis_id" in params

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_drug_not_found(self, mock_link):
        mock_link.return_value = None
        engine, _ = _make_engine()
        q = ClinicalQuery(intent="dosing", concepts=["Unknown"])
        result = engine.query(q)
        assert result.confidence == "low"


class TestQueryMonitoring:
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_returns_labs(self, mock_link):
        linked = MagicMock()
        linked.node_id = "drug_warfarin"
        mock_link.return_value = linked

        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {"lab_id": "lab_inr", "lab_name": "INR"}
        ]
        q = ClinicalQuery(intent="monitoring", concepts=["Warfarin"])
        result = engine.query(q)
        assert len(result.semantic_matches) == 1
        assert result.semantic_matches[0].entity_type == "Lab"
        assert result.semantic_matches[0].edge_type == "MONITORED_BY"


class TestQueryGeneric:
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_tries_entity_types_until_match(self, mock_link):
        # Return None for drug, drug_class, then match on disease
        disease = MagicMock()
        disease.node_id = "disease_hf"
        disease.node_label = "Disease"
        mock_link.side_effect = [None, None, disease, None, None]

        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {
                "rec_id": "rec_001",
                "rec_type": "diagnostic_criteria",
                "action": "Measure BNP",
                "detail": "Check BNP levels",
                "strength": "strong_for",
                "evidence_quality": "high",
                "source_text": "BNP should be measured...",
                "guideline": "AHA HF 2022",
                "doi": "10.1234/test",
                "section": "Diagnosis",
            }
        ]
        q = ClinicalQuery(intent="diagnostic_criteria", concepts=["HF"])
        result = engine.query(q)
        assert len(result.recommendation_matches) == 1
        assert len(result.evidence) == 1
        assert result.confidence == "high"

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_no_matches_gives_low_confidence(self, mock_link):
        mock_link.return_value = None
        engine, _ = _make_engine()
        q = ClinicalQuery(intent="unknown_type", concepts=["X"])
        result = engine.query(q)
        assert result.confidence == "low"
        assert result.recommendation_matches == []


class TestQueryDiagnosticCriteria:
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_diagnostic_criteria_routed(self, mock_link):
        """diagnostic_criteria intent should route to dedicated method."""
        disease = MagicMock()
        disease.node_id = "snomed:84114007"
        disease.node_label = "Disease"
        mock_link.return_value = disease

        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {
                "entity_id": "loinc:10230-1",
                "entity_name": "LVEF",
                "entity_type": "Lab",
            }
        ]
        q = ClinicalQuery(intent="diagnostic_criteria", concepts=["Heart Failure"])
        result = engine.query(q)
        assert len(result.semantic_matches) >= 1
        assert result.semantic_matches[0].edge_type == "DIAGNOSED_BY"

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_diagnostic_criteria_returns_labs_and_procedures(self, mock_link):
        disease = MagicMock()
        disease.node_id = "snomed:84114007"
        disease.node_label = "Disease"
        mock_link.return_value = disease

        engine, conn = _make_engine()
        conn.execute_read.side_effect = [
            [  # Layer 1: DIAGNOSED_BY
                {"entity_id": "loinc:1", "entity_name": "LVEF", "entity_type": "Lab"},
                {"entity_id": "snomed:2", "entity_name": "Echo", "entity_type": "Procedure"},
            ],
        ]
        q = ClinicalQuery(
            intent="diagnostic_criteria", concepts=["Heart Failure"],
            include_evidence=False,
        )
        result = engine.query(q)
        types = {m.entity_type for m in result.semantic_matches}
        assert "Lab" in types or "Procedure" in types

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_diagnostic_criteria_no_results_falls_to_generic(self, mock_link):
        """If no DIAGNOSED_BY edges, fall back to generic recommendation search."""
        disease = MagicMock()
        disease.node_id = "snomed:84114007"
        disease.node_label = "Disease"
        # First call for diagnostic method, then subsequent for generic fallback
        mock_link.side_effect = [disease, None, None, disease, None, None]

        engine, conn = _make_engine()
        conn.execute_read.side_effect = [
            [],  # Layer 1: no DIAGNOSED_BY edges
            [    # Generic: recommendation search
                {
                    "rec_id": "rec_001", "rec_type": "diagnostic_criteria",
                    "action": "classify_as_HFrEF",
                    "detail": "Classify as HFrEF if LVEF ≤40%",
                    "strength": "strong_for", "evidence_quality": "high",
                    "source_text": "LVEF ≤40% = HFrEF",
                    "guideline": "AHA", "doi": "10.1234", "section": "Dx",
                }
            ],
        ]
        q = ClinicalQuery(intent="diagnostic_criteria", concepts=["Heart Failure"])
        result = engine.query(q)
        # Should have recommendation matches from generic fallback
        assert len(result.recommendation_matches) >= 1

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_diagnostic_criteria_no_entity_match(self, mock_link):
        mock_link.return_value = None
        engine, _ = _make_engine()
        q = ClinicalQuery(intent="diagnostic_criteria", concepts=["Unknown"])
        result = engine.query(q)
        assert result.confidence == "low"


class TestEvaluateConditions:
    def test_no_conditions(self):
        engine, _ = _make_engine()
        match = SemanticMatch(
            entity_id="d1",
            entity_name="D",
            entity_type="Drug",
            edge_type="INDICATED_FOR",
            strength="strong_for",
            evidence_quality="high",
            conditions_json=None,
        )
        engine._evaluate_match_conditions(match, {"LVEF": 30})
        # No conditions means conditions_met stays True (default)
        assert match.conditions_met is True

    def test_conditions_met(self):
        engine, _ = _make_engine()
        conditions = json.dumps([
            {"variable": "LVEF", "operator": "<=", "threshold": 40}
        ])
        match = SemanticMatch(
            entity_id="d1",
            entity_name="D",
            entity_type="Drug",
            edge_type="INDICATED_FOR",
            strength="strong_for",
            evidence_quality="high",
            conditions_json=conditions,
        )
        engine._evaluate_match_conditions(match, {"LVEF": 30})
        assert match.conditions_met is True
        assert match.missing_variables == []

    def test_conditions_not_met(self):
        engine, _ = _make_engine()
        conditions = json.dumps([
            {"variable": "LVEF", "operator": "<=", "threshold": 40}
        ])
        match = SemanticMatch(
            entity_id="d1",
            entity_name="D",
            entity_type="Drug",
            edge_type="INDICATED_FOR",
            strength="strong_for",
            evidence_quality="high",
            conditions_json=conditions,
        )
        engine._evaluate_match_conditions(match, {"LVEF": 55})
        assert match.conditions_met is False

    def test_missing_variable(self):
        engine, _ = _make_engine()
        conditions = json.dumps([
            {"variable": "eGFR", "operator": ">=", "threshold": 30}
        ])
        match = SemanticMatch(
            entity_id="d1",
            entity_name="D",
            entity_type="Drug",
            edge_type="INDICATED_FOR",
            strength="strong_for",
            evidence_quality="high",
            conditions_json=conditions,
        )
        engine._evaluate_match_conditions(match, {})
        # C1 safety fix: missing vars → conditions_met=None (uncertain)
        assert match.conditions_met is None
        assert "eGFR" in match.missing_variables

    def test_invalid_json_ignored(self):
        engine, _ = _make_engine()
        match = SemanticMatch(
            entity_id="d1",
            entity_name="D",
            entity_type="Drug",
            edge_type="INDICATED_FOR",
            strength="strong_for",
            evidence_quality="high",
            conditions_json="not valid json",
        )
        engine._evaluate_match_conditions(match, {"LVEF": 30})
        # Should not raise, conditions_met stays default True
        assert match.conditions_met is True

    def test_non_list_conditions_ignored(self):
        engine, _ = _make_engine()
        match = SemanticMatch(
            entity_id="d1",
            entity_name="D",
            entity_type="Drug",
            edge_type="INDICATED_FOR",
            strength="strong_for",
            evidence_quality="high",
            conditions_json='{"not": "a list"}',
        )
        engine._evaluate_match_conditions(match, {})
        assert match.conditions_met is True


    # --- L3: Case-insensitive variable matching ---

    def test_condition_evaluation_case_insensitive(self):
        """egfr in patient_vars should match eGFR in condition."""
        engine, _ = _make_engine()
        conditions = json.dumps([
            {"variable": "eGFR", "operator": ">=", "threshold": 30}
        ])
        match = SemanticMatch(
            entity_id="d1", entity_name="D", entity_type="Drug",
            edge_type="INDICATED_FOR", strength="strong_for",
            evidence_quality="high", conditions_json=conditions,
        )
        engine._evaluate_match_conditions(match, {"egfr": 35})
        assert match.conditions_met is True
        assert match.missing_variables == []

    def test_condition_evaluation_mixed_case(self):
        """LVEF should match lvef and vice versa."""
        engine, _ = _make_engine()
        conditions = json.dumps([
            {"variable": "lvef", "operator": "<=", "threshold": 40}
        ])
        match = SemanticMatch(
            entity_id="d1", entity_name="D", entity_type="Drug",
            edge_type="INDICATED_FOR", strength="strong_for",
            evidence_quality="high", conditions_json=conditions,
        )
        engine._evaluate_match_conditions(match, {"LVEF": 30})
        assert match.conditions_met is True

    # --- L4: Missing vars vs failed conditions ---

    def test_missing_vars_only_sets_uncertain(self):
        """Missing vars but no failed condition → conditions_met=None (uncertain)."""
        engine, _ = _make_engine()
        conditions = json.dumps([
            {"variable": "eGFR", "operator": ">=", "threshold": 30}
        ])
        match = SemanticMatch(
            entity_id="d1", entity_name="D", entity_type="Drug",
            edge_type="INDICATED_FOR", strength="strong_for",
            evidence_quality="high", conditions_json=conditions,
        )
        engine._evaluate_match_conditions(match, {})
        assert match.conditions_met is None
        assert "eGFR" in match.missing_variables

    def test_failed_condition_sets_conditions_met_false(self):
        """Explicit failure (value doesn't meet threshold) → conditions_met=False."""
        engine, _ = _make_engine()
        conditions = json.dumps([
            {"variable": "LVEF", "operator": "<=", "threshold": 40}
        ])
        match = SemanticMatch(
            entity_id="d1", entity_name="D", entity_type="Drug",
            edge_type="INDICATED_FOR", strength="strong_for",
            evidence_quality="high", conditions_json=conditions,
        )
        engine._evaluate_match_conditions(match, {"LVEF": 55})
        assert match.conditions_met is False

    def test_mixed_missing_and_met_conditions(self):
        """One met condition + one missing var → conditions_met=None (uncertain)."""
        engine, _ = _make_engine()
        conditions = json.dumps([
            {"variable": "LVEF", "operator": "<=", "threshold": 40},
            {"variable": "eGFR", "operator": ">=", "threshold": 30},
        ])
        match = SemanticMatch(
            entity_id="d1", entity_name="D", entity_type="Drug",
            edge_type="INDICATED_FOR", strength="strong_for",
            evidence_quality="high", conditions_json=conditions,
        )
        engine._evaluate_match_conditions(match, {"LVEF": 30})
        assert match.conditions_met is None
        assert "eGFR" in match.missing_variables


class TestThreeStateConditions:
    """C1 safety fix: three-state conditions_met logic.

    True  → all conditions evaluated and passed
    None  → uncertain — missing variables prevent full evaluation
    False → at least one condition explicitly failed
    """

    def test_all_conditions_pass_returns_true(self):
        engine, _ = _make_engine()
        conditions = json.dumps([
            {"variable": "LVEF", "operator": "<=", "threshold": 40},
            {"variable": "eGFR", "operator": ">=", "threshold": 30},
        ])
        match = SemanticMatch(
            entity_id="d1", entity_name="D", entity_type="Drug",
            edge_type="INDICATED_FOR", strength="strong_for",
            evidence_quality="high", conditions_json=conditions,
        )
        engine._evaluate_match_conditions(match, {"LVEF": 30, "eGFR": 45})
        assert match.conditions_met is True
        assert match.missing_variables == []

    def test_missing_variable_returns_none(self):
        """A contraindication with unknown pregnancy status must NOT pass."""
        engine, _ = _make_engine()
        conditions = json.dumps([
            {"variable": "pregnant", "operator": "==", "threshold": "false"},
        ])
        match = SemanticMatch(
            entity_id="d1", entity_name="D", entity_type="Drug",
            edge_type="CONTRAINDICATED_IN", strength="strong_against",
            evidence_quality="high", conditions_json=conditions,
        )
        engine._evaluate_match_conditions(match, {})
        assert match.conditions_met is None
        assert "pregnant" in match.missing_variables

    def test_failed_condition_returns_false(self):
        engine, _ = _make_engine()
        conditions = json.dumps([
            {"variable": "LVEF", "operator": "<=", "threshold": 40},
        ])
        match = SemanticMatch(
            entity_id="d1", entity_name="D", entity_type="Drug",
            edge_type="INDICATED_FOR", strength="strong_for",
            evidence_quality="high", conditions_json=conditions,
        )
        engine._evaluate_match_conditions(match, {"LVEF": 55})
        assert match.conditions_met is False
        assert match.missing_variables == []

    def test_failed_plus_missing_returns_false(self):
        """If any condition explicitly fails, result is False even with missing vars."""
        engine, _ = _make_engine()
        conditions = json.dumps([
            {"variable": "LVEF", "operator": "<=", "threshold": 40},
            {"variable": "eGFR", "operator": ">=", "threshold": 30},
        ])
        match = SemanticMatch(
            entity_id="d1", entity_name="D", entity_type="Drug",
            edge_type="INDICATED_FOR", strength="strong_for",
            evidence_quality="high", conditions_json=conditions,
        )
        engine._evaluate_match_conditions(match, {"LVEF": 55})  # fails; eGFR missing
        assert match.conditions_met is False
        assert "eGFR" in match.missing_variables

    def test_no_conditions_stays_true(self):
        """No conditions_json → conditions_met stays at default True."""
        engine, _ = _make_engine()
        match = SemanticMatch(
            entity_id="d1", entity_name="D", entity_type="Drug",
            edge_type="INDICATED_FOR", strength="strong_for",
            evidence_quality="high", conditions_json=None,
        )
        engine._evaluate_match_conditions(match, {})
        assert match.conditions_met is True

    def test_build_result_sort_order_with_uncertain(self):
        """True matches rank before None (uncertain) which rank before False."""
        engine, _ = _make_engine()
        matches = [
            SemanticMatch(
                entity_id="d_false", entity_name="False", entity_type="Drug",
                edge_type="INDICATED_FOR", strength="strong_for",
                evidence_quality="high", conditions_met=False,
            ),
            SemanticMatch(
                entity_id="d_none", entity_name="None", entity_type="Drug",
                edge_type="INDICATED_FOR", strength="strong_for",
                evidence_quality="high", conditions_met=None,
            ),
            SemanticMatch(
                entity_id="d_true", entity_name="True", entity_type="Drug",
                edge_type="INDICATED_FOR", strength="strong_for",
                evidence_quality="high", conditions_met=True,
            ),
        ]
        q = ClinicalQuery(intent="treatment_selection", concepts=["X"])
        result = engine._build_result(matches, [], q)
        assert result.semantic_matches[0].conditions_met is True
        assert result.semantic_matches[1].conditions_met is None
        assert result.semantic_matches[2].conditions_met is False

    def test_build_result_confidence_medium_for_uncertain_only(self):
        """If only uncertain matches exist, confidence is medium."""
        engine, _ = _make_engine()
        matches = [
            SemanticMatch(
                entity_id="d1", entity_name="D", entity_type="Drug",
                edge_type="INDICATED_FOR", strength="strong_for",
                evidence_quality="high", conditions_met=None,
                missing_variables=["eGFR"],
            ),
        ]
        q = ClinicalQuery(intent="treatment_selection", concepts=["X"])
        result = engine._build_result(matches, [], q)
        assert result.confidence == "medium"

    def test_build_result_confidence_high_when_true_match_exists(self):
        """If at least one True match exists alongside None, confidence is high."""
        engine, _ = _make_engine()
        matches = [
            SemanticMatch(
                entity_id="d1", entity_name="D1", entity_type="Drug",
                edge_type="INDICATED_FOR", strength="strong_for",
                evidence_quality="high", conditions_met=True,
            ),
            SemanticMatch(
                entity_id="d2", entity_name="D2", entity_type="Drug",
                edge_type="INDICATED_FOR", strength="moderate_for",
                evidence_quality="high", conditions_met=None,
                missing_variables=["eGFR"],
            ),
        ]
        q = ClinicalQuery(intent="treatment_selection", concepts=["X"])
        result = engine._build_result(matches, [], q)
        assert result.confidence == "high"


class TestEvaluateCondition:
    def test_numeric_comparison(self):
        # _evaluate_condition receives pre-normalized (lowercase) patient vars
        assert ReasoningEngine._evaluate_condition(
            {"variable": "LVEF", "operator": "<=", "threshold": 40}, {"lvef": 30}
        ) is True

    def test_missing_variable_returns_none(self):
        assert ReasoningEngine._evaluate_condition(
            {"variable": "LVEF", "operator": "<=", "threshold": 40}, {}
        ) is None

    def test_unknown_operator_returns_none(self):
        assert ReasoningEngine._evaluate_condition(
            {"variable": "LVEF", "operator": "~", "threshold": 40}, {"lvef": 30}
        ) is None

    def test_string_comparison_fallback(self):
        result = ReasoningEngine._evaluate_condition(
            {"variable": "sex", "operator": "==", "threshold": "male"},
            {"sex": "male"},
        )
        assert result is True


class TestBuildResult:
    def _make_match(self, strength, conditions_met=True, missing=None):
        return SemanticMatch(
            entity_id="d1",
            entity_name="D",
            entity_type="Drug",
            edge_type="INDICATED_FOR",
            strength=strength,
            evidence_quality="high",
            conditions_met=conditions_met,
            missing_variables=missing or [],
        )

    def test_ranking_conditions_first(self):
        engine, _ = _make_engine()
        matches = [
            self._make_match("weak_for", conditions_met=False),
            self._make_match("strong_for", conditions_met=True),
            self._make_match("moderate_for", conditions_met=True),
        ]
        q = ClinicalQuery(intent="treatment_selection", concepts=["X"])
        result = engine._build_result(matches, [], q)
        # Met conditions first, then by strength rank
        assert result.semantic_matches[0].strength == "strong_for"
        assert result.semantic_matches[0].conditions_met is True
        assert result.semantic_matches[-1].conditions_met is False

    def test_confidence_high_when_full_matches(self):
        engine, _ = _make_engine()
        matches = [self._make_match("strong_for", conditions_met=True)]
        q = ClinicalQuery(intent="treatment_selection", concepts=["X"])
        result = engine._build_result(matches, [], q)
        assert result.confidence == "high"

    def test_confidence_medium_when_no_full_match(self):
        engine, _ = _make_engine()
        matches = [self._make_match("strong_for", conditions_met=False)]
        q = ClinicalQuery(intent="treatment_selection", concepts=["X"])
        result = engine._build_result(matches, [], q)
        assert result.confidence == "medium"

    def test_confidence_low_when_no_matches(self):
        engine, _ = _make_engine()
        q = ClinicalQuery(intent="treatment_selection", concepts=["X"])
        result = engine._build_result([], [], q)
        assert result.confidence == "low"

    def test_missing_variables_collected(self):
        engine, _ = _make_engine()
        matches = [
            self._make_match("strong_for", conditions_met=False, missing=["LVEF"]),
            self._make_match("moderate_for", conditions_met=False, missing=["eGFR", "LVEF"]),
        ]
        q = ClinicalQuery(intent="treatment_selection", concepts=["X"])
        result = engine._build_result(matches, [], q)
        assert set(result.missing_variables) == {"LVEF", "eGFR"}


class TestEmptyResult:
    def test_returns_low_confidence(self):
        result = ReasoningEngine._empty_result()
        assert result.confidence == "low"
        assert result.source == "graph_traversal"
        assert result.semantic_matches == []


class TestFetchEvidence:
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_evidence_enrichment(self, mock_link):
        linked = MagicMock()
        linked.node_id = "disease_hfref"
        mock_link.return_value = linked

        engine, conn = _make_engine()
        # First call: treatments query; second call: evidence fetch
        conn.execute_read.side_effect = [
            [
                {
                    "entity_id": "drug_sacubitril",
                    "entity_name": "Sacubitril/Valsartan",
                    "entity_type": "Drug",
                    "strength": "strong_for",
                    "evidence_quality": "high",
                    "conditions": None,
                }
            ],
            [
                {
                    "source_text": "ARNi recommended for HFrEF...",
                    "guideline": "AHA HF 2022",
                    "doi": "10.1234/test",
                    "section": "Treatment",
                }
            ],
        ]
        q = ClinicalQuery(
            intent="treatment_selection",
            concepts=["HFrEF"],
            include_evidence=True,
        )
        result = engine.query(q)
        assert len(result.evidence) == 1
        assert result.evidence[0].text == "ARNi recommended for HFrEF..."

class TestNewTypeFields:
    def test_semantic_match_source_layer_default(self):
        m = SemanticMatch(
            entity_id="d1", entity_name="D", entity_type="Drug",
            edge_type="INDICATED_FOR", strength="strong_for", evidence_quality="high",
        )
        assert m.source_layer == "direct"

    def test_semantic_match_source_layer_custom(self):
        m = SemanticMatch(
            entity_id="d1", entity_name="D", entity_type="Drug",
            edge_type="INDICATED_FOR", strength="strong_for", evidence_quality="high",
            source_layer="expanded",
        )
        assert m.source_layer == "expanded"

    def test_graphrag_result_new_fields_default(self):
        r = GraphRAGResult()
        assert r.retrieval_layers_used == []
        assert r.hints == []

    def test_graphrag_result_hints_populated(self):
        r = GraphRAGResult(hints=["Try intent='dosing'"])
        assert len(r.hints) == 1

    def test_clinical_query_min_threshold_default(self):
        q = ClinicalQuery(intent="treatment_selection", concepts=["X"])
        assert q.min_results_threshold == 1

    def test_clinical_query_min_threshold_custom(self):
        q = ClinicalQuery(intent="treatment_selection", concepts=["X"], min_results_threshold=5)
        assert q.min_results_threshold == 5


    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_deduplicates_evidence(self, mock_link):
        engine, conn = _make_engine()
        # Simulate two matches returning the same evidence text
        same_text = "Same evidence text"
        matches = [
            SemanticMatch(
                entity_id="d1", entity_name="D1", entity_type="Drug",
                edge_type="INDICATED_FOR", strength="strong_for", evidence_quality="high",
            ),
            SemanticMatch(
                entity_id="d2", entity_name="D2", entity_type="Drug",
                edge_type="INDICATED_FOR", strength="moderate_for", evidence_quality="moderate",
            ),
        ]
        conn.execute_read.return_value = [
            {"source_text": same_text, "guideline": "G", "doi": "", "section": "S"}
        ]
        q = ClinicalQuery(intent="treatment_selection", concepts=["X"])
        evidence = engine._fetch_evidence_for_matches(matches, q)
        assert len(evidence) == 1


class TestLayer2Expansion:
    """Layer 2: DrugClass↔member and Disease↔stage expansion."""

    @patch("open_medicine.graphrag.reasoning.engine_v2.get_drug_class_members")
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_treatment_expands_disease_to_parent(self, mock_link, mock_members):
        """If HFrEF returns 0 results, expand to parent Heart Failure."""
        disease = MagicMock()
        disease.node_id = "snomed:703272007"
        disease.node_label = "Disease"
        disease.entity_type = "disease"

        mock_link.return_value = disease
        mock_members.return_value = []

        engine, conn = _make_engine()
        # Layer 1 returns empty, Layer 2 (parent disease) returns result
        conn.execute_read.side_effect = [
            [],  # Layer 1: find_treatments for HFrEF
            [{"parent_id": "snomed:84114007", "parent_name": "Heart Failure"}],  # find_disease_parents
            [    # Layer 2: find_treatments for parent
                {
                    "entity_id": "drug_x", "entity_name": "DrugX",
                    "entity_type": "Drug", "strength": "strong_for",
                    "evidence_quality": "high", "conditions": None,
                }
            ],
        ]
        q = ClinicalQuery(
            intent="treatment_selection", concepts=["HFrEF"],
            include_evidence=False, min_results_threshold=1,
        )
        result = engine.query(q)
        assert len(result.semantic_matches) >= 1
        assert "expanded" in result.retrieval_layers_used

    @patch("open_medicine.graphrag.reasoning.engine_v2.get_drug_class_members")
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_monitoring_expands_class_to_members(self, mock_link, mock_members):
        """If MRA class has no MONITORED_BY, expand to member drugs."""
        # First call: link_entity("MRA", "drug") returns None
        # Second call: link_entity("MRA", "drug_class") returns None (not in graph)
        # Third call: link_entity("Spironolactone", "drug") returns a drug
        member_drug = MagicMock()
        member_drug.node_id = "rxnorm:35827"
        member_drug.node_label = "Drug"
        member_drug.entity_type = "drug"

        mock_link.side_effect = [None, None, member_drug]
        mock_members.return_value = ["Spironolactone"]

        engine, conn = _make_engine()
        conn.execute_read.side_effect = [
            [    # Layer 2: monitoring for Spironolactone
                {"lab_id": "loinc:2823-3", "lab_name": "Potassium"}
            ],
        ]
        q = ClinicalQuery(
            intent="monitoring", concepts=["MRA"],
            include_evidence=False, min_results_threshold=1,
        )
        result = engine.query(q)
        assert len(result.semantic_matches) >= 1
        assert result.semantic_matches[0].source_layer == "expanded"

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_no_expansion_when_layer1_sufficient(self, mock_link):
        """Layer 2 should NOT run if Layer 1 meets threshold."""
        linked = MagicMock()
        linked.node_id = "disease_hfref"
        mock_link.return_value = linked

        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {
                "entity_id": "drug_1", "entity_name": "Drug1",
                "entity_type": "Drug", "strength": "strong_for",
                "evidence_quality": "high", "conditions": None,
            }
        ]
        q = ClinicalQuery(
            intent="treatment_selection", concepts=["HFrEF"],
            include_evidence=False, min_results_threshold=1,
        )
        result = engine.query(q)
        # Only 1 execute_read call (Layer 1), no expansion
        assert conn.execute_read.call_count == 1
        assert "expanded" not in result.retrieval_layers_used

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_deduplication_across_layers(self, mock_link):
        """Same entity from Layer 1 and Layer 2 — keep Layer 1 version."""
        linked = MagicMock()
        linked.node_id = "disease_hfref"
        linked.entity_type = "disease"
        mock_link.return_value = linked

        engine, conn = _make_engine()
        same_row = {
            "entity_id": "drug_1", "entity_name": "Drug1",
            "entity_type": "Drug", "strength": "strong_for",
            "evidence_quality": "high", "conditions": None,
        }
        conn.execute_read.return_value = [same_row]

        # Simulate: Layer 1 returns 1 result, Layer 2 returns same entity
        q = ClinicalQuery(
            intent="treatment_selection", concepts=["HFrEF"],
            include_evidence=False, min_results_threshold=1,
        )
        result = engine.query(q)
        # Should have exactly 1, not 2
        drug1_matches = [m for m in result.semantic_matches if m.entity_id == "drug_1"]
        assert len(drug1_matches) == 1
        assert drug1_matches[0].source_layer == "direct"


class TestLayer3VectorFallback:
    """Layer 3: Vector search over EvidenceChunks when Layers 1+2 return nothing."""

    @patch("open_medicine.graphrag.reasoning.engine_v2.embed_query")
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_vector_fallback_when_graph_empty(self, mock_link, mock_embed):
        """When Layers 1+2 return 0, try vector search."""
        mock_link.return_value = None  # Entity not found → no Layer 1/2 results
        mock_embed.return_value = [0.1] * 1024

        engine, conn = _make_engine()
        # Vector search returns entities via chunk traversal
        conn.execute_read.return_value = [
            {
                "entity_id": "drug_1", "entity_name": "SomeDrug",
                "entity_type": "Drug", "strength": "strong_for",
                "evidence_quality": "high", "conditions": None,
                "score": 0.92,
            }
        ]
        q = ClinicalQuery(
            intent="treatment_selection", concepts=["SomeRareCondition"],
            include_evidence=False,
        )
        result = engine.query(q)
        assert len(result.semantic_matches) >= 1
        assert result.semantic_matches[0].source_layer == "vector"
        assert "vector" in result.retrieval_layers_used

    @patch("open_medicine.graphrag.reasoning.engine_v2.embed_query")
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_vector_fallback_skipped_when_layer1_has_results(self, mock_link, mock_embed):
        """Vector fallback should NOT run if Layer 1 has results."""
        linked = MagicMock()
        linked.node_id = "disease_hfref"
        mock_link.return_value = linked

        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {
                "entity_id": "drug_1", "entity_name": "Drug1",
                "entity_type": "Drug", "strength": "strong_for",
                "evidence_quality": "high", "conditions": None,
            }
        ]
        q = ClinicalQuery(
            intent="treatment_selection", concepts=["HFrEF"],
            include_evidence=False,
        )
        result = engine.query(q)
        mock_embed.assert_not_called()
        assert "vector" not in result.retrieval_layers_used

    @patch("open_medicine.graphrag.reasoning.engine_v2.embed_query", side_effect=Exception("No API key"))
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity", return_value=None)
    def test_vector_fallback_graceful_on_embed_error(self, mock_link, mock_embed):
        """If embedding fails (no API key), skip Layer 3 gracefully."""
        engine, conn = _make_engine()
        q = ClinicalQuery(
            intent="treatment_selection", concepts=["Unknown"],
            include_evidence=False,
        )
        result = engine.query(q)
        # Should not crash, just return empty
        assert result.confidence == "low"


class TestLayer4Hints:
    """Layer 4: Actionable hints when all layers return nothing."""

    @patch("open_medicine.graphrag.reasoning.engine_v2.embed_query", side_effect=Exception("skip"))
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity", return_value=None)
    def test_unknown_concept_suggests_similar(self, mock_link, mock_embed):
        engine, conn = _make_engine()
        q = ClinicalQuery(
            intent="treatment_selection", concepts=["Carvedilo"],  # typo
            include_evidence=False,
        )
        result = engine.query(q)
        assert len(result.hints) > 0
        assert any("Carvedilol" in h for h in result.hints)

    @patch("open_medicine.graphrag.reasoning.engine_v2.embed_query", side_effect=Exception("skip"))
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity", return_value=None)
    def test_unsupported_intent_suggests_alternatives(self, mock_link, mock_embed):
        engine, conn = _make_engine()
        q = ClinicalQuery(
            intent="surgery_planning", concepts=["CABG"],
            include_evidence=False,
        )
        result = engine.query(q)
        assert any("treatment_selection" in h for h in result.hints)

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_no_hints_when_results_exist(self, mock_link):
        linked = MagicMock()
        linked.node_id = "disease_hfref"
        mock_link.return_value = linked

        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {
                "entity_id": "drug_1", "entity_name": "Drug1",
                "entity_type": "Drug", "strength": "strong_for",
                "evidence_quality": "high", "conditions": None,
            }
        ]
        q = ClinicalQuery(
            intent="treatment_selection", concepts=["HFrEF"],
            include_evidence=False,
        )
        result = engine.query(q)
        assert result.hints == []


class TestSourceLayerSorting:
    def _make_match(self, source_layer, strength="strong_for", conditions_met=True):
        return SemanticMatch(
            entity_id=f"id_{source_layer}_{strength}", entity_name=f"Name_{source_layer}",
            entity_type="Drug", edge_type="INDICATED_FOR",
            strength=strength, evidence_quality="high",
            conditions_met=conditions_met, source_layer=source_layer,
        )

    def test_direct_ranks_before_expanded(self):
        engine, _ = _make_engine()
        matches = [
            self._make_match("expanded"),
            self._make_match("direct"),
        ]
        q = ClinicalQuery(intent="treatment_selection", concepts=["X"])
        result = engine._build_result(matches, [], q)
        assert result.semantic_matches[0].source_layer == "direct"
        assert result.semantic_matches[1].source_layer == "expanded"

    def test_expanded_ranks_before_vector(self):
        engine, _ = _make_engine()
        matches = [
            self._make_match("vector"),
            self._make_match("expanded"),
        ]
        q = ClinicalQuery(intent="treatment_selection", concepts=["X"])
        result = engine._build_result(matches, [], q)
        assert result.semantic_matches[0].source_layer == "expanded"
        assert result.semantic_matches[1].source_layer == "vector"

    def test_full_sort_order(self):
        engine, _ = _make_engine()
        matches = [
            self._make_match("vector", "weak_for", conditions_met=False),
            self._make_match("direct", "moderate_for", conditions_met=True),
            self._make_match("expanded", "strong_for", conditions_met=True),
            self._make_match("direct", "strong_for", conditions_met=True),
        ]
        q = ClinicalQuery(intent="treatment_selection", concepts=["X"])
        result = engine._build_result(matches, [], q)
        layers = [m.source_layer for m in result.semantic_matches]
        # direct+met first (sorted by strength), then expanded+met, then vector+unmet
        assert layers[0] == "direct"
        assert layers[-1] == "vector"


# ---------------------------------------------------------------------------
# Fix 1: Class-Level Edge Inheritance
# ---------------------------------------------------------------------------


class TestClassInheritance:
    """Tests for drug → drug class inheritance in monitoring/interactions."""

    def _mock_drug_entity(self, name="Lisinopril", node_id="rxnorm:29046"):
        entity = MagicMock()
        entity.node_id = node_id
        entity.node_label = "Drug"
        entity.snomed_code = None
        entity.rxnorm_code = "29046"
        entity.atc_code = None
        entity.loinc_code = None
        entity.icd10_code = None
        entity.cpt_code = None
        entity.gmdn_code = None
        return entity

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_monitoring_inherits_from_class(self, mock_link):
        """Query Lisinopril monitoring should inherit from ACE Inhibitor class."""
        entity = self._mock_drug_entity()
        mock_link.return_value = entity

        engine, conn = _make_engine()

        # First call: find_monitoring for Drug — returns empty (no direct edges)
        # Second call: find_drug_class — returns ACE Inhibitor class
        # Third call: find_monitoring for DrugClass — returns monitoring labs
        conn.execute_read.side_effect = [
            [],  # Drug-level monitoring: empty
            [{"class_id": "atc:C09A", "class_name": "ACE Inhibitor"}],  # MEMBER_OF
            [  # Class-level monitoring: has results
                {"lab_id": "loinc:2823-3", "lab_name": "Potassium"},
                {"lab_id": "loinc:2160-0", "lab_name": "Creatinine"},
            ],
            [],  # _fetch_evidence_for_matches for Potassium
            [],  # _fetch_evidence_for_matches for Creatinine
        ]

        q = ClinicalQuery(intent="monitoring", concepts=["Lisinopril"])
        result = engine.query(q)

        assert len(result.semantic_matches) == 2
        lab_names = {m.entity_name for m in result.semantic_matches}
        assert "Potassium" in lab_names
        assert "Creatinine" in lab_names
        # Inherited results should be marked as expanded
        assert all(m.source_layer == "expanded" for m in result.semantic_matches)

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_interaction_inherits_from_class(self, mock_link):
        """Query Spironolactone interactions should inherit from MRA class."""
        entity = self._mock_drug_entity(
            name="Spironolactone", node_id="rxnorm:9997"
        )
        mock_link.return_value = entity

        engine, conn = _make_engine()

        conn.execute_read.side_effect = [
            [],  # Drug-level interactions: empty
            [{"class_id": "atc:C03DA", "class_name": "MRA"}],  # MEMBER_OF
            [  # Class-level interactions
                {
                    "entity_id": "atc:C09A",
                    "entity_name": "ACE Inhibitor",
                    "entity_type": "DrugClass",
                },
            ],
            [],  # _fetch_evidence_for_matches for ACE Inhibitor
        ]

        q = ClinicalQuery(intent="interaction", concepts=["Spironolactone"])
        result = engine.query(q)

        assert len(result.semantic_matches) == 1
        assert result.semantic_matches[0].entity_name == "ACE Inhibitor"
        assert result.semantic_matches[0].source_layer == "expanded"

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_direct_match_skips_inheritance(self, mock_link):
        """When drug has direct edges, class lookup should not happen."""
        entity = self._mock_drug_entity(
            name="Spironolactone", node_id="rxnorm:9997"
        )
        mock_link.return_value = entity

        engine, conn = _make_engine()

        # Drug-level monitoring returns results — no inheritance needed
        conn.execute_read.return_value = [
            {"lab_id": "loinc:2823-3", "lab_name": "Potassium"},
        ]

        q = ClinicalQuery(
            intent="monitoring", concepts=["Spironolactone"],
            include_evidence=False,
        )
        result = engine.query(q)

        assert len(result.semantic_matches) == 1
        assert result.semantic_matches[0].entity_name == "Potassium"
        # Should be direct layer, not expanded
        assert result.semantic_matches[0].source_layer == "direct"
        # execute_read called only once (for drug-level query, not class lookup)
        assert conn.execute_read.call_count == 1

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_contraindication_inherits_from_class(self, mock_link):
        """Drug with no direct contraindications inherits from class."""
        entity = self._mock_drug_entity()
        mock_link.return_value = entity

        engine, conn = _make_engine()

        conn.execute_read.side_effect = [
            [],  # Drug-level contraindications: empty
            [{"class_id": "atc:C09A", "class_name": "ACE Inhibitor"}],  # MEMBER_OF
            [  # Class-level contraindications
                {
                    "disease_id": "snomed:77386006",
                    "disease_name": "Pregnancy",
                    "strength": "strong_against",
                },
            ],
            [],  # _fetch_evidence_for_matches
        ]

        q = ClinicalQuery(
            intent="contraindication", concepts=["Lisinopril"],
            include_evidence=False,
        )
        result = engine.query(q)

        assert len(result.semantic_matches) == 1
        assert result.semantic_matches[0].entity_name == "Pregnancy"
        assert result.semantic_matches[0].source_layer == "expanded"

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_dosing_inherits_from_class(self, mock_link):
        """Drug with no direct dosing edges inherits from class."""
        entity = self._mock_drug_entity()
        mock_link.return_value = entity

        engine, conn = _make_engine()

        conn.execute_read.side_effect = [
            [],  # Drug-level dosing: empty
            [{"class_id": "atc:C09A", "class_name": "ACE Inhibitor"}],  # MEMBER_OF
            [  # Class-level dosing
                {"disease": "Heart Failure", "disease_id": "snomed:84114007"},
            ],
        ]

        q = ClinicalQuery(
            intent="dosing", concepts=["Lisinopril"],
            include_evidence=False,
        )
        result = engine.query(q)

        assert len(result.semantic_matches) == 1
        assert result.semantic_matches[0].source_layer == "expanded"


# ---------------------------------------------------------------------------
# Fix 2: Terminology Expansion
# ---------------------------------------------------------------------------


class TestTerminologyExpansion:
    """Tests for new terminology entries resolving correctly."""

    def test_nsaid_resolves(self):
        from open_medicine.graphrag.ingestion.linker_v2 import link_entity

        entity = link_entity("NSAIDs", "drug_class")
        assert entity is not None
        assert entity.atc_code == "M01A"

    def test_nsaid_singular_resolves(self):
        from open_medicine.graphrag.ingestion.linker_v2 import link_entity

        entity = link_entity("NSAID", "drug_class")
        assert entity is not None
        assert entity.atc_code == "M01A"

    def test_ccb_resolves(self):
        from open_medicine.graphrag.ingestion.linker_v2 import link_entity

        entity = link_entity("Calcium Channel Blockers", "drug_class")
        assert entity is not None
        assert entity.atc_code == "C08"

    def test_ccb_abbreviation_resolves(self):
        from open_medicine.graphrag.ingestion.linker_v2 import link_entity

        entity = link_entity("CCB", "drug_class")
        assert entity is not None
        assert entity.atc_code == "C08"

    def test_common_abbreviations(self):
        """All common drug class abbreviations should resolve."""
        from open_medicine.graphrag.ingestion.linker_v2 import link_entity

        abbreviations = {
            "ACEi": "C09A",
            "ARNi": "C09DX",
            "BB": "C07",
            "CCB": "C08",
            "MRA": "C03DA",
            "SGLT2i": "A10BK",
        }
        for abbr, expected_atc in abbreviations.items():
            entity = link_entity(abbr, "drug_class")
            assert entity is not None, f"{abbr} did not resolve"
            assert entity.atc_code == expected_atc, (
                f"{abbr} resolved to {entity.atc_code}, expected {expected_atc}"
            )

    def test_beta_blockers_plural_resolves(self):
        from open_medicine.graphrag.ingestion.linker_v2 import link_entity

        entity = link_entity("beta-blockers", "drug_class")
        assert entity is not None
        assert entity.atc_code == "C07"

    def test_sacubitril_valsartan_resolves(self):
        from open_medicine.graphrag.ingestion.linker_v2 import link_entity

        entity = link_entity("sacubitril-valsartan", "drug_class")
        assert entity is not None
        assert entity.atc_code == "C09DX"


# ---------------------------------------------------------------------------
# Fix 3: Variable Alias Resolution
# ---------------------------------------------------------------------------


class TestVariableAliases:
    """Tests for variable name alias resolution in condition evaluation."""

    def test_variable_alias_heart_failure_type(self):
        """Patient vars with heart_failure_type should match HF_type condition."""
        engine, _ = _make_engine()
        match = SemanticMatch(
            entity_id="test",
            entity_name="Test",
            entity_type="Drug",
            edge_type="INDICATED_FOR",
            strength="strong_for",
            evidence_quality="high",
            conditions_json=json.dumps([
                {"variable": "HF_type", "operator": "==", "threshold": "HFrEF"},
            ]),
        )

        engine._evaluate_match_conditions(
            match, {"heart_failure_type": "HFrEF"}
        )

        assert match.conditions_met is True
        assert match.missing_variables == []

    def test_variable_alias_ef(self):
        """Patient vars with ejection_fraction should match LVEF condition."""
        engine, _ = _make_engine()
        match = SemanticMatch(
            entity_id="test",
            entity_name="Test",
            entity_type="Drug",
            edge_type="INDICATED_FOR",
            strength="strong_for",
            evidence_quality="high",
            conditions_json=json.dumps([
                {"variable": "LVEF", "operator": "<=", "threshold": "40"},
            ]),
        )

        engine._evaluate_match_conditions(
            match, {"ejection_fraction": 35}
        )

        assert match.conditions_met is True

    def test_canonical_still_works(self):
        """Patient vars with lvef should still match LVEF condition."""
        engine, _ = _make_engine()
        match = SemanticMatch(
            entity_id="test",
            entity_name="Test",
            entity_type="Drug",
            edge_type="INDICATED_FOR",
            strength="strong_for",
            evidence_quality="high",
            conditions_json=json.dumps([
                {"variable": "LVEF", "operator": "<=", "threshold": "40"},
            ]),
        )

        engine._evaluate_match_conditions(match, {"lvef": 30})

        assert match.conditions_met is True
        assert match.missing_variables == []

    def test_alias_missing_variable_still_reported(self):
        """Unresolvable variables should still be reported as missing."""
        engine, _ = _make_engine()
        match = SemanticMatch(
            entity_id="test",
            entity_name="Test",
            entity_type="Drug",
            edge_type="INDICATED_FOR",
            strength="strong_for",
            evidence_quality="high",
            conditions_json=json.dumps([
                {"variable": "LVEF", "operator": "<=", "threshold": "40"},
                {"variable": "some_unknown_var", "operator": "==", "threshold": "yes"},
            ]),
        )

        engine._evaluate_match_conditions(match, {"ejection_fraction": 35})

        assert match.conditions_met is None  # uncertain: known condition met but missing var
        assert "some_unknown_var" in match.missing_variables

    def test_multiple_aliases_in_same_query(self):
        """Multiple aliased variables should all resolve correctly."""
        engine, _ = _make_engine()
        match = SemanticMatch(
            entity_id="test",
            entity_name="Test",
            entity_type="Drug",
            edge_type="INDICATED_FOR",
            strength="strong_for",
            evidence_quality="high",
            conditions_json=json.dumps([
                {"variable": "LVEF", "operator": "<=", "threshold": "40"},
                {"variable": "potassium", "operator": "<", "threshold": "5.0"},
                {"variable": "eGFR", "operator": ">=", "threshold": "30"},
            ]),
        )

        engine._evaluate_match_conditions(
            match,
            {"ejection_fraction": 35, "K": 4.5, "estimated_gfr": 45},
        )

        assert match.conditions_met is True
        assert match.missing_variables == []


# ---------------------------------------------------------------------------
# Fix 6: Fuzzy Auto-Retry
# ---------------------------------------------------------------------------


class TestFuzzyAutoRetry:
    """Tests for automatic retry with fuzzy-matched concepts."""

    @patch("open_medicine.graphrag.reasoning.engine_v2.get_drug_class_members", return_value=[])
    @patch("open_medicine.graphrag.reasoning.engine_v2.fuzzy_match")
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_fuzzy_auto_retry_on_empty_results(self, mock_link, mock_fuzzy, _mock_members):
        """When initial query returns empty with misspelling, auto-retry with fuzzy match."""
        # "spironolacton" (misspelled) → fuzzy suggests "Spironolactone"
        mock_fuzzy.return_value = [("Spironolactone", "drug")]

        def link_side_effect(name, etype):
            if etype != "drug":
                return None
            # Only resolve exact canonical name
            if name != "Spironolactone":
                return None
            entity = MagicMock()
            entity.node_id = "rxnorm:9997"
            entity.node_label = "Drug"
            entity.snomed_code = None
            entity.rxnorm_code = "9997"
            entity.atc_code = None
            entity.loinc_code = None
            entity.icd10_code = None
            entity.cpt_code = None
            entity.gmdn_code = None
            return entity

        mock_link.side_effect = link_side_effect

        engine, conn = _make_engine()

        # Retry with "Spironolactone": monitoring returns results
        conn.execute_read.side_effect = [
            [{"lab_id": "loinc:2823-3", "lab_name": "Potassium"}],
            [],  # _fetch_evidence_for_matches
        ]

        q = ClinicalQuery(intent="monitoring", concepts=["spironolacton"])
        result = engine.query(q)

        assert len(result.semantic_matches) == 1
        assert result.semantic_matches[0].entity_name == "Potassium"

    @patch("open_medicine.graphrag.reasoning.engine_v2.fuzzy_match")
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity", return_value=None)
    def test_fuzzy_no_infinite_loop(self, _mock_link, mock_fuzzy):
        """When no fuzzy match, should generate hints without retry loop."""
        mock_fuzzy.return_value = []

        engine, conn = _make_engine()
        q = ClinicalQuery(intent="monitoring", concepts=["unknowndrug"])
        result = engine.query(q)

        assert len(result.semantic_matches) == 0
        # Should still have hints
        assert result.confidence == "low"

    @patch("open_medicine.graphrag.reasoning.engine_v2.fuzzy_match")
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity", return_value=None)
    def test_fuzzy_same_concept_no_retry(self, _mock_link, mock_fuzzy):
        """If fuzzy match returns same concept (case-insensitive), don't retry."""
        mock_fuzzy.return_value = [("unknowndrug", "drug")]

        engine, conn = _make_engine()
        q = ClinicalQuery(intent="monitoring", concepts=["unknowndrug"])
        result = engine.query(q)

        # Should not retry — fuzzy returned same concept
        assert len(result.semantic_matches) == 0


class TestQueryMonitoring:
    @patch("open_medicine.graphrag.reasoning.engine_v2.get_drug_class_members", return_value=[])
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_drug_class_direct_lookup_before_expansion(self, mock_link, mock_members):
        """When 'MRA' fails as drug, try drug_class directly before expanding."""
        mock_class_entity = MagicMock()
        mock_class_entity.node_id = "class_mra"
        mock_class_entity.node_label = "DrugClass"

        # First call: link_entity("MRA", "drug") -> None
        # Second call: link_entity("MRA", "drug_class") -> mock_class_entity
        mock_link.side_effect = [None, mock_class_entity]

        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {"lab_id": "lab_potassium", "lab_name": "Potassium"}
        ]
        q = ClinicalQuery(intent="monitoring", concepts=["MRA"])
        result = engine.query(q)

        assert len(result.semantic_matches) >= 1
        assert result.semantic_matches[0].entity_name == "Potassium"
        assert mock_link.call_count == 2
        mock_members.assert_not_called()


class TestQueryDosing:
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_drug_class_fallback(self, mock_link):
        """When drug lookup fails, try drug_class before returning empty."""
        mock_class_entity = MagicMock()
        mock_class_entity.node_id = "class_arni"
        mock_class_entity.node_label = "DrugClass"

        mock_link.side_effect = [None, mock_class_entity]

        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {"disease_id": "disease_hfref", "disease": "HFrEF", "conditions": None}
        ]
        q = ClinicalQuery(intent="dosing", concepts=["ARNi"])
        result = engine.query(q)

        assert len(result.semantic_matches) >= 1
        assert mock_link.call_count == 2


class TestEvidenceReranking:
    @patch("open_medicine.graphrag.reasoning.engine_v2.embed_query")
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_evidence_ranked_by_relevance(self, mock_link, mock_embed):
        """Evidence re-ranked by cosine similarity when > 5 candidates."""
        mock_embed.return_value = [1.0, 0.0, 0.0]

        engine, conn = _make_engine()

        # First call: find_recommendations_for_entity returns 6+ citations
        # Second call: embedding fetch
        recommendations = [
            {"source_text": f"text_{i}", "guideline": "AHA", "doi": "10.1161/test", "section": "S"}
            for i in range(8)
        ]
        embeddings = [
            {"text": "text_0", "embedding": [0.0, 1.0, 0.0]},
            {"text": "text_1", "embedding": [0.9, 0.1, 0.0]},  # most similar
            {"text": "text_2", "embedding": [0.5, 0.5, 0.0]},
            {"text": "text_3", "embedding": [0.1, 0.9, 0.0]},
            {"text": "text_4", "embedding": [0.8, 0.2, 0.0]},  # second most
            {"text": "text_5", "embedding": [0.0, 0.0, 1.0]},
            {"text": "text_6", "embedding": [0.3, 0.7, 0.0]},
            {"text": "text_7", "embedding": [0.7, 0.3, 0.0]},  # third most
        ]
        conn.execute_read.side_effect = [recommendations, embeddings]

        matches = [
            SemanticMatch(
                entity_id="x", entity_name="X", entity_type="Drug", edge_type="INDICATED_FOR",
                strength="strong_for", evidence_quality="high",
            )
        ]
        q = ClinicalQuery(intent="monitoring", concepts=["Spironolactone"], include_evidence=True)

        evidence = engine._fetch_evidence_for_matches(matches, q)

        assert len(evidence) == 5
        # Most similar (text_1, score ~0.99) should be first
        assert evidence[0].text == "text_1"

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_evidence_no_reranking_when_few(self, mock_link):
        """When <= 5 evidence citations, skip re-ranking."""
        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {"source_text": "Only one citation", "guideline": "AHA", "doi": "10.1161/test", "section": "X"},
        ]

        matches = [SemanticMatch(
            entity_id="x", entity_name="X", entity_type="Drug", edge_type="INDICATED_FOR",
            strength="strong_for", evidence_quality="high",
        )]
        q = ClinicalQuery(intent="treatment_selection", concepts=["X"], include_evidence=True)

        evidence = engine._fetch_evidence_for_matches(matches, q)
        assert len(evidence) == 1


# ---------------------------------------------------------------------------
# Fix: Vector Fallback Deduplication
# ---------------------------------------------------------------------------


class TestVectorDeduplication:
    @patch("open_medicine.graphrag.reasoning.engine_v2.embed_query")
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity", return_value=None)
    def test_vector_results_deduplicated(self, mock_link, mock_embed):
        """Vector fallback results should be deduplicated."""
        mock_embed.return_value = [1.0, 0.0]

        engine, conn = _make_engine()
        # Return duplicate entity_ids from vector search
        conn.execute_read.return_value = [
            {"entity_id": "disease_hfref", "entity_name": "HFrEF", "entity_type": "Disease",
             "strength": "", "evidence_quality": "", "conditions": None},
            {"entity_id": "disease_hfref", "entity_name": "HFrEF", "entity_type": "Disease",
             "strength": "", "evidence_quality": "", "conditions": None},
            {"entity_id": "class_mra", "entity_name": "MRA", "entity_type": "DrugClass",
             "strength": "", "evidence_quality": "", "conditions": None},
        ]

        q = ClinicalQuery(intent="monitoring", concepts=["MRA"])
        result = engine.query(q)

        # Should be deduplicated: only 2 unique (entity_id, edge_type) pairs
        assert len(result.semantic_matches) == 2
        names = {m.entity_name for m in result.semantic_matches}
        assert names == {"HFrEF", "MRA"}


# ---------------------------------------------------------------------------
# C7: data_coverage — distinguish "no data" from "no contraindications"
# ---------------------------------------------------------------------------


def _make_unknown_entity():
    """Create a mock entity that is NOT in terminology (no coded IDs)."""
    entity = MagicMock()
    entity.node_id = "drug:unknowndrug123"
    entity.node_label = "Drug"
    entity.snomed_code = None
    entity.rxnorm_code = None
    entity.atc_code = None
    entity.loinc_code = None
    entity.icd10_code = None
    entity.cpt_code = None
    entity.gmdn_code = None
    return entity


def _make_known_entity(node_id="rxnorm:12345", label="Drug"):
    """Create a mock entity that IS in terminology (has coded IDs)."""
    entity = MagicMock()
    entity.node_id = node_id
    entity.node_label = label
    entity.snomed_code = None
    entity.rxnorm_code = "12345"
    entity.atc_code = None
    entity.loinc_code = None
    entity.icd10_code = None
    entity.cpt_code = None
    entity.gmdn_code = None
    return entity


class TestDataCoverageContraindications:
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_unknown_drug_returns_coverage_none(self, mock_link):
        """Unknown drug -> data_coverage='none' (cannot confirm safety)."""
        unknown = _make_unknown_entity()
        mock_link.return_value = unknown

        engine, conn = _make_engine()
        conn.execute_read.return_value = []

        q = ClinicalQuery(intent="contraindication", concepts=["FakeDrugXYZ"])
        result = engine.query(q)

        assert result.data_coverage == "none"

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_known_drug_no_results_returns_coverage_full(self, mock_link):
        """Known drug with no contraindications -> data_coverage='full'."""
        known = _make_known_entity()
        mock_link.return_value = known

        engine, conn = _make_engine()
        conn.execute_read.return_value = []

        q = ClinicalQuery(intent="contraindication", concepts=["Metoprolol"])
        result = engine.query(q)

        assert result.data_coverage == "full"

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_mixed_concepts_returns_coverage_partial(self, mock_link):
        """One known + one unknown concept -> data_coverage='partial'."""
        known = _make_known_entity()
        unknown = _make_unknown_entity()

        # contraindications: tries ("drug", "drug_class") per concept
        # Concept 1 "Metoprolol": drug -> known, finds rows -> found=True, break
        # Concept 2 "FakeDrug": drug -> unknown (not None but no codes),
        #   no CI rows, then parent classes (empty), then drug_class -> unknown, no CI rows
        mock_link.side_effect = [known, unknown, unknown]

        engine, conn = _make_engine()
        # Call 1: find_contraindications for known drug -> results, break
        # Call 2: find_contraindications for unknown as drug -> empty
        # Call 3: _get_parent_classes for unknown drug -> empty
        # Call 4: find_contraindications for unknown as drug_class -> empty
        conn.execute_read.side_effect = [
            [{"disease_id": "d1", "disease_name": "Asthma",
              "strength": "strong_against", "evidence_quality": "",
              "conditions": None}],
            [],  # CI for FakeDrug as drug
            [],  # parent classes for FakeDrug
            [],  # CI for FakeDrug as drug_class
        ]

        q = ClinicalQuery(
            intent="contraindication", concepts=["Metoprolol", "FakeDrug"],
            include_evidence=False,
        )
        result = engine.query(q)

        assert result.data_coverage == "partial"


class TestDataCoverageTreatments:
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_unknown_disease_returns_coverage_none(self, mock_link):
        """Unknown disease -> data_coverage='none'."""
        unknown = _make_unknown_entity()
        unknown.node_label = "Disease"
        mock_link.return_value = unknown

        engine, conn = _make_engine()
        conn.execute_read.return_value = []

        q = ClinicalQuery(intent="treatment_selection", concepts=["FakeDisease"])
        result = engine.query(q)

        assert result.data_coverage == "none"

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_known_disease_returns_coverage_full(self, mock_link):
        """Known disease -> data_coverage='full'."""
        known = _make_known_entity(node_id="snomed:42343007", label="Disease")
        known.snomed_code = "42343007"
        mock_link.return_value = known

        engine, conn = _make_engine()
        conn.execute_read.return_value = []

        q = ClinicalQuery(intent="treatment_selection", concepts=["Heart Failure"])
        result = engine.query(q)

        assert result.data_coverage == "full"


class TestDataCoverageInteractions:
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_unknown_drug_interactions_coverage_none(self, mock_link):
        """Unknown drug in interaction query -> data_coverage='none'."""
        unknown = _make_unknown_entity()
        mock_link.return_value = unknown

        engine, conn = _make_engine()
        conn.execute_read.return_value = []

        q = ClinicalQuery(intent="interaction", concepts=["UnknownDrug"])
        result = engine.query(q)

        assert result.data_coverage == "none"


class TestDataCoverageMonitoring:
    @patch("open_medicine.graphrag.reasoning.engine_v2.get_drug_class_members", return_value=[])
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity", return_value=None)
    def test_fully_unknown_monitoring_coverage_none(self, _mock_link, _mock_members):
        """Completely unknown concept -> data_coverage='none'."""
        engine, conn = _make_engine()
        conn.execute_read.return_value = []

        q = ClinicalQuery(intent="monitoring", concepts=["TotallyUnknown"])
        result = engine.query(q)

        assert result.data_coverage == "none"


class TestDataCoverageDosing:
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_known_drug_dosing_coverage_full(self, mock_link):
        """Known drug in dosing query -> data_coverage='full'."""
        known = _make_known_entity()
        mock_link.return_value = known

        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {"disease_id": "d1", "disease": "HFrEF", "conditions": None}
        ]

        q = ClinicalQuery(intent="dosing", concepts=["Metoprolol"])
        result = engine.query(q)

        assert result.data_coverage == "full"


class TestVectorSimilarityThreshold:
    """Tests for cosine similarity threshold filtering in vector fallback."""

    @patch("open_medicine.graphrag.reasoning.engine_v2.embed_query")
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity", return_value=None)
    def test_below_threshold_filtered_out(self, _mock_link, mock_embed):
        """Vector results with score < 0.7 should be discarded."""
        mock_embed.return_value = [0.1] * 128
        engine, conn = _make_engine()
        # Return rows: one below threshold, one above
        conn.execute_read.return_value = [
            {
                "entity_id": "drug_aspirin",
                "entity_name": "Aspirin",
                "entity_type": "Drug",
                "strength": "weak_for",
                "evidence_quality": "low",
                "conditions": None,
                "score": 0.5,
            },
            {
                "entity_id": "drug_acetaminophen",
                "entity_name": "Acetaminophen",
                "entity_type": "Drug",
                "strength": "strong_for",
                "evidence_quality": "high",
                "conditions": None,
                "score": 0.85,
            },
        ]
        q = ClinicalQuery(
            intent="treatment_selection",
            concepts=["acetaminophen"],
            include_evidence=False,
        )
        result = engine.query(q)

        # Only the above-threshold match should survive
        assert len(result.semantic_matches) == 1
        assert result.semantic_matches[0].entity_name == "Acetaminophen"

    @patch("open_medicine.graphrag.reasoning.engine_v2.embed_query")
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity", return_value=None)
    def test_above_threshold_kept(self, _mock_link, mock_embed):
        """Vector results at or above 0.7 should be kept."""
        mock_embed.return_value = [0.1] * 128
        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {
                "entity_id": "drug_a",
                "entity_name": "DrugA",
                "entity_type": "Drug",
                "strength": "",
                "evidence_quality": "",
                "conditions": None,
                "score": 0.7,
            },
            {
                "entity_id": "drug_b",
                "entity_name": "DrugB",
                "entity_type": "Drug",
                "strength": "",
                "evidence_quality": "",
                "conditions": None,
                "score": 0.95,
            },
        ]
        q = ClinicalQuery(
            intent="treatment_selection",
            concepts=["something"],
            include_evidence=False,
        )
        result = engine.query(q)

        assert len(result.semantic_matches) == 2
        names = {m.entity_name for m in result.semantic_matches}
        assert names == {"DrugA", "DrugB"}

    @patch("open_medicine.graphrag.reasoning.engine_v2.embed_query")
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity", return_value=None)
    def test_similarity_score_populated_on_vector_matches(self, _mock_link, mock_embed):
        """Vector matches should have similarity_score set from the row score."""
        mock_embed.return_value = [0.1] * 128
        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {
                "entity_id": "drug_x",
                "entity_name": "DrugX",
                "entity_type": "Drug",
                "strength": "",
                "evidence_quality": "",
                "conditions": None,
                "score": 0.82,
            },
        ]
        q = ClinicalQuery(
            intent="treatment_selection",
            concepts=["test"],
            include_evidence=False,
        )
        result = engine.query(q)

        assert len(result.semantic_matches) == 1
        match = result.semantic_matches[0]
        assert match.similarity_score == 0.82
        assert match.source_layer == "vector"

    def test_non_vector_matches_have_none_similarity_score(self):
        """Non-vector SemanticMatch objects should have similarity_score=None."""
        match = SemanticMatch(
            entity_id="drug_1",
            entity_name="TestDrug",
            entity_type="Drug",
            edge_type="INDICATED_FOR",
            strength="strong_for",
            evidence_quality="high",
            source_layer="direct",
        )
        assert match.similarity_score is None

    @patch("open_medicine.graphrag.reasoning.engine_v2.embed_query")
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity", return_value=None)
    def test_all_below_threshold_returns_empty(self, _mock_link, mock_embed):
        """If all vector results are below threshold, return empty list."""
        mock_embed.return_value = [0.1] * 128
        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {
                "entity_id": "drug_a",
                "entity_name": "DrugA",
                "entity_type": "Drug",
                "strength": "",
                "evidence_quality": "",
                "conditions": None,
                "score": 0.3,
            },
            {
                "entity_id": "drug_b",
                "entity_name": "DrugB",
                "entity_type": "Drug",
                "strength": "",
                "evidence_quality": "",
                "conditions": None,
                "score": 0.65,
            },
        ]
        q = ClinicalQuery(
            intent="treatment_selection",
            concepts=["something"],
            include_evidence=False,
        )
        result = engine.query(q)

        assert len(result.semantic_matches) == 0

    def test_threshold_is_module_constant(self):
        """VECTOR_SIMILARITY_THRESHOLD should be 0.7."""
        assert VECTOR_SIMILARITY_THRESHOLD == 0.7


class TestVectorOnlyConfidenceDowngrade:
    """C5: Vector-only results should be capped at 'medium' confidence.

    When all results come exclusively from the vector fallback layer,
    confidence must not be 'high' — vector matches are semantically
    approximate and may be clinically incorrect.
    """

    def test_vector_only_high_downgraded_to_medium(self):
        """If _build_result would assign 'high' but all matches are vector-sourced,
        confidence should be downgraded to 'medium'."""
        engine, _ = _make_engine()
        matches = [
            SemanticMatch(
                entity_id="drug_x",
                entity_name="DrugX",
                entity_type="Drug",
                edge_type="INDICATED_FOR",
                strength="strong_for",
                evidence_quality="high",
                conditions_met=True,
                source_layer="vector",
                similarity_score=0.85,
            )
        ]
        q = ClinicalQuery(intent="treatment_selection", concepts=["test"])
        result = engine._build_result(matches, [], q)
        assert result.confidence == "medium"

    def test_direct_layer_keeps_high_confidence(self):
        """Results from direct layer should keep 'high' confidence."""
        engine, _ = _make_engine()
        matches = [
            SemanticMatch(
                entity_id="drug_x",
                entity_name="DrugX",
                entity_type="Drug",
                edge_type="INDICATED_FOR",
                strength="strong_for",
                evidence_quality="high",
                conditions_met=True,
                source_layer="direct",
            )
        ]
        q = ClinicalQuery(intent="treatment_selection", concepts=["test"])
        result = engine._build_result(matches, [], q)
        assert result.confidence == "high"

    def test_mixed_layers_keep_high_confidence(self):
        """When results come from both direct and vector, keep 'high'."""
        engine, _ = _make_engine()
        matches = [
            SemanticMatch(
                entity_id="drug_a",
                entity_name="DrugA",
                entity_type="Drug",
                edge_type="INDICATED_FOR",
                strength="strong_for",
                evidence_quality="high",
                conditions_met=True,
                source_layer="direct",
            ),
            SemanticMatch(
                entity_id="drug_b",
                entity_name="DrugB",
                entity_type="Drug",
                edge_type="INDICATED_FOR",
                strength="moderate_for",
                evidence_quality="moderate",
                conditions_met=True,
                source_layer="vector",
                similarity_score=0.8,
            ),
        ]
        q = ClinicalQuery(intent="treatment_selection", concepts=["test"])
        result = engine._build_result(matches, [], q)
        assert result.confidence == "high"

    def test_vector_only_medium_stays_medium(self):
        """If confidence is already 'medium', vector-only doesn't change it."""
        engine, _ = _make_engine()
        matches = [
            SemanticMatch(
                entity_id="drug_x",
                entity_name="DrugX",
                entity_type="Drug",
                edge_type="INDICATED_FOR",
                strength="strong_for",
                evidence_quality="high",
                conditions_met=False,
                source_layer="vector",
                similarity_score=0.85,
            )
        ]
        q = ClinicalQuery(intent="treatment_selection", concepts=["test"])
        result = engine._build_result(matches, [], q)
        assert result.confidence == "medium"

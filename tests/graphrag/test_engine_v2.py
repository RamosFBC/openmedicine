"""Tests for GraphRAG Reasoning Engine v2."""

import json
from unittest.mock import MagicMock, patch

from open_medicine.graphrag.reasoning.engine_v2 import (
    OPS,
    STRENGTH_RANK,
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
        q = ClinicalQuery(intent="treatment_selection", concepts=["Unknown"])
        result = engine.query(q)
        assert result.semantic_matches == []
        conn.execute_read.assert_not_called()

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


class TestQueryInteractions:
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_returns_interactions(self, mock_link):
        linked = MagicMock()
        linked.node_id = "drug_warfarin"
        mock_link.return_value = linked

        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {"drug_id": "drug_aspirin", "drug_name": "Aspirin"}
        ]
        q = ClinicalQuery(intent="interaction", concepts=["Warfarin"])
        result = engine.query(q)
        assert len(result.semantic_matches) == 1
        assert result.semantic_matches[0].edge_type == "INTERACTS_WITH"
        assert result.semantic_matches[0].entity_type == "Drug"


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
        assert match.conditions_met is False
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


class TestEvaluateCondition:
    def test_numeric_comparison(self):
        assert ReasoningEngine._evaluate_condition(
            {"variable": "LVEF", "operator": "<=", "threshold": 40}, {"LVEF": 30}
        ) is True

    def test_missing_variable_returns_none(self):
        assert ReasoningEngine._evaluate_condition(
            {"variable": "LVEF", "operator": "<=", "threshold": 40}, {}
        ) is None

    def test_unknown_operator_returns_none(self):
        assert ReasoningEngine._evaluate_condition(
            {"variable": "LVEF", "operator": "~", "threshold": 40}, {"LVEF": 30}
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
        # Second call: link_entity("Spironolactone", "drug") returns a drug
        member_drug = MagicMock()
        member_drug.node_id = "rxnorm:35827"
        member_drug.node_label = "Drug"
        member_drug.entity_type = "drug"

        mock_link.side_effect = [None, member_drug]
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

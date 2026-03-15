import pytest

from open_medicine.graphrag.graph.queries_v2 import LoaderQueries, ReasoningQueries
from open_medicine.graphrag.graph.schema_v2 import (
    ContraindicatedInProps,
    ContraindicationSeverity,
    DosedForProps,
    EvidenceQuality,
    Guideline,
    IndicatedForProps,
    InteractsWithProps,
    InteractionSeverity,
    MonitoredByProps,
    Recommendation,
    RecommendationStrength,
    RecommendationType,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _assert_valid_cypher(result: tuple[str, dict]) -> tuple[str, dict]:
    """Basic validation that a Cypher statement is well-formed."""
    cypher, params = result
    assert isinstance(cypher, str)
    assert isinstance(params, dict)
    assert len(cypher) > 0
    # Every parameter referenced in params should have a $ prefix in the query
    # (not all params are necessarily used in ON CREATE SET, but all should be referenced)
    for key in params:
        assert f"${key}" in cypher, f"Parameter ${key} not found in query: {cypher}"
    return cypher, params


# ---------------------------------------------------------------------------
# LoaderQueries — Node creators
# ---------------------------------------------------------------------------


class TestLoaderNodeCreators:
    def test_create_guideline(self):
        g = Guideline(
            id="g1", title="Test", doi="10.x/y", year=2024, organization="Org"
        )
        cypher, params = _assert_valid_cypher(LoaderQueries.create_guideline(g))
        assert "MERGE (g:Guideline" in cypher
        assert params["id"] == "g1"

    def test_create_drug(self):
        cypher, params = _assert_valid_cypher(
            LoaderQueries.create_drug(
                "rxnorm:123", "TestDrug", rxnorm_code="123", aliases=["TD"]
            )
        )
        assert "MERGE (d:Drug" in cypher
        assert params["aliases"] == ["TD"]

    def test_create_drug_defaults(self):
        _, params = _assert_valid_cypher(
            LoaderQueries.create_drug("rxnorm:1", "D")
        )
        assert params["aliases"] == []
        assert params["rxnorm"] is None

    def test_create_drug_class(self):
        cypher, params = _assert_valid_cypher(
            LoaderQueries.create_drug_class("atc:C07", "Beta Blocker", atc_code="C07")
        )
        assert "DrugClass" in cypher

    def test_create_disease(self):
        cypher, params = _assert_valid_cypher(
            LoaderQueries.create_disease(
                "snomed:84114007", "Heart Failure", snomed_code="84114007"
            )
        )
        assert "Disease" in cypher

    def test_create_symptom(self):
        cypher, _ = _assert_valid_cypher(
            LoaderQueries.create_symptom("snomed:267036007", "Dyspnea")
        )
        assert "Symptom" in cypher

    def test_create_lab(self):
        cypher, _ = _assert_valid_cypher(
            LoaderQueries.create_lab(
                "loinc:77147-7", "eGFR", loinc_code="77147-7", unit="mL/min/1.73m²"
            )
        )
        assert "Lab" in cypher

    def test_create_procedure(self):
        cypher, _ = _assert_valid_cypher(
            LoaderQueries.create_procedure("snomed:40701008", "Echocardiography")
        )
        assert "Procedure" in cypher

    def test_create_device(self):
        cypher, _ = _assert_valid_cypher(
            LoaderQueries.create_device("snomed:72506001", "ICD")
        )
        assert "Device" in cypher

    def test_create_recommendation(self):
        rec = Recommendation(
            id="rec_001",
            type=RecommendationType.TREATMENT_SELECTION,
            action="Prescribe ARNi",
            action_detail="Recommended for HFrEF",
            strength=RecommendationStrength.STRONG_FOR,
            evidence_quality=EvidenceQuality.HIGH,
            guideline_id="g1",
        )
        cypher, params = _assert_valid_cypher(
            LoaderQueries.create_recommendation(rec)
        )
        assert "Recommendation" in cypher
        assert params["strength"] == "strong_for"
        assert params["eq"] == "high"

    def test_create_evidence_chunk(self):
        cypher, _ = _assert_valid_cypher(
            LoaderQueries.create_evidence_chunk("c1", "Some text", section="Treatment")
        )
        assert "EvidenceChunk" in cypher

    def test_create_publication(self):
        cypher, params = _assert_valid_cypher(
            LoaderQueries.create_publication("10.1056/NEJMoa1409077", title="PARADIGM-HF")
        )
        assert "Publication" in cypher
        assert params["doi"] == "10.1056/NEJMoa1409077"

    def test_create_patient_variable(self):
        cypher, _ = _assert_valid_cypher(
            LoaderQueries.create_patient_variable(
                "pv:lvef", "LVEF", loinc_code="10230-1", unit="%"
            )
        )
        assert "PatientVariable" in cypher

    def test_create_population(self):
        cypher, _ = _assert_valid_cypher(
            LoaderQueries.create_population("pop_001", "HFrEF LVEF<=40%")
        )
        assert "Population" in cypher

    def test_create_temporal_constraint(self):
        cypher, _ = _assert_valid_cypher(
            LoaderQueries.create_temporal_constraint(
                "tc_001", "washout", value=36, unit="hours"
            )
        )
        assert "TemporalConstraint" in cypher

    def test_create_organization(self):
        cypher, _ = _assert_valid_cypher(
            LoaderQueries.create_organization("aha", "American Heart Association")
        )
        assert "Organization" in cypher


# ---------------------------------------------------------------------------
# LoaderQueries — Semantic edge creators (Layer 1)
# ---------------------------------------------------------------------------


class TestLoaderSemanticEdges:
    def test_create_indicated_for(self):
        props = IndicatedForProps(
            strength=RecommendationStrength.STRONG_FOR,
            evidence_quality=EvidenceQuality.HIGH,
        )
        cypher, params = _assert_valid_cypher(
            LoaderQueries.create_indicated_for("rxnorm:123", "Drug", "snomed:456", props)
        )
        assert "INDICATED_FOR" in cypher
        assert "Drug" in cypher
        assert "Disease" in cypher

    def test_indicated_for_drug_class(self):
        props = IndicatedForProps(
            strength=RecommendationStrength.STRONG_FOR,
            evidence_quality=EvidenceQuality.MODERATE,
        )
        cypher, _ = _assert_valid_cypher(
            LoaderQueries.create_indicated_for("atc:C07", "DrugClass", "snomed:456", props)
        )
        assert "DrugClass" in cypher

    def test_create_contraindicated_in(self):
        props = ContraindicatedInProps(
            strength=RecommendationStrength.STRONG_AGAINST,
            severity=ContraindicationSeverity.ABSOLUTE,
        )
        cypher, params = _assert_valid_cypher(
            LoaderQueries.create_contraindicated_in("rxnorm:123", "Drug", "snomed:456", props)
        )
        assert "CONTRAINDICATED_IN" in cypher
        assert params["severity"] == "absolute"

    def test_create_interacts_with(self):
        props = InteractsWithProps(
            severity=InteractionSeverity.MAJOR,
            mechanism="CYP3A4",
        )
        cypher, _ = _assert_valid_cypher(
            LoaderQueries.create_interacts_with("rxnorm:1", "rxnorm:2", props)
        )
        assert "INTERACTS_WITH" in cypher
        assert cypher.count("Drug") == 2  # Both source and target are Drug

    def test_create_dosed_for(self):
        props = DosedForProps(
            starting_dose="2.5 mg BID", target_dose="10 mg BID"
        )
        cypher, _ = _assert_valid_cypher(
            LoaderQueries.create_dosed_for("rxnorm:123", "snomed:456", props)
        )
        assert "DOSED_FOR" in cypher

    def test_create_monitored_by(self):
        props = MonitoredByProps(frequency="weekly")
        cypher, _ = _assert_valid_cypher(
            LoaderQueries.create_monitored_by("rxnorm:123", "loinc:456", props)
        )
        assert "MONITORED_BY" in cypher

    def test_create_member_of(self):
        cypher, _ = _assert_valid_cypher(
            LoaderQueries.create_member_of("rxnorm:123", "atc:C07")
        )
        assert "MEMBER_OF" in cypher

    def test_create_presents_with(self):
        cypher, _ = _assert_valid_cypher(
            LoaderQueries.create_presents_with("snomed:1", "snomed:2", "common")
        )
        assert "PRESENTS_WITH" in cypher

    def test_create_diagnosed_by(self):
        cypher, _ = _assert_valid_cypher(
            LoaderQueries.create_diagnosed_by("snomed:1", "loinc:2", "Lab")
        )
        assert "DIAGNOSED_BY" in cypher

    def test_create_stage_of(self):
        cypher, _ = _assert_valid_cypher(
            LoaderQueries.create_stage_of(
                "snomed:child", "snomed:parent", stage_system="ACC/AHA", stage_value="C"
            )
        )
        assert "STAGE_OF" in cypher


# ---------------------------------------------------------------------------
# LoaderQueries — Evidence edge creators (Layer 2)
# ---------------------------------------------------------------------------


class TestLoaderEvidenceEdges:
    def test_create_recommends(self):
        cypher, _ = _assert_valid_cypher(
            LoaderQueries.create_recommends("rec_001", "rxnorm:123", "Drug", role="primary")
        )
        assert "RECOMMENDS" in cypher

    def test_create_for_condition(self):
        cypher, _ = _assert_valid_cypher(
            LoaderQueries.create_for_condition("rec_001", "snomed:456")
        )
        assert "FOR_CONDITION" in cypher

    def test_create_sourced_from(self):
        cypher, _ = _assert_valid_cypher(
            LoaderQueries.create_sourced_from("rec_001", "chunk_001")
        )
        assert "SOURCED_FROM" in cypher

    def test_create_defined_by(self):
        cypher, _ = _assert_valid_cypher(
            LoaderQueries.create_defined_by("rec_001", "g1")
        )
        assert "DEFINED_BY" in cypher

    def test_create_evaluates(self):
        cypher, _ = _assert_valid_cypher(
            LoaderQueries.create_evaluates("rec_001", "pv:lvef")
        )
        assert "EVALUATES" in cypher

    def test_create_applies_to(self):
        cypher, _ = _assert_valid_cypher(
            LoaderQueries.create_applies_to("rec_001", "pop_001")
        )
        assert "APPLIES_TO" in cypher

    def test_create_timed_by(self):
        cypher, _ = _assert_valid_cypher(
            LoaderQueries.create_timed_by("rec_001", "tc_001")
        )
        assert "TIMED_BY" in cypher

    def test_create_published_by(self):
        cypher, _ = _assert_valid_cypher(
            LoaderQueries.create_published_by("g1", "aha")
        )
        assert "PUBLISHED_BY" in cypher

    def test_create_cited_in(self):
        cypher, _ = _assert_valid_cypher(
            LoaderQueries.create_cited_in("10.1056/NEJMoa1409077", "rec_001")
        )
        assert "CITED_IN" in cypher

    def test_create_measures(self):
        cypher, _ = _assert_valid_cypher(
            LoaderQueries.create_measures("pv:lvef", "loinc:10230-1")
        )
        assert "MEASURES" in cypher


# ---------------------------------------------------------------------------
# LoaderQueries — Cross-guideline edges
# ---------------------------------------------------------------------------


class TestLoaderCrossGuidelineEdges:
    def test_create_conflicts_with(self):
        cypher, _ = _assert_valid_cypher(
            LoaderQueries.create_conflicts_with("rec_a", "rec_b", resolution="newer")
        )
        assert "CONFLICTS_WITH" in cypher

    def test_create_supersedes(self):
        cypher, _ = _assert_valid_cypher(
            LoaderQueries.create_supersedes("rec_new", "rec_old", reason="Updated guideline")
        )
        assert "SUPERSEDES" in cypher


# ---------------------------------------------------------------------------
# LoaderQueries — Delete
# ---------------------------------------------------------------------------


class TestLoaderDelete:
    def test_delete_guideline(self):
        stmts = LoaderQueries.delete_guideline("g1")
        assert len(stmts) == 3
        for cypher, params in stmts:
            assert isinstance(cypher, str)
            assert isinstance(params, dict)


# ---------------------------------------------------------------------------
# ReasoningQueries — Layer 1 (semantic)
# ---------------------------------------------------------------------------


class TestReasoningLayer1:
    def test_find_treatments(self):
        cypher, params = _assert_valid_cypher(
            ReasoningQueries.find_treatments("snomed:84114007")
        )
        assert "INDICATED_FOR" in cypher
        assert params["dis_id"] == "snomed:84114007"

    def test_find_treatments_with_guideline_filter(self):
        cypher, params = _assert_valid_cypher(
            ReasoningQueries.find_treatments("snomed:84114007", guideline_filter="g1")
        )
        assert "gfilter" in params

    def test_find_contraindications(self):
        cypher, _ = _assert_valid_cypher(
            ReasoningQueries.find_contraindications("rxnorm:123", "Drug")
        )
        assert "CONTRAINDICATED_IN" in cypher

    def test_find_interactions(self):
        cypher, _ = _assert_valid_cypher(
            ReasoningQueries.find_interactions("rxnorm:123")
        )
        assert "INTERACTS_WITH" in cypher

    def test_find_dosing(self):
        cypher, _ = _assert_valid_cypher(
            ReasoningQueries.find_dosing("rxnorm:123")
        )
        assert "DOSED_FOR" in cypher

    def test_find_dosing_for_disease(self):
        cypher, params = _assert_valid_cypher(
            ReasoningQueries.find_dosing("rxnorm:123", disease_id="snomed:456")
        )
        assert "dis_id" in params

    def test_find_monitoring(self):
        cypher, _ = _assert_valid_cypher(
            ReasoningQueries.find_monitoring("rxnorm:123")
        )
        assert "MONITORED_BY" in cypher

    def test_find_drug_class_members(self):
        cypher, _ = _assert_valid_cypher(
            ReasoningQueries.find_drug_class_members("atc:C07")
        )
        assert "MEMBER_OF" in cypher

    def test_find_drug_class(self):
        cypher, _ = _assert_valid_cypher(
            ReasoningQueries.find_drug_class("rxnorm:123")
        )
        assert "MEMBER_OF" in cypher


# ---------------------------------------------------------------------------
# ReasoningQueries — Layer 2 (evidence)
# ---------------------------------------------------------------------------


class TestReasoningLayer2:
    def test_get_recommendation_detail(self):
        cypher, _ = _assert_valid_cypher(
            ReasoningQueries.get_recommendation_detail("rec_001")
        )
        assert "SOURCED_FROM" in cypher
        assert "DEFINED_BY" in cypher
        assert "EVALUATES" in cypher

    def test_find_recommendations_for_entity(self):
        cypher, _ = _assert_valid_cypher(
            ReasoningQueries.find_recommendations_for_entity("rxnorm:123", "Drug")
        )
        assert "RECOMMENDS" in cypher

    def test_find_recommendations_with_type_filter(self):
        cypher, params = _assert_valid_cypher(
            ReasoningQueries.find_recommendations_for_entity(
                "rxnorm:123", "Drug", rec_type="dosing"
            )
        )
        assert "rtype" in params

    def test_get_full_recommendation_chain(self):
        cypher, _ = _assert_valid_cypher(
            ReasoningQueries.get_full_recommendation_chain(
                "rxnorm:123", "Drug", "snomed:456"
            )
        )
        assert "RECOMMENDS" in cypher
        assert "FOR_CONDITION" in cypher
        assert "SOURCED_FROM" in cypher


# ---------------------------------------------------------------------------
# ReasoningQueries — Vector search & utilities
# ---------------------------------------------------------------------------


class TestReasoningUtilities:
    def test_vector_search(self):
        embedding = [0.1] * 1024
        cypher, params = _assert_valid_cypher(
            ReasoningQueries.vector_search(embedding, limit=5)
        )
        assert "db.index.vector.queryNodes" in cypher
        assert params["limit"] == 5

    def test_find_conflicts(self):
        cypher, _ = _assert_valid_cypher(
            ReasoningQueries.find_conflicts(["rec_1", "rec_2"])
        )
        assert "CONFLICTS_WITH" in cypher

    def test_get_evidence_chunk(self):
        cypher, _ = _assert_valid_cypher(
            ReasoningQueries.get_evidence_chunk("chunk_001")
        )
        assert "EvidenceChunk" in cypher

    def test_list_guidelines(self):
        cypher, params = _assert_valid_cypher(
            ReasoningQueries.list_guidelines()
        )
        assert "Guideline" in cypher
        assert params == {}

    def test_list_drugs(self):
        cypher, _ = _assert_valid_cypher(ReasoningQueries.list_drugs())
        assert "Drug" in cypher

    def test_list_diseases(self):
        cypher, _ = _assert_valid_cypher(ReasoningQueries.list_diseases())
        assert "Disease" in cypher

    def test_list_drug_classes(self):
        cypher, _ = _assert_valid_cypher(ReasoningQueries.list_drug_classes())
        assert "DrugClass" in cypher
        assert "MEMBER_OF" in cypher


class TestVectorEntitySearch:
    def test_returns_cypher_and_params(self):
        embedding = [0.1] * 10
        cypher, params = ReasoningQueries.vector_entity_search(embedding, rec_type="treatment_selection")
        assert "db.index.vector.queryNodes" in cypher
        assert "RECOMMENDS" in cypher
        assert params["embedding"] == embedding
        assert params["rec_type"] == "treatment_selection"
        assert params["limit"] == 10

    def test_custom_limit(self):
        embedding = [0.1] * 10
        cypher, params = ReasoningQueries.vector_entity_search(embedding, rec_type="dosing", limit=5)
        assert params["limit"] == 5

    def test_no_rec_type_filter(self):
        embedding = [0.1] * 10
        cypher, params = ReasoningQueries.vector_entity_search(embedding)
        assert "rec.type" not in cypher
        assert "rec_type" not in params

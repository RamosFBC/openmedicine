import pytest
from pydantic import ValidationError
from open_medicine.mcp.calculators.rass import calculate_rass, RASSParams


# ---------------------------------------------------------------------------
# Tier 1: Deterministic Unit Tests
# ---------------------------------------------------------------------------


class TestRASSMinimumScore:
    """Test RASS -5 -- unarousable, lowest possible score (maximum sedation)."""

    def test_score_minus5_value(self):
        result = calculate_rass(RASSParams(score=-5))
        assert result.value == -5

    def test_score_minus5_interpretation_contains_unarousable(self):
        result = calculate_rass(RASSParams(score=-5))
        assert "Unarousable" in result.interpretation

    def test_score_minus5_interpretation_contains_no_response(self):
        result = calculate_rass(RASSParams(score=-5))
        assert "No response to voice or physical stimulation" in result.interpretation

    def test_score_minus5_category_sedated(self):
        result = calculate_rass(RASSParams(score=-5))
        assert "Sedated" in result.interpretation


class TestRASSMaximumScore:
    """Test RASS +4 -- combative, highest possible score (maximum agitation)."""

    def test_score_plus4_value(self):
        result = calculate_rass(RASSParams(score=4))
        assert result.value == 4

    def test_score_plus4_interpretation_contains_combative(self):
        result = calculate_rass(RASSParams(score=4))
        assert "Combative" in result.interpretation

    def test_score_plus4_interpretation_contains_violent(self):
        result = calculate_rass(RASSParams(score=4))
        assert "violent" in result.interpretation.lower()

    def test_score_plus4_category_agitated(self):
        result = calculate_rass(RASSParams(score=4))
        assert "Agitated" in result.interpretation

    def test_score_plus4_urgent_intervention(self):
        result = calculate_rass(RASSParams(score=4))
        assert "Urgent" in result.interpretation


class TestRASSAlertAndCalm:
    """Test RASS 0 -- alert and calm, target sedation level."""

    def test_score_0_value(self):
        result = calculate_rass(RASSParams(score=0))
        assert result.value == 0

    def test_score_0_interpretation_contains_alert_and_calm(self):
        result = calculate_rass(RASSParams(score=0))
        assert "Alert and calm" in result.interpretation

    def test_score_0_target_level(self):
        result = calculate_rass(RASSParams(score=0))
        assert "target" in result.interpretation.lower()

    def test_score_0_no_adjustment_needed(self):
        result = calculate_rass(RASSParams(score=0))
        assert "No sedation adjustment needed" in result.interpretation


class TestRASSEachAgitationLevel:
    """Test each agitation level individually (+1 to +3)."""

    def test_score_plus1_value(self):
        result = calculate_rass(RASSParams(score=1))
        assert result.value == 1

    def test_score_plus1_interpretation_contains_restless(self):
        result = calculate_rass(RASSParams(score=1))
        assert "Restless" in result.interpretation

    def test_score_plus1_interpretation_contains_anxious(self):
        result = calculate_rass(RASSParams(score=1))
        assert "Anxious" in result.interpretation or "anxious" in result.interpretation

    def test_score_plus2_value(self):
        result = calculate_rass(RASSParams(score=2))
        assert result.value == 2

    def test_score_plus2_interpretation_contains_agitated(self):
        result = calculate_rass(RASSParams(score=2))
        assert "Agitated" in result.interpretation

    def test_score_plus2_interpretation_contains_non_purposeful(self):
        result = calculate_rass(RASSParams(score=2))
        assert "non-purposeful" in result.interpretation

    def test_score_plus3_value(self):
        result = calculate_rass(RASSParams(score=3))
        assert result.value == 3

    def test_score_plus3_interpretation_contains_very_agitated(self):
        result = calculate_rass(RASSParams(score=3))
        assert "Very agitated" in result.interpretation

    def test_score_plus3_interpretation_contains_aggressive(self):
        result = calculate_rass(RASSParams(score=3))
        assert "aggressive" in result.interpretation.lower()


class TestRASSEachSedationLevel:
    """Test each sedation level individually (-1 to -4)."""

    def test_score_minus1_value(self):
        result = calculate_rass(RASSParams(score=-1))
        assert result.value == -1

    def test_score_minus1_interpretation_contains_drowsy(self):
        result = calculate_rass(RASSParams(score=-1))
        assert "Drowsy" in result.interpretation

    def test_score_minus1_interpretation_contains_sustained_awakening(self):
        result = calculate_rass(RASSParams(score=-1))
        assert "sustained awakening" in result.interpretation

    def test_score_minus1_acceptable_target(self):
        result = calculate_rass(RASSParams(score=-1))
        assert "acceptable" in result.interpretation.lower()

    def test_score_minus2_value(self):
        result = calculate_rass(RASSParams(score=-2))
        assert result.value == -2

    def test_score_minus2_interpretation_contains_light_sedation(self):
        result = calculate_rass(RASSParams(score=-2))
        assert "Light sedation" in result.interpretation

    def test_score_minus2_interpretation_contains_briefly_awakens(self):
        result = calculate_rass(RASSParams(score=-2))
        assert "Briefly awakens" in result.interpretation

    def test_score_minus3_value(self):
        result = calculate_rass(RASSParams(score=-3))
        assert result.value == -3

    def test_score_minus3_interpretation_contains_moderate_sedation(self):
        result = calculate_rass(RASSParams(score=-3))
        assert "Moderate sedation" in result.interpretation

    def test_score_minus3_interpretation_contains_no_eye_contact(self):
        result = calculate_rass(RASSParams(score=-3))
        assert "no eye contact" in result.interpretation

    def test_score_minus4_value(self):
        result = calculate_rass(RASSParams(score=-4))
        assert result.value == -4

    def test_score_minus4_interpretation_contains_deep_sedation(self):
        result = calculate_rass(RASSParams(score=-4))
        assert "Deep sedation" in result.interpretation

    def test_score_minus4_interpretation_contains_physical_stimulation(self):
        result = calculate_rass(RASSParams(score=-4))
        assert "physical stimulation" in result.interpretation


class TestRASSEvidence:
    """Verify Evidence DOI and metadata."""

    def test_evidence_doi(self):
        result = calculate_rass(RASSParams(score=0))
        assert result.evidence.source_doi == "10.1164/rccm.2107138"

    def test_evidence_level(self):
        result = calculate_rass(RASSParams(score=0))
        assert result.evidence.level == "Derivation & Validation Study"

    def test_evidence_description_contains_sessler(self):
        result = calculate_rass(RASSParams(score=0))
        assert "Sessler" in result.evidence.description

    def test_evidence_description_contains_rass(self):
        result = calculate_rass(RASSParams(score=0))
        assert "Richmond Agitation-Sedation Scale" in result.evidence.description


class TestRASSFHIR:
    """Verify FHIR code metadata."""

    def test_fhir_code(self):
        result = calculate_rass(RASSParams(score=0))
        assert result.fhir_code == "LL6536-8"

    def test_fhir_system(self):
        result = calculate_rass(RASSParams(score=0))
        assert result.fhir_system == "http://loinc.org"

    def test_fhir_display(self):
        result = calculate_rass(RASSParams(score=0))
        assert result.fhir_display == "Richmond Agitation Sedation Scale [RASS] Score"


class TestRASSValidation:
    """Test input validation via Pydantic constraints."""

    def test_score_below_minus5_raises_error(self):
        with pytest.raises(ValidationError):
            RASSParams(score=-6)

    def test_score_above_plus4_raises_error(self):
        with pytest.raises(ValidationError):
            RASSParams(score=5)

    def test_score_large_negative_raises_error(self):
        with pytest.raises(ValidationError):
            RASSParams(score=-100)

    def test_score_large_positive_raises_error(self):
        with pytest.raises(ValidationError):
            RASSParams(score=100)


class TestRASSAllLevelsParametrized:
    """Parametrized tests for all valid RASS levels ensuring basic correctness."""

    @pytest.mark.parametrize(
        "score,expected_term",
        [
            (-5, "Unarousable"),
            (-4, "Deep sedation"),
            (-3, "Moderate sedation"),
            (-2, "Light sedation"),
            (-1, "Drowsy"),
            (0, "Alert and calm"),
            (1, "Restless"),
            (2, "Agitated"),
            (3, "Very agitated"),
            (4, "Combative"),
        ],
    )
    def test_level_returns_correct_term(self, score, expected_term):
        result = calculate_rass(RASSParams(score=score))
        assert result.value == score
        assert expected_term in result.interpretation

    @pytest.mark.parametrize("score", list(range(-5, 5)))
    def test_level_interpretation_never_empty(self, score):
        result = calculate_rass(RASSParams(score=score))
        assert len(result.interpretation) > 0

    @pytest.mark.parametrize("score", list(range(-5, 5)))
    def test_level_value_matches_input(self, score):
        result = calculate_rass(RASSParams(score=score))
        assert result.value == score

    @pytest.mark.parametrize("score", list(range(-5, 5)))
    def test_rass_label_in_interpretation(self, score):
        result = calculate_rass(RASSParams(score=score))
        assert "RASS" in result.interpretation

    @pytest.mark.parametrize("score", list(range(-5, 5)))
    def test_evidence_always_populated(self, score):
        result = calculate_rass(RASSParams(score=score))
        assert result.evidence is not None
        assert result.evidence.source_doi != ""
        assert result.evidence.description != ""

    @pytest.mark.parametrize(
        "score,expected_category",
        [
            (-5, "Sedated"),
            (-4, "Sedated"),
            (-3, "Sedated"),
            (-2, "Sedated"),
            (-1, "Sedated"),
            (0, "Alert and calm"),
            (1, "Agitated"),
            (2, "Agitated"),
            (3, "Agitated"),
            (4, "Agitated"),
        ],
    )
    def test_level_returns_correct_category(self, score, expected_category):
        result = calculate_rass(RASSParams(score=score))
        assert expected_category in result.interpretation

    @pytest.mark.parametrize("score", list(range(-5, 5)))
    def test_score_format_in_interpretation(self, score):
        """Verify the score is displayed with +/- sign in interpretation."""
        result = calculate_rass(RASSParams(score=score))
        expected_str = f"{score:+d}"
        assert expected_str in result.interpretation


class TestRASSToFHIR:
    """Test FHIR resource generation."""

    def test_to_fhir_returns_observation(self):
        result = calculate_rass(RASSParams(score=0))
        fhir = result.to_fhir(subject_reference="Patient/123")
        assert fhir["resourceType"] == "Observation"
        assert fhir["status"] == "final"
        assert fhir["subject"]["reference"] == "Patient/123"

    def test_to_fhir_contains_loinc_code(self):
        result = calculate_rass(RASSParams(score=0))
        fhir = result.to_fhir(subject_reference="Patient/123")
        assert fhir["code"]["coding"][0]["code"] == "LL6536-8"
        assert fhir["code"]["coding"][0]["system"] == "http://loinc.org"

    def test_to_fhir_with_encounter(self):
        result = calculate_rass(RASSParams(score=-2))
        fhir = result.to_fhir(
            subject_reference="Patient/456",
            encounter_reference="Encounter/789",
        )
        assert fhir["encounter"]["reference"] == "Encounter/789"

    def test_to_fhir_value_is_score(self):
        result = calculate_rass(RASSParams(score=-3))
        fhir = result.to_fhir(subject_reference="Patient/123")
        assert fhir["valueQuantity"]["value"] == -3


class TestRASSClinicalBoundaries:
    """Test the clinical boundary between sedation, calm, and agitation."""

    def test_boundary_sedated_to_calm(self):
        """RASS -1 is sedated, RASS 0 is calm."""
        sedated = calculate_rass(RASSParams(score=-1))
        calm = calculate_rass(RASSParams(score=0))
        assert "Sedated" in sedated.interpretation
        assert "Alert and calm" in calm.interpretation

    def test_boundary_calm_to_agitated(self):
        """RASS 0 is calm, RASS +1 is agitated."""
        calm = calculate_rass(RASSParams(score=0))
        agitated = calculate_rass(RASSParams(score=1))
        assert "Alert and calm" in calm.interpretation
        assert "Agitated" in agitated.interpretation

    def test_voice_vs_physical_stimulation_boundary(self):
        """RASS -3 responds to voice, RASS -4 only to physical stimulation."""
        minus3 = calculate_rass(RASSParams(score=-3))
        minus4 = calculate_rass(RASSParams(score=-4))
        assert "voice" in minus3.interpretation.lower()
        assert "physical stimulation" in minus4.interpretation.lower()

    def test_deep_sedation_worse_outcomes_warning(self):
        """RASS -4 should warn about worse outcomes from deep sedation."""
        result = calculate_rass(RASSParams(score=-4))
        assert "prolonged" in result.interpretation.lower() or "worse" in result.interpretation.lower()

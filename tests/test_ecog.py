import pytest
from pydantic import ValidationError
from open_medicine.mcp.calculators.ecog import calculate_ecog, ECOGParams


# ---------------------------------------------------------------------------
# Tier 1: Deterministic Unit Tests
# ---------------------------------------------------------------------------


class TestECOGMinimumScore:
    """Test ECOG grade 0 -- fully active, best possible functional status."""

    def test_grade_0_value(self):
        result = calculate_ecog(ECOGParams(performance_status=0))
        assert result.value == 0

    def test_grade_0_interpretation_contains_asymptomatic(self):
        result = calculate_ecog(ECOGParams(performance_status=0))
        assert "Asymptomatic" in result.interpretation

    def test_grade_0_interpretation_contains_fully_active(self):
        result = calculate_ecog(ECOGParams(performance_status=0))
        assert "Fully active" in result.interpretation

    def test_grade_0_eligible_for_all_therapies(self):
        result = calculate_ecog(ECOGParams(performance_status=0))
        assert "Eligible for all standard therapies" in result.interpretation


class TestECOGMaximumScore:
    """Test ECOG grade 5 -- dead, worst possible status."""

    def test_grade_5_value(self):
        result = calculate_ecog(ECOGParams(performance_status=5))
        assert result.value == 5

    def test_grade_5_interpretation_contains_dead(self):
        result = calculate_ecog(ECOGParams(performance_status=5))
        assert "Dead" in result.interpretation

    def test_grade_5_interpretation_contains_deceased(self):
        result = calculate_ecog(ECOGParams(performance_status=5))
        assert "deceased" in result.interpretation


class TestECOGEachGrade:
    """Test each intermediate ECOG grade individually."""

    def test_grade_1_value(self):
        result = calculate_ecog(ECOGParams(performance_status=1))
        assert result.value == 1

    def test_grade_1_interpretation_contains_ambulatory(self):
        result = calculate_ecog(ECOGParams(performance_status=1))
        assert "ambulatory" in result.interpretation.lower()

    def test_grade_1_interpretation_contains_light_sedentary(self):
        result = calculate_ecog(ECOGParams(performance_status=1))
        assert "light or sedentary" in result.interpretation

    def test_grade_1_eligible_for_most_regimens(self):
        result = calculate_ecog(ECOGParams(performance_status=1))
        assert "most chemotherapy regimens" in result.interpretation

    def test_grade_2_value(self):
        result = calculate_ecog(ECOGParams(performance_status=2))
        assert result.value == 2

    def test_grade_2_interpretation_contains_self_care(self):
        result = calculate_ecog(ECOGParams(performance_status=2))
        assert "self-care" in result.interpretation or "self care" in result.interpretation

    def test_grade_2_interpretation_contains_50_percent(self):
        result = calculate_ecog(ECOGParams(performance_status=2))
        assert "50%" in result.interpretation

    def test_grade_2_clinical_trial_note(self):
        result = calculate_ecog(ECOGParams(performance_status=2))
        assert "ECOG 0-2" in result.interpretation

    def test_grade_3_value(self):
        result = calculate_ecog(ECOGParams(performance_status=3))
        assert result.value == 3

    def test_grade_3_interpretation_contains_limited_self_care(self):
        result = calculate_ecog(ECOGParams(performance_status=3))
        assert "limited self-care" in result.interpretation or "limited self care" in result.interpretation

    def test_grade_3_palliative_care_mention(self):
        result = calculate_ecog(ECOGParams(performance_status=3))
        assert "palliative" in result.interpretation.lower()

    def test_grade_4_value(self):
        result = calculate_ecog(ECOGParams(performance_status=4))
        assert result.value == 4

    def test_grade_4_interpretation_contains_completely_disabled(self):
        result = calculate_ecog(ECOGParams(performance_status=4))
        assert "Completely disabled" in result.interpretation

    def test_grade_4_not_recommended_therapy(self):
        result = calculate_ecog(ECOGParams(performance_status=4))
        assert "not recommended" in result.interpretation.lower()


class TestECOGEvidence:
    """Verify Evidence DOI and metadata."""

    def test_evidence_doi(self):
        result = calculate_ecog(ECOGParams(performance_status=0))
        assert result.evidence.source_doi == "10.1097/00000421-198212000-00014"

    def test_evidence_level(self):
        result = calculate_ecog(ECOGParams(performance_status=0))
        assert result.evidence.level == "Validation Study"

    def test_evidence_description_contains_oken(self):
        result = calculate_ecog(ECOGParams(performance_status=0))
        assert "Oken" in result.evidence.description

    def test_evidence_description_contains_ecog(self):
        result = calculate_ecog(ECOGParams(performance_status=0))
        assert "Eastern Cooperative Oncology Group" in result.evidence.description


class TestECOGFHIR:
    """Verify FHIR code metadata."""

    def test_fhir_code(self):
        result = calculate_ecog(ECOGParams(performance_status=0))
        assert result.fhir_code == "89247-1"

    def test_fhir_system(self):
        result = calculate_ecog(ECOGParams(performance_status=0))
        assert result.fhir_system == "http://loinc.org"

    def test_fhir_display(self):
        result = calculate_ecog(ECOGParams(performance_status=0))
        assert result.fhir_display == "ECOG Performance Status score"


class TestECOGValidation:
    """Test input validation via Pydantic constraints."""

    def test_negative_grade_raises_error(self):
        with pytest.raises(ValidationError):
            ECOGParams(performance_status=-1)

    def test_grade_above_5_raises_error(self):
        with pytest.raises(ValidationError):
            ECOGParams(performance_status=6)

    def test_grade_large_value_raises_error(self):
        with pytest.raises(ValidationError):
            ECOGParams(performance_status=100)


class TestECOGAllGradesParametrized:
    """Parametrized tests for all valid grades ensuring basic correctness."""

    @pytest.mark.parametrize(
        "grade,expected_category",
        [
            (0, "Asymptomatic"),
            (1, "Symptomatic, fully ambulatory"),
            (2, "Symptomatic, in bed less than 50% of the day"),
            (3, "Symptomatic, in bed more than 50% of the day"),
            (4, "Bedbound"),
            (5, "Dead"),
        ],
    )
    def test_grade_returns_correct_category(self, grade, expected_category):
        result = calculate_ecog(ECOGParams(performance_status=grade))
        assert result.value == grade
        assert expected_category in result.interpretation

    @pytest.mark.parametrize("grade", [0, 1, 2, 3, 4, 5])
    def test_grade_interpretation_never_empty(self, grade):
        result = calculate_ecog(ECOGParams(performance_status=grade))
        assert len(result.interpretation) > 0

    @pytest.mark.parametrize("grade", [0, 1, 2, 3, 4, 5])
    def test_grade_value_matches_input(self, grade):
        result = calculate_ecog(ECOGParams(performance_status=grade))
        assert result.value == grade

    @pytest.mark.parametrize("grade", [0, 1, 2, 3, 4, 5])
    def test_ecog_label_in_interpretation(self, grade):
        result = calculate_ecog(ECOGParams(performance_status=grade))
        assert "ECOG Performance Status" in result.interpretation

    @pytest.mark.parametrize("grade", [0, 1, 2, 3, 4, 5])
    def test_evidence_always_populated(self, grade):
        result = calculate_ecog(ECOGParams(performance_status=grade))
        assert result.evidence is not None
        assert result.evidence.source_doi != ""
        assert result.evidence.description != ""


class TestECOGToFHIR:
    """Test FHIR resource generation."""

    def test_to_fhir_returns_observation(self):
        result = calculate_ecog(ECOGParams(performance_status=2))
        fhir = result.to_fhir(subject_reference="Patient/123")
        assert fhir["resourceType"] == "Observation"
        assert fhir["status"] == "final"
        assert fhir["subject"]["reference"] == "Patient/123"

    def test_to_fhir_contains_loinc_code(self):
        result = calculate_ecog(ECOGParams(performance_status=2))
        fhir = result.to_fhir(subject_reference="Patient/123")
        assert fhir["code"]["coding"][0]["code"] == "89247-1"
        assert fhir["code"]["coding"][0]["system"] == "http://loinc.org"

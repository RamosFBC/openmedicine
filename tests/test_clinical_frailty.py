import pytest
from open_medicine.mcp.calculators.clinical_frailty import (
    calculate_clinical_frailty,
    ClinicalFrailtyParams,
)


# ---------------------------------------------------------------------------
# Tier 1: Deterministic Unit Tests
# ---------------------------------------------------------------------------


class TestClinicalFrailtyMinMax:
    """Test minimum and maximum score boundaries."""

    def test_minimum_score_very_fit(self):
        """CFS 1 = Very Fit, the lowest (best) possible score."""
        params = ClinicalFrailtyParams(frailty_level=1)
        result = calculate_clinical_frailty(params)
        assert result.value == 1
        assert "Very Fit" in result.interpretation
        assert "Non-frail (Fit)" in result.interpretation
        assert "not frail" in result.interpretation

    def test_maximum_score_terminally_ill(self):
        """CFS 9 = Terminally Ill, the highest (worst) possible score."""
        params = ClinicalFrailtyParams(frailty_level=9)
        result = calculate_clinical_frailty(params)
        assert result.value == 9
        assert "Terminally Ill" in result.interpretation
        assert "life expectancy" in result.interpretation.lower()


class TestClinicalFrailtyEachLevel:
    """Test that each CFS level returns the correct label and category."""

    def test_level_1_very_fit(self):
        params = ClinicalFrailtyParams(frailty_level=1)
        result = calculate_clinical_frailty(params)
        assert result.value == 1
        assert "Very Fit" in result.interpretation
        assert "Non-frail (Fit)" in result.interpretation

    def test_level_2_fit(self):
        params = ClinicalFrailtyParams(frailty_level=2)
        result = calculate_clinical_frailty(params)
        assert result.value == 2
        assert "Fit" in result.interpretation
        assert "Non-frail (Fit)" in result.interpretation

    def test_level_3_managing_well(self):
        params = ClinicalFrailtyParams(frailty_level=3)
        result = calculate_clinical_frailty(params)
        assert result.value == 3
        assert "Managing Well" in result.interpretation
        assert "Non-frail (Fit)" in result.interpretation

    def test_level_4_very_mild_frailty(self):
        params = ClinicalFrailtyParams(frailty_level=4)
        result = calculate_clinical_frailty(params)
        assert result.value == 4
        assert "Living with Very Mild Frailty" in result.interpretation
        assert "Pre-frail" in result.interpretation

    def test_level_5_mild_frailty(self):
        params = ClinicalFrailtyParams(frailty_level=5)
        result = calculate_clinical_frailty(params)
        assert result.value == 5
        assert "Living with Mild Frailty" in result.interpretation
        assert "Mildly Frail" in result.interpretation
        assert "IADL" in result.interpretation

    def test_level_6_moderate_frailty(self):
        params = ClinicalFrailtyParams(frailty_level=6)
        result = calculate_clinical_frailty(params)
        assert result.value == 6
        assert "Living with Moderate Frailty" in result.interpretation
        assert "Moderately Frail" in result.interpretation

    def test_level_7_severe_frailty(self):
        params = ClinicalFrailtyParams(frailty_level=7)
        result = calculate_clinical_frailty(params)
        assert result.value == 7
        assert "Living with Severe Frailty" in result.interpretation
        assert "Severely Frail" in result.interpretation
        assert "dependent" in result.interpretation.lower()

    def test_level_8_very_severe_frailty(self):
        params = ClinicalFrailtyParams(frailty_level=8)
        result = calculate_clinical_frailty(params)
        assert result.value == 8
        assert "Living with Very Severe Frailty" in result.interpretation
        assert "Very Severely Frail" in result.interpretation
        assert "palliative" in result.interpretation.lower()

    def test_level_9_terminally_ill(self):
        params = ClinicalFrailtyParams(frailty_level=9)
        result = calculate_clinical_frailty(params)
        assert result.value == 9
        assert "Terminally Ill" in result.interpretation
        assert "end of life" in result.interpretation.lower()


class TestClinicalFrailtyCategoryBoundaries:
    """Test boundaries between frailty categories."""

    def test_boundary_nonfrail_to_prefrail(self):
        """Boundary: CFS 3 (Non-frail) -> CFS 4 (Pre-frail)."""
        result_3 = calculate_clinical_frailty(ClinicalFrailtyParams(frailty_level=3))
        result_4 = calculate_clinical_frailty(ClinicalFrailtyParams(frailty_level=4))
        assert "Non-frail (Fit)" in result_3.interpretation
        assert "Pre-frail" in result_4.interpretation

    def test_boundary_prefrail_to_mild(self):
        """Boundary: CFS 4 (Pre-frail) -> CFS 5 (Mildly Frail)."""
        result_4 = calculate_clinical_frailty(ClinicalFrailtyParams(frailty_level=4))
        result_5 = calculate_clinical_frailty(ClinicalFrailtyParams(frailty_level=5))
        assert "Pre-frail" in result_4.interpretation
        assert "Mildly Frail" in result_5.interpretation

    def test_boundary_mild_to_moderate(self):
        """Boundary: CFS 5 (Mildly Frail) -> CFS 6 (Moderately Frail)."""
        result_5 = calculate_clinical_frailty(ClinicalFrailtyParams(frailty_level=5))
        result_6 = calculate_clinical_frailty(ClinicalFrailtyParams(frailty_level=6))
        assert "Mildly Frail" in result_5.interpretation
        assert "Moderately Frail" in result_6.interpretation

    def test_boundary_moderate_to_severe(self):
        """Boundary: CFS 6 (Moderately Frail) -> CFS 7 (Severely Frail)."""
        result_6 = calculate_clinical_frailty(ClinicalFrailtyParams(frailty_level=6))
        result_7 = calculate_clinical_frailty(ClinicalFrailtyParams(frailty_level=7))
        assert "Moderately Frail" in result_6.interpretation
        assert "Severely Frail" in result_7.interpretation

    def test_boundary_severe_to_very_severe(self):
        """Boundary: CFS 7 (Severely Frail) -> CFS 8 (Very Severely Frail)."""
        result_7 = calculate_clinical_frailty(ClinicalFrailtyParams(frailty_level=7))
        result_8 = calculate_clinical_frailty(ClinicalFrailtyParams(frailty_level=8))
        assert "Severely Frail" in result_7.interpretation
        assert "Very Severely Frail" in result_8.interpretation

    def test_boundary_very_severe_to_terminal(self):
        """Boundary: CFS 8 (Very Severely Frail) -> CFS 9 (Terminally Ill)."""
        result_8 = calculate_clinical_frailty(ClinicalFrailtyParams(frailty_level=8))
        result_9 = calculate_clinical_frailty(ClinicalFrailtyParams(frailty_level=9))
        assert "Very Severely Frail" in result_8.interpretation
        assert "Terminally Ill" in result_9.interpretation


class TestClinicalFrailtyEvidence:
    """Verify evidence and FHIR metadata."""

    def test_evidence_doi(self):
        """Verify DOI matches Rockwood et al. CMAJ 2005."""
        params = ClinicalFrailtyParams(frailty_level=5)
        result = calculate_clinical_frailty(params)
        assert result.evidence.source_doi == "10.1503/cmaj.050051"

    def test_evidence_level(self):
        """Verify evidence level is appropriate for derivation/validation study."""
        params = ClinicalFrailtyParams(frailty_level=5)
        result = calculate_clinical_frailty(params)
        assert result.evidence.level == "Derivation & Validation Study"

    def test_evidence_description(self):
        """Verify evidence description mentions Rockwood and CMAJ."""
        params = ClinicalFrailtyParams(frailty_level=5)
        result = calculate_clinical_frailty(params)
        assert "Rockwood" in result.evidence.description
        assert "CMAJ" in result.evidence.description

    def test_fhir_code(self):
        """Verify FHIR code is present and system is LOINC."""
        params = ClinicalFrailtyParams(frailty_level=1)
        result = calculate_clinical_frailty(params)
        assert result.fhir_code == "89013-7"
        assert result.fhir_system == "http://loinc.org"
        assert result.fhir_display == "Clinical Frailty Scale score"


class TestClinicalFrailtyInputValidation:
    """Test Pydantic validation for out-of-range inputs."""

    def test_below_minimum_raises(self):
        """CFS level 0 is invalid and should raise a validation error."""
        with pytest.raises(Exception):
            ClinicalFrailtyParams(frailty_level=0)

    def test_above_maximum_raises(self):
        """CFS level 10 is invalid and should raise a validation error."""
        with pytest.raises(Exception):
            ClinicalFrailtyParams(frailty_level=10)

    def test_negative_raises(self):
        """Negative CFS level is invalid."""
        with pytest.raises(Exception):
            ClinicalFrailtyParams(frailty_level=-1)


class TestClinicalFrailtyInterpretationContent:
    """Verify interpretation strings contain the expected clinical content."""

    def test_interpretation_contains_score(self):
        """Interpretation should always include the numeric score."""
        for level in range(1, 10):
            params = ClinicalFrailtyParams(frailty_level=level)
            result = calculate_clinical_frailty(params)
            assert f"Clinical Frailty Scale is {level}" in result.interpretation

    def test_interpretation_contains_label(self):
        """Interpretation should always include the level label."""
        expected_labels = {
            1: "Very Fit",
            2: "Fit",
            3: "Managing Well",
            4: "Living with Very Mild Frailty",
            5: "Living with Mild Frailty",
            6: "Living with Moderate Frailty",
            7: "Living with Severe Frailty",
            8: "Living with Very Severe Frailty",
            9: "Terminally Ill",
        }
        for level, label in expected_labels.items():
            params = ClinicalFrailtyParams(frailty_level=level)
            result = calculate_clinical_frailty(params)
            assert label in result.interpretation

    def test_interpretation_contains_category(self):
        """Interpretation should always include the frailty category."""
        for level in range(1, 10):
            params = ClinicalFrailtyParams(frailty_level=level)
            result = calculate_clinical_frailty(params)
            assert "Category:" in result.interpretation

    def test_all_levels_return_nonempty_interpretation(self):
        """Every valid CFS level must produce a non-empty interpretation."""
        for level in range(1, 10):
            params = ClinicalFrailtyParams(frailty_level=level)
            result = calculate_clinical_frailty(params)
            assert len(result.interpretation) > 0

    def test_clinical_frailty_monotonic_values(self):
        """Score value should equal the input level for all valid inputs."""
        for level in range(1, 10):
            params = ClinicalFrailtyParams(frailty_level=level)
            result = calculate_clinical_frailty(params)
            assert result.value == level


class TestClinicalFrailtyFHIRExport:
    """Test FHIR export functionality."""

    def test_to_fhir_structure(self):
        """Verify to_fhir() produces valid FHIR Observation structure."""
        params = ClinicalFrailtyParams(frailty_level=6)
        result = calculate_clinical_frailty(params)
        fhir = result.to_fhir(subject_reference="Patient/123")
        assert fhir["resourceType"] == "Observation"
        assert fhir["status"] == "final"
        assert fhir["valueInteger"] == 6
        assert fhir["code"]["coding"][0]["code"] == "89013-7"
        assert fhir["code"]["coding"][0]["system"] == "http://loinc.org"

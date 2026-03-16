"""
Tests for the Modified Duke Criteria for Infective Endocarditis calculator.

Reference: Li JS et al. Clin Infect Dis. 2000;30(4):633-638.
DOI: 10.1086/313753

Classification rules:
  Definite (Pathological): pathological vegetation/lesions present
  Definite (Clinical): 2 major, OR 1 major + 3 minor, OR 5 minor
  Possible: 1 major + 1-2 minor, OR 3 minor
  Rejected: does not meet criteria for possible or definite IE
"""

import pytest
from hypothesis import given, settings, strategies as st

from open_medicine.mcp.calculators.duke_criteria import (
    calculate_duke_criteria,
    DukeCriteriaParams,
)


# =============================================================================
# Tier 1: Deterministic Unit Tests
# =============================================================================


class TestRejectedClassification:
    """Cases that should be classified as 'Rejected'."""

    def test_all_criteria_absent(self):
        """No criteria met at all -> Rejected."""
        params = DukeCriteriaParams()
        result = calculate_duke_criteria(params)
        assert result.value == "Rejected"
        assert "Rejected" in result.interpretation

    def test_one_minor_only(self):
        """Only 1 minor criterion -> Rejected (need >= 3 minor for Possible)."""
        params = DukeCriteriaParams(fever=True)
        result = calculate_duke_criteria(params)
        assert result.value == "Rejected"

    def test_two_minor_only(self):
        """Only 2 minor criteria -> Rejected (need >= 3 minor for Possible)."""
        params = DukeCriteriaParams(fever=True, predisposing_condition=True)
        result = calculate_duke_criteria(params)
        assert result.value == "Rejected"

    def test_one_major_zero_minor(self):
        """1 major + 0 minor -> Rejected (need at least 1 minor with 1 major)."""
        params = DukeCriteriaParams(blood_culture_typical_organisms=True)
        result = calculate_duke_criteria(params)
        assert result.value == "Rejected"


class TestPossibleClassification:
    """Cases that should be classified as 'Possible' IE."""

    def test_one_major_one_minor(self):
        """1 major + 1 minor -> Possible."""
        params = DukeCriteriaParams(
            blood_culture_typical_organisms=True,
            fever=True,
        )
        result = calculate_duke_criteria(params)
        assert result.value == "Possible"
        assert "Possible" in result.interpretation

    def test_one_major_two_minor(self):
        """1 major + 2 minor -> Possible (not definite, need 3 minor for that)."""
        params = DukeCriteriaParams(
            echocardiogram_positive=True,
            fever=True,
            predisposing_condition=True,
        )
        result = calculate_duke_criteria(params)
        assert result.value == "Possible"

    def test_three_minor_only(self):
        """0 major + 3 minor -> Possible."""
        params = DukeCriteriaParams(
            fever=True,
            predisposing_condition=True,
            vascular_phenomena=True,
        )
        result = calculate_duke_criteria(params)
        assert result.value == "Possible"

    def test_four_minor_only(self):
        """0 major + 4 minor -> Possible (need 5 for Definite)."""
        params = DukeCriteriaParams(
            fever=True,
            predisposing_condition=True,
            vascular_phenomena=True,
            immunologic_phenomena=True,
        )
        result = calculate_duke_criteria(params)
        assert result.value == "Possible"

    def test_one_major_endocardial_one_minor(self):
        """1 major (endocardial) + 1 minor -> Possible."""
        params = DukeCriteriaParams(
            new_valvular_regurgitation=True,
            fever=True,
        )
        result = calculate_duke_criteria(params)
        assert result.value == "Possible"


class TestDefiniteClassification:
    """Cases that should be classified as 'Definite' IE."""

    def test_two_major_criteria(self):
        """2 major criteria -> Definite."""
        params = DukeCriteriaParams(
            blood_culture_typical_organisms=True,
            echocardiogram_positive=True,
        )
        result = calculate_duke_criteria(params)
        assert result.value == "Definite"
        assert "Definite" in result.interpretation

    def test_one_major_three_minor(self):
        """1 major + 3 minor -> Definite."""
        params = DukeCriteriaParams(
            blood_culture_typical_organisms=True,
            fever=True,
            predisposing_condition=True,
            vascular_phenomena=True,
        )
        result = calculate_duke_criteria(params)
        assert result.value == "Definite"

    def test_five_minor_criteria(self):
        """5 minor criteria -> Definite."""
        params = DukeCriteriaParams(
            predisposing_condition=True,
            fever=True,
            vascular_phenomena=True,
            immunologic_phenomena=True,
            microbiological_evidence_minor=True,
        )
        result = calculate_duke_criteria(params)
        assert result.value == "Definite"

    def test_pathological_vegetation(self):
        """Pathological vegetation alone -> Definite (pathological)."""
        params = DukeCriteriaParams(pathological_vegetation=True)
        result = calculate_duke_criteria(params)
        assert result.value == "Definite"
        assert "pathological" in result.interpretation.lower()

    def test_pathological_lesions(self):
        """Pathological lesions alone -> Definite (pathological)."""
        params = DukeCriteriaParams(pathological_lesions=True)
        result = calculate_duke_criteria(params)
        assert result.value == "Definite"
        assert "pathological" in result.interpretation.lower()

    def test_all_criteria_present(self):
        """All criteria met -> Definite (pathological takes precedence)."""
        params = DukeCriteriaParams(
            pathological_vegetation=True,
            pathological_lesions=True,
            blood_culture_typical_organisms=True,
            blood_culture_persistently_positive=True,
            coxiella_burnetii=True,
            echocardiogram_positive=True,
            new_valvular_regurgitation=True,
            predisposing_condition=True,
            fever=True,
            vascular_phenomena=True,
            immunologic_phenomena=True,
            microbiological_evidence_minor=True,
        )
        result = calculate_duke_criteria(params)
        assert result.value == "Definite"
        assert "pathological" in result.interpretation.lower()

    def test_two_major_via_different_blood_culture_and_echo(self):
        """Persistently positive blood cultures + new regurgitation -> Definite (2 major)."""
        params = DukeCriteriaParams(
            blood_culture_persistently_positive=True,
            new_valvular_regurgitation=True,
        )
        result = calculate_duke_criteria(params)
        assert result.value == "Definite"

    def test_coxiella_plus_echo_positive(self):
        """Coxiella burnetii (major) + echo positive (major) -> Definite."""
        params = DukeCriteriaParams(
            coxiella_burnetii=True,
            echocardiogram_positive=True,
        )
        result = calculate_duke_criteria(params)
        assert result.value == "Definite"

    def test_one_major_four_minor(self):
        """1 major + 4 minor -> Definite (exceeds 1 major + 3 minor threshold)."""
        params = DukeCriteriaParams(
            echocardiogram_positive=True,
            predisposing_condition=True,
            fever=True,
            vascular_phenomena=True,
            immunologic_phenomena=True,
        )
        result = calculate_duke_criteria(params)
        assert result.value == "Definite"

    def test_one_major_five_minor(self):
        """1 major + 5 minor -> Definite."""
        params = DukeCriteriaParams(
            blood_culture_typical_organisms=True,
            predisposing_condition=True,
            fever=True,
            vascular_phenomena=True,
            immunologic_phenomena=True,
            microbiological_evidence_minor=True,
        )
        result = calculate_duke_criteria(params)
        assert result.value == "Definite"

    def test_two_major_plus_minor(self):
        """2 major + minor criteria -> still Definite."""
        params = DukeCriteriaParams(
            blood_culture_typical_organisms=True,
            echocardiogram_positive=True,
            fever=True,
            vascular_phenomena=True,
        )
        result = calculate_duke_criteria(params)
        assert result.value == "Definite"


class TestMajorCriteriaGrouping:
    """Test that blood culture sub-criteria are correctly grouped as one major criterion."""

    def test_multiple_blood_culture_subcriteria_count_as_one_major(self):
        """All 3 blood culture sub-criteria still count as only 1 major criterion."""
        params = DukeCriteriaParams(
            blood_culture_typical_organisms=True,
            blood_culture_persistently_positive=True,
            coxiella_burnetii=True,
            # No endocardial involvement -> only 1 major
            fever=True,  # 1 minor
        )
        result = calculate_duke_criteria(params)
        # 1 major + 1 minor = Possible, NOT Definite
        assert result.value == "Possible"

    def test_echo_and_regurgitation_count_as_one_major(self):
        """Both echo sub-criteria count as only 1 major criterion."""
        params = DukeCriteriaParams(
            echocardiogram_positive=True,
            new_valvular_regurgitation=True,
            # No blood culture -> only 1 major
            fever=True,  # 1 minor
        )
        result = calculate_duke_criteria(params)
        # 1 major + 1 minor = Possible, NOT Definite
        assert result.value == "Possible"


class TestEdgeCases:
    """Edge cases and boundary tests."""

    def test_pathological_overrides_clinical(self):
        """Pathological criteria make it Definite even with no clinical criteria."""
        params = DukeCriteriaParams(pathological_vegetation=True)
        result = calculate_duke_criteria(params)
        assert result.value == "Definite"

    def test_boundary_possible_to_definite_minor_count(self):
        """Boundary: 0 major + 4 minor = Possible, 0 major + 5 minor = Definite."""
        # 4 minor -> Possible
        params_4 = DukeCriteriaParams(
            predisposing_condition=True,
            fever=True,
            vascular_phenomena=True,
            immunologic_phenomena=True,
        )
        result_4 = calculate_duke_criteria(params_4)
        assert result_4.value == "Possible"

        # 5 minor -> Definite
        params_5 = DukeCriteriaParams(
            predisposing_condition=True,
            fever=True,
            vascular_phenomena=True,
            immunologic_phenomena=True,
            microbiological_evidence_minor=True,
        )
        result_5 = calculate_duke_criteria(params_5)
        assert result_5.value == "Definite"

    def test_boundary_possible_to_definite_major_minor(self):
        """Boundary: 1 major + 2 minor = Possible, 1 major + 3 minor = Definite."""
        # 1 major + 2 minor -> Possible
        params_2 = DukeCriteriaParams(
            blood_culture_typical_organisms=True,
            fever=True,
            predisposing_condition=True,
        )
        result_2 = calculate_duke_criteria(params_2)
        assert result_2.value == "Possible"

        # 1 major + 3 minor -> Definite
        params_3 = DukeCriteriaParams(
            blood_culture_typical_organisms=True,
            fever=True,
            predisposing_condition=True,
            vascular_phenomena=True,
        )
        result_3 = calculate_duke_criteria(params_3)
        assert result_3.value == "Definite"

    def test_boundary_rejected_to_possible_minor(self):
        """Boundary: 0 major + 2 minor = Rejected, 0 major + 3 minor = Possible."""
        # 2 minor -> Rejected
        params_2 = DukeCriteriaParams(
            fever=True,
            predisposing_condition=True,
        )
        result_2 = calculate_duke_criteria(params_2)
        assert result_2.value == "Rejected"

        # 3 minor -> Possible
        params_3 = DukeCriteriaParams(
            fever=True,
            predisposing_condition=True,
            vascular_phenomena=True,
        )
        result_3 = calculate_duke_criteria(params_3)
        assert result_3.value == "Possible"

    def test_boundary_rejected_to_possible_major_minor(self):
        """Boundary: 1 major + 0 minor = Rejected, 1 major + 1 minor = Possible."""
        # 1 major + 0 minor -> Rejected
        params_0 = DukeCriteriaParams(
            echocardiogram_positive=True,
        )
        result_0 = calculate_duke_criteria(params_0)
        assert result_0.value == "Rejected"

        # 1 major + 1 minor -> Possible
        params_1 = DukeCriteriaParams(
            echocardiogram_positive=True,
            fever=True,
        )
        result_1 = calculate_duke_criteria(params_1)
        assert result_1.value == "Possible"


class TestClinicalScenarios:
    """Realistic clinical scenario tests."""

    def test_classic_ie_presentation(self):
        """Classic IE: positive blood cultures (S. aureus) + echo vegetation + fever + emboli."""
        params = DukeCriteriaParams(
            blood_culture_typical_organisms=True,
            echocardiogram_positive=True,
            fever=True,
            vascular_phenomena=True,
        )
        result = calculate_duke_criteria(params)
        assert result.value == "Definite"

    def test_ivdu_with_fever_and_emboli(self):
        """IV drug user with fever, emboli, and atypical blood cultures."""
        params = DukeCriteriaParams(
            predisposing_condition=True,   # IVDU
            fever=True,
            vascular_phenomena=True,       # septic pulmonary infarcts
            microbiological_evidence_minor=True,  # atypical organism
        )
        result = calculate_duke_criteria(params)
        # 0 major + 4 minor = Possible
        assert result.value == "Possible"

    def test_prosthetic_valve_full_workup(self):
        """Prosthetic valve patient with S. aureus bacteremia and echo vegetation."""
        params = DukeCriteriaParams(
            blood_culture_typical_organisms=True,
            echocardiogram_positive=True,
            predisposing_condition=True,
            fever=True,
        )
        result = calculate_duke_criteria(params)
        assert result.value == "Definite"

    def test_q_fever_endocarditis(self):
        """Q fever with positive serology and echo findings."""
        params = DukeCriteriaParams(
            coxiella_burnetii=True,
            echocardiogram_positive=True,
        )
        result = calculate_duke_criteria(params)
        assert result.value == "Definite"

    def test_culture_negative_with_clinical_features(self):
        """Culture-negative but strong clinical presentation."""
        params = DukeCriteriaParams(
            echocardiogram_positive=True,   # 1 major
            predisposing_condition=True,     # minor
            fever=True,                      # minor
            immunologic_phenomena=True,      # minor (Osler nodes)
        )
        result = calculate_duke_criteria(params)
        # 1 major + 3 minor = Definite
        assert result.value == "Definite"


class TestEvidenceAndFHIR:
    """Test evidence and FHIR metadata."""

    def test_evidence_doi(self):
        """Verify DOI is correct for Li JS et al. 2000."""
        params = DukeCriteriaParams()
        result = calculate_duke_criteria(params)
        assert result.evidence.source_doi == "10.1086/313753"

    def test_evidence_level(self):
        """Verify evidence level."""
        params = DukeCriteriaParams()
        result = calculate_duke_criteria(params)
        assert result.evidence.level == "Validation Study"

    def test_evidence_description(self):
        """Verify evidence description references Li JS et al."""
        params = DukeCriteriaParams()
        result = calculate_duke_criteria(params)
        assert "Li JS" in result.evidence.description
        assert "2000" in result.evidence.description

    def test_fhir_code(self):
        """Verify FHIR code is set."""
        params = DukeCriteriaParams()
        result = calculate_duke_criteria(params)
        assert result.fhir_code is None
        assert result.fhir_system is None
        assert result.fhir_display == "Modified Duke Criteria classification"

    def test_interpretation_always_present(self):
        """Interpretation is never empty for any classification."""
        for classification_params in [
            DukeCriteriaParams(),  # Rejected
            DukeCriteriaParams(blood_culture_typical_organisms=True, fever=True),  # Possible
            DukeCriteriaParams(blood_culture_typical_organisms=True, echocardiogram_positive=True),  # Definite
            DukeCriteriaParams(pathological_vegetation=True),  # Definite (pathological)
        ]:
            result = calculate_duke_criteria(classification_params)
            assert result.interpretation
            assert len(result.interpretation) > 0


# =============================================================================
# Tier 2: Property-Based Fuzz Tests
# =============================================================================


@pytest.mark.slow
@given(
    pathological_vegetation=st.booleans(),
    pathological_lesions=st.booleans(),
    blood_culture_typical_organisms=st.booleans(),
    blood_culture_persistently_positive=st.booleans(),
    coxiella_burnetii=st.booleans(),
    echocardiogram_positive=st.booleans(),
    new_valvular_regurgitation=st.booleans(),
    predisposing_condition=st.booleans(),
    fever=st.booleans(),
    vascular_phenomena=st.booleans(),
    immunologic_phenomena=st.booleans(),
    microbiological_evidence_minor=st.booleans(),
)
@settings(max_examples=500)
def test_duke_criteria_fuzz_valid_classification(
    pathological_vegetation,
    pathological_lesions,
    blood_culture_typical_organisms,
    blood_culture_persistently_positive,
    coxiella_burnetii,
    echocardiogram_positive,
    new_valvular_regurgitation,
    predisposing_condition,
    fever,
    vascular_phenomena,
    immunologic_phenomena,
    microbiological_evidence_minor,
):
    """Output is always a valid classification for any combination of boolean inputs."""
    params = DukeCriteriaParams(
        pathological_vegetation=pathological_vegetation,
        pathological_lesions=pathological_lesions,
        blood_culture_typical_organisms=blood_culture_typical_organisms,
        blood_culture_persistently_positive=blood_culture_persistently_positive,
        coxiella_burnetii=coxiella_burnetii,
        echocardiogram_positive=echocardiogram_positive,
        new_valvular_regurgitation=new_valvular_regurgitation,
        predisposing_condition=predisposing_condition,
        fever=fever,
        vascular_phenomena=vascular_phenomena,
        immunologic_phenomena=immunologic_phenomena,
        microbiological_evidence_minor=microbiological_evidence_minor,
    )
    result = calculate_duke_criteria(params)

    # Classification must be one of the three valid categories
    assert result.value in ("Definite", "Possible", "Rejected")

    # Interpretation is never empty
    assert result.interpretation
    assert len(result.interpretation) > 0

    # Evidence is always populated
    assert result.evidence.source_doi == "10.1086/313753"
    assert result.evidence.description

    # FHIR display always present (fhir_code/fhir_system intentionally None —
    # no LOINC code exists for Duke Criteria classification)
    assert result.fhir_display


@pytest.mark.slow
@given(
    pathological_vegetation=st.booleans(),
    pathological_lesions=st.booleans(),
    blood_culture_typical_organisms=st.booleans(),
    blood_culture_persistently_positive=st.booleans(),
    coxiella_burnetii=st.booleans(),
    echocardiogram_positive=st.booleans(),
    new_valvular_regurgitation=st.booleans(),
    predisposing_condition=st.booleans(),
    fever=st.booleans(),
    vascular_phenomena=st.booleans(),
    immunologic_phenomena=st.booleans(),
    microbiological_evidence_minor=st.booleans(),
)
@settings(max_examples=500)
def test_duke_criteria_fuzz_pathological_always_definite(
    pathological_vegetation,
    pathological_lesions,
    blood_culture_typical_organisms,
    blood_culture_persistently_positive,
    coxiella_burnetii,
    echocardiogram_positive,
    new_valvular_regurgitation,
    predisposing_condition,
    fever,
    vascular_phenomena,
    immunologic_phenomena,
    microbiological_evidence_minor,
):
    """If any pathological criterion is True, classification must be Definite."""
    if not (pathological_vegetation or pathological_lesions):
        return  # Skip cases without pathological criteria

    params = DukeCriteriaParams(
        pathological_vegetation=pathological_vegetation,
        pathological_lesions=pathological_lesions,
        blood_culture_typical_organisms=blood_culture_typical_organisms,
        blood_culture_persistently_positive=blood_culture_persistently_positive,
        coxiella_burnetii=coxiella_burnetii,
        echocardiogram_positive=echocardiogram_positive,
        new_valvular_regurgitation=new_valvular_regurgitation,
        predisposing_condition=predisposing_condition,
        fever=fever,
        vascular_phenomena=vascular_phenomena,
        immunologic_phenomena=immunologic_phenomena,
        microbiological_evidence_minor=microbiological_evidence_minor,
    )
    result = calculate_duke_criteria(params)
    assert result.value == "Definite"


@pytest.mark.slow
@given(
    pathological_vegetation=st.booleans(),
    pathological_lesions=st.booleans(),
    blood_culture_typical_organisms=st.booleans(),
    blood_culture_persistently_positive=st.booleans(),
    coxiella_burnetii=st.booleans(),
    echocardiogram_positive=st.booleans(),
    new_valvular_regurgitation=st.booleans(),
    predisposing_condition=st.booleans(),
    fever=st.booleans(),
    vascular_phenomena=st.booleans(),
    immunologic_phenomena=st.booleans(),
    microbiological_evidence_minor=st.booleans(),
)
@settings(max_examples=500)
def test_duke_criteria_fuzz_classification_interpretation_consistency(
    pathological_vegetation,
    pathological_lesions,
    blood_culture_typical_organisms,
    blood_culture_persistently_positive,
    coxiella_burnetii,
    echocardiogram_positive,
    new_valvular_regurgitation,
    predisposing_condition,
    fever,
    vascular_phenomena,
    immunologic_phenomena,
    microbiological_evidence_minor,
):
    """The classification in value must always appear in the interpretation string."""
    params = DukeCriteriaParams(
        pathological_vegetation=pathological_vegetation,
        pathological_lesions=pathological_lesions,
        blood_culture_typical_organisms=blood_culture_typical_organisms,
        blood_culture_persistently_positive=blood_culture_persistently_positive,
        coxiella_burnetii=coxiella_burnetii,
        echocardiogram_positive=echocardiogram_positive,
        new_valvular_regurgitation=new_valvular_regurgitation,
        predisposing_condition=predisposing_condition,
        fever=fever,
        vascular_phenomena=vascular_phenomena,
        immunologic_phenomena=immunologic_phenomena,
        microbiological_evidence_minor=microbiological_evidence_minor,
    )
    result = calculate_duke_criteria(params)

    # The classification value must appear in the interpretation
    assert result.value in result.interpretation

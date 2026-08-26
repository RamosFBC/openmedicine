import pytest
from hypothesis import given, strategies as st
from open_medicine.mcp.calculators.rcri import calculate_rcri, RCRIParams


# ---- Tier 1: Deterministic Unit Tests ----


def test_rcri_minimum_score():
    """Test lowest possible score: 0 predictors (Class I)."""
    params = RCRIParams(
        high_risk_surgery=False,
        history_of_ischemic_heart_disease=False,
        history_of_congestive_heart_failure=False,
        history_of_cerebrovascular_disease=False,
        preoperative_insulin_treatment=False,
        preoperative_creatinine_above_2=False,
    )
    result = calculate_rcri(params)
    assert result.value == 0
    assert "Class I" in result.interpretation
    assert "0.4%" in result.interpretation
    assert "Low risk" in result.interpretation


def test_rcri_score_1_class_ii():
    """Test score of 1 (Class II) with only high-risk surgery."""
    params = RCRIParams(
        high_risk_surgery=True,
        history_of_ischemic_heart_disease=False,
        history_of_congestive_heart_failure=False,
        history_of_cerebrovascular_disease=False,
        preoperative_insulin_treatment=False,
        preoperative_creatinine_above_2=False,
    )
    result = calculate_rcri(params)
    assert result.value == 1
    assert "Class II" in result.interpretation
    assert "0.9%" in result.interpretation
    assert "Low risk" in result.interpretation


def test_rcri_score_1_ischemic_heart_disease():
    """Test score of 1 with only ischemic heart disease history."""
    params = RCRIParams(
        high_risk_surgery=False,
        history_of_ischemic_heart_disease=True,
        history_of_congestive_heart_failure=False,
        history_of_cerebrovascular_disease=False,
        preoperative_insulin_treatment=False,
        preoperative_creatinine_above_2=False,
    )
    result = calculate_rcri(params)
    assert result.value == 1
    assert "Class II" in result.interpretation


def test_rcri_score_1_chf():
    """Test score of 1 with only congestive heart failure history."""
    params = RCRIParams(
        high_risk_surgery=False,
        history_of_ischemic_heart_disease=False,
        history_of_congestive_heart_failure=True,
        history_of_cerebrovascular_disease=False,
        preoperative_insulin_treatment=False,
        preoperative_creatinine_above_2=False,
    )
    result = calculate_rcri(params)
    assert result.value == 1
    assert "Class II" in result.interpretation


def test_rcri_score_1_cerebrovascular():
    """Test score of 1 with only cerebrovascular disease history."""
    params = RCRIParams(
        high_risk_surgery=False,
        history_of_ischemic_heart_disease=False,
        history_of_congestive_heart_failure=False,
        history_of_cerebrovascular_disease=True,
        preoperative_insulin_treatment=False,
        preoperative_creatinine_above_2=False,
    )
    result = calculate_rcri(params)
    assert result.value == 1
    assert "Class II" in result.interpretation


def test_rcri_score_1_insulin():
    """Test score of 1 with only insulin treatment."""
    params = RCRIParams(
        high_risk_surgery=False,
        history_of_ischemic_heart_disease=False,
        history_of_congestive_heart_failure=False,
        history_of_cerebrovascular_disease=False,
        preoperative_insulin_treatment=True,
        preoperative_creatinine_above_2=False,
    )
    result = calculate_rcri(params)
    assert result.value == 1
    assert "Class II" in result.interpretation


def test_rcri_score_1_creatinine():
    """Test score of 1 with only elevated creatinine."""
    params = RCRIParams(
        high_risk_surgery=False,
        history_of_ischemic_heart_disease=False,
        history_of_congestive_heart_failure=False,
        history_of_cerebrovascular_disease=False,
        preoperative_insulin_treatment=False,
        preoperative_creatinine_above_2=True,
    )
    result = calculate_rcri(params)
    assert result.value == 1
    assert "Class II" in result.interpretation


def test_rcri_score_2_class_iii():
    """Test score of 2 (Class III) - elevated risk threshold."""
    params = RCRIParams(
        high_risk_surgery=True,
        history_of_ischemic_heart_disease=True,
        history_of_congestive_heart_failure=False,
        history_of_cerebrovascular_disease=False,
        preoperative_insulin_treatment=False,
        preoperative_creatinine_above_2=False,
    )
    result = calculate_rcri(params)
    assert result.value == 2
    assert "Class III" in result.interpretation
    assert "6.6%" in result.interpretation
    assert "Elevated risk" in result.interpretation


def test_rcri_score_3_class_iv():
    """Test score of 3 (Class IV) - high risk threshold."""
    params = RCRIParams(
        high_risk_surgery=True,
        history_of_ischemic_heart_disease=True,
        history_of_congestive_heart_failure=True,
        history_of_cerebrovascular_disease=False,
        preoperative_insulin_treatment=False,
        preoperative_creatinine_above_2=False,
    )
    result = calculate_rcri(params)
    assert result.value == 3
    assert "Class IV" in result.interpretation
    assert "11%" in result.interpretation
    assert "Elevated risk" in result.interpretation


def test_rcri_score_4():
    """Test score of 4 (still Class IV)."""
    params = RCRIParams(
        high_risk_surgery=True,
        history_of_ischemic_heart_disease=True,
        history_of_congestive_heart_failure=True,
        history_of_cerebrovascular_disease=True,
        preoperative_insulin_treatment=False,
        preoperative_creatinine_above_2=False,
    )
    result = calculate_rcri(params)
    assert result.value == 4
    assert "Class IV" in result.interpretation


def test_rcri_score_5():
    """Test score of 5 (still Class IV)."""
    params = RCRIParams(
        high_risk_surgery=True,
        history_of_ischemic_heart_disease=True,
        history_of_congestive_heart_failure=True,
        history_of_cerebrovascular_disease=True,
        preoperative_insulin_treatment=True,
        preoperative_creatinine_above_2=False,
    )
    result = calculate_rcri(params)
    assert result.value == 5
    assert "Class IV" in result.interpretation


def test_rcri_maximum_score():
    """Test highest possible score: all 6 predictors present (Class IV)."""
    params = RCRIParams(
        high_risk_surgery=True,
        history_of_ischemic_heart_disease=True,
        history_of_congestive_heart_failure=True,
        history_of_cerebrovascular_disease=True,
        preoperative_insulin_treatment=True,
        preoperative_creatinine_above_2=True,
    )
    result = calculate_rcri(params)
    assert result.value == 6
    assert "Class IV" in result.interpretation
    assert "11%" in result.interpretation


def test_rcri_defaults_all_false():
    """Test that all boolean fields default to False, producing score 0."""
    params = RCRIParams()
    result = calculate_rcri(params)
    assert result.value == 0
    assert "Class I" in result.interpretation


def test_rcri_evidence_doi():
    """Verify DOI matches the original Lee 1999 Circulation paper."""
    params = RCRIParams()
    result = calculate_rcri(params)
    assert result.evidence.source_doi == "10.1161/01.CIR.100.10.1043"
    assert result.evidence.level == "Derivation & Validation Study"
    assert "Lee TH" in result.evidence.description


def test_rcri_fhir_code():
    """Verify FHIR code is None (no valid LOINC exists for RCRI)."""
    params = RCRIParams()
    result = calculate_rcri(params)
    assert result.fhir_code is None
    assert result.fhir_system is None
    assert result.fhir_display == "Revised Cardiac Risk Index"


def test_rcri_boundary_class_i_to_ii():
    """Test the boundary between Class I (score 0) and Class II (score 1)."""
    # Score 0 -> Class I
    params_0 = RCRIParams()
    result_0 = calculate_rcri(params_0)
    assert result_0.value == 0
    assert "Class I" in result_0.interpretation

    # Score 1 -> Class II
    params_1 = RCRIParams(high_risk_surgery=True)
    result_1 = calculate_rcri(params_1)
    assert result_1.value == 1
    assert "Class II" in result_1.interpretation


def test_rcri_boundary_class_ii_to_iii():
    """Test the boundary between Class II (score 1) and Class III (score 2)."""
    # Score 1 -> Class II
    params_1 = RCRIParams(high_risk_surgery=True)
    result_1 = calculate_rcri(params_1)
    assert result_1.value == 1
    assert "Class II" in result_1.interpretation

    # Score 2 -> Class III
    params_2 = RCRIParams(
        high_risk_surgery=True,
        history_of_ischemic_heart_disease=True,
    )
    result_2 = calculate_rcri(params_2)
    assert result_2.value == 2
    assert "Class III" in result_2.interpretation


def test_rcri_boundary_class_iii_to_iv():
    """Test the boundary between Class III (score 2) and Class IV (score >=3)."""
    # Score 2 -> Class III
    params_2 = RCRIParams(
        high_risk_surgery=True,
        history_of_ischemic_heart_disease=True,
    )
    result_2 = calculate_rcri(params_2)
    assert result_2.value == 2
    assert "Class III" in result_2.interpretation

    # Score 3 -> Class IV
    params_3 = RCRIParams(
        high_risk_surgery=True,
        history_of_ischemic_heart_disease=True,
        history_of_congestive_heart_failure=True,
    )
    result_3 = calculate_rcri(params_3)
    assert result_3.value == 3
    assert "Class IV" in result_3.interpretation


def test_rcri_interpretation_includes_score():
    """Verify each risk stratum interpretation includes the numeric score."""
    for i in range(7):
        # Build params with the first i criteria set to True
        criteria = [False] * 6
        for j in range(i):
            criteria[j] = True
        params = RCRIParams(
            high_risk_surgery=criteria[0],
            history_of_ischemic_heart_disease=criteria[1],
            history_of_congestive_heart_failure=criteria[2],
            history_of_cerebrovascular_disease=criteria[3],
            preoperative_insulin_treatment=criteria[4],
            preoperative_creatinine_above_2=criteria[5],
        )
        result = calculate_rcri(params)
        assert result.value == i
        assert f"RCRI score is {i}" in result.interpretation


def test_rcri_to_fhir():
    """Verify FHIR export fails closed with no code."""
    params = RCRIParams(high_risk_surgery=True, history_of_ischemic_heart_disease=True)
    result = calculate_rcri(params)
    with pytest.raises(ValueError, match="FHIR code and system are required"):
        result.to_fhir(subject_reference="Patient/123")


# ---- Tier 2: Property-Based Fuzz Tests ----
# RCRI is a scoring calculator (not equation), but we add a bounds test
# for completeness, testing all 64 possible boolean combinations.


@pytest.mark.slow
@given(
    st.builds(
        RCRIParams,
        high_risk_surgery=st.booleans(),
        history_of_ischemic_heart_disease=st.booleans(),
        history_of_congestive_heart_failure=st.booleans(),
        history_of_cerebrovascular_disease=st.booleans(),
        preoperative_insulin_treatment=st.booleans(),
        preoperative_creatinine_above_2=st.booleans(),
    )
)
def test_rcri_fuzz_bounds(params):
    """Property-based test: RCRI must always return 0-6 across all boolean permutations."""
    result = calculate_rcri(params)
    assert result.value is not None
    assert 0 <= result.value <= 6
    assert isinstance(result.interpretation, str)
    assert len(result.interpretation) > 0
    assert "RCRI score is" in result.interpretation
    assert result.evidence.source_doi == "10.1161/01.CIR.100.10.1043"
    assert result.fhir_code is None

import pytest
from hypothesis import given, strategies as st
from open_medicine.mcp.calculators.stop_bang import calculate_stop_bang, STOPBangParams


# ---------------------------------------------------------------------------
# Tier 1: Deterministic Unit Tests
# ---------------------------------------------------------------------------


def test_stop_bang_minimum_score():
    """Test lowest possible score with all criteria absent (score 0, low risk)."""
    params = STOPBangParams(
        snoring=False,
        tired=False,
        observed_apnea=False,
        high_blood_pressure=False,
        bmi_over_35=False,
        age_over_50=False,
        neck_circumference_over_40=False,
        male_gender=False,
    )
    result = calculate_stop_bang(params)
    assert result.value == 0
    assert "Low risk" in result.interpretation
    assert "STOP-Bang score is 0" in result.interpretation


def test_stop_bang_maximum_score():
    """Test highest possible score with all criteria present (score 8, high risk)."""
    params = STOPBangParams(
        snoring=True,
        tired=True,
        observed_apnea=True,
        high_blood_pressure=True,
        bmi_over_35=True,
        age_over_50=True,
        neck_circumference_over_40=True,
        male_gender=True,
    )
    result = calculate_stop_bang(params)
    assert result.value == 8
    assert "High risk" in result.interpretation
    assert "STOP-Bang score is 8" in result.interpretation
    assert "polysomnography" in result.interpretation.lower()


def test_stop_bang_low_risk_boundary():
    """Score of 2 is the upper boundary of low risk."""
    params = STOPBangParams(
        snoring=True,
        tired=True,
        observed_apnea=False,
        high_blood_pressure=False,
        bmi_over_35=False,
        age_over_50=False,
        neck_circumference_over_40=False,
        male_gender=False,
    )
    result = calculate_stop_bang(params)
    assert result.value == 2
    assert "Low risk" in result.interpretation


def test_stop_bang_intermediate_risk_lower_boundary():
    """Score of 3 is the lower boundary of intermediate risk."""
    params = STOPBangParams(
        snoring=True,
        tired=True,
        observed_apnea=True,
        high_blood_pressure=False,
        bmi_over_35=False,
        age_over_50=False,
        neck_circumference_over_40=False,
        male_gender=False,
    )
    result = calculate_stop_bang(params)
    assert result.value == 3
    assert "Intermediate risk" in result.interpretation
    assert "93%" in result.interpretation


def test_stop_bang_intermediate_risk_upper_boundary():
    """Score of 4 is the upper boundary of intermediate risk."""
    params = STOPBangParams(
        snoring=True,
        tired=True,
        observed_apnea=True,
        high_blood_pressure=True,
        bmi_over_35=False,
        age_over_50=False,
        neck_circumference_over_40=False,
        male_gender=False,
    )
    result = calculate_stop_bang(params)
    assert result.value == 4
    assert "Intermediate risk" in result.interpretation


def test_stop_bang_high_risk_lower_boundary():
    """Score of 5 is the lower boundary of high risk."""
    params = STOPBangParams(
        snoring=True,
        tired=True,
        observed_apnea=True,
        high_blood_pressure=True,
        bmi_over_35=True,
        age_over_50=False,
        neck_circumference_over_40=False,
        male_gender=False,
    )
    result = calculate_stop_bang(params)
    assert result.value == 5
    assert "High risk" in result.interpretation
    assert "polysomnography" in result.interpretation.lower()


def test_stop_bang_single_criterion_snoring():
    """Only snoring positive yields score 1."""
    params = STOPBangParams(snoring=True)
    result = calculate_stop_bang(params)
    assert result.value == 1
    assert "Low risk" in result.interpretation


def test_stop_bang_single_criterion_male():
    """Only male gender positive yields score 1."""
    params = STOPBangParams(male_gender=True)
    result = calculate_stop_bang(params)
    assert result.value == 1
    assert "Low risk" in result.interpretation


def test_stop_bang_bang_only():
    """Only BANG criteria (BMI, Age, Neck, Gender) positive = score 4 (intermediate)."""
    params = STOPBangParams(
        snoring=False,
        tired=False,
        observed_apnea=False,
        high_blood_pressure=False,
        bmi_over_35=True,
        age_over_50=True,
        neck_circumference_over_40=True,
        male_gender=True,
    )
    result = calculate_stop_bang(params)
    assert result.value == 4
    assert "Intermediate risk" in result.interpretation


def test_stop_bang_stop_only():
    """Only STOP criteria (Snoring, Tired, Observed, Pressure) positive = score 4 (intermediate)."""
    params = STOPBangParams(
        snoring=True,
        tired=True,
        observed_apnea=True,
        high_blood_pressure=True,
        bmi_over_35=False,
        age_over_50=False,
        neck_circumference_over_40=False,
        male_gender=False,
    )
    result = calculate_stop_bang(params)
    assert result.value == 4
    assert "Intermediate risk" in result.interpretation


def test_stop_bang_defaults_all_false():
    """With no arguments provided, all defaults are False -> score 0."""
    params = STOPBangParams()
    result = calculate_stop_bang(params)
    assert result.value == 0
    assert "Low risk" in result.interpretation


def test_stop_bang_evidence_doi():
    """Verify DOI matches the original STOP questionnaire paper."""
    params = STOPBangParams()
    result = calculate_stop_bang(params)
    assert result.evidence.source_doi == "10.1097/ALN.0b013e31816d83e4"
    assert result.evidence.level == "Derivation & Validation Study"


def test_stop_bang_fhir_code():
    """Verify FHIR code and system are populated."""
    params = STOPBangParams()
    result = calculate_stop_bang(params)
    assert result.fhir_code == "28633-6"
    assert result.fhir_system == "http://loinc.org"
    assert result.fhir_display is not None
    assert "STOP-Bang" in result.fhir_display


def test_stop_bang_typical_male_patient_high_risk():
    """Typical high-risk male surgical patient: obese, older, snores, hypertensive, thick neck."""
    params = STOPBangParams(
        snoring=True,
        tired=True,
        observed_apnea=True,
        high_blood_pressure=True,
        bmi_over_35=True,
        age_over_50=True,
        neck_circumference_over_40=True,
        male_gender=True,
    )
    result = calculate_stop_bang(params)
    assert result.value == 8
    assert "High risk" in result.interpretation


def test_stop_bang_typical_low_risk_female():
    """Young, thin female with no symptoms: low risk."""
    params = STOPBangParams(
        snoring=False,
        tired=False,
        observed_apnea=False,
        high_blood_pressure=False,
        bmi_over_35=False,
        age_over_50=False,
        neck_circumference_over_40=False,
        male_gender=False,
    )
    result = calculate_stop_bang(params)
    assert result.value == 0
    assert "Low risk" in result.interpretation


def test_stop_bang_score_6():
    """Score 6 is high risk."""
    params = STOPBangParams(
        snoring=True,
        tired=True,
        observed_apnea=True,
        high_blood_pressure=True,
        bmi_over_35=True,
        age_over_50=True,
        neck_circumference_over_40=False,
        male_gender=False,
    )
    result = calculate_stop_bang(params)
    assert result.value == 6
    assert "High risk" in result.interpretation


def test_stop_bang_score_7():
    """Score 7 is high risk."""
    params = STOPBangParams(
        snoring=True,
        tired=True,
        observed_apnea=True,
        high_blood_pressure=True,
        bmi_over_35=True,
        age_over_50=True,
        neck_circumference_over_40=True,
        male_gender=False,
    )
    result = calculate_stop_bang(params)
    assert result.value == 7
    assert "High risk" in result.interpretation


# ---------------------------------------------------------------------------
# Tier 2: Property-Based Fuzz Tests
# ---------------------------------------------------------------------------


@pytest.mark.slow
@given(
    st.builds(
        STOPBangParams,
        snoring=st.booleans(),
        tired=st.booleans(),
        observed_apnea=st.booleans(),
        high_blood_pressure=st.booleans(),
        bmi_over_35=st.booleans(),
        age_over_50=st.booleans(),
        neck_circumference_over_40=st.booleans(),
        male_gender=st.booleans(),
    )
)
def test_stop_bang_fuzz_bounds(params):
    """Property-based test: STOP-Bang must always return 0-8 across all 256 boolean permutations."""
    result = calculate_stop_bang(params)
    assert result.value is not None
    assert isinstance(result.value, int)
    assert 0 <= result.value <= 8
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "STOP-Bang score is" in result.interpretation
    assert result.evidence.source_doi == "10.1097/ALN.0b013e31816d83e4"


@pytest.mark.slow
@given(
    st.builds(
        STOPBangParams,
        snoring=st.booleans(),
        tired=st.booleans(),
        observed_apnea=st.booleans(),
        high_blood_pressure=st.booleans(),
        bmi_over_35=st.booleans(),
        age_over_50=st.booleans(),
        neck_circumference_over_40=st.booleans(),
        male_gender=st.booleans(),
    )
)
def test_stop_bang_fuzz_risk_categories(params):
    """Property-based test: risk category must match the score range."""
    result = calculate_stop_bang(params)
    score = result.value
    if score <= 2:
        assert "Low risk" in result.interpretation
    elif score <= 4:
        assert "Intermediate risk" in result.interpretation
    else:
        assert "High risk" in result.interpretation

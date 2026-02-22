import pytest
from open_medicine.mcp.calculators.ascvd import calculate_ascvd, ASCVDParams

def test_ascvd_unsupported_age():
    params = ASCVDParams(
        is_male=True,
        is_black=False,
        smoker=False,
        hypertensive=False,
        diabetic=False,
        age=30, # under 40
        systolic_blood_pressure=120,
        total_cholesterol=200,
        hdl_cholesterol=50
    )
    result = calculate_ascvd(params)
    assert result.value is None
    assert "only validated for ages 40 through 79" in result.interpretation

def test_ascvd_white_female_low_risk():
    params = ASCVDParams(
        is_male=False,
        is_black=False,
        smoker=False,
        hypertensive=False,
        diabetic=False,
        age=55,
        systolic_blood_pressure=120,
        total_cholesterol=213,
        hdl_cholesterol=50
    )
    # Using the equations, a healthy 55yo white female should have very low risk (~2.1%)
    result = calculate_ascvd(params)
    assert result.value is not None
    assert result.value < 5.0
    assert "Low Risk" in result.interpretation

def test_ascvd_white_male_high_risk():
    params = ASCVDParams(
        is_male=True,
        is_black=False,
        smoker=True, # Smoker
        hypertensive=True, # Treated hypertension
        diabetic=True, # Diabetic
        age=65,
        systolic_blood_pressure=150,
        total_cholesterol=250,
        hdl_cholesterol=40
    )
    result = calculate_ascvd(params)
    assert result.value is not None
    assert result.value >= 20.0
    assert "High Risk" in result.interpretation

def test_ascvd_aa_female_intermediate_risk():
    params = ASCVDParams(
        is_male=False,
        is_black=True,
        smoker=False,
        hypertensive=True, # Treated hypertension
        diabetic=False,
        age=60,
        systolic_blood_pressure=140,
        total_cholesterol=200,
        hdl_cholesterol=45
    )
    result = calculate_ascvd(params)
    assert result.value is not None
    # ASCVD AA Female calculation usually places this profile in intermediate range
    assert 7.5 <= result.value < 20.0
    assert "Intermediate Risk" in result.interpretation

def test_ascvd_aa_male_borderline_risk():
    params = ASCVDParams(
        is_male=True,
        is_black=True,
        smoker=False,
        hypertensive=False,
        diabetic=False,
        age=55,
        systolic_blood_pressure=130,
        total_cholesterol=200,
        hdl_cholesterol=50
    )
    result = calculate_ascvd(params)
    assert result.value is not None
    assert 5.0 <= result.value < 10.0 # likely fits borderline or low intermediate

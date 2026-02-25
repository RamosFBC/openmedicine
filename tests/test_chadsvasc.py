import pytest
from open_medicine.mcp.calculators.chadsvasc import calculate_chadsvasc, CHADSVAScParams

def test_chadsvasc_zero_score_male():
    params = CHADSVAScParams(
        female_sex=False,
        age=50,
        congestive_heart_failure=False,
        hypertension=False,
        diabetes=False,
        stroke_tia_thromboembolism=False,
        vascular_disease=False
    )
    result = calculate_chadsvasc(params)
    assert result.value == 0
    assert "low stroke risk" in result.interpretation
    assert "Oral anticoagulation is generally not recommended" in result.interpretation

def test_chadsvasc_one_score_female():
    params = CHADSVAScParams(
        female_sex=True,
        age=50,
        congestive_heart_failure=False,
        hypertension=False,
        diabetes=False,
        stroke_tia_thromboembolism=False,
        vascular_disease=False
    )
    # 1 point from female sex alone
    result = calculate_chadsvasc(params)
    assert result.value == 1
    assert "low stroke risk" in result.interpretation
    assert "Oral anticoagulation is generally not recommended" in result.interpretation

def test_chadsvasc_moderate_risk_male():
    params = CHADSVAScParams(
        female_sex=False,
        age=65, # 1 point
        congestive_heart_failure=False,
        hypertension=False,
        diabetes=False,
        stroke_tia_thromboembolism=False,
        vascular_disease=False
    )
    result = calculate_chadsvasc(params)
    assert result.value == 1
    assert "moderate stroke risk" in result.interpretation

def test_chadsvasc_moderate_risk_female():
    params = CHADSVAScParams(
        female_sex=True, # 1 point
        age=50,
        congestive_heart_failure=False,
        hypertension=True, # 1 point
        diabetes=False,
        stroke_tia_thromboembolism=False,
        vascular_disease=False
    )
    result = calculate_chadsvasc(params)
    assert result.value == 2
    assert "moderate stroke risk" in result.interpretation

def test_chadsvasc_high_risk_male():
    params = CHADSVAScParams(
        female_sex=False,
        age=75, # 2 points
        congestive_heart_failure=False,
        hypertension=False,
        diabetes=False,
        stroke_tia_thromboembolism=False,
        vascular_disease=False
    )
    result = calculate_chadsvasc(params)
    assert result.value == 2
    assert "high stroke risk" in result.interpretation
    assert "Oral anticoagulation is recommended" in result.interpretation

def test_chadsvasc_high_risk_female():
    params = CHADSVAScParams(
        female_sex=True, # 1 point
        age=75, # 2 points
        congestive_heart_failure=False,
        hypertension=False,
        diabetes=False,
        stroke_tia_thromboembolism=False,
        vascular_disease=False
    )
    result = calculate_chadsvasc(params)
    assert result.value == 3
    assert "high stroke risk" in result.interpretation
    assert "Oral anticoagulation is recommended" in result.interpretation

def test_chadsvasc_max_score():
    params = CHADSVAScParams(
        female_sex=True, # 1
        age=80, # 2
        congestive_heart_failure=True, # 1
        hypertension=True, # 1
        diabetes=True, # 1
        stroke_tia_thromboembolism=True, # 2
        vascular_disease=True # 1
    )
    result = calculate_chadsvasc(params)
    assert result.value == 9
    assert result.evidence.source_doi == "10.1378/chest.09-1584"

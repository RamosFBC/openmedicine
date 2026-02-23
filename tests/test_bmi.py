import pytest
from hypothesis import given, strategies as st, settings
from open_medicine.mcp.calculators.bmi import calculate_bmi, BMIParams


def test_normal_bmi():
    # 70kg, 175cm → 70/(1.75²) = 22.86 → 22.9
    params = BMIParams(weight_kg=70, height_cm=175)
    result = calculate_bmi(params)
    assert result.value == 22.9
    assert "Normal" in result.interpretation


def test_underweight():
    params = BMIParams(weight_kg=45, height_cm=175)
    result = calculate_bmi(params)
    assert result.value < 18.5
    assert "Underweight" in result.interpretation


def test_overweight():
    params = BMIParams(weight_kg=85, height_cm=175)
    result = calculate_bmi(params)
    assert 25 <= result.value < 30
    assert "Overweight" in result.interpretation


def test_obesity_class_i():
    params = BMIParams(weight_kg=100, height_cm=175)
    result = calculate_bmi(params)
    assert 30 <= result.value < 35
    assert "Obesity class I" in result.interpretation


def test_obesity_class_ii():
    params = BMIParams(weight_kg=115, height_cm=175)
    result = calculate_bmi(params)
    assert 35 <= result.value < 40
    assert "Obesity class II" in result.interpretation


def test_obesity_class_iii():
    params = BMIParams(weight_kg=130, height_cm=175)
    result = calculate_bmi(params)
    assert result.value >= 40
    assert "Obesity class III" in result.interpretation


def test_fhir_code():
    result = calculate_bmi(BMIParams(weight_kg=70, height_cm=175))
    assert result.fhir_code == "39156-5"
    assert result.fhir_system == "http://loinc.org"


def test_invalid_height():
    result = calculate_bmi(BMIParams(weight_kg=70, height_cm=0))
    assert result.value is None


@given(
    weight=st.floats(min_value=20, max_value=300),
    height=st.floats(min_value=50, max_value=250),
)
@settings(max_examples=200)
def test_fuzz(weight, height):
    result = calculate_bmi(BMIParams(weight_kg=weight, height_cm=height))
    assert result.value is not None
    assert result.value > 0
    assert result.interpretation

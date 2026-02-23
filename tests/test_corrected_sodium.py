import pytest
from hypothesis import given, strategies as st, settings
from open_medicine.mcp.calculators.corrected_sodium import calculate_corrected_sodium, CorrectedSodiumParams


def test_normal_glucose():
    # Glucose=100 → correction=0 → corrected=140
    params = CorrectedSodiumParams(sodium=140, glucose=100)
    result = calculate_corrected_sodium(params)
    assert result.value == 140.0


def test_moderate_hyperglycemia():
    # Na=130, Glucose=400 → correction = 1.6*(300/100) = 4.8 → 134.8
    params = CorrectedSodiumParams(sodium=130, glucose=400)
    result = calculate_corrected_sodium(params)
    assert result.value == 134.8


def test_severe_hyperglycemia_shows_hillier():
    # Glucose=600 → Katz: 1.6*5=8, Hillier: 2.4*5=12
    params = CorrectedSodiumParams(sodium=125, glucose=600)
    result = calculate_corrected_sodium(params)
    assert result.value == 133.0  # 125 + 8
    assert "Hillier" in result.interpretation


def test_true_hypernatremia():
    params = CorrectedSodiumParams(sodium=145, glucose=500)
    result = calculate_corrected_sodium(params)
    assert result.value > 145
    assert "elevated" in result.interpretation or "hypernatremia" in result.interpretation


def test_true_hyponatremia():
    params = CorrectedSodiumParams(sodium=120, glucose=200)
    result = calculate_corrected_sodium(params)
    # 120 + 1.6*1 = 121.6
    assert result.value < 135
    assert "low" in result.interpretation or "hyponatremia" in result.interpretation


def test_evidence_doi():
    result = calculate_corrected_sodium(CorrectedSodiumParams(sodium=140, glucose=100))
    assert result.evidence.source_doi == "10.1056/NEJM197304052881404"


def test_fhir_code():
    result = calculate_corrected_sodium(CorrectedSodiumParams(sodium=140, glucose=100))
    assert result.fhir_code == "2951-2"
    assert result.fhir_system == "http://loinc.org"


@given(
    sodium=st.floats(min_value=100, max_value=180),
    glucose=st.floats(min_value=50, max_value=1500),
)
@settings(max_examples=200)
def test_fuzz(sodium, glucose):
    result = calculate_corrected_sodium(CorrectedSodiumParams(sodium=sodium, glucose=glucose))
    assert result.value is not None
    assert result.interpretation

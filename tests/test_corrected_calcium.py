import pytest
from hypothesis import given, strategies as st, settings
from open_medicine.mcp.calculators.corrected_calcium import calculate_corrected_calcium, CorrectedCalciumParams


def test_normal_albumin():
    # Albumin=4.0 → correction=0 → corrected=9.5
    params = CorrectedCalciumParams(calcium=9.5, albumin=4.0)
    result = calculate_corrected_calcium(params)
    assert result.value == 9.5
    assert "Normal" in result.interpretation


def test_low_albumin():
    # Ca=8.0, Alb=2.0 → corrected = 8.0 + 0.8*2 = 9.6
    params = CorrectedCalciumParams(calcium=8.0, albumin=2.0)
    result = calculate_corrected_calcium(params)
    assert result.value == 9.6
    assert "Normal" in result.interpretation


def test_hypercalcemia():
    # Ca=11.0, Alb=4.0 → corrected = 11.0
    params = CorrectedCalciumParams(calcium=11.0, albumin=4.0)
    result = calculate_corrected_calcium(params)
    assert result.value == 11.0
    assert "Hypercalcemia" in result.interpretation


def test_hypocalcemia():
    # Ca=7.0, Alb=4.0 → corrected = 7.0
    params = CorrectedCalciumParams(calcium=7.0, albumin=4.0)
    result = calculate_corrected_calcium(params)
    assert result.value == 7.0
    assert "Hypocalcemia" in result.interpretation


def test_evidence_doi():
    result = calculate_corrected_calcium(CorrectedCalciumParams(calcium=9.0, albumin=4.0))
    assert result.evidence.source_doi == "10.1136/bmj.4.5893.643"


def test_fhir_code():
    result = calculate_corrected_calcium(CorrectedCalciumParams(calcium=9.0, albumin=4.0))
    assert result.fhir_code == "29265-6"
    assert result.fhir_system == "http://loinc.org"


@pytest.mark.slow
@given(
    calcium=st.floats(min_value=4.0, max_value=16.0),
    albumin=st.floats(min_value=1.0, max_value=6.0),
)
@settings(max_examples=200)
def test_fuzz(calcium, albumin):
    result = calculate_corrected_calcium(CorrectedCalciumParams(calcium=calcium, albumin=albumin))
    assert result.value is not None
    assert result.interpretation

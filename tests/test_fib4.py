import math
import pytest
from hypothesis import given, strategies as st, settings
from open_medicine.mcp.calculators.fib4 import calculate_fib4, FIB4Params


def test_fib4_low_risk():
    """Young patient with normal labs → low FIB-4."""
    params = FIB4Params(age=40, ast=25.0, alt=30.0, platelets=250.0)
    res = calculate_fib4(params)
    assert res.value < 1.30
    assert "Low risk" in res.interpretation


def test_fib4_high_risk():
    """Older patient with abnormal labs → high FIB-4."""
    params = FIB4Params(age=60, ast=120.0, alt=40.0, platelets=80.0)
    res = calculate_fib4(params)
    assert res.value > 2.67
    assert "High risk" in res.interpretation


def test_fib4_indeterminate():
    """Values producing indeterminate range."""
    params = FIB4Params(age=50, ast=50.0, alt=40.0, platelets=200.0)
    res = calculate_fib4(params)
    assert 1.30 <= res.value <= 2.67
    assert "Indeterminate" in res.interpretation


def test_fib4_known_calculation():
    """Manual calculation: (50 × 80) / (150 × √40) = 4000 / (150 × 6.3246) = 4.22"""
    params = FIB4Params(age=50, ast=80.0, alt=40.0, platelets=150.0)
    res = calculate_fib4(params)
    expected = (50 * 80.0) / (150.0 * math.sqrt(40.0))
    assert abs(res.value - round(expected, 2)) < 0.01


def test_fib4_age_outside_validation():
    """Age outside 35-65 should still calculate but warn."""
    params = FIB4Params(age=70, ast=50.0, alt=30.0, platelets=200.0)
    res = calculate_fib4(params)
    assert res.value is not None
    assert "caution" in res.interpretation


def test_fib4_zero_alt_returns_none():
    params = FIB4Params(age=50, ast=50.0, alt=0.0, platelets=200.0)
    res = calculate_fib4(params)
    assert res.value is None


def test_fib4_zero_platelets_returns_none():
    params = FIB4Params(age=50, ast=50.0, alt=30.0, platelets=0.0)
    res = calculate_fib4(params)
    assert res.value is None


def test_fib4_evidence_doi():
    params = FIB4Params(age=50, ast=30.0, alt=25.0, platelets=200.0)
    res = calculate_fib4(params)
    assert res.evidence.source_doi == "10.1002/hep.21178"


def test_fib4_fhir_code():
    params = FIB4Params(age=50, ast=30.0, alt=25.0, platelets=200.0)
    res = calculate_fib4(params)
    assert res.fhir_code == "96154-5"
    assert res.fhir_system == "http://loinc.org"


@pytest.mark.slow
@given(
    age=st.integers(min_value=18, max_value=100),
    ast=st.floats(min_value=1.0, max_value=500.0),
    alt=st.floats(min_value=1.0, max_value=500.0),
    platelets=st.floats(min_value=1.0, max_value=600.0),
)
@settings(max_examples=500)
def test_fib4_fuzz(age, ast, alt, platelets):
    params = FIB4Params(age=age, ast=ast, alt=alt, platelets=platelets)
    res = calculate_fib4(params)
    assert res.value is not None
    assert res.value >= 0
    assert res.interpretation

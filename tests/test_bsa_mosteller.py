import math
import pytest
from hypothesis import given, strategies as st, settings
from open_medicine.mcp.calculators.bsa_mosteller import calculate_bsa_mosteller, BSAMostellerParams


def test_bsa_typical_adult():
    """170cm, 70kg → ~1.81 m²"""
    params = BSAMostellerParams(height_cm=170, weight_kg=70)
    result = calculate_bsa_mosteller(params)
    expected = round(math.sqrt((170 * 70) / 3600), 2)
    assert result.value == expected
    assert "normal adult range" in result.interpretation.lower() or "within" in result.interpretation.lower()


def test_bsa_small_person():
    """150cm, 40kg → below normal range"""
    params = BSAMostellerParams(height_cm=150, weight_kg=40)
    result = calculate_bsa_mosteller(params)
    expected = round(math.sqrt((150 * 40) / 3600), 2)
    assert result.value == expected
    assert result.value < 1.5


def test_bsa_large_person():
    """190cm, 120kg → above normal range"""
    params = BSAMostellerParams(height_cm=190, weight_kg=120)
    result = calculate_bsa_mosteller(params)
    expected = round(math.sqrt((190 * 120) / 3600), 2)
    assert result.value == expected
    assert result.value > 2.2


def test_bsa_known_value():
    """180cm, 80kg → √(14400/3600) = √4 = 2.0 exactly"""
    params = BSAMostellerParams(height_cm=180, weight_kg=80)
    result = calculate_bsa_mosteller(params)
    assert result.value == 2.0


def test_bsa_evidence_doi():
    params = BSAMostellerParams(height_cm=170, weight_kg=70)
    result = calculate_bsa_mosteller(params)
    assert result.evidence.source_doi == "10.1056/NEJM198710223171717"


def test_bsa_fhir_code():
    params = BSAMostellerParams(height_cm=170, weight_kg=70)
    result = calculate_bsa_mosteller(params)
    assert result.fhir_code == "3140-1"
    assert result.fhir_system == "http://loinc.org"


@pytest.mark.slow
@given(
    height_cm=st.floats(min_value=30, max_value=250),
    weight_kg=st.floats(min_value=1, max_value=300),
)
@settings(max_examples=500)
def test_bsa_fuzz_valid_range(height_cm, weight_kg):
    params = BSAMostellerParams(height_cm=height_cm, weight_kg=weight_kg)
    result = calculate_bsa_mosteller(params)
    assert result.value is not None
    assert isinstance(result.value, float)
    assert result.value > 0
    assert result.value < 10  # physically impossible to exceed
    assert result.interpretation
    assert result.evidence.source_doi

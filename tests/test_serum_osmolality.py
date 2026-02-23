import pytest
from hypothesis import given, strategies as st, settings
from open_medicine.mcp.calculators.serum_osmolality import calculate_serum_osmolality, SerumOsmolalityParams


def test_normal_values():
    params = SerumOsmolalityParams(sodium=140, glucose=90, bun=14)
    result = calculate_serum_osmolality(params)
    # 2*140 + 90/18 + 14/2.8 = 280 + 5 + 5 = 290
    assert result.value == 290.0
    assert "Normal" in result.interpretation


def test_high_osmolality():
    params = SerumOsmolalityParams(sodium=155, glucose=400, bun=60)
    result = calculate_serum_osmolality(params)
    # 2*155 + 400/18 + 60/2.8 = 310 + 22.22 + 21.43 = 353.65
    assert result.value > 295
    assert "Elevated" in result.interpretation


def test_low_osmolality():
    params = SerumOsmolalityParams(sodium=120, glucose=90, bun=7)
    result = calculate_serum_osmolality(params)
    # 2*120 + 90/18 + 7/2.8 = 240 + 5 + 2.5 = 247.5
    assert result.value < 275
    assert "Low" in result.interpretation


def test_evidence_doi():
    result = calculate_serum_osmolality(SerumOsmolalityParams(sodium=140, glucose=90, bun=14))
    assert result.evidence.source_doi == "10.1067/mem.2001.119455"


def test_fhir_code():
    result = calculate_serum_osmolality(SerumOsmolalityParams(sodium=140, glucose=90, bun=14))
    assert result.fhir_code == "2692-2"
    assert result.fhir_system == "http://loinc.org"


@given(
    sodium=st.floats(min_value=100, max_value=180),
    glucose=st.floats(min_value=20, max_value=1000),
    bun=st.floats(min_value=1, max_value=150),
)
@settings(max_examples=200)
def test_fuzz_valid_range(sodium, glucose, bun):
    params = SerumOsmolalityParams(sodium=sodium, glucose=glucose, bun=bun)
    result = calculate_serum_osmolality(params)
    assert result.value is not None
    assert isinstance(result.value, float)
    assert result.value > 0
    assert result.interpretation

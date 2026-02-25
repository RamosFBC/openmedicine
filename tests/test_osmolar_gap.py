import pytest
from hypothesis import given, strategies as st, settings
from open_medicine.mcp.calculators.osmolar_gap import calculate_osmolar_gap, OsmolarGapParams


def test_normal_gap():
    # Calculated osm ~290, measured 295 → gap = 5
    params = OsmolarGapParams(measured_osmolality=295, sodium=140, glucose=90, bun=14)
    result = calculate_osmolar_gap(params)
    assert result.value == 5.0
    assert "Normal" in result.interpretation


def test_elevated_gap():
    # Calculated osm ~290, measured 320 → gap = 30
    params = OsmolarGapParams(measured_osmolality=320, sodium=140, glucose=90, bun=14)
    result = calculate_osmolar_gap(params)
    assert result.value > 10
    assert "Elevated" in result.interpretation


def test_negative_gap():
    params = OsmolarGapParams(measured_osmolality=270, sodium=140, glucose=90, bun=14)
    result = calculate_osmolar_gap(params)
    assert result.value < -10
    assert "Negative" in result.interpretation


def test_evidence_doi():
    result = calculate_osmolar_gap(OsmolarGapParams(measured_osmolality=295, sodium=140, glucose=90, bun=14))
    assert result.evidence.source_doi == "10.1001/jama.1976.03270150050029"


def test_fhir_code():
    result = calculate_osmolar_gap(OsmolarGapParams(measured_osmolality=295, sodium=140, glucose=90, bun=14))
    assert result.fhir_code == "2693-0"
    assert result.fhir_system == "http://loinc.org"


@given(
    measured=st.floats(min_value=200, max_value=450),
    sodium=st.floats(min_value=100, max_value=180),
    glucose=st.floats(min_value=20, max_value=1000),
    bun=st.floats(min_value=1, max_value=150),
)
@settings(max_examples=200)
def test_fuzz(measured, sodium, glucose, bun):
    params = OsmolarGapParams(measured_osmolality=measured, sodium=sodium, glucose=glucose, bun=bun)
    result = calculate_osmolar_gap(params)
    assert result.value is not None
    assert result.interpretation

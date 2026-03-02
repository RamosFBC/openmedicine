import pytest
from hypothesis import given, strategies as st, settings
from open_medicine.mcp.calculators.maintenance_iv_fluids import (
    calculate_maintenance_iv_fluids,
    MaintenanceIVFluidsParams,
)


# ---------------------------------------------------------------------------
# Tier 1: Deterministic Unit Tests
# ---------------------------------------------------------------------------


def test_maintenance_iv_fluids_5kg_infant():
    """5 kg infant: hourly = 4 * 5 = 20 mL/hr, daily = 100 * 5 = 500 mL/day."""
    params = MaintenanceIVFluidsParams(weight_kg=5.0)
    result = calculate_maintenance_iv_fluids(params)
    assert result.value == 20.0
    assert "20.0 mL/hr" in result.interpretation
    assert "500.0 mL/day" in result.interpretation


def test_maintenance_iv_fluids_10kg_child():
    """10 kg child: hourly = 4 * 10 = 40 mL/hr, daily = 100 * 10 = 1000 mL/day."""
    params = MaintenanceIVFluidsParams(weight_kg=10.0)
    result = calculate_maintenance_iv_fluids(params)
    assert result.value == 40.0
    assert "40.0 mL/hr" in result.interpretation
    assert "1000.0 mL/day" in result.interpretation


def test_maintenance_iv_fluids_15kg_child():
    """15 kg child: hourly = 40 + 2*(15-10) = 50 mL/hr, daily = 1000 + 50*5 = 1250 mL/day."""
    params = MaintenanceIVFluidsParams(weight_kg=15.0)
    result = calculate_maintenance_iv_fluids(params)
    assert result.value == 50.0
    assert "50.0 mL/hr" in result.interpretation
    assert "1250.0 mL/day" in result.interpretation


def test_maintenance_iv_fluids_20kg_child():
    """20 kg child: hourly = 40 + 2*10 = 60 mL/hr, daily = 1000 + 50*10 = 1500 mL/day."""
    params = MaintenanceIVFluidsParams(weight_kg=20.0)
    result = calculate_maintenance_iv_fluids(params)
    assert result.value == 60.0
    assert "60.0 mL/hr" in result.interpretation
    assert "1500.0 mL/day" in result.interpretation


def test_maintenance_iv_fluids_25kg_child():
    """25 kg child: hourly = 60 + 1*(25-20) = 65 mL/hr, daily = 1500 + 20*5 = 1600 mL/day."""
    params = MaintenanceIVFluidsParams(weight_kg=25.0)
    result = calculate_maintenance_iv_fluids(params)
    assert result.value == 65.0
    assert "65.0 mL/hr" in result.interpretation
    assert "1600.0 mL/day" in result.interpretation


def test_maintenance_iv_fluids_50kg_adult():
    """50 kg adult: hourly = 60 + 1*30 = 90 mL/hr, daily = 1500 + 20*30 = 2100 mL/day."""
    params = MaintenanceIVFluidsParams(weight_kg=50.0)
    result = calculate_maintenance_iv_fluids(params)
    assert result.value == 90.0
    assert "90.0 mL/hr" in result.interpretation
    assert "2100.0 mL/day" in result.interpretation


def test_maintenance_iv_fluids_70kg_adult():
    """70 kg adult: hourly = 60 + 1*50 = 110 mL/hr, daily = 1500 + 20*50 = 2500 mL/day."""
    params = MaintenanceIVFluidsParams(weight_kg=70.0)
    result = calculate_maintenance_iv_fluids(params)
    assert result.value == 110.0
    assert "110.0 mL/hr" in result.interpretation
    assert "2500.0 mL/day" in result.interpretation


def test_maintenance_iv_fluids_100kg_adult():
    """100 kg adult: hourly = 60 + 1*80 = 140 mL/hr, daily = 1500 + 20*80 = 3100 mL/day."""
    params = MaintenanceIVFluidsParams(weight_kg=100.0)
    result = calculate_maintenance_iv_fluids(params)
    assert result.value == 140.0
    assert "140.0 mL/hr" in result.interpretation
    assert "3100.0 mL/day" in result.interpretation


def test_maintenance_iv_fluids_fractional_weight():
    """7.5 kg infant: hourly = 4 * 7.5 = 30 mL/hr, daily = 100 * 7.5 = 750 mL/day."""
    params = MaintenanceIVFluidsParams(weight_kg=7.5)
    result = calculate_maintenance_iv_fluids(params)
    assert result.value == 30.0
    assert "30.0 mL/hr" in result.interpretation
    assert "750.0 mL/day" in result.interpretation


def test_maintenance_iv_fluids_boundary_just_above_10kg():
    """10.5 kg: hourly = 40 + 2*0.5 = 41 mL/hr, daily = 1000 + 50*0.5 = 1025 mL/day."""
    params = MaintenanceIVFluidsParams(weight_kg=10.5)
    result = calculate_maintenance_iv_fluids(params)
    assert result.value == 41.0
    assert "41.0 mL/hr" in result.interpretation
    assert "1025.0 mL/day" in result.interpretation


def test_maintenance_iv_fluids_boundary_just_above_20kg():
    """20.5 kg: hourly = 60 + 1*0.5 = 60.5 mL/hr, daily = 1500 + 20*0.5 = 1510 mL/day."""
    params = MaintenanceIVFluidsParams(weight_kg=20.5)
    result = calculate_maintenance_iv_fluids(params)
    assert result.value == 60.5
    assert "60.5 mL/hr" in result.interpretation
    assert "1510.0 mL/day" in result.interpretation


def test_maintenance_iv_fluids_very_small_weight():
    """1 kg neonate: hourly = 4 * 1 = 4 mL/hr, daily = 100 * 1 = 100 mL/day."""
    params = MaintenanceIVFluidsParams(weight_kg=1.0)
    result = calculate_maintenance_iv_fluids(params)
    assert result.value == 4.0
    assert "4.0 mL/hr" in result.interpretation
    assert "100.0 mL/day" in result.interpretation


def test_maintenance_iv_fluids_evidence_doi():
    """Verify the DOI is the original 1957 Holliday-Segar paper."""
    params = MaintenanceIVFluidsParams(weight_kg=10.0)
    result = calculate_maintenance_iv_fluids(params)
    assert result.evidence.source_doi == "10.1542/peds.19.5.823"
    assert "Holliday" in result.evidence.description
    assert "Segar" in result.evidence.description
    assert "1957" in result.evidence.description


def test_maintenance_iv_fluids_fhir_code():
    """Verify the FHIR/LOINC code is set correctly."""
    params = MaintenanceIVFluidsParams(weight_kg=10.0)
    result = calculate_maintenance_iv_fluids(params)
    assert result.fhir_code == "8710-0"
    assert result.fhir_system == "http://loinc.org"
    assert result.fhir_display is not None


def test_maintenance_iv_fluids_interpretation_contains_fluid_type():
    """Interpretation should mention fluid type guidance."""
    params = MaintenanceIVFluidsParams(weight_kg=70.0)
    result = calculate_maintenance_iv_fluids(params)
    assert "isotonic" in result.interpretation.lower() or "NaCl" in result.interpretation


def test_maintenance_iv_fluids_interpretation_mentions_weight():
    """Interpretation should include the patient weight for traceability."""
    params = MaintenanceIVFluidsParams(weight_kg=35.0)
    result = calculate_maintenance_iv_fluids(params)
    assert "35.0 kg" in result.interpretation


# ---------------------------------------------------------------------------
# Tier 2: Property-Based Fuzz Tests (equation calculator)
# ---------------------------------------------------------------------------


@given(
    weight_kg=st.floats(min_value=0.1, max_value=300.0),
)
@settings(max_examples=500)
def test_maintenance_iv_fluids_fuzz_valid_range(weight_kg):
    """Output is always within expected bounds for any valid input weight."""
    params = MaintenanceIVFluidsParams(weight_kg=weight_kg)
    result = calculate_maintenance_iv_fluids(params)
    assert result.value is not None
    assert isinstance(result.value, float)
    # Minimum hourly rate: 0.1 kg * 4 = 0.4 mL/hr
    # Maximum hourly rate: 300 kg -> 60 + 280 = 340 mL/hr
    assert result.value > 0
    assert result.value <= 400.0  # generous upper bound
    assert result.interpretation
    assert result.evidence.source_doi == "10.1542/peds.19.5.823"


@given(
    weight_kg=st.floats(min_value=0.1, max_value=300.0),
)
@settings(max_examples=200)
def test_maintenance_iv_fluids_fuzz_monotonic(weight_kg):
    """Hourly rate should increase monotonically with weight."""
    params1 = MaintenanceIVFluidsParams(weight_kg=weight_kg)
    params2 = MaintenanceIVFluidsParams(weight_kg=weight_kg + 0.1)
    result1 = calculate_maintenance_iv_fluids(params1)
    result2 = calculate_maintenance_iv_fluids(params2)
    assert result2.value >= result1.value


@given(
    weight_kg=st.floats(min_value=0.1, max_value=10.0),
)
@settings(max_examples=200)
def test_maintenance_iv_fluids_fuzz_first_bracket(weight_kg):
    """For weight <= 10 kg, hourly rate should be exactly 4 * weight."""
    params = MaintenanceIVFluidsParams(weight_kg=weight_kg)
    result = calculate_maintenance_iv_fluids(params)
    expected = round(4.0 * weight_kg, 1)
    assert result.value == expected


@given(
    weight_kg=st.floats(min_value=10.01, max_value=20.0),
)
@settings(max_examples=200)
def test_maintenance_iv_fluids_fuzz_second_bracket(weight_kg):
    """For 10 < weight <= 20 kg, hourly rate should be 40 + 2*(weight-10)."""
    params = MaintenanceIVFluidsParams(weight_kg=weight_kg)
    result = calculate_maintenance_iv_fluids(params)
    expected = round(40.0 + 2.0 * (weight_kg - 10.0), 1)
    assert result.value == expected


@given(
    weight_kg=st.floats(min_value=20.01, max_value=300.0),
)
@settings(max_examples=200)
def test_maintenance_iv_fluids_fuzz_third_bracket(weight_kg):
    """For weight > 20 kg, hourly rate should be 60 + 1*(weight-20)."""
    params = MaintenanceIVFluidsParams(weight_kg=weight_kg)
    result = calculate_maintenance_iv_fluids(params)
    expected = round(60.0 + 1.0 * (weight_kg - 20.0), 1)
    assert result.value == expected

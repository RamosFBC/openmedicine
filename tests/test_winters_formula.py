import pytest
from hypothesis import given, strategies as st, settings
from open_medicine.mcp.calculators.winters_formula import calculate_winters_formula, WintersFormulaParams


def test_basic_calculation():
    # HCO3=12: expected = 1.5*12 + 8 = 26
    params = WintersFormulaParams(bicarbonate=12)
    result = calculate_winters_formula(params)
    assert result.value == 26.0
    assert "26.0" in result.interpretation


def test_appropriate_compensation():
    params = WintersFormulaParams(bicarbonate=12, paco2=26)
    result = calculate_winters_formula(params)
    assert "Appropriate" in result.interpretation or "within expected" in result.interpretation


def test_respiratory_acidosis():
    # Expected 26 ±2 → upper 28. paco2=35 > 28
    params = WintersFormulaParams(bicarbonate=12, paco2=35)
    result = calculate_winters_formula(params)
    assert "respiratory acidosis" in result.interpretation


def test_respiratory_alkalosis():
    # Expected 26 ±2 → lower 24. paco2=20 < 24
    params = WintersFormulaParams(bicarbonate=12, paco2=20)
    result = calculate_winters_formula(params)
    assert "respiratory alkalosis" in result.interpretation


def test_evidence_doi():
    result = calculate_winters_formula(WintersFormulaParams(bicarbonate=15))
    assert result.evidence.source_doi == "10.7326/0003-4819-66-2-312"


def test_fhir_code():
    result = calculate_winters_formula(WintersFormulaParams(bicarbonate=15))
    assert result.fhir_code == "2021-4"
    assert result.fhir_system == "http://loinc.org"


@given(bicarbonate=st.floats(min_value=1, max_value=40))
@settings(max_examples=200)
def test_fuzz(bicarbonate):
    result = calculate_winters_formula(WintersFormulaParams(bicarbonate=bicarbonate))
    assert result.value is not None
    assert result.value > 0
    assert result.interpretation

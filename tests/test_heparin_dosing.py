import pytest
from open_medicine.mcp.calculators.heparin_dosing import calculate_heparin_dosing, HeparinDosingParams


def test_heparin_initial_dosing():
    """No aPTT → initial bolus + infusion only."""
    params = HeparinDosingParams(weight_kg=70)
    result = calculate_heparin_dosing(params)
    assert "5600" in result.interpretation  # 80 * 70 = 5600 bolus
    assert "1260" in result.interpretation  # 18 * 70 = 1260 infusion


def test_heparin_aptt_below_35():
    params = HeparinDosingParams(weight_kg=70, aptt=30)
    result = calculate_heparin_dosing(params)
    assert "Bolus" in result.interpretation
    assert "increase" in result.interpretation


def test_heparin_aptt_35_45():
    params = HeparinDosingParams(weight_kg=70, aptt=40)
    result = calculate_heparin_dosing(params)
    assert "Bolus" in result.interpretation
    assert "increase" in result.interpretation


def test_heparin_therapeutic():
    params = HeparinDosingParams(weight_kg=70, aptt=55)
    result = calculate_heparin_dosing(params)
    assert "Therapeutic" in result.interpretation or "No change" in result.interpretation


def test_heparin_aptt_71_90():
    params = HeparinDosingParams(weight_kg=70, aptt=80)
    result = calculate_heparin_dosing(params)
    assert "Decrease" in result.interpretation or "decrease" in result.interpretation


def test_heparin_aptt_above_90():
    params = HeparinDosingParams(weight_kg=70, aptt=100)
    result = calculate_heparin_dosing(params)
    assert "Hold" in result.interpretation
    assert "decrease" in result.interpretation


def test_heparin_evidence_doi():
    params = HeparinDosingParams(weight_kg=70)
    result = calculate_heparin_dosing(params)
    assert result.evidence.source_doi == "10.7326/0003-4819-119-9-199311010-00007"

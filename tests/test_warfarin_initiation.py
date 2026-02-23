import pytest
from open_medicine.mcp.calculators.warfarin_initiation import calculate_warfarin_initiation, WarfarinInitiationParams, WarfarinIndication


def test_warfarin_standard_dose():
    params = WarfarinInitiationParams(age=55, indication=WarfarinIndication.AF_VTE)
    result = calculate_warfarin_initiation(params)
    assert result.value == 5.0
    assert "2.0-3.0" in result.interpretation


def test_warfarin_reduced_elderly():
    params = WarfarinInitiationParams(age=70, indication=WarfarinIndication.AF_VTE)
    result = calculate_warfarin_initiation(params)
    assert result.value == 2.5
    assert "age > 60" in result.interpretation


def test_warfarin_reduced_liver():
    params = WarfarinInitiationParams(age=50, has_liver_disease=True, indication=WarfarinIndication.AF_VTE)
    result = calculate_warfarin_initiation(params)
    assert result.value == 2.5


def test_warfarin_reduced_drug_interactions():
    params = WarfarinInitiationParams(age=50, has_drug_interactions=True, indication=WarfarinIndication.AF_VTE)
    result = calculate_warfarin_initiation(params)
    assert result.value == 2.5


def test_warfarin_higher_dose_young():
    params = WarfarinInitiationParams(age=40, indication=WarfarinIndication.AF_VTE)
    result = calculate_warfarin_initiation(params)
    assert result.value == 7.5


def test_warfarin_mechanical_valve_target():
    params = WarfarinInitiationParams(age=55, indication=WarfarinIndication.MECHANICAL_VALVE)
    result = calculate_warfarin_initiation(params)
    assert "2.5-3.5" in result.interpretation


def test_warfarin_evidence_doi():
    params = WarfarinInitiationParams(age=55, indication=WarfarinIndication.AF_VTE)
    result = calculate_warfarin_initiation(params)
    assert result.evidence.source_doi == "10.1378/chest.11-2295"

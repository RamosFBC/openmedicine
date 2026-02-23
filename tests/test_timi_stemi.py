import pytest
from open_medicine.mcp.calculators.timi_stemi import calculate_timi_stemi, TIMISTEMIParams


def test_timi_stemi_minimum():
    params = TIMISTEMIParams(age=40)
    result = calculate_timi_stemi(params)
    assert result.value == 0


def test_timi_stemi_maximum():
    params = TIMISTEMIParams(
        age=75,
        diabetes_or_hypertension_or_angina=True,
        systolic_bp_lt_100=True,
        heart_rate_gt_100=True,
        killip_class_ii_iv=True,
        weight_lt_67kg=True,
        anterior_st_elevation_or_lbbb=True,
        time_to_treatment_gt_4h=True,
    )
    result = calculate_timi_stemi(params)
    assert result.value == 14


def test_timi_stemi_age_65_74():
    params = TIMISTEMIParams(age=70)
    result = calculate_timi_stemi(params)
    assert result.value == 2


def test_timi_stemi_age_75():
    params = TIMISTEMIParams(age=75)
    result = calculate_timi_stemi(params)
    assert result.value == 3


def test_timi_stemi_age_64():
    params = TIMISTEMIParams(age=64)
    result = calculate_timi_stemi(params)
    assert result.value == 0


def test_timi_stemi_sbp_gives_3():
    params = TIMISTEMIParams(age=40, systolic_bp_lt_100=True)
    result = calculate_timi_stemi(params)
    assert result.value == 3


def test_timi_stemi_evidence_doi():
    result = calculate_timi_stemi(TIMISTEMIParams(age=50))
    assert result.evidence.source_doi == "10.1161/01.CIR.102.17.2031"


def test_timi_stemi_fhir():
    result = calculate_timi_stemi(TIMISTEMIParams(age=50))
    assert result.fhir_system == "http://loinc.org"

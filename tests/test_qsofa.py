import pytest
from open_medicine.mcp.calculators.qsofa import calculate_qsofa, QSOFAParams


def test_qsofa_minimum_score():
    params = QSOFAParams(respiratory_rate=18, systolic_blood_pressure=120, altered_mentation=False)
    result = calculate_qsofa(params)
    assert result.value == 0
    assert "Low risk" in result.interpretation


def test_qsofa_maximum_score():
    params = QSOFAParams(respiratory_rate=30, systolic_blood_pressure=80, altered_mentation=True)
    result = calculate_qsofa(params)
    assert result.value == 3
    assert "High risk" in result.interpretation


def test_qsofa_score_1_rr():
    params = QSOFAParams(respiratory_rate=22, systolic_blood_pressure=120, altered_mentation=False)
    result = calculate_qsofa(params)
    assert result.value == 1
    assert "Low risk" in result.interpretation


def test_qsofa_score_1_sbp():
    params = QSOFAParams(respiratory_rate=18, systolic_blood_pressure=100, altered_mentation=False)
    result = calculate_qsofa(params)
    assert result.value == 1


def test_qsofa_score_1_mentation():
    params = QSOFAParams(respiratory_rate=18, systolic_blood_pressure=120, altered_mentation=True)
    result = calculate_qsofa(params)
    assert result.value == 1


def test_qsofa_score_2_threshold():
    """Score of 2 = high risk threshold."""
    params = QSOFAParams(respiratory_rate=22, systolic_blood_pressure=100, altered_mentation=False)
    result = calculate_qsofa(params)
    assert result.value == 2
    assert "High risk" in result.interpretation


def test_qsofa_rr_boundary_below():
    params = QSOFAParams(respiratory_rate=21, systolic_blood_pressure=120, altered_mentation=False)
    result = calculate_qsofa(params)
    assert result.value == 0


def test_qsofa_sbp_boundary_above():
    params = QSOFAParams(respiratory_rate=18, systolic_blood_pressure=101, altered_mentation=False)
    result = calculate_qsofa(params)
    assert result.value == 0


def test_qsofa_evidence_doi():
    params = QSOFAParams(respiratory_rate=18, systolic_blood_pressure=120, altered_mentation=False)
    result = calculate_qsofa(params)
    assert result.evidence.source_doi == "10.1001/jama.2016.0288"


def test_qsofa_fhir_code():
    params = QSOFAParams(respiratory_rate=18, systolic_blood_pressure=120, altered_mentation=False)
    result = calculate_qsofa(params)
    assert result.fhir_code == "96792-0"
    assert result.fhir_system == "http://loinc.org"

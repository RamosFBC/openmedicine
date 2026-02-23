import pytest
from open_medicine.mcp.calculators.heart_score import calculate_heart_score, HEARTScoreParams


def test_heart_score_minimum():
    params = HEARTScoreParams(history=0, ecg=0, age=30, risk_factor_count=0, troponin=0)
    result = calculate_heart_score(params)
    assert result.value == 0
    assert "Low risk" in result.interpretation


def test_heart_score_maximum():
    params = HEARTScoreParams(history=2, ecg=2, age=70, risk_factor_count=3, troponin=2)
    result = calculate_heart_score(params)
    assert result.value == 10
    assert "High risk" in result.interpretation


def test_heart_score_low_boundary():
    # Score = 3: history=1, ecg=0, age=30(0), risk_factor_count=1(1), troponin=1
    params = HEARTScoreParams(history=1, ecg=0, age=30, risk_factor_count=1, troponin=1)
    result = calculate_heart_score(params)
    assert result.value == 3
    assert "Low risk" in result.interpretation


def test_heart_score_moderate_boundary():
    # Score = 4
    params = HEARTScoreParams(history=1, ecg=1, age=30, risk_factor_count=1, troponin=1)
    result = calculate_heart_score(params)
    assert result.value == 4
    assert "Moderate risk" in result.interpretation


def test_heart_score_moderate_upper():
    # Score = 6
    params = HEARTScoreParams(history=2, ecg=2, age=30, risk_factor_count=1, troponin=1)
    result = calculate_heart_score(params)
    assert result.value == 6
    assert "Moderate risk" in result.interpretation


def test_heart_score_high_boundary():
    # Score = 7
    params = HEARTScoreParams(history=2, ecg=2, age=50, risk_factor_count=1, troponin=1)
    result = calculate_heart_score(params)
    assert result.value == 7
    assert "High risk" in result.interpretation


def test_heart_score_age_thresholds():
    base = dict(history=0, ecg=0, risk_factor_count=0, troponin=0)
    assert calculate_heart_score(HEARTScoreParams(age=44, **base)).value == 0
    assert calculate_heart_score(HEARTScoreParams(age=45, **base)).value == 1
    assert calculate_heart_score(HEARTScoreParams(age=64, **base)).value == 1
    assert calculate_heart_score(HEARTScoreParams(age=65, **base)).value == 2


def test_heart_score_atherosclerosis_gives_2():
    params = HEARTScoreParams(history=0, ecg=0, age=30, risk_factor_count=0, history_of_atherosclerosis=True, troponin=0)
    result = calculate_heart_score(params)
    assert result.value == 2


def test_heart_score_evidence_doi():
    params = HEARTScoreParams(history=0, ecg=0, age=30, troponin=0)
    result = calculate_heart_score(params)
    assert result.evidence.source_doi == "10.1007/BF03086144"


def test_heart_score_fhir():
    params = HEARTScoreParams(history=0, ecg=0, age=30, troponin=0)
    result = calculate_heart_score(params)
    assert result.fhir_system == "http://loinc.org"

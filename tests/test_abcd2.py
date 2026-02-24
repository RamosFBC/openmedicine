import pytest
from open_medicine.mcp.calculators.abcd2 import (
    calculate_abcd2, ABCD2Params, ABCD2ClinicalFeature, ABCD2Duration,
)


def test_abcd2_minimum_score():
    params = ABCD2Params(
        age_ge_60=False, bp_ge_140_90=False,
        clinical_features=ABCD2ClinicalFeature.OTHER,
        duration=ABCD2Duration.LT_10_MIN, diabetes=False,
    )
    result = calculate_abcd2(params)
    assert result.value == 0
    assert "Low risk" in result.interpretation


def test_abcd2_maximum_score():
    params = ABCD2Params(
        age_ge_60=True, bp_ge_140_90=True,
        clinical_features=ABCD2ClinicalFeature.UNILATERAL_WEAKNESS,
        duration=ABCD2Duration.GE_60_MIN, diabetes=True,
    )
    result = calculate_abcd2(params)
    assert result.value == 7
    assert "High risk" in result.interpretation


def test_abcd2_low_risk_boundary():
    params = ABCD2Params(
        age_ge_60=True, bp_ge_140_90=True,
        clinical_features=ABCD2ClinicalFeature.SPEECH_DISTURBANCE,
        duration=ABCD2Duration.LT_10_MIN, diabetes=False,
    )
    result = calculate_abcd2(params)
    assert result.value == 3
    assert "Low risk" in result.interpretation


def test_abcd2_moderate_risk():
    params = ABCD2Params(
        age_ge_60=True, bp_ge_140_90=True,
        clinical_features=ABCD2ClinicalFeature.UNILATERAL_WEAKNESS,
        duration=ABCD2Duration.LT_10_MIN, diabetes=False,
    )
    result = calculate_abcd2(params)
    assert result.value == 4
    assert "Moderate risk" in result.interpretation


def test_abcd2_high_risk_boundary():
    params = ABCD2Params(
        age_ge_60=True, bp_ge_140_90=True,
        clinical_features=ABCD2ClinicalFeature.UNILATERAL_WEAKNESS,
        duration=ABCD2Duration.TEN_TO_59_MIN, diabetes=True,
    )
    result = calculate_abcd2(params)
    assert result.value == 6
    assert "High risk" in result.interpretation


def test_abcd2_evidence_doi():
    params = ABCD2Params(
        age_ge_60=False, bp_ge_140_90=False,
        clinical_features=ABCD2ClinicalFeature.OTHER,
        duration=ABCD2Duration.LT_10_MIN,
    )
    result = calculate_abcd2(params)
    assert result.evidence.source_doi == "10.1016/S0140-6736(07)60150-0"


def test_abcd2_fhir_code():
    params = ABCD2Params(
        age_ge_60=False, bp_ge_140_90=False,
        clinical_features=ABCD2ClinicalFeature.OTHER,
        duration=ABCD2Duration.LT_10_MIN,
    )
    result = calculate_abcd2(params)
    assert result.fhir_code == "72090-4"
    assert result.fhir_system == "http://loinc.org"

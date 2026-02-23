import pytest
from open_medicine.mcp.calculators.timi_ua_nstemi import calculate_timi_ua_nstemi, TIMIUANSTEMIParams


def test_timi_ua_nstemi_minimum():
    params = TIMIUANSTEMIParams()
    result = calculate_timi_ua_nstemi(params)
    assert result.value == 0
    assert "Low risk" in result.interpretation


def test_timi_ua_nstemi_maximum():
    params = TIMIUANSTEMIParams(
        age_gte_65=True,
        three_or_more_cad_risk_factors=True,
        known_cad_gte_50_stenosis=True,
        aspirin_use_past_7_days=True,
        two_or_more_anginal_events_24h=True,
        st_deviation_gte_0_5mm=True,
        elevated_cardiac_markers=True,
    )
    result = calculate_timi_ua_nstemi(params)
    assert result.value == 7
    assert "High risk" in result.interpretation


def test_timi_ua_nstemi_low_boundary():
    params = TIMIUANSTEMIParams(age_gte_65=True, three_or_more_cad_risk_factors=True)
    result = calculate_timi_ua_nstemi(params)
    assert result.value == 2
    assert "Low risk" in result.interpretation


def test_timi_ua_nstemi_intermediate_boundary():
    params = TIMIUANSTEMIParams(age_gte_65=True, three_or_more_cad_risk_factors=True, known_cad_gte_50_stenosis=True)
    result = calculate_timi_ua_nstemi(params)
    assert result.value == 3
    assert "Intermediate risk" in result.interpretation


def test_timi_ua_nstemi_high_boundary():
    params = TIMIUANSTEMIParams(
        age_gte_65=True,
        three_or_more_cad_risk_factors=True,
        known_cad_gte_50_stenosis=True,
        aspirin_use_past_7_days=True,
        two_or_more_anginal_events_24h=True,
    )
    result = calculate_timi_ua_nstemi(params)
    assert result.value == 5
    assert "High risk" in result.interpretation


def test_timi_ua_nstemi_evidence_doi():
    result = calculate_timi_ua_nstemi(TIMIUANSTEMIParams())
    assert result.evidence.source_doi == "10.1001/jama.284.7.835"


def test_timi_ua_nstemi_fhir():
    result = calculate_timi_ua_nstemi(TIMIUANSTEMIParams())
    assert result.fhir_system == "http://loinc.org"

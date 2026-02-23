import pytest
from open_medicine.mcp.calculators.padua import calculate_padua, PaduaParams


def test_minimum_score():
    result = calculate_padua(PaduaParams())
    assert result.value == 0
    assert "Low" in result.interpretation


def test_maximum_score():
    result = calculate_padua(PaduaParams(
        active_cancer=True, previous_vte=True, reduced_mobility=True,
        known_thrombophilia=True, recent_trauma_or_surgery=True,
        age_70_or_older=True, heart_or_respiratory_failure=True,
        acute_mi_or_stroke=True, acute_infection_or_rheumatic=True,
        obesity=True, ongoing_hormonal_treatment=True,
    ))
    # 4*3 + 1*2 + 6*1 = 12+2+6 = 20
    assert result.value == 20
    assert "High" in result.interpretation


def test_low_risk_boundary():
    """Score of 3 is still low risk."""
    result = calculate_padua(PaduaParams(active_cancer=True))
    assert result.value == 3
    assert "Low" in result.interpretation


def test_high_risk_boundary():
    """Score of 4 is high risk."""
    result = calculate_padua(PaduaParams(active_cancer=True, age_70_or_older=True))
    assert result.value == 4
    assert "High" in result.interpretation
    assert "recommended" in result.interpretation.lower()


def test_two_point_item():
    result = calculate_padua(PaduaParams(recent_trauma_or_surgery=True))
    assert result.value == 2


def test_one_point_items():
    result = calculate_padua(PaduaParams(age_70_or_older=True, obesity=True))
    assert result.value == 2


def test_evidence_doi():
    result = calculate_padua(PaduaParams())
    assert result.evidence.source_doi == "10.1111/j.1538-7836.2010.04044.x"


def test_fhir():
    result = calculate_padua(PaduaParams())
    assert result.fhir_system == "http://loinc.org"

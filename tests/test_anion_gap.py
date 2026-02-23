import pytest
from open_medicine.mcp.calculators.anion_gap import calculate_anion_gap, AnionGapParams


def test_anion_gap_normal():
    params = AnionGapParams(sodium=140, chloride=104, bicarbonate=24)
    result = calculate_anion_gap(params)
    assert result.value == 12.0
    assert "Normal" in result.interpretation


def test_anion_gap_elevated():
    params = AnionGapParams(sodium=140, chloride=100, bicarbonate=15)
    result = calculate_anion_gap(params)
    assert result.value == 25.0
    assert "Elevated" in result.interpretation
    assert "HAGMA" in result.interpretation


def test_anion_gap_low():
    params = AnionGapParams(sodium=140, chloride=110, bicarbonate=24)
    result = calculate_anion_gap(params)
    assert result.value == 6.0
    assert "Low" in result.interpretation


def test_anion_gap_corrected_normal_albumin():
    """Normal albumin (4.0) should not change AG."""
    params = AnionGapParams(sodium=140, chloride=104, bicarbonate=24, albumin=4.0)
    result = calculate_anion_gap(params)
    assert result.value == 12.0


def test_anion_gap_corrected_low_albumin():
    """Low albumin masks true AG. Corrected AG = 12 + 2.5*(4-2) = 17."""
    params = AnionGapParams(sodium=140, chloride=104, bicarbonate=24, albumin=2.0)
    result = calculate_anion_gap(params)
    assert result.value == 17.0
    assert "corrected" in result.interpretation.lower()
    assert "Elevated" in result.interpretation


def test_anion_gap_evidence_doi():
    params = AnionGapParams(sodium=140, chloride=104, bicarbonate=24)
    result = calculate_anion_gap(params)
    assert result.evidence.source_doi == "10.1056/NEJMra066466"


def test_anion_gap_fhir_code():
    params = AnionGapParams(sodium=140, chloride=104, bicarbonate=24)
    result = calculate_anion_gap(params)
    assert result.fhir_code == "33037-3"

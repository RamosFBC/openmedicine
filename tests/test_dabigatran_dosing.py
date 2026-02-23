import pytest
from open_medicine.mcp.calculators.dabigatran_dosing import calculate_dabigatran_dosing, DabigatranDosingParams, DabigatranIndication


def test_dabigatran_nvaf_standard():
    params = DabigatranDosingParams(crcl=80, indication=DabigatranIndication.NVAF)
    result = calculate_dabigatran_dosing(params)
    assert "150 mg twice daily" in result.interpretation


def test_dabigatran_nvaf_severe_renal():
    params = DabigatranDosingParams(crcl=20, indication=DabigatranIndication.NVAF)
    result = calculate_dabigatran_dosing(params)
    assert "75 mg twice daily" in result.interpretation


def test_dabigatran_nvaf_esrd():
    params = DabigatranDosingParams(crcl=10, indication=DabigatranIndication.NVAF)
    result = calculate_dabigatran_dosing(params)
    assert "Avoid" in result.interpretation


def test_dabigatran_nvaf_pgp_normal_renal():
    params = DabigatranDosingParams(crcl=80, indication=DabigatranIndication.NVAF, concomitant_pgp_inhibitor=True)
    result = calculate_dabigatran_dosing(params)
    assert "75 mg twice daily" in result.interpretation
    assert "P-gp" in result.interpretation


def test_dabigatran_nvaf_pgp_moderate_renal():
    params = DabigatranDosingParams(crcl=40, indication=DabigatranIndication.NVAF, concomitant_pgp_inhibitor=True)
    result = calculate_dabigatran_dosing(params)
    assert "75 mg twice daily" in result.interpretation


def test_dabigatran_nvaf_pgp_severe_renal():
    params = DabigatranDosingParams(crcl=20, indication=DabigatranIndication.NVAF, concomitant_pgp_inhibitor=True)
    result = calculate_dabigatran_dosing(params)
    assert "Avoid" in result.interpretation


def test_dabigatran_vte_standard():
    params = DabigatranDosingParams(crcl=60, indication=DabigatranIndication.VTE_TREATMENT)
    result = calculate_dabigatran_dosing(params)
    assert "150 mg twice daily" in result.interpretation
    assert "parenteral" in result.interpretation


def test_dabigatran_vte_severe_renal():
    params = DabigatranDosingParams(crcl=20, indication=DabigatranIndication.VTE_TREATMENT)
    result = calculate_dabigatran_dosing(params)
    assert "Avoid" in result.interpretation


def test_dabigatran_evidence_doi():
    params = DabigatranDosingParams(crcl=60, indication=DabigatranIndication.NVAF)
    result = calculate_dabigatran_dosing(params)
    assert result.evidence.source_doi == "10.1056/NEJMoa0905561"

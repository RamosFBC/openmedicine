import pytest
from open_medicine.mcp.calculators.edoxaban_dosing import calculate_edoxaban_dosing, EdoxabanDosingParams, EdoxabanIndication


def test_edoxaban_nvaf_standard():
    params = EdoxabanDosingParams(crcl=70, weight_kg=80, indication=EdoxabanIndication.NVAF)
    result = calculate_edoxaban_dosing(params)
    assert "60 mg once daily" in result.interpretation


def test_edoxaban_nvaf_high_crcl():
    """CrCl >95 — edoxaban NOT recommended in NVAF."""
    params = EdoxabanDosingParams(crcl=100, weight_kg=80, indication=EdoxabanIndication.NVAF)
    result = calculate_edoxaban_dosing(params)
    assert "Not recommended" in result.interpretation


def test_edoxaban_nvaf_moderate_renal():
    params = EdoxabanDosingParams(crcl=40, weight_kg=80, indication=EdoxabanIndication.NVAF)
    result = calculate_edoxaban_dosing(params)
    assert "30 mg once daily" in result.interpretation


def test_edoxaban_nvaf_esrd():
    params = EdoxabanDosingParams(crcl=10, weight_kg=80, indication=EdoxabanIndication.NVAF)
    result = calculate_edoxaban_dosing(params)
    assert "Avoid" in result.interpretation


def test_edoxaban_vte_standard():
    params = EdoxabanDosingParams(crcl=70, weight_kg=80, indication=EdoxabanIndication.VTE_TREATMENT)
    result = calculate_edoxaban_dosing(params)
    assert "60 mg once daily" in result.interpretation
    assert "parenteral" in result.interpretation


def test_edoxaban_vte_reduced_renal():
    params = EdoxabanDosingParams(crcl=40, weight_kg=80, indication=EdoxabanIndication.VTE_TREATMENT)
    result = calculate_edoxaban_dosing(params)
    assert "30 mg once daily" in result.interpretation


def test_edoxaban_vte_reduced_weight():
    params = EdoxabanDosingParams(crcl=70, weight_kg=55, indication=EdoxabanIndication.VTE_TREATMENT)
    result = calculate_edoxaban_dosing(params)
    assert "30 mg once daily" in result.interpretation
    assert "low body weight" in result.interpretation


def test_edoxaban_vte_reduced_pgp():
    params = EdoxabanDosingParams(crcl=70, weight_kg=80, indication=EdoxabanIndication.VTE_TREATMENT, concomitant_pgp_inhibitor=True)
    result = calculate_edoxaban_dosing(params)
    assert "30 mg once daily" in result.interpretation
    assert "P-gp" in result.interpretation


def test_edoxaban_evidence_doi():
    params = EdoxabanDosingParams(crcl=70, weight_kg=80, indication=EdoxabanIndication.NVAF)
    result = calculate_edoxaban_dosing(params)
    assert result.evidence.source_doi == "10.1056/NEJMoa1310907"

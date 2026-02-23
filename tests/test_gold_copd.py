import pytest
from open_medicine.mcp.calculators.gold_copd import calculate_gold_copd, GOLDCOPDParams


def test_gold1_group_a():
    result = calculate_gold_copd(GOLDCOPDParams(
        fev1_percent_predicted=85, exacerbations_past_year=0,
        hospitalizations_past_year=0, mmrc_dyspnea=1
    ))
    assert result.value == 1
    assert "GOLD 1" in result.interpretation
    assert "Group A" in result.interpretation


def test_gold2_group_b():
    result = calculate_gold_copd(GOLDCOPDParams(
        fev1_percent_predicted=60, exacerbations_past_year=1,
        hospitalizations_past_year=0, mmrc_dyspnea=3
    ))
    assert result.value == 2
    assert "GOLD 2" in result.interpretation
    assert "Group B" in result.interpretation


def test_gold3_group_e_by_exacerbations():
    result = calculate_gold_copd(GOLDCOPDParams(
        fev1_percent_predicted=35, exacerbations_past_year=2,
        hospitalizations_past_year=0, mmrc_dyspnea=1
    ))
    assert result.value == 3
    assert "GOLD 3" in result.interpretation
    assert "Group E" in result.interpretation


def test_gold4_group_e_by_hospitalization():
    result = calculate_gold_copd(GOLDCOPDParams(
        fev1_percent_predicted=25, exacerbations_past_year=0,
        hospitalizations_past_year=1, mmrc_dyspnea=0
    ))
    assert result.value == 4
    assert "GOLD 4" in result.interpretation
    assert "Group E" in result.interpretation


def test_cat_score_overrides_mmrc_high():
    """CAT ≥10 → high symptoms even if mMRC is low."""
    result = calculate_gold_copd(GOLDCOPDParams(
        fev1_percent_predicted=90, exacerbations_past_year=0,
        hospitalizations_past_year=0, mmrc_dyspnea=0, cat_score=15
    ))
    assert "Group B" in result.interpretation


def test_cat_score_overrides_mmrc_low():
    """CAT <10 → low symptoms even if mMRC is high."""
    result = calculate_gold_copd(GOLDCOPDParams(
        fev1_percent_predicted=90, exacerbations_past_year=0,
        hospitalizations_past_year=0, mmrc_dyspnea=3, cat_score=5
    ))
    assert "Group A" in result.interpretation


def test_boundary_fev1_80():
    result = calculate_gold_copd(GOLDCOPDParams(
        fev1_percent_predicted=80, exacerbations_past_year=0,
        hospitalizations_past_year=0, mmrc_dyspnea=0
    ))
    assert result.value == 1


def test_boundary_fev1_50():
    result = calculate_gold_copd(GOLDCOPDParams(
        fev1_percent_predicted=50, exacerbations_past_year=0,
        hospitalizations_past_year=0, mmrc_dyspnea=0
    ))
    assert result.value == 2


def test_boundary_fev1_30():
    result = calculate_gold_copd(GOLDCOPDParams(
        fev1_percent_predicted=30, exacerbations_past_year=0,
        hospitalizations_past_year=0, mmrc_dyspnea=0
    ))
    assert result.value == 3


def test_boundary_fev1_29():
    result = calculate_gold_copd(GOLDCOPDParams(
        fev1_percent_predicted=29, exacerbations_past_year=0,
        hospitalizations_past_year=0, mmrc_dyspnea=0
    ))
    assert result.value == 4


def test_evidence():
    result = calculate_gold_copd(GOLDCOPDParams(
        fev1_percent_predicted=50, exacerbations_past_year=0,
        hospitalizations_past_year=0, mmrc_dyspnea=0
    ))
    assert "GOLD" in result.evidence.description
    assert result.evidence.level == "Guideline"


def test_fhir_code():
    result = calculate_gold_copd(GOLDCOPDParams(
        fev1_percent_predicted=50, exacerbations_past_year=0,
        hospitalizations_past_year=0, mmrc_dyspnea=0
    ))
    assert result.fhir_system == "http://loinc.org"

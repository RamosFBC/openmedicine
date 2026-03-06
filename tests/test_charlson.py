import math
import pytest
from open_medicine.mcp.calculators.charlson import calculate_charlson, CharlsonParams


# ========================================================================
# Tier 1: Deterministic Unit Tests
# ========================================================================


def test_charlson_minimum_score():
    """Test lowest possible score with all comorbidities absent and no age."""
    params = CharlsonParams()
    result = calculate_charlson(params)
    assert result.value == 0
    assert "No comorbidity burden" in result.interpretation
    assert "Estimated 10-year survival: 98.3%" in result.interpretation


def test_charlson_maximum_comorbidity_score():
    """Test highest possible comorbidity score with all conditions present (no age).

    Maximum comorbidity points:
    10 x 1-point conditions = 10
    6 x 2-point conditions = 12
    1 x 3-point condition = 3
    2 x 6-point conditions = 12
    Total = 37
    """
    params = CharlsonParams(
        myocardial_infarction=True,
        congestive_heart_failure=True,
        peripheral_vascular_disease=True,
        cerebrovascular_disease=True,
        dementia=True,
        chronic_pulmonary_disease=True,
        connective_tissue_disease=True,
        peptic_ulcer_disease=True,
        mild_liver_disease=True,
        uncomplicated_diabetes=True,
        hemiplegia=True,
        moderate_severe_renal_disease=True,
        diabetes_with_end_organ_damage=True,
        solid_tumor=True,
        leukemia=True,
        lymphoma=True,
        moderate_severe_liver_disease=True,
        metastatic_solid_tumor=True,
        aids=True,
    )
    result = calculate_charlson(params)
    assert result.value == 37
    assert "High comorbidity burden" in result.interpretation


def test_charlson_maximum_with_age():
    """Test highest possible total score: 37 comorbidity + 4 age points = 41."""
    params = CharlsonParams(
        myocardial_infarction=True,
        congestive_heart_failure=True,
        peripheral_vascular_disease=True,
        cerebrovascular_disease=True,
        dementia=True,
        chronic_pulmonary_disease=True,
        connective_tissue_disease=True,
        peptic_ulcer_disease=True,
        mild_liver_disease=True,
        uncomplicated_diabetes=True,
        hemiplegia=True,
        moderate_severe_renal_disease=True,
        diabetes_with_end_organ_damage=True,
        solid_tumor=True,
        leukemia=True,
        lymphoma=True,
        moderate_severe_liver_disease=True,
        metastatic_solid_tumor=True,
        aids=True,
        age=85,
    )
    result = calculate_charlson(params)
    assert result.value == 41
    assert "age-adjusted" in result.interpretation
    assert "comorbidity score 37" in result.interpretation
    assert "age points 4" in result.interpretation


def test_charlson_single_1_point_condition():
    """Each 1-point condition adds exactly 1 point."""
    # Test myocardial infarction alone
    params = CharlsonParams(myocardial_infarction=True)
    result = calculate_charlson(params)
    assert result.value == 1

    # Test dementia alone
    params = CharlsonParams(dementia=True)
    result = calculate_charlson(params)
    assert result.value == 1


def test_charlson_single_2_point_condition():
    """Each 2-point condition adds exactly 2 points."""
    params = CharlsonParams(hemiplegia=True)
    result = calculate_charlson(params)
    assert result.value == 2

    params = CharlsonParams(leukemia=True)
    result = calculate_charlson(params)
    assert result.value == 2

    params = CharlsonParams(solid_tumor=True)
    result = calculate_charlson(params)
    assert result.value == 2


def test_charlson_single_3_point_condition():
    """Moderate/severe liver disease adds exactly 3 points."""
    params = CharlsonParams(moderate_severe_liver_disease=True)
    result = calculate_charlson(params)
    assert result.value == 3


def test_charlson_single_6_point_condition():
    """Each 6-point condition adds exactly 6 points."""
    params = CharlsonParams(metastatic_solid_tumor=True)
    result = calculate_charlson(params)
    assert result.value == 6

    params = CharlsonParams(aids=True)
    result = calculate_charlson(params)
    assert result.value == 6


def test_charlson_all_1_point_conditions():
    """All 10 one-point conditions = 10 points."""
    params = CharlsonParams(
        myocardial_infarction=True,
        congestive_heart_failure=True,
        peripheral_vascular_disease=True,
        cerebrovascular_disease=True,
        dementia=True,
        chronic_pulmonary_disease=True,
        connective_tissue_disease=True,
        peptic_ulcer_disease=True,
        mild_liver_disease=True,
        uncomplicated_diabetes=True,
    )
    result = calculate_charlson(params)
    assert result.value == 10


def test_charlson_all_2_point_conditions():
    """All 6 two-point conditions = 12 points."""
    params = CharlsonParams(
        hemiplegia=True,
        moderate_severe_renal_disease=True,
        diabetes_with_end_organ_damage=True,
        solid_tumor=True,
        leukemia=True,
        lymphoma=True,
    )
    result = calculate_charlson(params)
    assert result.value == 12


# ========================================================================
# Age adjustment tests
# ========================================================================


def test_charlson_age_below_50_no_points():
    """Age < 50 adds 0 age points."""
    params = CharlsonParams(age=30)
    result = calculate_charlson(params)
    assert result.value == 0
    assert "age points 0" in result.interpretation


def test_charlson_age_50_adds_1_point():
    """Age 50-59 adds 1 age point."""
    params = CharlsonParams(age=50)
    result = calculate_charlson(params)
    assert result.value == 1
    assert "age points 1" in result.interpretation


def test_charlson_age_59_adds_1_point():
    """Age 59 still adds 1 age point."""
    params = CharlsonParams(age=59)
    result = calculate_charlson(params)
    assert result.value == 1
    assert "age points 1" in result.interpretation


def test_charlson_age_60_adds_2_points():
    """Age 60-69 adds 2 age points."""
    params = CharlsonParams(age=60)
    result = calculate_charlson(params)
    assert result.value == 2
    assert "age points 2" in result.interpretation


def test_charlson_age_70_adds_3_points():
    """Age 70-79 adds 3 age points."""
    params = CharlsonParams(age=70)
    result = calculate_charlson(params)
    assert result.value == 3
    assert "age points 3" in result.interpretation


def test_charlson_age_80_adds_4_points():
    """Age >= 80 adds max 4 age points."""
    params = CharlsonParams(age=80)
    result = calculate_charlson(params)
    assert result.value == 4
    assert "age points 4" in result.interpretation


def test_charlson_age_99_adds_4_points():
    """Age 99 still capped at 4 age points."""
    params = CharlsonParams(age=99)
    result = calculate_charlson(params)
    assert result.value == 4
    assert "age points 4" in result.interpretation


def test_charlson_age_combined_with_comorbidities():
    """Comorbidity score + age points are additive.

    Example: MI (1) + diabetes (1) + age 65 (2 age points) = 4.
    """
    params = CharlsonParams(
        myocardial_infarction=True,
        uncomplicated_diabetes=True,
        age=65,
    )
    result = calculate_charlson(params)
    assert result.value == 4
    assert "comorbidity score 2" in result.interpretation
    assert "age points 2" in result.interpretation


# ========================================================================
# Risk strata boundary tests
# ========================================================================


def test_charlson_stratum_no_comorbidity_score_0():
    """Score 0 => 'No comorbidity burden'."""
    params = CharlsonParams()
    result = calculate_charlson(params)
    assert result.value == 0
    assert "No comorbidity burden" in result.interpretation


def test_charlson_stratum_low_score_1():
    """Score 1 => 'Low comorbidity burden'."""
    params = CharlsonParams(myocardial_infarction=True)
    result = calculate_charlson(params)
    assert result.value == 1
    assert "Low comorbidity burden" in result.interpretation


def test_charlson_stratum_low_score_2():
    """Score 2 => 'Low comorbidity burden'."""
    params = CharlsonParams(hemiplegia=True)
    result = calculate_charlson(params)
    assert result.value == 2
    assert "Low comorbidity burden" in result.interpretation


def test_charlson_stratum_moderate_score_3():
    """Score 3 => 'Moderate comorbidity burden'."""
    params = CharlsonParams(moderate_severe_liver_disease=True)
    result = calculate_charlson(params)
    assert result.value == 3
    assert "Moderate comorbidity burden" in result.interpretation


def test_charlson_stratum_moderate_score_4():
    """Score 4 => 'Moderate comorbidity burden'."""
    params = CharlsonParams(
        moderate_severe_liver_disease=True,
        myocardial_infarction=True,
    )
    result = calculate_charlson(params)
    assert result.value == 4
    assert "Moderate comorbidity burden" in result.interpretation


def test_charlson_stratum_high_score_5():
    """Score 5 => 'High comorbidity burden'."""
    params = CharlsonParams(
        moderate_severe_liver_disease=True,
        hemiplegia=True,
    )
    result = calculate_charlson(params)
    assert result.value == 5
    assert "High comorbidity burden" in result.interpretation


def test_charlson_stratum_high_score_6():
    """Score 6 (aids alone) => 'High comorbidity burden'."""
    params = CharlsonParams(aids=True)
    result = calculate_charlson(params)
    assert result.value == 6
    assert "High comorbidity burden" in result.interpretation


# ========================================================================
# 10-year survival formula verification
# ========================================================================


def test_charlson_10yr_survival_score_0():
    """Score 0: 10-year survival = 0.983^exp(0*0.9) = 0.983^1 = 98.3%."""
    params = CharlsonParams()
    result = calculate_charlson(params)
    expected = round(0.983 ** math.exp(0 * 0.9) * 100, 1)
    assert f"Estimated 10-year survival: {expected}%" in result.interpretation


def test_charlson_10yr_survival_score_2():
    """Score 2: verify survival formula calculation."""
    params = CharlsonParams(hemiplegia=True)
    result = calculate_charlson(params)
    expected = round(0.983 ** math.exp(2 * 0.9) * 100, 1)
    assert f"Estimated 10-year survival: {expected}%" in result.interpretation


def test_charlson_10yr_survival_score_5():
    """Score 5: verify survival formula calculation."""
    params = CharlsonParams(
        moderate_severe_liver_disease=True,
        hemiplegia=True,
    )
    result = calculate_charlson(params)
    expected = round(0.983 ** math.exp(5 * 0.9) * 100, 1)
    assert f"Estimated 10-year survival: {expected}%" in result.interpretation


# ========================================================================
# Evidence and FHIR verification
# ========================================================================


def test_charlson_evidence_doi():
    """Verify DOI is the original Charlson 1987 paper."""
    params = CharlsonParams()
    result = calculate_charlson(params)
    assert result.evidence.source_doi == "10.1016/0021-9681(87)90171-8"


def test_charlson_evidence_level():
    """Verify evidence level is set correctly."""
    params = CharlsonParams()
    result = calculate_charlson(params)
    assert result.evidence.level == "Derivation & Validation Study"


def test_charlson_evidence_description():
    """Verify evidence description references original paper."""
    params = CharlsonParams()
    result = calculate_charlson(params)
    assert "Charlson" in result.evidence.description
    assert "1987" in result.evidence.description


def test_charlson_fhir_code():
    """Verify FHIR code is None (no LOINC observation code exists for CCI score).

    LOINC 75618-9 "Comorbid condition" represents individual comorbid conditions
    (input data), not a composite comorbidity index (output concept). No LOINC
    observation code is currently registered for the Charlson Comorbidity Index.
    """
    params = CharlsonParams()
    result = calculate_charlson(params)
    assert result.fhir_code is None
    assert result.fhir_system is None
    assert result.fhir_display == "Charlson Comorbidity Index"


# ========================================================================
# No-age vs age-adjusted interpretation
# ========================================================================


def test_charlson_no_age_interpretation_label():
    """Without age, interpretation says 'Charlson Comorbidity Index is X'."""
    params = CharlsonParams(myocardial_infarction=True)
    result = calculate_charlson(params)
    assert "Charlson Comorbidity Index is 1" in result.interpretation
    assert "age-adjusted" not in result.interpretation


def test_charlson_with_age_interpretation_label():
    """With age, interpretation says 'age-adjusted' and breaks down score."""
    params = CharlsonParams(myocardial_infarction=True, age=65)
    result = calculate_charlson(params)
    assert "age-adjusted" in result.interpretation
    assert "comorbidity score 1" in result.interpretation
    assert "age points 2" in result.interpretation


# ========================================================================
# Cross-validation against original paper data
# ========================================================================


def test_charlson_original_paper_cohort1_score_0():
    """Original paper cohort 1: score 0 had 12% 1-year mortality.

    Our CCI score 0 should produce 98.3% 10-year survival,
    consistent with low comorbidity burden.
    """
    params = CharlsonParams()
    result = calculate_charlson(params)
    assert result.value == 0
    assert "No comorbidity burden" in result.interpretation


def test_charlson_original_paper_typical_patient():
    """Typical patient from original paper: 65-yr-old with MI and diabetes.

    Score: MI(1) + DM(1) + age 65(2) = 4 => Moderate comorbidity.
    """
    params = CharlsonParams(
        myocardial_infarction=True,
        uncomplicated_diabetes=True,
        age=65,
    )
    result = calculate_charlson(params)
    assert result.value == 4
    assert "Moderate comorbidity burden" in result.interpretation


def test_charlson_original_paper_high_burden():
    """High burden patient: 75-yr-old with CHF, COPD, moderate renal disease, and DM.

    Score: CHF(1) + COPD(1) + renal(2) + DM(1) + age 75(3) = 8 => High.
    """
    params = CharlsonParams(
        congestive_heart_failure=True,
        chronic_pulmonary_disease=True,
        moderate_severe_renal_disease=True,
        uncomplicated_diabetes=True,
        age=75,
    )
    result = calculate_charlson(params)
    assert result.value == 8
    assert "High comorbidity burden" in result.interpretation


def test_charlson_original_paper_metastatic_cancer():
    """Metastatic solid tumor alone = 6 => High comorbidity burden.

    Per original paper: score >= 5 had 85% 1-year mortality.
    """
    params = CharlsonParams(metastatic_solid_tumor=True)
    result = calculate_charlson(params)
    assert result.value == 6
    assert "High comorbidity burden" in result.interpretation

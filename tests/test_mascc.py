import pytest
from hypothesis import given, strategies as st, settings

from open_medicine.mcp.calculators.mascc import (
    calculate_mascc,
    MASCCParams,
    BurdenOfIllness,
    CancerType,
)


# ---------------------------------------------------------------------------
# Tier 1: Deterministic Unit Tests
# ---------------------------------------------------------------------------


def test_mascc_maximum_score():
    """Maximum score = 26: all favorable criteria present.
    Burden mild(5) + no hypotension(5) + no COPD(4) + solid tumor(4)
    + no dehydration(3) + outpatient(3) + age<60(2) = 26.
    """
    params = MASCCParams(
        burden_of_illness=BurdenOfIllness.NONE_OR_MILD,
        hypotension=False,
        active_copd=False,
        cancer_type=CancerType.SOLID_TUMOR,
        dehydration=False,
        outpatient_status=True,
        age=45,
    )
    result = calculate_mascc(params)
    assert result.value == 26
    assert "Low risk" in result.interpretation


def test_mascc_minimum_score():
    """Minimum score = 0: all unfavorable criteria present.
    Burden severe(0) + hypotension(0) + active COPD(0)
    + hematologic with prior fungal(0) + dehydration(0) + inpatient(0) + age>=60(0) = 0.
    """
    params = MASCCParams(
        burden_of_illness=BurdenOfIllness.SEVERE,
        hypotension=True,
        active_copd=True,
        cancer_type=CancerType.HEMATOLOGIC_PRIOR_FUNGAL,
        dehydration=True,
        outpatient_status=False,
        age=70,
    )
    result = calculate_mascc(params)
    assert result.value == 0
    assert "High risk" in result.interpretation


def test_mascc_low_risk_threshold_exact_21():
    """Score of exactly 21 is low risk (>= 21 threshold).
    Burden mild(5) + no hypotension(5) + no COPD(4) + solid tumor(4)
    + no dehydration(3) + inpatient(0) + age>=60(0) = 21.
    """
    params = MASCCParams(
        burden_of_illness=BurdenOfIllness.NONE_OR_MILD,
        hypotension=False,
        active_copd=False,
        cancer_type=CancerType.SOLID_TUMOR,
        dehydration=False,
        outpatient_status=False,
        age=65,
    )
    result = calculate_mascc(params)
    assert result.value == 21
    assert "Low risk" in result.interpretation
    assert "outpatient management" in result.interpretation.lower()


def test_mascc_high_risk_threshold_score_20():
    """Score of 20 is high risk (< 21 threshold).
    Burden mild(5) + no hypotension(5) + no COPD(4) + solid tumor(4)
    + dehydration(0) + inpatient(0) + age<60(2) = 20.
    """
    params = MASCCParams(
        burden_of_illness=BurdenOfIllness.NONE_OR_MILD,
        hypotension=False,
        active_copd=False,
        cancer_type=CancerType.SOLID_TUMOR,
        dehydration=True,
        outpatient_status=False,
        age=45,
    )
    result = calculate_mascc(params)
    assert result.value == 20
    assert "High risk" in result.interpretation
    assert "intravenous" in result.interpretation.lower()


def test_mascc_burden_moderate():
    """Moderate burden gives 3 points instead of 5.
    Moderate(3) + no hypotension(5) + no COPD(4) + solid tumor(4)
    + no dehydration(3) + outpatient(3) + age<60(2) = 24.
    """
    params = MASCCParams(
        burden_of_illness=BurdenOfIllness.MODERATE,
        hypotension=False,
        active_copd=False,
        cancer_type=CancerType.SOLID_TUMOR,
        dehydration=False,
        outpatient_status=True,
        age=50,
    )
    result = calculate_mascc(params)
    assert result.value == 24
    assert "Low risk" in result.interpretation


def test_mascc_burden_severe():
    """Severe burden gives 0 points.
    Severe(0) + no hypotension(5) + no COPD(4) + solid tumor(4)
    + no dehydration(3) + outpatient(3) + age<60(2) = 21.
    """
    params = MASCCParams(
        burden_of_illness=BurdenOfIllness.SEVERE,
        hypotension=False,
        active_copd=False,
        cancer_type=CancerType.SOLID_TUMOR,
        dehydration=False,
        outpatient_status=True,
        age=50,
    )
    result = calculate_mascc(params)
    assert result.value == 21
    assert "Low risk" in result.interpretation


def test_mascc_hypotension_subtracts_5():
    """Hypotension removes 5 points vs no hypotension.
    Mild(5) + hypotension(0) + no COPD(4) + solid tumor(4)
    + no dehydration(3) + outpatient(3) + age<60(2) = 21.
    """
    params = MASCCParams(
        burden_of_illness=BurdenOfIllness.NONE_OR_MILD,
        hypotension=True,
        active_copd=False,
        cancer_type=CancerType.SOLID_TUMOR,
        dehydration=False,
        outpatient_status=True,
        age=50,
    )
    result = calculate_mascc(params)
    assert result.value == 21


def test_mascc_active_copd():
    """Active COPD removes 4 points vs no COPD.
    Mild(5) + no hypotension(5) + COPD(0) + solid tumor(4)
    + no dehydration(3) + outpatient(3) + age<60(2) = 22.
    """
    params = MASCCParams(
        burden_of_illness=BurdenOfIllness.NONE_OR_MILD,
        hypotension=False,
        active_copd=True,
        cancer_type=CancerType.SOLID_TUMOR,
        dehydration=False,
        outpatient_status=True,
        age=50,
    )
    result = calculate_mascc(params)
    assert result.value == 22
    assert "Low risk" in result.interpretation


def test_mascc_hematologic_no_fungal():
    """Hematologic malignancy without prior fungal infection gives same 4 points as solid tumor.
    Mild(5) + no hypotension(5) + no COPD(4) + hematologic_no_fungal(4)
    + no dehydration(3) + outpatient(3) + age<60(2) = 26.
    """
    params = MASCCParams(
        burden_of_illness=BurdenOfIllness.NONE_OR_MILD,
        hypotension=False,
        active_copd=False,
        cancer_type=CancerType.HEMATOLOGIC_NO_FUNGAL,
        dehydration=False,
        outpatient_status=True,
        age=50,
    )
    result = calculate_mascc(params)
    assert result.value == 26


def test_mascc_hematologic_prior_fungal():
    """Hematologic malignancy with prior fungal infection gives 0 points.
    Mild(5) + no hypotension(5) + no COPD(4) + hematologic_prior_fungal(0)
    + no dehydration(3) + outpatient(3) + age<60(2) = 22.
    """
    params = MASCCParams(
        burden_of_illness=BurdenOfIllness.NONE_OR_MILD,
        hypotension=False,
        active_copd=False,
        cancer_type=CancerType.HEMATOLOGIC_PRIOR_FUNGAL,
        dehydration=False,
        outpatient_status=True,
        age=50,
    )
    result = calculate_mascc(params)
    assert result.value == 22


def test_mascc_dehydration():
    """Dehydration requiring IV fluids removes 3 points.
    Mild(5) + no hypotension(5) + no COPD(4) + solid tumor(4)
    + dehydration(0) + outpatient(3) + age<60(2) = 23.
    """
    params = MASCCParams(
        burden_of_illness=BurdenOfIllness.NONE_OR_MILD,
        hypotension=False,
        active_copd=False,
        cancer_type=CancerType.SOLID_TUMOR,
        dehydration=True,
        outpatient_status=True,
        age=50,
    )
    result = calculate_mascc(params)
    assert result.value == 23


def test_mascc_inpatient_status():
    """Inpatient status at fever onset gives 0 (vs outpatient +3).
    Mild(5) + no hypotension(5) + no COPD(4) + solid tumor(4)
    + no dehydration(3) + inpatient(0) + age<60(2) = 23.
    """
    params = MASCCParams(
        burden_of_illness=BurdenOfIllness.NONE_OR_MILD,
        hypotension=False,
        active_copd=False,
        cancer_type=CancerType.SOLID_TUMOR,
        dehydration=False,
        outpatient_status=False,
        age=50,
    )
    result = calculate_mascc(params)
    assert result.value == 23


def test_mascc_age_boundary_59():
    """Age 59 (< 60) gets +2 points."""
    params = MASCCParams(
        burden_of_illness=BurdenOfIllness.NONE_OR_MILD,
        hypotension=False,
        active_copd=False,
        cancer_type=CancerType.SOLID_TUMOR,
        dehydration=False,
        outpatient_status=True,
        age=59,
    )
    result = calculate_mascc(params)
    assert result.value == 26


def test_mascc_age_boundary_60():
    """Age 60 (>= 60) gets 0 points for age.
    Mild(5) + no hypotension(5) + no COPD(4) + solid tumor(4)
    + no dehydration(3) + outpatient(3) + age>=60(0) = 24.
    """
    params = MASCCParams(
        burden_of_illness=BurdenOfIllness.NONE_OR_MILD,
        hypotension=False,
        active_copd=False,
        cancer_type=CancerType.SOLID_TUMOR,
        dehydration=False,
        outpatient_status=True,
        age=60,
    )
    result = calculate_mascc(params)
    assert result.value == 24


def test_mascc_evidence_doi():
    """Verify the DOI matches the Klastersky et al. 2000 original paper."""
    params = MASCCParams(
        burden_of_illness=BurdenOfIllness.NONE_OR_MILD,
        hypotension=False,
        active_copd=False,
        cancer_type=CancerType.SOLID_TUMOR,
        dehydration=False,
        outpatient_status=True,
        age=50,
    )
    result = calculate_mascc(params)
    assert result.evidence.source_doi == "10.1200/JCO.2000.18.16.3038"
    assert "Klastersky" in result.evidence.description


def test_mascc_fhir_code():
    """Verify FHIR metadata is populated."""
    params = MASCCParams(
        burden_of_illness=BurdenOfIllness.NONE_OR_MILD,
        hypotension=False,
        active_copd=False,
        cancer_type=CancerType.SOLID_TUMOR,
        dehydration=False,
        outpatient_status=True,
        age=50,
    )
    result = calculate_mascc(params)
    assert result.fhir_code is None
    assert result.fhir_system is None
    assert result.fhir_display == "MASCC Risk Index score"


def test_mascc_clinical_scenario_high_risk_sick_elderly():
    """Elderly inpatient with hematologic malignancy, prior fungal, COPD,
    hypotension, dehydration, severe burden.
    All 0 points = score 0, high risk.
    """
    params = MASCCParams(
        burden_of_illness=BurdenOfIllness.SEVERE,
        hypotension=True,
        active_copd=True,
        cancer_type=CancerType.HEMATOLOGIC_PRIOR_FUNGAL,
        dehydration=True,
        outpatient_status=False,
        age=75,
    )
    result = calculate_mascc(params)
    assert result.value == 0
    assert "High risk" in result.interpretation
    assert "inpatient" in result.interpretation.lower()


def test_mascc_clinical_scenario_low_risk_young_outpatient():
    """Young outpatient with solid tumor, mild symptoms, no comorbidities.
    Max score = 26, low risk.
    """
    params = MASCCParams(
        burden_of_illness=BurdenOfIllness.NONE_OR_MILD,
        hypotension=False,
        active_copd=False,
        cancer_type=CancerType.SOLID_TUMOR,
        dehydration=False,
        outpatient_status=True,
        age=35,
    )
    result = calculate_mascc(params)
    assert result.value == 26
    assert "Low risk" in result.interpretation


def test_mascc_clinical_scenario_borderline():
    """Borderline case: moderate burden, elderly, inpatient, hematologic
    with prior fungal, but no hypotension, no COPD, no dehydration.
    Moderate(3) + no hypotension(5) + no COPD(4) + hematologic_prior_fungal(0)
    + no dehydration(3) + inpatient(0) + age>=60(0) = 15, high risk.
    """
    params = MASCCParams(
        burden_of_illness=BurdenOfIllness.MODERATE,
        hypotension=False,
        active_copd=False,
        cancer_type=CancerType.HEMATOLOGIC_PRIOR_FUNGAL,
        dehydration=False,
        outpatient_status=False,
        age=68,
    )
    result = calculate_mascc(params)
    assert result.value == 15
    assert "High risk" in result.interpretation


# ---------------------------------------------------------------------------
# Tier 2: Property-Based Fuzz Tests
# ---------------------------------------------------------------------------


burden_strategy = st.sampled_from(list(BurdenOfIllness))
cancer_strategy = st.sampled_from(list(CancerType))


@given(
    burden_of_illness=burden_strategy,
    hypotension=st.booleans(),
    active_copd=st.booleans(),
    cancer_type=cancer_strategy,
    dehydration=st.booleans(),
    outpatient_status=st.booleans(),
    age=st.integers(min_value=18, max_value=120),
)
@settings(max_examples=500)
def test_mascc_fuzz_valid_range(
    burden_of_illness,
    hypotension,
    active_copd,
    cancer_type,
    dehydration,
    outpatient_status,
    age,
):
    """Output is always within expected bounds for any valid input."""
    params = MASCCParams(
        burden_of_illness=burden_of_illness,
        hypotension=hypotension,
        active_copd=active_copd,
        cancer_type=cancer_type,
        dehydration=dehydration,
        outpatient_status=outpatient_status,
        age=age,
    )
    result = calculate_mascc(params)

    # Score is always an integer between 0 and 26
    assert isinstance(result.value, int)
    assert 0 <= result.value <= 26

    # Interpretation is never empty and matches score threshold
    assert result.interpretation
    if result.value >= 21:
        assert "Low risk" in result.interpretation
    else:
        assert "High risk" in result.interpretation

    # Evidence is always populated
    assert result.evidence.source_doi == "10.1200/JCO.2000.18.16.3038"
    assert result.evidence.description


@given(
    burden_of_illness=burden_strategy,
    hypotension=st.booleans(),
    active_copd=st.booleans(),
    cancer_type=cancer_strategy,
    dehydration=st.booleans(),
    outpatient_status=st.booleans(),
    age=st.integers(min_value=18, max_value=120),
)
@settings(max_examples=200)
def test_mascc_fuzz_score_decomposition(
    burden_of_illness,
    hypotension,
    active_copd,
    cancer_type,
    dehydration,
    outpatient_status,
    age,
):
    """Verify the score equals the sum of individual component contributions."""
    params = MASCCParams(
        burden_of_illness=burden_of_illness,
        hypotension=hypotension,
        active_copd=active_copd,
        cancer_type=cancer_type,
        dehydration=dehydration,
        outpatient_status=outpatient_status,
        age=age,
    )
    result = calculate_mascc(params)

    # Manually compute expected score
    expected = 0
    if burden_of_illness == BurdenOfIllness.NONE_OR_MILD:
        expected += 5
    elif burden_of_illness == BurdenOfIllness.MODERATE:
        expected += 3

    if not hypotension:
        expected += 5
    if not active_copd:
        expected += 4
    if cancer_type in (CancerType.SOLID_TUMOR, CancerType.HEMATOLOGIC_NO_FUNGAL):
        expected += 4
    if not dehydration:
        expected += 3
    if outpatient_status:
        expected += 3
    if age < 60:
        expected += 2

    assert result.value == expected

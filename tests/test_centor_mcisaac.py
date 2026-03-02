import pytest
from open_medicine.mcp.calculators.centor_mcisaac import (
    calculate_centor_mcisaac,
    CentorMcIsaacParams,
)


# ---------------------------------------------------------------------------
# Tier 1: Deterministic unit tests
# ---------------------------------------------------------------------------


def test_centor_mcisaac_minimum_score():
    """Oldest patient, no criteria met -> score = -1 (age >=45 gives -1)."""
    params = CentorMcIsaacParams(
        age=60,
        tonsillar_swelling_or_exudate=False,
        tender_anterior_cervical_lymphadenopathy=False,
        fever=False,
        absence_of_cough=False,
    )
    result = calculate_centor_mcisaac(params)
    assert result.value == -1
    assert "Very low risk" in result.interpretation
    assert "1-2.5%" in result.interpretation


def test_centor_mcisaac_maximum_score():
    """Young patient (<15), all 4 clinical criteria met -> score = 5."""
    params = CentorMcIsaacParams(
        age=10,
        tonsillar_swelling_or_exudate=True,
        tender_anterior_cervical_lymphadenopathy=True,
        fever=True,
        absence_of_cough=True,
    )
    result = calculate_centor_mcisaac(params)
    assert result.value == 5
    assert "High risk" in result.interpretation
    assert "51-53%" in result.interpretation


def test_centor_mcisaac_score_zero_no_criteria_mid_age():
    """Patient age 15-44, no criteria met -> score = 0."""
    params = CentorMcIsaacParams(
        age=30,
        tonsillar_swelling_or_exudate=False,
        tender_anterior_cervical_lymphadenopathy=False,
        fever=False,
        absence_of_cough=False,
    )
    result = calculate_centor_mcisaac(params)
    assert result.value == 0
    assert "Very low risk" in result.interpretation


def test_centor_mcisaac_score_1_low_risk():
    """Patient age 30, only fever -> score = 1 (low risk)."""
    params = CentorMcIsaacParams(
        age=30,
        tonsillar_swelling_or_exudate=False,
        tender_anterior_cervical_lymphadenopathy=False,
        fever=True,
        absence_of_cough=False,
    )
    result = calculate_centor_mcisaac(params)
    assert result.value == 1
    assert "Low risk" in result.interpretation
    assert "5-10%" in result.interpretation


def test_centor_mcisaac_score_2_moderate_risk():
    """Patient age 30, fever + absence of cough -> score = 2 (moderate risk)."""
    params = CentorMcIsaacParams(
        age=30,
        tonsillar_swelling_or_exudate=False,
        tender_anterior_cervical_lymphadenopathy=False,
        fever=True,
        absence_of_cough=True,
    )
    result = calculate_centor_mcisaac(params)
    assert result.value == 2
    assert "Moderate risk" in result.interpretation
    assert "11-17%" in result.interpretation
    assert "RADT" in result.interpretation


def test_centor_mcisaac_score_3_moderately_high_risk():
    """Patient age 30, fever + absence of cough + tonsillar exudate -> score = 3."""
    params = CentorMcIsaacParams(
        age=30,
        tonsillar_swelling_or_exudate=True,
        tender_anterior_cervical_lymphadenopathy=False,
        fever=True,
        absence_of_cough=True,
    )
    result = calculate_centor_mcisaac(params)
    assert result.value == 3
    assert "Moderately high risk" in result.interpretation
    assert "28-35%" in result.interpretation
    assert "RADT" in result.interpretation


def test_centor_mcisaac_score_4_high_risk():
    """Patient age 30, all 4 clinical criteria met -> score = 4 (high risk)."""
    params = CentorMcIsaacParams(
        age=30,
        tonsillar_swelling_or_exudate=True,
        tender_anterior_cervical_lymphadenopathy=True,
        fever=True,
        absence_of_cough=True,
    )
    result = calculate_centor_mcisaac(params)
    assert result.value == 4
    assert "High risk" in result.interpretation
    assert "51-53%" in result.interpretation


# ---------------------------------------------------------------------------
# Age validation tests (age < 3 excluded from derivation study)
# ---------------------------------------------------------------------------


def test_centor_mcisaac_age_under_3_returns_none():
    """Age < 3 is outside the validated range (McIsaac 1998 included ages 3-76)."""
    params = CentorMcIsaacParams(
        age=2,
        tonsillar_swelling_or_exudate=True,
        tender_anterior_cervical_lymphadenopathy=True,
        fever=True,
        absence_of_cough=True,
    )
    result = calculate_centor_mcisaac(params)
    assert result.value is None
    assert "only validated" in result.interpretation
    assert ">= 3" in result.interpretation


def test_centor_mcisaac_age_0_returns_none():
    """Age 0 (neonate) should return value=None."""
    params = CentorMcIsaacParams(
        age=0,
        tonsillar_swelling_or_exudate=False,
        tender_anterior_cervical_lymphadenopathy=False,
        fever=False,
        absence_of_cough=False,
    )
    result = calculate_centor_mcisaac(params)
    assert result.value is None
    assert "only validated" in result.interpretation


def test_centor_mcisaac_age_3_is_valid():
    """Age 3 is the minimum validated age; should return a score, not None."""
    params = CentorMcIsaacParams(
        age=3,
        tonsillar_swelling_or_exudate=False,
        tender_anterior_cervical_lymphadenopathy=False,
        fever=False,
        absence_of_cough=False,
    )
    result = calculate_centor_mcisaac(params)
    # Age 3 is < 15, so gets +1 age point; 0 clinical + 1 age = 1
    assert result.value == 1
    assert result.value is not None


def test_centor_mcisaac_age_under_3_evidence_preserved():
    """Even when age is out of range, evidence and PMID should be present."""
    params = CentorMcIsaacParams(
        age=1,
        tonsillar_swelling_or_exudate=False,
        tender_anterior_cervical_lymphadenopathy=False,
        fever=False,
        absence_of_cough=False,
    )
    result = calculate_centor_mcisaac(params)
    assert result.evidence.source_doi == "PMID:9475915"
    assert "McIsaac" in result.evidence.description


# ---------------------------------------------------------------------------
# Age boundary tests
# ---------------------------------------------------------------------------


def test_centor_mcisaac_age_14_gets_plus_one():
    """Age 14 (< 15) should give +1 age point."""
    params = CentorMcIsaacParams(
        age=14,
        tonsillar_swelling_or_exudate=False,
        tender_anterior_cervical_lymphadenopathy=False,
        fever=False,
        absence_of_cough=False,
    )
    result = calculate_centor_mcisaac(params)
    # 0 clinical + 1 age = 1
    assert result.value == 1


def test_centor_mcisaac_age_15_gets_zero():
    """Age 15 should give 0 age points."""
    params = CentorMcIsaacParams(
        age=15,
        tonsillar_swelling_or_exudate=False,
        tender_anterior_cervical_lymphadenopathy=False,
        fever=False,
        absence_of_cough=False,
    )
    result = calculate_centor_mcisaac(params)
    # 0 clinical + 0 age = 0
    assert result.value == 0


def test_centor_mcisaac_age_44_gets_zero():
    """Age 44 (still 15-44 range) should give 0 age points."""
    params = CentorMcIsaacParams(
        age=44,
        tonsillar_swelling_or_exudate=False,
        tender_anterior_cervical_lymphadenopathy=False,
        fever=False,
        absence_of_cough=False,
    )
    result = calculate_centor_mcisaac(params)
    assert result.value == 0


def test_centor_mcisaac_age_45_gets_minus_one():
    """Age 45 (>= 45) should give -1 age point."""
    params = CentorMcIsaacParams(
        age=45,
        tonsillar_swelling_or_exudate=False,
        tender_anterior_cervical_lymphadenopathy=False,
        fever=False,
        absence_of_cough=False,
    )
    result = calculate_centor_mcisaac(params)
    # 0 clinical + (-1) age = -1
    assert result.value == -1


# ---------------------------------------------------------------------------
# Individual criterion contribution tests
# ---------------------------------------------------------------------------


def test_centor_mcisaac_tonsillar_only():
    """Only tonsillar exudate positive, mid-age -> score = 1."""
    params = CentorMcIsaacParams(
        age=30,
        tonsillar_swelling_or_exudate=True,
        tender_anterior_cervical_lymphadenopathy=False,
        fever=False,
        absence_of_cough=False,
    )
    result = calculate_centor_mcisaac(params)
    assert result.value == 1


def test_centor_mcisaac_lymphadenopathy_only():
    """Only cervical lymphadenopathy positive, mid-age -> score = 1."""
    params = CentorMcIsaacParams(
        age=30,
        tonsillar_swelling_or_exudate=False,
        tender_anterior_cervical_lymphadenopathy=True,
        fever=False,
        absence_of_cough=False,
    )
    result = calculate_centor_mcisaac(params)
    assert result.value == 1


def test_centor_mcisaac_absence_of_cough_only():
    """Only absence of cough positive, mid-age -> score = 1."""
    params = CentorMcIsaacParams(
        age=30,
        tonsillar_swelling_or_exudate=False,
        tender_anterior_cervical_lymphadenopathy=False,
        fever=False,
        absence_of_cough=True,
    )
    result = calculate_centor_mcisaac(params)
    assert result.value == 1


# ---------------------------------------------------------------------------
# Age + clinical interaction edge cases
# ---------------------------------------------------------------------------


def test_centor_mcisaac_elderly_all_criteria():
    """Elderly patient (>=45), all clinical criteria -> score = 3 (4 clinical - 1 age)."""
    params = CentorMcIsaacParams(
        age=70,
        tonsillar_swelling_or_exudate=True,
        tender_anterior_cervical_lymphadenopathy=True,
        fever=True,
        absence_of_cough=True,
    )
    result = calculate_centor_mcisaac(params)
    assert result.value == 3
    assert "Moderately high risk" in result.interpretation


def test_centor_mcisaac_child_no_criteria():
    """Young child (<15), no clinical criteria -> score = 1 (0 clinical + 1 age)."""
    params = CentorMcIsaacParams(
        age=5,
        tonsillar_swelling_or_exudate=False,
        tender_anterior_cervical_lymphadenopathy=False,
        fever=False,
        absence_of_cough=False,
    )
    result = calculate_centor_mcisaac(params)
    assert result.value == 1
    assert "Low risk" in result.interpretation


# ---------------------------------------------------------------------------
# Evidence and FHIR metadata tests
# ---------------------------------------------------------------------------


def test_centor_mcisaac_evidence_doi():
    """Verify the source reference matches the McIsaac 1998 CMAJ paper (PMID:9475915).

    The original DOI 10.1016/S0196-0644(98)70224-X was incorrect -- it belongs
    to Annals of Emergency Medicine (Elsevier), not CMAJ. The McIsaac 1998 CMAJ
    paper does not have a DOI assigned; PMID is used instead.
    """
    params = CentorMcIsaacParams(
        age=30,
        tonsillar_swelling_or_exudate=False,
        tender_anterior_cervical_lymphadenopathy=False,
        fever=False,
        absence_of_cough=False,
    )
    result = calculate_centor_mcisaac(params)
    assert result.evidence.source_doi == "PMID:9475915"
    assert "McIsaac" in result.evidence.description
    assert "CMAJ" in result.evidence.description
    assert result.evidence.level == "Derivation & Validation Study"


def test_centor_mcisaac_fhir_code():
    """Verify FHIR metadata documents absence of a proper LOINC observation code.

    No specific LOINC observation code exists for the Centor/McIsaac score.
    LP419468-2 was previously used but is a LOINC Part code (LP prefix), not
    a proper observation code. fhir_code and fhir_system are set to None;
    fhir_display still contains the human-readable score name.
    """
    params = CentorMcIsaacParams(
        age=30,
        tonsillar_swelling_or_exudate=False,
        tender_anterior_cervical_lymphadenopathy=False,
        fever=False,
        absence_of_cough=False,
    )
    result = calculate_centor_mcisaac(params)
    assert result.fhir_code is None
    assert result.fhir_system is None
    assert "Centor" in result.fhir_display or "McIsaac" in result.fhir_display


def test_centor_mcisaac_interpretation_contains_score():
    """Every interpretation string should include the numeric score."""
    for age in [10, 30, 60]:
        for fever in [True, False]:
            params = CentorMcIsaacParams(
                age=age,
                tonsillar_swelling_or_exudate=False,
                tender_anterior_cervical_lymphadenopathy=False,
                fever=fever,
                absence_of_cough=False,
            )
            result = calculate_centor_mcisaac(params)
            assert str(result.value) in result.interpretation


# ---------------------------------------------------------------------------
# Cross-validation: published risk strata from McIsaac 1998 / MDCalc
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "age, tonsil, lymph, fever, no_cough, expected_score",
    [
        # Score -1: elderly, nothing present
        (50, False, False, False, False, -1),
        # Score 0: mid-age adult, nothing present
        (25, False, False, False, False, 0),
        # Score 0: elderly with one criterion (4 clinical - 1 age offset = 0)
        (50, True, False, False, False, 0),
        # Score 1: child with no clinical criteria
        (8, False, False, False, False, 1),
        # Score 2: mid-age, 2 criteria
        (30, True, True, False, False, 2),
        # Score 3: mid-age, 3 criteria
        (30, True, True, True, False, 3),
        # Score 4: mid-age, all 4 criteria
        (30, True, True, True, True, 4),
        # Score 5: child, all 4 criteria
        (10, True, True, True, True, 5),
        # Score 3: elderly, all 4 clinical (4 - 1 = 3)
        (55, True, True, True, True, 3),
        # Score 2: child, 1 clinical criterion (1 + 1 age = 2)
        (12, True, False, False, False, 2),
    ],
)
def test_centor_mcisaac_parametrized(age, tonsil, lymph, fever, no_cough, expected_score):
    """Parametrized test verifying score computation across age groups."""
    params = CentorMcIsaacParams(
        age=age,
        tonsillar_swelling_or_exudate=tonsil,
        tender_anterior_cervical_lymphadenopathy=lymph,
        fever=fever,
        absence_of_cough=no_cough,
    )
    result = calculate_centor_mcisaac(params)
    assert result.value == expected_score

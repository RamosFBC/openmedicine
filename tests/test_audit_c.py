import pytest
from open_medicine.mcp.calculators.audit_c import calculate_audit_c, AUDITCParams


def _make_params(**kwargs):
    """Helper to create AUDITCParams with defaults for all items at 0 (non-drinker, male)."""
    defaults = dict(
        frequency=0,
        typical_quantity=0,
        binge_frequency=0,
        is_male=True,
    )
    defaults.update(kwargs)
    return AUDITCParams(**defaults)


# ---------------------------------------------------------------------------
# Minimum and maximum score tests
# ---------------------------------------------------------------------------


def test_audit_c_minimum_score():
    """All items scored 0 = total 0, non-drinker, negative screen."""
    result = calculate_audit_c(_make_params())
    assert result.value == 0
    assert "non-drinker" in result.interpretation.lower()
    assert "Negative screen" in result.interpretation


def test_audit_c_maximum_score_male():
    """All items scored 4 = total 12, male, positive screen (severe)."""
    params = AUDITCParams(
        frequency=4,
        typical_quantity=4,
        binge_frequency=4,
        is_male=True,
    )
    result = calculate_audit_c(params)
    assert result.value == 12
    assert "Positive screen" in result.interpretation
    assert "likely alcohol dependence" in result.interpretation.lower() or "severe" in result.interpretation.lower()


def test_audit_c_maximum_score_female():
    """All items scored 4 = total 12, female, positive screen (severe)."""
    params = AUDITCParams(
        frequency=4,
        typical_quantity=4,
        binge_frequency=4,
        is_male=False,
    )
    result = calculate_audit_c(params)
    assert result.value == 12
    assert "Positive screen" in result.interpretation


# ---------------------------------------------------------------------------
# Sex-specific threshold boundary tests
# ---------------------------------------------------------------------------


def test_audit_c_male_below_threshold():
    """Male with score 3: below positive threshold (>= 4), negative screen."""
    result = calculate_audit_c(_make_params(
        frequency=1,
        typical_quantity=1,
        binge_frequency=1,
        is_male=True,
    ))
    assert result.value == 3
    assert "Negative screen" in result.interpretation
    assert ">= 4" in result.interpretation


def test_audit_c_male_at_threshold():
    """Male with score 4: at positive threshold, positive screen."""
    result = calculate_audit_c(_make_params(
        frequency=2,
        typical_quantity=1,
        binge_frequency=1,
        is_male=True,
    ))
    assert result.value == 4
    assert "Positive screen" in result.interpretation
    assert "hazardous drinking" in result.interpretation.lower()


def test_audit_c_female_below_threshold():
    """Female with score 2: below positive threshold (>= 3), negative screen."""
    result = calculate_audit_c(_make_params(
        frequency=1,
        typical_quantity=1,
        binge_frequency=0,
        is_male=False,
    ))
    assert result.value == 2
    assert "Negative screen" in result.interpretation
    assert ">= 3" in result.interpretation


def test_audit_c_female_at_threshold():
    """Female with score 3: at positive threshold, positive screen."""
    result = calculate_audit_c(_make_params(
        frequency=1,
        typical_quantity=1,
        binge_frequency=1,
        is_male=False,
    ))
    assert result.value == 3
    assert "Positive screen" in result.interpretation
    assert "hazardous drinking" in result.interpretation.lower()


def test_audit_c_female_score_1_negative():
    """Female with score 1: negative screen."""
    result = calculate_audit_c(_make_params(
        frequency=1,
        typical_quantity=0,
        binge_frequency=0,
        is_male=False,
    ))
    assert result.value == 1
    assert "Negative screen" in result.interpretation
    assert "low-risk" in result.interpretation.lower()


def test_audit_c_male_score_1_negative():
    """Male with score 1: negative screen (low-risk)."""
    result = calculate_audit_c(_make_params(
        frequency=1,
        typical_quantity=0,
        binge_frequency=0,
        is_male=True,
    ))
    assert result.value == 1
    assert "Negative screen" in result.interpretation


# ---------------------------------------------------------------------------
# Score stratum boundary tests
# ---------------------------------------------------------------------------


def test_audit_c_hazardous_range_lower():
    """Score at positive threshold (male=4) but <= 7: hazardous drinking."""
    result = calculate_audit_c(_make_params(
        frequency=2,
        typical_quantity=1,
        binge_frequency=1,
        is_male=True,
    ))
    assert result.value == 4
    assert "hazardous drinking" in result.interpretation.lower()
    assert "Brief intervention" in result.interpretation


def test_audit_c_hazardous_range_upper():
    """Score 7: still in hazardous drinking range."""
    result = calculate_audit_c(_make_params(
        frequency=3,
        typical_quantity=2,
        binge_frequency=2,
        is_male=True,
    ))
    assert result.value == 7
    assert "hazardous drinking" in result.interpretation.lower()


def test_audit_c_severe_range_lower():
    """Score 8: crosses into severe/likely dependence range."""
    result = calculate_audit_c(_make_params(
        frequency=3,
        typical_quantity=3,
        binge_frequency=2,
        is_male=True,
    ))
    assert result.value == 8
    assert "likely alcohol dependence" in result.interpretation.lower() or "severe" in result.interpretation.lower()
    assert "diagnostic evaluation" in result.interpretation.lower()


def test_audit_c_severe_range_mid():
    """Score 10: severe range."""
    result = calculate_audit_c(_make_params(
        frequency=4,
        typical_quantity=3,
        binge_frequency=3,
        is_male=True,
    ))
    assert result.value == 10
    assert "Positive screen" in result.interpretation


# ---------------------------------------------------------------------------
# Sex-specific interpretation labels
# ---------------------------------------------------------------------------


def test_audit_c_interpretation_includes_sex_male():
    """Interpretation mentions 'male' when is_male=True."""
    result = calculate_audit_c(_make_params(is_male=True))
    assert "male" in result.interpretation.lower()


def test_audit_c_interpretation_includes_sex_female():
    """Interpretation mentions 'female' when is_male=False."""
    result = calculate_audit_c(_make_params(is_male=False))
    assert "female" in result.interpretation.lower()


# ---------------------------------------------------------------------------
# Score arithmetic verification
# ---------------------------------------------------------------------------


def test_audit_c_score_is_sum_of_items():
    """Score must always equal the sum of the three item scores."""
    params = AUDITCParams(
        frequency=2,
        typical_quantity=3,
        binge_frequency=1,
        is_male=True,
    )
    result = calculate_audit_c(params)
    assert result.value == 2 + 3 + 1  # = 6


def test_audit_c_each_item_contributes():
    """Verify that each item individually contributes its value."""
    # Only frequency=4, others 0
    r1 = calculate_audit_c(_make_params(frequency=4))
    assert r1.value == 4

    # Only typical_quantity=4, others 0
    r2 = calculate_audit_c(_make_params(typical_quantity=4))
    assert r2.value == 4

    # Only binge_frequency=4, others 0
    r3 = calculate_audit_c(_make_params(binge_frequency=4))
    assert r3.value == 4


# ---------------------------------------------------------------------------
# Evidence and FHIR metadata tests
# ---------------------------------------------------------------------------


def test_audit_c_evidence_doi():
    """Verify DOI matches Bush et al. 1998."""
    result = calculate_audit_c(_make_params())
    assert result.evidence.source_doi == "10.1001/archinte.158.16.1789"


def test_audit_c_evidence_level():
    """Verify evidence level is Derivation & Validation Study."""
    result = calculate_audit_c(_make_params())
    assert result.evidence.level == "Derivation & Validation Study"


def test_audit_c_evidence_description():
    """Verify evidence description references Bush et al."""
    result = calculate_audit_c(_make_params())
    assert "Bush" in result.evidence.description
    assert "AUDIT" in result.evidence.description


def test_audit_c_fhir_code():
    """Verify FHIR code is LOINC 75626-2 for AUDIT-C total score."""
    result = calculate_audit_c(_make_params())
    assert result.fhir_code == "75626-2"
    assert result.fhir_system == "http://loinc.org"
    assert "AUDIT-C" in result.fhir_display


# ---------------------------------------------------------------------------
# Interpretation always contains numeric score
# ---------------------------------------------------------------------------


def test_audit_c_interpretation_contains_score():
    """Interpretation always includes the numeric score value."""
    for freq in range(5):
        for qty in range(5):
            for binge in range(5):
                total = freq + qty + binge
                params = AUDITCParams(
                    frequency=freq,
                    typical_quantity=qty,
                    binge_frequency=binge,
                    is_male=True,
                )
                result = calculate_audit_c(params)
                assert f"AUDIT-C score is {total}" in result.interpretation


# ---------------------------------------------------------------------------
# Pydantic validation tests
# ---------------------------------------------------------------------------


def test_audit_c_rejects_out_of_range_high():
    """Items greater than 4 should be rejected by Pydantic validation."""
    with pytest.raises(Exception):
        AUDITCParams(
            frequency=5,
            typical_quantity=0,
            binge_frequency=0,
            is_male=True,
        )


def test_audit_c_rejects_out_of_range_low():
    """Items less than 0 should be rejected by Pydantic validation."""
    with pytest.raises(Exception):
        AUDITCParams(
            frequency=-1,
            typical_quantity=0,
            binge_frequency=0,
            is_male=True,
        )


def test_audit_c_rejects_missing_is_male():
    """is_male is required and must not be omitted."""
    with pytest.raises(Exception):
        AUDITCParams(
            frequency=1,
            typical_quantity=1,
            binge_frequency=1,
        )


# ---------------------------------------------------------------------------
# Cross-validation clinical scenarios
# ---------------------------------------------------------------------------


def test_audit_c_clinical_scenario_non_drinker():
    """Non-drinker: never drinks, score 0."""
    result = calculate_audit_c(AUDITCParams(
        frequency=0,  # Never
        typical_quantity=0,  # 1-2 (N/A since never drinks)
        binge_frequency=0,  # Never
        is_male=True,
    ))
    assert result.value == 0
    assert "non-drinker" in result.interpretation.lower()


def test_audit_c_clinical_scenario_moderate_male_drinker():
    """Male: monthly or less, 1-2 drinks, never binges. Score 1, negative."""
    result = calculate_audit_c(AUDITCParams(
        frequency=1,  # Monthly or less
        typical_quantity=0,  # 1-2
        binge_frequency=0,  # Never
        is_male=True,
    ))
    assert result.value == 1
    assert "Negative screen" in result.interpretation


def test_audit_c_clinical_scenario_moderate_female_drinker():
    """Female: 2-4 times/month, 3-4 drinks, never binges. Score 3, positive for female."""
    result = calculate_audit_c(AUDITCParams(
        frequency=2,  # 2-4 times per month
        typical_quantity=1,  # 3-4
        binge_frequency=0,  # Never
        is_male=False,
    ))
    assert result.value == 3
    assert "Positive screen" in result.interpretation


def test_audit_c_clinical_scenario_heavy_drinker():
    """Heavy drinker: 4+ times/week, 7-9 drinks, weekly binge. Score 10, severe."""
    result = calculate_audit_c(AUDITCParams(
        frequency=4,  # 4+ times per week
        typical_quantity=3,  # 7-9
        binge_frequency=3,  # Weekly
        is_male=True,
    ))
    assert result.value == 10
    assert "Positive screen" in result.interpretation
    assert "diagnostic evaluation" in result.interpretation.lower() or "dependence" in result.interpretation.lower()


def test_audit_c_clinical_scenario_daily_binge():
    """Daily binge drinker: maximum score 12."""
    result = calculate_audit_c(AUDITCParams(
        frequency=4,  # 4+ times per week
        typical_quantity=4,  # 10+
        binge_frequency=4,  # Daily or almost daily
        is_male=False,
    ))
    assert result.value == 12
    assert "Positive screen" in result.interpretation

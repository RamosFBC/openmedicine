import pytest
from hypothesis import given, strategies as st, settings
from open_medicine.mcp.calculators.crb65 import calculate_crb65, CRB65Params


# ---------------------------------------------------------------------------
# Tier 1: Deterministic Unit Tests
# ---------------------------------------------------------------------------

def test_crb65_minimum_score():
    """All criteria absent -- score 0, low risk, outpatient."""
    params = CRB65Params(
        confusion=False,
        respiratory_rate=18,
        systolic_bp=120,
        diastolic_bp=80,
        age=40,
    )
    result = calculate_crb65(params)
    assert result.value == 0
    assert "Low risk" in result.interpretation
    assert "home treatment" in result.interpretation.lower()


def test_crb65_maximum_score():
    """All criteria present -- score 4, high risk, urgent admission."""
    params = CRB65Params(
        confusion=True,
        respiratory_rate=35,
        systolic_bp=80,
        diastolic_bp=50,
        age=75,
    )
    result = calculate_crb65(params)
    assert result.value == 4
    assert "High risk" in result.interpretation
    assert "urgent" in result.interpretation.lower()


def test_crb65_score_1_intermediate():
    """Single criterion (confusion only) -- score 1, intermediate risk."""
    params = CRB65Params(
        confusion=True,
        respiratory_rate=18,
        systolic_bp=120,
        diastolic_bp=80,
        age=40,
    )
    result = calculate_crb65(params)
    assert result.value == 1
    assert "Intermediate risk" in result.interpretation


def test_crb65_score_2_intermediate():
    """Two criteria (confusion + age) -- score 2, intermediate risk."""
    params = CRB65Params(
        confusion=True,
        respiratory_rate=20,
        systolic_bp=110,
        diastolic_bp=70,
        age=70,
    )
    result = calculate_crb65(params)
    assert result.value == 2
    assert "Intermediate risk" in result.interpretation


def test_crb65_score_3_high_risk():
    """Three criteria -- score 3, high risk."""
    params = CRB65Params(
        confusion=True,
        respiratory_rate=32,
        systolic_bp=85,
        diastolic_bp=55,
        age=50,
    )
    result = calculate_crb65(params)
    assert result.value == 3
    assert "High risk" in result.interpretation


def test_crb65_respiratory_rate_threshold_below():
    """RR = 29 (just below threshold) should NOT trigger the R criterion."""
    params = CRB65Params(
        confusion=False,
        respiratory_rate=29,
        systolic_bp=120,
        diastolic_bp=80,
        age=40,
    )
    result = calculate_crb65(params)
    assert result.value == 0


def test_crb65_respiratory_rate_threshold_at():
    """RR = 30 (at threshold) should trigger the R criterion."""
    params = CRB65Params(
        confusion=False,
        respiratory_rate=30,
        systolic_bp=120,
        diastolic_bp=80,
        age=40,
    )
    result = calculate_crb65(params)
    assert result.value == 1


def test_crb65_systolic_bp_threshold_below():
    """Systolic BP = 89 (< 90) should trigger the B criterion."""
    params = CRB65Params(
        confusion=False,
        respiratory_rate=18,
        systolic_bp=89,
        diastolic_bp=80,
        age=40,
    )
    result = calculate_crb65(params)
    assert result.value == 1


def test_crb65_systolic_bp_threshold_at():
    """Systolic BP = 90 (not < 90) should NOT trigger the B criterion when diastolic is normal."""
    params = CRB65Params(
        confusion=False,
        respiratory_rate=18,
        systolic_bp=90,
        diastolic_bp=80,
        age=40,
    )
    result = calculate_crb65(params)
    assert result.value == 0


def test_crb65_diastolic_bp_threshold_at():
    """Diastolic BP = 60 (<= 60) should trigger the B criterion."""
    params = CRB65Params(
        confusion=False,
        respiratory_rate=18,
        systolic_bp=120,
        diastolic_bp=60,
        age=40,
    )
    result = calculate_crb65(params)
    assert result.value == 1


def test_crb65_diastolic_bp_threshold_above():
    """Diastolic BP = 61 (> 60) should NOT trigger the B criterion when systolic is normal."""
    params = CRB65Params(
        confusion=False,
        respiratory_rate=18,
        systolic_bp=120,
        diastolic_bp=61,
        age=40,
    )
    result = calculate_crb65(params)
    assert result.value == 0


def test_crb65_age_threshold_below():
    """Age = 64 (< 65) should NOT trigger the 65 criterion."""
    params = CRB65Params(
        confusion=False,
        respiratory_rate=18,
        systolic_bp=120,
        diastolic_bp=80,
        age=64,
    )
    result = calculate_crb65(params)
    assert result.value == 0


def test_crb65_age_threshold_at():
    """Age = 65 (>= 65) should trigger the 65 criterion."""
    params = CRB65Params(
        confusion=False,
        respiratory_rate=18,
        systolic_bp=120,
        diastolic_bp=80,
        age=65,
    )
    result = calculate_crb65(params)
    assert result.value == 1


def test_crb65_bp_both_low():
    """Both systolic and diastolic low -- BP criterion only counts once."""
    params = CRB65Params(
        confusion=False,
        respiratory_rate=18,
        systolic_bp=80,
        diastolic_bp=50,
        age=40,
    )
    result = calculate_crb65(params)
    assert result.value == 1  # Only 1 point for BP, not 2


def test_crb65_evidence_doi():
    """Verify the DOI matches the Bauer 2006 validation study."""
    params = CRB65Params(
        confusion=False,
        respiratory_rate=18,
        systolic_bp=120,
        diastolic_bp=80,
        age=40,
    )
    result = calculate_crb65(params)
    assert result.evidence.source_doi == "10.1111/j.1365-2796.2006.01657.x"
    assert "Bauer" in result.evidence.description


def test_crb65_fhir_code():
    """Verify FHIR code is present and system is LOINC."""
    params = CRB65Params(
        confusion=False,
        respiratory_rate=18,
        systolic_bp=120,
        diastolic_bp=80,
        age=40,
    )
    result = calculate_crb65(params)
    assert result.fhir_code == "LP419467-4"
    assert result.fhir_system == "http://loinc.org"
    assert result.fhir_display == "CRB-65 score"


def test_crb65_interpretation_includes_score():
    """Interpretation string must include the numeric score value."""
    for expected_score in range(5):
        # Build params to produce each score
        params = CRB65Params(
            confusion=(expected_score >= 1),
            respiratory_rate=35 if expected_score >= 2 else 18,
            systolic_bp=80 if expected_score >= 3 else 120,
            diastolic_bp=80,
            age=75 if expected_score >= 4 else 40,
        )
        result = calculate_crb65(params)
        assert result.value == expected_score
        assert str(expected_score) in result.interpretation


def test_crb65_each_criterion_individually():
    """Each criterion alone should produce a score of 1."""
    # Confusion only
    r = calculate_crb65(CRB65Params(confusion=True, respiratory_rate=18, systolic_bp=120, diastolic_bp=80, age=40))
    assert r.value == 1

    # Respiratory rate only
    r = calculate_crb65(CRB65Params(confusion=False, respiratory_rate=30, systolic_bp=120, diastolic_bp=80, age=40))
    assert r.value == 1

    # Blood pressure (systolic) only
    r = calculate_crb65(CRB65Params(confusion=False, respiratory_rate=18, systolic_bp=89, diastolic_bp=80, age=40))
    assert r.value == 1

    # Blood pressure (diastolic) only
    r = calculate_crb65(CRB65Params(confusion=False, respiratory_rate=18, systolic_bp=120, diastolic_bp=60, age=40))
    assert r.value == 1

    # Age only
    r = calculate_crb65(CRB65Params(confusion=False, respiratory_rate=18, systolic_bp=120, diastolic_bp=80, age=65))
    assert r.value == 1


# ---------------------------------------------------------------------------
# Tier 2: Property-Based Fuzz Tests
# ---------------------------------------------------------------------------

@pytest.mark.slow
@given(
    confusion=st.booleans(),
    respiratory_rate=st.integers(min_value=8, max_value=60),
    systolic_bp=st.integers(min_value=40, max_value=250),
    diastolic_bp=st.integers(min_value=20, max_value=150),
    age=st.integers(min_value=18, max_value=110),
)
@settings(max_examples=500)
def test_crb65_fuzz_valid_range(confusion, respiratory_rate, systolic_bp, diastolic_bp, age):
    """Output is always within expected bounds for any valid input."""
    params = CRB65Params(
        confusion=confusion,
        respiratory_rate=respiratory_rate,
        systolic_bp=systolic_bp,
        diastolic_bp=diastolic_bp,
        age=age,
    )
    result = calculate_crb65(params)

    # Score must be an integer in [0, 4]
    assert isinstance(result.value, int)
    assert 0 <= result.value <= 4

    # Interpretation must not be empty
    assert result.interpretation
    assert len(result.interpretation) > 0

    # Evidence must be populated
    assert result.evidence.source_doi
    assert result.evidence.description


@pytest.mark.slow
@given(
    confusion=st.booleans(),
    respiratory_rate=st.integers(min_value=8, max_value=60),
    systolic_bp=st.integers(min_value=40, max_value=250),
    diastolic_bp=st.integers(min_value=20, max_value=150),
    age=st.integers(min_value=18, max_value=110),
)
@settings(max_examples=500)
def test_crb65_fuzz_risk_stratification_consistency(confusion, respiratory_rate, systolic_bp, diastolic_bp, age):
    """Risk stratification is consistent with the score value."""
    params = CRB65Params(
        confusion=confusion,
        respiratory_rate=respiratory_rate,
        systolic_bp=systolic_bp,
        diastolic_bp=diastolic_bp,
        age=age,
    )
    result = calculate_crb65(params)

    if result.value == 0:
        assert "Low risk" in result.interpretation
    elif result.value <= 2:
        assert "Intermediate risk" in result.interpretation
    else:
        assert "High risk" in result.interpretation


@pytest.mark.slow
@given(
    confusion=st.booleans(),
    respiratory_rate=st.integers(min_value=8, max_value=60),
    systolic_bp=st.integers(min_value=40, max_value=250),
    diastolic_bp=st.integers(min_value=20, max_value=150),
    age=st.integers(min_value=18, max_value=110),
)
@settings(max_examples=500)
def test_crb65_fuzz_score_matches_criteria(confusion, respiratory_rate, systolic_bp, diastolic_bp, age):
    """Score must equal the sum of individual criteria satisfied."""
    params = CRB65Params(
        confusion=confusion,
        respiratory_rate=respiratory_rate,
        systolic_bp=systolic_bp,
        diastolic_bp=diastolic_bp,
        age=age,
    )
    result = calculate_crb65(params)

    expected = 0
    if confusion:
        expected += 1
    if respiratory_rate >= 30:
        expected += 1
    if systolic_bp < 90 or diastolic_bp <= 60:
        expected += 1
    if age >= 65:
        expected += 1

    assert result.value == expected

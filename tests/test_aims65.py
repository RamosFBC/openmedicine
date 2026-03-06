import pytest
from hypothesis import given, strategies as st
from open_medicine.mcp.calculators.aims65 import calculate_aims65, AIMS65Params


def _make(**kwargs):
    defaults = dict(
        albumin_below_3=False,
        inr_above_1_5=False,
        altered_mental_status=False,
        systolic_bp_90_or_less=False,
        age_65_or_older=False,
    )
    defaults.update(kwargs)
    return AIMS65Params(**defaults)


# ---------------------------------------------------------------------------
# Tier 1: Deterministic Unit Tests
# ---------------------------------------------------------------------------

def test_aims65_minimum_score():
    """Test lowest possible score with all criteria absent."""
    result = calculate_aims65(_make())
    assert result.value == 0
    assert "0.3%" in result.interpretation
    assert "Low risk" in result.interpretation


def test_aims65_maximum_score():
    """Test highest possible score with all criteria present."""
    result = calculate_aims65(_make(
        albumin_below_3=True,
        inr_above_1_5=True,
        altered_mental_status=True,
        systolic_bp_90_or_less=True,
        age_65_or_older=True,
    ))
    assert result.value == 5
    assert "24.5%" in result.interpretation
    assert "High risk" in result.interpretation


def test_aims65_score_1_albumin():
    """Score 1 from albumin alone."""
    result = calculate_aims65(_make(albumin_below_3=True))
    assert result.value == 1
    assert "1.2%" in result.interpretation
    assert "Low risk" in result.interpretation


def test_aims65_score_1_inr():
    """Score 1 from INR alone."""
    result = calculate_aims65(_make(inr_above_1_5=True))
    assert result.value == 1


def test_aims65_score_1_mental_status():
    """Score 1 from altered mental status alone."""
    result = calculate_aims65(_make(altered_mental_status=True))
    assert result.value == 1


def test_aims65_score_1_systolic_bp():
    """Score 1 from systolic BP alone."""
    result = calculate_aims65(_make(systolic_bp_90_or_less=True))
    assert result.value == 1


def test_aims65_score_1_age():
    """Score 1 from age alone."""
    result = calculate_aims65(_make(age_65_or_older=True))
    assert result.value == 1


def test_aims65_low_risk_boundary():
    """Score 1 is the upper boundary of low risk."""
    result = calculate_aims65(_make(albumin_below_3=True))
    assert result.value == 1
    assert "Low risk" in result.interpretation


def test_aims65_high_risk_boundary():
    """Score 2 is the lower boundary of high risk (>= 2)."""
    result = calculate_aims65(_make(albumin_below_3=True, inr_above_1_5=True))
    assert result.value == 2
    assert "5.3%" in result.interpretation
    assert "High risk" in result.interpretation


def test_aims65_score_3():
    """Score 3 with three criteria present."""
    result = calculate_aims65(_make(
        albumin_below_3=True,
        inr_above_1_5=True,
        altered_mental_status=True,
    ))
    assert result.value == 3
    assert "10.3%" in result.interpretation
    assert "High risk" in result.interpretation


def test_aims65_score_4():
    """Score 4 with four criteria present."""
    result = calculate_aims65(_make(
        albumin_below_3=True,
        inr_above_1_5=True,
        altered_mental_status=True,
        systolic_bp_90_or_less=True,
    ))
    assert result.value == 4
    assert "16.5%" in result.interpretation
    assert "High risk" in result.interpretation


def test_aims65_evidence_doi():
    """Verify DOI is correct for the original Saltzman 2011 study."""
    result = calculate_aims65(_make())
    assert result.evidence.source_doi == "10.1016/j.gie.2011.03.1164"


def test_aims65_evidence_level():
    """Verify evidence level is correct."""
    result = calculate_aims65(_make())
    assert result.evidence.level == "Derivation & Validation Study"


def test_aims65_fhir_code():
    """Verify FHIR code and system."""
    result = calculate_aims65(_make())
    assert result.fhir_code == "LP419518-4"
    assert result.fhir_system == "http://loinc.org"
    assert result.fhir_display == "AIMS65 Score"


def test_aims65_interpretation_includes_score():
    """Verify interpretation always starts with AIMS65 Score is <value>."""
    for n in range(6):
        bools = [False] * 5
        for i in range(n):
            bools[i] = True
        params = AIMS65Params(
            albumin_below_3=bools[0],
            inr_above_1_5=bools[1],
            altered_mental_status=bools[2],
            systolic_bp_90_or_less=bools[3],
            age_65_or_older=bools[4],
        )
        result = calculate_aims65(params)
        assert result.value == n
        assert f"AIMS65 Score is {n}" in result.interpretation


def test_aims65_mortality_rates():
    """Verify all mortality rates match the original paper."""
    expected_mortality = {
        0: "0.3%",
        1: "1.2%",
        2: "5.3%",
        3: "10.3%",
        4: "16.5%",
        5: "24.5%",
    }
    for n, expected_pct in expected_mortality.items():
        bools = [False] * 5
        for i in range(n):
            bools[i] = True
        params = AIMS65Params(
            albumin_below_3=bools[0],
            inr_above_1_5=bools[1],
            altered_mental_status=bools[2],
            systolic_bp_90_or_less=bools[3],
            age_65_or_older=bools[4],
        )
        result = calculate_aims65(params)
        assert expected_pct in result.interpretation, (
            f"Score {n}: expected '{expected_pct}' in interpretation, "
            f"got '{result.interpretation}'"
        )


def test_aims65_defaults():
    """Verify that default params produce score 0 (all absent)."""
    params = AIMS65Params()
    result = calculate_aims65(params)
    assert result.value == 0


# ---------------------------------------------------------------------------
# Tier 2: Property-Based Fuzz Tests
# ---------------------------------------------------------------------------

@given(
    st.builds(
        AIMS65Params,
        albumin_below_3=st.booleans(),
        inr_above_1_5=st.booleans(),
        altered_mental_status=st.booleans(),
        systolic_bp_90_or_less=st.booleans(),
        age_65_or_older=st.booleans(),
    )
)
def test_aims65_fuzz_valid_range(params):
    """Output is always within expected bounds for any valid input combination."""
    result = calculate_aims65(params)
    assert result.value is not None
    assert isinstance(result.value, int)
    assert 0 <= result.value <= 5
    assert result.interpretation
    assert "AIMS65 Score is" in result.interpretation
    assert result.evidence.source_doi == "10.1016/j.gie.2011.03.1164"
    assert result.fhir_code == "LP419518-4"

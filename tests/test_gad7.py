import pytest
from hypothesis import given, strategies as st, settings
from open_medicine.mcp.calculators.gad7 import calculate_gad7, GAD7Params


# ---------------------------------------------------------------------------
# Tier 1: Deterministic Unit Tests
# ---------------------------------------------------------------------------

def test_gad7_minimum_score():
    """All items 0 -> total score 0, minimal anxiety."""
    params = GAD7Params(
        feeling_nervous=0,
        cannot_stop_worrying=0,
        worrying_too_much=0,
        trouble_relaxing=0,
        being_restless=0,
        easily_annoyed=0,
        feeling_afraid=0,
    )
    result = calculate_gad7(params)
    assert result.value == 0
    assert "Minimal anxiety" in result.interpretation
    assert "GAD-7 score is 0" in result.interpretation


def test_gad7_maximum_score():
    """All items 3 -> total score 21, severe anxiety."""
    params = GAD7Params(
        feeling_nervous=3,
        cannot_stop_worrying=3,
        worrying_too_much=3,
        trouble_relaxing=3,
        being_restless=3,
        easily_annoyed=3,
        feeling_afraid=3,
    )
    result = calculate_gad7(params)
    assert result.value == 21
    assert "Severe anxiety" in result.interpretation
    assert "GAD-7 score is 21" in result.interpretation


def test_gad7_minimal_upper_boundary():
    """Score 4 is still minimal anxiety (boundary before mild at 5)."""
    # 4 items scored 1, 3 items scored 0 => total = 4
    params = GAD7Params(
        feeling_nervous=1,
        cannot_stop_worrying=1,
        worrying_too_much=1,
        trouble_relaxing=1,
        being_restless=0,
        easily_annoyed=0,
        feeling_afraid=0,
    )
    result = calculate_gad7(params)
    assert result.value == 4
    assert "Minimal anxiety" in result.interpretation


def test_gad7_mild_lower_boundary():
    """Score 5 is mild anxiety (first score in mild range)."""
    # 5 items scored 1, 2 items scored 0 => total = 5
    params = GAD7Params(
        feeling_nervous=1,
        cannot_stop_worrying=1,
        worrying_too_much=1,
        trouble_relaxing=1,
        being_restless=1,
        easily_annoyed=0,
        feeling_afraid=0,
    )
    result = calculate_gad7(params)
    assert result.value == 5
    assert "Mild anxiety" in result.interpretation


def test_gad7_mild_upper_boundary():
    """Score 9 is the top of mild anxiety range."""
    # 3 items scored 3 = 9
    params = GAD7Params(
        feeling_nervous=3,
        cannot_stop_worrying=3,
        worrying_too_much=3,
        trouble_relaxing=0,
        being_restless=0,
        easily_annoyed=0,
        feeling_afraid=0,
    )
    result = calculate_gad7(params)
    assert result.value == 9
    assert "Mild anxiety" in result.interpretation


def test_gad7_moderate_lower_boundary():
    """Score 10 is moderate anxiety (optimal screening threshold)."""
    # Items: 3+3+3+1+0+0+0 = 10
    params = GAD7Params(
        feeling_nervous=3,
        cannot_stop_worrying=3,
        worrying_too_much=3,
        trouble_relaxing=1,
        being_restless=0,
        easily_annoyed=0,
        feeling_afraid=0,
    )
    result = calculate_gad7(params)
    assert result.value == 10
    assert "Moderate anxiety" in result.interpretation
    assert "screening threshold" in result.interpretation.lower()


def test_gad7_moderate_upper_boundary():
    """Score 14 is the top of moderate anxiety range."""
    # All items scored 2 = 14
    params = GAD7Params(
        feeling_nervous=2,
        cannot_stop_worrying=2,
        worrying_too_much=2,
        trouble_relaxing=2,
        being_restless=2,
        easily_annoyed=2,
        feeling_afraid=2,
    )
    result = calculate_gad7(params)
    assert result.value == 14
    assert "Moderate anxiety" in result.interpretation


def test_gad7_severe_lower_boundary():
    """Score 15 is severe anxiety (first score in severe range)."""
    # Items: 3+3+3+3+3+0+0 = 15
    params = GAD7Params(
        feeling_nervous=3,
        cannot_stop_worrying=3,
        worrying_too_much=3,
        trouble_relaxing=3,
        being_restless=3,
        easily_annoyed=0,
        feeling_afraid=0,
    )
    result = calculate_gad7(params)
    assert result.value == 15
    assert "Severe anxiety" in result.interpretation


def test_gad7_evidence_doi():
    """Verify the DOI matches the original Spitzer et al. 2006 paper."""
    params = GAD7Params(
        feeling_nervous=0,
        cannot_stop_worrying=0,
        worrying_too_much=0,
        trouble_relaxing=0,
        being_restless=0,
        easily_annoyed=0,
        feeling_afraid=0,
    )
    result = calculate_gad7(params)
    assert result.evidence.source_doi == "10.1001/archinte.166.10.1092"
    assert result.evidence.level == "Derivation & Validation Study"


def test_gad7_fhir_code():
    """Verify FHIR code represents the GAD-7 total score output concept."""
    params = GAD7Params(
        feeling_nervous=1,
        cannot_stop_worrying=1,
        worrying_too_much=1,
        trouble_relaxing=1,
        being_restless=1,
        easily_annoyed=1,
        feeling_afraid=1,
    )
    result = calculate_gad7(params)
    assert result.fhir_code == "70274-6"
    assert result.fhir_system == "http://loinc.org"
    assert "GAD-7" in result.fhir_display


def test_gad7_single_item_contribution():
    """Each individual item scored 1, rest 0 -> total equals 1."""
    items = [
        "feeling_nervous",
        "cannot_stop_worrying",
        "worrying_too_much",
        "trouble_relaxing",
        "being_restless",
        "easily_annoyed",
        "feeling_afraid",
    ]
    for item in items:
        kwargs = {k: 0 for k in items}
        kwargs[item] = 1
        params = GAD7Params(**kwargs)
        result = calculate_gad7(params)
        assert result.value == 1, f"Expected score 1 when only {item} = 1"


def test_gad7_additive_scoring():
    """Score is purely additive: sum of all 7 item values."""
    # 1+2+3+0+1+2+3 = 12
    params = GAD7Params(
        feeling_nervous=1,
        cannot_stop_worrying=2,
        worrying_too_much=3,
        trouble_relaxing=0,
        being_restless=1,
        easily_annoyed=2,
        feeling_afraid=3,
    )
    result = calculate_gad7(params)
    assert result.value == 12
    assert "Moderate anxiety" in result.interpretation


def test_gad7_interpretation_always_includes_score():
    """Every severity level includes the numeric score in interpretation."""
    test_cases = [
        (0, "0"),   # minimal
        (7, "7"),   # mild
        (12, "12"), # moderate
        (18, "18"), # severe
    ]
    for target_score, score_str in test_cases:
        # Distribute the target score across items
        items = [0] * 7
        remaining = target_score
        for i in range(7):
            items[i] = min(remaining, 3)
            remaining -= items[i]
        params = GAD7Params(
            feeling_nervous=items[0],
            cannot_stop_worrying=items[1],
            worrying_too_much=items[2],
            trouble_relaxing=items[3],
            being_restless=items[4],
            easily_annoyed=items[5],
            feeling_afraid=items[6],
        )
        result = calculate_gad7(params)
        assert result.value == target_score
        assert f"GAD-7 score is {score_str}" in result.interpretation


def test_gad7_field_validation_rejects_out_of_range():
    """Pydantic model rejects item values outside 0-3."""
    with pytest.raises(Exception):
        GAD7Params(
            feeling_nervous=4,
            cannot_stop_worrying=0,
            worrying_too_much=0,
            trouble_relaxing=0,
            being_restless=0,
            easily_annoyed=0,
            feeling_afraid=0,
        )

    with pytest.raises(Exception):
        GAD7Params(
            feeling_nervous=-1,
            cannot_stop_worrying=0,
            worrying_too_much=0,
            trouble_relaxing=0,
            being_restless=0,
            easily_annoyed=0,
            feeling_afraid=0,
        )


# ---------------------------------------------------------------------------
# Tier 2: Property-Based Fuzz Tests
# ---------------------------------------------------------------------------

@pytest.mark.slow
@given(
    feeling_nervous=st.integers(min_value=0, max_value=3),
    cannot_stop_worrying=st.integers(min_value=0, max_value=3),
    worrying_too_much=st.integers(min_value=0, max_value=3),
    trouble_relaxing=st.integers(min_value=0, max_value=3),
    being_restless=st.integers(min_value=0, max_value=3),
    easily_annoyed=st.integers(min_value=0, max_value=3),
    feeling_afraid=st.integers(min_value=0, max_value=3),
)
@settings(max_examples=500)
def test_gad7_fuzz_valid_range(
    feeling_nervous,
    cannot_stop_worrying,
    worrying_too_much,
    trouble_relaxing,
    being_restless,
    easily_annoyed,
    feeling_afraid,
):
    """Output is always 0-21 with non-empty interpretation for any valid input."""
    params = GAD7Params(
        feeling_nervous=feeling_nervous,
        cannot_stop_worrying=cannot_stop_worrying,
        worrying_too_much=worrying_too_much,
        trouble_relaxing=trouble_relaxing,
        being_restless=being_restless,
        easily_annoyed=easily_annoyed,
        feeling_afraid=feeling_afraid,
    )
    result = calculate_gad7(params)
    assert result.value is not None
    assert isinstance(result.value, int)
    assert 0 <= result.value <= 21
    assert result.interpretation
    assert result.evidence.source_doi
    assert "GAD-7" in result.interpretation


@pytest.mark.slow
@given(
    feeling_nervous=st.integers(min_value=0, max_value=3),
    cannot_stop_worrying=st.integers(min_value=0, max_value=3),
    worrying_too_much=st.integers(min_value=0, max_value=3),
    trouble_relaxing=st.integers(min_value=0, max_value=3),
    being_restless=st.integers(min_value=0, max_value=3),
    easily_annoyed=st.integers(min_value=0, max_value=3),
    feeling_afraid=st.integers(min_value=0, max_value=3),
)
@settings(max_examples=500)
def test_gad7_fuzz_additive_property(
    feeling_nervous,
    cannot_stop_worrying,
    worrying_too_much,
    trouble_relaxing,
    being_restless,
    easily_annoyed,
    feeling_afraid,
):
    """Score always equals the exact sum of all 7 item values."""
    params = GAD7Params(
        feeling_nervous=feeling_nervous,
        cannot_stop_worrying=cannot_stop_worrying,
        worrying_too_much=worrying_too_much,
        trouble_relaxing=trouble_relaxing,
        being_restless=being_restless,
        easily_annoyed=easily_annoyed,
        feeling_afraid=feeling_afraid,
    )
    result = calculate_gad7(params)
    expected = (
        feeling_nervous
        + cannot_stop_worrying
        + worrying_too_much
        + trouble_relaxing
        + being_restless
        + easily_annoyed
        + feeling_afraid
    )
    assert result.value == expected


@pytest.mark.slow
@given(
    feeling_nervous=st.integers(min_value=0, max_value=3),
    cannot_stop_worrying=st.integers(min_value=0, max_value=3),
    worrying_too_much=st.integers(min_value=0, max_value=3),
    trouble_relaxing=st.integers(min_value=0, max_value=3),
    being_restless=st.integers(min_value=0, max_value=3),
    easily_annoyed=st.integers(min_value=0, max_value=3),
    feeling_afraid=st.integers(min_value=0, max_value=3),
)
@settings(max_examples=500)
def test_gad7_fuzz_severity_strata_consistency(
    feeling_nervous,
    cannot_stop_worrying,
    worrying_too_much,
    trouble_relaxing,
    being_restless,
    easily_annoyed,
    feeling_afraid,
):
    """Severity label is always consistent with the score value."""
    params = GAD7Params(
        feeling_nervous=feeling_nervous,
        cannot_stop_worrying=cannot_stop_worrying,
        worrying_too_much=worrying_too_much,
        trouble_relaxing=trouble_relaxing,
        being_restless=being_restless,
        easily_annoyed=easily_annoyed,
        feeling_afraid=feeling_afraid,
    )
    result = calculate_gad7(params)
    score = result.value
    if score <= 4:
        assert "Minimal anxiety" in result.interpretation
    elif score <= 9:
        assert "Mild anxiety" in result.interpretation
    elif score <= 14:
        assert "Moderate anxiety" in result.interpretation
    else:
        assert "Severe anxiety" in result.interpretation

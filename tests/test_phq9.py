import pytest
from open_medicine.mcp.calculators.phq9 import calculate_phq9, PHQ9Params


def _make_params(**kwargs):
    """Helper to create PHQ9Params with all items defaulting to 0."""
    defaults = dict(
        interest_pleasure=0,
        feeling_down=0,
        sleep=0,
        energy=0,
        appetite=0,
        self_esteem=0,
        concentration=0,
        psychomotor=0,
        suicidal_ideation=0,
    )
    defaults.update(kwargs)
    return PHQ9Params(**defaults)


# ---------------------------------------------------------------------------
# Minimum and maximum score tests
# ---------------------------------------------------------------------------


def test_phq9_minimum_score():
    """All items scored 0 = total 0, minimal depression."""
    result = calculate_phq9(_make_params())
    assert result.value == 0
    assert "Minimal depression" in result.interpretation
    assert "No treatment action required" in result.interpretation


def test_phq9_maximum_score():
    """All items scored 3 = total 27, severe depression."""
    params = PHQ9Params(
        interest_pleasure=3,
        feeling_down=3,
        sleep=3,
        energy=3,
        appetite=3,
        self_esteem=3,
        concentration=3,
        psychomotor=3,
        suicidal_ideation=3,
    )
    result = calculate_phq9(params)
    assert result.value == 27
    assert "Severe depression" in result.interpretation
    assert "Immediate initiation" in result.interpretation


# ---------------------------------------------------------------------------
# Severity threshold boundary tests
# ---------------------------------------------------------------------------


def test_phq9_minimal_upper_boundary():
    """Score of 4 = still minimal depression."""
    # 4 items at 1 each = 4
    result = calculate_phq9(_make_params(
        interest_pleasure=1,
        feeling_down=1,
        sleep=1,
        energy=1,
    ))
    assert result.value == 4
    assert "Minimal depression" in result.interpretation


def test_phq9_mild_lower_boundary():
    """Score of 5 = mild depression."""
    result = calculate_phq9(_make_params(
        interest_pleasure=1,
        feeling_down=1,
        sleep=1,
        energy=1,
        appetite=1,
    ))
    assert result.value == 5
    assert "Mild depression" in result.interpretation
    assert "Watchful waiting" in result.interpretation


def test_phq9_mild_upper_boundary():
    """Score of 9 = still mild depression."""
    result = calculate_phq9(_make_params(
        interest_pleasure=1,
        feeling_down=1,
        sleep=1,
        energy=1,
        appetite=1,
        self_esteem=1,
        concentration=1,
        psychomotor=1,
        suicidal_ideation=1,
    ))
    assert result.value == 9
    assert "Mild depression" in result.interpretation


def test_phq9_moderate_lower_boundary():
    """Score of 10 = moderate depression (clinical threshold for major depression screening)."""
    # 3 items at 3 + 1 item at 1 = 10
    result = calculate_phq9(_make_params(
        interest_pleasure=3,
        feeling_down=3,
        sleep=3,
        energy=1,
    ))
    assert result.value == 10
    assert "Moderate depression" in result.interpretation
    assert "Treatment plan" in result.interpretation


def test_phq9_moderate_upper_boundary():
    """Score of 14 = still moderate depression."""
    # 4 items at 3 + 1 item at 2 = 14
    result = calculate_phq9(_make_params(
        interest_pleasure=3,
        feeling_down=3,
        sleep=3,
        energy=3,
        appetite=2,
    ))
    assert result.value == 14
    assert "Moderate depression" in result.interpretation


def test_phq9_moderately_severe_lower_boundary():
    """Score of 15 = moderately severe depression."""
    # 5 items at 3 = 15
    result = calculate_phq9(_make_params(
        interest_pleasure=3,
        feeling_down=3,
        sleep=3,
        energy=3,
        appetite=3,
    ))
    assert result.value == 15
    assert "Moderately severe depression" in result.interpretation
    assert "Active treatment" in result.interpretation


def test_phq9_moderately_severe_upper_boundary():
    """Score of 19 = still moderately severe depression."""
    # 6 items at 3 + 1 item at 1 = 19
    result = calculate_phq9(_make_params(
        interest_pleasure=3,
        feeling_down=3,
        sleep=3,
        energy=3,
        appetite=3,
        self_esteem=3,
        concentration=1,
    ))
    assert result.value == 19
    assert "Moderately severe depression" in result.interpretation


def test_phq9_severe_lower_boundary():
    """Score of 20 = severe depression."""
    # 6 items at 3 + 1 item at 2 = 20
    result = calculate_phq9(_make_params(
        interest_pleasure=3,
        feeling_down=3,
        sleep=3,
        energy=3,
        appetite=3,
        self_esteem=3,
        concentration=2,
    ))
    assert result.value == 20
    assert "Severe depression" in result.interpretation
    assert "Immediate initiation" in result.interpretation


# ---------------------------------------------------------------------------
# Individual item contribution tests
# ---------------------------------------------------------------------------


def test_phq9_single_item_max():
    """A single item at max (3) gives score of 3 = minimal depression."""
    result = calculate_phq9(_make_params(suicidal_ideation=3))
    assert result.value == 3
    assert "Minimal depression" in result.interpretation


def test_phq9_each_item_contributes():
    """Each item contributes its value to the total score."""
    # Set each item to a different value (1 through 3 cycling) and verify sum
    params = PHQ9Params(
        interest_pleasure=1,
        feeling_down=2,
        sleep=3,
        energy=1,
        appetite=2,
        self_esteem=3,
        concentration=1,
        psychomotor=2,
        suicidal_ideation=3,
    )
    result = calculate_phq9(params)
    assert result.value == 1 + 2 + 3 + 1 + 2 + 3 + 1 + 2 + 3  # = 18


# ---------------------------------------------------------------------------
# Evidence and FHIR metadata tests
# ---------------------------------------------------------------------------


def test_phq9_evidence_doi():
    """Verify DOI matches Kroenke et al. 2001."""
    result = calculate_phq9(_make_params())
    assert result.evidence.source_doi == "10.1046/j.1525-1497.2001.016009606.x"


def test_phq9_evidence_level():
    """Verify evidence level is Derivation & Validation Study."""
    result = calculate_phq9(_make_params())
    assert result.evidence.level == "Derivation & Validation Study"


def test_phq9_fhir_code():
    """Verify FHIR code is LOINC 44261-6 for PHQ-9 total score."""
    result = calculate_phq9(_make_params())
    assert result.fhir_code == "44261-6"
    assert result.fhir_system == "http://loinc.org"
    assert "PHQ-9" in result.fhir_display or "Patient Health Questionnaire" in result.fhir_display


# ---------------------------------------------------------------------------
# Interpretation format tests
# ---------------------------------------------------------------------------


def test_phq9_interpretation_contains_score():
    """Interpretation always starts with the numeric score."""
    for total in [0, 5, 10, 15, 20, 27]:
        # Build a params set that sums to the target total
        items = [0] * 9
        remaining = total
        for i in range(9):
            add = min(3, remaining)
            items[i] = add
            remaining -= add
        params = PHQ9Params(
            interest_pleasure=items[0],
            feeling_down=items[1],
            sleep=items[2],
            energy=items[3],
            appetite=items[4],
            self_esteem=items[5],
            concentration=items[6],
            psychomotor=items[7],
            suicidal_ideation=items[8],
        )
        result = calculate_phq9(params)
        assert f"PHQ-9 score is {total}" in result.interpretation


# ---------------------------------------------------------------------------
# Pydantic validation tests
# ---------------------------------------------------------------------------


def test_phq9_rejects_out_of_range_high():
    """Items greater than 3 should be rejected by Pydantic validation."""
    with pytest.raises(Exception):
        PHQ9Params(
            interest_pleasure=4,
            feeling_down=0,
            sleep=0,
            energy=0,
            appetite=0,
            self_esteem=0,
            concentration=0,
            psychomotor=0,
            suicidal_ideation=0,
        )


def test_phq9_rejects_out_of_range_low():
    """Items less than 0 should be rejected by Pydantic validation."""
    with pytest.raises(Exception):
        PHQ9Params(
            interest_pleasure=-1,
            feeling_down=0,
            sleep=0,
            energy=0,
            appetite=0,
            self_esteem=0,
            concentration=0,
            psychomotor=0,
            suicidal_ideation=0,
        )

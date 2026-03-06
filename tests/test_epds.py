import pytest
from open_medicine.mcp.calculators.epds import calculate_epds, EPDSParams


def _make_params(**kwargs):
    """Helper to create EPDSParams with all items defaulting to 0."""
    defaults = dict(
        laugh=0,
        enjoyment=0,
        self_blame=0,
        anxious=0,
        scared=0,
        things_on_top=0,
        difficulty_sleeping=0,
        sad=0,
        crying=0,
        self_harm=0,
    )
    defaults.update(kwargs)
    return EPDSParams(**defaults)


# ---------------------------------------------------------------------------
# Minimum and maximum score tests
# ---------------------------------------------------------------------------


def test_epds_minimum_score():
    """All items scored 0 = total 0, low risk (negative screen)."""
    result = calculate_epds(_make_params())
    assert result.value == 0
    assert "Low risk" in result.interpretation
    assert "negative screen" in result.interpretation
    assert "Continue routine clinical monitoring" in result.interpretation


def test_epds_maximum_score():
    """All items scored 3 = total 30, probable depression."""
    params = EPDSParams(
        laugh=3,
        enjoyment=3,
        self_blame=3,
        anxious=3,
        scared=3,
        things_on_top=3,
        difficulty_sleeping=3,
        sad=3,
        crying=3,
        self_harm=3,
    )
    result = calculate_epds(params)
    assert result.value == 30
    assert "Probable depression" in result.interpretation
    assert "Comprehensive diagnostic evaluation" in result.interpretation
    # Self-harm flag should also be present
    assert "SAFETY ALERT" in result.interpretation


# ---------------------------------------------------------------------------
# Severity threshold boundary tests
# ---------------------------------------------------------------------------


def test_epds_low_risk_upper_boundary():
    """Score of 9 = still low risk (negative screen)."""
    # 9 items at 1 each = 9
    result = calculate_epds(_make_params(
        laugh=1,
        enjoyment=1,
        self_blame=1,
        anxious=1,
        scared=1,
        things_on_top=1,
        difficulty_sleeping=1,
        sad=1,
        crying=1,
    ))
    assert result.value == 9
    assert "Low risk" in result.interpretation
    assert "negative screen" in result.interpretation


def test_epds_possible_depression_lower_boundary():
    """Score of 10 = possible depression."""
    # 10 items at 1 each = 10
    result = calculate_epds(_make_params(
        laugh=1,
        enjoyment=1,
        self_blame=1,
        anxious=1,
        scared=1,
        things_on_top=1,
        difficulty_sleeping=1,
        sad=1,
        crying=1,
        self_harm=1,
    ))
    assert result.value == 10
    assert "Possible depression" in result.interpretation
    assert "Further clinical assessment recommended" in result.interpretation


def test_epds_possible_depression_upper_boundary():
    """Score of 12 = still possible depression."""
    # 4 items at 3 = 12
    result = calculate_epds(_make_params(
        laugh=3,
        enjoyment=3,
        self_blame=3,
        anxious=3,
    ))
    assert result.value == 12
    assert "Possible depression" in result.interpretation


def test_epds_probable_depression_lower_boundary():
    """Score of 13 = probable depression (positive screen)."""
    # 4 items at 3 + 1 item at 1 = 13
    result = calculate_epds(_make_params(
        laugh=3,
        enjoyment=3,
        self_blame=3,
        anxious=3,
        scared=1,
    ))
    assert result.value == 13
    assert "Probable depression" in result.interpretation
    assert "positive screen" in result.interpretation
    assert "threshold of 12/13" in result.interpretation
    assert "sensitivity 86%" in result.interpretation


def test_epds_high_score():
    """Score of 25 = probable depression with high severity."""
    # 8 items at 3 + 1 item at 1 = 25
    result = calculate_epds(_make_params(
        laugh=3,
        enjoyment=3,
        self_blame=3,
        anxious=3,
        scared=3,
        things_on_top=3,
        difficulty_sleeping=3,
        sad=3,
        crying=1,
    ))
    assert result.value == 25
    assert "Probable depression" in result.interpretation


# ---------------------------------------------------------------------------
# Self-harm safety alert tests (item 10)
# ---------------------------------------------------------------------------


def test_epds_self_harm_item_zero_no_flag():
    """Self-harm item scored 0 = no safety alert."""
    result = calculate_epds(_make_params(self_harm=0))
    assert "SAFETY ALERT" not in result.interpretation


def test_epds_self_harm_item_one_flags():
    """Self-harm item scored 1 = safety alert triggered."""
    result = calculate_epds(_make_params(self_harm=1))
    assert "SAFETY ALERT" in result.interpretation
    assert "Item 10" in result.interpretation
    assert "1/3" in result.interpretation
    assert "Immediate safety assessment" in result.interpretation


def test_epds_self_harm_item_two_flags():
    """Self-harm item scored 2 = safety alert triggered."""
    result = calculate_epds(_make_params(self_harm=2))
    assert "SAFETY ALERT" in result.interpretation
    assert "2/3" in result.interpretation


def test_epds_self_harm_item_three_flags():
    """Self-harm item scored 3 = safety alert triggered."""
    result = calculate_epds(_make_params(self_harm=3))
    assert "SAFETY ALERT" in result.interpretation
    assert "3/3" in result.interpretation


def test_epds_self_harm_with_low_total():
    """Self-harm alert appears even with low total score."""
    result = calculate_epds(_make_params(self_harm=1))
    assert result.value == 1
    assert "Low risk" in result.interpretation
    assert "SAFETY ALERT" in result.interpretation


# ---------------------------------------------------------------------------
# Individual item contribution tests
# ---------------------------------------------------------------------------


def test_epds_single_item_max():
    """A single item at max (3) gives score of 3."""
    result = calculate_epds(_make_params(sad=3))
    assert result.value == 3


def test_epds_each_item_contributes():
    """Each item contributes its value to the total score."""
    params = EPDSParams(
        laugh=1,
        enjoyment=2,
        self_blame=3,
        anxious=1,
        scared=2,
        things_on_top=3,
        difficulty_sleeping=1,
        sad=2,
        crying=3,
        self_harm=0,
    )
    result = calculate_epds(params)
    assert result.value == 1 + 2 + 3 + 1 + 2 + 3 + 1 + 2 + 3 + 0  # = 18


# ---------------------------------------------------------------------------
# Evidence and FHIR metadata tests
# ---------------------------------------------------------------------------


def test_epds_evidence_doi():
    """Verify DOI matches Cox et al. 1987."""
    result = calculate_epds(_make_params())
    assert result.evidence.source_doi == "10.1192/bjp.150.6.782"


def test_epds_evidence_level():
    """Verify evidence level is Derivation & Validation Study."""
    result = calculate_epds(_make_params())
    assert result.evidence.level == "Derivation & Validation Study"


def test_epds_evidence_description():
    """Verify evidence description mentions the original paper."""
    result = calculate_epds(_make_params())
    assert "Cox" in result.evidence.description
    assert "Edinburgh" in result.evidence.description
    assert "1987" in result.evidence.description


def test_epds_fhir_code():
    """Verify FHIR code is LOINC 71354-5 for EPDS total score."""
    result = calculate_epds(_make_params())
    assert result.fhir_code == "71354-5"
    assert result.fhir_system == "http://loinc.org"
    assert "EPDS" in result.fhir_display or "Edinburgh" in result.fhir_display


# ---------------------------------------------------------------------------
# Interpretation format tests
# ---------------------------------------------------------------------------


def test_epds_interpretation_contains_score():
    """Interpretation always contains the numeric score."""
    for total in [0, 5, 10, 13, 20, 30]:
        # Build a params set that sums to the target total
        items = [0] * 10
        remaining = total
        for i in range(10):
            add = min(3, remaining)
            items[i] = add
            remaining -= add
        params = EPDSParams(
            laugh=items[0],
            enjoyment=items[1],
            self_blame=items[2],
            anxious=items[3],
            scared=items[4],
            things_on_top=items[5],
            difficulty_sleeping=items[6],
            sad=items[7],
            crying=items[8],
            self_harm=items[9],
        )
        result = calculate_epds(params)
        assert f"EPDS score is {total}" in result.interpretation


# ---------------------------------------------------------------------------
# Pydantic validation tests
# ---------------------------------------------------------------------------


def test_epds_rejects_out_of_range_high():
    """Items greater than 3 should be rejected by Pydantic validation."""
    with pytest.raises(Exception):
        EPDSParams(
            laugh=4,
            enjoyment=0,
            self_blame=0,
            anxious=0,
            scared=0,
            things_on_top=0,
            difficulty_sleeping=0,
            sad=0,
            crying=0,
            self_harm=0,
        )


def test_epds_rejects_out_of_range_low():
    """Items less than 0 should be rejected by Pydantic validation."""
    with pytest.raises(Exception):
        EPDSParams(
            laugh=-1,
            enjoyment=0,
            self_blame=0,
            anxious=0,
            scared=0,
            things_on_top=0,
            difficulty_sleeping=0,
            sad=0,
            crying=0,
            self_harm=0,
        )


def test_epds_rejects_missing_required_field():
    """Missing a required field should raise a validation error."""
    with pytest.raises(Exception):
        # Missing self_harm
        EPDSParams(
            laugh=0,
            enjoyment=0,
            self_blame=0,
            anxious=0,
            scared=0,
            things_on_top=0,
            difficulty_sleeping=0,
            sad=0,
            crying=0,
        )


# ---------------------------------------------------------------------------
# Cross-validation test cases (verified against MDCalc / reference implementations)
# ---------------------------------------------------------------------------


def test_epds_cross_validation_case_1():
    """Healthy mother with no symptoms: score 0."""
    result = calculate_epds(_make_params())
    assert result.value == 0
    assert "Low risk" in result.interpretation


def test_epds_cross_validation_case_2():
    """Mild symptoms across several items: score 7."""
    result = calculate_epds(_make_params(
        laugh=1,
        enjoyment=1,
        anxious=1,
        things_on_top=1,
        difficulty_sleeping=1,
        sad=1,
        crying=1,
    ))
    assert result.value == 7
    assert "Low risk" in result.interpretation


def test_epds_cross_validation_case_3():
    """Moderate symptoms pushing into possible depression: score 11."""
    # 3 items at 3 + 1 item at 2 = 11
    result = calculate_epds(_make_params(
        self_blame=3,
        anxious=3,
        scared=3,
        things_on_top=2,
    ))
    assert result.value == 11
    assert "Possible depression" in result.interpretation


def test_epds_cross_validation_case_4():
    """Significant symptoms at threshold: score 13."""
    result = calculate_epds(_make_params(
        laugh=2,
        enjoyment=2,
        self_blame=2,
        anxious=2,
        scared=1,
        things_on_top=2,
        difficulty_sleeping=1,
        sad=1,
    ))
    assert result.value == 13
    assert "Probable depression" in result.interpretation


def test_epds_cross_validation_case_5():
    """Severe depression with self-harm ideation: score 24."""
    result = calculate_epds(EPDSParams(
        laugh=3,
        enjoyment=3,
        self_blame=3,
        anxious=2,
        scared=2,
        things_on_top=3,
        difficulty_sleeping=2,
        sad=3,
        crying=2,
        self_harm=1,
    ))
    assert result.value == 24
    assert "Probable depression" in result.interpretation
    assert "SAFETY ALERT" in result.interpretation

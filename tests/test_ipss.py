import pytest
from hypothesis import given, strategies as st, settings
from open_medicine.mcp.calculators.ipss import calculate_ipss, IPSSParams


def _make_params(**kwargs):
    """Helper to create IPSSParams with all symptom items defaulting to 0."""
    defaults = dict(
        incomplete_emptying=0,
        frequency=0,
        intermittency=0,
        urgency=0,
        weak_stream=0,
        straining=0,
        nocturia=0,
    )
    defaults.update(kwargs)
    return IPSSParams(**defaults)


# ---------------------------------------------------------------------------
# Minimum and maximum score tests
# ---------------------------------------------------------------------------


def test_ipss_minimum_score():
    """All items scored 0 = total 0, mild symptoms."""
    result = calculate_ipss(_make_params())
    assert result.value == 0
    assert "Mild symptoms" in result.interpretation
    assert "Watchful waiting" in result.interpretation


def test_ipss_maximum_score():
    """All items scored 5 = total 35, severe symptoms."""
    params = IPSSParams(
        incomplete_emptying=5,
        frequency=5,
        intermittency=5,
        urgency=5,
        weak_stream=5,
        straining=5,
        nocturia=5,
    )
    result = calculate_ipss(params)
    assert result.value == 35
    assert "Severe symptoms" in result.interpretation
    assert "Urology referral" in result.interpretation


# ---------------------------------------------------------------------------
# Severity threshold boundary tests
# ---------------------------------------------------------------------------


def test_ipss_mild_upper_boundary():
    """Score of 7 = still mild symptoms."""
    # 1+1+1+1+1+1+1 = 7
    result = calculate_ipss(_make_params(
        incomplete_emptying=1,
        frequency=1,
        intermittency=1,
        urgency=1,
        weak_stream=1,
        straining=1,
        nocturia=1,
    ))
    assert result.value == 7
    assert "Mild symptoms" in result.interpretation


def test_ipss_moderate_lower_boundary():
    """Score of 8 = moderate symptoms."""
    # 2+1+1+1+1+1+1 = 8
    result = calculate_ipss(_make_params(
        incomplete_emptying=2,
        frequency=1,
        intermittency=1,
        urgency=1,
        weak_stream=1,
        straining=1,
        nocturia=1,
    ))
    assert result.value == 8
    assert "Moderate symptoms" in result.interpretation
    assert "Medical therapy" in result.interpretation


def test_ipss_moderate_upper_boundary():
    """Score of 19 = still moderate symptoms."""
    # 3+3+3+3+3+3+1 = 19
    result = calculate_ipss(_make_params(
        incomplete_emptying=3,
        frequency=3,
        intermittency=3,
        urgency=3,
        weak_stream=3,
        straining=3,
        nocturia=1,
    ))
    assert result.value == 19
    assert "Moderate symptoms" in result.interpretation


def test_ipss_severe_lower_boundary():
    """Score of 20 = severe symptoms."""
    # 3+3+3+3+3+3+2 = 20
    result = calculate_ipss(_make_params(
        incomplete_emptying=3,
        frequency=3,
        intermittency=3,
        urgency=3,
        weak_stream=3,
        straining=3,
        nocturia=2,
    ))
    assert result.value == 20
    assert "Severe symptoms" in result.interpretation
    assert "Urology referral" in result.interpretation


# ---------------------------------------------------------------------------
# Quality of Life (QoL) tests
# ---------------------------------------------------------------------------


def test_ipss_without_qol():
    """When QoL is not provided, interpretation does not mention QoL."""
    result = calculate_ipss(_make_params())
    assert "Quality of Life" not in result.interpretation


def test_ipss_with_qol_delighted():
    """QoL = 0 (Delighted) is appended to interpretation."""
    result = calculate_ipss(_make_params(quality_of_life=0))
    assert "Quality of Life (QoL) score is 0" in result.interpretation
    assert "Delighted" in result.interpretation


def test_ipss_with_qol_terrible():
    """QoL = 6 (Terrible) is appended to interpretation."""
    result = calculate_ipss(_make_params(quality_of_life=6))
    assert "Quality of Life (QoL) score is 6" in result.interpretation
    assert "Terrible" in result.interpretation


def test_ipss_with_qol_mixed():
    """QoL = 3 (Mixed) is appended to interpretation."""
    result = calculate_ipss(_make_params(quality_of_life=3))
    assert "Quality of Life (QoL) score is 3" in result.interpretation
    assert "Mixed" in result.interpretation


def test_ipss_qol_all_values():
    """Verify all QoL values (0-6) produce appropriate labels."""
    expected_labels = {
        0: "Delighted",
        1: "Pleased",
        2: "Mostly satisfied",
        3: "Mixed",
        4: "Mostly dissatisfied",
        5: "Unhappy",
        6: "Terrible",
    }
    for qol_value, label in expected_labels.items():
        result = calculate_ipss(_make_params(quality_of_life=qol_value))
        assert label in result.interpretation


# ---------------------------------------------------------------------------
# Individual item contribution tests
# ---------------------------------------------------------------------------


def test_ipss_single_item_max():
    """A single item at max (5) gives score of 5 = mild symptoms."""
    result = calculate_ipss(_make_params(nocturia=5))
    assert result.value == 5
    assert "Mild symptoms" in result.interpretation


def test_ipss_each_item_contributes():
    """Each item contributes its value to the total score."""
    params = IPSSParams(
        incomplete_emptying=1,
        frequency=2,
        intermittency=3,
        urgency=4,
        weak_stream=5,
        straining=0,
        nocturia=1,
    )
    result = calculate_ipss(params)
    assert result.value == 1 + 2 + 3 + 4 + 5 + 0 + 1  # = 16


# ---------------------------------------------------------------------------
# Evidence and FHIR metadata tests
# ---------------------------------------------------------------------------


def test_ipss_evidence_doi():
    """Verify DOI matches Barry MJ et al. 1992."""
    result = calculate_ipss(_make_params())
    assert result.evidence.source_doi == "10.1016/S0022-5347(17)36966-5"


def test_ipss_evidence_level():
    """Verify evidence level is Derivation & Validation Study."""
    result = calculate_ipss(_make_params())
    assert result.evidence.level == "Derivation & Validation Study"


def test_ipss_fhir_code():
    """Verify FHIR code is LOINC 80976-4 for IPSS total score."""
    result = calculate_ipss(_make_params())
    assert result.fhir_code == "80976-4"
    assert result.fhir_system == "http://loinc.org"
    assert "IPSS" in result.fhir_display or "International Prostate Symptom Score" in result.fhir_display


# ---------------------------------------------------------------------------
# Interpretation format tests
# ---------------------------------------------------------------------------


def test_ipss_interpretation_contains_score():
    """Interpretation always includes the numeric IPSS score."""
    for total in [0, 7, 8, 19, 20, 35]:
        # Build params that sum to the target total
        items = [0] * 7
        remaining = total
        for i in range(7):
            add = min(5, remaining)
            items[i] = add
            remaining -= add
        params = IPSSParams(
            incomplete_emptying=items[0],
            frequency=items[1],
            intermittency=items[2],
            urgency=items[3],
            weak_stream=items[4],
            straining=items[5],
            nocturia=items[6],
        )
        result = calculate_ipss(params)
        assert f"IPSS is {total}" in result.interpretation


# ---------------------------------------------------------------------------
# Pydantic validation tests
# ---------------------------------------------------------------------------


def test_ipss_rejects_symptom_out_of_range_high():
    """Symptom items greater than 5 should be rejected by Pydantic validation."""
    with pytest.raises(Exception):
        IPSSParams(
            incomplete_emptying=6,
            frequency=0,
            intermittency=0,
            urgency=0,
            weak_stream=0,
            straining=0,
            nocturia=0,
        )


def test_ipss_rejects_symptom_out_of_range_low():
    """Symptom items less than 0 should be rejected by Pydantic validation."""
    with pytest.raises(Exception):
        IPSSParams(
            incomplete_emptying=-1,
            frequency=0,
            intermittency=0,
            urgency=0,
            weak_stream=0,
            straining=0,
            nocturia=0,
        )


def test_ipss_rejects_qol_out_of_range_high():
    """QoL greater than 6 should be rejected by Pydantic validation."""
    with pytest.raises(Exception):
        IPSSParams(
            incomplete_emptying=0,
            frequency=0,
            intermittency=0,
            urgency=0,
            weak_stream=0,
            straining=0,
            nocturia=0,
            quality_of_life=7,
        )


def test_ipss_rejects_qol_out_of_range_low():
    """QoL less than 0 should be rejected by Pydantic validation."""
    with pytest.raises(Exception):
        IPSSParams(
            incomplete_emptying=0,
            frequency=0,
            intermittency=0,
            urgency=0,
            weak_stream=0,
            straining=0,
            nocturia=0,
            quality_of_life=-1,
        )


# ---------------------------------------------------------------------------
# Property-based fuzz tests
# ---------------------------------------------------------------------------


@given(
    st.builds(
        IPSSParams,
        incomplete_emptying=st.integers(min_value=0, max_value=5),
        frequency=st.integers(min_value=0, max_value=5),
        intermittency=st.integers(min_value=0, max_value=5),
        urgency=st.integers(min_value=0, max_value=5),
        weak_stream=st.integers(min_value=0, max_value=5),
        straining=st.integers(min_value=0, max_value=5),
        nocturia=st.integers(min_value=0, max_value=5),
        quality_of_life=st.one_of(st.none(), st.integers(min_value=0, max_value=6)),
    )
)
@settings(max_examples=500, deadline=None)
def test_ipss_fuzz_valid_range(params):
    """Output is always within expected bounds for any valid input."""
    result = calculate_ipss(params)
    assert result.value is not None
    assert isinstance(result.value, int)
    assert 0 <= result.value <= 35
    assert result.interpretation
    assert result.evidence.source_doi
    # Verify score matches sum of inputs
    expected = (
        params.incomplete_emptying
        + params.frequency
        + params.intermittency
        + params.urgency
        + params.weak_stream
        + params.straining
        + params.nocturia
    )
    assert result.value == expected


# ---------------------------------------------------------------------------
# Cross-validation test vectors (from published references)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "inputs,expected_score,expected_severity",
    [
        # All zeros - asymptomatic
        (dict(incomplete_emptying=0, frequency=0, intermittency=0, urgency=0,
              weak_stream=0, straining=0, nocturia=0), 0, "Mild"),
        # Classic mild case: occasional nocturia
        (dict(incomplete_emptying=0, frequency=1, intermittency=0, urgency=0,
              weak_stream=1, straining=0, nocturia=2), 4, "Mild"),
        # Boundary mild/moderate
        (dict(incomplete_emptying=1, frequency=1, intermittency=1, urgency=1,
              weak_stream=1, straining=1, nocturia=1), 7, "Mild"),
        # Just into moderate
        (dict(incomplete_emptying=2, frequency=2, intermittency=1, urgency=1,
              weak_stream=1, straining=0, nocturia=1), 8, "Moderate"),
        # Mid-moderate
        (dict(incomplete_emptying=2, frequency=3, intermittency=2, urgency=2,
              weak_stream=2, straining=1, nocturia=2), 14, "Moderate"),
        # Boundary moderate/severe
        (dict(incomplete_emptying=3, frequency=3, intermittency=3, urgency=3,
              weak_stream=3, straining=3, nocturia=1), 19, "Moderate"),
        # Just into severe
        (dict(incomplete_emptying=3, frequency=3, intermittency=3, urgency=3,
              weak_stream=3, straining=3, nocturia=2), 20, "Severe"),
        # High severe
        (dict(incomplete_emptying=4, frequency=5, intermittency=4, urgency=5,
              weak_stream=5, straining=4, nocturia=4), 31, "Severe"),
        # Maximum
        (dict(incomplete_emptying=5, frequency=5, intermittency=5, urgency=5,
              weak_stream=5, straining=5, nocturia=5), 35, "Severe"),
    ],
    ids=[
        "asymptomatic",
        "classic_mild",
        "mild_upper_boundary",
        "moderate_lower_boundary",
        "mid_moderate",
        "moderate_upper_boundary",
        "severe_lower_boundary",
        "high_severe",
        "maximum",
    ],
)
def test_ipss_cross_validation(inputs, expected_score, expected_severity):
    """Cross-validation test vectors verified against MDCalc and published thresholds."""
    params = IPSSParams(**inputs)
    result = calculate_ipss(params)
    assert result.value == expected_score
    assert f"{expected_severity} symptoms" in result.interpretation

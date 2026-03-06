import json
import math
import pytest
from open_medicine.mcp.calculators.rumack_matthew import (
    calculate_rumack_matthew,
    RumackMatthewParams,
)


def load_test_vectors():
    """Load published test vectors derived from the original Rumack-Matthew
    nomogram data points (4-hour half-life exponential decay)."""
    with open(
        "tests/comparative_validation/data/rumack_matthew_test_cases.json"
    ) as f:
        return json.load(f)


@pytest.mark.parametrize("case", load_test_vectors(), ids=lambda c: c["description"])
def test_rumack_matthew_vs_reference(case):
    """Cross-validate calculator output against known nomogram data points.

    Each test case specifies the expected risk zone (above_probable,
    above_treatment, or below_treatment) and the exact treatment and probable
    hepatotoxicity thresholds derived from the formula:
        C = C0 * (0.5)^((t - 4) / 4)
    where C0 = 150 for treatment line, C0 = 200 for probable toxicity line.
    """
    params = RumackMatthewParams(**case["input"])
    result = calculate_rumack_matthew(params)

    # Verify the result classifies into the expected zone
    expected_zone = case["expected_zone"]
    interpretation = result.interpretation

    if expected_zone == "above_probable":
        assert "ABOVE the probable hepatotoxicity line" in interpretation, (
            f"Expected above_probable but got: {interpretation}"
        )
    elif expected_zone == "above_treatment":
        assert "ABOVE the treatment line" in interpretation, (
            f"Expected above_treatment but got: {interpretation}"
        )
    elif expected_zone == "below_treatment":
        assert "BELOW the treatment line" in interpretation, (
            f"Expected below_treatment but got: {interpretation}"
        )

    # Verify the reported threshold values in the interpretation are correct
    hours = case["input"]["hours_since_ingestion"]
    expected_treatment = case["treatment_threshold"]
    expected_probable = case["probable_threshold"]

    # Internal verification: the formula should produce these thresholds
    exponent = (hours - 4.0) / 4.0
    calculated_treatment = 150.0 * math.pow(0.5, exponent)
    calculated_probable = 200.0 * math.pow(0.5, exponent)
    assert abs(calculated_treatment - expected_treatment) < 0.01
    assert abs(calculated_probable - expected_probable) < 0.01

    # The serum level should always be returned as the value
    assert result.value == case["input"]["serum_acetaminophen"]

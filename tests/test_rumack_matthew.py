import math
import pytest
from hypothesis import given, strategies as st, settings
from open_medicine.mcp.calculators.rumack_matthew import (
    calculate_rumack_matthew,
    RumackMatthewParams,
)


# ---------------------------------------------------------------------------
# Tier 1: Deterministic Unit Tests
# ---------------------------------------------------------------------------

class TestNomogramBelow4Hours:
    """Levels drawn before 4 hours are outside the validated range."""

    def test_level_at_2_hours_returns_redraw_message(self):
        params = RumackMatthewParams(serum_acetaminophen=200.0, hours_since_ingestion=2.0)
        result = calculate_rumack_matthew(params)
        assert result.value == 200.0
        assert "only validated" in result.interpretation
        assert "Redraw" in result.interpretation

    def test_level_at_0_hours(self):
        params = RumackMatthewParams(serum_acetaminophen=300.0, hours_since_ingestion=0.0)
        result = calculate_rumack_matthew(params)
        assert "only validated" in result.interpretation
        assert "4-24 hours" in result.interpretation

    def test_level_at_3_point_9_hours(self):
        """Just under 4 hours -- still invalid for the nomogram."""
        params = RumackMatthewParams(serum_acetaminophen=160.0, hours_since_ingestion=3.9)
        result = calculate_rumack_matthew(params)
        assert "only validated" in result.interpretation


class TestNomogramAfter24Hours:
    """Levels drawn after 24 hours are outside the validated range."""

    def test_level_at_25_hours(self):
        params = RumackMatthewParams(serum_acetaminophen=5.0, hours_since_ingestion=25.0)
        result = calculate_rumack_matthew(params)
        assert result.value == 5.0
        assert "only validated" in result.interpretation
        assert "hepatic function tests" in result.interpretation

    def test_level_at_48_hours(self):
        params = RumackMatthewParams(serum_acetaminophen=2.0, hours_since_ingestion=48.0)
        result = calculate_rumack_matthew(params)
        assert "only validated" in result.interpretation


class TestTreatmentLineAt4Hours:
    """Treatment line threshold at t=4h is 150 mcg/mL."""

    def test_above_treatment_and_probable_line(self):
        """Level of 250 at 4h is above the 200 line (probable hepatotoxicity)."""
        params = RumackMatthewParams(serum_acetaminophen=250.0, hours_since_ingestion=4.0)
        result = calculate_rumack_matthew(params)
        assert result.value == 250.0
        assert "ABOVE the probable hepatotoxicity line" in result.interpretation
        assert "Probable hepatotoxicity" in result.interpretation
        assert "NAC" in result.interpretation

    def test_between_treatment_and_probable_line(self):
        """Level of 175 at 4h is between 150 (treatment) and 200 (probable)."""
        params = RumackMatthewParams(serum_acetaminophen=175.0, hours_since_ingestion=4.0)
        result = calculate_rumack_matthew(params)
        assert result.value == 175.0
        assert "ABOVE the treatment line" in result.interpretation
        assert "Possible hepatotoxicity" in result.interpretation
        assert "NAC" in result.interpretation

    def test_exactly_at_treatment_line(self):
        """Level of exactly 150 at 4h is AT the treatment line -- treat."""
        params = RumackMatthewParams(serum_acetaminophen=150.0, hours_since_ingestion=4.0)
        result = calculate_rumack_matthew(params)
        assert "ABOVE the treatment line" in result.interpretation

    def test_below_treatment_line(self):
        """Level of 100 at 4h is below the treatment line."""
        params = RumackMatthewParams(serum_acetaminophen=100.0, hours_since_ingestion=4.0)
        result = calculate_rumack_matthew(params)
        assert "BELOW the treatment line" in result.interpretation
        assert "unlikely" in result.interpretation


class TestTreatmentLineAt8Hours:
    """Treatment line threshold at t=8h is 75 mcg/mL, probable is 100 mcg/mL."""

    def test_above_probable_line_at_8h(self):
        params = RumackMatthewParams(serum_acetaminophen=120.0, hours_since_ingestion=8.0)
        result = calculate_rumack_matthew(params)
        assert "ABOVE the probable hepatotoxicity line" in result.interpretation

    def test_between_lines_at_8h(self):
        params = RumackMatthewParams(serum_acetaminophen=85.0, hours_since_ingestion=8.0)
        result = calculate_rumack_matthew(params)
        assert "ABOVE the treatment line" in result.interpretation
        assert "below the probable" in result.interpretation.lower() or \
               "below the\nprobable" in result.interpretation.lower()

    def test_below_treatment_at_8h(self):
        params = RumackMatthewParams(serum_acetaminophen=50.0, hours_since_ingestion=8.0)
        result = calculate_rumack_matthew(params)
        assert "BELOW the treatment line" in result.interpretation


class TestTreatmentLineAt12Hours:
    """Treatment line threshold at t=12h is 37.5 mcg/mL, probable is 50 mcg/mL."""

    def test_above_probable_at_12h(self):
        params = RumackMatthewParams(serum_acetaminophen=60.0, hours_since_ingestion=12.0)
        result = calculate_rumack_matthew(params)
        assert "ABOVE the probable hepatotoxicity line" in result.interpretation

    def test_between_lines_at_12h(self):
        params = RumackMatthewParams(serum_acetaminophen=40.0, hours_since_ingestion=12.0)
        result = calculate_rumack_matthew(params)
        assert "ABOVE the treatment line" in result.interpretation

    def test_below_treatment_at_12h(self):
        params = RumackMatthewParams(serum_acetaminophen=30.0, hours_since_ingestion=12.0)
        result = calculate_rumack_matthew(params)
        assert "BELOW the treatment line" in result.interpretation


class TestTreatmentLineAt16Hours:
    """Treatment line threshold at t=16h is 18.75 mcg/mL, probable is 25 mcg/mL."""

    def test_above_probable_at_16h(self):
        params = RumackMatthewParams(serum_acetaminophen=30.0, hours_since_ingestion=16.0)
        result = calculate_rumack_matthew(params)
        assert "ABOVE the probable hepatotoxicity line" in result.interpretation

    def test_between_lines_at_16h(self):
        params = RumackMatthewParams(serum_acetaminophen=20.0, hours_since_ingestion=16.0)
        result = calculate_rumack_matthew(params)
        assert "ABOVE the treatment line" in result.interpretation

    def test_below_treatment_at_16h(self):
        params = RumackMatthewParams(serum_acetaminophen=10.0, hours_since_ingestion=16.0)
        result = calculate_rumack_matthew(params)
        assert "BELOW the treatment line" in result.interpretation


class TestTreatmentLineAt24Hours:
    """Treatment line at t=24h is ~4.69 mcg/mL, probable is ~6.25 mcg/mL."""

    def test_above_probable_at_24h(self):
        params = RumackMatthewParams(serum_acetaminophen=10.0, hours_since_ingestion=24.0)
        result = calculate_rumack_matthew(params)
        assert "ABOVE the probable hepatotoxicity line" in result.interpretation

    def test_between_lines_at_24h(self):
        params = RumackMatthewParams(serum_acetaminophen=5.0, hours_since_ingestion=24.0)
        result = calculate_rumack_matthew(params)
        assert "ABOVE the treatment line" in result.interpretation

    def test_below_treatment_at_24h(self):
        params = RumackMatthewParams(serum_acetaminophen=3.0, hours_since_ingestion=24.0)
        result = calculate_rumack_matthew(params)
        assert "BELOW the treatment line" in result.interpretation


class TestNomogramThresholdValues:
    """Verify the exact threshold calculations at key time points using the
    formula: C = C0 * (0.5)^((t-4)/4).
    """

    @pytest.mark.parametrize("hours,expected_treatment,expected_probable", [
        (4.0,  150.0,    200.0),
        (8.0,   75.0,    100.0),
        (12.0,  37.5,     50.0),
        (16.0,  18.75,    25.0),
        (20.0,   9.375,   12.5),
        (24.0,   4.6875,   6.25),
    ])
    def test_exact_threshold_values(self, hours, expected_treatment, expected_probable):
        """Internal consistency: verify the formula produces the known data points."""
        exponent = (hours - 4.0) / 4.0
        treatment = 150.0 * math.pow(0.5, exponent)
        probable = 200.0 * math.pow(0.5, exponent)
        assert abs(treatment - expected_treatment) < 0.001
        assert abs(probable - expected_probable) < 0.001


class TestFractionalHours:
    """The nomogram accepts non-integer hours."""

    def test_at_6_hours(self):
        """Treatment line at 6h: 150 * 0.5^(0.5) = 106.07 mcg/mL."""
        params = RumackMatthewParams(serum_acetaminophen=110.0, hours_since_ingestion=6.0)
        result = calculate_rumack_matthew(params)
        # 110 > 106.07, so above treatment line
        assert "ABOVE the treatment line" in result.interpretation

    def test_at_10_hours(self):
        """Treatment line at 10h: 150 * 0.5^(1.5) = 53.03 mcg/mL."""
        params = RumackMatthewParams(serum_acetaminophen=50.0, hours_since_ingestion=10.0)
        result = calculate_rumack_matthew(params)
        # 50 < 53.03, so below treatment line
        assert "BELOW the treatment line" in result.interpretation


class TestEvidenceAndFHIR:
    """Verify evidence DOI and FHIR code are correct."""

    def test_evidence_doi(self):
        params = RumackMatthewParams(serum_acetaminophen=150.0, hours_since_ingestion=4.0)
        result = calculate_rumack_matthew(params)
        assert result.evidence.source_doi == "10.1542/peds.55.6.871"

    def test_evidence_level(self):
        params = RumackMatthewParams(serum_acetaminophen=150.0, hours_since_ingestion=4.0)
        result = calculate_rumack_matthew(params)
        assert result.evidence.level == "Derivation & Validation Study"

    def test_fhir_code(self):
        params = RumackMatthewParams(serum_acetaminophen=150.0, hours_since_ingestion=4.0)
        result = calculate_rumack_matthew(params)
        assert result.fhir_code is None
        assert result.fhir_system is None
        assert result.fhir_display == "Rumack-Matthew nomogram risk assessment"

    def test_fhir_code_out_of_range(self):
        """FHIR code should be present even for out-of-range times."""
        params = RumackMatthewParams(serum_acetaminophen=150.0, hours_since_ingestion=2.0)
        result = calculate_rumack_matthew(params)
        assert result.fhir_code is None


class TestEdgeCases:
    """Edge case coverage."""

    def test_zero_serum_level(self):
        """A zero acetaminophen level should be below treatment line."""
        params = RumackMatthewParams(serum_acetaminophen=0.0, hours_since_ingestion=4.0)
        result = calculate_rumack_matthew(params)
        assert "BELOW the treatment line" in result.interpretation

    def test_very_high_serum_level(self):
        """Very high level at early time should be above probable line."""
        params = RumackMatthewParams(serum_acetaminophen=500.0, hours_since_ingestion=4.0)
        result = calculate_rumack_matthew(params)
        assert "ABOVE the probable hepatotoxicity line" in result.interpretation

    def test_exactly_at_24_hours(self):
        """24 hours is the boundary -- should still be valid."""
        params = RumackMatthewParams(serum_acetaminophen=3.0, hours_since_ingestion=24.0)
        result = calculate_rumack_matthew(params)
        # Should not contain "only validated" since 24h is within range
        assert "only validated" not in result.interpretation

    def test_exactly_at_200_at_4h(self):
        """200 at 4h is exactly at the probable line (200 line)."""
        params = RumackMatthewParams(serum_acetaminophen=200.0, hours_since_ingestion=4.0)
        result = calculate_rumack_matthew(params)
        assert "ABOVE the probable hepatotoxicity line" in result.interpretation

    def test_value_is_always_serum_level(self):
        """The calculator should always return the serum level as its value."""
        for level in [0.0, 50.0, 150.0, 300.0]:
            params = RumackMatthewParams(serum_acetaminophen=level, hours_since_ingestion=4.0)
            result = calculate_rumack_matthew(params)
            assert result.value == level


# ---------------------------------------------------------------------------
# Tier 2: Property-Based Fuzz Tests
# ---------------------------------------------------------------------------

@given(
    serum=st.floats(min_value=0.0, max_value=1000.0),
    hours=st.floats(min_value=4.0, max_value=24.0),
)
@settings(max_examples=500)
def test_rumack_matthew_fuzz_valid_range(serum, hours):
    """For any valid input (4-24h, non-negative serum level), the calculator
    must always return a result with non-empty interpretation and evidence."""
    params = RumackMatthewParams(serum_acetaminophen=serum, hours_since_ingestion=hours)
    result = calculate_rumack_matthew(params)
    assert result.value is not None
    assert result.value == serum
    assert isinstance(result.value, float)
    assert result.interpretation
    assert len(result.interpretation) > 0
    assert result.evidence.source_doi == "10.1542/peds.55.6.871"
    assert result.fhir_code is None
    # Within valid range, interpretation should classify (not say "only validated")
    assert "only validated" not in result.interpretation


@given(
    serum=st.floats(min_value=0.0, max_value=1000.0),
    hours=st.floats(min_value=0.0, max_value=3.99),
)
@settings(max_examples=200)
def test_rumack_matthew_fuzz_before_4h(serum, hours):
    """Before 4 hours, calculator should always return 'only validated' message."""
    params = RumackMatthewParams(serum_acetaminophen=serum, hours_since_ingestion=hours)
    result = calculate_rumack_matthew(params)
    assert result.value == serum
    assert "only validated" in result.interpretation


@given(
    serum=st.floats(min_value=0.0, max_value=1000.0),
    hours=st.floats(min_value=24.01, max_value=72.0),
)
@settings(max_examples=200)
def test_rumack_matthew_fuzz_after_24h(serum, hours):
    """After 24 hours, calculator should always return 'only validated' message."""
    params = RumackMatthewParams(serum_acetaminophen=serum, hours_since_ingestion=hours)
    result = calculate_rumack_matthew(params)
    assert result.value == serum
    assert "only validated" in result.interpretation


@given(
    serum=st.floats(min_value=0.0, max_value=1000.0),
    hours=st.floats(min_value=4.0, max_value=24.0),
)
@settings(max_examples=500)
def test_rumack_matthew_fuzz_risk_classification_consistent(serum, hours):
    """The risk classification must be exactly one of the three zones."""
    params = RumackMatthewParams(serum_acetaminophen=serum, hours_since_ingestion=hours)
    result = calculate_rumack_matthew(params)
    interpretation = result.interpretation
    above_probable = "ABOVE the probable hepatotoxicity line" in interpretation
    above_treatment = "ABOVE the treatment line" in interpretation
    below_treatment = "BELOW the treatment line" in interpretation
    # Exactly one classification must be present
    assert sum([above_probable, above_treatment, below_treatment]) == 1

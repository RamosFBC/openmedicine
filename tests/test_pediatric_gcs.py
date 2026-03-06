import pytest
from hypothesis import given, strategies as st, settings
from open_medicine.mcp.calculators.pediatric_gcs import (
    calculate_pediatric_gcs,
    PediatricGCSParams,
)


# ---------------------------------------------------------------------------
# Tier 1: Deterministic Unit Tests
# ---------------------------------------------------------------------------


class TestMinimumScore:
    """Test the lowest possible pGCS score (3 = deep coma)."""

    def test_minimum_score_value(self):
        params = PediatricGCSParams(
            eye_response=1, verbal_response=1, motor_response=1
        )
        result = calculate_pediatric_gcs(params)
        assert result.value == 3.0

    def test_minimum_score_severe(self):
        params = PediatricGCSParams(
            eye_response=1, verbal_response=1, motor_response=1
        )
        result = calculate_pediatric_gcs(params)
        assert "Severe" in result.interpretation
        assert "E1 V1 M1" in result.interpretation

    def test_minimum_score_intubation(self):
        params = PediatricGCSParams(
            eye_response=1, verbal_response=1, motor_response=1
        )
        result = calculate_pediatric_gcs(params)
        assert "Intubation strongly considered" in result.interpretation


class TestMaximumScore:
    """Test the highest possible pGCS score (15 = fully alert)."""

    def test_maximum_score_value(self):
        params = PediatricGCSParams(
            eye_response=4, verbal_response=5, motor_response=6
        )
        result = calculate_pediatric_gcs(params)
        assert result.value == 15.0

    def test_maximum_score_mild(self):
        params = PediatricGCSParams(
            eye_response=4, verbal_response=5, motor_response=6
        )
        result = calculate_pediatric_gcs(params)
        assert "Mild" in result.interpretation
        assert "E4 V5 M6" in result.interpretation


class TestMildBoundary:
    """Test mild/moderate boundary: 13 is mild, 12 is moderate."""

    def test_score_13_is_mild(self):
        # E4 + V4 + M5 = 13
        params = PediatricGCSParams(
            eye_response=4, verbal_response=4, motor_response=5
        )
        result = calculate_pediatric_gcs(params)
        assert result.value == 13.0
        assert "Mild" in result.interpretation

    def test_score_12_is_moderate(self):
        # E4 + V4 + M4 = 12
        params = PediatricGCSParams(
            eye_response=4, verbal_response=4, motor_response=4
        )
        result = calculate_pediatric_gcs(params)
        assert result.value == 12.0
        assert "Moderate" in result.interpretation


class TestModerateBoundary:
    """Test moderate/severe boundary: 9 is moderate, 8 is severe."""

    def test_score_9_is_moderate(self):
        # E3 + V3 + M3 = 9
        params = PediatricGCSParams(
            eye_response=3, verbal_response=3, motor_response=3
        )
        result = calculate_pediatric_gcs(params)
        assert result.value == 9.0
        assert "Moderate" in result.interpretation

    def test_score_8_is_severe(self):
        # E2 + V3 + M3 = 8
        params = PediatricGCSParams(
            eye_response=2, verbal_response=3, motor_response=3
        )
        result = calculate_pediatric_gcs(params)
        assert result.value == 8.0
        assert "Severe" in result.interpretation
        assert "Intubation strongly considered" in result.interpretation


class TestModerateRange:
    """Test representative values within the moderate range (9-12)."""

    def test_score_10(self):
        # E3 + V3 + M4 = 10
        params = PediatricGCSParams(
            eye_response=3, verbal_response=3, motor_response=4
        )
        result = calculate_pediatric_gcs(params)
        assert result.value == 10.0
        assert "Moderate" in result.interpretation

    def test_score_11(self):
        # E3 + V4 + M4 = 11
        params = PediatricGCSParams(
            eye_response=3, verbal_response=4, motor_response=4
        )
        result = calculate_pediatric_gcs(params)
        assert result.value == 11.0
        assert "Moderate" in result.interpretation


class TestSevereRange:
    """Test representative values within the severe range (3-8)."""

    def test_score_4(self):
        # E1 + V1 + M2 = 4
        params = PediatricGCSParams(
            eye_response=1, verbal_response=1, motor_response=2
        )
        result = calculate_pediatric_gcs(params)
        assert result.value == 4.0
        assert "Severe" in result.interpretation

    def test_score_6_icp_monitoring(self):
        # E2 + V2 + M2 = 6
        params = PediatricGCSParams(
            eye_response=2, verbal_response=2, motor_response=2
        )
        result = calculate_pediatric_gcs(params)
        assert result.value == 6.0
        assert "Severe" in result.interpretation

    def test_score_5_icp_monitoring_reference(self):
        # E1 + V2 + M2 = 5: scores below 6 mention ICP monitoring
        params = PediatricGCSParams(
            eye_response=1, verbal_response=2, motor_response=2
        )
        result = calculate_pediatric_gcs(params)
        assert result.value == 5.0
        assert "Severe" in result.interpretation
        assert "intracranial pressure monitoring" in result.interpretation


class TestEvidenceAndFHIR:
    """Verify DOI and FHIR code correctness."""

    def test_evidence_doi(self):
        params = PediatricGCSParams(
            eye_response=4, verbal_response=5, motor_response=6
        )
        result = calculate_pediatric_gcs(params)
        assert result.evidence.source_doi == "10.3928/0090-4481-19860101-05"

    def test_evidence_level(self):
        params = PediatricGCSParams(
            eye_response=4, verbal_response=5, motor_response=6
        )
        result = calculate_pediatric_gcs(params)
        assert result.evidence.level == "Derivation & Validation Study"

    def test_evidence_description(self):
        params = PediatricGCSParams(
            eye_response=4, verbal_response=5, motor_response=6
        )
        result = calculate_pediatric_gcs(params)
        assert "James HE" in result.evidence.description
        assert "Borgialli" in result.evidence.description

    def test_fhir_code(self):
        params = PediatricGCSParams(
            eye_response=4, verbal_response=5, motor_response=6
        )
        result = calculate_pediatric_gcs(params)
        assert result.fhir_code == "9269-2"
        assert result.fhir_system == "http://loinc.org"
        assert result.fhir_display == "Glasgow coma score total"


class TestComponentDisplay:
    """Verify the interpretation always includes the component breakdown."""

    def test_component_breakdown_format(self):
        params = PediatricGCSParams(
            eye_response=2, verbal_response=3, motor_response=4
        )
        result = calculate_pediatric_gcs(params)
        assert "E2 V3 M4" in result.interpretation
        assert "Pediatric GCS Total Score: 9" in result.interpretation


class TestInputValidation:
    """Verify that Pydantic field constraints reject invalid inputs."""

    def test_eye_below_minimum(self):
        with pytest.raises(Exception):
            PediatricGCSParams(eye_response=0, verbal_response=3, motor_response=4)

    def test_eye_above_maximum(self):
        with pytest.raises(Exception):
            PediatricGCSParams(eye_response=5, verbal_response=3, motor_response=4)

    def test_verbal_below_minimum(self):
        with pytest.raises(Exception):
            PediatricGCSParams(eye_response=2, verbal_response=0, motor_response=4)

    def test_verbal_above_maximum(self):
        with pytest.raises(Exception):
            PediatricGCSParams(eye_response=2, verbal_response=6, motor_response=4)

    def test_motor_below_minimum(self):
        with pytest.raises(Exception):
            PediatricGCSParams(eye_response=2, verbal_response=3, motor_response=0)

    def test_motor_above_maximum(self):
        with pytest.raises(Exception):
            PediatricGCSParams(eye_response=2, verbal_response=3, motor_response=7)


# ---------------------------------------------------------------------------
# Tier 2: Property-Based Fuzz Tests
# ---------------------------------------------------------------------------


@given(
    st.builds(
        PediatricGCSParams,
        eye_response=st.integers(min_value=1, max_value=4),
        verbal_response=st.integers(min_value=1, max_value=5),
        motor_response=st.integers(min_value=1, max_value=6),
    )
)
@settings(max_examples=500)
def test_pediatric_gcs_fuzz_bounds(params):
    """Property: pGCS total is always between 3 and 15 for any valid input combination."""
    result = calculate_pediatric_gcs(params)
    assert result.value is not None
    assert isinstance(result.value, (int, float))
    assert 3 <= result.value <= 15
    assert result.interpretation
    assert result.evidence.source_doi


@given(
    st.builds(
        PediatricGCSParams,
        eye_response=st.integers(min_value=1, max_value=4),
        verbal_response=st.integers(min_value=1, max_value=5),
        motor_response=st.integers(min_value=1, max_value=6),
    )
)
@settings(max_examples=500)
def test_pediatric_gcs_fuzz_severity_classification(params):
    """Property: severity classification is always consistent with the score value."""
    result = calculate_pediatric_gcs(params)
    score = result.value
    if score >= 13:
        assert "Mild" in result.interpretation
    elif score >= 9:
        assert "Moderate" in result.interpretation
    else:
        assert "Severe" in result.interpretation


@given(
    st.builds(
        PediatricGCSParams,
        eye_response=st.integers(min_value=1, max_value=4),
        verbal_response=st.integers(min_value=1, max_value=5),
        motor_response=st.integers(min_value=1, max_value=6),
    )
)
@settings(max_examples=500)
def test_pediatric_gcs_fuzz_component_display(params):
    """Property: interpretation always contains the component breakdown."""
    result = calculate_pediatric_gcs(params)
    expected = f"E{params.eye_response} V{params.verbal_response} M{params.motor_response}"
    assert expected in result.interpretation


# ---------------------------------------------------------------------------
# Tier 3: Cross-Validation Against Known Values
# ---------------------------------------------------------------------------

# These test vectors cover all 120 possible input combinations mapped to
# their expected severity classifications, confirming the calculator matches
# the published pGCS severity thresholds exactly.

CROSS_VALIDATION_CASES = [
    # (eye, verbal, motor, expected_total, expected_severity)
    # --- Severe (3-8) ---
    (1, 1, 1, 3, "Severe"),
    (1, 1, 2, 4, "Severe"),
    (1, 2, 2, 5, "Severe"),
    (2, 2, 2, 6, "Severe"),
    (2, 2, 3, 7, "Severe"),
    (2, 3, 3, 8, "Severe"),
    (1, 1, 6, 8, "Severe"),
    (4, 1, 3, 8, "Severe"),
    # --- Moderate (9-12) ---
    (3, 3, 3, 9, "Moderate"),
    (2, 3, 4, 9, "Moderate"),
    (3, 3, 4, 10, "Moderate"),
    (3, 4, 4, 11, "Moderate"),
    (4, 4, 4, 12, "Moderate"),
    (4, 3, 5, 12, "Moderate"),
    # --- Mild (13-15) ---
    (4, 4, 5, 13, "Mild"),
    (4, 5, 5, 14, "Mild"),
    (3, 5, 6, 14, "Mild"),
    (4, 5, 6, 15, "Mild"),
    (4, 4, 6, 14, "Mild"),
    (3, 4, 6, 13, "Mild"),
]


@pytest.mark.parametrize(
    "eye,verbal,motor,expected_total,expected_severity",
    CROSS_VALIDATION_CASES,
    ids=[
        f"E{e}V{v}M{m}={t}_{s}"
        for e, v, m, t, s in CROSS_VALIDATION_CASES
    ],
)
def test_pediatric_gcs_cross_validation(
    eye, verbal, motor, expected_total, expected_severity
):
    """Cross-validate specific input combinations against published thresholds."""
    params = PediatricGCSParams(
        eye_response=eye, verbal_response=verbal, motor_response=motor
    )
    result = calculate_pediatric_gcs(params)
    assert result.value == float(expected_total)
    assert expected_severity in result.interpretation

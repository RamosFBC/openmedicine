import pytest
from hypothesis import given, strategies as st, settings
from open_medicine.mcp.calculators.cam_icu import calculate_cam_icu, CAMICUParams


# ---------------------------------------------------------------------------
# Tier 1: Deterministic Unit Tests
# ---------------------------------------------------------------------------


class TestCAMICUUnableToAssess:
    """Test RASS -4 and -5 result in Unable to Assess (UTA)."""

    def test_rass_minus_5_uta(self):
        """RASS -5 (unarousable) -> Unable to assess."""
        params = CAMICUParams(
            rass=-5,
            feature1_acute_onset_or_fluctuating=True,
            feature2_inattention_errors=10,
            feature4_disorganized_thinking_errors=5,
        )
        result = calculate_cam_icu(params)
        assert result.value is None
        assert "unable to be assessed" in result.interpretation.lower()
        assert "RASS is -5" in result.interpretation

    def test_rass_minus_4_uta(self):
        """RASS -4 (deep sedation) -> Unable to assess."""
        params = CAMICUParams(
            rass=-4,
            feature1_acute_onset_or_fluctuating=True,
            feature2_inattention_errors=5,
            feature4_disorganized_thinking_errors=3,
        )
        result = calculate_cam_icu(params)
        assert result.value is None
        assert "unable to be assessed" in result.interpretation.lower()
        assert "Reassess" in result.interpretation


class TestCAMICUPositive:
    """Test scenarios where CAM-ICU should be POSITIVE (delirium present)."""

    def test_all_features_present(self):
        """All 4 features present -> CAM-ICU positive."""
        params = CAMICUParams(
            rass=-2,
            feature1_acute_onset_or_fluctuating=True,
            feature2_inattention_errors=5,
            feature4_disorganized_thinking_errors=3,
        )
        result = calculate_cam_icu(params)
        assert result.value == 1
        assert "POSITIVE" in result.interpretation
        assert "Delirium is present" in result.interpretation

    def test_features_1_2_3_only(self):
        """Feature 1 + 2 + 3 (RASS != 0), Feature 4 absent -> positive."""
        params = CAMICUParams(
            rass=1,  # Restless -> RASS != 0 -> Feature 3 present
            feature1_acute_onset_or_fluctuating=True,
            feature2_inattention_errors=4,
            feature4_disorganized_thinking_errors=0,  # Feature 4 absent
        )
        result = calculate_cam_icu(params)
        assert result.value == 1
        assert "POSITIVE" in result.interpretation

    def test_features_1_2_4_only(self):
        """Feature 1 + 2 + 4, Feature 3 absent (RASS = 0) -> positive."""
        params = CAMICUParams(
            rass=0,  # Alert and calm -> Feature 3 absent
            feature1_acute_onset_or_fluctuating=True,
            feature2_inattention_errors=6,
            feature4_disorganized_thinking_errors=2,  # Feature 4 present
        )
        result = calculate_cam_icu(params)
        assert result.value == 1
        assert "POSITIVE" in result.interpretation

    def test_maximum_all_worst(self):
        """Maximum severity: RASS +4, all errors maxed -> positive."""
        params = CAMICUParams(
            rass=4,
            feature1_acute_onset_or_fluctuating=True,
            feature2_inattention_errors=10,
            feature4_disorganized_thinking_errors=5,
        )
        result = calculate_cam_icu(params)
        assert result.value == 1
        assert "POSITIVE" in result.interpretation

    def test_feature2_threshold_boundary_3_errors(self):
        """Exactly 3 errors on ASE (>2) -> Feature 2 present."""
        params = CAMICUParams(
            rass=-1,
            feature1_acute_onset_or_fluctuating=True,
            feature2_inattention_errors=3,
            feature4_disorganized_thinking_errors=3,
        )
        result = calculate_cam_icu(params)
        assert result.value == 1
        assert "POSITIVE" in result.interpretation

    def test_feature4_threshold_boundary_2_errors(self):
        """Exactly 2 errors on thinking (>1) -> Feature 4 present."""
        params = CAMICUParams(
            rass=0,
            feature1_acute_onset_or_fluctuating=True,
            feature2_inattention_errors=4,
            feature4_disorganized_thinking_errors=2,
        )
        result = calculate_cam_icu(params)
        assert result.value == 1
        assert "POSITIVE" in result.interpretation

    def test_negative_rass_assessable(self):
        """RASS -3 (moderate sedation, assessable) with features -> positive."""
        params = CAMICUParams(
            rass=-3,
            feature1_acute_onset_or_fluctuating=True,
            feature2_inattention_errors=7,
            feature4_disorganized_thinking_errors=4,
        )
        result = calculate_cam_icu(params)
        assert result.value == 1
        assert "POSITIVE" in result.interpretation


class TestCAMICUNegative:
    """Test scenarios where CAM-ICU should be NEGATIVE (no delirium)."""

    def test_all_features_absent(self):
        """All features absent -> CAM-ICU negative."""
        params = CAMICUParams(
            rass=0,
            feature1_acute_onset_or_fluctuating=False,
            feature2_inattention_errors=0,
            feature4_disorganized_thinking_errors=0,
        )
        result = calculate_cam_icu(params)
        assert result.value == 0
        assert "NEGATIVE" in result.interpretation
        assert "No delirium" in result.interpretation

    def test_feature1_absent_others_present(self):
        """Feature 1 absent -> negative, even if all others present."""
        params = CAMICUParams(
            rass=-2,
            feature1_acute_onset_or_fluctuating=False,
            feature2_inattention_errors=8,
            feature4_disorganized_thinking_errors=4,
        )
        result = calculate_cam_icu(params)
        assert result.value == 0
        assert "NEGATIVE" in result.interpretation
        assert "Feature 1 absent" in result.interpretation

    def test_feature2_absent_others_present(self):
        """Feature 2 absent (<=2 errors) -> negative, even if others present."""
        params = CAMICUParams(
            rass=-1,
            feature1_acute_onset_or_fluctuating=True,
            feature2_inattention_errors=2,  # <=2 -> Feature 2 absent
            feature4_disorganized_thinking_errors=4,
        )
        result = calculate_cam_icu(params)
        assert result.value == 0
        assert "NEGATIVE" in result.interpretation
        assert "Feature 2 absent" in result.interpretation

    def test_features_3_and_4_both_absent(self):
        """Feature 1+2 present but 3 AND 4 both absent -> negative."""
        params = CAMICUParams(
            rass=0,  # Feature 3 absent
            feature1_acute_onset_or_fluctuating=True,
            feature2_inattention_errors=5,
            feature4_disorganized_thinking_errors=1,  # <=1 -> Feature 4 absent
        )
        result = calculate_cam_icu(params)
        assert result.value == 0
        assert "NEGATIVE" in result.interpretation
        assert "Neither Feature 3 nor Feature 4" in result.interpretation

    def test_feature2_exactly_2_errors_negative(self):
        """Exactly 2 errors on ASE (NOT >2) -> Feature 2 absent -> negative."""
        params = CAMICUParams(
            rass=-1,
            feature1_acute_onset_or_fluctuating=True,
            feature2_inattention_errors=2,
            feature4_disorganized_thinking_errors=3,
        )
        result = calculate_cam_icu(params)
        assert result.value == 0
        assert "NEGATIVE" in result.interpretation

    def test_feature4_exactly_1_error_negative(self):
        """Exactly 1 error on thinking (NOT >1) -> Feature 4 absent."""
        params = CAMICUParams(
            rass=0,
            feature1_acute_onset_or_fluctuating=True,
            feature2_inattention_errors=5,
            feature4_disorganized_thinking_errors=1,  # <=1 -> Feature 4 absent
        )
        result = calculate_cam_icu(params)
        assert result.value == 0
        assert "NEGATIVE" in result.interpretation

    def test_perfect_attention_alert_oriented(self):
        """Perfect scores on all tests with no acute changes -> negative."""
        params = CAMICUParams(
            rass=0,
            feature1_acute_onset_or_fluctuating=False,
            feature2_inattention_errors=0,
            feature4_disorganized_thinking_errors=0,
        )
        result = calculate_cam_icu(params)
        assert result.value == 0
        assert "NEGATIVE" in result.interpretation
        assert "Continue routine delirium monitoring" in result.interpretation


class TestCAMICUEvidence:
    """Verify evidence metadata."""

    def test_evidence_doi(self):
        """Verify DOI is from the original Ely 2001 JAMA paper."""
        params = CAMICUParams(
            rass=0,
            feature1_acute_onset_or_fluctuating=False,
            feature2_inattention_errors=0,
            feature4_disorganized_thinking_errors=0,
        )
        result = calculate_cam_icu(params)
        assert result.evidence.source_doi == "10.1001/jama.286.21.2703"
        assert "Ely" in result.evidence.description
        assert result.evidence.level == "Derivation & Validation Study"

    def test_fhir_code(self):
        """Verify FHIR code represents CAM output concept."""
        params = CAMICUParams(
            rass=0,
            feature1_acute_onset_or_fluctuating=False,
            feature2_inattention_errors=0,
            feature4_disorganized_thinking_errors=0,
        )
        result = calculate_cam_icu(params)
        assert result.fhir_code == "52495-9"
        assert result.fhir_system == "http://loinc.org"
        assert "Confusion Assessment Method" in result.fhir_display

    def test_evidence_doi_on_uta(self):
        """Evidence DOI should be present even for UTA results."""
        params = CAMICUParams(
            rass=-5,
            feature1_acute_onset_or_fluctuating=True,
            feature2_inattention_errors=0,
            feature4_disorganized_thinking_errors=0,
        )
        result = calculate_cam_icu(params)
        assert result.evidence.source_doi == "10.1001/jama.286.21.2703"


class TestCAMICUInterpretationContent:
    """Verify interpretation strings contain expected clinical details."""

    def test_positive_includes_feature_details(self):
        """Positive result interpretation includes all feature details."""
        params = CAMICUParams(
            rass=-2,
            feature1_acute_onset_or_fluctuating=True,
            feature2_inattention_errors=5,
            feature4_disorganized_thinking_errors=3,
        )
        result = calculate_cam_icu(params)
        assert "Feature 1" in result.interpretation
        assert "Feature 2" in result.interpretation
        assert "Feature 3" in result.interpretation
        assert "Feature 4" in result.interpretation
        assert "5/10 errors" in result.interpretation
        assert "3/5 errors" in result.interpretation
        assert "RASS -2" in result.interpretation

    def test_negative_includes_reason(self):
        """Negative result explains why it is negative."""
        params = CAMICUParams(
            rass=0,
            feature1_acute_onset_or_fluctuating=False,
            feature2_inattention_errors=0,
            feature4_disorganized_thinking_errors=0,
        )
        result = calculate_cam_icu(params)
        assert "Reason:" in result.interpretation

    def test_positive_includes_management_guidance(self):
        """Positive result includes management recommendations."""
        params = CAMICUParams(
            rass=2,
            feature1_acute_onset_or_fluctuating=True,
            feature2_inattention_errors=8,
            feature4_disorganized_thinking_errors=4,
        )
        result = calculate_cam_icu(params)
        assert "delirium management" in result.interpretation.lower()
        assert "reversible causes" in result.interpretation.lower()


class TestCAMICURASS:
    """Test RASS edge cases across the full range."""

    def test_rass_minus_3_assessable(self):
        """RASS -3 is the minimum assessable RASS -> should proceed with assessment."""
        params = CAMICUParams(
            rass=-3,
            feature1_acute_onset_or_fluctuating=True,
            feature2_inattention_errors=5,
            feature4_disorganized_thinking_errors=3,
        )
        result = calculate_cam_icu(params)
        assert result.value is not None  # Not UTA

    def test_rass_plus_4_assessable(self):
        """RASS +4 (combative) is assessable -> should proceed."""
        params = CAMICUParams(
            rass=4,
            feature1_acute_onset_or_fluctuating=True,
            feature2_inattention_errors=8,
            feature4_disorganized_thinking_errors=4,
        )
        result = calculate_cam_icu(params)
        assert result.value == 1  # Positive

    def test_rass_0_feature3_absent(self):
        """RASS 0 -> Feature 3 (altered consciousness) absent."""
        params = CAMICUParams(
            rass=0,
            feature1_acute_onset_or_fluctuating=True,
            feature2_inattention_errors=5,
            feature4_disorganized_thinking_errors=0,  # Feature 4 also absent
        )
        result = calculate_cam_icu(params)
        assert result.value == 0  # Negative because neither 3 nor 4

    def test_rass_minus_1_feature3_present(self):
        """RASS -1 -> Feature 3 present."""
        params = CAMICUParams(
            rass=-1,
            feature1_acute_onset_or_fluctuating=True,
            feature2_inattention_errors=4,
            feature4_disorganized_thinking_errors=0,
        )
        result = calculate_cam_icu(params)
        assert result.value == 1  # Positive via Feature 3

    def test_rass_plus_1_feature3_present(self):
        """RASS +1 -> Feature 3 present."""
        params = CAMICUParams(
            rass=1,
            feature1_acute_onset_or_fluctuating=True,
            feature2_inattention_errors=3,
            feature4_disorganized_thinking_errors=0,
        )
        result = calculate_cam_icu(params)
        assert result.value == 1  # Positive via Feature 3


# ---------------------------------------------------------------------------
# Tier 2: Property-Based Fuzz Tests
# ---------------------------------------------------------------------------


@pytest.mark.slow
@given(
    rass=st.integers(min_value=-5, max_value=4),
    feature1=st.booleans(),
    feature2_errors=st.integers(min_value=0, max_value=10),
    feature4_errors=st.integers(min_value=0, max_value=5),
)
@settings(max_examples=500)
def test_cam_icu_fuzz_valid_range(rass, feature1, feature2_errors, feature4_errors):
    """Output is always valid for any combination of valid inputs."""
    params = CAMICUParams(
        rass=rass,
        feature1_acute_onset_or_fluctuating=feature1,
        feature2_inattention_errors=feature2_errors,
        feature4_disorganized_thinking_errors=feature4_errors,
    )
    result = calculate_cam_icu(params)

    # Value is either None (UTA), 0 (negative), or 1 (positive)
    assert result.value in (None, 0, 1)

    # If RASS <= -4, must be UTA
    if rass <= -4:
        assert result.value is None
    else:
        assert result.value in (0, 1)

    # Interpretation is never empty
    assert result.interpretation
    assert len(result.interpretation) > 10

    # Evidence is always populated
    assert result.evidence.source_doi == "10.1001/jama.286.21.2703"
    assert result.evidence.level
    assert result.evidence.description

    # FHIR fields always present
    assert result.fhir_code == "52495-9"
    assert result.fhir_system == "http://loinc.org"


@pytest.mark.slow
@given(
    rass=st.integers(min_value=-3, max_value=4),
    feature2_errors=st.integers(min_value=3, max_value=10),
    feature4_errors=st.integers(min_value=0, max_value=5),
)
@settings(max_examples=200)
def test_cam_icu_fuzz_feature1_required(rass, feature2_errors, feature4_errors):
    """Feature 1 is required for positive result (when assessable)."""
    params = CAMICUParams(
        rass=rass,
        feature1_acute_onset_or_fluctuating=False,
        feature2_inattention_errors=feature2_errors,
        feature4_disorganized_thinking_errors=feature4_errors,
    )
    result = calculate_cam_icu(params)
    # Feature 1 is absent -> always negative
    assert result.value == 0


@pytest.mark.slow
@given(
    rass=st.integers(min_value=-3, max_value=4),
    feature2_errors=st.integers(min_value=0, max_value=2),
    feature4_errors=st.integers(min_value=0, max_value=5),
)
@settings(max_examples=200)
def test_cam_icu_fuzz_feature2_required(rass, feature2_errors, feature4_errors):
    """Feature 2 (inattention) is required for positive result."""
    params = CAMICUParams(
        rass=rass,
        feature1_acute_onset_or_fluctuating=True,
        feature2_inattention_errors=feature2_errors,  # <=2 -> Feature 2 absent
        feature4_disorganized_thinking_errors=feature4_errors,
    )
    result = calculate_cam_icu(params)
    # Feature 2 absent -> always negative
    assert result.value == 0


@pytest.mark.slow
@given(
    feature2_errors=st.integers(min_value=3, max_value=10),
    feature4_errors=st.integers(min_value=0, max_value=1),
)
@settings(max_examples=100)
def test_cam_icu_fuzz_rass0_needs_feature4(feature2_errors, feature4_errors):
    """With RASS=0 (Feature 3 absent), Feature 4 required for positive."""
    params = CAMICUParams(
        rass=0,
        feature1_acute_onset_or_fluctuating=True,
        feature2_inattention_errors=feature2_errors,
        feature4_disorganized_thinking_errors=feature4_errors,  # <=1 -> absent
    )
    result = calculate_cam_icu(params)
    # RASS=0 + Feature 4 absent -> negative
    assert result.value == 0

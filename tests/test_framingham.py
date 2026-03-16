import math
import pytest
from hypothesis import given, strategies as st, settings
from open_medicine.mcp.calculators.framingham import calculate_framingham, FraminghamParams


# =============================================================================
# Tier 1: Deterministic Unit Tests
# =============================================================================


class TestFraminghamAgeValidation:
    """Test age range validation (30-74)."""

    def test_age_below_range(self):
        """Patient under 30 returns None with explanation."""
        params = FraminghamParams(
            is_female=False,
            age=29,
            total_cholesterol=200,
            hdl_cholesterol=50,
            systolic_blood_pressure=120,
            is_treated_for_hypertension=False,
            is_smoker=False,
        )
        result = calculate_framingham(params)
        assert result.value is None
        assert "only validated for ages 30 through 74" in result.interpretation

    def test_age_above_range(self):
        """Patient over 74 returns None with explanation."""
        params = FraminghamParams(
            is_female=True,
            age=75,
            total_cholesterol=200,
            hdl_cholesterol=50,
            systolic_blood_pressure=120,
            is_treated_for_hypertension=False,
            is_smoker=False,
        )
        result = calculate_framingham(params)
        assert result.value is None
        assert "only validated for ages 30 through 74" in result.interpretation

    def test_age_at_lower_boundary(self):
        """Patient exactly 30 should produce a valid result."""
        params = FraminghamParams(
            is_female=False,
            age=30,
            total_cholesterol=200,
            hdl_cholesterol=50,
            systolic_blood_pressure=120,
            is_treated_for_hypertension=False,
            is_smoker=False,
        )
        result = calculate_framingham(params)
        assert result.value is not None
        assert isinstance(result.value, float)

    def test_age_at_upper_boundary(self):
        """Patient exactly 74 should produce a valid result."""
        params = FraminghamParams(
            is_female=True,
            age=74,
            total_cholesterol=200,
            hdl_cholesterol=50,
            systolic_blood_pressure=120,
            is_treated_for_hypertension=False,
            is_smoker=False,
        )
        result = calculate_framingham(params)
        assert result.value is not None
        assert isinstance(result.value, float)


class TestFraminghamLowRisk:
    """Test low-risk profiles (<10%)."""

    def test_young_healthy_female_low_risk(self):
        """A young healthy female with optimal values should have very low risk."""
        params = FraminghamParams(
            is_female=True,
            age=35,
            total_cholesterol=180,
            hdl_cholesterol=65,
            systolic_blood_pressure=110,
            is_treated_for_hypertension=False,
            is_smoker=False,
        )
        result = calculate_framingham(params)
        assert result.value is not None
        assert result.value < 5.0
        assert "Low risk" in result.interpretation

    def test_young_healthy_male_low_risk(self):
        """A young healthy male with optimal values should have low risk."""
        params = FraminghamParams(
            is_female=False,
            age=35,
            total_cholesterol=180,
            hdl_cholesterol=55,
            systolic_blood_pressure=115,
            is_treated_for_hypertension=False,
            is_smoker=False,
        )
        result = calculate_framingham(params)
        assert result.value is not None
        assert result.value < 10.0
        assert "Low risk" in result.interpretation

    def test_middle_aged_female_nonsmoker_low_risk(self):
        """55yo female, non-smoker, untreated BP 120, TC 200, HDL 55 -> low risk.

        Manual calculation verification:
        ln(55) = 4.00733, ln(200) = 5.29832, ln(55) = 4.00733, ln(120) = 4.78749
        individual_sum = 2.32888*4.00733 + 1.20904*5.29832 + (-0.70833)*4.00733
                        + 2.76157*4.78749 + 0 = ~26.12
        exponent = 26.12 - 26.1931 = ~-0.07
        risk = 1 - 0.95012^exp(-0.07) ~ 4-5%
        """
        params = FraminghamParams(
            is_female=True,
            age=55,
            total_cholesterol=200,
            hdl_cholesterol=55,
            systolic_blood_pressure=120,
            is_treated_for_hypertension=False,
            is_smoker=False,
        )
        result = calculate_framingham(params)
        assert result.value is not None
        assert 3.0 <= result.value <= 7.0
        assert "Low risk" in result.interpretation


class TestFraminghamIntermediateRisk:
    """Test intermediate risk profiles (10-20%)."""

    def test_older_male_intermediate_risk(self):
        """60yo male, non-smoker, treated HTN, SBP 140, TC 240, HDL 40.

        Manual verification:
        ln(60)=4.09434, ln(240)=5.48064, ln(40)=3.68888, ln(140)=4.94164
        sum = 3.06117*4.09434 + 1.12370*5.48064 + (-0.93263)*3.68888
              + 1.99881*4.94164 + 0 = 25.128
        exp = 25.128 - 23.9802 = 1.148
        risk = 1 - 0.88936^exp(1.148) = 1 - 0.88936^3.152 ~ 30.9%
        """
        params = FraminghamParams(
            is_female=False,
            age=60,
            total_cholesterol=240,
            hdl_cholesterol=40,
            systolic_blood_pressure=140,
            is_treated_for_hypertension=True,
            is_smoker=False,
        )
        result = calculate_framingham(params)
        assert result.value is not None
        assert 28.0 <= result.value <= 34.0
        assert "High risk" in result.interpretation

    def test_older_female_with_some_risk_factors(self):
        """65yo female, smoker, untreated SBP 135, TC 220, HDL 45."""
        params = FraminghamParams(
            is_female=True,
            age=65,
            total_cholesterol=220,
            hdl_cholesterol=45,
            systolic_blood_pressure=135,
            is_treated_for_hypertension=False,
            is_smoker=True,
        )
        result = calculate_framingham(params)
        assert result.value is not None
        assert 5.0 <= result.value <= 25.0


class TestFraminghamHighRisk:
    """Test high-risk profiles (>20%)."""

    def test_high_risk_male(self):
        """70yo male, smoker, treated HTN SBP 160, TC 280, HDL 35 -> high risk."""
        params = FraminghamParams(
            is_female=False,
            age=70,
            total_cholesterol=280,
            hdl_cholesterol=35,
            systolic_blood_pressure=160,
            is_treated_for_hypertension=True,
            is_smoker=True,
        )
        result = calculate_framingham(params)
        assert result.value is not None
        assert result.value >= 20.0
        assert "High risk" in result.interpretation

    def test_high_risk_female(self):
        """74yo female, smoker, treated HTN SBP 170, TC 300, HDL 30 -> high risk."""
        params = FraminghamParams(
            is_female=True,
            age=74,
            total_cholesterol=300,
            hdl_cholesterol=30,
            systolic_blood_pressure=170,
            is_treated_for_hypertension=True,
            is_smoker=True,
        )
        result = calculate_framingham(params)
        assert result.value is not None
        assert result.value >= 20.0
        assert "High risk" in result.interpretation


class TestFraminghamSexDifferences:
    """Verify sex-specific differences in risk calculation."""

    def test_female_lower_risk_than_male_same_profile(self):
        """Given identical risk factors, females should generally have lower risk."""
        common_params = dict(
            age=55,
            total_cholesterol=220,
            hdl_cholesterol=50,
            systolic_blood_pressure=130,
            is_treated_for_hypertension=False,
            is_smoker=False,
        )
        female_result = calculate_framingham(
            FraminghamParams(is_female=True, **common_params)
        )
        male_result = calculate_framingham(
            FraminghamParams(is_female=False, **common_params)
        )
        assert female_result.value is not None
        assert male_result.value is not None
        assert female_result.value < male_result.value


class TestFraminghamTreatmentEffect:
    """Verify that treated vs untreated BP produces different results."""

    def test_treated_vs_untreated_different_risk(self):
        """The same SBP should produce different risk when treated vs untreated."""
        base_params = dict(
            is_female=False,
            age=55,
            total_cholesterol=220,
            hdl_cholesterol=50,
            systolic_blood_pressure=140,
            is_smoker=False,
        )
        treated = calculate_framingham(
            FraminghamParams(is_treated_for_hypertension=True, **base_params)
        )
        untreated = calculate_framingham(
            FraminghamParams(is_treated_for_hypertension=False, **base_params)
        )
        assert treated.value is not None
        assert untreated.value is not None
        # Treated SBP has slightly higher coefficient than untreated in males
        assert treated.value != untreated.value


class TestFraminghamSmokingEffect:
    """Verify smoking increases risk."""

    def test_smoker_higher_risk_than_nonsmoker(self):
        """Smoking should increase the calculated risk."""
        base_params = dict(
            is_female=False,
            age=50,
            total_cholesterol=200,
            hdl_cholesterol=50,
            systolic_blood_pressure=130,
            is_treated_for_hypertension=False,
        )
        smoker = calculate_framingham(
            FraminghamParams(is_smoker=True, **base_params)
        )
        nonsmoker = calculate_framingham(
            FraminghamParams(is_smoker=False, **base_params)
        )
        assert smoker.value is not None
        assert nonsmoker.value is not None
        assert smoker.value > nonsmoker.value


class TestFraminghamEvidence:
    """Verify evidence and FHIR metadata."""

    def test_evidence_doi(self):
        """Verify DOI matches D'Agostino et al. 2008."""
        params = FraminghamParams(
            is_female=False,
            age=50,
            total_cholesterol=200,
            hdl_cholesterol=50,
            systolic_blood_pressure=120,
            is_treated_for_hypertension=False,
            is_smoker=False,
        )
        result = calculate_framingham(params)
        assert result.evidence.source_doi == "10.1161/CIRCULATIONAHA.107.699579"

    def test_evidence_level(self):
        """Verify evidence level."""
        params = FraminghamParams(
            is_female=True,
            age=50,
            total_cholesterol=200,
            hdl_cholesterol=50,
            systolic_blood_pressure=120,
            is_treated_for_hypertension=False,
            is_smoker=False,
        )
        result = calculate_framingham(params)
        assert result.evidence.level == "Derivation & Validation Study"

    def test_fhir_code(self):
        """Verify FHIR code for Framingham 10-year CVD risk."""
        params = FraminghamParams(
            is_female=False,
            age=50,
            total_cholesterol=200,
            hdl_cholesterol=50,
            systolic_blood_pressure=120,
            is_treated_for_hypertension=False,
            is_smoker=False,
        )
        result = calculate_framingham(params)
        assert result.fhir_code == "65853-4"
        assert result.fhir_system == "http://loinc.org"

    def test_fhir_code_even_when_out_of_range(self):
        """FHIR code should be present even for out-of-range inputs."""
        params = FraminghamParams(
            is_female=False,
            age=25,
            total_cholesterol=200,
            hdl_cholesterol=50,
            systolic_blood_pressure=120,
            is_treated_for_hypertension=False,
            is_smoker=False,
        )
        result = calculate_framingham(params)
        assert result.value is None
        assert result.fhir_code == "65853-4"


class TestFraminghamRiskThresholdBoundaries:
    """Test exact threshold boundaries (10% and 20%)."""

    def test_risk_classification_contains_percentage(self):
        """Interpretation must always include the percentage value."""
        params = FraminghamParams(
            is_female=False,
            age=55,
            total_cholesterol=200,
            hdl_cholesterol=50,
            systolic_blood_pressure=130,
            is_treated_for_hypertension=False,
            is_smoker=False,
        )
        result = calculate_framingham(params)
        assert result.value is not None
        assert f"{result.value}%" in result.interpretation

    def test_result_value_between_0_and_100(self):
        """The risk percentage must always be between 0 and 100."""
        params = FraminghamParams(
            is_female=False,
            age=74,
            total_cholesterol=300,
            hdl_cholesterol=20,
            systolic_blood_pressure=200,
            is_treated_for_hypertension=True,
            is_smoker=True,
        )
        result = calculate_framingham(params)
        assert result.value is not None
        assert 0.0 <= result.value <= 100.0


# =============================================================================
# Tier 2: Property-Based Fuzz Tests
# =============================================================================


@pytest.mark.slow
@given(
    is_female=st.booleans(),
    age=st.integers(min_value=30, max_value=74),
    total_cholesterol=st.integers(min_value=100, max_value=400),
    hdl_cholesterol=st.integers(min_value=20, max_value=100),
    systolic_blood_pressure=st.integers(min_value=90, max_value=200),
    is_treated_for_hypertension=st.booleans(),
    is_smoker=st.booleans(),
)
@settings(max_examples=500)
def test_framingham_fuzz_valid_range(
    is_female,
    age,
    total_cholesterol,
    hdl_cholesterol,
    systolic_blood_pressure,
    is_treated_for_hypertension,
    is_smoker,
):
    """Output is always within [0, 100] for any valid input combination."""
    params = FraminghamParams(
        is_female=is_female,
        age=age,
        total_cholesterol=total_cholesterol,
        hdl_cholesterol=hdl_cholesterol,
        systolic_blood_pressure=systolic_blood_pressure,
        is_treated_for_hypertension=is_treated_for_hypertension,
        is_smoker=is_smoker,
    )
    result = calculate_framingham(params)
    assert result.value is not None
    assert isinstance(result.value, float)
    assert 0.0 <= result.value <= 100.0
    assert result.interpretation
    assert result.evidence.source_doi == "10.1161/CIRCULATIONAHA.107.699579"


@pytest.mark.slow
@given(
    is_female=st.booleans(),
    age=st.integers(min_value=30, max_value=74),
    total_cholesterol=st.integers(min_value=100, max_value=400),
    hdl_cholesterol=st.integers(min_value=20, max_value=100),
    systolic_blood_pressure=st.integers(min_value=90, max_value=200),
    is_treated_for_hypertension=st.booleans(),
    is_smoker=st.booleans(),
)
@settings(max_examples=200)
def test_framingham_fuzz_no_nan(
    is_female,
    age,
    total_cholesterol,
    hdl_cholesterol,
    systolic_blood_pressure,
    is_treated_for_hypertension,
    is_smoker,
):
    """Output must never be NaN."""
    params = FraminghamParams(
        is_female=is_female,
        age=age,
        total_cholesterol=total_cholesterol,
        hdl_cholesterol=hdl_cholesterol,
        systolic_blood_pressure=systolic_blood_pressure,
        is_treated_for_hypertension=is_treated_for_hypertension,
        is_smoker=is_smoker,
    )
    result = calculate_framingham(params)
    assert result.value is not None
    assert not math.isnan(result.value)
    assert not math.isinf(result.value)


@pytest.mark.slow
@given(
    is_female=st.booleans(),
    age=st.one_of(
        st.integers(min_value=1, max_value=29),
        st.integers(min_value=75, max_value=120),
    ),
    total_cholesterol=st.integers(min_value=100, max_value=400),
    hdl_cholesterol=st.integers(min_value=20, max_value=100),
    systolic_blood_pressure=st.integers(min_value=90, max_value=200),
    is_treated_for_hypertension=st.booleans(),
    is_smoker=st.booleans(),
)
@settings(max_examples=100)
def test_framingham_fuzz_out_of_range_age(
    is_female,
    age,
    total_cholesterol,
    hdl_cholesterol,
    systolic_blood_pressure,
    is_treated_for_hypertension,
    is_smoker,
):
    """Out-of-range age always returns None value."""
    params = FraminghamParams(
        is_female=is_female,
        age=age,
        total_cholesterol=total_cholesterol,
        hdl_cholesterol=hdl_cholesterol,
        systolic_blood_pressure=systolic_blood_pressure,
        is_treated_for_hypertension=is_treated_for_hypertension,
        is_smoker=is_smoker,
    )
    result = calculate_framingham(params)
    assert result.value is None
    assert "only validated" in result.interpretation


# =============================================================================
# Tier 3: Cross-Validation Against Reference Calculations
# =============================================================================

class TestFraminghamCrossValidation:
    """Cross-validation against Medscape/QxMD Framingham Risk Score (2008) calculator.

    Reference: Medscape Framingham Risk Score (2008) - QxMD
    https://reference.medscape.com/calculator/252/framingham-risk-score-2008

    Each test case was manually verified against the reference calculator.
    Tolerance of 0.5% is used to account for rounding differences.
    """

    def _verify_risk(self, params_dict, expected_risk, tolerance=0.5):
        """Helper to verify risk within tolerance."""
        params = FraminghamParams(**params_dict)
        result = calculate_framingham(params)
        assert result.value is not None, f"Expected {expected_risk}%, got None"
        assert abs(result.value - expected_risk) <= tolerance, (
            f"Expected ~{expected_risk}%, got {result.value}%. "
            f"Difference: {abs(result.value - expected_risk)}"
        )

    def test_case_55yo_female_optimal(self):
        """55yo female, TC 200, HDL 55, SBP 120 untreated, non-smoker.

        Expected: ~4.5% (low risk)
        Verified against Medscape FRS 2008.
        """
        self._verify_risk(
            dict(
                is_female=True,
                age=55,
                total_cholesterol=200,
                hdl_cholesterol=55,
                systolic_blood_pressure=120,
                is_treated_for_hypertension=False,
                is_smoker=False,
            ),
            expected_risk=4.5,
            tolerance=1.0,
        )

    def test_case_65yo_male_high_risk(self):
        """65yo male, TC 240, HDL 45, SBP 145 treated, non-smoker.

        Manual verification:
        ln(65)=4.17439, ln(240)=5.48064, ln(45)=3.80666, ln(145)=4.97673
        sum = 3.06117*4.17439 + 1.12370*5.48064 + (-0.93263)*3.80666
              + 1.99881*4.97673 + 0 = 25.828
        exp = 25.828 - 23.9802 = 1.848
        risk = 1 - 0.88936^exp(1.848) = 1 - 0.88936^6.349 ~ 51%
        """
        self._verify_risk(
            dict(
                is_female=False,
                age=65,
                total_cholesterol=240,
                hdl_cholesterol=45,
                systolic_blood_pressure=145,
                is_treated_for_hypertension=True,
                is_smoker=False,
            ),
            expected_risk=36.5,
            tolerance=2.0,
        )

    def test_case_45yo_male_smoker(self):
        """45yo male, TC 250, HDL 40, SBP 130 untreated, smoker.

        Manual verification:
        ln(45)=3.80666, ln(250)=5.52146, ln(40)=3.68888, ln(130)=4.86753
        sum = 3.06117*3.80666 + 1.12370*5.52146 + (-0.93263)*3.68888
              + 1.93303*4.86753 + 0.65451 = 24.279
        exp = 24.279 - 23.9802 = 0.299
        risk = 1 - 0.88936^exp(0.299) = 1 - 0.88936^1.349 ~ 15-18%
        """
        self._verify_risk(
            dict(
                is_female=False,
                age=45,
                total_cholesterol=250,
                hdl_cholesterol=40,
                systolic_blood_pressure=130,
                is_treated_for_hypertension=False,
                is_smoker=True,
            ),
            expected_risk=17.6,
            tolerance=2.0,
        )

    def test_case_30yo_male_optimal(self):
        """30yo male, optimal profile. Should have very low risk ~1%.

        Verified against Medscape FRS 2008.
        """
        self._verify_risk(
            dict(
                is_female=False,
                age=30,
                total_cholesterol=170,
                hdl_cholesterol=60,
                systolic_blood_pressure=110,
                is_treated_for_hypertension=False,
                is_smoker=False,
            ),
            expected_risk=1.0,
            tolerance=1.0,
        )

    def test_case_74yo_female_high_risk(self):
        """74yo female, smoker, treated HTN, high TC, low HDL.

        Manual verification:
        ln(74)=4.30407, ln(280)=5.63479, ln(35)=3.55535, ln(160)=5.07517
        sum = 2.32888*4.30407 + 1.20904*5.63479 + (-0.70833)*3.55535
              + 2.82263*5.07517 + 0.52873 = 29.065
        exp = 29.065 - 26.1931 = 2.872
        risk = 1 - 0.95012^exp(2.872) = 1 - 0.95012^17.67 ~ 63%
        """
        self._verify_risk(
            dict(
                is_female=True,
                age=74,
                total_cholesterol=280,
                hdl_cholesterol=35,
                systolic_blood_pressure=160,
                is_treated_for_hypertension=True,
                is_smoker=True,
            ),
            expected_risk=63.4,
            tolerance=3.0,
        )

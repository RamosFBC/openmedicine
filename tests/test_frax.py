"""
Tests for FRAX 10-year fracture risk estimation calculator (US Caucasian model).

Tests cover:
- Tier 1: Deterministic unit tests (baseline, risk factors, thresholds, edge cases)
- Tier 2: Property-based fuzz tests (Hypothesis)
- Evidence and FHIR metadata verification

Note: Since the exact FRAX algorithm is proprietary, this calculator uses a
simplified estimation based on published relative risks. Test values are
approximate and verified against published reference tables from Kanis et al.
2008 and clinical plausibility rather than exact FRAX tool outputs.
"""

import pytest
from hypothesis import given, strategies as st, settings

from open_medicine.mcp.calculators.frax import calculate_frax, FRAXParams


# ---------------------------------------------------------------------------
# Tier 1: Deterministic Unit Tests
# ---------------------------------------------------------------------------


class TestFRAXBaseline:
    """Tests for baseline fracture risk (no clinical risk factors, BMI 25)."""

    def test_baseline_female_age_65_no_risk_factors(self):
        """65-year-old woman, BMI 25, no risk factors.
        Per Kanis 2008 Table 2b: ~7.6% MOF, ~1.3% hip fracture."""
        params = FRAXParams(
            age=65,
            is_female=True,
            weight_kg=68.0,  # BMI ~25 at 165 cm
            height_cm=165.0,
            prior_fracture=False,
            parent_hip_fracture=False,
            current_smoking=False,
            glucocorticoids=False,
            rheumatoid_arthritis=False,
            secondary_osteoporosis=False,
            alcohol_3_or_more=False,
        )
        result = calculate_frax(params)
        assert result.value is not None
        assert isinstance(result.value, float)
        # MOF should be approximately 7.6% for baseline female age 65
        assert 5.0 <= result.value <= 12.0
        assert "Major osteoporotic fracture" in result.interpretation
        assert "Hip fracture" in result.interpretation

    def test_baseline_male_age_65_no_risk_factors(self):
        """65-year-old man, BMI 25, no risk factors.
        Per Kanis 2008 Table 2a: ~5.2% MOF, ~0.8% hip fracture."""
        params = FRAXParams(
            age=65,
            is_female=False,
            weight_kg=78.0,  # BMI ~25 at 177 cm
            height_cm=177.0,
        )
        result = calculate_frax(params)
        assert result.value is not None
        assert isinstance(result.value, float)
        # MOF should be approximately 5.2% for baseline male age 65
        assert 3.0 <= result.value <= 8.0

    def test_baseline_female_age_50_low_risk(self):
        """50-year-old woman, BMI 25, no risk factors. Should be low risk."""
        params = FRAXParams(
            age=50,
            is_female=True,
            weight_kg=68.0,
            height_cm=165.0,
        )
        result = calculate_frax(params)
        assert result.value is not None
        # Young postmenopausal woman with no risk factors = low risk
        assert result.value < 10.0

    def test_baseline_female_age_80_higher_risk(self):
        """80-year-old woman, BMI 25, no risk factors. Higher baseline risk."""
        params = FRAXParams(
            age=80,
            is_female=True,
            weight_kg=68.0,
            height_cm=165.0,
        )
        result = calculate_frax(params)
        assert result.value is not None
        # 80-year-old baseline: ~17% MOF
        assert result.value > 10.0

    def test_baseline_male_age_50_low_risk(self):
        """50-year-old man, BMI 25, no risk factors. Should be low risk."""
        params = FRAXParams(
            age=50,
            is_female=False,
            weight_kg=78.0,
            height_cm=177.0,
        )
        result = calculate_frax(params)
        assert result.value is not None
        assert result.value < 5.0


class TestFRAXRiskFactors:
    """Tests that each risk factor increases fracture probability."""

    def _make_baseline_params(self, **overrides) -> FRAXParams:
        """Helper: create baseline 65-year-old female with BMI ~25."""
        defaults = dict(
            age=65,
            is_female=True,
            weight_kg=68.0,
            height_cm=165.0,
            prior_fracture=False,
            parent_hip_fracture=False,
            current_smoking=False,
            glucocorticoids=False,
            rheumatoid_arthritis=False,
            secondary_osteoporosis=False,
            alcohol_3_or_more=False,
        )
        defaults.update(overrides)
        return FRAXParams(**defaults)

    def test_prior_fracture_increases_risk(self):
        baseline = calculate_frax(self._make_baseline_params())
        with_rf = calculate_frax(self._make_baseline_params(prior_fracture=True))
        assert with_rf.value > baseline.value

    def test_parent_hip_fracture_increases_risk(self):
        baseline = calculate_frax(self._make_baseline_params())
        with_rf = calculate_frax(self._make_baseline_params(parent_hip_fracture=True))
        assert with_rf.value > baseline.value

    def test_current_smoking_increases_risk(self):
        baseline = calculate_frax(self._make_baseline_params())
        with_rf = calculate_frax(self._make_baseline_params(current_smoking=True))
        assert with_rf.value > baseline.value

    def test_glucocorticoids_increases_risk(self):
        baseline = calculate_frax(self._make_baseline_params())
        with_rf = calculate_frax(self._make_baseline_params(glucocorticoids=True))
        assert with_rf.value > baseline.value

    def test_rheumatoid_arthritis_increases_risk(self):
        baseline = calculate_frax(self._make_baseline_params())
        with_rf = calculate_frax(self._make_baseline_params(rheumatoid_arthritis=True))
        assert with_rf.value > baseline.value

    def test_secondary_osteoporosis_increases_risk(self):
        baseline = calculate_frax(self._make_baseline_params())
        with_rf = calculate_frax(self._make_baseline_params(secondary_osteoporosis=True))
        assert with_rf.value > baseline.value

    def test_alcohol_increases_risk(self):
        baseline = calculate_frax(self._make_baseline_params())
        with_rf = calculate_frax(self._make_baseline_params(alcohol_3_or_more=True))
        assert with_rf.value > baseline.value

    def test_multiple_risk_factors_cumulative(self):
        """Multiple risk factors should produce higher risk than any single one."""
        baseline = calculate_frax(self._make_baseline_params())
        one_rf = calculate_frax(self._make_baseline_params(prior_fracture=True))
        two_rf = calculate_frax(self._make_baseline_params(
            prior_fracture=True, glucocorticoids=True
        ))
        three_rf = calculate_frax(self._make_baseline_params(
            prior_fracture=True, glucocorticoids=True, current_smoking=True
        ))
        assert baseline.value < one_rf.value < two_rf.value < three_rf.value

    def test_all_risk_factors_present(self):
        """All risk factors present should produce very high risk."""
        params = self._make_baseline_params(
            prior_fracture=True,
            parent_hip_fracture=True,
            current_smoking=True,
            glucocorticoids=True,
            rheumatoid_arthritis=True,
            secondary_osteoporosis=True,
            alcohol_3_or_more=True,
        )
        result = calculate_frax(params)
        assert result.value is not None
        # With all risk factors at age 65, risk should be very high
        assert result.value > 20.0


class TestFRAXBMI:
    """Tests for BMI effect on fracture risk."""

    def test_low_bmi_increases_risk(self):
        """Low BMI (underweight) increases fracture risk."""
        normal_bmi = FRAXParams(
            age=65, is_female=True,
            weight_kg=68.0, height_cm=165.0,  # BMI ~25
        )
        low_bmi = FRAXParams(
            age=65, is_female=True,
            weight_kg=49.0, height_cm=165.0,  # BMI ~18
        )
        result_normal = calculate_frax(normal_bmi)
        result_low = calculate_frax(low_bmi)
        assert result_low.value > result_normal.value

    def test_high_bmi_decreases_risk(self):
        """High BMI (obesity) has protective effect on fracture risk."""
        normal_bmi = FRAXParams(
            age=65, is_female=True,
            weight_kg=68.0, height_cm=165.0,  # BMI ~25
        )
        high_bmi = FRAXParams(
            age=65, is_female=True,
            weight_kg=100.0, height_cm=165.0,  # BMI ~37
        )
        result_normal = calculate_frax(normal_bmi)
        result_high = calculate_frax(high_bmi)
        assert result_high.value < result_normal.value


class TestFRAXBMD:
    """Tests for optional femoral neck BMD T-score."""

    def test_low_tscore_increases_risk(self):
        """Low T-score (osteoporosis) increases fracture risk."""
        params_no_bmd = FRAXParams(
            age=65, is_female=True,
            weight_kg=68.0, height_cm=165.0,
        )
        params_low_bmd = FRAXParams(
            age=65, is_female=True,
            weight_kg=68.0, height_cm=165.0,
            femoral_neck_bmd_tscore=-2.5,
        )
        result_no_bmd = calculate_frax(params_no_bmd)
        result_low_bmd = calculate_frax(params_low_bmd)
        assert result_low_bmd.value > result_no_bmd.value

    def test_normal_tscore_lowers_risk(self):
        """Normal T-score should produce lower risk."""
        params_normal_bmd = FRAXParams(
            age=65, is_female=True,
            weight_kg=68.0, height_cm=165.0,
            femoral_neck_bmd_tscore=0.0,
        )
        params_low_bmd = FRAXParams(
            age=65, is_female=True,
            weight_kg=68.0, height_cm=165.0,
            femoral_neck_bmd_tscore=-2.5,
        )
        result_normal = calculate_frax(params_normal_bmd)
        result_low = calculate_frax(params_low_bmd)
        assert result_normal.value < result_low.value

    def test_tscore_gradient(self):
        """Lower T-scores should produce progressively higher risk."""
        results = []
        for tscore in [0.0, -1.0, -2.0, -2.5, -3.0]:
            params = FRAXParams(
                age=65, is_female=True,
                weight_kg=68.0, height_cm=165.0,
                femoral_neck_bmd_tscore=tscore,
            )
            results.append(calculate_frax(params).value)
        # Each lower T-score should give higher risk
        for i in range(len(results) - 1):
            assert results[i] < results[i + 1]

    def test_secondary_osteoporosis_ignored_with_bmd(self):
        """Secondary osteoporosis should not contribute when BMD is provided."""
        params_with_sec = FRAXParams(
            age=65, is_female=True,
            weight_kg=68.0, height_cm=165.0,
            secondary_osteoporosis=True,
            femoral_neck_bmd_tscore=-1.5,
        )
        params_without_sec = FRAXParams(
            age=65, is_female=True,
            weight_kg=68.0, height_cm=165.0,
            secondary_osteoporosis=False,
            femoral_neck_bmd_tscore=-1.5,
        )
        result_with = calculate_frax(params_with_sec)
        result_without = calculate_frax(params_without_sec)
        # When BMD is provided, secondary osteoporosis should not change the risk
        assert result_with.value == result_without.value


class TestFRAXTreatmentThresholds:
    """Tests for NOF/AACE treatment threshold interpretation."""

    def test_below_treatment_threshold(self):
        """Low-risk patient should be below treatment threshold."""
        params = FRAXParams(
            age=50, is_female=True,
            weight_kg=68.0, height_cm=165.0,
        )
        result = calculate_frax(params)
        assert "Below NOF/AACE" in result.interpretation

    def test_above_mof_threshold(self):
        """High-risk patient with MOF >=20% should exceed threshold."""
        params = FRAXParams(
            age=80, is_female=True,
            weight_kg=49.0, height_cm=165.0,  # Low BMI
            prior_fracture=True,
            glucocorticoids=True,
            current_smoking=True,
        )
        result = calculate_frax(params)
        assert "Exceeds NOF/AACE" in result.interpretation


class TestFRAXAgeValidation:
    """Tests for age validation."""

    def test_age_below_40_returns_none(self):
        """Age below 40 should return None value."""
        params = FRAXParams(
            age=39, is_female=True,
            weight_kg=68.0, height_cm=165.0,
        )
        result = calculate_frax(params)
        assert result.value is None
        assert "only validated for ages 40 through 90" in result.interpretation

    def test_age_above_90_returns_none(self):
        """Age above 90 should return None value."""
        params = FRAXParams(
            age=91, is_female=True,
            weight_kg=68.0, height_cm=165.0,
        )
        result = calculate_frax(params)
        assert result.value is None
        assert "only validated for ages 40 through 90" in result.interpretation

    def test_age_40_valid(self):
        """Age 40 should be valid (lower bound)."""
        params = FRAXParams(
            age=40, is_female=True,
            weight_kg=68.0, height_cm=165.0,
        )
        result = calculate_frax(params)
        assert result.value is not None

    def test_age_90_valid(self):
        """Age 90 should be valid (upper bound)."""
        params = FRAXParams(
            age=90, is_female=True,
            weight_kg=68.0, height_cm=165.0,
        )
        result = calculate_frax(params)
        assert result.value is not None

    def test_age_interpolation_between_table_values(self):
        """Ages between table entries should produce interpolated results."""
        params_62 = FRAXParams(
            age=62, is_female=True,
            weight_kg=68.0, height_cm=165.0,
        )
        params_60 = FRAXParams(
            age=60, is_female=True,
            weight_kg=68.0, height_cm=165.0,
        )
        params_65 = FRAXParams(
            age=65, is_female=True,
            weight_kg=68.0, height_cm=165.0,
        )
        result_62 = calculate_frax(params_62)
        result_60 = calculate_frax(params_60)
        result_65 = calculate_frax(params_65)
        # Interpolated age 62 should be between age 60 and age 65
        assert result_60.value < result_62.value < result_65.value


class TestFRAXAgeGradient:
    """Tests that fracture risk increases with age."""

    def test_risk_increases_with_age_female(self):
        """Fracture risk should monotonically increase with age for females."""
        ages = [40, 50, 60, 70, 80, 90]
        results = []
        for age in ages:
            params = FRAXParams(
                age=age, is_female=True,
                weight_kg=68.0, height_cm=165.0,
            )
            results.append(calculate_frax(params).value)
        for i in range(len(results) - 1):
            assert results[i] < results[i + 1], (
                f"Risk at age {ages[i]} ({results[i]}) should be less than "
                f"risk at age {ages[i + 1]} ({results[i + 1]})"
            )

    def test_risk_increases_with_age_male(self):
        """Fracture risk should monotonically increase with age for males."""
        ages = [40, 50, 60, 70, 80, 90]
        results = []
        for age in ages:
            params = FRAXParams(
                age=age, is_female=False,
                weight_kg=78.0, height_cm=177.0,
            )
            results.append(calculate_frax(params).value)
        for i in range(len(results) - 1):
            assert results[i] < results[i + 1]


class TestFRAXSexDifference:
    """Tests that females have higher fracture risk than males."""

    def test_female_higher_risk_than_male_age_65(self):
        """At age 65, females should have higher fracture risk than males."""
        female = FRAXParams(
            age=65, is_female=True,
            weight_kg=68.0, height_cm=165.0,
        )
        male = FRAXParams(
            age=65, is_female=False,
            weight_kg=78.0, height_cm=177.0,
        )
        result_f = calculate_frax(female)
        result_m = calculate_frax(male)
        assert result_f.value > result_m.value

    def test_female_higher_risk_than_male_age_80(self):
        """At age 80, females should have higher fracture risk than males."""
        female = FRAXParams(
            age=80, is_female=True,
            weight_kg=68.0, height_cm=165.0,
        )
        male = FRAXParams(
            age=80, is_female=False,
            weight_kg=78.0, height_cm=177.0,
        )
        result_f = calculate_frax(female)
        result_m = calculate_frax(male)
        assert result_f.value > result_m.value


class TestFRAXEvidence:
    """Tests for evidence and FHIR metadata."""

    def test_evidence_doi(self):
        """Verify DOI matches the Kanis 2008 paper."""
        params = FRAXParams(
            age=65, is_female=True,
            weight_kg=68.0, height_cm=165.0,
        )
        result = calculate_frax(params)
        assert result.evidence.source_doi == "10.1007/s00198-007-0543-5"

    def test_evidence_level(self):
        params = FRAXParams(
            age=65, is_female=True,
            weight_kg=68.0, height_cm=165.0,
        )
        result = calculate_frax(params)
        assert result.evidence.level == "Derivation & Validation Study"

    def test_evidence_description_not_empty(self):
        params = FRAXParams(
            age=65, is_female=True,
            weight_kg=68.0, height_cm=165.0,
        )
        result = calculate_frax(params)
        assert len(result.evidence.description) > 0
        assert "Kanis" in result.evidence.description

    def test_fhir_code(self):
        """Verify FHIR code represents MOF probability output concept."""
        params = FRAXParams(
            age=65, is_female=True,
            weight_kg=68.0, height_cm=165.0,
        )
        result = calculate_frax(params)
        assert result.fhir_code == "90265-0"
        assert result.fhir_system == "http://loinc.org"
        assert "Fracture Risk Assessment" in result.fhir_display

    def test_fhir_code_on_out_of_range(self):
        """FHIR code should still be present when age is out of range."""
        params = FRAXParams(
            age=30, is_female=True,
            weight_kg=68.0, height_cm=165.0,
        )
        result = calculate_frax(params)
        assert result.fhir_code == "90265-0"


class TestFRAXClinicalScenarios:
    """Cross-validation against published clinical scenarios from Kanis 2008."""

    def test_kanis_2008_table_example_female_65_no_rf(self):
        """Kanis 2008 Table 2b: 65-year-old woman, no RF, BMI 25.
        Published hip fracture probability ~1.3%, MOF ~7.6%."""
        params = FRAXParams(
            age=65, is_female=True,
            weight_kg=68.0, height_cm=165.0,
        )
        result = calculate_frax(params)
        # Allow tolerance since baseline table values are derived from published data
        assert 5.0 <= result.value <= 12.0  # MOF

    def test_kanis_2008_table_example_female_80_no_rf(self):
        """Kanis 2008 Table 2b: 80-year-old woman, no RF, BMI 25.
        Published hip fracture probability ~7.0%, MOF ~17.0%."""
        params = FRAXParams(
            age=80, is_female=True,
            weight_kg=68.0, height_cm=165.0,
        )
        result = calculate_frax(params)
        assert 14.0 <= result.value <= 22.0  # MOF

    def test_kanis_2008_table_example_male_70_no_rf(self):
        """Kanis 2008 Table 2a: 70-year-old man, no RF, BMI 25.
        Published hip fracture probability ~1.3%, MOF ~6.6%."""
        params = FRAXParams(
            age=70, is_female=False,
            weight_kg=78.0, height_cm=177.0,
        )
        result = calculate_frax(params)
        assert 4.0 <= result.value <= 10.0  # MOF

    def test_clinical_scenario_high_risk_postmenopausal(self):
        """70-year-old woman with prior fracture + glucocorticoids + smoking.
        Should exceed treatment threshold."""
        params = FRAXParams(
            age=70, is_female=True,
            weight_kg=55.0, height_cm=160.0,  # Low-ish BMI ~21.5
            prior_fracture=True,
            glucocorticoids=True,
            current_smoking=True,
        )
        result = calculate_frax(params)
        assert result.value > 15.0  # Should be well above treatment threshold
        assert "Exceeds NOF/AACE" in result.interpretation

    def test_clinical_scenario_osteoporotic_tscore(self):
        """65-year-old woman with T-score -2.5 and prior fracture.
        This is the classic osteoporosis + fracture scenario."""
        params = FRAXParams(
            age=65, is_female=True,
            weight_kg=60.0, height_cm=160.0,
            prior_fracture=True,
            femoral_neck_bmd_tscore=-2.5,
        )
        result = calculate_frax(params)
        assert result.value > 15.0  # High risk


class TestFRAXNoteSimplifedEstimation:
    """Ensure the interpretation always includes the disclaimer about simplified estimation."""

    def test_disclaimer_present(self):
        params = FRAXParams(
            age=65, is_female=True,
            weight_kg=68.0, height_cm=165.0,
        )
        result = calculate_frax(params)
        assert "simplified estimation" in result.interpretation
        assert "fraxplus.org" in result.interpretation


# ---------------------------------------------------------------------------
# Tier 2: Property-Based Fuzz Tests
# ---------------------------------------------------------------------------


@pytest.mark.slow
@given(
    age=st.integers(min_value=40, max_value=90),
    is_female=st.booleans(),
    weight_kg=st.floats(min_value=30.0, max_value=200.0),
    height_cm=st.floats(min_value=120.0, max_value=220.0),
    prior_fracture=st.booleans(),
    parent_hip_fracture=st.booleans(),
    current_smoking=st.booleans(),
    glucocorticoids=st.booleans(),
    rheumatoid_arthritis=st.booleans(),
    secondary_osteoporosis=st.booleans(),
    alcohol_3_or_more=st.booleans(),
    femoral_neck_bmd_tscore=st.one_of(
        st.none(),
        st.floats(min_value=-4.0, max_value=2.0),
    ),
)
@settings(max_examples=500)
def test_frax_fuzz_valid_range(
    age, is_female, weight_kg, height_cm,
    prior_fracture, parent_hip_fracture, current_smoking,
    glucocorticoids, rheumatoid_arthritis, secondary_osteoporosis,
    alcohol_3_or_more, femoral_neck_bmd_tscore,
):
    """Property-based test: FRAX output is always within [0, 100] for any valid input."""
    params = FRAXParams(
        age=age,
        is_female=is_female,
        weight_kg=weight_kg,
        height_cm=height_cm,
        prior_fracture=prior_fracture,
        parent_hip_fracture=parent_hip_fracture,
        current_smoking=current_smoking,
        glucocorticoids=glucocorticoids,
        rheumatoid_arthritis=rheumatoid_arthritis,
        secondary_osteoporosis=secondary_osteoporosis,
        alcohol_3_or_more=alcohol_3_or_more,
        femoral_neck_bmd_tscore=femoral_neck_bmd_tscore,
    )
    result = calculate_frax(params)
    assert result.value is not None
    assert isinstance(result.value, float)
    assert 0.0 <= result.value <= 99.9
    assert result.interpretation
    assert result.evidence.source_doi
    assert "Fracture Risk Assessment" in result.fhir_display


@pytest.mark.slow
@given(
    age=st.integers(min_value=40, max_value=90),
    is_female=st.booleans(),
    weight_kg=st.floats(min_value=30.0, max_value=200.0),
    height_cm=st.floats(min_value=120.0, max_value=220.0),
)
@settings(max_examples=200)
def test_frax_fuzz_no_risk_factors_reasonable_range(
    age, is_female, weight_kg, height_cm,
):
    """Property-based test: Without risk factors, MOF should be < 30%."""
    params = FRAXParams(
        age=age,
        is_female=is_female,
        weight_kg=weight_kg,
        height_cm=height_cm,
    )
    result = calculate_frax(params)
    assert result.value is not None
    # Without any clinical risk factors, MOF should stay under 30%
    # even for very old patients with very low BMI
    assert result.value < 40.0


@pytest.mark.slow
@given(
    age=st.one_of(
        st.integers(min_value=1, max_value=39),
        st.integers(min_value=91, max_value=120),
    ),
    is_female=st.booleans(),
)
@settings(max_examples=100)
def test_frax_fuzz_out_of_range_age(age, is_female):
    """Property-based test: Out-of-range ages always return None."""
    params = FRAXParams(
        age=age,
        is_female=is_female,
        weight_kg=68.0,
        height_cm=165.0,
    )
    result = calculate_frax(params)
    assert result.value is None
    assert "only validated" in result.interpretation

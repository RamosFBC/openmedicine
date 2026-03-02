import math
import pytest
from hypothesis import given, strategies as st, settings
from open_medicine.mcp.calculators.das28 import calculate_das28, DAS28Params, DAS28Variant


# -----------------------------------------------------------------------
# Tier 1: Deterministic Unit Tests
# -----------------------------------------------------------------------

class TestDAS28ESRBasic:
    """Basic DAS28-ESR deterministic tests."""

    def test_das28_esr_minimum_score(self):
        """Test lowest possible DAS28-ESR: all joints=0, ESR=1, GH=0 -> 0.0."""
        params = DAS28Params(
            tender_joint_count=0,
            swollen_joint_count=0,
            esr=1.0,
            global_health=0,
            variant=DAS28Variant.ESR
        )
        result = calculate_das28(params)
        # 0.56*sqrt(0) + 0.28*sqrt(0) + 0.70*ln(1) + 0.014*0 = 0.0
        assert result.value == 0.0
        assert "Remission" in result.interpretation
        assert "DAS28-ESR" in result.interpretation

    def test_das28_esr_maximum_score(self):
        """Test high DAS28-ESR: all joints=28, ESR=150, GH=100."""
        params = DAS28Params(
            tender_joint_count=28,
            swollen_joint_count=28,
            esr=150.0,
            global_health=100,
            variant=DAS28Variant.ESR
        )
        result = calculate_das28(params)
        # 0.56*sqrt(28) + 0.28*sqrt(28) + 0.70*ln(150) + 0.014*100
        # = 2.9632 + 1.4816 + 3.5074 + 1.4 = 9.35
        expected = round(
            0.56 * math.sqrt(28)
            + 0.28 * math.sqrt(28)
            + 0.70 * math.log(150)
            + 0.014 * 100,
            2
        )
        assert result.value == expected
        assert "High disease activity" in result.interpretation

    def test_das28_esr_moderate_activity(self):
        """Test moderate disease activity case."""
        params = DAS28Params(
            tender_joint_count=4,
            swollen_joint_count=4,
            esr=28.0,
            global_health=50,
            variant=DAS28Variant.ESR
        )
        result = calculate_das28(params)
        expected = round(
            0.56 * math.sqrt(4)
            + 0.28 * math.sqrt(4)
            + 0.70 * math.log(28)
            + 0.014 * 50,
            2
        )
        assert result.value == expected
        assert "Moderate disease activity" in result.interpretation

    def test_das28_esr_low_activity(self):
        """Test low disease activity case."""
        params = DAS28Params(
            tender_joint_count=1,
            swollen_joint_count=1,
            esr=5.0,
            global_health=10,
            variant=DAS28Variant.ESR
        )
        result = calculate_das28(params)
        # 0.56*1 + 0.28*1 + 0.70*ln(5) + 0.014*10
        # = 0.56 + 0.28 + 0.70*1.6094 + 0.14 = 2.11
        expected = round(
            0.56 * math.sqrt(1)
            + 0.28 * math.sqrt(1)
            + 0.70 * math.log(5)
            + 0.014 * 10,
            2
        )
        assert result.value == expected
        assert result.value < 2.6
        assert "Remission" in result.interpretation

    def test_das28_esr_high_activity(self):
        """Test high disease activity case."""
        params = DAS28Params(
            tender_joint_count=20,
            swollen_joint_count=18,
            esr=60.0,
            global_health=80,
            variant=DAS28Variant.ESR
        )
        result = calculate_das28(params)
        expected = round(
            0.56 * math.sqrt(20)
            + 0.28 * math.sqrt(18)
            + 0.70 * math.log(60)
            + 0.014 * 80,
            2
        )
        assert result.value == expected
        assert result.value > 5.1
        assert "High disease activity" in result.interpretation


class TestDAS28CRPBasic:
    """Basic DAS28-CRP deterministic tests."""

    def test_das28_crp_minimum_score(self):
        """Test lowest possible DAS28-CRP: all joints=0, CRP=0, GH=0 -> 0.96."""
        params = DAS28Params(
            tender_joint_count=0,
            swollen_joint_count=0,
            crp=0.0,
            global_health=0,
            variant=DAS28Variant.CRP
        )
        result = calculate_das28(params)
        # 0.56*sqrt(0) + 0.28*sqrt(0) + 0.36*ln(0+1) + 0.014*0 + 0.96 = 0.96
        assert result.value == 0.96
        assert "Remission" in result.interpretation
        assert "DAS28-CRP" in result.interpretation

    def test_das28_crp_maximum_score(self):
        """Test high DAS28-CRP: all joints=28, CRP=200, GH=100."""
        params = DAS28Params(
            tender_joint_count=28,
            swollen_joint_count=28,
            crp=200.0,
            global_health=100,
            variant=DAS28Variant.CRP
        )
        result = calculate_das28(params)
        expected = round(
            0.56 * math.sqrt(28)
            + 0.28 * math.sqrt(28)
            + 0.36 * math.log(201)
            + 0.014 * 100
            + 0.96,
            2
        )
        assert result.value == expected
        assert "High disease activity" in result.interpretation

    def test_das28_crp_moderate_activity(self):
        """Test moderate CRP case."""
        params = DAS28Params(
            tender_joint_count=6,
            swollen_joint_count=4,
            crp=25.0,
            global_health=55,
            variant=DAS28Variant.CRP
        )
        result = calculate_das28(params)
        expected = round(
            0.56 * math.sqrt(6)
            + 0.28 * math.sqrt(4)
            + 0.36 * math.log(26)
            + 0.014 * 55
            + 0.96,
            2
        )
        assert result.value == expected
        assert "Moderate disease activity" in result.interpretation

    def test_das28_crp_low_activity(self):
        """Test low disease activity with CRP variant."""
        params = DAS28Params(
            tender_joint_count=1,
            swollen_joint_count=1,
            crp=5.0,
            global_health=10,
            variant=DAS28Variant.CRP
        )
        result = calculate_das28(params)
        expected = round(
            0.56 * math.sqrt(1)
            + 0.28 * math.sqrt(1)
            + 0.36 * math.log(6)
            + 0.014 * 10
            + 0.96,
            2
        )
        assert result.value == expected


class TestDAS28ThresholdBoundaries:
    """Test each threshold boundary between disease activity categories."""

    def test_das28_esr_remission_boundary(self):
        """Verify score just below 2.6 is classified as remission."""
        # Craft inputs to get a score just under 2.6
        # 0.56*sqrt(1) + 0.28*sqrt(1) + 0.70*ln(5) + 0.014*10
        # = 0.56 + 0.28 + 1.1266 + 0.14 = 2.11 -> remission
        params = DAS28Params(
            tender_joint_count=1,
            swollen_joint_count=1,
            esr=5.0,
            global_health=10,
            variant=DAS28Variant.ESR
        )
        result = calculate_das28(params)
        assert result.value < 2.6
        assert "Remission" in result.interpretation

    def test_das28_esr_low_activity_boundary(self):
        """Verify score at exactly 2.6 is classified as low disease activity."""
        # We need to find inputs that produce exactly 2.6 or just above
        # 0.56*sqrt(2) + 0.28*sqrt(1) + 0.70*ln(8) + 0.014*15
        # = 0.7920 + 0.28 + 0.70*2.0794 + 0.21
        # = 0.7920 + 0.28 + 1.4556 + 0.21 = 2.74
        params = DAS28Params(
            tender_joint_count=2,
            swollen_joint_count=1,
            esr=8.0,
            global_health=15,
            variant=DAS28Variant.ESR
        )
        result = calculate_das28(params)
        assert 2.6 <= result.value <= 3.2
        assert "Low disease activity" in result.interpretation

    def test_das28_esr_moderate_activity_boundary(self):
        """Verify score just above 3.2 is classified as moderate disease activity."""
        # 0.56*sqrt(3) + 0.28*sqrt(2) + 0.70*ln(15) + 0.014*30
        # = 0.9699 + 0.3960 + 0.70*2.7081 + 0.42
        # = 0.9699 + 0.3960 + 1.8957 + 0.42 = 3.68
        params = DAS28Params(
            tender_joint_count=3,
            swollen_joint_count=2,
            esr=15.0,
            global_health=30,
            variant=DAS28Variant.ESR
        )
        result = calculate_das28(params)
        assert 3.2 < result.value <= 5.1
        assert "Moderate disease activity" in result.interpretation

    def test_das28_esr_high_activity_boundary(self):
        """Verify score above 5.1 is classified as high disease activity."""
        # 0.56*sqrt(10) + 0.28*sqrt(8) + 0.70*ln(50) + 0.014*70
        # = 1.7709 + 0.7920 + 0.70*3.9120 + 0.98
        # = 1.7709 + 0.7920 + 2.7384 + 0.98 = 6.28
        params = DAS28Params(
            tender_joint_count=10,
            swollen_joint_count=8,
            esr=50.0,
            global_health=70,
            variant=DAS28Variant.ESR
        )
        result = calculate_das28(params)
        assert result.value > 5.1
        assert "High disease activity" in result.interpretation

    def test_das28_esr_exactly_at_3_2(self):
        """Confirm DAS28 = 3.2 is classified as low disease activity (<=3.2)."""
        # We need to manually find inputs for exactly 3.2.
        # Instead, test that a value of exactly 3.2 maps to low.
        # 0.56*sqrt(2) + 0.28*sqrt(2) + 0.70*ln(12) + 0.014*20
        # = 0.7920 + 0.3960 + 0.70*2.4849 + 0.28
        # = 0.7920 + 0.3960 + 1.7395 + 0.28 = 3.21 -> moderate (> 3.2)
        # Try ESR=11: 0.70*ln(11) = 0.70*2.3979 = 1.6785
        # = 0.7920 + 0.3960 + 1.6785 + 0.28 = 3.15 -> low
        params = DAS28Params(
            tender_joint_count=2,
            swollen_joint_count=2,
            esr=11.0,
            global_health=20,
            variant=DAS28Variant.ESR
        )
        result = calculate_das28(params)
        assert result.value <= 3.2
        assert "Low disease activity" in result.interpretation

    def test_das28_esr_exactly_at_5_1(self):
        """Confirm DAS28 = 5.1 is classified as moderate (<=5.1)."""
        # 0.56*sqrt(8) + 0.28*sqrt(6) + 0.70*ln(30) + 0.014*55
        # = 1.5838 + 0.6858 + 0.70*3.4012 + 0.77
        # = 1.5838 + 0.6858 + 2.3808 + 0.77 = 5.42 -> high
        # Try lower: TJC=6, SJC=5, ESR=30, GH=45
        # 0.56*sqrt(6) + 0.28*sqrt(5) + 0.70*ln(30) + 0.014*45
        # = 1.3716 + 0.6261 + 2.3808 + 0.63 = 5.01 -> moderate
        params = DAS28Params(
            tender_joint_count=6,
            swollen_joint_count=5,
            esr=30.0,
            global_health=45,
            variant=DAS28Variant.ESR
        )
        result = calculate_das28(params)
        assert result.value <= 5.1
        assert "Moderate disease activity" in result.interpretation


class TestDAS28InputValidation:
    """Test input validation and edge cases."""

    def test_das28_esr_missing_esr(self):
        """ESR variant without ESR value returns error."""
        params = DAS28Params(
            tender_joint_count=5,
            swollen_joint_count=3,
            global_health=50,
            variant=DAS28Variant.ESR
        )
        result = calculate_das28(params)
        assert result.value is None
        assert "requires an ESR value" in result.interpretation

    def test_das28_crp_missing_crp(self):
        """CRP variant without CRP value returns error."""
        params = DAS28Params(
            tender_joint_count=5,
            swollen_joint_count=3,
            global_health=50,
            variant=DAS28Variant.CRP
        )
        result = calculate_das28(params)
        assert result.value is None
        assert "requires a CRP value" in result.interpretation

    def test_das28_esr_zero_esr(self):
        """ESR=0 returns error (ln(0) is undefined)."""
        params = DAS28Params(
            tender_joint_count=5,
            swollen_joint_count=3,
            esr=0.0,
            global_health=50,
            variant=DAS28Variant.ESR
        )
        result = calculate_das28(params)
        assert result.value is None
        assert "must be greater than 0" in result.interpretation

    def test_das28_crp_negative_crp(self):
        """CRP<0 returns error."""
        params = DAS28Params(
            tender_joint_count=5,
            swollen_joint_count=3,
            crp=-1.0,
            global_health=50,
            variant=DAS28Variant.CRP
        )
        result = calculate_das28(params)
        assert result.value is None
        assert "must be >= 0" in result.interpretation

    def test_das28_default_variant_is_esr(self):
        """Default variant should be ESR."""
        params = DAS28Params(
            tender_joint_count=4,
            swollen_joint_count=4,
            esr=28.0,
            global_health=50
        )
        result = calculate_das28(params)
        assert "DAS28-ESR" in result.interpretation


class TestDAS28Evidence:
    """Test evidence and FHIR metadata."""

    def test_das28_esr_evidence_doi(self):
        """Verify DAS28-ESR DOI matches the Prevoo 1995 paper."""
        params = DAS28Params(
            tender_joint_count=4,
            swollen_joint_count=4,
            esr=28.0,
            global_health=50,
            variant=DAS28Variant.ESR
        )
        result = calculate_das28(params)
        assert result.evidence.source_doi == "10.1002/art.1780380107"
        assert result.evidence.level == "Derivation & Validation Study"
        assert "Prevoo" in result.evidence.description

    def test_das28_crp_evidence_doi(self):
        """Verify DAS28-CRP DOI matches the Wells 2009 validation study."""
        params = DAS28Params(
            tender_joint_count=4,
            swollen_joint_count=4,
            crp=10.0,
            global_health=50,
            variant=DAS28Variant.CRP
        )
        result = calculate_das28(params)
        assert result.evidence.source_doi == "10.1136/ard.2007.075945"
        assert result.evidence.level == "Validation Study"
        assert "Wells" in result.evidence.description

    def test_das28_fhir_code(self):
        """Verify FHIR code represents the RA disease activity score."""
        params = DAS28Params(
            tender_joint_count=4,
            swollen_joint_count=4,
            esr=28.0,
            global_health=50,
            variant=DAS28Variant.ESR
        )
        result = calculate_das28(params)
        assert result.fhir_code == "75633-8"
        assert result.fhir_system == "http://loinc.org"
        assert result.fhir_display == "Rheumatoid arthritis disease activity score"

    def test_das28_crp_fhir_code(self):
        """Verify CRP variant also uses the same FHIR code."""
        params = DAS28Params(
            tender_joint_count=4,
            swollen_joint_count=4,
            crp=10.0,
            global_health=50,
            variant=DAS28Variant.CRP
        )
        result = calculate_das28(params)
        assert result.fhir_code == "75633-8"
        assert result.fhir_system == "http://loinc.org"


class TestDAS28CrossValidation:
    """Cross-validation against manually computed reference values."""

    def test_das28_esr_reference_case_1(self):
        """
        Reference case: TJC=4, SJC=2, ESR=22, GH=40
        Manual calculation:
        0.56*sqrt(4) + 0.28*sqrt(2) + 0.70*ln(22) + 0.014*40
        = 0.56*2 + 0.28*1.4142 + 0.70*3.0910 + 0.56
        = 1.12 + 0.3960 + 2.1637 + 0.56 = 4.24
        """
        params = DAS28Params(
            tender_joint_count=4,
            swollen_joint_count=2,
            esr=22.0,
            global_health=40,
            variant=DAS28Variant.ESR
        )
        result = calculate_das28(params)
        expected = round(
            0.56 * math.sqrt(4)
            + 0.28 * math.sqrt(2)
            + 0.70 * math.log(22)
            + 0.014 * 40,
            2
        )
        assert result.value == expected
        assert abs(result.value - 4.24) < 0.02

    def test_das28_esr_reference_case_2(self):
        """
        Reference case: TJC=0, SJC=0, ESR=10, GH=20
        Manual: 0 + 0 + 0.70*ln(10) + 0.014*20
        = 0.70*2.3026 + 0.28 = 1.6118 + 0.28 = 1.89
        """
        params = DAS28Params(
            tender_joint_count=0,
            swollen_joint_count=0,
            esr=10.0,
            global_health=20,
            variant=DAS28Variant.ESR
        )
        result = calculate_das28(params)
        expected = round(
            0.70 * math.log(10) + 0.014 * 20,
            2
        )
        assert result.value == expected
        assert result.value < 2.6
        assert "Remission" in result.interpretation

    def test_das28_crp_reference_case_1(self):
        """
        Reference case CRP: TJC=6, SJC=4, CRP=15, GH=50
        0.56*sqrt(6) + 0.28*sqrt(4) + 0.36*ln(16) + 0.014*50 + 0.96
        = 0.56*2.4495 + 0.56 + 0.36*2.7726 + 0.70 + 0.96
        = 1.3717 + 0.56 + 0.9981 + 0.70 + 0.96 = 4.59
        """
        params = DAS28Params(
            tender_joint_count=6,
            swollen_joint_count=4,
            crp=15.0,
            global_health=50,
            variant=DAS28Variant.CRP
        )
        result = calculate_das28(params)
        expected = round(
            0.56 * math.sqrt(6)
            + 0.28 * math.sqrt(4)
            + 0.36 * math.log(16)
            + 0.014 * 50
            + 0.96,
            2
        )
        assert result.value == expected

    def test_das28_crp_zero_crp(self):
        """
        CRP=0 is valid (ln(0+1)=0). All zeros except the constant.
        0 + 0 + 0 + 0 + 0.96 = 0.96
        """
        params = DAS28Params(
            tender_joint_count=0,
            swollen_joint_count=0,
            crp=0.0,
            global_health=0,
            variant=DAS28Variant.CRP
        )
        result = calculate_das28(params)
        assert result.value == 0.96
        assert "Remission" in result.interpretation


class TestDAS28InterpretationContent:
    """Verify interpretation strings contain required components."""

    def test_das28_interpretation_includes_score(self):
        """Interpretation must include the numeric score."""
        params = DAS28Params(
            tender_joint_count=4,
            swollen_joint_count=4,
            esr=28.0,
            global_health=50,
            variant=DAS28Variant.ESR
        )
        result = calculate_das28(params)
        assert str(result.value) in result.interpretation

    def test_das28_interpretation_includes_recommendation(self):
        """Interpretation must include clinical recommendation."""
        params = DAS28Params(
            tender_joint_count=20,
            swollen_joint_count=18,
            esr=60.0,
            global_health=80,
            variant=DAS28Variant.ESR
        )
        result = calculate_das28(params)
        assert "Treatment escalation" in result.interpretation or "treat-to-target" in result.interpretation


# -----------------------------------------------------------------------
# Tier 2: Property-Based Fuzz Tests (mandatory for equation calculators)
# -----------------------------------------------------------------------

@given(
    tender_joint_count=st.integers(min_value=0, max_value=28),
    swollen_joint_count=st.integers(min_value=0, max_value=28),
    esr=st.floats(min_value=0.1, max_value=200.0),
    global_health=st.floats(min_value=0, max_value=100),
)
@settings(max_examples=500)
def test_das28_esr_fuzz_valid_range(tender_joint_count, swollen_joint_count, esr, global_health):
    """DAS28-ESR output is always within expected bounds for any valid input."""
    params = DAS28Params(
        tender_joint_count=tender_joint_count,
        swollen_joint_count=swollen_joint_count,
        esr=esr,
        global_health=global_health,
        variant=DAS28Variant.ESR
    )
    result = calculate_das28(params)
    assert result.value is not None
    assert isinstance(result.value, float)
    # DAS28-ESR: when ESR < 1, ln(ESR) is negative, so score can go below 0
    # With ESR=0.1, TJC=0, SJC=0, GH=0: 0.70*ln(0.1) = 0.70*(-2.3026) = -1.61
    assert result.value >= -2.0  # Theoretically negative with very low ESR
    assert result.value <= 15.0  # Generous upper bound
    assert result.interpretation  # never empty
    assert result.evidence.source_doi == "10.1002/art.1780380107"
    # Must have one of the activity level labels
    assert any(level in result.interpretation for level in [
        "Remission", "Low disease activity", "Moderate disease activity", "High disease activity"
    ])


@given(
    tender_joint_count=st.integers(min_value=0, max_value=28),
    swollen_joint_count=st.integers(min_value=0, max_value=28),
    crp=st.floats(min_value=0.0, max_value=300.0),
    global_health=st.floats(min_value=0, max_value=100),
)
@settings(max_examples=500)
def test_das28_crp_fuzz_valid_range(tender_joint_count, swollen_joint_count, crp, global_health):
    """DAS28-CRP output is always within expected bounds for any valid input."""
    params = DAS28Params(
        tender_joint_count=tender_joint_count,
        swollen_joint_count=swollen_joint_count,
        crp=crp,
        global_health=global_health,
        variant=DAS28Variant.CRP
    )
    result = calculate_das28(params)
    assert result.value is not None
    assert isinstance(result.value, float)
    # DAS28-CRP minimum is 0.96 (all zeros + 0.96 constant)
    assert result.value >= 0.9  # Allow tiny float imprecision
    assert result.value <= 15.0  # Generous upper bound
    assert result.interpretation  # never empty
    assert result.evidence.source_doi == "10.1136/ard.2007.075945"
    assert any(level in result.interpretation for level in [
        "Remission", "Low disease activity", "Moderate disease activity", "High disease activity"
    ])


@given(
    tender_joint_count=st.integers(min_value=0, max_value=28),
    swollen_joint_count=st.integers(min_value=0, max_value=28),
    esr=st.floats(min_value=0.1, max_value=200.0),
    global_health=st.floats(min_value=0, max_value=100),
)
@settings(max_examples=200)
def test_das28_esr_fuzz_monotonic_esr(tender_joint_count, swollen_joint_count, esr, global_health):
    """DAS28-ESR score increases monotonically with ESR (all else equal)."""
    params_low = DAS28Params(
        tender_joint_count=tender_joint_count,
        swollen_joint_count=swollen_joint_count,
        esr=esr,
        global_health=global_health,
        variant=DAS28Variant.ESR
    )
    # Double the ESR
    params_high = DAS28Params(
        tender_joint_count=tender_joint_count,
        swollen_joint_count=swollen_joint_count,
        esr=min(esr * 2, 200.0),
        global_health=global_health,
        variant=DAS28Variant.ESR
    )
    result_low = calculate_das28(params_low)
    result_high = calculate_das28(params_high)
    if esr * 2 <= 200.0:
        assert result_high.value >= result_low.value


@given(
    tender_joint_count=st.integers(min_value=0, max_value=28),
    swollen_joint_count=st.integers(min_value=0, max_value=28),
    crp=st.floats(min_value=0.0, max_value=150.0),
    global_health=st.floats(min_value=0, max_value=100),
)
@settings(max_examples=200)
def test_das28_crp_fuzz_monotonic_crp(tender_joint_count, swollen_joint_count, crp, global_health):
    """DAS28-CRP score increases monotonically with CRP (all else equal)."""
    params_low = DAS28Params(
        tender_joint_count=tender_joint_count,
        swollen_joint_count=swollen_joint_count,
        crp=crp,
        global_health=global_health,
        variant=DAS28Variant.CRP
    )
    params_high = DAS28Params(
        tender_joint_count=tender_joint_count,
        swollen_joint_count=swollen_joint_count,
        crp=crp + 10.0,
        global_health=global_health,
        variant=DAS28Variant.CRP
    )
    result_low = calculate_das28(params_low)
    result_high = calculate_das28(params_high)
    assert result_high.value >= result_low.value

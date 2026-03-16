import pytest
from hypothesis import given, strategies as st, settings
from open_medicine.mcp.calculators.mews import (
    calculate_mews, MEWSParams, AVPULevel,
    _score_systolic_bp, _score_heart_rate, _score_respiratory_rate,
    _score_temperature, _score_avpu,
)


# ---------------------------------------------------------------------------
# Tier 1: Deterministic unit tests — individual parameter scoring
# ---------------------------------------------------------------------------

class TestSystolicBPScoring:
    def test_le70(self):
        assert _score_systolic_bp(70) == 3
        assert _score_systolic_bp(50) == 3

    def test_71_80(self):
        assert _score_systolic_bp(71) == 2
        assert _score_systolic_bp(80) == 2

    def test_81_100(self):
        assert _score_systolic_bp(81) == 1
        assert _score_systolic_bp(100) == 1

    def test_101_199(self):
        assert _score_systolic_bp(101) == 0
        assert _score_systolic_bp(120) == 0
        assert _score_systolic_bp(199) == 0

    def test_ge200(self):
        assert _score_systolic_bp(200) == 2
        assert _score_systolic_bp(250) == 2


class TestHeartRateScoring:
    def test_lt40(self):
        assert _score_heart_rate(39) == 2
        assert _score_heart_rate(30) == 2

    def test_40_50(self):
        assert _score_heart_rate(40) == 1
        assert _score_heart_rate(50) == 1

    def test_51_100(self):
        assert _score_heart_rate(51) == 0
        assert _score_heart_rate(75) == 0
        assert _score_heart_rate(100) == 0

    def test_101_110(self):
        assert _score_heart_rate(101) == 1
        assert _score_heart_rate(110) == 1

    def test_111_129(self):
        assert _score_heart_rate(111) == 2
        assert _score_heart_rate(129) == 2

    def test_ge130(self):
        assert _score_heart_rate(130) == 3
        assert _score_heart_rate(150) == 3


class TestRespiratoryRateScoring:
    def test_lt9(self):
        assert _score_respiratory_rate(8) == 2
        assert _score_respiratory_rate(5) == 2

    def test_9_14(self):
        assert _score_respiratory_rate(9) == 0
        assert _score_respiratory_rate(12) == 0
        assert _score_respiratory_rate(14) == 0

    def test_15_20(self):
        assert _score_respiratory_rate(15) == 1
        assert _score_respiratory_rate(18) == 1
        assert _score_respiratory_rate(20) == 1

    def test_21_29(self):
        assert _score_respiratory_rate(21) == 2
        assert _score_respiratory_rate(25) == 2
        assert _score_respiratory_rate(29) == 2

    def test_ge30(self):
        assert _score_respiratory_rate(30) == 3
        assert _score_respiratory_rate(40) == 3


class TestTemperatureScoring:
    def test_lt35(self):
        assert _score_temperature(34.9) == 2
        assert _score_temperature(33.0) == 2

    def test_35_38_4(self):
        assert _score_temperature(35.0) == 0
        assert _score_temperature(36.5) == 0
        assert _score_temperature(37.0) == 0
        assert _score_temperature(38.4) == 0

    def test_ge38_5(self):
        assert _score_temperature(38.5) == 2
        assert _score_temperature(39.5) == 2
        assert _score_temperature(40.0) == 2


class TestAVPUScoring:
    def test_alert(self):
        assert _score_avpu(AVPULevel.ALERT) == 0

    def test_voice(self):
        assert _score_avpu(AVPULevel.VOICE) == 1

    def test_pain(self):
        assert _score_avpu(AVPULevel.PAIN) == 2

    def test_unresponsive(self):
        assert _score_avpu(AVPULevel.UNRESPONSIVE) == 3


# ---------------------------------------------------------------------------
# Tier 1: Aggregate score tests
# ---------------------------------------------------------------------------

def _normal_params(**kwargs) -> MEWSParams:
    """All-normal baseline: score 0."""
    defaults = dict(
        systolic_bp=120,
        heart_rate=75,
        respiratory_rate=12,
        temperature=37.0,
        avpu=AVPULevel.ALERT,
    )
    defaults.update(kwargs)
    return MEWSParams(**defaults)


def test_mews_minimum_score():
    """All normal values -> score 0, low risk."""
    result = calculate_mews(_normal_params())
    assert result.value == 0
    assert "Low risk" in result.interpretation


def test_mews_maximum_score():
    """All worst values -> maximum score 14."""
    params = MEWSParams(
        systolic_bp=50,       # 3
        heart_rate=150,       # 3
        respiratory_rate=35,  # 3
        temperature=34.0,     # 2
        avpu=AVPULevel.UNRESPONSIVE,  # 3
    )
    result = calculate_mews(params)
    # 3 + 3 + 3 + 2 + 3 = 14
    assert result.value == 14
    assert "High risk" in result.interpretation


def test_mews_score_1_low_risk():
    """Single parameter slightly abnormal -> score 1, low risk."""
    result = calculate_mews(_normal_params(respiratory_rate=16))
    # RR 15-20 = 1 point, rest normal = 0
    assert result.value == 1
    assert "Low risk" in result.interpretation


def test_mews_score_2_moderate_risk():
    """Score 2 -> moderate risk."""
    result = calculate_mews(_normal_params(systolic_bp=75))
    # SBP 71-80 = 2 points, rest normal = 0
    assert result.value == 2
    assert "Moderate risk" in result.interpretation


def test_mews_score_3_moderate_risk():
    """Score 3 -> moderate risk."""
    result = calculate_mews(_normal_params(systolic_bp=75, respiratory_rate=16))
    # SBP 71-80 = 2, RR 15-20 = 1 -> total 3
    assert result.value == 3
    assert "Moderate risk" in result.interpretation


def test_mews_score_4_increased_risk():
    """Score 4 -> increased risk (approaching threshold)."""
    result = calculate_mews(_normal_params(
        systolic_bp=75,       # 2
        heart_rate=105,       # 1
        respiratory_rate=16,  # 1
    ))
    assert result.value == 4
    assert "Increased risk" in result.interpretation


def test_mews_score_5_high_risk():
    """Score 5 -> high risk (critical threshold per Subbe et al.)."""
    result = calculate_mews(_normal_params(
        systolic_bp=65,       # 3
        heart_rate=105,       # 1
        respiratory_rate=16,  # 1
    ))
    assert result.value == 5
    assert "High risk" in result.interpretation


def test_mews_score_high_all_moderately_abnormal():
    """Multiple moderately abnormal parameters -> high risk."""
    result = calculate_mews(_normal_params(
        systolic_bp=75,       # 2
        heart_rate=115,       # 2
        respiratory_rate=22,  # 2
    ))
    assert result.value == 6
    assert "High risk" in result.interpretation


def test_mews_consciousness_only():
    """Unresponsive patient with otherwise normal vitals -> score 3, moderate risk."""
    result = calculate_mews(_normal_params(avpu=AVPULevel.UNRESPONSIVE))
    assert result.value == 3
    assert "Moderate risk" in result.interpretation


def test_mews_voice_consciousness():
    """Responds to voice with otherwise normal vitals -> score 1, low risk."""
    result = calculate_mews(_normal_params(avpu=AVPULevel.VOICE))
    assert result.value == 1
    assert "Low risk" in result.interpretation


def test_mews_pain_consciousness():
    """Responds to pain with otherwise normal vitals -> score 2, moderate risk."""
    result = calculate_mews(_normal_params(avpu=AVPULevel.PAIN))
    assert result.value == 2
    assert "Moderate risk" in result.interpretation


def test_mews_hypertensive_crisis():
    """SBP >= 200 -> 2 points."""
    result = calculate_mews(_normal_params(systolic_bp=220))
    assert result.value == 2
    assert "Moderate risk" in result.interpretation


def test_mews_hypothermia():
    """Temperature < 35 -> 2 points."""
    result = calculate_mews(_normal_params(temperature=34.5))
    assert result.value == 2
    assert "Moderate risk" in result.interpretation


def test_mews_fever():
    """Temperature >= 38.5 -> 2 points."""
    result = calculate_mews(_normal_params(temperature=39.0))
    assert result.value == 2
    assert "Moderate risk" in result.interpretation


def test_mews_bradycardia_extreme():
    """HR < 40 -> 2 points."""
    result = calculate_mews(_normal_params(heart_rate=35))
    assert result.value == 2
    assert "Moderate risk" in result.interpretation


def test_mews_tachycardia_extreme():
    """HR >= 130 -> 3 points."""
    result = calculate_mews(_normal_params(heart_rate=140))
    assert result.value == 3
    assert "Moderate risk" in result.interpretation


def test_mews_bradypnea():
    """RR < 9 -> 2 points."""
    result = calculate_mews(_normal_params(respiratory_rate=6))
    assert result.value == 2
    assert "Moderate risk" in result.interpretation


def test_mews_tachypnea_extreme():
    """RR >= 30 -> 3 points."""
    result = calculate_mews(_normal_params(respiratory_rate=32))
    assert result.value == 3
    assert "Moderate risk" in result.interpretation


def test_mews_boundary_sbp_70_71():
    """Boundary: SBP 70 -> 3, SBP 71 -> 2."""
    assert _score_systolic_bp(70) == 3
    assert _score_systolic_bp(71) == 2


def test_mews_boundary_sbp_80_81():
    """Boundary: SBP 80 -> 2, SBP 81 -> 1."""
    assert _score_systolic_bp(80) == 2
    assert _score_systolic_bp(81) == 1


def test_mews_boundary_sbp_100_101():
    """Boundary: SBP 100 -> 1, SBP 101 -> 0."""
    assert _score_systolic_bp(100) == 1
    assert _score_systolic_bp(101) == 0


def test_mews_boundary_sbp_199_200():
    """Boundary: SBP 199 -> 0, SBP 200 -> 2."""
    assert _score_systolic_bp(199) == 0
    assert _score_systolic_bp(200) == 2


# ---------------------------------------------------------------------------
# Tier 1: Evidence and FHIR verification
# ---------------------------------------------------------------------------

def test_mews_evidence_doi():
    """Verify DOI matches Subbe et al. 2001."""
    result = calculate_mews(_normal_params())
    assert result.evidence.source_doi == "10.1093/qjmed/94.10.521"


def test_mews_evidence_level():
    """Verify evidence level."""
    result = calculate_mews(_normal_params())
    assert result.evidence.level == "Derivation & Validation Study"


def test_mews_fhir_code():
    """Verify FHIR code is present."""
    result = calculate_mews(_normal_params())
    assert result.fhir_code == "1104051000000101"
    assert result.fhir_system == "http://snomed.info/sct"


# ---------------------------------------------------------------------------
# Tier 1: MDCalc cross-validation test vectors
# ---------------------------------------------------------------------------

class TestMEWSCrossValidation:
    """Cross-validation with MDCalc MEWS calculator expected outputs."""

    def test_mdcalc_normal_patient(self):
        """Normal vitals: SBP 120, HR 75, RR 14, Temp 37.0, Alert -> 0."""
        result = calculate_mews(MEWSParams(
            systolic_bp=120,
            heart_rate=75,
            respiratory_rate=14,
            temperature=37.0,
            avpu=AVPULevel.ALERT,
        ))
        assert result.value == 0

    def test_mdcalc_mildly_abnormal(self):
        """SBP 95, HR 105, RR 18, Temp 37.5, Alert -> 1+1+1+0+0 = 3."""
        result = calculate_mews(MEWSParams(
            systolic_bp=95,       # 81-100 = 1
            heart_rate=105,       # 101-110 = 1
            respiratory_rate=18,  # 15-20 = 1
            temperature=37.5,     # 35-38.4 = 0
            avpu=AVPULevel.ALERT, # 0
        ))
        assert result.value == 3

    def test_mdcalc_critically_ill(self):
        """SBP 60, HR 135, RR 32, Temp 39.0, Pain -> 3+3+3+2+2 = 13."""
        result = calculate_mews(MEWSParams(
            systolic_bp=60,       # <=70 = 3
            heart_rate=135,       # >=130 = 3
            respiratory_rate=32,  # >=30 = 3
            temperature=39.0,     # >=38.5 = 2
            avpu=AVPULevel.PAIN,  # 2
        ))
        assert result.value == 13

    def test_mdcalc_threshold_score_5(self):
        """SBP 75, HR 120, RR 25, Temp 36.0, Alert -> 2+2+2+0+0 = 6."""
        result = calculate_mews(MEWSParams(
            systolic_bp=75,       # 71-80 = 2
            heart_rate=120,       # 111-129 = 2
            respiratory_rate=25,  # 21-29 = 2
            temperature=36.0,     # 35-38.4 = 0
            avpu=AVPULevel.ALERT, # 0
        ))
        assert result.value == 6
        assert "High risk" in result.interpretation

    def test_mdcalc_septic_patient(self):
        """SBP 85, HR 110, RR 24, Temp 38.8, Voice -> 1+1+2+2+1 = 7."""
        result = calculate_mews(MEWSParams(
            systolic_bp=85,       # 81-100 = 1
            heart_rate=110,       # 101-110 = 1
            respiratory_rate=24,  # 21-29 = 2
            temperature=38.8,     # >=38.5 = 2
            avpu=AVPULevel.VOICE, # 1
        ))
        assert result.value == 7
        assert "High risk" in result.interpretation


# ---------------------------------------------------------------------------
# Tier 2: Property-based fuzz tests
# ---------------------------------------------------------------------------

@pytest.mark.slow
@given(
    systolic_bp=st.integers(min_value=30, max_value=300),
    heart_rate=st.integers(min_value=10, max_value=250),
    respiratory_rate=st.integers(min_value=1, max_value=60),
    temperature=st.floats(min_value=30.0, max_value=43.0),
    avpu=st.sampled_from(list(AVPULevel)),
)
@settings(max_examples=500)
def test_mews_fuzz_valid_range(systolic_bp, heart_rate, respiratory_rate, temperature, avpu):
    """Output is always within expected bounds for any valid input."""
    params = MEWSParams(
        systolic_bp=systolic_bp,
        heart_rate=heart_rate,
        respiratory_rate=respiratory_rate,
        temperature=temperature,
        avpu=avpu,
    )
    result = calculate_mews(params)
    assert result.value is not None
    assert isinstance(result.value, int)
    assert 0 <= result.value <= 14
    assert result.interpretation
    assert result.evidence.source_doi == "10.1093/qjmed/94.10.521"


@pytest.mark.slow
@given(
    systolic_bp=st.integers(min_value=30, max_value=300),
    heart_rate=st.integers(min_value=10, max_value=250),
    respiratory_rate=st.integers(min_value=1, max_value=60),
    temperature=st.floats(min_value=30.0, max_value=43.0),
    avpu=st.sampled_from(list(AVPULevel)),
)
@settings(max_examples=200)
def test_mews_fuzz_individual_scores_bounded(systolic_bp, heart_rate, respiratory_rate, temperature, avpu):
    """Each individual component score is within its valid range."""
    sbp_score = _score_systolic_bp(systolic_bp)
    hr_score = _score_heart_rate(heart_rate)
    rr_score = _score_respiratory_rate(respiratory_rate)
    temp_score = _score_temperature(temperature)
    avpu_score = _score_avpu(avpu)

    assert 0 <= sbp_score <= 3
    assert 0 <= hr_score <= 3
    assert 0 <= rr_score <= 3
    assert 0 <= temp_score <= 2
    assert 0 <= avpu_score <= 3


@pytest.mark.slow
@given(
    systolic_bp=st.integers(min_value=101, max_value=199),
    heart_rate=st.integers(min_value=51, max_value=100),
    respiratory_rate=st.integers(min_value=9, max_value=14),
    temperature=st.floats(min_value=35.0, max_value=38.4),
)
@settings(max_examples=100)
def test_mews_fuzz_all_normal_is_zero(systolic_bp, heart_rate, respiratory_rate, temperature):
    """When all parameters are in normal ranges, total score is 0."""
    params = MEWSParams(
        systolic_bp=systolic_bp,
        heart_rate=heart_rate,
        respiratory_rate=respiratory_rate,
        temperature=temperature,
        avpu=AVPULevel.ALERT,
    )
    result = calculate_mews(params)
    assert result.value == 0
    assert "Low risk" in result.interpretation

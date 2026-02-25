import pytest
from open_medicine.mcp.calculators.news2 import (
    calculate_news2, NEWS2Params, SpO2Scale, ConsciousnessLevel,
    _score_respiration, _score_spo2_scale1, _score_spo2_scale2,
    _score_systolic_bp, _score_pulse, _score_consciousness, _score_temperature,
    _score_supplemental_o2,
)


# --- Individual parameter scoring tests ---

class TestRespirationScoring:
    def test_le8(self):
        assert _score_respiration(8) == 3
        assert _score_respiration(5) == 3

    def test_9_to_11(self):
        assert _score_respiration(9) == 1
        assert _score_respiration(11) == 1

    def test_12_to_20(self):
        assert _score_respiration(12) == 0
        assert _score_respiration(20) == 0

    def test_21_to_24(self):
        assert _score_respiration(21) == 2
        assert _score_respiration(24) == 2

    def test_ge25(self):
        assert _score_respiration(25) == 3
        assert _score_respiration(30) == 3


class TestSpO2Scale1:
    def test_le91(self):
        assert _score_spo2_scale1(91) == 3
    def test_92_93(self):
        assert _score_spo2_scale1(92) == 2
        assert _score_spo2_scale1(93) == 2
    def test_94_95(self):
        assert _score_spo2_scale1(94) == 1
        assert _score_spo2_scale1(95) == 1
    def test_ge96(self):
        assert _score_spo2_scale1(96) == 0
        assert _score_spo2_scale1(99) == 0


class TestSpO2Scale2:
    def test_le83(self):
        assert _score_spo2_scale2(83, False) == 3
    def test_84_85(self):
        assert _score_spo2_scale2(84, False) == 2
        assert _score_spo2_scale2(85, True) == 2
    def test_86_87(self):
        assert _score_spo2_scale2(86, False) == 1
        assert _score_spo2_scale2(87, True) == 1
    def test_88_92_on_air(self):
        assert _score_spo2_scale2(88, False) == 0
        assert _score_spo2_scale2(92, False) == 0
    def test_93_94_on_o2(self):
        assert _score_spo2_scale2(93, True) == 1
        assert _score_spo2_scale2(94, True) == 1
    def test_95_96_on_o2(self):
        assert _score_spo2_scale2(95, True) == 2
        assert _score_spo2_scale2(96, True) == 2
    def test_ge97_on_o2(self):
        assert _score_spo2_scale2(97, True) == 3
        assert _score_spo2_scale2(100, True) == 3
    def test_93_plus_on_air(self):
        assert _score_spo2_scale2(93, False) == 0
        assert _score_spo2_scale2(97, False) == 0


class TestSystolicBP:
    def test_le90(self):
        assert _score_systolic_bp(90) == 3
    def test_91_100(self):
        assert _score_systolic_bp(91) == 2
        assert _score_systolic_bp(100) == 2
    def test_101_110(self):
        assert _score_systolic_bp(101) == 1
        assert _score_systolic_bp(110) == 1
    def test_111_219(self):
        assert _score_systolic_bp(111) == 0
        assert _score_systolic_bp(219) == 0
    def test_ge220(self):
        assert _score_systolic_bp(220) == 3
        assert _score_systolic_bp(250) == 3


class TestPulse:
    def test_le40(self):
        assert _score_pulse(40) == 3
    def test_41_50(self):
        assert _score_pulse(41) == 1
        assert _score_pulse(50) == 1
    def test_51_90(self):
        assert _score_pulse(51) == 0
        assert _score_pulse(90) == 0
    def test_91_110(self):
        assert _score_pulse(91) == 1
        assert _score_pulse(110) == 1
    def test_111_130(self):
        assert _score_pulse(111) == 2
        assert _score_pulse(130) == 2
    def test_ge131(self):
        assert _score_pulse(131) == 3


class TestConsciousness:
    def test_alert(self):
        assert _score_consciousness(ConsciousnessLevel.ALERT) == 0
    def test_non_alert(self):
        assert _score_consciousness(ConsciousnessLevel.CONFUSION) == 3
        assert _score_consciousness(ConsciousnessLevel.VOICE) == 3
        assert _score_consciousness(ConsciousnessLevel.PAIN) == 3
        assert _score_consciousness(ConsciousnessLevel.UNRESPONSIVE) == 3


class TestTemperature:
    def test_le35(self):
        assert _score_temperature(35.0) == 3
        assert _score_temperature(34.0) == 3
    def test_35_1_to_36(self):
        assert _score_temperature(35.1) == 1
        assert _score_temperature(36.0) == 1
    def test_36_1_to_38(self):
        assert _score_temperature(36.1) == 0
        assert _score_temperature(38.0) == 0
    def test_38_1_to_39(self):
        assert _score_temperature(38.1) == 1
        assert _score_temperature(39.0) == 1
    def test_ge39_1(self):
        assert _score_temperature(39.1) == 2
        assert _score_temperature(40.0) == 2


# --- Aggregate score tests ---

def _normal_params(**kwargs) -> NEWS2Params:
    """All-normal baseline: score 0."""
    defaults = dict(
        respiration_rate=15,
        spo2=97,
        spo2_scale=SpO2Scale.SCALE_1,
        on_supplemental_o2=False,
        systolic_bp=120,
        pulse=70,
        consciousness=ConsciousnessLevel.ALERT,
        temperature=37.0,
    )
    defaults.update(kwargs)
    return NEWS2Params(**defaults)


def test_news2_minimum_score():
    result = calculate_news2(_normal_params())
    assert result.value == 0
    assert "Low clinical risk" in result.interpretation


def test_news2_maximum_score():
    """All worst values → maximum score."""
    params = NEWS2Params(
        respiration_rate=4,
        spo2=80,
        spo2_scale=SpO2Scale.SCALE_1,
        on_supplemental_o2=True,
        systolic_bp=80,
        pulse=35,
        consciousness=ConsciousnessLevel.UNRESPONSIVE,
        temperature=34.0,
    )
    result = calculate_news2(params)
    # resp=3, spo2=3, o2=2, bp=3, pulse=3, consciousness=3, temp=3 = 20
    assert result.value == 20
    assert "High clinical risk" in result.interpretation


def test_news2_low_risk_score_4():
    # resp_rate=21→2, temp=38.5→1, pulse=95→1 = 4; rest normal
    result = calculate_news2(_normal_params(respiration_rate=21, temperature=38.5, pulse=95))
    assert result.value == 4
    assert "Low clinical risk" in result.interpretation


def test_news2_medium_risk_score_5():
    # resp=21→2, temp=38.5→1, pulse=95→1, bp=100→2 = 6
    result = calculate_news2(_normal_params(respiration_rate=21, temperature=38.5, pulse=95, systolic_bp=100))
    assert result.value == 6
    assert "Medium clinical risk" in result.interpretation


def test_news2_medium_risk_single_param_3():
    """Score of 3 in single parameter triggers medium even if total < 5."""
    # consciousness=VOICE→3, rest normal → total=3
    result = calculate_news2(_normal_params(consciousness=ConsciousnessLevel.VOICE))
    assert result.value == 3
    assert "Medium clinical risk" in result.interpretation


def test_news2_high_risk_score_7():
    # resp=4→3, spo2=91→3, pulse=35→3 = 9 + rest normal
    result = calculate_news2(_normal_params(respiration_rate=4, spo2=91, pulse=35))
    assert result.value == 9
    assert "High clinical risk" in result.interpretation


def test_news2_scale2_normal_on_air():
    result = calculate_news2(_normal_params(spo2=90, spo2_scale=SpO2Scale.SCALE_2))
    assert result.value == 0  # 88-92 on air = 0 for scale 2


def test_news2_scale2_high_spo2_on_o2():
    """Scale 2: SpO2 ≥97 on O2 → score 3."""
    result = calculate_news2(_normal_params(spo2=98, spo2_scale=SpO2Scale.SCALE_2, on_supplemental_o2=True))
    # spo2=3, o2=2 = 5 → medium
    assert result.value == 5
    assert "Medium clinical risk" in result.interpretation


def test_news2_supplemental_o2_adds_2():
    result = calculate_news2(_normal_params(on_supplemental_o2=True))
    assert result.value == 2


def test_news2_evidence():
    result = calculate_news2(_normal_params())
    assert result.evidence.source_doi == "10.7861/clinmedicine.19-3-260"
    assert result.evidence.level == "Guideline"


def test_news2_fhir():
    result = calculate_news2(_normal_params())
    assert result.fhir_code == "1104051000000101"
    assert result.fhir_system == "http://snomed.info/sct"

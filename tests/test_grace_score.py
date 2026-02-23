import pytest
from open_medicine.mcp.calculators.grace_score import calculate_grace_score, GRACEScoreParams


def _base(**kwargs):
    defaults = dict(age=50, heart_rate=70, systolic_bp=120, creatinine=0.9, killip_class=1)
    defaults.update(kwargs)
    return GRACEScoreParams(**defaults)


def test_grace_minimum():
    # Age <30 → 0, HR <50 → 0, SBP ≥200 → 0, Cr 0-0.39 → 1, Killip I → 0
    params = GRACEScoreParams(age=25, heart_rate=40, systolic_bp=200, creatinine=0.3, killip_class=1)
    result = calculate_grace_score(params)
    assert result.value == 1  # only creatinine contributes 1


def test_grace_maximum():
    # Age ≥90→100, HR ≥200→46, SBP <80→58, Cr ≥4→28, Killip IV→59, arrest→39, ST→28, enzymes→14
    params = GRACEScoreParams(
        age=95, heart_rate=210, systolic_bp=70, creatinine=5.0, killip_class=4,
        cardiac_arrest_at_admission=True, st_segment_deviation=True, elevated_cardiac_enzymes=True,
    )
    result = calculate_grace_score(params)
    assert result.value == 100 + 46 + 58 + 28 + 59 + 39 + 28 + 14  # 372
    assert "High risk" in result.interpretation


def test_grace_low_risk():
    # Build a low-risk case: score ≤ 108
    params = GRACEScoreParams(age=50, heart_rate=70, systolic_bp=140, creatinine=0.9, killip_class=1)
    result = calculate_grace_score(params)
    # age 50-59→41, HR 70-89→9, SBP 140-159→24, Cr 0.8-1.19→7, Killip I→0 = 81
    assert result.value == 81
    assert "Low risk" in result.interpretation


def test_grace_intermediate_risk():
    # Score 109-140
    params = GRACEScoreParams(age=70, heart_rate=90, systolic_bp=100, creatinine=1.0, killip_class=1)
    # age 70-79→75, HR 90-109→15, SBP 100-119→43, Cr 0.8-1.19→7, Killip I→0 = 140
    result = calculate_grace_score(params)
    assert result.value == 140
    assert "Intermediate risk" in result.interpretation


def test_grace_high_risk():
    # Score > 140
    params = GRACEScoreParams(
        age=70, heart_rate=90, systolic_bp=100, creatinine=1.0, killip_class=1,
        elevated_cardiac_enzymes=True,
    )
    result = calculate_grace_score(params)
    assert result.value == 154
    assert "High risk" in result.interpretation


def test_grace_age_scoring():
    base = dict(heart_rate=40, systolic_bp=200, creatinine=0.3, killip_class=1)
    assert calculate_grace_score(GRACEScoreParams(age=25, **base)).value == 1  # 0 + 1
    assert calculate_grace_score(GRACEScoreParams(age=35, **base)).value == 9  # 8 + 1
    assert calculate_grace_score(GRACEScoreParams(age=45, **base)).value == 26  # 25 + 1
    assert calculate_grace_score(GRACEScoreParams(age=55, **base)).value == 42  # 41 + 1
    assert calculate_grace_score(GRACEScoreParams(age=65, **base)).value == 59  # 58 + 1
    assert calculate_grace_score(GRACEScoreParams(age=75, **base)).value == 76  # 75 + 1
    assert calculate_grace_score(GRACEScoreParams(age=85, **base)).value == 92  # 91 + 1
    assert calculate_grace_score(GRACEScoreParams(age=95, **base)).value == 101  # 100 + 1


def test_grace_evidence_doi():
    result = calculate_grace_score(_base())
    assert result.evidence.source_doi == "10.1136/bmj.38985.646481.55"


def test_grace_fhir():
    result = calculate_grace_score(_base())
    assert result.fhir_system == "http://loinc.org"

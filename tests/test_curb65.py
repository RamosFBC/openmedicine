from open_medicine.mcp.calculators.curb65 import calculate_curb65, CURB65Params


def test_curb65_low_risk():
    """Young, healthy vitals = score 0, outpatient."""
    params = CURB65Params(confusion=False, bun=10.0, respiratory_rate=18, systolic_bp=120, diastolic_bp=80, age=40)
    res = calculate_curb65(params)
    assert res.value == 0
    assert "Low risk" in res.interpretation
    assert "outpatient" in res.interpretation.lower()
    assert res.evidence.source_doi == "10.1136/thorax.58.5.377"


def test_curb65_moderate_risk():
    """Confusion + age >= 65 = score 2, moderate risk."""
    params = CURB65Params(confusion=True, bun=15.0, respiratory_rate=22, systolic_bp=110, diastolic_bp=70, age=70)
    res = calculate_curb65(params)
    assert res.value == 2
    assert "Moderate risk" in res.interpretation


def test_curb65_high_risk():
    """All 5 criteria met = score 5, severe pneumonia."""
    params = CURB65Params(confusion=True, bun=25.0, respiratory_rate=35, systolic_bp=80, diastolic_bp=50, age=75)
    res = calculate_curb65(params)
    assert res.value == 5
    assert "High risk" in res.interpretation
    assert "severe pneumonia" in res.interpretation.lower()


def test_curb65_bp_diastolic_only():
    """Diastolic <= 60 alone triggers the BP criterion."""
    params = CURB65Params(confusion=False, bun=10.0, respiratory_rate=18, systolic_bp=120, diastolic_bp=60, age=40)
    res = calculate_curb65(params)
    assert res.value == 1
    assert "Low risk" in res.interpretation

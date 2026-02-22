from open_medicine.mcp.calculators.hasbled import calculate_hasbled, HASBLEDParams


def test_hasbled_low_risk():
    """All factors false = score 0, low risk."""
    params = HASBLEDParams()
    res = calculate_hasbled(params)
    assert res.value == 0
    assert "Low bleeding risk" in res.interpretation
    assert res.evidence.source_doi == "10.1378/chest.10-0134"


def test_hasbled_moderate_risk():
    """Hypertension + elderly = score 2, moderate risk."""
    params = HASBLEDParams(hypertension=True, elderly=True)
    res = calculate_hasbled(params)
    assert res.value == 2
    assert "Moderate bleeding risk" in res.interpretation


def test_hasbled_high_risk():
    """Score >= 3 triggers high bleeding risk warning."""
    params = HASBLEDParams(
        hypertension=True,
        abnormal_renal_function=True,
        stroke=True,
        bleeding=True
    )
    res = calculate_hasbled(params)
    assert res.value == 4
    assert "High bleeding risk" in res.interpretation


def test_hasbled_max_score():
    """All 9 factors true = score 9."""
    params = HASBLEDParams(
        hypertension=True,
        abnormal_renal_function=True,
        abnormal_liver_function=True,
        stroke=True,
        bleeding=True,
        labile_inr=True,
        elderly=True,
        drugs=True,
        alcohol=True
    )
    res = calculate_hasbled(params)
    assert res.value == 9

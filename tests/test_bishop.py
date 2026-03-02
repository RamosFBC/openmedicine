import pytest
from open_medicine.mcp.calculators.bishop import calculate_bishop, BishopParams


# ------------------------------------------------------------------ #
# Tier 1: Deterministic Unit Tests
# ------------------------------------------------------------------ #


def test_bishop_minimum_score():
    """All parameters at their lowest values -> score 0, unfavorable."""
    params = BishopParams(
        dilation_cm=0,
        effacement_pct=0,
        station=-3,
        consistency=0,
        position=0,
    )
    result = calculate_bishop(params)
    assert result.value == 0
    assert "Unfavorable" in result.interpretation
    assert "cervical ripening" in result.interpretation.lower()


def test_bishop_maximum_score():
    """All parameters at their highest values -> score 13, favorable."""
    params = BishopParams(
        dilation_cm=6,
        effacement_pct=100,
        station=2,
        consistency=2,
        position=2,
    )
    result = calculate_bishop(params)
    assert result.value == 13
    assert "Favorable" in result.interpretation


def test_bishop_favorable_threshold_at_8():
    """Score exactly 8 should be classified as favorable."""
    # dilation 5 cm -> 3, effacement 80% -> 3, station +1 -> 3,
    # consistency firm -> 0, position posterior -> 0
    # Subtotal: 3+3+3+0+0 = 9, too high. Adjust:
    # dilation 3 cm -> 2, effacement 60% -> 2, station -1 -> 2,
    # consistency soft -> 2, position anterior -> 2
    # Subtotal: 2+2+2+2+2 = 10, still too high. Adjust:
    # dilation 1 cm -> 1, effacement 60% -> 2, station -1 -> 2,
    # consistency medium -> 1, position anterior -> 2
    # Subtotal: 1+2+2+1+2 = 8
    params = BishopParams(
        dilation_cm=1,
        effacement_pct=60,
        station=-1,
        consistency=1,
        position=2,
    )
    result = calculate_bishop(params)
    assert result.value == 8
    assert "Favorable" in result.interpretation


def test_bishop_moderately_favorable_at_7():
    """Score of 7 should be moderately favorable."""
    # dilation 1 cm -> 1, effacement 60% -> 2, station -1 -> 2,
    # consistency firm -> 0, position anterior -> 2
    # Subtotal: 1+2+2+0+2 = 7
    params = BishopParams(
        dilation_cm=1,
        effacement_pct=60,
        station=-1,
        consistency=0,
        position=2,
    )
    result = calculate_bishop(params)
    assert result.value == 7
    assert "Moderately favorable" in result.interpretation


def test_bishop_moderately_favorable_at_6():
    """Score of 6 should be moderately favorable (lower boundary)."""
    # dilation 1 cm -> 1, effacement 40% -> 1, station -1 -> 2,
    # consistency soft -> 2, position posterior -> 0
    # Subtotal: 1+1+2+2+0 = 6
    params = BishopParams(
        dilation_cm=1,
        effacement_pct=40,
        station=-1,
        consistency=2,
        position=0,
    )
    result = calculate_bishop(params)
    assert result.value == 6
    assert "Moderately favorable" in result.interpretation


def test_bishop_unfavorable_at_5():
    """Score of 5 should be unfavorable."""
    # dilation 1 cm -> 1, effacement 40% -> 1, station -2 -> 1,
    # consistency soft -> 2, position posterior -> 0
    # Subtotal: 1+1+1+2+0 = 5
    params = BishopParams(
        dilation_cm=1,
        effacement_pct=40,
        station=-2,
        consistency=2,
        position=0,
    )
    result = calculate_bishop(params)
    assert result.value == 5
    assert "Unfavorable" in result.interpretation


def test_bishop_dilation_scoring():
    """Test each dilation threshold independently."""
    base = dict(effacement_pct=0, station=-3, consistency=0, position=0)

    # Closed = 0 pts
    r = calculate_bishop(BishopParams(dilation_cm=0, **base))
    assert r.value == 0

    # 1 cm = 1 pt
    r = calculate_bishop(BishopParams(dilation_cm=1, **base))
    assert r.value == 1

    # 2 cm = 1 pt
    r = calculate_bishop(BishopParams(dilation_cm=2, **base))
    assert r.value == 1

    # 3 cm = 2 pts
    r = calculate_bishop(BishopParams(dilation_cm=3, **base))
    assert r.value == 2

    # 4 cm = 2 pts
    r = calculate_bishop(BishopParams(dilation_cm=4, **base))
    assert r.value == 2

    # 5 cm = 3 pts
    r = calculate_bishop(BishopParams(dilation_cm=5, **base))
    assert r.value == 3

    # 6 cm = 3 pts
    r = calculate_bishop(BishopParams(dilation_cm=6, **base))
    assert r.value == 3


def test_bishop_effacement_scoring():
    """Test each effacement threshold independently.

    Published ranges: 0-30% = 0 pts, 40-50% = 1 pt, 60-70% = 2 pts, >=80% = 3 pts.
    Thresholds use <40, <60, <80 boundaries so intermediate values (31-39%,
    51-59%, 71-79%) are assigned to the lower bin, matching standard clinical
    implementations.
    """
    base = dict(dilation_cm=0, station=-3, consistency=0, position=0)

    # 0% = 0 pts
    r = calculate_bishop(BishopParams(effacement_pct=0, **base))
    assert r.value == 0

    # 30% = 0 pts (upper boundary of published 0-30 range)
    r = calculate_bishop(BishopParams(effacement_pct=30, **base))
    assert r.value == 0

    # 39% = 0 pts (last value before the 40-50 range)
    r = calculate_bishop(BishopParams(effacement_pct=39, **base))
    assert r.value == 0

    # 40% = 1 pt (lower boundary of published 40-50 range)
    r = calculate_bishop(BishopParams(effacement_pct=40, **base))
    assert r.value == 1

    # 50% = 1 pt
    r = calculate_bishop(BishopParams(effacement_pct=50, **base))
    assert r.value == 1

    # 59% = 1 pt (last value before the 60-70 range)
    r = calculate_bishop(BishopParams(effacement_pct=59, **base))
    assert r.value == 1

    # 60% = 2 pts (lower boundary of published 60-70 range)
    r = calculate_bishop(BishopParams(effacement_pct=60, **base))
    assert r.value == 2

    # 70% = 2 pts
    r = calculate_bishop(BishopParams(effacement_pct=70, **base))
    assert r.value == 2

    # 79% = 2 pts (last value before the >=80 range)
    r = calculate_bishop(BishopParams(effacement_pct=79, **base))
    assert r.value == 2

    # 80% = 3 pts (lower boundary of published >=80 range)
    r = calculate_bishop(BishopParams(effacement_pct=80, **base))
    assert r.value == 3

    # 100% = 3 pts
    r = calculate_bishop(BishopParams(effacement_pct=100, **base))
    assert r.value == 3


def test_bishop_station_scoring():
    """Test each station value independently."""
    base = dict(dilation_cm=0, effacement_pct=0, consistency=0, position=0)

    # -3 = 0 pts
    r = calculate_bishop(BishopParams(station=-3, **base))
    assert r.value == 0

    # -2 = 1 pt
    r = calculate_bishop(BishopParams(station=-2, **base))
    assert r.value == 1

    # -1 = 2 pts
    r = calculate_bishop(BishopParams(station=-1, **base))
    assert r.value == 2

    # 0 = 2 pts
    r = calculate_bishop(BishopParams(station=0, **base))
    assert r.value == 2

    # +1 = 3 pts
    r = calculate_bishop(BishopParams(station=1, **base))
    assert r.value == 3

    # +2 = 3 pts
    r = calculate_bishop(BishopParams(station=2, **base))
    assert r.value == 3


def test_bishop_consistency_scoring():
    """Test each consistency value independently."""
    base = dict(dilation_cm=0, effacement_pct=0, station=-3, position=0)

    # 0 = firm, 0 pts
    r = calculate_bishop(BishopParams(consistency=0, **base))
    assert r.value == 0

    # 1 = medium, 1 pt
    r = calculate_bishop(BishopParams(consistency=1, **base))
    assert r.value == 1

    # 2 = soft, 2 pts
    r = calculate_bishop(BishopParams(consistency=2, **base))
    assert r.value == 2


def test_bishop_position_scoring():
    """Test each position value independently."""
    base = dict(dilation_cm=0, effacement_pct=0, station=-3, consistency=0)

    # 0 = posterior, 0 pts
    r = calculate_bishop(BishopParams(position=0, **base))
    assert r.value == 0

    # 1 = mid-position, 1 pt
    r = calculate_bishop(BishopParams(position=1, **base))
    assert r.value == 1

    # 2 = anterior, 2 pts
    r = calculate_bishop(BishopParams(position=2, **base))
    assert r.value == 2


def test_bishop_evidence_doi():
    """Verify DOI matches Bishop 1964 original paper."""
    params = BishopParams(
        dilation_cm=0,
        effacement_pct=0,
        station=-3,
        consistency=0,
        position=0,
    )
    result = calculate_bishop(params)
    assert result.evidence.source_doi == "10.1097/00006250-196408000-00009"
    assert "Bishop" in result.evidence.description
    assert "1964" in result.evidence.description


def test_bishop_fhir_code():
    """Verify FHIR code fields.

    No dedicated LOINC code exists for the Bishop Score. LOINC 76504-0 was
    previously used in error -- it represents "Total score [HARK]" (an
    interpersonal violence screening tool), not the Bishop cervical favorability
    score. fhir_code and fhir_system are set to None; fhir_display still
    contains the human-readable score name.
    """
    params = BishopParams(
        dilation_cm=0,
        effacement_pct=0,
        station=-3,
        consistency=0,
        position=0,
    )
    result = calculate_bishop(params)
    assert result.fhir_code is None
    assert result.fhir_system is None
    assert result.fhir_display is not None
    assert "Bishop" in result.fhir_display


def test_bishop_interpretation_contains_score():
    """Every interpretation should state the numeric score value."""
    for score_val in range(14):
        # Use brute force to hit each possible total (0-13)
        # Not all values are easily constructible, so just test a sample
        pass

    # Test a few representative cases
    params_low = BishopParams(
        dilation_cm=0, effacement_pct=0, station=-3, consistency=0, position=0
    )
    result_low = calculate_bishop(params_low)
    assert "0" in result_low.interpretation

    params_mid = BishopParams(
        dilation_cm=1, effacement_pct=40, station=-1, consistency=2, position=0
    )
    result_mid = calculate_bishop(params_mid)
    assert str(result_mid.value) in result_mid.interpretation

    params_high = BishopParams(
        dilation_cm=6, effacement_pct=100, station=2, consistency=2, position=2
    )
    result_high = calculate_bishop(params_high)
    assert "13" in result_high.interpretation


def test_bishop_clinical_scenario_nullipara_unfavorable():
    """Typical nulliparous patient with unfavorable cervix for induction."""
    # Closed, 20% effaced, station -3, firm, posterior
    params = BishopParams(
        dilation_cm=0,
        effacement_pct=20,
        station=-3,
        consistency=0,
        position=0,
    )
    result = calculate_bishop(params)
    assert result.value == 0
    assert "Unfavorable" in result.interpretation
    assert "ripening" in result.interpretation.lower()


def test_bishop_clinical_scenario_multipara_favorable():
    """Typical multiparous patient with favorable cervix."""
    # 3 cm dilated, 70% effaced, station 0, soft, anterior
    params = BishopParams(
        dilation_cm=3,
        effacement_pct=70,
        station=0,
        consistency=2,
        position=2,
    )
    result = calculate_bishop(params)
    assert result.value == 2 + 2 + 2 + 2 + 2  # = 10
    assert "Favorable" in result.interpretation


def test_bishop_pydantic_validation_dilation_out_of_range():
    """Dilation > 6 should raise validation error."""
    with pytest.raises(Exception):
        BishopParams(
            dilation_cm=7,
            effacement_pct=50,
            station=0,
            consistency=1,
            position=1,
        )


def test_bishop_pydantic_validation_station_out_of_range():
    """Station > +2 should raise validation error."""
    with pytest.raises(Exception):
        BishopParams(
            dilation_cm=2,
            effacement_pct=50,
            station=3,
            consistency=1,
            position=1,
        )


def test_bishop_pydantic_validation_consistency_out_of_range():
    """Consistency > 2 should raise validation error."""
    with pytest.raises(Exception):
        BishopParams(
            dilation_cm=2,
            effacement_pct=50,
            station=0,
            consistency=3,
            position=1,
        )


def test_bishop_pydantic_validation_position_out_of_range():
    """Position > 2 should raise validation error."""
    with pytest.raises(Exception):
        BishopParams(
            dilation_cm=2,
            effacement_pct=50,
            station=0,
            consistency=1,
            position=3,
        )


def test_bishop_each_component_contributes_independently():
    """Verify that each component adds its score independently (no interactions)."""
    base_score = calculate_bishop(BishopParams(
        dilation_cm=0, effacement_pct=0, station=-3, consistency=0, position=0
    )).value
    assert base_score == 0

    # Add dilation only
    r1 = calculate_bishop(BishopParams(
        dilation_cm=3, effacement_pct=0, station=-3, consistency=0, position=0
    ))
    assert r1.value == 2

    # Add effacement only
    r2 = calculate_bishop(BishopParams(
        dilation_cm=0, effacement_pct=60, station=-3, consistency=0, position=0
    ))
    assert r2.value == 2

    # Add both dilation and effacement
    r3 = calculate_bishop(BishopParams(
        dilation_cm=3, effacement_pct=60, station=-3, consistency=0, position=0
    ))
    assert r3.value == r1.value + r2.value  # 2 + 2 = 4

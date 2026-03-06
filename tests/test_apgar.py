import pytest
from open_medicine.mcp.calculators.apgar import calculate_apgar, ApgarParams


# ---- Tier 1: Deterministic Unit Tests ----


def test_apgar_minimum_score():
    """Test lowest possible score (0) with all criteria absent/worst."""
    params = ApgarParams(
        appearance=0,
        pulse=0,
        grimace=0,
        activity=0,
        respiration=0,
    )
    result = calculate_apgar(params)
    assert result.value == 0
    assert "Low (critically low)" in result.interpretation
    assert "Immediate resuscitation" in result.interpretation


def test_apgar_maximum_score():
    """Test highest possible score (10) with all criteria optimal."""
    params = ApgarParams(
        appearance=2,
        pulse=2,
        grimace=2,
        activity=2,
        respiration=2,
    )
    result = calculate_apgar(params)
    assert result.value == 10
    assert "Reassuring" in result.interpretation
    assert "good condition" in result.interpretation


def test_apgar_score_3_low_boundary():
    """Test score of 3, the upper boundary of the critically low range."""
    params = ApgarParams(
        appearance=1,
        pulse=1,
        grimace=1,
        activity=0,
        respiration=0,
    )
    result = calculate_apgar(params)
    assert result.value == 3
    assert "Low (critically low)" in result.interpretation
    assert "Immediate resuscitation" in result.interpretation


def test_apgar_score_4_moderate_boundary():
    """Test score of 4, the lower boundary of the moderately abnormal range."""
    params = ApgarParams(
        appearance=1,
        pulse=1,
        grimace=1,
        activity=1,
        respiration=0,
    )
    result = calculate_apgar(params)
    assert result.value == 4
    assert "Moderately abnormal" in result.interpretation
    assert "resuscitative measures" in result.interpretation


def test_apgar_score_6_moderate_upper():
    """Test score of 6, the upper boundary of the moderately abnormal range."""
    params = ApgarParams(
        appearance=1,
        pulse=2,
        grimace=1,
        activity=1,
        respiration=1,
    )
    result = calculate_apgar(params)
    assert result.value == 6
    assert "Moderately abnormal" in result.interpretation


def test_apgar_score_7_reassuring_boundary():
    """Test score of 7, the lower boundary of the reassuring range."""
    params = ApgarParams(
        appearance=1,
        pulse=2,
        grimace=2,
        activity=1,
        respiration=1,
    )
    result = calculate_apgar(params)
    assert result.value == 7
    assert "Reassuring" in result.interpretation
    assert "good condition" in result.interpretation


def test_apgar_score_each_component_contributes():
    """Verify each individual component correctly adds to the total."""
    # Only appearance = 2, rest 0 -> score 2
    params = ApgarParams(appearance=2, pulse=0, grimace=0, activity=0, respiration=0)
    assert calculate_apgar(params).value == 2

    # Only pulse = 2, rest 0 -> score 2
    params = ApgarParams(appearance=0, pulse=2, grimace=0, activity=0, respiration=0)
    assert calculate_apgar(params).value == 2

    # Only grimace = 2, rest 0 -> score 2
    params = ApgarParams(appearance=0, pulse=0, grimace=2, activity=0, respiration=0)
    assert calculate_apgar(params).value == 2

    # Only activity = 2, rest 0 -> score 2
    params = ApgarParams(appearance=0, pulse=0, grimace=0, activity=2, respiration=0)
    assert calculate_apgar(params).value == 2

    # Only respiration = 2, rest 0 -> score 2
    params = ApgarParams(appearance=0, pulse=0, grimace=0, activity=0, respiration=2)
    assert calculate_apgar(params).value == 2


def test_apgar_all_ones():
    """Score of 5 (all components at 1) is moderately abnormal."""
    params = ApgarParams(
        appearance=1,
        pulse=1,
        grimace=1,
        activity=1,
        respiration=1,
    )
    result = calculate_apgar(params)
    assert result.value == 5
    assert "Moderately abnormal" in result.interpretation


def test_apgar_evidence_doi():
    """Verify DOI is correct for the original 1953 Apgar paper."""
    params = ApgarParams(
        appearance=2,
        pulse=2,
        grimace=2,
        activity=2,
        respiration=2,
    )
    result = calculate_apgar(params)
    assert result.evidence.source_doi == "10.1213/00000539-195301000-00041"
    assert result.evidence.level == "Derivation & Validation Study"
    assert "Apgar" in result.evidence.description


def test_apgar_fhir_code():
    """Verify FHIR code represents the Apgar Score output concept."""
    params = ApgarParams(
        appearance=2,
        pulse=2,
        grimace=2,
        activity=2,
        respiration=2,
    )
    result = calculate_apgar(params)
    assert result.fhir_code == "9274-2"
    assert result.fhir_system == "http://loinc.org"
    assert "Apgar" in result.fhir_display


def test_apgar_interpretation_includes_score_value():
    """Interpretation string always includes the numeric score."""
    for total in range(11):
        # Distribute score across components
        components = [0, 0, 0, 0, 0]
        remaining = total
        for i in range(5):
            assign = min(remaining, 2)
            components[i] = assign
            remaining -= assign
        params = ApgarParams(
            appearance=components[0],
            pulse=components[1],
            grimace=components[2],
            activity=components[3],
            respiration=components[4],
        )
        result = calculate_apgar(params)
        assert str(total) in result.interpretation


def test_apgar_pydantic_validation_rejects_invalid():
    """Pydantic should reject out-of-range component scores."""
    with pytest.raises(Exception):
        ApgarParams(appearance=3, pulse=0, grimace=0, activity=0, respiration=0)

    with pytest.raises(Exception):
        ApgarParams(appearance=-1, pulse=0, grimace=0, activity=0, respiration=0)

    with pytest.raises(Exception):
        ApgarParams(appearance=0, pulse=0, grimace=0, activity=0, respiration=3)


def test_apgar_score_9_near_perfect():
    """Test score of 9, typical for healthy newborn with mild acrocyanosis."""
    params = ApgarParams(
        appearance=1,  # acrocyanosis is common even in healthy newborns
        pulse=2,
        grimace=2,
        activity=2,
        respiration=2,
    )
    result = calculate_apgar(params)
    assert result.value == 9
    assert "Reassuring" in result.interpretation


def test_apgar_original_paper_good_category():
    """
    Cross-validate: Original 1953 paper classified 8-10 as 'good' condition.
    Modern thresholds (7-10 = reassuring) are consistent.
    """
    for score_target in [8, 9, 10]:
        components = [0, 0, 0, 0, 0]
        remaining = score_target
        for i in range(5):
            assign = min(remaining, 2)
            components[i] = assign
            remaining -= assign
        params = ApgarParams(
            appearance=components[0],
            pulse=components[1],
            grimace=components[2],
            activity=components[3],
            respiration=components[4],
        )
        result = calculate_apgar(params)
        assert result.value == score_target
        assert "Reassuring" in result.interpretation


def test_apgar_original_paper_fair_category():
    """
    Cross-validate: Original 1953 paper classified 3-7 as 'fair' condition.
    Modern thresholds split this into 4-6 moderately abnormal + 7 reassuring.
    Score of 5 should be moderately abnormal.
    """
    params = ApgarParams(
        appearance=1,
        pulse=1,
        grimace=1,
        activity=1,
        respiration=1,
    )
    result = calculate_apgar(params)
    assert result.value == 5
    assert "Moderately abnormal" in result.interpretation


def test_apgar_original_paper_poor_category():
    """
    Cross-validate: Original 1953 paper classified 0-2 as 'poor' condition.
    Modern thresholds: 0-3 = low (critically low). These ranges overlap.
    Score of 2 should be critically low.
    """
    params = ApgarParams(
        appearance=1,
        pulse=1,
        grimace=0,
        activity=0,
        respiration=0,
    )
    result = calculate_apgar(params)
    assert result.value == 2
    assert "Low (critically low)" in result.interpretation

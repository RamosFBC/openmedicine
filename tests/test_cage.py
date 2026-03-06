import pytest
from open_medicine.mcp.calculators.cage import calculate_cage, CAGEParams


def _make_params(**kwargs):
    """Helper to create CAGEParams with defaults for all items as False (no alcohol problems)."""
    defaults = dict(
        cut_down=False,
        annoyed=False,
        guilty=False,
        eye_opener=False,
    )
    defaults.update(kwargs)
    return CAGEParams(**defaults)


# ---------------------------------------------------------------------------
# Minimum and maximum score tests
# ---------------------------------------------------------------------------


def test_cage_minimum_score():
    """All items answered No = total 0, negative screen."""
    result = calculate_cage(_make_params())
    assert result.value == 0
    assert "Negative screen" in result.interpretation
    assert "CAGE score is 0/4" in result.interpretation


def test_cage_maximum_score():
    """All items answered Yes = total 4, positive screen (very high suspicion)."""
    params = CAGEParams(
        cut_down=True,
        annoyed=True,
        guilty=True,
        eye_opener=True,
    )
    result = calculate_cage(params)
    assert result.value == 4
    assert "Positive screen" in result.interpretation
    assert "very high suspicion" in result.interpretation.lower()
    assert "CAGE score is 4/4" in result.interpretation


# ---------------------------------------------------------------------------
# Threshold boundary tests (score 2 is the clinically significant threshold)
# ---------------------------------------------------------------------------


def test_cage_score_1_below_threshold():
    """Score 1: below clinical threshold (>= 2), negative screen."""
    result = calculate_cage(_make_params(cut_down=True))
    assert result.value == 1
    assert "Negative screen" in result.interpretation
    assert "sub-threshold" in result.interpretation.lower()
    assert "below the clinical threshold" in result.interpretation.lower()


def test_cage_score_2_at_threshold():
    """Score 2: at clinical threshold, positive screen (clinically significant)."""
    result = calculate_cage(_make_params(cut_down=True, annoyed=True))
    assert result.value == 2
    assert "Positive screen" in result.interpretation
    assert "clinically significant" in result.interpretation.lower()
    assert "Further evaluation" in result.interpretation


def test_cage_score_3_high_suspicion():
    """Score 3: positive screen, high suspicion."""
    result = calculate_cage(_make_params(cut_down=True, annoyed=True, guilty=True))
    assert result.value == 3
    assert "Positive screen" in result.interpretation
    assert "high suspicion" in result.interpretation.lower()


# ---------------------------------------------------------------------------
# Individual item contribution tests
# ---------------------------------------------------------------------------


def test_cage_only_cut_down():
    """Only Cut down = Yes: score 1."""
    result = calculate_cage(_make_params(cut_down=True))
    assert result.value == 1


def test_cage_only_annoyed():
    """Only Annoyed = Yes: score 1."""
    result = calculate_cage(_make_params(annoyed=True))
    assert result.value == 1


def test_cage_only_guilty():
    """Only Guilty = Yes: score 1."""
    result = calculate_cage(_make_params(guilty=True))
    assert result.value == 1


def test_cage_only_eye_opener():
    """Only Eye-opener = Yes: score 1."""
    result = calculate_cage(_make_params(eye_opener=True))
    assert result.value == 1


def test_cage_each_item_contributes_equally():
    """Each item contributes exactly 1 point."""
    for field in ["cut_down", "annoyed", "guilty", "eye_opener"]:
        result = calculate_cage(_make_params(**{field: True}))
        assert result.value == 1, f"Expected 1 for {field}=True, got {result.value}"


# ---------------------------------------------------------------------------
# All score combinations (exhaustive for 4 boolean items = 16 combinations)
# ---------------------------------------------------------------------------


def test_cage_score_is_sum_of_yes_answers():
    """Score must always equal the number of Yes answers."""
    import itertools
    fields = ["cut_down", "annoyed", "guilty", "eye_opener"]
    for combo in itertools.product([False, True], repeat=4):
        kwargs = dict(zip(fields, combo))
        expected_score = sum(combo)
        params = CAGEParams(**kwargs)
        result = calculate_cage(params)
        assert result.value == expected_score, (
            f"Expected {expected_score} for {kwargs}, got {result.value}"
        )


# ---------------------------------------------------------------------------
# Interpretation content tests
# ---------------------------------------------------------------------------


def test_cage_interpretation_contains_score():
    """Interpretation always includes the numeric score value as 'CAGE score is X/4'."""
    for score in range(5):
        # Build params that yield the target score
        fields = ["cut_down", "annoyed", "guilty", "eye_opener"]
        kwargs = {fields[i]: (i < score) for i in range(4)}
        params = CAGEParams(**kwargs)
        result = calculate_cage(params)
        assert f"CAGE score is {score}/4" in result.interpretation


def test_cage_negative_screen_at_zero():
    """Score 0: Negative screen, no positive responses."""
    result = calculate_cage(_make_params())
    assert "No positive responses" in result.interpretation
    assert "No further evaluation" in result.interpretation


def test_cage_negative_screen_at_one():
    """Score 1: Negative screen (sub-threshold)."""
    result = calculate_cage(_make_params(guilty=True))
    assert "Negative screen" in result.interpretation
    assert "clinical judgment" in result.interpretation.lower()


def test_cage_positive_at_two_recommends_evaluation():
    """Score 2: Positive screen recommends further evaluation."""
    result = calculate_cage(_make_params(cut_down=True, guilty=True))
    assert "Positive screen" in result.interpretation
    assert "AUDIT" in result.interpretation or "DSM-5" in result.interpretation


def test_cage_positive_at_three_recommends_referral():
    """Score 3: Positive screen recommends referral."""
    result = calculate_cage(_make_params(cut_down=True, annoyed=True, guilty=True))
    assert "referral" in result.interpretation.lower()


def test_cage_positive_at_four_recommends_immediate_assessment():
    """Score 4: Positive screen with all items endorsed."""
    params = CAGEParams(
        cut_down=True, annoyed=True, guilty=True, eye_opener=True
    )
    result = calculate_cage(params)
    assert "All four CAGE items" in result.interpretation
    assert "Immediate" in result.interpretation


# ---------------------------------------------------------------------------
# Evidence and FHIR metadata tests
# ---------------------------------------------------------------------------


def test_cage_evidence_doi():
    """Verify DOI matches Ewing JA 1984."""
    result = calculate_cage(_make_params())
    assert result.evidence.source_doi == "10.1001/jama.1984.03350140051025"


def test_cage_evidence_level():
    """Verify evidence level is Derivation & Validation Study."""
    result = calculate_cage(_make_params())
    assert result.evidence.level == "Derivation & Validation Study"


def test_cage_evidence_description():
    """Verify evidence description references Ewing and CAGE."""
    result = calculate_cage(_make_params())
    assert "Ewing" in result.evidence.description
    assert "CAGE" in result.evidence.description


def test_cage_fhir_code():
    """Verify FHIR code is None (no CAGE-specific LOINC code exists)."""
    result = calculate_cage(_make_params())
    assert result.fhir_code is None
    assert result.fhir_system is None
    assert result.fhir_display == "CAGE Questionnaire score"


# ---------------------------------------------------------------------------
# Clinical scenario cross-validation tests (from MDCalc / reference sources)
# ---------------------------------------------------------------------------


def test_cage_clinical_scenario_non_drinker():
    """Non-drinker: all No answers, score 0, negative."""
    result = calculate_cage(CAGEParams(
        cut_down=False,
        annoyed=False,
        guilty=False,
        eye_opener=False,
    ))
    assert result.value == 0
    assert "Negative screen" in result.interpretation


def test_cage_clinical_scenario_social_drinker_no_problems():
    """Social drinker with no alcohol-related concerns: all No, score 0."""
    result = calculate_cage(CAGEParams(
        cut_down=False,
        annoyed=False,
        guilty=False,
        eye_opener=False,
    ))
    assert result.value == 0
    assert "Negative screen" in result.interpretation


def test_cage_clinical_scenario_mild_concern():
    """Mild concern: only felt guilty about drinking. Score 1, negative."""
    result = calculate_cage(CAGEParams(
        cut_down=False,
        annoyed=False,
        guilty=True,
        eye_opener=False,
    ))
    assert result.value == 1
    assert "Negative screen" in result.interpretation


def test_cage_clinical_scenario_possible_aud():
    """Possible AUD: felt should cut down + guilty. Score 2, positive."""
    result = calculate_cage(CAGEParams(
        cut_down=True,
        annoyed=False,
        guilty=True,
        eye_opener=False,
    ))
    assert result.value == 2
    assert "Positive screen" in result.interpretation


def test_cage_clinical_scenario_probable_aud():
    """Probable AUD: cut down + annoyed + eye opener. Score 3, high suspicion."""
    result = calculate_cage(CAGEParams(
        cut_down=True,
        annoyed=True,
        guilty=False,
        eye_opener=True,
    ))
    assert result.value == 3
    assert "Positive screen" in result.interpretation
    assert "high suspicion" in result.interpretation.lower()


def test_cage_clinical_scenario_severe_aud():
    """Severe AUD: all 4 positive. Score 4, very high suspicion."""
    result = calculate_cage(CAGEParams(
        cut_down=True,
        annoyed=True,
        guilty=True,
        eye_opener=True,
    ))
    assert result.value == 4
    assert "Positive screen" in result.interpretation
    assert "very high suspicion" in result.interpretation.lower()


# ---------------------------------------------------------------------------
# Pydantic model tests
# ---------------------------------------------------------------------------


def test_cage_all_fields_required():
    """All four CAGE items are required (no defaults)."""
    with pytest.raises(Exception):
        CAGEParams()  # Missing all fields


def test_cage_missing_one_field():
    """Missing a single field should raise validation error."""
    with pytest.raises(Exception):
        CAGEParams(cut_down=True, annoyed=True, guilty=True)  # Missing eye_opener


# ---------------------------------------------------------------------------
# Verify CAGE is registered in the calculator registry
# ---------------------------------------------------------------------------


def test_cage_registered():
    """Verify calculate_cage is registered in the CALCULATOR_REGISTRY."""
    from open_medicine.mcp.registry import CALCULATOR_REGISTRY
    assert "calculate_cage" in CALCULATOR_REGISTRY
    tool = CALCULATOR_REGISTRY["calculate_cage"]
    assert tool.pydantic_model is CAGEParams
    assert tool.execute_function is calculate_cage

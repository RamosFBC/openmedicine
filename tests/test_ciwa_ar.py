import pytest
from hypothesis import given, strategies as st, settings
from open_medicine.mcp.calculators.ciwa_ar import calculate_ciwa_ar, CIWAArParams


def _make_params(**kwargs):
    """Helper to create CIWAArParams with defaults for all items at 0 (no withdrawal)."""
    defaults = dict(
        nausea_vomiting=0,
        tremor=0,
        paroxysmal_sweats=0,
        anxiety=0,
        agitation=0,
        tactile_disturbances=0,
        auditory_disturbances=0,
        visual_disturbances=0,
        headache=0,
        orientation=0,
    )
    defaults.update(kwargs)
    return CIWAArParams(**defaults)


# ---------------------------------------------------------------------------
# Minimum and maximum score tests
# ---------------------------------------------------------------------------


def test_ciwa_ar_minimum_score():
    """All items at 0 = total 0, absent or minimal withdrawal."""
    result = calculate_ciwa_ar(_make_params())
    assert result.value == 0
    assert "Absent or minimal withdrawal" in result.interpretation
    assert "CIWA-Ar score is 0/67" in result.interpretation


def test_ciwa_ar_maximum_score():
    """All items at maximum = total 67, severe withdrawal."""
    params = CIWAArParams(
        nausea_vomiting=7,
        tremor=7,
        paroxysmal_sweats=7,
        anxiety=7,
        agitation=7,
        tactile_disturbances=7,
        auditory_disturbances=7,
        visual_disturbances=7,
        headache=7,
        orientation=4,
    )
    result = calculate_ciwa_ar(params)
    assert result.value == 67
    assert "Severe withdrawal" in result.interpretation
    assert "CIWA-Ar score is 67/67" in result.interpretation


# ---------------------------------------------------------------------------
# Threshold boundary tests
# ---------------------------------------------------------------------------


def test_ciwa_ar_score_8_upper_minimal():
    """Score 8: upper boundary of absent/minimal withdrawal (score 0-8)."""
    result = calculate_ciwa_ar(_make_params(nausea_vomiting=4, tremor=4))
    assert result.value == 8
    assert "Absent or minimal withdrawal" in result.interpretation
    assert "Pharmacologic treatment is generally not needed" in result.interpretation


def test_ciwa_ar_score_9_lower_mild():
    """Score 9: lower boundary of mild to moderate withdrawal (score 9-15)."""
    result = calculate_ciwa_ar(_make_params(nausea_vomiting=5, tremor=4))
    assert result.value == 9
    assert "Mild to moderate withdrawal" in result.interpretation
    assert "symptom-triggered benzodiazepine" in result.interpretation


def test_ciwa_ar_score_15_upper_mild():
    """Score 15: upper boundary of mild to moderate withdrawal (score 9-15)."""
    result = calculate_ciwa_ar(_make_params(
        nausea_vomiting=5, tremor=5, anxiety=5
    ))
    assert result.value == 15
    assert "Mild to moderate withdrawal" in result.interpretation


def test_ciwa_ar_score_16_lower_moderate():
    """Score 16: lower boundary of moderate to severe withdrawal (score 16-20)."""
    result = calculate_ciwa_ar(_make_params(
        nausea_vomiting=5, tremor=5, anxiety=5, agitation=1
    ))
    assert result.value == 16
    assert "Moderate to severe withdrawal" in result.interpretation
    assert "Benzodiazepine treatment is indicated" in result.interpretation


def test_ciwa_ar_score_20_upper_moderate():
    """Score 20: upper boundary of moderate to severe withdrawal (score 16-20)."""
    result = calculate_ciwa_ar(_make_params(
        nausea_vomiting=5, tremor=5, anxiety=5, agitation=5
    ))
    assert result.value == 20
    assert "Moderate to severe withdrawal" in result.interpretation


def test_ciwa_ar_score_21_lower_severe():
    """Score 21: lower boundary of severe withdrawal (score >20)."""
    result = calculate_ciwa_ar(_make_params(
        nausea_vomiting=7, tremor=7, anxiety=7
    ))
    assert result.value == 21
    assert "Severe withdrawal" in result.interpretation
    assert "ICU-level care" in result.interpretation


# ---------------------------------------------------------------------------
# Individual item contribution tests
# ---------------------------------------------------------------------------


def test_ciwa_ar_nausea_vomiting_only():
    """Nausea/vomiting scored at max (7) with all others 0."""
    result = calculate_ciwa_ar(_make_params(nausea_vomiting=7))
    assert result.value == 7


def test_ciwa_ar_tremor_only():
    """Tremor scored at max (7) with all others 0."""
    result = calculate_ciwa_ar(_make_params(tremor=7))
    assert result.value == 7


def test_ciwa_ar_paroxysmal_sweats_only():
    """Paroxysmal sweats scored at max (7) with all others 0."""
    result = calculate_ciwa_ar(_make_params(paroxysmal_sweats=7))
    assert result.value == 7


def test_ciwa_ar_anxiety_only():
    """Anxiety scored at max (7) with all others 0."""
    result = calculate_ciwa_ar(_make_params(anxiety=7))
    assert result.value == 7


def test_ciwa_ar_agitation_only():
    """Agitation scored at max (7) with all others 0."""
    result = calculate_ciwa_ar(_make_params(agitation=7))
    assert result.value == 7


def test_ciwa_ar_tactile_only():
    """Tactile disturbances scored at max (7) with all others 0."""
    result = calculate_ciwa_ar(_make_params(tactile_disturbances=7))
    assert result.value == 7


def test_ciwa_ar_auditory_only():
    """Auditory disturbances scored at max (7) with all others 0."""
    result = calculate_ciwa_ar(_make_params(auditory_disturbances=7))
    assert result.value == 7


def test_ciwa_ar_visual_only():
    """Visual disturbances scored at max (7) with all others 0."""
    result = calculate_ciwa_ar(_make_params(visual_disturbances=7))
    assert result.value == 7


def test_ciwa_ar_headache_only():
    """Headache scored at max (7) with all others 0."""
    result = calculate_ciwa_ar(_make_params(headache=7))
    assert result.value == 7


def test_ciwa_ar_orientation_only():
    """Orientation scored at max (4) with all others 0."""
    result = calculate_ciwa_ar(_make_params(orientation=4))
    assert result.value == 4


def test_ciwa_ar_orientation_max_is_4():
    """Orientation item has a maximum of 4 (not 7 like other items)."""
    with pytest.raises(Exception):
        CIWAArParams(
            nausea_vomiting=0, tremor=0, paroxysmal_sweats=0, anxiety=0,
            agitation=0, tactile_disturbances=0, auditory_disturbances=0,
            visual_disturbances=0, headache=0, orientation=5,
        )


# ---------------------------------------------------------------------------
# Score additivity test
# ---------------------------------------------------------------------------


def test_ciwa_ar_score_is_sum_of_all_items():
    """Score equals the sum of all individual item scores."""
    params = CIWAArParams(
        nausea_vomiting=3,
        tremor=2,
        paroxysmal_sweats=1,
        anxiety=4,
        agitation=5,
        tactile_disturbances=6,
        auditory_disturbances=0,
        visual_disturbances=2,
        headache=3,
        orientation=2,
    )
    expected = 3 + 2 + 1 + 4 + 5 + 6 + 0 + 2 + 3 + 2  # = 28
    result = calculate_ciwa_ar(params)
    assert result.value == expected


# ---------------------------------------------------------------------------
# Interpretation content tests
# ---------------------------------------------------------------------------


def test_ciwa_ar_interpretation_always_contains_score():
    """Interpretation always includes 'CIWA-Ar score is X/67'."""
    for total in [0, 5, 8, 9, 15, 16, 20, 21, 40, 67]:
        # Build params that yield the target score
        # Use nausea_vomiting (max 7) and tremor (max 7) to accumulate
        # For larger totals, spread across items
        remaining = total
        items = {}
        fields_7 = [
            "nausea_vomiting", "tremor", "paroxysmal_sweats", "anxiety",
            "agitation", "tactile_disturbances", "auditory_disturbances",
            "visual_disturbances", "headache",
        ]
        for field in fields_7:
            val = min(remaining, 7)
            items[field] = val
            remaining -= val
            if remaining <= 0:
                break
        # Handle orientation (max 4)
        if remaining > 0:
            items["orientation"] = min(remaining, 4)
        params = _make_params(**items)
        result = calculate_ciwa_ar(params)
        assert result.value == total
        assert f"CIWA-Ar score is {total}/67" in result.interpretation


def test_ciwa_ar_minimal_no_medication():
    """Score 0-8: interpretation says pharmacologic treatment not needed."""
    result = calculate_ciwa_ar(_make_params(tremor=3))
    assert result.value == 3
    assert "Pharmacologic treatment is generally not needed" in result.interpretation


def test_ciwa_ar_mild_moderate_recommends_benzodiazepine():
    """Score 9-15: interpretation mentions symptom-triggered benzodiazepine."""
    result = calculate_ciwa_ar(_make_params(
        nausea_vomiting=3, tremor=3, anxiety=3
    ))
    assert result.value == 9
    assert "symptom-triggered benzodiazepine" in result.interpretation


def test_ciwa_ar_moderate_severe_treatment_indicated():
    """Score 16-20: interpretation says benzodiazepine treatment indicated."""
    result = calculate_ciwa_ar(_make_params(
        nausea_vomiting=4, tremor=4, anxiety=4, agitation=4
    ))
    assert result.value == 16
    assert "Benzodiazepine treatment is indicated" in result.interpretation


def test_ciwa_ar_severe_icu_care():
    """Score >20: interpretation mentions ICU-level care."""
    result = calculate_ciwa_ar(_make_params(
        nausea_vomiting=7, tremor=7, anxiety=7, agitation=1
    ))
    assert result.value == 22
    assert "ICU-level care" in result.interpretation
    assert "delirium tremens" in result.interpretation


# ---------------------------------------------------------------------------
# Evidence and FHIR metadata tests
# ---------------------------------------------------------------------------


def test_ciwa_ar_evidence_doi():
    """Verify DOI matches Sullivan et al. 1989."""
    result = calculate_ciwa_ar(_make_params())
    assert result.evidence.source_doi == "10.1111/j.1360-0443.1989.tb00737.x"


def test_ciwa_ar_evidence_level():
    """Verify evidence level is Derivation & Validation Study."""
    result = calculate_ciwa_ar(_make_params())
    assert result.evidence.level == "Derivation & Validation Study"


def test_ciwa_ar_evidence_description():
    """Verify evidence description references Sullivan and CIWA-Ar."""
    result = calculate_ciwa_ar(_make_params())
    assert "Sullivan" in result.evidence.description
    assert "CIWA-Ar" in result.evidence.description


def test_ciwa_ar_fhir_code():
    """Verify FHIR code is None (no CIWA-Ar-specific LOINC code exists)."""
    result = calculate_ciwa_ar(_make_params())
    assert result.fhir_code is None
    assert result.fhir_system is None
    assert "CIWA-Ar" in result.fhir_display


# ---------------------------------------------------------------------------
# Pydantic model validation tests
# ---------------------------------------------------------------------------


def test_ciwa_ar_all_fields_required():
    """All 10 items are required (no defaults)."""
    with pytest.raises(Exception):
        CIWAArParams()


def test_ciwa_ar_missing_one_field():
    """Missing a single field should raise validation error."""
    with pytest.raises(Exception):
        CIWAArParams(
            nausea_vomiting=0, tremor=0, paroxysmal_sweats=0, anxiety=0,
            agitation=0, tactile_disturbances=0, auditory_disturbances=0,
            visual_disturbances=0, headache=0,
            # orientation is missing
        )


def test_ciwa_ar_negative_value_rejected():
    """Negative score values should be rejected by Pydantic validation."""
    with pytest.raises(Exception):
        CIWAArParams(
            nausea_vomiting=-1, tremor=0, paroxysmal_sweats=0, anxiety=0,
            agitation=0, tactile_disturbances=0, auditory_disturbances=0,
            visual_disturbances=0, headache=0, orientation=0,
        )


def test_ciwa_ar_exceeding_max_rejected():
    """Values exceeding item max (8 for 0-7 items) should be rejected."""
    with pytest.raises(Exception):
        CIWAArParams(
            nausea_vomiting=8, tremor=0, paroxysmal_sweats=0, anxiety=0,
            agitation=0, tactile_disturbances=0, auditory_disturbances=0,
            visual_disturbances=0, headache=0, orientation=0,
        )


# ---------------------------------------------------------------------------
# Clinical scenario cross-validation tests (from MDCalc / reference sources)
# ---------------------------------------------------------------------------


def test_ciwa_ar_clinical_scenario_no_withdrawal():
    """Patient with no withdrawal symptoms: all zeros, score 0."""
    result = calculate_ciwa_ar(CIWAArParams(
        nausea_vomiting=0, tremor=0, paroxysmal_sweats=0, anxiety=0,
        agitation=0, tactile_disturbances=0, auditory_disturbances=0,
        visual_disturbances=0, headache=0, orientation=0,
    ))
    assert result.value == 0
    assert "Absent or minimal withdrawal" in result.interpretation


def test_ciwa_ar_clinical_scenario_mild_withdrawal():
    """Patient with mild withdrawal: mild nausea, slight tremor, mild anxiety.
    Score = 2 + 1 + 2 + 1 + 1 + 0 + 0 + 0 + 1 + 0 = 8."""
    result = calculate_ciwa_ar(CIWAArParams(
        nausea_vomiting=2, tremor=1, paroxysmal_sweats=2, anxiety=1,
        agitation=1, tactile_disturbances=0, auditory_disturbances=0,
        visual_disturbances=0, headache=1, orientation=0,
    ))
    assert result.value == 8
    assert "Absent or minimal withdrawal" in result.interpretation


def test_ciwa_ar_clinical_scenario_moderate_withdrawal():
    """Patient with moderate withdrawal: significant symptoms across
    multiple domains. Score = 4 + 3 + 2 + 3 + 2 + 0 + 0 + 0 + 2 + 0 = 16."""
    result = calculate_ciwa_ar(CIWAArParams(
        nausea_vomiting=4, tremor=3, paroxysmal_sweats=2, anxiety=3,
        agitation=2, tactile_disturbances=0, auditory_disturbances=0,
        visual_disturbances=0, headache=2, orientation=0,
    ))
    assert result.value == 16
    assert "Moderate to severe withdrawal" in result.interpretation


def test_ciwa_ar_clinical_scenario_severe_withdrawal_with_hallucinations():
    """Patient with severe withdrawal including hallucinations and
    disorientation. Score = 6 + 6 + 5 + 5 + 4 + 5 + 4 + 4 + 3 + 3 = 45."""
    result = calculate_ciwa_ar(CIWAArParams(
        nausea_vomiting=6, tremor=6, paroxysmal_sweats=5, anxiety=5,
        agitation=4, tactile_disturbances=5, auditory_disturbances=4,
        visual_disturbances=4, headache=3, orientation=3,
    ))
    assert result.value == 45
    assert "Severe withdrawal" in result.interpretation
    assert "ICU-level care" in result.interpretation


def test_ciwa_ar_clinical_scenario_impending_dt():
    """Patient presenting with impending delirium tremens: nearly maximum
    scores across all items. Score = 7 + 7 + 7 + 7 + 7 + 7 + 6 + 6 + 6 + 4 = 64."""
    result = calculate_ciwa_ar(CIWAArParams(
        nausea_vomiting=7, tremor=7, paroxysmal_sweats=7, anxiety=7,
        agitation=7, tactile_disturbances=7, auditory_disturbances=6,
        visual_disturbances=6, headache=6, orientation=4,
    ))
    assert result.value == 64
    assert "Severe withdrawal" in result.interpretation
    assert "delirium tremens" in result.interpretation


def test_ciwa_ar_clinical_scenario_borderline_mild_to_moderate():
    """Score exactly at 9: boundary between minimal and mild/moderate.
    Score = 3 + 3 + 3 + 0 + 0 + 0 + 0 + 0 + 0 + 0 = 9."""
    result = calculate_ciwa_ar(CIWAArParams(
        nausea_vomiting=3, tremor=3, paroxysmal_sweats=3, anxiety=0,
        agitation=0, tactile_disturbances=0, auditory_disturbances=0,
        visual_disturbances=0, headache=0, orientation=0,
    ))
    assert result.value == 9
    assert "Mild to moderate withdrawal" in result.interpretation


# ---------------------------------------------------------------------------
# Property-based fuzz test (Tier 2)
# ---------------------------------------------------------------------------


@given(
    st.builds(
        CIWAArParams,
        nausea_vomiting=st.integers(min_value=0, max_value=7),
        tremor=st.integers(min_value=0, max_value=7),
        paroxysmal_sweats=st.integers(min_value=0, max_value=7),
        anxiety=st.integers(min_value=0, max_value=7),
        agitation=st.integers(min_value=0, max_value=7),
        tactile_disturbances=st.integers(min_value=0, max_value=7),
        auditory_disturbances=st.integers(min_value=0, max_value=7),
        visual_disturbances=st.integers(min_value=0, max_value=7),
        headache=st.integers(min_value=0, max_value=7),
        orientation=st.integers(min_value=0, max_value=4),
    )
)
@settings(max_examples=500)
def test_ciwa_ar_fuzz_valid_range(params):
    """Output is always within expected bounds for any valid input combination."""
    result = calculate_ciwa_ar(params)
    assert result.value is not None
    assert isinstance(result.value, int)
    # Minimum: 0, Maximum: 9*7 + 4 = 67
    assert 0 <= result.value <= 67
    assert result.interpretation
    assert "CIWA-Ar score is" in result.interpretation
    assert result.evidence.source_doi == "10.1111/j.1360-0443.1989.tb00737.x"


@given(
    st.builds(
        CIWAArParams,
        nausea_vomiting=st.integers(min_value=0, max_value=7),
        tremor=st.integers(min_value=0, max_value=7),
        paroxysmal_sweats=st.integers(min_value=0, max_value=7),
        anxiety=st.integers(min_value=0, max_value=7),
        agitation=st.integers(min_value=0, max_value=7),
        tactile_disturbances=st.integers(min_value=0, max_value=7),
        auditory_disturbances=st.integers(min_value=0, max_value=7),
        visual_disturbances=st.integers(min_value=0, max_value=7),
        headache=st.integers(min_value=0, max_value=7),
        orientation=st.integers(min_value=0, max_value=4),
    )
)
@settings(max_examples=500)
def test_ciwa_ar_fuzz_severity_strata_consistent(params):
    """Severity strata are mutually exclusive and exhaustive for any valid input."""
    result = calculate_ciwa_ar(params)
    interp = result.interpretation
    score = result.value

    # Exactly one severity stratum should be mentioned
    strata = [
        "Absent or minimal withdrawal",
        "Mild to moderate withdrawal",
        "Moderate to severe withdrawal",
        "Severe withdrawal",
    ]
    matched = [s for s in strata if s in interp]
    assert len(matched) >= 1, f"No stratum found in interpretation for score {score}"

    # Verify correct stratum assignment
    if score <= 8:
        assert "Absent or minimal withdrawal" in interp
    elif score <= 15:
        assert "Mild to moderate withdrawal" in interp
    elif score <= 20:
        assert "Moderate to severe withdrawal" in interp
    else:
        assert "Severe withdrawal" in interp


# ---------------------------------------------------------------------------
# Verify CIWA-Ar is registered in the calculator registry
# ---------------------------------------------------------------------------


def test_ciwa_ar_registered():
    """Verify calculate_ciwa_ar is registered in the CALCULATOR_REGISTRY."""
    from open_medicine.mcp.registry import CALCULATOR_REGISTRY
    assert "calculate_ciwa_ar" in CALCULATOR_REGISTRY
    tool = CALCULATOR_REGISTRY["calculate_ciwa_ar"]
    assert tool.pydantic_model is CIWAArParams
    assert tool.execute_function is calculate_ciwa_ar


def test_ciwa_ar_registry_description():
    """Verify registry description mentions CIWA-Ar and alcohol withdrawal."""
    from open_medicine.mcp.registry import CALCULATOR_REGISTRY
    desc = CALCULATOR_REGISTRY["calculate_ciwa_ar"].description
    assert "CIWA-Ar" in desc
    assert "alcohol withdrawal" in desc.lower()

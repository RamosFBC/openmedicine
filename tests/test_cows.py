import pytest
from hypothesis import given, strategies as st, settings
from open_medicine.mcp.calculators.cows import calculate_cows, COWSParams


# ---------------------------------------------------------------------------
# Tier 1: Deterministic Unit Tests
# ---------------------------------------------------------------------------

def test_cows_minimum_score():
    """Test lowest possible score: all criteria absent/normal -> 0 (no withdrawal)."""
    params = COWSParams(
        resting_pulse_rate=0,
        sweating=0,
        restlessness=0,
        pupil_size=0,
        bone_or_joint_aches=0,
        runny_nose_or_tearing=0,
        gi_upset=0,
        tremor=0,
        yawning=0,
        anxiety_or_irritability=0,
        gooseflesh_skin=0,
    )
    result = calculate_cows(params)
    assert result.value == 0
    assert "No active withdrawal" in result.interpretation
    assert "COWS total score is 0" in result.interpretation


def test_cows_maximum_score():
    """Test highest possible score: all criteria at maximum -> 48 (severe withdrawal)."""
    params = COWSParams(
        resting_pulse_rate=4,
        sweating=4,
        restlessness=5,
        pupil_size=5,
        bone_or_joint_aches=4,
        runny_nose_or_tearing=4,
        gi_upset=5,
        tremor=4,
        yawning=4,
        anxiety_or_irritability=4,
        gooseflesh_skin=5,
    )
    result = calculate_cows(params)
    assert result.value == 48
    assert "Severe withdrawal" in result.interpretation
    assert "COWS total score is 48" in result.interpretation


def test_cows_no_active_withdrawal_threshold():
    """Test score of 4 -> no active withdrawal (just below mild threshold)."""
    params = COWSParams(
        resting_pulse_rate=1,
        sweating=1,
        restlessness=1,
        pupil_size=1,
        bone_or_joint_aches=0,
        runny_nose_or_tearing=0,
        gi_upset=0,
        tremor=0,
        yawning=0,
        anxiety_or_irritability=0,
        gooseflesh_skin=0,
    )
    result = calculate_cows(params)
    assert result.value == 4
    assert "No active withdrawal" in result.interpretation


def test_cows_mild_lower_boundary():
    """Test score of 5 -> mild withdrawal (lower boundary)."""
    params = COWSParams(
        resting_pulse_rate=1,
        sweating=1,
        restlessness=1,
        pupil_size=1,
        bone_or_joint_aches=1,
        runny_nose_or_tearing=0,
        gi_upset=0,
        tremor=0,
        yawning=0,
        anxiety_or_irritability=0,
        gooseflesh_skin=0,
    )
    result = calculate_cows(params)
    assert result.value == 5
    assert "Mild withdrawal" in result.interpretation


def test_cows_mild_upper_boundary():
    """Test score of 12 -> mild withdrawal (upper boundary)."""
    params = COWSParams(
        resting_pulse_rate=2,
        sweating=2,
        restlessness=1,
        pupil_size=2,
        bone_or_joint_aches=1,
        runny_nose_or_tearing=1,
        gi_upset=1,
        tremor=1,
        yawning=1,
        anxiety_or_irritability=0,
        gooseflesh_skin=0,
    )
    result = calculate_cows(params)
    assert result.value == 12
    assert "Mild withdrawal" in result.interpretation


def test_cows_moderate_lower_boundary():
    """Test score of 13 -> moderate withdrawal (lower boundary)."""
    params = COWSParams(
        resting_pulse_rate=2,
        sweating=2,
        restlessness=1,
        pupil_size=2,
        bone_or_joint_aches=1,
        runny_nose_or_tearing=1,
        gi_upset=2,
        tremor=1,
        yawning=1,
        anxiety_or_irritability=0,
        gooseflesh_skin=0,
    )
    result = calculate_cows(params)
    assert result.value == 13
    assert "Moderate withdrawal" in result.interpretation


def test_cows_moderate_upper_boundary():
    """Test score of 24 -> moderate withdrawal (upper boundary)."""
    params = COWSParams(
        resting_pulse_rate=4,
        sweating=3,
        restlessness=3,
        pupil_size=2,
        bone_or_joint_aches=2,
        runny_nose_or_tearing=2,
        gi_upset=2,
        tremor=2,
        yawning=2,
        anxiety_or_irritability=2,
        gooseflesh_skin=0,
    )
    result = calculate_cows(params)
    assert result.value == 24
    assert "Moderate withdrawal" in result.interpretation


def test_cows_moderately_severe_lower_boundary():
    """Test score of 25 -> moderately severe withdrawal (lower boundary)."""
    params = COWSParams(
        resting_pulse_rate=4,
        sweating=3,
        restlessness=3,
        pupil_size=2,
        bone_or_joint_aches=2,
        runny_nose_or_tearing=2,
        gi_upset=3,
        tremor=2,
        yawning=2,
        anxiety_or_irritability=2,
        gooseflesh_skin=0,
    )
    result = calculate_cows(params)
    assert result.value == 25
    assert "Moderately severe withdrawal" in result.interpretation


def test_cows_moderately_severe_upper_boundary():
    """Test score of 36 -> moderately severe withdrawal (upper boundary)."""
    params = COWSParams(
        resting_pulse_rate=4,
        sweating=4,
        restlessness=5,
        pupil_size=5,
        bone_or_joint_aches=4,
        runny_nose_or_tearing=4,
        gi_upset=3,
        tremor=2,
        yawning=2,
        anxiety_or_irritability=0,
        gooseflesh_skin=3,
    )
    result = calculate_cows(params)
    assert result.value == 36
    assert "Moderately severe withdrawal" in result.interpretation


def test_cows_severe_lower_boundary():
    """Test score of 37 -> severe withdrawal (lower boundary)."""
    params = COWSParams(
        resting_pulse_rate=4,
        sweating=4,
        restlessness=5,
        pupil_size=5,
        bone_or_joint_aches=4,
        runny_nose_or_tearing=4,
        gi_upset=3,
        tremor=2,
        yawning=2,
        anxiety_or_irritability=1,
        gooseflesh_skin=3,
    )
    result = calculate_cows(params)
    assert result.value == 37
    assert "Severe withdrawal" in result.interpretation


def test_cows_evidence_doi():
    """Verify the DOI matches the original Wesson & Ling 2003 paper."""
    params = COWSParams(
        resting_pulse_rate=0,
        sweating=0,
        restlessness=0,
        pupil_size=0,
        bone_or_joint_aches=0,
        runny_nose_or_tearing=0,
        gi_upset=0,
        tremor=0,
        yawning=0,
        anxiety_or_irritability=0,
        gooseflesh_skin=0,
    )
    result = calculate_cows(params)
    assert result.evidence.source_doi == "10.1080/02791072.2003.10400007"
    assert "Wesson" in result.evidence.description
    assert "2003" in result.evidence.description


def test_cows_fhir_code():
    """Verify FHIR metadata is correctly populated."""
    params = COWSParams(
        resting_pulse_rate=0,
        sweating=0,
        restlessness=0,
        pupil_size=0,
        bone_or_joint_aches=0,
        runny_nose_or_tearing=0,
        gi_upset=0,
        tremor=0,
        yawning=0,
        anxiety_or_irritability=0,
        gooseflesh_skin=0,
    )
    result = calculate_cows(params)
    assert result.fhir_code is None
    assert result.fhir_system is None
    assert result.fhir_display == "Clinical Opiate Withdrawal Scale total score"


def test_cows_interpretation_contains_score_and_classification():
    """Verify interpretation always includes numeric score and classification."""
    params = COWSParams(
        resting_pulse_rate=2,
        sweating=1,
        restlessness=1,
        pupil_size=1,
        bone_or_joint_aches=1,
        runny_nose_or_tearing=1,
        gi_upset=1,
        tremor=1,
        yawning=1,
        anxiety_or_irritability=1,
        gooseflesh_skin=0,
    )
    result = calculate_cows(params)
    assert result.value == 11
    assert "COWS total score is 11" in result.interpretation
    assert "Classification:" in result.interpretation
    assert "Mild withdrawal" in result.interpretation


def test_cows_typical_buprenorphine_induction_case():
    """Test a typical clinical scenario for buprenorphine induction (score ~13-24)."""
    params = COWSParams(
        resting_pulse_rate=2,     # Pulse 101-120
        sweating=2,               # Flushed/observable moistness
        restlessness=3,           # Frequent shifting
        pupil_size=2,             # Moderately dilated
        bone_or_joint_aches=2,    # Severe diffuse aching
        runny_nose_or_tearing=2,  # Nose running/tearing
        gi_upset=2,               # Nausea or loose stool
        tremor=2,                 # Slight tremor
        yawning=2,                # 3+ times
        anxiety_or_irritability=2,# Obviously irritable
        gooseflesh_skin=0,        # Smooth skin
    )
    result = calculate_cows(params)
    assert result.value == 21
    assert "Moderate withdrawal" in result.interpretation
    assert "Buprenorphine induction is generally appropriate" in result.interpretation


def test_cows_single_item_contribution():
    """Test that each individual item contributes correctly to total."""
    # Start with all zeros
    base = dict(
        resting_pulse_rate=0,
        sweating=0,
        restlessness=0,
        pupil_size=0,
        bone_or_joint_aches=0,
        runny_nose_or_tearing=0,
        gi_upset=0,
        tremor=0,
        yawning=0,
        anxiety_or_irritability=0,
        gooseflesh_skin=0,
    )

    # Test each item individually with value of 1
    items_with_1 = [
        "resting_pulse_rate", "sweating", "restlessness", "pupil_size",
        "bone_or_joint_aches", "runny_nose_or_tearing", "gi_upset",
        "tremor", "yawning", "anxiety_or_irritability",
    ]
    for item in items_with_1:
        test_params = dict(base)
        test_params[item] = 1
        result = calculate_cows(COWSParams(**test_params))
        assert result.value == 1, f"Expected 1 when only {item}=1, got {result.value}"

    # Gooseflesh has minimum non-zero of 3
    test_params = dict(base)
    test_params["gooseflesh_skin"] = 3
    result = calculate_cows(COWSParams(**test_params))
    assert result.value == 3


# ---------------------------------------------------------------------------
# Tier 2: Property-Based Fuzz Tests
# ---------------------------------------------------------------------------

# Valid score values for each COWS item (non-contiguous scales)
VALID_PULSE = [0, 1, 2, 4]
VALID_SWEATING = [0, 1, 2, 3, 4]
VALID_RESTLESSNESS = [0, 1, 3, 5]
VALID_PUPIL = [0, 1, 2, 5]
VALID_BONE_ACHES = [0, 1, 2, 4]
VALID_RUNNY_NOSE = [0, 1, 2, 4]
VALID_GI = [0, 1, 2, 3, 5]
VALID_TREMOR = [0, 1, 2, 4]
VALID_YAWNING = [0, 1, 2, 4]
VALID_ANXIETY = [0, 1, 2, 4]
VALID_GOOSEFLESH = [0, 3, 5]


@pytest.mark.slow
@given(
    resting_pulse_rate=st.sampled_from(VALID_PULSE),
    sweating=st.sampled_from(VALID_SWEATING),
    restlessness=st.sampled_from(VALID_RESTLESSNESS),
    pupil_size=st.sampled_from(VALID_PUPIL),
    bone_or_joint_aches=st.sampled_from(VALID_BONE_ACHES),
    runny_nose_or_tearing=st.sampled_from(VALID_RUNNY_NOSE),
    gi_upset=st.sampled_from(VALID_GI),
    tremor=st.sampled_from(VALID_TREMOR),
    yawning=st.sampled_from(VALID_YAWNING),
    anxiety_or_irritability=st.sampled_from(VALID_ANXIETY),
    gooseflesh_skin=st.sampled_from(VALID_GOOSEFLESH),
)
@settings(max_examples=500)
def test_cows_fuzz_valid_scores(
    resting_pulse_rate,
    sweating,
    restlessness,
    pupil_size,
    bone_or_joint_aches,
    runny_nose_or_tearing,
    gi_upset,
    tremor,
    yawning,
    anxiety_or_irritability,
    gooseflesh_skin,
):
    """Property test: COWS score is always 0-48 for any valid input combination."""
    params = COWSParams(
        resting_pulse_rate=resting_pulse_rate,
        sweating=sweating,
        restlessness=restlessness,
        pupil_size=pupil_size,
        bone_or_joint_aches=bone_or_joint_aches,
        runny_nose_or_tearing=runny_nose_or_tearing,
        gi_upset=gi_upset,
        tremor=tremor,
        yawning=yawning,
        anxiety_or_irritability=anxiety_or_irritability,
        gooseflesh_skin=gooseflesh_skin,
    )
    result = calculate_cows(params)
    assert result.value is not None
    assert isinstance(result.value, int)
    assert 0 <= result.value <= 48
    assert result.interpretation
    assert "COWS total score is" in result.interpretation
    assert "Classification:" in result.interpretation
    assert result.evidence.source_doi == "10.1080/02791072.2003.10400007"


@pytest.mark.slow
@given(
    resting_pulse_rate=st.integers(min_value=0, max_value=4),
    sweating=st.integers(min_value=0, max_value=4),
    restlessness=st.integers(min_value=0, max_value=5),
    pupil_size=st.integers(min_value=0, max_value=5),
    bone_or_joint_aches=st.integers(min_value=0, max_value=4),
    runny_nose_or_tearing=st.integers(min_value=0, max_value=4),
    gi_upset=st.integers(min_value=0, max_value=5),
    tremor=st.integers(min_value=0, max_value=4),
    yawning=st.integers(min_value=0, max_value=4),
    anxiety_or_irritability=st.integers(min_value=0, max_value=4),
    gooseflesh_skin=st.integers(min_value=0, max_value=5),
)
@settings(max_examples=500)
def test_cows_fuzz_full_range(
    resting_pulse_rate,
    sweating,
    restlessness,
    pupil_size,
    bone_or_joint_aches,
    runny_nose_or_tearing,
    gi_upset,
    tremor,
    yawning,
    anxiety_or_irritability,
    gooseflesh_skin,
):
    """Property test using full integer ranges (including non-standard values).

    The COWS form has non-contiguous scores (e.g., restlessness is 0,1,3,5),
    but pydantic allows any integer within ge/le bounds. The calculator should
    still return a valid score without crashing.
    """
    params = COWSParams(
        resting_pulse_rate=resting_pulse_rate,
        sweating=sweating,
        restlessness=restlessness,
        pupil_size=pupil_size,
        bone_or_joint_aches=bone_or_joint_aches,
        runny_nose_or_tearing=runny_nose_or_tearing,
        gi_upset=gi_upset,
        tremor=tremor,
        yawning=yawning,
        anxiety_or_irritability=anxiety_or_irritability,
        gooseflesh_skin=gooseflesh_skin,
    )
    result = calculate_cows(params)
    assert result.value is not None
    assert isinstance(result.value, int)
    # With full integer ranges, max could exceed 48 slightly (e.g., pulse 3 instead of gap to 4)
    # but still bounded by sum of maxima
    assert 0 <= result.value <= 50
    assert result.interpretation
    assert result.evidence.source_doi

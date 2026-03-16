import pytest
from hypothesis import given, strategies as st, settings
from open_medicine.mcp.calculators.tbsa import calculate_tbsa, TBSAParams


# ============================================================
# Tier 1: Deterministic Unit Tests
# ============================================================


def test_tbsa_no_burns():
    """Test 0% TBSA when no body regions are burned."""
    params = TBSAParams()
    result = calculate_tbsa(params)
    assert result.value == 0.0
    assert "0%" in result.interpretation
    assert "No burn areas selected" in result.interpretation


def test_tbsa_maximum():
    """Test 100% TBSA when all body regions are burned."""
    params = TBSAParams(
        head_and_neck=True,
        anterior_trunk=True,
        posterior_trunk=True,
        left_upper_extremity=True,
        right_upper_extremity=True,
        left_lower_extremity=True,
        right_lower_extremity=True,
        perineum=True,
    )
    result = calculate_tbsa(params)
    # 9 + 18 + 18 + 9 + 9 + 18 + 18 + 1 = 100
    assert result.value == 100.0
    assert "100.0%" in result.interpretation
    assert "Major burn" in result.interpretation


def test_tbsa_head_only():
    """Test head and neck only = 9% TBSA (minor burn)."""
    params = TBSAParams(head_and_neck=True)
    result = calculate_tbsa(params)
    assert result.value == 9.0
    assert "9.0%" in result.interpretation
    assert "Minor burn" in result.interpretation


def test_tbsa_anterior_trunk_only():
    """Test anterior trunk only = 18% TBSA (moderate burn)."""
    params = TBSAParams(anterior_trunk=True)
    result = calculate_tbsa(params)
    assert result.value == 18.0
    assert "18.0%" in result.interpretation
    assert "Moderate burn" in result.interpretation


def test_tbsa_posterior_trunk_only():
    """Test posterior trunk only = 18% TBSA (moderate burn)."""
    params = TBSAParams(posterior_trunk=True)
    result = calculate_tbsa(params)
    assert result.value == 18.0
    assert "18.0%" in result.interpretation
    assert "Moderate burn" in result.interpretation


def test_tbsa_left_upper_extremity():
    """Test left upper extremity only = 9% TBSA (minor burn)."""
    params = TBSAParams(left_upper_extremity=True)
    result = calculate_tbsa(params)
    assert result.value == 9.0
    assert "9.0%" in result.interpretation
    assert "Minor burn" in result.interpretation


def test_tbsa_right_upper_extremity():
    """Test right upper extremity only = 9% TBSA."""
    params = TBSAParams(right_upper_extremity=True)
    result = calculate_tbsa(params)
    assert result.value == 9.0


def test_tbsa_left_lower_extremity():
    """Test left lower extremity only = 18% TBSA (moderate burn)."""
    params = TBSAParams(left_lower_extremity=True)
    result = calculate_tbsa(params)
    assert result.value == 18.0
    assert "18.0%" in result.interpretation
    assert "Moderate burn" in result.interpretation


def test_tbsa_right_lower_extremity():
    """Test right lower extremity only = 18% TBSA."""
    params = TBSAParams(right_lower_extremity=True)
    result = calculate_tbsa(params)
    assert result.value == 18.0


def test_tbsa_perineum_only():
    """Test perineum only = 1% TBSA (minor burn)."""
    params = TBSAParams(perineum=True)
    result = calculate_tbsa(params)
    assert result.value == 1.0
    assert "1.0%" in result.interpretation
    assert "Minor burn" in result.interpretation


def test_tbsa_both_upper_extremities():
    """Test both upper extremities = 18% TBSA (moderate burn)."""
    params = TBSAParams(left_upper_extremity=True, right_upper_extremity=True)
    result = calculate_tbsa(params)
    assert result.value == 18.0
    assert "Moderate burn" in result.interpretation


def test_tbsa_both_lower_extremities():
    """Test both lower extremities = 36% TBSA (major burn)."""
    params = TBSAParams(left_lower_extremity=True, right_lower_extremity=True)
    result = calculate_tbsa(params)
    assert result.value == 36.0
    assert "Major burn" in result.interpretation


def test_tbsa_full_trunk():
    """Test anterior + posterior trunk = 36% TBSA (major burn)."""
    params = TBSAParams(anterior_trunk=True, posterior_trunk=True)
    result = calculate_tbsa(params)
    assert result.value == 36.0
    assert "Major burn" in result.interpretation


def test_tbsa_minor_threshold_9():
    """Test 9% TBSA is classified as minor burn (<10%)."""
    params = TBSAParams(head_and_neck=True)
    result = calculate_tbsa(params)
    assert result.value == 9.0
    assert "Minor burn" in result.interpretation


def test_tbsa_moderate_threshold_10():
    """Test 10% TBSA boundary: head + perineum = 10% -> moderate burn."""
    params = TBSAParams(head_and_neck=True, perineum=True)
    result = calculate_tbsa(params)
    assert result.value == 10.0
    assert "Moderate burn" in result.interpretation


def test_tbsa_moderate_threshold_20():
    """Test 20% TBSA is still moderate (<= 20%)."""
    # Head (9) + left upper extremity (9) + perineum (1) = 19
    # Anterior trunk (18) + perineum (1) = 19
    # Need exactly 20: left upper (9) + right upper (9) + perineum (1) = 19 -- not 20
    # anterior trunk (18) + perineum (1) + head_and_neck would be 28
    # Actually: two upper extremities (18) + perineum (1) = 19; can't get exactly 20
    # Head (9) + left upper (9) + perineum (1) = 19;
    # Anterior trunk (18) alone = 18; anterior_trunk + perineum = 19
    # The possible values are limited by discrete regions. Closest to 20 is 19.
    # However, 18 is moderate and next is 27, so the 20% boundary can't be
    # exactly hit. Let's test at anterior_trunk = 18 (moderate)
    params = TBSAParams(anterior_trunk=True)
    result = calculate_tbsa(params)
    assert result.value == 18.0
    assert "Moderate burn" in result.interpretation


def test_tbsa_major_threshold_above_20():
    """Test >20% TBSA is classified as major burn: head(9) + both arms(18) = 27%."""
    params = TBSAParams(
        head_and_neck=True,
        left_upper_extremity=True,
        right_upper_extremity=True,
    )
    result = calculate_tbsa(params)
    assert result.value == 27.0
    assert "Major burn" in result.interpretation


def test_tbsa_classical_example_anterior_trunk_and_arm():
    """Clinical scenario: anterior trunk (18%) + right arm (9%) = 27% major burn."""
    params = TBSAParams(anterior_trunk=True, right_upper_extremity=True)
    result = calculate_tbsa(params)
    assert result.value == 27.0
    assert "Major burn" in result.interpretation
    assert "burn center transfer" in result.interpretation.lower()


def test_tbsa_evidence_doi():
    """Verify the DOI references the original Wallace 1951 paper."""
    params = TBSAParams(head_and_neck=True)
    result = calculate_tbsa(params)
    assert result.evidence.source_doi == "10.1016/S0140-6736(51)91975-7"
    assert "Wallace" in result.evidence.description
    assert "1951" in result.evidence.description


def test_tbsa_fhir_code():
    """Verify FHIR code and system are set correctly."""
    params = TBSAParams(head_and_neck=True)
    result = calculate_tbsa(params)
    assert result.fhir_code == "8277-6"
    assert result.fhir_system == "http://loinc.org"
    assert result.fhir_display == "Body surface area"


def test_tbsa_interpretation_never_empty():
    """Ensure interpretation is always populated regardless of input."""
    for region in [
        "head_and_neck",
        "anterior_trunk",
        "posterior_trunk",
        "left_upper_extremity",
        "right_upper_extremity",
        "left_lower_extremity",
        "right_lower_extremity",
        "perineum",
    ]:
        params = TBSAParams(**{region: True})
        result = calculate_tbsa(params)
        assert result.interpretation is not None
        assert len(result.interpretation) > 0


def test_tbsa_region_sum_is_100():
    """Verify that all 8 regions sum exactly to 100% TBSA per Rule of Nines."""
    params = TBSAParams(
        head_and_neck=True,
        anterior_trunk=True,
        posterior_trunk=True,
        left_upper_extremity=True,
        right_upper_extremity=True,
        left_lower_extremity=True,
        right_lower_extremity=True,
        perineum=True,
    )
    result = calculate_tbsa(params)
    assert result.value == 100.0


def test_tbsa_parkland_reference_in_moderate():
    """Verify Parkland formula reference appears for moderate burns."""
    params = TBSAParams(anterior_trunk=True)  # 18%
    result = calculate_tbsa(params)
    assert "Parkland" in result.interpretation


def test_tbsa_parkland_reference_in_major():
    """Verify Parkland formula reference appears for major burns."""
    params = TBSAParams(anterior_trunk=True, posterior_trunk=True)  # 36%
    result = calculate_tbsa(params)
    assert "Parkland" in result.interpretation


def test_tbsa_value_type():
    """Verify value is always a float."""
    params = TBSAParams(head_and_neck=True)
    result = calculate_tbsa(params)
    assert isinstance(result.value, float)


# ============================================================
# Tier 2: Property-Based Fuzz Tests
# ============================================================


@pytest.mark.slow
@given(
    head_and_neck=st.booleans(),
    anterior_trunk=st.booleans(),
    posterior_trunk=st.booleans(),
    left_upper_extremity=st.booleans(),
    right_upper_extremity=st.booleans(),
    left_lower_extremity=st.booleans(),
    right_lower_extremity=st.booleans(),
    perineum=st.booleans(),
)
@settings(max_examples=500)
def test_tbsa_fuzz_valid_range(
    head_and_neck,
    anterior_trunk,
    posterior_trunk,
    left_upper_extremity,
    right_upper_extremity,
    left_lower_extremity,
    right_lower_extremity,
    perineum,
):
    """Output is always within 0-100% for any valid boolean combination."""
    params = TBSAParams(
        head_and_neck=head_and_neck,
        anterior_trunk=anterior_trunk,
        posterior_trunk=posterior_trunk,
        left_upper_extremity=left_upper_extremity,
        right_upper_extremity=right_upper_extremity,
        left_lower_extremity=left_lower_extremity,
        right_lower_extremity=right_lower_extremity,
        perineum=perineum,
    )
    result = calculate_tbsa(params)
    assert result.value is not None
    assert isinstance(result.value, float)
    assert 0.0 <= result.value <= 100.0
    assert result.interpretation is not None
    assert len(result.interpretation) > 0
    assert result.evidence.source_doi == "10.1016/S0140-6736(51)91975-7"


@pytest.mark.slow
@given(
    head_and_neck=st.booleans(),
    anterior_trunk=st.booleans(),
    posterior_trunk=st.booleans(),
    left_upper_extremity=st.booleans(),
    right_upper_extremity=st.booleans(),
    left_lower_extremity=st.booleans(),
    right_lower_extremity=st.booleans(),
    perineum=st.booleans(),
)
@settings(max_examples=500)
def test_tbsa_fuzz_severity_classification(
    head_and_neck,
    anterior_trunk,
    posterior_trunk,
    left_upper_extremity,
    right_upper_extremity,
    left_lower_extremity,
    right_lower_extremity,
    perineum,
):
    """Severity classification is consistent with TBSA value for all inputs."""
    params = TBSAParams(
        head_and_neck=head_and_neck,
        anterior_trunk=anterior_trunk,
        posterior_trunk=posterior_trunk,
        left_upper_extremity=left_upper_extremity,
        right_upper_extremity=right_upper_extremity,
        left_lower_extremity=left_lower_extremity,
        right_lower_extremity=right_lower_extremity,
        perineum=perineum,
    )
    result = calculate_tbsa(params)
    tbsa = result.value

    if tbsa == 0.0:
        assert "No burn areas selected" in result.interpretation
    elif tbsa < 10.0:
        assert "Minor burn" in result.interpretation
    elif tbsa <= 20.0:
        assert "Moderate burn" in result.interpretation
    else:
        assert "Major burn" in result.interpretation

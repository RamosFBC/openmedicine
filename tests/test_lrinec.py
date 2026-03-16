import pytest
from hypothesis import given, strategies as st, settings
from open_medicine.mcp.calculators.lrinec import calculate_lrinec, LRINECParams


# ---------------------------------------------------------------------------
# Tier 1: Deterministic Unit Tests
# ---------------------------------------------------------------------------

def test_lrinec_minimum_score():
    """All labs normal: CRP <150, WBC <15, Hgb >13.5, Na >=135, Cr <=1.6, Glc <=180 -> score 0."""
    params = LRINECParams(
        crp=10.0,
        wbc=8.0,
        hemoglobin=15.0,
        sodium=140.0,
        creatinine=0.9,
        glucose=100.0,
    )
    result = calculate_lrinec(params)
    assert result.value == 0
    assert "Low risk" in result.interpretation
    assert "LRINEC score is 0" in result.interpretation


def test_lrinec_maximum_score():
    """All labs worst: CRP >=150 (4) + WBC >25 (2) + Hgb <11 (2) + Na <135 (2) + Cr >1.6 (2) + Glc >180 (1) = 13."""
    params = LRINECParams(
        crp=300.0,
        wbc=30.0,
        hemoglobin=8.0,
        sodium=128.0,
        creatinine=3.0,
        glucose=250.0,
    )
    result = calculate_lrinec(params)
    assert result.value == 13
    assert "High risk" in result.interpretation


def test_lrinec_low_risk_boundary():
    """Score of 5 is the upper boundary of low risk."""
    # CRP >=150 (4) + Glucose >180 (1) = 5, rest normal
    params = LRINECParams(
        crp=200.0,
        wbc=10.0,
        hemoglobin=14.0,
        sodium=140.0,
        creatinine=1.0,
        glucose=200.0,
    )
    result = calculate_lrinec(params)
    assert result.value == 5
    assert "Low risk" in result.interpretation


def test_lrinec_moderate_risk_lower_boundary():
    """Score of 6 enters moderate risk."""
    # CRP >=150 (4) + Na <135 (2) = 6, rest normal
    params = LRINECParams(
        crp=160.0,
        wbc=10.0,
        hemoglobin=14.0,
        sodium=130.0,
        creatinine=1.0,
        glucose=100.0,
    )
    result = calculate_lrinec(params)
    assert result.value == 6
    assert "Moderate risk" in result.interpretation


def test_lrinec_moderate_risk_upper_boundary():
    """Score of 7 is the upper boundary of moderate risk."""
    # CRP >=150 (4) + Na <135 (2) + Glucose >180 (1) = 7
    params = LRINECParams(
        crp=160.0,
        wbc=10.0,
        hemoglobin=14.0,
        sodium=130.0,
        creatinine=1.0,
        glucose=200.0,
    )
    result = calculate_lrinec(params)
    assert result.value == 7
    assert "Moderate risk" in result.interpretation


def test_lrinec_high_risk_lower_boundary():
    """Score of 8 enters high risk."""
    # CRP >=150 (4) + Na <135 (2) + Hgb 11-13.5 (1) + Glucose >180 (1) = 8
    params = LRINECParams(
        crp=160.0,
        wbc=10.0,
        hemoglobin=12.0,
        sodium=130.0,
        creatinine=1.0,
        glucose=200.0,
    )
    result = calculate_lrinec(params)
    assert result.value == 8
    assert "High risk" in result.interpretation
    assert "surgical exploration" in result.interpretation.lower()


def test_lrinec_crp_threshold():
    """CRP at exactly 150 should score 4 points."""
    params = LRINECParams(
        crp=150.0,
        wbc=8.0,
        hemoglobin=15.0,
        sodium=140.0,
        creatinine=0.9,
        glucose=100.0,
    )
    result = calculate_lrinec(params)
    assert result.value == 4


def test_lrinec_crp_below_threshold():
    """CRP at 149.9 should score 0 points."""
    params = LRINECParams(
        crp=149.9,
        wbc=8.0,
        hemoglobin=15.0,
        sodium=140.0,
        creatinine=0.9,
        glucose=100.0,
    )
    result = calculate_lrinec(params)
    assert result.value == 0


def test_lrinec_wbc_low():
    """WBC <15 scores 0 points."""
    params = LRINECParams(
        crp=10.0,
        wbc=14.9,
        hemoglobin=15.0,
        sodium=140.0,
        creatinine=0.9,
        glucose=100.0,
    )
    result = calculate_lrinec(params)
    assert result.value == 0


def test_lrinec_wbc_mid():
    """WBC 15-25 scores 1 point."""
    params = LRINECParams(
        crp=10.0,
        wbc=20.0,
        hemoglobin=15.0,
        sodium=140.0,
        creatinine=0.9,
        glucose=100.0,
    )
    result = calculate_lrinec(params)
    assert result.value == 1


def test_lrinec_wbc_boundary_15():
    """WBC at exactly 15 scores 1 point."""
    params = LRINECParams(
        crp=10.0,
        wbc=15.0,
        hemoglobin=15.0,
        sodium=140.0,
        creatinine=0.9,
        glucose=100.0,
    )
    result = calculate_lrinec(params)
    assert result.value == 1


def test_lrinec_wbc_boundary_25():
    """WBC at exactly 25 scores 1 point (>25 needed for 2 points)."""
    params = LRINECParams(
        crp=10.0,
        wbc=25.0,
        hemoglobin=15.0,
        sodium=140.0,
        creatinine=0.9,
        glucose=100.0,
    )
    result = calculate_lrinec(params)
    assert result.value == 1


def test_lrinec_wbc_high():
    """WBC >25 scores 2 points."""
    params = LRINECParams(
        crp=10.0,
        wbc=25.1,
        hemoglobin=15.0,
        sodium=140.0,
        creatinine=0.9,
        glucose=100.0,
    )
    result = calculate_lrinec(params)
    assert result.value == 2


def test_lrinec_hemoglobin_normal():
    """Hemoglobin >13.5 scores 0 points."""
    params = LRINECParams(
        crp=10.0,
        wbc=8.0,
        hemoglobin=14.0,
        sodium=140.0,
        creatinine=0.9,
        glucose=100.0,
    )
    result = calculate_lrinec(params)
    assert result.value == 0


def test_lrinec_hemoglobin_boundary_13_5():
    """Hemoglobin at exactly 13.5 scores 1 point (11-13.5 range)."""
    params = LRINECParams(
        crp=10.0,
        wbc=8.0,
        hemoglobin=13.5,
        sodium=140.0,
        creatinine=0.9,
        glucose=100.0,
    )
    result = calculate_lrinec(params)
    assert result.value == 1


def test_lrinec_hemoglobin_mid():
    """Hemoglobin 12.0 (in 11-13.5 range) scores 1 point."""
    params = LRINECParams(
        crp=10.0,
        wbc=8.0,
        hemoglobin=12.0,
        sodium=140.0,
        creatinine=0.9,
        glucose=100.0,
    )
    result = calculate_lrinec(params)
    assert result.value == 1


def test_lrinec_hemoglobin_boundary_11():
    """Hemoglobin at exactly 11.0 scores 1 point (11-13.5 range includes 11)."""
    params = LRINECParams(
        crp=10.0,
        wbc=8.0,
        hemoglobin=11.0,
        sodium=140.0,
        creatinine=0.9,
        glucose=100.0,
    )
    result = calculate_lrinec(params)
    assert result.value == 1


def test_lrinec_hemoglobin_low():
    """Hemoglobin <11 scores 2 points."""
    params = LRINECParams(
        crp=10.0,
        wbc=8.0,
        hemoglobin=10.9,
        sodium=140.0,
        creatinine=0.9,
        glucose=100.0,
    )
    result = calculate_lrinec(params)
    assert result.value == 2


def test_lrinec_sodium_normal():
    """Sodium >=135 scores 0 points."""
    params = LRINECParams(
        crp=10.0,
        wbc=8.0,
        hemoglobin=15.0,
        sodium=135.0,
        creatinine=0.9,
        glucose=100.0,
    )
    result = calculate_lrinec(params)
    assert result.value == 0


def test_lrinec_sodium_low():
    """Sodium <135 scores 2 points."""
    params = LRINECParams(
        crp=10.0,
        wbc=8.0,
        hemoglobin=15.0,
        sodium=134.9,
        creatinine=0.9,
        glucose=100.0,
    )
    result = calculate_lrinec(params)
    assert result.value == 2


def test_lrinec_creatinine_normal():
    """Creatinine <=1.6 scores 0 points."""
    params = LRINECParams(
        crp=10.0,
        wbc=8.0,
        hemoglobin=15.0,
        sodium=140.0,
        creatinine=1.6,
        glucose=100.0,
    )
    result = calculate_lrinec(params)
    assert result.value == 0


def test_lrinec_creatinine_high():
    """Creatinine >1.6 scores 2 points."""
    params = LRINECParams(
        crp=10.0,
        wbc=8.0,
        hemoglobin=15.0,
        sodium=140.0,
        creatinine=1.7,
        glucose=100.0,
    )
    result = calculate_lrinec(params)
    assert result.value == 2


def test_lrinec_glucose_normal():
    """Glucose <=180 scores 0 points."""
    params = LRINECParams(
        crp=10.0,
        wbc=8.0,
        hemoglobin=15.0,
        sodium=140.0,
        creatinine=0.9,
        glucose=180.0,
    )
    result = calculate_lrinec(params)
    assert result.value == 0


def test_lrinec_glucose_high():
    """Glucose >180 scores 1 point."""
    params = LRINECParams(
        crp=10.0,
        wbc=8.0,
        hemoglobin=15.0,
        sodium=140.0,
        creatinine=0.9,
        glucose=181.0,
    )
    result = calculate_lrinec(params)
    assert result.value == 1


def test_lrinec_evidence_doi():
    """Verify DOI matches the original Wong 2004 paper."""
    params = LRINECParams(
        crp=10.0,
        wbc=8.0,
        hemoglobin=15.0,
        sodium=140.0,
        creatinine=0.9,
        glucose=100.0,
    )
    result = calculate_lrinec(params)
    assert result.evidence.source_doi == "10.1097/01.CCM.0000121422.83937.48"
    assert result.evidence.level == "Derivation & Validation Study"


def test_lrinec_fhir_code():
    """Verify FHIR metadata. No specific LOINC for LRINEC, so code is None."""
    params = LRINECParams(
        crp=10.0,
        wbc=8.0,
        hemoglobin=15.0,
        sodium=140.0,
        creatinine=0.9,
        glucose=100.0,
    )
    result = calculate_lrinec(params)
    assert result.fhir_code is None
    assert result.fhir_system == "http://loinc.org"
    assert "LRINEC" in result.fhir_display


def test_lrinec_each_parameter_isolated():
    """Score each parameter individually to verify correct point contribution."""
    base = dict(crp=10.0, wbc=8.0, hemoglobin=15.0, sodium=140.0, creatinine=0.9, glucose=100.0)

    # CRP only
    r = calculate_lrinec(LRINECParams(**{**base, "crp": 200.0}))
    assert r.value == 4

    # WBC mid only
    r = calculate_lrinec(LRINECParams(**{**base, "wbc": 20.0}))
    assert r.value == 1

    # WBC high only
    r = calculate_lrinec(LRINECParams(**{**base, "wbc": 30.0}))
    assert r.value == 2

    # Hemoglobin mid only
    r = calculate_lrinec(LRINECParams(**{**base, "hemoglobin": 12.0}))
    assert r.value == 1

    # Hemoglobin low only
    r = calculate_lrinec(LRINECParams(**{**base, "hemoglobin": 9.0}))
    assert r.value == 2

    # Sodium low only
    r = calculate_lrinec(LRINECParams(**{**base, "sodium": 130.0}))
    assert r.value == 2

    # Creatinine high only
    r = calculate_lrinec(LRINECParams(**{**base, "creatinine": 2.0}))
    assert r.value == 2

    # Glucose high only
    r = calculate_lrinec(LRINECParams(**{**base, "glucose": 200.0}))
    assert r.value == 1


def test_lrinec_clinical_scenario_nf_patient():
    """Typical NF patient: very elevated CRP, high WBC, low Hgb, low Na, high Cr, high Glc."""
    params = LRINECParams(
        crp=250.0,   # >= 150 -> 4
        wbc=22.0,    # 15-25 -> 1
        hemoglobin=10.0,  # <11 -> 2
        sodium=131.0,  # <135 -> 2
        creatinine=2.5,   # >1.6 -> 2
        glucose=220.0,    # >180 -> 1
    )
    result = calculate_lrinec(params)
    assert result.value == 12
    assert "High risk" in result.interpretation


def test_lrinec_clinical_scenario_cellulitis():
    """Typical cellulitis patient: mildly elevated CRP, normal other labs."""
    params = LRINECParams(
        crp=80.0,     # <150 -> 0
        wbc=12.0,     # <15 -> 0
        hemoglobin=13.0,  # 11-13.5 -> 1
        sodium=138.0,    # >=135 -> 0
        creatinine=1.0,   # <=1.6 -> 0
        glucose=110.0,    # <=180 -> 0
    )
    result = calculate_lrinec(params)
    assert result.value == 1
    assert "Low risk" in result.interpretation


# ---------------------------------------------------------------------------
# Tier 2: Property-Based Fuzz Tests (bounds checking)
# ---------------------------------------------------------------------------

@pytest.mark.slow
@given(
    st.builds(
        LRINECParams,
        crp=st.floats(min_value=0.0, max_value=500.0),
        wbc=st.floats(min_value=0.0, max_value=100.0),
        hemoglobin=st.floats(min_value=1.0, max_value=25.0),
        sodium=st.floats(min_value=100.0, max_value=180.0),
        creatinine=st.floats(min_value=0.1, max_value=20.0),
        glucose=st.floats(min_value=10.0, max_value=1000.0),
    )
)
@settings(max_examples=500)
def test_lrinec_fuzz_valid_range(params):
    """LRINEC score is always 0-13 for any valid lab input combination."""
    result = calculate_lrinec(params)
    assert result.value is not None
    assert isinstance(result.value, int)
    assert 0 <= result.value <= 13
    assert result.interpretation
    assert result.evidence.source_doi
    # Risk category must be one of the three defined
    interp = result.interpretation
    assert any(
        cat in interp for cat in ["Low risk", "Moderate risk", "High risk"]
    )

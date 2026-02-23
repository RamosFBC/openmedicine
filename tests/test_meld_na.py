import pytest
from hypothesis import given, strategies as st, settings
from open_medicine.mcp.calculators.meld_na import calculate_meld_na, MELDNaParams


def test_meld_na_minimum_score():
    """All normal values → floor is 6."""
    params = MELDNaParams(creatinine=0.5, bilirubin=0.5, inr=0.9, sodium=140.0, on_dialysis=False)
    res = calculate_meld_na(params)
    # With all labs at minimum (capped to 1.0) and Na capped to 137,
    # MELD(i)=round(0.643*10)=6, MELD-Na=6-137-0.025*6*3+140=6+3-0.45≈9
    assert res.value >= 6
    assert res.value <= 12


def test_meld_na_maximum_score():
    """Worst values → maximum score of 40."""
    params = MELDNaParams(creatinine=5.0, bilirubin=30.0, inr=5.0, sodium=120.0, on_dialysis=True)
    res = calculate_meld_na(params)
    assert res.value == 40


def test_meld_na_dialysis_sets_cr_4():
    """On dialysis should set creatinine to 4.0."""
    p1 = MELDNaParams(creatinine=1.0, bilirubin=2.0, inr=1.5, sodium=130.0, on_dialysis=True)
    p2 = MELDNaParams(creatinine=4.0, bilirubin=2.0, inr=1.5, sodium=130.0, on_dialysis=False)
    assert calculate_meld_na(p1).value == calculate_meld_na(p2).value


def test_meld_na_low_sodium_capped():
    """Sodium below 125 should be capped at 125."""
    p1 = MELDNaParams(creatinine=2.0, bilirubin=3.0, inr=2.0, sodium=110.0)
    p2 = MELDNaParams(creatinine=2.0, bilirubin=3.0, inr=2.0, sodium=125.0)
    assert calculate_meld_na(p1).value == calculate_meld_na(p2).value


def test_meld_na_high_sodium_capped():
    """Sodium above 137 should be capped at 137."""
    p1 = MELDNaParams(creatinine=2.0, bilirubin=3.0, inr=2.0, sodium=145.0)
    p2 = MELDNaParams(creatinine=2.0, bilirubin=3.0, inr=2.0, sodium=137.0)
    assert calculate_meld_na(p1).value == calculate_meld_na(p2).value


def test_meld_na_moderate_case():
    """A moderate case within typical range."""
    params = MELDNaParams(creatinine=1.5, bilirubin=2.0, inr=1.5, sodium=135.0)
    res = calculate_meld_na(params)
    assert 6 <= res.value <= 40
    assert "MELD-Na score" in res.interpretation


def test_meld_na_stratum_low():
    """Score ≤9 → low mortality."""
    params = MELDNaParams(creatinine=0.8, bilirubin=1.0, inr=1.0, sodium=137.0)
    res = calculate_meld_na(params)
    assert res.value <= 9
    assert "Low" in res.interpretation


def test_meld_na_evidence_doi():
    params = MELDNaParams(creatinine=1.0, bilirubin=1.0, inr=1.0, sodium=137.0)
    res = calculate_meld_na(params)
    assert res.evidence.source_doi == "10.1002/hep.22023"


def test_meld_na_fhir_code():
    params = MELDNaParams(creatinine=1.0, bilirubin=1.0, inr=1.0, sodium=137.0)
    res = calculate_meld_na(params)
    assert res.fhir_code == "75622-1"
    assert res.fhir_system == "http://loinc.org"


@given(
    creatinine=st.floats(min_value=0.3, max_value=8.0),
    bilirubin=st.floats(min_value=0.1, max_value=50.0),
    inr=st.floats(min_value=0.5, max_value=10.0),
    sodium=st.floats(min_value=100.0, max_value=160.0),
    on_dialysis=st.booleans(),
)
@settings(max_examples=500)
def test_meld_na_fuzz(creatinine, bilirubin, inr, sodium, on_dialysis):
    params = MELDNaParams(creatinine=creatinine, bilirubin=bilirubin, inr=inr, sodium=sodium, on_dialysis=on_dialysis)
    res = calculate_meld_na(params)
    assert res.value is not None
    assert 6 <= res.value <= 40
    assert res.interpretation

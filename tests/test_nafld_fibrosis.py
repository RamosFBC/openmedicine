import pytest
from hypothesis import given, strategies as st, settings
from open_medicine.mcp.calculators.nafld_fibrosis import calculate_nafld_fibrosis, NAFLDFibrosisParams


def test_nfs_low_probability():
    """Young, healthy BMI, no DM, normal labs → low probability."""
    params = NAFLDFibrosisParams(
        age=35, bmi=24.0, impaired_fasting_glucose_or_diabetes=False,
        ast=20.0, alt=25.0, platelets=250.0, albumin=4.5
    )
    res = calculate_nafld_fibrosis(params)
    assert res.value < -1.455
    assert "Low probability" in res.interpretation


def test_nfs_high_probability():
    """Older, obese, diabetic, abnormal labs → high probability."""
    params = NAFLDFibrosisParams(
        age=65, bmi=38.0, impaired_fasting_glucose_or_diabetes=True,
        ast=80.0, alt=50.0, platelets=90.0, albumin=2.8
    )
    res = calculate_nafld_fibrosis(params)
    assert res.value > 0.676
    assert "High probability" in res.interpretation


def test_nfs_indeterminate():
    """Middle-range values → indeterminate."""
    params = NAFLDFibrosisParams(
        age=50, bmi=30.0, impaired_fasting_glucose_or_diabetes=False,
        ast=40.0, alt=45.0, platelets=180.0, albumin=3.8
    )
    res = calculate_nafld_fibrosis(params)
    assert -1.455 <= res.value <= 0.676
    assert "Indeterminate" in res.interpretation


def test_nfs_known_calculation():
    """Manual: -1.675 + 0.037*50 + 0.094*28 + 1.13*0 + 0.99*(30/30) - 0.013*200 - 0.66*4.0
       = -1.675 + 1.85 + 2.632 + 0 + 0.99 - 2.6 - 2.64 = -1.443"""
    params = NAFLDFibrosisParams(
        age=50, bmi=28.0, impaired_fasting_glucose_or_diabetes=False,
        ast=30.0, alt=30.0, platelets=200.0, albumin=4.0
    )
    res = calculate_nafld_fibrosis(params)
    assert abs(res.value - (-1.443)) < 0.01


def test_nfs_zero_alt_returns_none():
    params = NAFLDFibrosisParams(
        age=50, bmi=28.0, impaired_fasting_glucose_or_diabetes=False,
        ast=30.0, alt=0.0, platelets=200.0, albumin=4.0
    )
    res = calculate_nafld_fibrosis(params)
    assert res.value is None


def test_nfs_evidence_doi():
    params = NAFLDFibrosisParams(
        age=50, bmi=28.0, impaired_fasting_glucose_or_diabetes=False,
        ast=30.0, alt=30.0, platelets=200.0, albumin=4.0
    )
    res = calculate_nafld_fibrosis(params)
    assert res.evidence.source_doi == "10.1002/hep.21496"


def test_nfs_fhir_code():
    params = NAFLDFibrosisParams(
        age=50, bmi=28.0, impaired_fasting_glucose_or_diabetes=False,
        ast=30.0, alt=30.0, platelets=200.0, albumin=4.0
    )
    res = calculate_nafld_fibrosis(params)
    assert res.fhir_code == "96155-2"
    assert res.fhir_system == "http://loinc.org"


@pytest.mark.slow
@given(
    age=st.integers(min_value=18, max_value=90),
    bmi=st.floats(min_value=15.0, max_value=60.0),
    dm=st.booleans(),
    ast=st.floats(min_value=5.0, max_value=500.0),
    alt=st.floats(min_value=5.0, max_value=500.0),
    platelets=st.floats(min_value=10.0, max_value=500.0),
    albumin=st.floats(min_value=1.0, max_value=6.0),
)
@settings(max_examples=500)
def test_nfs_fuzz(age, bmi, dm, ast, alt, platelets, albumin):
    params = NAFLDFibrosisParams(
        age=age, bmi=bmi, impaired_fasting_glucose_or_diabetes=dm,
        ast=ast, alt=alt, platelets=platelets, albumin=albumin
    )
    res = calculate_nafld_fibrosis(params)
    assert res.value is not None
    assert res.interpretation

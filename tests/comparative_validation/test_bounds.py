import pytest
from hypothesis import given, strategies as st
from open_medicine.mcp.calculators.sofa import calculate_sofa, SOFAParams
from open_medicine.mcp.calculators.chadsvasc import calculate_chadsvasc, CHADSVAScParams
from open_medicine.mcp.calculators.ckd_epi import calculate_ckd_epi, CKDEPIParams
from open_medicine.mcp.calculators.cockcroft_gault import calculate_cockcroft_gault, CockcroftGaultParams
from open_medicine.mcp.calculators.gcs import calculate_gcs, GCSParams
from open_medicine.mcp.calculators.hasbled import calculate_hasbled, HASBLEDParams
from open_medicine.mcp.calculators.curb65 import calculate_curb65, CURB65Params

@given(
    st.builds(
        SOFAParams,
        # Generate entirely random bounds across reasonable ranges to assert it never crashes
        pao2_fio2_ratio=st.one_of(st.none(), st.floats(min_value=0.0, max_value=800.0)),
        mechanical_ventilation=st.booleans(),
        platelets=st.one_of(st.none(), st.integers(min_value=0, max_value=800)),
        bilirubin=st.one_of(st.none(), st.floats(min_value=0.0, max_value=50.0)),
        map=st.one_of(st.none(), st.floats(min_value=20.0, max_value=200.0)),
        dopamine_dose=st.one_of(st.none(), st.floats(min_value=0.0, max_value=50.0)),
        epinephrine_dose=st.one_of(st.none(), st.floats(min_value=0.0, max_value=2.0)),
        norepinephrine_dose=st.one_of(st.none(), st.floats(min_value=0.0, max_value=2.0)),
        dobutamine=st.booleans(),
        gcs=st.one_of(st.none(), st.integers(min_value=3, max_value=15)),
        creatinine=st.one_of(st.none(), st.floats(min_value=0.0, max_value=20.0)),
        urine_output=st.one_of(st.none(), st.floats(min_value=0.0, max_value=5000.0))
    )
)
def test_sofa_bounds(params):
    """
    Property-based test: No matter the random combinations of inputs,
    SOFA score must always be calculating, returning between 0-24 points.
    """
    result = calculate_sofa(params)
    assert result.value is not None
    assert 0 <= result.value <= 24
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0


@given(
    st.builds(
        CHADSVAScParams,
        congestive_heart_failure=st.booleans(),
        hypertension=st.booleans(),
        age=st.integers(min_value=18, max_value=120),
        diabetes=st.booleans(),
        stroke_tia_thromboembolism=st.booleans(),
        vascular_disease=st.booleans(),
        female_sex=st.booleans()
    )
)
def test_chadsvasc_bounds(params):
    """
    Property-based test: No matter the combinations of inputs,
    CHA2DS2-VASc must always return a score between 0 and 9 points.
    """
    result = calculate_chadsvasc(params)
    assert result.value is not None
    assert 0 <= result.value <= 9
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0

@given(
    st.builds(
        CKDEPIParams,
        age=st.integers(min_value=18, max_value=120),
        is_female=st.booleans(),
        serum_creatinine=st.floats(min_value=0.1, max_value=25.0)
    )
)
def test_ckd_epi_bounds(params):
    """
    Ensure that the CKD-EPI formula never raises arbitrary mathematical 
    exceptions across the full spread of reasonable clinical boundaries.
    Since it produces a real ratio, valid range varies from ~0 to ~200.
    """
    result = calculate_ckd_epi(params)
    assert result.value is not None
    assert type(result.value) == float
    assert result.value >= 0.0
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "eGFR" in result.interpretation


@given(
    st.builds(
        CockcroftGaultParams,
        age=st.integers(min_value=18, max_value=120),
        weight=st.floats(min_value=30.0, max_value=300.0),
        is_female=st.booleans(),
        serum_creatinine=st.floats(min_value=0.1, max_value=30.0)
    )
)
def test_cockcroft_gault_bounds(params):
    """
    Ensure the Cockcroft-Gault equation parses gracefully across infinite permutations mapping
    severe obesity, extreme low weights, and massive serum creatinine bounds without crashing.
    """
    result = calculate_cockcroft_gault(params)
    assert result.value is not None
    assert type(result.value) == float
    assert result.value >= 0.0
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "mL/min" in result.interpretation


@given(
    st.builds(
        GCSParams,
        eye_response=st.integers(min_value=1, max_value=4),
        verbal_response=st.integers(min_value=1, max_value=5),
        motor_response=st.integers(min_value=1, max_value=6)
    )
)
def test_gcs_bounds(params):
    """
    Ensure the Glasgow Coma Scale behaves safely across all valid permutations of E, V, and M scores.
    """
    result = calculate_gcs(params)
    assert result.value is not None
    assert type(result.value) == float
    assert 3.0 <= result.value <= 15.0
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "Classification:" in result.interpretation


@given(
    st.builds(
        HASBLEDParams,
        hypertension=st.booleans(),
        abnormal_renal_function=st.booleans(),
        abnormal_liver_function=st.booleans(),
        stroke=st.booleans(),
        bleeding=st.booleans(),
        labile_inr=st.booleans(),
        elderly=st.booleans(),
        drugs=st.booleans(),
        alcohol=st.booleans()
    )
)
def test_hasbled_bounds(params):
    """
    Property-based test: HAS-BLED must always return 0-9 across all boolean permutations.
    """
    result = calculate_hasbled(params)
    assert result.value is not None
    assert 0 <= result.value <= 9
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "HAS-BLED" in result.interpretation


@given(
    st.builds(
        CURB65Params,
        confusion=st.booleans(),
        bun=st.floats(min_value=0.0, max_value=150.0),
        respiratory_rate=st.integers(min_value=8, max_value=60),
        systolic_bp=st.integers(min_value=40, max_value=250),
        diastolic_bp=st.integers(min_value=20, max_value=150),
        age=st.integers(min_value=18, max_value=120)
    )
)
def test_curb65_bounds(params):
    """
    Property-based test: CURB-65 must always return 0-5 across all valid clinical input combinations.
    """
    result = calculate_curb65(params)
    assert result.value is not None
    assert 0 <= result.value <= 5
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "CURB-65" in result.interpretation

import pytest
from hypothesis import given, strategies as st
from open_medicine.mcp.calculators.sofa import calculate_sofa, SOFAParams
from open_medicine.mcp.calculators.chadsvasc import calculate_chadsvasc, CHADSVAScParams

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

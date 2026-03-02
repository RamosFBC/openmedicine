import pytest
from hypothesis import given, strategies as st
from open_medicine.mcp.calculators.sofa import calculate_sofa, SOFAParams
from open_medicine.mcp.calculators.chadsvasc import calculate_chadsvasc, CHADSVAScParams
from open_medicine.mcp.calculators.ckd_epi import calculate_ckd_epi, CKDEPIParams
from open_medicine.mcp.calculators.cockcroft_gault import calculate_cockcroft_gault, CockcroftGaultParams
from open_medicine.mcp.calculators.gcs import calculate_gcs, GCSParams
from open_medicine.mcp.calculators.hasbled import calculate_hasbled, HASBLEDParams
from open_medicine.mcp.calculators.curb65 import calculate_curb65, CURB65Params
from open_medicine.mcp.calculators.ottawa_ankle import calculate_ottawa_ankle, OttawaAnkleParams
from open_medicine.mcp.calculators.gad7 import calculate_gad7, GAD7Params
from open_medicine.mcp.calculators.audit_c import calculate_audit_c, AUDITCParams
from open_medicine.mcp.calculators.apache2 import calculate_apache2, APACHE2Params, AdmissionType
from open_medicine.mcp.calculators.isth_dic import calculate_isth_dic, ISTHDICParams
from open_medicine.mcp.calculators.maintenance_iv_fluids import calculate_maintenance_iv_fluids, MaintenanceIVFluidsParams
from open_medicine.mcp.calculators.framingham import calculate_framingham, FraminghamParams
from open_medicine.mcp.calculators.frax import calculate_frax, FRAXParams
from open_medicine.mcp.calculators.das28 import calculate_das28, DAS28Params, DAS28Variant

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


@given(
    st.builds(
        OttawaAnkleParams,
        malleolar_zone_pain=st.booleans(),
        tenderness_posterior_edge_or_tip_lateral_malleolus=st.booleans(),
        tenderness_posterior_edge_or_tip_medial_malleolus=st.booleans(),
        midfoot_zone_pain=st.booleans(),
        tenderness_base_fifth_metatarsal=st.booleans(),
        tenderness_navicular=st.booleans(),
        inability_to_bear_weight=st.booleans()
    )
)
def test_ottawa_ankle_bounds(params):
    """
    Property-based test: Ottawa Ankle Rules must always return a value
    in {0, 1, 2, 3} across all boolean permutations.
    """
    result = calculate_ottawa_ankle(params)
    assert result.value is not None
    assert result.value in (0, 1, 2, 3)
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "Ottawa Ankle Rules:" in result.interpretation


@given(
    st.builds(
        GAD7Params,
        feeling_nervous=st.integers(min_value=0, max_value=3),
        cannot_stop_worrying=st.integers(min_value=0, max_value=3),
        worrying_too_much=st.integers(min_value=0, max_value=3),
        trouble_relaxing=st.integers(min_value=0, max_value=3),
        being_restless=st.integers(min_value=0, max_value=3),
        easily_annoyed=st.integers(min_value=0, max_value=3),
        feeling_afraid=st.integers(min_value=0, max_value=3),
    )
)
def test_gad7_bounds(params):
    """
    Property-based test: GAD-7 must always return 0-21 across all valid item value permutations.
    """
    result = calculate_gad7(params)
    assert result.value is not None
    assert 0 <= result.value <= 21
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "GAD-7" in result.interpretation


@given(
    st.builds(
        AUDITCParams,
        frequency=st.integers(min_value=0, max_value=4),
        typical_quantity=st.integers(min_value=0, max_value=4),
        binge_frequency=st.integers(min_value=0, max_value=4),
        is_male=st.booleans(),
    )
)
def test_audit_c_bounds(params):
    """
    Property-based test: AUDIT-C must always return 0-12 across all valid item value permutations.
    """
    result = calculate_audit_c(params)
    assert result.value is not None
    assert 0 <= result.value <= 12
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "AUDIT-C" in result.interpretation


@given(
    temperature=st.floats(min_value=20.0, max_value=45.0),
    mean_arterial_pressure=st.floats(min_value=20.0, max_value=250.0),
    heart_rate=st.integers(min_value=10, max_value=250),
    respiratory_rate=st.integers(min_value=0, max_value=70),
    fio2=st.floats(min_value=0.21, max_value=1.0),
    pao2=st.floats(min_value=20.0, max_value=600.0),
    paco2=st.one_of(st.none(), st.floats(min_value=10.0, max_value=120.0)),
    arterial_ph=st.floats(min_value=6.5, max_value=8.0),
    serum_sodium=st.floats(min_value=90.0, max_value=200.0),
    serum_potassium=st.floats(min_value=1.0, max_value=10.0),
    serum_creatinine=st.floats(min_value=0.1, max_value=15.0),
    acute_renal_failure=st.booleans(),
    hematocrit=st.floats(min_value=5.0, max_value=80.0),
    white_blood_cell_count=st.floats(min_value=0.1, max_value=100.0),
    gcs=st.integers(min_value=3, max_value=15),
    age=st.integers(min_value=18, max_value=110),
    admission_type=st.sampled_from(list(AdmissionType)),
    severe_organ=st.booleans(),
)
def test_apache2_bounds(
    temperature,
    mean_arterial_pressure,
    heart_rate,
    respiratory_rate,
    fio2,
    pao2,
    paco2,
    arterial_ph,
    serum_sodium,
    serum_potassium,
    serum_creatinine,
    acute_renal_failure,
    hematocrit,
    white_blood_cell_count,
    gcs,
    age,
    admission_type,
    severe_organ,
):
    """
    Property-based test: APACHE II must always return a score between 0 and 71
    across all valid clinical input combinations.
    """
    params = APACHE2Params(
        temperature=temperature,
        mean_arterial_pressure=mean_arterial_pressure,
        heart_rate=heart_rate,
        respiratory_rate=respiratory_rate,
        fio2=fio2,
        pao2=pao2,
        paco2=paco2,
        arterial_ph=arterial_ph,
        serum_sodium=serum_sodium,
        serum_potassium=serum_potassium,
        serum_creatinine=serum_creatinine,
        acute_renal_failure=acute_renal_failure,
        hematocrit=hematocrit,
        white_blood_cell_count=white_blood_cell_count,
        gcs=gcs,
        age=age,
        admission_type=admission_type,
        severe_organ_insufficiency_or_immunocompromised=severe_organ,
    )
    result = calculate_apache2(params)
    assert result.value is not None
    assert 0 <= result.value <= 71
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "APACHE II score is" in result.interpretation


@given(
    st.builds(
        ISTHDICParams,
        platelet_count=st.integers(min_value=0, max_value=800),
        fibrin_marker_increase=st.integers(min_value=0, max_value=2),
        pt_prolongation_seconds=st.floats(min_value=0.0, max_value=60.0),
        fibrinogen_level=st.floats(min_value=0.0, max_value=15.0),
    )
)
def test_isth_dic_bounds(params):
    """
    Property-based test: ISTH DIC score must always return 0-8
    across all valid clinical input combinations.
    """
    result = calculate_isth_dic(params)
    assert result.value is not None
    assert 0 <= result.value <= 8
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "DIC" in result.interpretation


@given(
    st.builds(
        MaintenanceIVFluidsParams,
        weight_kg=st.floats(min_value=0.1, max_value=300.0),
    )
)
def test_maintenance_iv_fluids_bounds(params):
    """
    Property-based test: Maintenance IV fluid hourly rate must always be positive
    and within a clinically plausible range across all valid weight inputs.
    """
    result = calculate_maintenance_iv_fluids(params)
    assert result.value is not None
    assert isinstance(result.value, float)
    assert result.value > 0
    # Max: 300 kg -> 60 + 280 = 340 mL/hr
    assert result.value <= 400.0
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "mL/hr" in result.interpretation


@given(
    is_female=st.booleans(),
    age=st.integers(min_value=30, max_value=74),
    total_cholesterol=st.integers(min_value=100, max_value=400),
    hdl_cholesterol=st.integers(min_value=20, max_value=100),
    systolic_blood_pressure=st.integers(min_value=90, max_value=200),
    is_treated_for_hypertension=st.booleans(),
    is_smoker=st.booleans(),
)
def test_framingham_bounds(
    is_female,
    age,
    total_cholesterol,
    hdl_cholesterol,
    systolic_blood_pressure,
    is_treated_for_hypertension,
    is_smoker,
):
    """
    Property-based test: Framingham Risk Score must always return a percentage
    between 0 and 100 across all valid clinical input combinations.
    """
    params = FraminghamParams(
        is_female=is_female,
        age=age,
        total_cholesterol=total_cholesterol,
        hdl_cholesterol=hdl_cholesterol,
        systolic_blood_pressure=systolic_blood_pressure,
        is_treated_for_hypertension=is_treated_for_hypertension,
        is_smoker=is_smoker,
    )
    result = calculate_framingham(params)
    assert result.value is not None
    assert isinstance(result.value, float)
    assert 0.0 <= result.value <= 100.0
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "Framingham" in result.interpretation


@given(
    age=st.integers(min_value=40, max_value=90),
    is_female=st.booleans(),
    weight_kg=st.floats(min_value=30.0, max_value=200.0),
    height_cm=st.floats(min_value=120.0, max_value=220.0),
    prior_fracture=st.booleans(),
    parent_hip_fracture=st.booleans(),
    current_smoking=st.booleans(),
    glucocorticoids=st.booleans(),
    rheumatoid_arthritis=st.booleans(),
    secondary_osteoporosis=st.booleans(),
    alcohol_3_or_more=st.booleans(),
    femoral_neck_bmd_tscore=st.one_of(
        st.none(),
        st.floats(min_value=-4.0, max_value=2.0),
    ),
)
def test_frax_bounds(
    age, is_female, weight_kg, height_cm,
    prior_fracture, parent_hip_fracture, current_smoking,
    glucocorticoids, rheumatoid_arthritis, secondary_osteoporosis,
    alcohol_3_or_more, femoral_neck_bmd_tscore,
):
    """
    Property-based test: FRAX 10-year MOF probability must always return
    a percentage between 0 and 100 across all valid clinical input combinations.
    """
    params = FRAXParams(
        age=age,
        is_female=is_female,
        weight_kg=weight_kg,
        height_cm=height_cm,
        prior_fracture=prior_fracture,
        parent_hip_fracture=parent_hip_fracture,
        current_smoking=current_smoking,
        glucocorticoids=glucocorticoids,
        rheumatoid_arthritis=rheumatoid_arthritis,
        secondary_osteoporosis=secondary_osteoporosis,
        alcohol_3_or_more=alcohol_3_or_more,
        femoral_neck_bmd_tscore=femoral_neck_bmd_tscore,
    )
    result = calculate_frax(params)
    assert result.value is not None
    assert isinstance(result.value, float)
    assert 0.0 <= result.value <= 99.9
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "FRAX" in result.interpretation


@given(
    tender_joint_count=st.integers(min_value=0, max_value=28),
    swollen_joint_count=st.integers(min_value=0, max_value=28),
    esr=st.floats(min_value=0.1, max_value=200.0),
    global_health=st.floats(min_value=0, max_value=100),
)
def test_das28_esr_bounds(
    tender_joint_count, swollen_joint_count, esr, global_health,
):
    """
    Property-based test: DAS28-ESR must always return a non-negative float
    within a clinically plausible range across all valid clinical input combinations.
    """
    params = DAS28Params(
        tender_joint_count=tender_joint_count,
        swollen_joint_count=swollen_joint_count,
        esr=esr,
        global_health=global_health,
        variant=DAS28Variant.ESR,
    )
    result = calculate_das28(params)
    assert result.value is not None
    assert isinstance(result.value, float)
    # Theoretical range: ~0 to ~10 for typical ESR values
    assert result.value >= 0.0
    assert result.value <= 15.0
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "DAS28-ESR" in result.interpretation


@given(
    tender_joint_count=st.integers(min_value=0, max_value=28),
    swollen_joint_count=st.integers(min_value=0, max_value=28),
    crp=st.floats(min_value=0.0, max_value=300.0),
    global_health=st.floats(min_value=0, max_value=100),
)
def test_das28_crp_bounds(
    tender_joint_count, swollen_joint_count, crp, global_health,
):
    """
    Property-based test: DAS28-CRP must always return a value >= 0.96 (the constant offset)
    within a clinically plausible range across all valid clinical input combinations.
    """
    params = DAS28Params(
        tender_joint_count=tender_joint_count,
        swollen_joint_count=swollen_joint_count,
        crp=crp,
        global_health=global_health,
        variant=DAS28Variant.CRP,
    )
    result = calculate_das28(params)
    assert result.value is not None
    assert isinstance(result.value, float)
    assert result.value >= 0.9  # 0.96 minus tiny float imprecision
    assert result.value <= 15.0
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "DAS28-CRP" in result.interpretation

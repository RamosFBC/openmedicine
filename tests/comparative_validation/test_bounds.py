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
from open_medicine.mcp.calculators.rcri import calculate_rcri, RCRIParams
from open_medicine.mcp.calculators.charlson import calculate_charlson, CharlsonParams
from open_medicine.mcp.calculators.ecog import calculate_ecog, ECOGParams
from open_medicine.mcp.calculators.karnofsky import calculate_karnofsky, KarnofskyParams
from open_medicine.mcp.calculators.epds import calculate_epds, EPDSParams
from open_medicine.mcp.calculators.tbsa import calculate_tbsa, TBSAParams
from open_medicine.mcp.calculators.apgar import calculate_apgar, ApgarParams
from open_medicine.mcp.calculators.cage import calculate_cage, CAGEParams
from open_medicine.mcp.calculators.clinical_frailty import calculate_clinical_frailty, ClinicalFrailtyParams
from open_medicine.mcp.calculators.psi_port import calculate_psi_port, PSIPortParams
from open_medicine.mcp.calculators.mascc import calculate_mascc, MASCCParams, BurdenOfIllness, CancerType
from open_medicine.mcp.calculators.ipss import calculate_ipss, IPSSParams
from open_medicine.mcp.calculators.naranjo import calculate_naranjo, NaranjoParams, NaranjoResponse
from open_medicine.mcp.calculators.ciwa_ar import calculate_ciwa_ar, CIWAArParams
from open_medicine.mcp.calculators.rumack_matthew import calculate_rumack_matthew, RumackMatthewParams
from open_medicine.mcp.calculators.mews import calculate_mews, MEWSParams, AVPULevel
from open_medicine.mcp.calculators.cows import calculate_cows, COWSParams
from open_medicine.mcp.calculators.stop_bang import calculate_stop_bang, STOPBangParams
from open_medicine.mcp.calculators.aims65 import calculate_aims65, AIMS65Params
from open_medicine.mcp.calculators.lrinec import calculate_lrinec, LRINECParams
from open_medicine.mcp.calculators.rass import calculate_rass, RASSParams
from open_medicine.mcp.calculators.pediatric_gcs import calculate_pediatric_gcs, PediatricGCSParams
from open_medicine.mcp.calculators.cam_icu import calculate_cam_icu, CAMICUParams
from open_medicine.mcp.calculators.pews import calculate_pews, PEWSParams, PEWSAgeGroup, RespiratoryEffort

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


@given(
    st.builds(
        RCRIParams,
        high_risk_surgery=st.booleans(),
        history_of_ischemic_heart_disease=st.booleans(),
        history_of_congestive_heart_failure=st.booleans(),
        history_of_cerebrovascular_disease=st.booleans(),
        preoperative_insulin_treatment=st.booleans(),
        preoperative_creatinine_above_2=st.booleans(),
    )
)
def test_rcri_bounds(params):
    """
    Property-based test: RCRI must always return a score between 0 and 6
    across all 64 boolean permutations.
    """
    result = calculate_rcri(params)
    assert result.value is not None
    assert 0 <= result.value <= 6
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "RCRI" in result.interpretation


@given(
    myocardial_infarction=st.booleans(),
    congestive_heart_failure=st.booleans(),
    peripheral_vascular_disease=st.booleans(),
    cerebrovascular_disease=st.booleans(),
    dementia=st.booleans(),
    chronic_pulmonary_disease=st.booleans(),
    connective_tissue_disease=st.booleans(),
    peptic_ulcer_disease=st.booleans(),
    mild_liver_disease=st.booleans(),
    uncomplicated_diabetes=st.booleans(),
    hemiplegia=st.booleans(),
    moderate_severe_renal_disease=st.booleans(),
    diabetes_with_end_organ_damage=st.booleans(),
    solid_tumor=st.booleans(),
    leukemia=st.booleans(),
    lymphoma=st.booleans(),
    moderate_severe_liver_disease=st.booleans(),
    metastatic_solid_tumor=st.booleans(),
    aids=st.booleans(),
    age=st.one_of(st.none(), st.integers(min_value=18, max_value=110)),
)
def test_charlson_bounds(
    myocardial_infarction,
    congestive_heart_failure,
    peripheral_vascular_disease,
    cerebrovascular_disease,
    dementia,
    chronic_pulmonary_disease,
    connective_tissue_disease,
    peptic_ulcer_disease,
    mild_liver_disease,
    uncomplicated_diabetes,
    hemiplegia,
    moderate_severe_renal_disease,
    diabetes_with_end_organ_damage,
    solid_tumor,
    leukemia,
    lymphoma,
    moderate_severe_liver_disease,
    metastatic_solid_tumor,
    aids,
    age,
):
    """
    Property-based test: Charlson Comorbidity Index must always return
    a score between 0 and 41 across all valid input combinations.
    Max comorbidity = 37, max age adjustment = 4, total max = 41.
    """
    params = CharlsonParams(
        myocardial_infarction=myocardial_infarction,
        congestive_heart_failure=congestive_heart_failure,
        peripheral_vascular_disease=peripheral_vascular_disease,
        cerebrovascular_disease=cerebrovascular_disease,
        dementia=dementia,
        chronic_pulmonary_disease=chronic_pulmonary_disease,
        connective_tissue_disease=connective_tissue_disease,
        peptic_ulcer_disease=peptic_ulcer_disease,
        mild_liver_disease=mild_liver_disease,
        uncomplicated_diabetes=uncomplicated_diabetes,
        hemiplegia=hemiplegia,
        moderate_severe_renal_disease=moderate_severe_renal_disease,
        diabetes_with_end_organ_damage=diabetes_with_end_organ_damage,
        solid_tumor=solid_tumor,
        leukemia=leukemia,
        lymphoma=lymphoma,
        moderate_severe_liver_disease=moderate_severe_liver_disease,
        metastatic_solid_tumor=metastatic_solid_tumor,
        aids=aids,
        age=age,
    )
    result = calculate_charlson(params)
    assert result.value is not None
    assert 0 <= result.value <= 41
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "Charlson Comorbidity Index" in result.interpretation
    assert "Estimated 10-year survival:" in result.interpretation


@given(
    st.builds(
        ECOGParams,
        performance_status=st.integers(min_value=0, max_value=5),
    )
)
def test_ecog_bounds(params):
    """
    Property-based test: ECOG Performance Status must always return a score
    between 0 and 5 across all valid grade inputs.
    """
    result = calculate_ecog(params)
    assert result.value is not None
    assert 0 <= result.value <= 5
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "ECOG Performance Status" in result.interpretation


@given(
    st.builds(
        KarnofskyParams,
        kps_score=st.sampled_from(list(range(0, 110, 10))),
    )
)
def test_karnofsky_bounds(params):
    """
    Property-based test: Karnofsky Performance Status must always return a score
    between 0 and 100 across all valid KPS score inputs (multiples of 10).
    """
    result = calculate_karnofsky(params)
    assert result.value is not None
    assert 0 <= result.value <= 100
    assert result.value % 10 == 0
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "Karnofsky Performance Status" in result.interpretation


@given(
    st.builds(
        ApgarParams,
        appearance=st.integers(min_value=0, max_value=2),
        pulse=st.integers(min_value=0, max_value=2),
        grimace=st.integers(min_value=0, max_value=2),
        activity=st.integers(min_value=0, max_value=2),
        respiration=st.integers(min_value=0, max_value=2),
    )
)
def test_apgar_bounds(params):
    """
    Property-based test: Apgar Score must always return 0-10 across all
    valid permutations of the five component scores (each 0-2).
    """
    result = calculate_apgar(params)
    assert result.value is not None
    assert 0 <= result.value <= 10
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "Apgar Score is" in result.interpretation


@given(
    st.builds(
        TBSAParams,
        head_and_neck=st.booleans(),
        anterior_trunk=st.booleans(),
        posterior_trunk=st.booleans(),
        left_upper_extremity=st.booleans(),
        right_upper_extremity=st.booleans(),
        left_lower_extremity=st.booleans(),
        right_lower_extremity=st.booleans(),
        perineum=st.booleans(),
    )
)
def test_tbsa_bounds(params):
    """
    Property-based test: TBSA Rule of Nines must always return a percentage
    between 0 and 100 across all boolean permutations of body regions.
    """
    result = calculate_tbsa(params)
    assert result.value is not None
    assert isinstance(result.value, float)
    assert 0.0 <= result.value <= 100.0
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "TBSA" in result.interpretation or "No burn areas selected" in result.interpretation


@given(
    st.builds(
        EPDSParams,
        laugh=st.integers(min_value=0, max_value=3),
        enjoyment=st.integers(min_value=0, max_value=3),
        self_blame=st.integers(min_value=0, max_value=3),
        anxious=st.integers(min_value=0, max_value=3),
        scared=st.integers(min_value=0, max_value=3),
        things_on_top=st.integers(min_value=0, max_value=3),
        difficulty_sleeping=st.integers(min_value=0, max_value=3),
        sad=st.integers(min_value=0, max_value=3),
        crying=st.integers(min_value=0, max_value=3),
        self_harm=st.integers(min_value=0, max_value=3),
    )
)
def test_epds_bounds(params):
    """
    Property-based test: EPDS must always return 0-30 across all valid
    item value permutations.
    """
    result = calculate_epds(params)
    assert result.value is not None
    assert 0 <= result.value <= 30
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "EPDS" in result.interpretation


@given(
    st.builds(
        ClinicalFrailtyParams,
        frailty_level=st.integers(min_value=1, max_value=9),
    )
)
def test_clinical_frailty_bounds(params):
    """
    Property-based test: Clinical Frailty Scale must always return a score
    between 1 and 9 across all valid frailty level inputs.
    """
    result = calculate_clinical_frailty(params)
    assert result.value is not None
    assert 1 <= result.value <= 9
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "Clinical Frailty Scale" in result.interpretation


@given(
    st.builds(
        CAGEParams,
        cut_down=st.booleans(),
        annoyed=st.booleans(),
        guilty=st.booleans(),
        eye_opener=st.booleans(),
    )
)
def test_cage_bounds(params):
    """
    Property-based test: CAGE score must always return 0-4
    across all 16 boolean permutations.
    """
    result = calculate_cage(params)
    assert result.value is not None
    assert 0 <= result.value <= 4
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "CAGE score is" in result.interpretation


@given(
    age=st.integers(min_value=18, max_value=110),
    is_female=st.booleans(),
    nursing_home_resident=st.booleans(),
    neoplastic_disease=st.booleans(),
    liver_disease=st.booleans(),
    congestive_heart_failure=st.booleans(),
    cerebrovascular_disease=st.booleans(),
    renal_disease=st.booleans(),
    altered_mental_status=st.booleans(),
    respiratory_rate=st.integers(min_value=8, max_value=60),
    systolic_bp=st.integers(min_value=40, max_value=250),
    temperature_celsius=st.floats(min_value=30.0, max_value=43.0),
    pulse=st.integers(min_value=30, max_value=200),
    arterial_ph=st.one_of(st.none(), st.floats(min_value=6.5, max_value=8.0)),
    bun=st.one_of(st.none(), st.floats(min_value=0.0, max_value=200.0)),
    sodium=st.one_of(st.none(), st.floats(min_value=90.0, max_value=200.0)),
    glucose=st.one_of(st.none(), st.floats(min_value=0.0, max_value=1000.0)),
    hematocrit=st.one_of(st.none(), st.floats(min_value=5.0, max_value=80.0)),
    pao2=st.one_of(st.none(), st.floats(min_value=10.0, max_value=600.0)),
    pleural_effusion=st.booleans(),
)
def test_psi_port_bounds(
    age,
    is_female,
    nursing_home_resident,
    neoplastic_disease,
    liver_disease,
    congestive_heart_failure,
    cerebrovascular_disease,
    renal_disease,
    altered_mental_status,
    respiratory_rate,
    systolic_bp,
    temperature_celsius,
    pulse,
    arterial_ph,
    bun,
    sodium,
    glucose,
    hematocrit,
    pao2,
    pleural_effusion,
):
    """
    Property-based test: PSI/PORT score must always return either 0 (Class I)
    or a positive integer (Classes II-V) across all valid clinical input combinations.
    The maximum theoretical score is bounded by age + all possible point additions.
    """
    params = PSIPortParams(
        age=age,
        is_female=is_female,
        nursing_home_resident=nursing_home_resident,
        neoplastic_disease=neoplastic_disease,
        liver_disease=liver_disease,
        congestive_heart_failure=congestive_heart_failure,
        cerebrovascular_disease=cerebrovascular_disease,
        renal_disease=renal_disease,
        altered_mental_status=altered_mental_status,
        respiratory_rate=respiratory_rate,
        systolic_bp=systolic_bp,
        temperature_celsius=temperature_celsius,
        pulse=pulse,
        arterial_ph=arterial_ph,
        bun=bun,
        sodium=sodium,
        glucose=glucose,
        hematocrit=hematocrit,
        pao2=pao2,
        pleural_effusion=pleural_effusion,
    )
    result = calculate_psi_port(params)
    assert result.value is not None
    assert isinstance(result.value, int)
    # Class I returns 0; Class II-V returns a positive score.
    # Max theoretical: 110 (age) + 10 (NH) + 30+20+10+10+10 (comorbid)
    #   + 20+20+20+15+10 (PE) + 30+20+20+10+10+10+10 (labs) = 395
    assert 0 <= result.value <= 400
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "PSI/PORT" in result.interpretation


@given(
    st.builds(
        IPSSParams,
        incomplete_emptying=st.integers(min_value=0, max_value=5),
        frequency=st.integers(min_value=0, max_value=5),
        intermittency=st.integers(min_value=0, max_value=5),
        urgency=st.integers(min_value=0, max_value=5),
        weak_stream=st.integers(min_value=0, max_value=5),
        straining=st.integers(min_value=0, max_value=5),
        nocturia=st.integers(min_value=0, max_value=5),
        quality_of_life=st.one_of(st.none(), st.integers(min_value=0, max_value=6)),
    )
)
def test_ipss_bounds(params):
    """
    Property-based test: No matter the combinations of inputs,
    IPSS must always return a score between 0 and 35 points.
    """
    result = calculate_ipss(params)
    assert result.value is not None
    assert 0 <= result.value <= 35
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "IPSS" in result.interpretation


@given(
    st.builds(
        MASCCParams,
        burden_of_illness=st.sampled_from(list(BurdenOfIllness)),
        hypotension=st.booleans(),
        active_copd=st.booleans(),
        cancer_type=st.sampled_from(list(CancerType)),
        dehydration=st.booleans(),
        outpatient_status=st.booleans(),
        age=st.integers(min_value=18, max_value=120),
    )
)
def test_mascc_bounds(params):
    """
    Property-based test: No matter the combinations of inputs,
    MASCC Risk Index must always return a score between 0 and 26 points.
    """
    result = calculate_mascc(params)
    assert result.value is not None
    assert 0 <= result.value <= 26
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "MASCC Risk Index is" in result.interpretation


@given(
    st.builds(
        NaranjoParams,
        previous_conclusive_reports=st.sampled_from(list(NaranjoResponse)),
        event_after_drug=st.sampled_from(list(NaranjoResponse)),
        improvement_on_discontinuation=st.sampled_from(list(NaranjoResponse)),
        reappearance_on_rechallenge=st.sampled_from(list(NaranjoResponse)),
        alternative_causes=st.sampled_from(list(NaranjoResponse)),
        reaction_with_placebo=st.sampled_from(list(NaranjoResponse)),
        drug_in_toxic_concentration=st.sampled_from(list(NaranjoResponse)),
        severity_dose_related=st.sampled_from(list(NaranjoResponse)),
        similar_prior_reaction=st.sampled_from(list(NaranjoResponse)),
        confirmed_by_objective_evidence=st.sampled_from(list(NaranjoResponse)),
    )
)
def test_naranjo_bounds(params):
    """
    Property-based test: No matter the combinations of inputs,
    Naranjo ADR Probability Scale must always return a score between -4 and +13 points.
    """
    result = calculate_naranjo(params)
    assert result.value is not None
    assert -4 <= result.value <= 13
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "Naranjo ADR Probability Scale score is" in result.interpretation


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
def test_ciwa_ar_bounds(params):
    """
    Property-based test: No matter the combinations of inputs,
    CIWA-Ar must always return a score between 0 and 67 points.
    """
    result = calculate_ciwa_ar(params)
    assert result.value is not None
    assert 0 <= result.value <= 67
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "CIWA-Ar score is" in result.interpretation


@given(
    st.builds(
        RumackMatthewParams,
        serum_acetaminophen=st.floats(min_value=0.0, max_value=1000.0),
        hours_since_ingestion=st.floats(min_value=0.0, max_value=72.0),
    )
)
def test_rumack_matthew_bounds(params):
    """
    Property-based test: Rumack-Matthew nomogram must always return a valid
    result with the serum level as the value, a non-empty interpretation,
    and valid evidence across all plausible input combinations.
    """
    result = calculate_rumack_matthew(params)
    assert result.value is not None
    assert result.value == params.serum_acetaminophen
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert result.evidence.source_doi == "10.1542/peds.55.6.871"
    assert result.fhir_code is None


@given(
    st.builds(
        MEWSParams,
        systolic_bp=st.integers(min_value=30, max_value=300),
        heart_rate=st.integers(min_value=10, max_value=250),
        respiratory_rate=st.integers(min_value=1, max_value=60),
        temperature=st.floats(min_value=30.0, max_value=43.0),
        avpu=st.sampled_from(list(AVPULevel)),
    )
)
def test_mews_bounds(params):
    """
    Property-based test: No matter the combinations of inputs,
    MEWS must always return a score between 0 and 14 points.
    """
    result = calculate_mews(params)
    assert result.value is not None
    assert 0 <= result.value <= 14
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "MEWS is" in result.interpretation


@given(
    st.builds(
        COWSParams,
        resting_pulse_rate=st.sampled_from([0, 1, 2, 4]),
        sweating=st.sampled_from([0, 1, 2, 3, 4]),
        restlessness=st.sampled_from([0, 1, 3, 5]),
        pupil_size=st.sampled_from([0, 1, 2, 5]),
        bone_or_joint_aches=st.sampled_from([0, 1, 2, 4]),
        runny_nose_or_tearing=st.sampled_from([0, 1, 2, 4]),
        gi_upset=st.sampled_from([0, 1, 2, 3, 5]),
        tremor=st.sampled_from([0, 1, 2, 4]),
        yawning=st.sampled_from([0, 1, 2, 4]),
        anxiety_or_irritability=st.sampled_from([0, 1, 2, 4]),
        gooseflesh_skin=st.sampled_from([0, 3, 5]),
    )
)
def test_cows_bounds(params):
    """
    Property-based test: No matter the combinations of valid COWS item scores,
    COWS must always return a score between 0 and 48 points.
    """
    result = calculate_cows(params)
    assert result.value is not None
    assert 0 <= result.value <= 48
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "COWS total score is" in result.interpretation


@given(
    st.builds(
        AIMS65Params,
        albumin_below_3=st.booleans(),
        inr_above_1_5=st.booleans(),
        altered_mental_status=st.booleans(),
        systolic_bp_90_or_less=st.booleans(),
        age_65_or_older=st.booleans(),
    )
)
def test_aims65_bounds(params):
    """
    Property-based test: No matter the combinations of boolean inputs,
    AIMS65 must always return a score between 0 and 5 points.
    """
    result = calculate_aims65(params)
    assert result.value is not None
    assert 0 <= result.value <= 5
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "AIMS65 Score is" in result.interpretation


@given(
    st.builds(
        STOPBangParams,
        snoring=st.booleans(),
        tired=st.booleans(),
        observed_apnea=st.booleans(),
        high_blood_pressure=st.booleans(),
        bmi_over_35=st.booleans(),
        age_over_50=st.booleans(),
        neck_circumference_over_40=st.booleans(),
        male_gender=st.booleans(),
    )
)
def test_stop_bang_bounds(params):
    """
    Property-based test: No matter the combinations of boolean inputs,
    STOP-Bang must always return a score between 0 and 8 points.
    """
    result = calculate_stop_bang(params)
    assert result.value is not None
    assert 0 <= result.value <= 8
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "STOP-Bang score is" in result.interpretation


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
def test_lrinec_bounds(params):
    """
    Property-based test: No matter the combinations of lab values,
    LRINEC must always return a score between 0 and 13 points.
    """
    result = calculate_lrinec(params)
    assert result.value is not None
    assert 0 <= result.value <= 13
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "LRINEC score is" in result.interpretation


@given(
    st.builds(
        RASSParams,
        score=st.integers(min_value=-5, max_value=4),
    )
)
def test_rass_bounds(params):
    """
    Property-based test: No matter the valid input score,
    RASS must always return a score between -5 and +4 matching the input.
    """
    result = calculate_rass(params)
    assert result.value is not None
    assert -5 <= result.value <= 4
    assert result.value == params.score
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "RASS" in result.interpretation


@given(
    st.builds(
        PediatricGCSParams,
        eye_response=st.integers(min_value=1, max_value=4),
        verbal_response=st.integers(min_value=1, max_value=5),
        motor_response=st.integers(min_value=1, max_value=6),
    )
)
def test_pediatric_gcs_bounds(params):
    """
    Property-based test: No matter the combinations of valid component scores,
    Pediatric GCS must always return a score between 3 and 15 points.
    """
    result = calculate_pediatric_gcs(params)
    assert result.value is not None
    assert type(result.value) == float
    assert 3.0 <= result.value <= 15.0
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "Classification:" in result.interpretation


@given(
    st.builds(
        CAMICUParams,
        rass=st.integers(min_value=-5, max_value=4),
        feature1_acute_onset_or_fluctuating=st.booleans(),
        feature2_inattention_errors=st.integers(min_value=0, max_value=10),
        feature4_disorganized_thinking_errors=st.integers(min_value=0, max_value=5),
    )
)
def test_cam_icu_bounds(params):
    """
    Property-based test: No matter the combinations of valid inputs,
    CAM-ICU must always return value of None (UTA), 0 (negative), or 1 (positive).
    """
    result = calculate_cam_icu(params)
    assert result.value in (None, 0, 1)
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert result.evidence.source_doi == "10.1001/jama.286.21.2703"
    if params.rass <= -4:
        assert result.value is None
    else:
        assert result.value in (0, 1)


@given(
    st.builds(
        PEWSParams,
        age_group=st.sampled_from(list(PEWSAgeGroup)),
        heart_rate=st.integers(min_value=0, max_value=300),
        systolic_bp=st.integers(min_value=0, max_value=300),
        capillary_refill_seconds=st.floats(min_value=0.0, max_value=30.0, allow_nan=False, allow_infinity=False),
        respiratory_rate=st.integers(min_value=0, max_value=120),
        respiratory_effort=st.sampled_from(list(RespiratoryEffort)),
        spo2=st.integers(min_value=0, max_value=100),
        oxygen_therapy=st.sampled_from(["room_air", "lt_4L_or_lt_50pct", "gte_4L_or_gte_50pct"]),
    )
)
def test_pews_bounds(params):
    """
    Property-based test: No matter the combinations of inputs,
    Bedside PEWS must always return a score between 0 and 26 points.
    """
    result = calculate_pews(params)
    assert result.value is not None
    assert 0 <= result.value <= 26
    assert type(result.interpretation) == str
    assert len(result.interpretation) > 0
    assert "Bedside PEWS score is" in result.interpretation

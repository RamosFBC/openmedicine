import pytest
from open_medicine.mcp.calculators.psi_port import calculate_psi_port, PSIPortParams


# ---------------------------------------------------------------------------
# Helper to create default "healthy young male" params (Class I baseline)
# ---------------------------------------------------------------------------
def _base_params(**overrides) -> PSIPortParams:
    """Return a young, healthy male with normal vitals and no comorbidities."""
    defaults = dict(
        age=30,
        is_female=False,
        nursing_home_resident=False,
        neoplastic_disease=False,
        liver_disease=False,
        congestive_heart_failure=False,
        cerebrovascular_disease=False,
        renal_disease=False,
        altered_mental_status=False,
        respiratory_rate=18,
        systolic_bp=120,
        temperature_celsius=37.0,
        pulse=80,
        arterial_ph=None,
        bun=None,
        sodium=None,
        glucose=None,
        hematocrit=None,
        pao2=None,
        pleural_effusion=False,
    )
    defaults.update(overrides)
    return PSIPortParams(**defaults)


# ===========================================================================
# Step 1: Risk Class I (direct assignment via algorithm, no point scoring)
# ===========================================================================

class TestRiskClassI:
    """Test cases for Step 1 Risk Class I assignment."""

    def test_young_healthy_male_class_i(self):
        """30-year-old healthy male with stable vitals -> Class I."""
        result = calculate_psi_port(_base_params())
        assert result.value == 0
        assert "Risk Class I" in result.interpretation
        assert "0.1-0.4%" in result.interpretation
        assert "Outpatient" in result.interpretation

    def test_young_healthy_female_class_i(self):
        """25-year-old healthy female with stable vitals -> Class I."""
        result = calculate_psi_port(_base_params(age=25, is_female=True))
        assert result.value == 0
        assert "Risk Class I" in result.interpretation

    def test_age_50_still_class_i(self):
        """Age exactly 50 still qualifies for Class I."""
        result = calculate_psi_port(_base_params(age=50))
        assert result.value == 0
        assert "Risk Class I" in result.interpretation

    def test_age_51_exits_class_i(self):
        """Age 51 forces step 2 scoring (no longer Class I)."""
        result = calculate_psi_port(_base_params(age=51))
        assert result.value is not None
        assert result.value > 0
        assert result.value != 0  # Not Class I (which returns value=0)

    def test_comorbidity_exits_class_i_neoplastic(self):
        """Neoplastic disease in young patient -> not Class I."""
        result = calculate_psi_port(_base_params(neoplastic_disease=True))
        assert result.value != 0  # Not Class I (which returns value=0)

    def test_comorbidity_exits_class_i_liver(self):
        """Liver disease in young patient -> not Class I."""
        result = calculate_psi_port(_base_params(liver_disease=True))
        assert result.value != 0  # Not Class I (which returns value=0)

    def test_comorbidity_exits_class_i_chf(self):
        """CHF in young patient -> not Class I."""
        result = calculate_psi_port(_base_params(congestive_heart_failure=True))
        assert result.value != 0  # Not Class I (which returns value=0)

    def test_comorbidity_exits_class_i_cerebrovascular(self):
        """Cerebrovascular disease in young patient -> not Class I."""
        result = calculate_psi_port(_base_params(cerebrovascular_disease=True))
        assert result.value != 0  # Not Class I (which returns value=0)

    def test_comorbidity_exits_class_i_renal(self):
        """Renal disease in young patient -> not Class I."""
        result = calculate_psi_port(_base_params(renal_disease=True))
        assert result.value != 0  # Not Class I (which returns value=0)

    def test_altered_mental_status_exits_class_i(self):
        """Altered mental status in young patient -> not Class I."""
        result = calculate_psi_port(_base_params(altered_mental_status=True))
        assert result.value != 0  # Not Class I (which returns value=0)

    def test_tachycardia_exits_class_i(self):
        """Pulse >= 125 in young patient -> not Class I."""
        result = calculate_psi_port(_base_params(pulse=125))
        assert result.value != 0  # Not Class I (which returns value=0)

    def test_pulse_124_stays_class_i(self):
        """Pulse 124 (just below threshold) -> still Class I."""
        result = calculate_psi_port(_base_params(pulse=124))
        assert "Risk Class I" in result.interpretation

    def test_tachypnea_exits_class_i(self):
        """Respiratory rate >= 30 in young patient -> not Class I."""
        result = calculate_psi_port(_base_params(respiratory_rate=30))
        assert result.value != 0  # Not Class I (which returns value=0)

    def test_rr_29_stays_class_i(self):
        """Respiratory rate 29 -> still Class I."""
        result = calculate_psi_port(_base_params(respiratory_rate=29))
        assert "Risk Class I" in result.interpretation

    def test_hypotension_exits_class_i(self):
        """Systolic BP < 90 in young patient -> not Class I."""
        result = calculate_psi_port(_base_params(systolic_bp=89))
        assert result.value != 0  # Not Class I (which returns value=0)

    def test_sbp_90_stays_class_i(self):
        """Systolic BP exactly 90 -> still Class I."""
        result = calculate_psi_port(_base_params(systolic_bp=90))
        assert "Risk Class I" in result.interpretation

    def test_hypothermia_exits_class_i(self):
        """Temperature < 35C in young patient -> not Class I."""
        result = calculate_psi_port(_base_params(temperature_celsius=34.9))
        assert result.value != 0  # Not Class I (which returns value=0)

    def test_temp_35_stays_class_i(self):
        """Temperature exactly 35C -> still Class I."""
        result = calculate_psi_port(_base_params(temperature_celsius=35.0))
        assert "Risk Class I" in result.interpretation

    def test_high_fever_exits_class_i(self):
        """Temperature >= 40C in young patient -> not Class I."""
        result = calculate_psi_port(_base_params(temperature_celsius=40.0))
        assert result.value != 0  # Not Class I (which returns value=0)

    def test_temp_39_9_stays_class_i(self):
        """Temperature 39.9C -> still Class I."""
        result = calculate_psi_port(_base_params(temperature_celsius=39.9))
        assert "Risk Class I" in result.interpretation


# ===========================================================================
# Step 2: Point Scoring and Risk Class II-V
# ===========================================================================

class TestRiskClassII:
    """Test cases for Risk Class II (score <= 70)."""

    def test_51yo_male_no_issues(self):
        """51-year-old healthy male: score = 51 -> Class II."""
        result = calculate_psi_port(_base_params(age=51))
        assert result.value == 51
        assert "Risk Class II" in result.interpretation
        assert "0.6-0.7%" in result.interpretation
        assert "Outpatient" in result.interpretation

    def test_60yo_female_no_issues(self):
        """60-year-old healthy female: score = 60 - 10 = 50 -> Class II."""
        result = calculate_psi_port(_base_params(age=60, is_female=True))
        assert result.value == 50
        assert "Risk Class II" in result.interpretation

    def test_score_exactly_70_is_class_ii(self):
        """70-year-old male: score = 70 -> Class II boundary."""
        result = calculate_psi_port(_base_params(age=70))
        assert result.value == 70
        assert "Risk Class II" in result.interpretation


class TestRiskClassIII:
    """Test cases for Risk Class III (score 71-90)."""

    def test_71yo_male_class_iii(self):
        """71-year-old male: score = 71 -> Class III lower boundary."""
        result = calculate_psi_port(_base_params(age=71))
        assert result.value == 71
        assert "Risk Class III" in result.interpretation
        assert "0.9-2.8%" in result.interpretation

    def test_score_90_is_class_iii(self):
        """80-year-old male with nursing home: 80 + 10 = 90 -> Class III upper boundary."""
        result = calculate_psi_port(_base_params(age=80, nursing_home_resident=True))
        assert result.value == 90
        assert "Risk Class III" in result.interpretation


class TestRiskClassIV:
    """Test cases for Risk Class IV (score 91-130)."""

    def test_score_91_is_class_iv(self):
        """81-year-old male with nursing home: 81 + 10 = 91 -> Class IV lower boundary."""
        result = calculate_psi_port(_base_params(age=81, nursing_home_resident=True))
        assert result.value == 91
        assert "Risk Class IV" in result.interpretation
        assert "4-10%" in result.interpretation
        assert "Inpatient" in result.interpretation

    def test_score_130_is_class_iv(self):
        """70-year-old male with neoplastic disease + liver disease + CHF:
        70 + 30 + 20 + 10 = 130 -> Class IV upper boundary."""
        result = calculate_psi_port(_base_params(
            age=70,
            neoplastic_disease=True,
            liver_disease=True,
            congestive_heart_failure=True,
        ))
        assert result.value == 130
        assert "Risk Class IV" in result.interpretation


class TestRiskClassV:
    """Test cases for Risk Class V (score > 130)."""

    def test_score_131_is_class_v(self):
        """Score 131 -> Class V lower boundary."""
        # 71-year-old male + neoplastic(30) + liver(20) + CHF(10) = 71+60=131
        result = calculate_psi_port(_base_params(
            age=71,
            neoplastic_disease=True,
            liver_disease=True,
            congestive_heart_failure=True,
        ))
        assert result.value == 131
        assert "Risk Class V" in result.interpretation
        assert "27%" in result.interpretation
        assert "ICU" in result.interpretation

    def test_maximum_score_scenario(self):
        """All criteria present on an elderly male -> very high Class V score."""
        params = PSIPortParams(
            age=90,
            is_female=False,
            nursing_home_resident=True,       # +10
            neoplastic_disease=True,          # +30
            liver_disease=True,               # +20
            congestive_heart_failure=True,     # +10
            cerebrovascular_disease=True,      # +10
            renal_disease=True,               # +10
            altered_mental_status=True,        # +20
            respiratory_rate=35,              # +20
            systolic_bp=80,                   # +20
            temperature_celsius=34.0,         # +15
            pulse=130,                        # +10
            arterial_ph=7.20,                 # +30
            bun=50.0,                         # +20
            sodium=125.0,                     # +20
            glucose=300.0,                    # +10
            hematocrit=25.0,                  # +10
            pao2=50.0,                        # +10
            pleural_effusion=True,            # +10
        )
        result = calculate_psi_port(params)
        # Expected: 90 (age) + 10 + 30 + 20 + 10 + 10 + 10 + 20 + 20 + 20 + 15 + 10
        #         + 30 + 20 + 20 + 10 + 10 + 10 + 10 = 375
        expected = 90 + 10 + 30 + 20 + 10 + 10 + 10 + 20 + 20 + 20 + 15 + 10 + 30 + 20 + 20 + 10 + 10 + 10 + 10
        assert result.value == expected
        assert result.value == 375
        assert "Risk Class V" in result.interpretation


# ===========================================================================
# Demographic Point Calculations
# ===========================================================================

class TestDemographicScoring:
    """Verify demographic point assignments."""

    def test_male_age_equals_score(self):
        """Male patient age = age in points."""
        result = calculate_psi_port(_base_params(age=65))
        assert result.value == 65

    def test_female_gets_age_minus_10(self):
        """Female patient gets age - 10 in points."""
        result = calculate_psi_port(_base_params(age=65, is_female=True))
        assert result.value == 55

    def test_nursing_home_adds_10(self):
        """Nursing home adds 10 points."""
        result_no_nh = calculate_psi_port(_base_params(age=60))
        result_nh = calculate_psi_port(_base_params(age=60, nursing_home_resident=True))
        assert result_nh.value - result_no_nh.value == 10


# ===========================================================================
# Comorbidity Point Calculations
# ===========================================================================

class TestComorbidityScoring:
    """Verify each comorbidity's point contribution."""

    def test_neoplastic_adds_30(self):
        """Neoplastic disease adds 30 points."""
        result_base = calculate_psi_port(_base_params(age=55))
        result_neo = calculate_psi_port(_base_params(age=55, neoplastic_disease=True))
        assert result_neo.value - result_base.value == 30

    def test_liver_adds_20(self):
        """Liver disease adds 20 points."""
        result_base = calculate_psi_port(_base_params(age=55))
        result_liver = calculate_psi_port(_base_params(age=55, liver_disease=True))
        assert result_liver.value - result_base.value == 20

    def test_chf_adds_10(self):
        """CHF adds 10 points."""
        result_base = calculate_psi_port(_base_params(age=55))
        result_chf = calculate_psi_port(_base_params(age=55, congestive_heart_failure=True))
        assert result_chf.value - result_base.value == 10

    def test_cerebrovascular_adds_10(self):
        """Cerebrovascular disease adds 10 points."""
        result_base = calculate_psi_port(_base_params(age=55))
        result_cvd = calculate_psi_port(_base_params(age=55, cerebrovascular_disease=True))
        assert result_cvd.value - result_base.value == 10

    def test_renal_adds_10(self):
        """Renal disease adds 10 points."""
        result_base = calculate_psi_port(_base_params(age=55))
        result_renal = calculate_psi_port(_base_params(age=55, renal_disease=True))
        assert result_renal.value - result_base.value == 10


# ===========================================================================
# Physical Exam Point Calculations
# ===========================================================================

class TestPhysicalExamScoring:
    """Verify physical exam finding point contributions."""

    def test_altered_mental_status_adds_20(self):
        """Altered mental status adds 20 points."""
        result_base = calculate_psi_port(_base_params(age=55))
        result_ams = calculate_psi_port(_base_params(age=55, altered_mental_status=True))
        assert result_ams.value - result_base.value == 20

    def test_rr_30_adds_20(self):
        """Respiratory rate >= 30 adds 20 points."""
        result_base = calculate_psi_port(_base_params(age=55))
        result_rr = calculate_psi_port(_base_params(age=55, respiratory_rate=30))
        assert result_rr.value - result_base.value == 20

    def test_rr_29_adds_0(self):
        """Respiratory rate 29 does not add points."""
        result_base = calculate_psi_port(_base_params(age=55))
        result_rr = calculate_psi_port(_base_params(age=55, respiratory_rate=29))
        assert result_rr.value == result_base.value

    def test_sbp_89_adds_20(self):
        """Systolic BP < 90 adds 20 points."""
        result_base = calculate_psi_port(_base_params(age=55))
        result_sbp = calculate_psi_port(_base_params(age=55, systolic_bp=89))
        assert result_sbp.value - result_base.value == 20

    def test_sbp_90_adds_0(self):
        """Systolic BP 90 does not add points."""
        result_base = calculate_psi_port(_base_params(age=55))
        result_sbp = calculate_psi_port(_base_params(age=55, systolic_bp=90))
        assert result_sbp.value == result_base.value

    def test_temp_below_35_adds_15(self):
        """Temperature < 35 adds 15 points."""
        result_base = calculate_psi_port(_base_params(age=55))
        result_temp = calculate_psi_port(_base_params(age=55, temperature_celsius=34.5))
        assert result_temp.value - result_base.value == 15

    def test_temp_40_or_above_adds_15(self):
        """Temperature >= 40 adds 15 points."""
        result_base = calculate_psi_port(_base_params(age=55))
        result_temp = calculate_psi_port(_base_params(age=55, temperature_celsius=40.0))
        assert result_temp.value - result_base.value == 15

    def test_temp_39_9_adds_0(self):
        """Temperature 39.9 does not add points."""
        result_base = calculate_psi_port(_base_params(age=55))
        result_temp = calculate_psi_port(_base_params(age=55, temperature_celsius=39.9))
        assert result_temp.value == result_base.value

    def test_pulse_125_adds_10(self):
        """Pulse >= 125 adds 10 points."""
        result_base = calculate_psi_port(_base_params(age=55))
        result_pulse = calculate_psi_port(_base_params(age=55, pulse=125))
        assert result_pulse.value - result_base.value == 10

    def test_pulse_124_adds_0(self):
        """Pulse 124 does not add points."""
        result_base = calculate_psi_port(_base_params(age=55))
        result_pulse = calculate_psi_port(_base_params(age=55, pulse=124))
        assert result_pulse.value == result_base.value


# ===========================================================================
# Laboratory Finding Point Calculations
# ===========================================================================

class TestLaboratoryScoring:
    """Verify laboratory finding point contributions."""

    def test_ph_below_7_35_adds_30(self):
        """Arterial pH < 7.35 adds 30 points."""
        result_base = calculate_psi_port(_base_params(age=55))
        result_ph = calculate_psi_port(_base_params(age=55, arterial_ph=7.30))
        assert result_ph.value - result_base.value == 30

    def test_ph_7_35_adds_0(self):
        """Arterial pH 7.35 does not add points."""
        result_base = calculate_psi_port(_base_params(age=55))
        result_ph = calculate_psi_port(_base_params(age=55, arterial_ph=7.35))
        assert result_ph.value == result_base.value

    def test_ph_none_adds_0(self):
        """Arterial pH not provided adds 0 points."""
        result_base = calculate_psi_port(_base_params(age=55))
        result_ph = calculate_psi_port(_base_params(age=55, arterial_ph=None))
        assert result_ph.value == result_base.value

    def test_bun_30_or_above_adds_20(self):
        """BUN >= 30 adds 20 points."""
        result_base = calculate_psi_port(_base_params(age=55))
        result_bun = calculate_psi_port(_base_params(age=55, bun=30.0))
        assert result_bun.value - result_base.value == 20

    def test_bun_29_adds_0(self):
        """BUN 29 does not add points."""
        result_base = calculate_psi_port(_base_params(age=55))
        result_bun = calculate_psi_port(_base_params(age=55, bun=29.0))
        assert result_bun.value == result_base.value

    def test_sodium_below_130_adds_20(self):
        """Sodium < 130 adds 20 points."""
        result_base = calculate_psi_port(_base_params(age=55))
        result_na = calculate_psi_port(_base_params(age=55, sodium=129.0))
        assert result_na.value - result_base.value == 20

    def test_sodium_130_adds_0(self):
        """Sodium 130 does not add points."""
        result_base = calculate_psi_port(_base_params(age=55))
        result_na = calculate_psi_port(_base_params(age=55, sodium=130.0))
        assert result_na.value == result_base.value

    def test_glucose_250_or_above_adds_10(self):
        """Glucose >= 250 adds 10 points."""
        result_base = calculate_psi_port(_base_params(age=55))
        result_glu = calculate_psi_port(_base_params(age=55, glucose=250.0))
        assert result_glu.value - result_base.value == 10

    def test_glucose_249_adds_0(self):
        """Glucose 249 does not add points."""
        result_base = calculate_psi_port(_base_params(age=55))
        result_glu = calculate_psi_port(_base_params(age=55, glucose=249.0))
        assert result_glu.value == result_base.value

    def test_hematocrit_below_30_adds_10(self):
        """Hematocrit < 30% adds 10 points."""
        result_base = calculate_psi_port(_base_params(age=55))
        result_hct = calculate_psi_port(_base_params(age=55, hematocrit=29.0))
        assert result_hct.value - result_base.value == 10

    def test_hematocrit_30_adds_0(self):
        """Hematocrit 30% does not add points."""
        result_base = calculate_psi_port(_base_params(age=55))
        result_hct = calculate_psi_port(_base_params(age=55, hematocrit=30.0))
        assert result_hct.value == result_base.value

    def test_pao2_below_60_adds_10(self):
        """PaO2 < 60 adds 10 points."""
        result_base = calculate_psi_port(_base_params(age=55))
        result_pao2 = calculate_psi_port(_base_params(age=55, pao2=59.0))
        assert result_pao2.value - result_base.value == 10

    def test_pao2_60_adds_0(self):
        """PaO2 60 does not add points."""
        result_base = calculate_psi_port(_base_params(age=55))
        result_pao2 = calculate_psi_port(_base_params(age=55, pao2=60.0))
        assert result_pao2.value == result_base.value

    def test_pleural_effusion_adds_10(self):
        """Pleural effusion adds 10 points."""
        result_base = calculate_psi_port(_base_params(age=55))
        result_pe = calculate_psi_port(_base_params(age=55, pleural_effusion=True))
        assert result_pe.value - result_base.value == 10

    def test_all_labs_none_assumed_normal(self):
        """All lab values as None add 0 points (assumed normal)."""
        result = calculate_psi_port(_base_params(age=55))
        # Score should be just 55 (age only)
        assert result.value == 55


# ===========================================================================
# Cross-Validation: Published Clinical Scenarios
# ===========================================================================

class TestClinicalScenarios:
    """Cross-validation with known clinical scenarios from literature."""

    def test_classic_low_risk_scenario(self):
        """45-year-old otherwise healthy female, mild pneumonia -> Class I."""
        params = PSIPortParams(
            age=45,
            is_female=True,
            nursing_home_resident=False,
            neoplastic_disease=False,
            liver_disease=False,
            congestive_heart_failure=False,
            cerebrovascular_disease=False,
            renal_disease=False,
            altered_mental_status=False,
            respiratory_rate=22,
            systolic_bp=115,
            temperature_celsius=38.5,
            pulse=95,
        )
        result = calculate_psi_port(params)
        assert result.value == 0
        assert "Risk Class I" in result.interpretation

    def test_moderate_elderly_patient(self):
        """75-year-old male with CHF, BUN 35, and pleural effusion.
        Score = 75 (age) + 10 (CHF) + 20 (BUN) + 10 (pleural effusion) = 115 -> Class IV."""
        params = PSIPortParams(
            age=75,
            is_female=False,
            nursing_home_resident=False,
            neoplastic_disease=False,
            liver_disease=False,
            congestive_heart_failure=True,
            cerebrovascular_disease=False,
            renal_disease=False,
            altered_mental_status=False,
            respiratory_rate=24,
            systolic_bp=110,
            temperature_celsius=38.8,
            pulse=100,
            bun=35.0,
            pleural_effusion=True,
        )
        result = calculate_psi_port(params)
        assert result.value == 115
        assert "Risk Class IV" in result.interpretation

    def test_severe_nursing_home_patient(self):
        """82-year-old female nursing home resident with neoplastic disease, altered mental
        status, low BP, tachycardia, acidosis, and low PaO2.
        Score = 72 (82-10) + 10 (NH) + 30 (neoplastic) + 20 (AMS) + 20 (SBP<90)
              + 10 (pulse>=125) + 30 (pH<7.35) + 10 (PaO2<60) = 202 -> Class V."""
        params = PSIPortParams(
            age=82,
            is_female=True,
            nursing_home_resident=True,
            neoplastic_disease=True,
            liver_disease=False,
            congestive_heart_failure=False,
            cerebrovascular_disease=False,
            renal_disease=False,
            altered_mental_status=True,
            respiratory_rate=22,
            systolic_bp=85,
            temperature_celsius=37.5,
            pulse=130,
            arterial_ph=7.25,
            pao2=55.0,
        )
        result = calculate_psi_port(params)
        assert result.value == 202
        assert "Risk Class V" in result.interpretation


# ===========================================================================
# Evidence and FHIR Metadata Verification
# ===========================================================================

class TestEvidenceAndFHIR:
    """Verify DOI, evidence, and FHIR code are correctly set."""

    def test_evidence_doi(self):
        """DOI matches Fine et al. NEJM 1997."""
        result = calculate_psi_port(_base_params())
        assert result.evidence.source_doi == "10.1056/NEJM199701233360402"

    def test_evidence_level(self):
        """Evidence level is Derivation & Validation Study."""
        result = calculate_psi_port(_base_params())
        assert result.evidence.level == "Derivation & Validation Study"

    def test_evidence_description(self):
        """Evidence description mentions Fine et al."""
        result = calculate_psi_port(_base_params())
        assert "Fine" in result.evidence.description
        assert "N Engl J Med" in result.evidence.description

    def test_fhir_code(self):
        """FHIR code is set correctly."""
        result = calculate_psi_port(_base_params())
        assert result.fhir_code == "LP419467-4"
        assert result.fhir_system == "http://loinc.org"

    def test_fhir_display(self):
        """FHIR display includes PSI/PORT."""
        result = calculate_psi_port(_base_params())
        assert "PSI" in result.fhir_display
        assert "PORT" in result.fhir_display

    def test_evidence_consistent_across_classes(self):
        """Evidence DOI is the same regardless of risk class."""
        result_class_i = calculate_psi_port(_base_params())
        result_class_v = calculate_psi_port(_base_params(
            age=90, neoplastic_disease=True, liver_disease=True,
            congestive_heart_failure=True, cerebrovascular_disease=True,
            renal_disease=True, altered_mental_status=True,
        ))
        assert result_class_i.evidence.source_doi == result_class_v.evidence.source_doi


# ===========================================================================
# Edge Cases
# ===========================================================================

class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_young_female_with_negative_score_component(self):
        """Very young female: age 18, female (-10): 18 - 10 = 8 -> Class II.
        (Not Class I because she has a comorbidity forcing step 2.)"""
        result = calculate_psi_port(_base_params(
            age=18, is_female=True, congestive_heart_failure=True
        ))
        # 18 - 10 + 10 (CHF) = 18
        assert result.value == 18
        assert "Risk Class II" in result.interpretation

    def test_all_labs_abnormal(self):
        """All lab values are abnormal -> each contributes points."""
        result = calculate_psi_port(_base_params(
            age=55,
            arterial_ph=7.20,     # +30
            bun=50.0,             # +20
            sodium=120.0,         # +20
            glucose=300.0,        # +10
            hematocrit=25.0,      # +10
            pao2=50.0,            # +10
            pleural_effusion=True # +10
        ))
        # 55 (age) + 30 + 20 + 20 + 10 + 10 + 10 + 10 = 165
        assert result.value == 165
        assert "Risk Class V" in result.interpretation

    def test_labs_at_threshold_no_points(self):
        """Labs at exact threshold values that do not trigger points."""
        result = calculate_psi_port(_base_params(
            age=55,
            arterial_ph=7.35,     # exactly 7.35 -> no points
            bun=29.9,             # < 30 -> no points
            sodium=130.0,         # exactly 130 -> no points
            glucose=249.0,        # < 250 -> no points
            hematocrit=30.0,      # exactly 30 -> no points
            pao2=60.0,            # exactly 60 -> no points
        ))
        assert result.value == 55  # age only

    def test_interpretation_always_has_content(self):
        """Interpretation is always a non-empty string for any input."""
        for age in [20, 55, 80, 100]:
            result = calculate_psi_port(_base_params(age=age))
            assert isinstance(result.interpretation, str)
            assert len(result.interpretation) > 0

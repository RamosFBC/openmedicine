import pytest
from hypothesis import given, strategies as st, settings
from open_medicine.mcp.calculators.apache2 import (
    calculate_apache2,
    APACHE2Params,
    AdmissionType,
    _score_temperature,
    _score_map,
    _score_heart_rate,
    _score_respiratory_rate,
    _score_oxygenation,
    _score_arterial_ph,
    _score_sodium,
    _score_potassium,
    _score_creatinine,
    _score_hematocrit,
    _score_wbc,
    _score_gcs,
    _score_age,
    _score_chronic_health,
)


# ---------------------------------------------------------------------------
# Helper: build a "normal patient" params dict to use as baseline
# ---------------------------------------------------------------------------
def _normal_params(**overrides):
    """Build APACHE2Params with all-normal values, allowing overrides."""
    defaults = dict(
        temperature=37.0,
        mean_arterial_pressure=80.0,
        heart_rate=80,
        respiratory_rate=16,
        fio2=0.21,
        pao2=90.0,
        paco2=None,
        arterial_ph=7.40,
        serum_sodium=140.0,
        serum_potassium=4.0,
        serum_creatinine=1.0,
        acute_renal_failure=False,
        hematocrit=40.0,
        white_blood_cell_count=8.0,
        gcs=15,
        age=40,
        admission_type=AdmissionType.NONOPERATIVE,
        severe_organ_insufficiency_or_immunocompromised=False,
    )
    defaults.update(overrides)
    return APACHE2Params(**defaults)


# ===========================================================================
# TIER 1: Deterministic Unit Tests
# ===========================================================================


class TestMinimumScore:
    """Test the lowest possible score: all normal values, young, no chronic health."""

    def test_all_normal(self):
        params = _normal_params()
        result = calculate_apache2(params)
        # All physiology normal -> APS=0, age 40 -> 0 pts, no chronic health -> 0
        assert result.value == 0
        assert "APACHE II score is 0" in result.interpretation
        assert "Low severity" in result.interpretation

    def test_gcs_15_contributes_zero(self):
        """GCS = 15 => 15 - 15 = 0 points."""
        assert _score_gcs(15) == 0

    def test_age_under_44_zero(self):
        assert _score_age(40) == 0
        assert _score_age(44) == 0


class TestMaximumScore:
    """Test the highest possible score: all worst values, oldest, worst chronic health."""

    def test_maximum_theoretical_score(self):
        """Maximum APACHE II = 71:
        APS max=60 (12 vars * 4 each max, plus creatinine doubled = 8 gives 64,
        but GCS max is 12, not 4*... let's compute).

        Actually:
        - 11 physiologic variables each max 4 pts = 44
        - Creatinine with ARF: 4 * 2 = 8
        - GCS: 15 - 3 = 12
        = 44 + 8 + 12 = 64 (APS theoretical max is higher than 60 due to GCS and doubled creatinine)
        Wait, the official max APS is described as allowing up to 60.
        GCS contributes 15 - GCS = max 12.
        11 other variables contribute 4 each = 44.
        Creatinine doubled = 8.
        Total APS = 44 + 8 + 12 = 64? No, creatinine is one of the 11.
        Correct: 10 other vars (excl creatinine & GCS) * 4 = 40
        + creatinine with ARF = 8
        + GCS = 12
        = 60 (APS max). That makes sense.

        Age max = 6
        Chronic health max = 5
        Total max = 60 + 6 + 5 = 71.
        """
        params = _normal_params(
            temperature=42.0,           # +4
            mean_arterial_pressure=170,  # +4
            heart_rate=190,             # +4
            respiratory_rate=55,        # +4
            fio2=1.0,                   # FiO2 >= 0.5, use A-aDO2
            pao2=50.0,                  # Low PaO2 -> high A-aDO2
            paco2=20.0,                 # A-aDO2 = 1.0*713 - 20/0.8 - 50 = 713 - 25 - 50 = 638 -> +4
            arterial_ph=7.0,            # +4
            serum_sodium=185.0,         # +4
            serum_potassium=8.0,        # +4
            serum_creatinine=5.0,       # +4, doubled with ARF -> +8
            acute_renal_failure=True,
            hematocrit=65.0,            # +4
            white_blood_cell_count=50.0,  # +4
            gcs=3,                      # 15-3 = +12
            age=80,                     # +6
            admission_type=AdmissionType.NONOPERATIVE,
            severe_organ_insufficiency_or_immunocompromised=True,  # +5
        )
        result = calculate_apache2(params)
        # APS: 4+4+4+4+4+4+4+4+8+4+4+12 = 60
        # Age: 6, Chronic Health: 5
        # Total: 71
        assert result.value == 71
        assert "APACHE II score is 71" in result.interpretation
        assert "Extremely critical" in result.interpretation


class TestEachPhysiologicVariable:
    """Test each scoring function individually for all threshold boundaries."""

    # --- Temperature ---
    def test_temp_high_4(self):
        assert _score_temperature(41.0) == 4
        assert _score_temperature(42.5) == 4

    def test_temp_high_3(self):
        assert _score_temperature(39.0) == 3
        assert _score_temperature(40.9) == 3

    def test_temp_high_1(self):
        assert _score_temperature(38.5) == 1
        assert _score_temperature(38.9) == 1

    def test_temp_normal_0(self):
        assert _score_temperature(36.0) == 0
        assert _score_temperature(37.0) == 0
        assert _score_temperature(38.4) == 0

    def test_temp_low_1(self):
        assert _score_temperature(34.0) == 1
        assert _score_temperature(35.9) == 1

    def test_temp_low_2(self):
        assert _score_temperature(32.0) == 2
        assert _score_temperature(33.9) == 2

    def test_temp_low_3(self):
        assert _score_temperature(30.0) == 3
        assert _score_temperature(31.9) == 3

    def test_temp_low_4(self):
        assert _score_temperature(29.9) == 4
        assert _score_temperature(25.0) == 4

    # --- Mean Arterial Pressure ---
    def test_map_high_4(self):
        assert _score_map(160) == 4
        assert _score_map(200) == 4

    def test_map_high_3(self):
        assert _score_map(130) == 3
        assert _score_map(159) == 3

    def test_map_high_2(self):
        assert _score_map(110) == 2
        assert _score_map(129) == 2

    def test_map_normal_0(self):
        assert _score_map(70) == 0
        assert _score_map(80) == 0
        assert _score_map(109) == 0

    def test_map_low_2(self):
        assert _score_map(50) == 2
        assert _score_map(69) == 2

    def test_map_low_4(self):
        assert _score_map(49) == 4
        assert _score_map(30) == 4

    # --- Heart Rate ---
    def test_hr_high_4(self):
        assert _score_heart_rate(180) == 4
        assert _score_heart_rate(220) == 4

    def test_hr_high_3(self):
        assert _score_heart_rate(140) == 3
        assert _score_heart_rate(179) == 3

    def test_hr_high_2(self):
        assert _score_heart_rate(110) == 2
        assert _score_heart_rate(139) == 2

    def test_hr_normal_0(self):
        assert _score_heart_rate(70) == 0
        assert _score_heart_rate(80) == 0
        assert _score_heart_rate(109) == 0

    def test_hr_low_2(self):
        assert _score_heart_rate(55) == 2
        assert _score_heart_rate(69) == 2

    def test_hr_low_3(self):
        assert _score_heart_rate(40) == 3
        assert _score_heart_rate(54) == 3

    def test_hr_low_4(self):
        assert _score_heart_rate(39) == 4
        assert _score_heart_rate(20) == 4

    # --- Respiratory Rate ---
    def test_rr_high_4(self):
        assert _score_respiratory_rate(50) == 4
        assert _score_respiratory_rate(60) == 4

    def test_rr_high_3(self):
        assert _score_respiratory_rate(35) == 3
        assert _score_respiratory_rate(49) == 3

    def test_rr_high_1(self):
        assert _score_respiratory_rate(25) == 1
        assert _score_respiratory_rate(34) == 1

    def test_rr_normal_0(self):
        assert _score_respiratory_rate(12) == 0
        assert _score_respiratory_rate(16) == 0
        assert _score_respiratory_rate(24) == 0

    def test_rr_low_1(self):
        assert _score_respiratory_rate(10) == 1
        assert _score_respiratory_rate(11) == 1

    def test_rr_low_2(self):
        assert _score_respiratory_rate(6) == 2
        assert _score_respiratory_rate(9) == 2

    def test_rr_low_4(self):
        assert _score_respiratory_rate(5) == 4
        assert _score_respiratory_rate(2) == 4

    # --- Oxygenation ---
    def test_oxygenation_fio2_low_pao2_normal(self):
        """FiO2 < 0.5, PaO2 > 70 => 0 points."""
        assert _score_oxygenation(0.21, 90.0, None) == 0

    def test_oxygenation_fio2_low_pao2_61_70(self):
        """FiO2 < 0.5, PaO2 61-70 => 1 point."""
        assert _score_oxygenation(0.21, 65.0, None) == 1
        assert _score_oxygenation(0.21, 61.0, None) == 1
        assert _score_oxygenation(0.21, 70.0, None) == 1

    def test_oxygenation_fio2_low_pao2_55_60(self):
        """FiO2 < 0.5, PaO2 55-60 => 3 points."""
        assert _score_oxygenation(0.21, 55.0, None) == 3
        assert _score_oxygenation(0.21, 60.0, None) == 3

    def test_oxygenation_fio2_low_pao2_below_55(self):
        """FiO2 < 0.5, PaO2 < 55 => 4 points."""
        assert _score_oxygenation(0.21, 54.0, None) == 4
        assert _score_oxygenation(0.21, 40.0, None) == 4

    def test_oxygenation_fio2_high_aado2_below_200(self):
        """FiO2 >= 0.5, A-aDO2 < 200 => 0 points.
        A-aDO2 = FiO2*713 - PaCO2/0.8 - PaO2
        FiO2=0.5, PaCO2=40, PaO2=200: 356.5 - 50 - 200 = 106.5 => 0 pts
        """
        assert _score_oxygenation(0.5, 200.0, 40.0) == 0

    def test_oxygenation_fio2_high_aado2_200_349(self):
        """FiO2 >= 0.5, A-aDO2 200-349 => 2 points.
        FiO2=0.6, PaCO2=40, PaO2=50: 427.8 - 50 - 50 = 327.8 => 2 pts
        """
        assert _score_oxygenation(0.6, 50.0, 40.0) == 2

    def test_oxygenation_fio2_high_aado2_350_499(self):
        """FiO2 >= 0.5, A-aDO2 350-499 => 3 points.
        FiO2=0.8, PaCO2=40, PaO2=100: 570.4 - 50 - 100 = 420.4 => 3 pts
        """
        assert _score_oxygenation(0.8, 100.0, 40.0) == 3

    def test_oxygenation_fio2_high_aado2_above_500(self):
        """FiO2 >= 0.5, A-aDO2 >= 500 => 4 points.
        FiO2=1.0, PaCO2=40, PaO2=100: 713 - 50 - 100 = 563 => 4 pts
        """
        assert _score_oxygenation(1.0, 100.0, 40.0) == 4

    def test_oxygenation_fio2_high_no_paco2_fallback(self):
        """FiO2 >= 0.5, PaCO2 not provided => fallback to PaO2 scoring."""
        assert _score_oxygenation(0.5, 90.0, None) == 0
        assert _score_oxygenation(0.5, 65.0, None) == 1
        assert _score_oxygenation(0.5, 55.0, None) == 3
        assert _score_oxygenation(0.5, 40.0, None) == 4

    # --- Arterial pH ---
    def test_ph_high_4(self):
        assert _score_arterial_ph(7.7) == 4
        assert _score_arterial_ph(7.8) == 4

    def test_ph_high_3(self):
        assert _score_arterial_ph(7.6) == 3
        assert _score_arterial_ph(7.69) == 3

    def test_ph_high_1(self):
        assert _score_arterial_ph(7.5) == 1
        assert _score_arterial_ph(7.59) == 1

    def test_ph_normal_0(self):
        assert _score_arterial_ph(7.33) == 0
        assert _score_arterial_ph(7.40) == 0
        assert _score_arterial_ph(7.49) == 0

    def test_ph_low_2(self):
        assert _score_arterial_ph(7.25) == 2
        assert _score_arterial_ph(7.32) == 2

    def test_ph_low_3(self):
        assert _score_arterial_ph(7.15) == 3
        assert _score_arterial_ph(7.24) == 3

    def test_ph_low_4(self):
        assert _score_arterial_ph(7.14) == 4
        assert _score_arterial_ph(7.0) == 4

    # --- Sodium ---
    def test_na_high_4(self):
        assert _score_sodium(180) == 4
        assert _score_sodium(190) == 4

    def test_na_high_3(self):
        assert _score_sodium(160) == 3
        assert _score_sodium(179) == 3

    def test_na_high_2(self):
        assert _score_sodium(155) == 2
        assert _score_sodium(159) == 2

    def test_na_high_1(self):
        assert _score_sodium(150) == 1
        assert _score_sodium(154) == 1

    def test_na_normal_0(self):
        assert _score_sodium(130) == 0
        assert _score_sodium(140) == 0
        assert _score_sodium(149) == 0

    def test_na_low_2(self):
        assert _score_sodium(120) == 2
        assert _score_sodium(129) == 2

    def test_na_low_3(self):
        assert _score_sodium(111) == 3
        assert _score_sodium(119) == 3

    def test_na_low_4(self):
        assert _score_sodium(110) == 4
        assert _score_sodium(100) == 4

    # --- Potassium ---
    def test_k_high_4(self):
        assert _score_potassium(7.0) == 4
        assert _score_potassium(8.0) == 4

    def test_k_high_3(self):
        assert _score_potassium(6.0) == 3
        assert _score_potassium(6.9) == 3

    def test_k_high_1(self):
        assert _score_potassium(5.5) == 1
        assert _score_potassium(5.9) == 1

    def test_k_normal_0(self):
        assert _score_potassium(3.5) == 0
        assert _score_potassium(4.0) == 0
        assert _score_potassium(5.4) == 0

    def test_k_low_1(self):
        assert _score_potassium(3.0) == 1
        assert _score_potassium(3.4) == 1

    def test_k_low_2(self):
        assert _score_potassium(2.5) == 2
        assert _score_potassium(2.9) == 2

    def test_k_low_4(self):
        assert _score_potassium(2.4) == 4
        assert _score_potassium(1.5) == 4

    # --- Creatinine ---
    def test_cr_high_4(self):
        assert _score_creatinine(3.5, False) == 4
        assert _score_creatinine(5.0, False) == 4

    def test_cr_high_3(self):
        assert _score_creatinine(2.0, False) == 3
        assert _score_creatinine(3.4, False) == 3

    def test_cr_high_2(self):
        assert _score_creatinine(1.5, False) == 2
        assert _score_creatinine(1.9, False) == 2

    def test_cr_normal_0(self):
        assert _score_creatinine(0.6, False) == 0
        assert _score_creatinine(1.0, False) == 0
        assert _score_creatinine(1.4, False) == 0

    def test_cr_low_2(self):
        assert _score_creatinine(0.5, False) == 2
        assert _score_creatinine(0.3, False) == 2

    def test_cr_arf_doubles(self):
        """Acute renal failure doubles the creatinine points."""
        assert _score_creatinine(3.5, True) == 8  # 4 * 2
        assert _score_creatinine(2.0, True) == 6  # 3 * 2
        assert _score_creatinine(1.5, True) == 4  # 2 * 2
        assert _score_creatinine(1.0, True) == 0  # 0 * 2 = 0
        assert _score_creatinine(0.5, True) == 4  # 2 * 2

    # --- Hematocrit ---
    def test_hct_high_4(self):
        assert _score_hematocrit(60) == 4
        assert _score_hematocrit(70) == 4

    def test_hct_high_2(self):
        assert _score_hematocrit(50) == 2
        assert _score_hematocrit(59) == 2

    def test_hct_high_1(self):
        assert _score_hematocrit(46) == 1
        assert _score_hematocrit(49) == 1

    def test_hct_normal_0(self):
        assert _score_hematocrit(30) == 0
        assert _score_hematocrit(40) == 0
        assert _score_hematocrit(45) == 0

    def test_hct_low_2(self):
        assert _score_hematocrit(20) == 2
        assert _score_hematocrit(29) == 2

    def test_hct_low_4(self):
        assert _score_hematocrit(19) == 4
        assert _score_hematocrit(10) == 4

    # --- WBC ---
    def test_wbc_high_4(self):
        assert _score_wbc(40) == 4
        assert _score_wbc(60) == 4

    def test_wbc_high_2(self):
        assert _score_wbc(20) == 2
        assert _score_wbc(39) == 2

    def test_wbc_high_1(self):
        assert _score_wbc(15) == 1
        assert _score_wbc(19) == 1

    def test_wbc_normal_0(self):
        assert _score_wbc(3) == 0
        assert _score_wbc(8) == 0
        assert _score_wbc(14) == 0

    def test_wbc_low_2(self):
        assert _score_wbc(1) == 2
        assert _score_wbc(2.9) == 2

    def test_wbc_low_4(self):
        assert _score_wbc(0.9) == 4
        assert _score_wbc(0.5) == 4

    # --- GCS ---
    def test_gcs_15_is_0(self):
        assert _score_gcs(15) == 0

    def test_gcs_3_is_12(self):
        assert _score_gcs(3) == 12

    def test_gcs_10_is_5(self):
        assert _score_gcs(10) == 5


class TestAgePoints:
    """Test age point assignment per APACHE II table."""

    def test_age_under_44(self):
        assert _score_age(20) == 0
        assert _score_age(44) == 0

    def test_age_45_54(self):
        assert _score_age(45) == 2
        assert _score_age(54) == 2

    def test_age_55_64(self):
        assert _score_age(55) == 3
        assert _score_age(64) == 3

    def test_age_65_74(self):
        assert _score_age(65) == 5
        assert _score_age(74) == 5

    def test_age_75_plus(self):
        assert _score_age(75) == 6
        assert _score_age(90) == 6


class TestChronicHealthPoints:
    """Test chronic health point assignment per APACHE II table."""

    def test_no_chronic_health(self):
        assert _score_chronic_health(AdmissionType.NONOPERATIVE, False) == 0
        assert _score_chronic_health(AdmissionType.EMERGENCY_SURGERY, False) == 0
        assert _score_chronic_health(AdmissionType.ELECTIVE_SURGERY, False) == 0

    def test_chronic_health_nonoperative(self):
        assert _score_chronic_health(AdmissionType.NONOPERATIVE, True) == 5

    def test_chronic_health_emergency_surgery(self):
        assert _score_chronic_health(AdmissionType.EMERGENCY_SURGERY, True) == 5

    def test_chronic_health_elective_surgery(self):
        assert _score_chronic_health(AdmissionType.ELECTIVE_SURGERY, True) == 2


class TestRiskStrata:
    """Test that risk strata boundaries produce the correct interpretation."""

    def test_low_severity(self):
        """Score 0-4 => Low severity."""
        params = _normal_params()  # All normal -> score 0
        result = calculate_apache2(params)
        assert result.value <= 4
        assert "Low severity" in result.interpretation

    def test_mild_severity(self):
        """Score 5-9 => Mild severity."""
        # Use age 55 (3 pts) + elevated temp 39.0 (3 pts) = score 6
        params = _normal_params(age=55, temperature=39.0)
        result = calculate_apache2(params)
        assert 5 <= result.value <= 9
        assert "Mild severity" in result.interpretation

    def test_moderate_severity(self):
        """Score 10-14 => Moderate severity."""
        # Age 75 (6 pts) + temp 41.0 (4 pts) = 10
        params = _normal_params(age=75, temperature=41.0)
        result = calculate_apache2(params)
        assert 10 <= result.value <= 14
        assert "Moderate severity" in result.interpretation

    def test_moderately_severe(self):
        """Score 15-19 => Moderately severe."""
        # Age 75 (6) + temp 41 (4) + HR 180 (4) + chronic elective (2) = 16
        params = _normal_params(
            age=75,
            temperature=41.0,
            heart_rate=180,
            admission_type=AdmissionType.ELECTIVE_SURGERY,
            severe_organ_insufficiency_or_immunocompromised=True,
        )
        result = calculate_apache2(params)
        assert 15 <= result.value <= 19
        assert "Moderately severe" in result.interpretation

    def test_severe(self):
        """Score 20-24 => Severe."""
        # Age 75 (6) + temp 41 (4) + HR 180 (4) + RR 50 (4) + chronic nonop (5) = 23
        params = _normal_params(
            age=75,
            temperature=41.0,
            heart_rate=180,
            respiratory_rate=50,
            admission_type=AdmissionType.NONOPERATIVE,
            severe_organ_insufficiency_or_immunocompromised=True,
        )
        result = calculate_apache2(params)
        assert 20 <= result.value <= 24
        assert "Severe" in result.interpretation

    def test_very_severe(self):
        """Score 25-29 => Very severe."""
        # Age 75 (6) + temp 41 (4) + HR 180 (4) + RR 50 (4) + pH 7.7 (4) + chronic nonop (5) = 27
        params = _normal_params(
            age=75,
            temperature=41.0,
            heart_rate=180,
            respiratory_rate=50,
            arterial_ph=7.7,
            admission_type=AdmissionType.NONOPERATIVE,
            severe_organ_insufficiency_or_immunocompromised=True,
        )
        result = calculate_apache2(params)
        assert 25 <= result.value <= 29
        assert "Very severe" in result.interpretation

    def test_critical(self):
        """Score 30-34 => Critical."""
        # Age 75 (6) + temp 41 (4) + HR 180 (4) + RR 50 (4) + pH 7.7 (4) + Na 180 (4) + chronic nonop (5) = 31
        params = _normal_params(
            age=75,
            temperature=41.0,
            heart_rate=180,
            respiratory_rate=50,
            arterial_ph=7.7,
            serum_sodium=180,
            admission_type=AdmissionType.NONOPERATIVE,
            severe_organ_insufficiency_or_immunocompromised=True,
        )
        result = calculate_apache2(params)
        assert 30 <= result.value <= 34
        assert "Critical" in result.interpretation

    def test_extremely_critical(self):
        """Score > 34 => Extremely critical."""
        # Age 75 (6) + temp 41 (4) + HR 180 (4) + RR 50 (4) + pH 7.7 (4) + Na 180 (4) + K 7 (4) + Cr 3.5 ARF (8) + chronic nonop (5) = 43
        params = _normal_params(
            age=75,
            temperature=41.0,
            heart_rate=180,
            respiratory_rate=50,
            arterial_ph=7.7,
            serum_sodium=180,
            serum_potassium=7.0,
            serum_creatinine=3.5,
            acute_renal_failure=True,
            admission_type=AdmissionType.NONOPERATIVE,
            severe_organ_insufficiency_or_immunocompromised=True,
        )
        result = calculate_apache2(params)
        assert result.value > 34
        assert "Extremely critical" in result.interpretation


class TestEvidenceAndFHIR:
    """Verify DOI and FHIR metadata."""

    def test_evidence_doi(self):
        params = _normal_params()
        result = calculate_apache2(params)
        assert result.evidence.source_doi == "10.1097/00003246-198510000-00009"
        assert result.evidence.level == "Derivation & Validation Study"

    def test_fhir_code(self):
        params = _normal_params()
        result = calculate_apache2(params)
        assert result.fhir_code == "9264-3"
        assert result.fhir_system == "http://loinc.org"
        assert result.fhir_display == "APACHE II score"

    def test_fhir_export(self):
        params = _normal_params()
        result = calculate_apache2(params)
        fhir_obs = result.to_fhir(subject_reference="Patient/123", encounter_reference="Encounter/456")
        assert fhir_obs["resourceType"] == "Observation"
        assert fhir_obs["status"] == "final"
        assert fhir_obs["subject"]["reference"] == "Patient/123"
        assert fhir_obs["encounter"]["reference"] == "Encounter/456"
        assert fhir_obs["code"]["coding"][0]["code"] == "9264-3"
        assert fhir_obs["code"]["coding"][0]["system"] == "http://loinc.org"
        assert "10.1097/00003246-198510000-00009" in fhir_obs["note"][0]["text"]


class TestIntegrationScenarios:
    """Clinical scenario-based integration tests cross-validated against MDCalc/reference calculators."""

    def test_typical_sepsis_patient(self):
        """Typical septic patient: fever, tachycardia, tachypnea, low MAP, elevated creatinine.
        Expected breakdown:
        - Temp 39.5 => +3
        - MAP 60 => +2
        - HR 130 => +2
        - RR 30 => +1
        - FiO2 0.4, PaO2 70 => +1 (PaO2 = 70, not > 70, so falls into 61-70 bracket)
        - pH 7.30 => +2
        - Na 138 => 0
        - K 4.5 => 0
        - Cr 2.5 (no ARF) => +3
        - Hct 35 => 0
        - WBC 18 => +1
        - GCS 13 => 15-13 = +2
        APS = 3+2+2+1+1+2+0+0+3+0+1+2 = 17
        Age 68 => +5
        Nonoperative, no chronic health => 0
        Total = 22
        """
        params = APACHE2Params(
            temperature=39.5,
            mean_arterial_pressure=60.0,
            heart_rate=130,
            respiratory_rate=30,
            fio2=0.4,
            pao2=70.0,
            paco2=None,
            arterial_ph=7.30,
            serum_sodium=138.0,
            serum_potassium=4.5,
            serum_creatinine=2.5,
            acute_renal_failure=False,
            hematocrit=35.0,
            white_blood_cell_count=18.0,
            gcs=13,
            age=68,
            admission_type=AdmissionType.NONOPERATIVE,
            severe_organ_insufficiency_or_immunocompromised=False,
        )
        result = calculate_apache2(params)
        assert result.value == 22
        assert "Severe" in result.interpretation

    def test_post_cardiac_surgery_elective(self):
        """Post-elective cardiac surgery patient with mild abnormalities.
        - Temp 36.5 => 0
        - MAP 75 => 0
        - HR 90 => 0
        - RR 18 => 0
        - FiO2 0.4, PaO2 80 => 0 (>70)
        - pH 7.35 => 0
        - Na 142 => 0
        - K 4.2 => 0
        - Cr 1.2 => 0
        - Hct 32 => 0
        - WBC 12 => 0
        - GCS 15 => 0
        APS = 0
        Age 72 => +5
        Elective surgery, chronic health (NYHA IV) => +2
        Total = 7
        """
        params = APACHE2Params(
            temperature=36.5,
            mean_arterial_pressure=75.0,
            heart_rate=90,
            respiratory_rate=18,
            fio2=0.4,
            pao2=80.0,
            paco2=None,
            arterial_ph=7.35,
            serum_sodium=142.0,
            serum_potassium=4.2,
            serum_creatinine=1.2,
            acute_renal_failure=False,
            hematocrit=32.0,
            white_blood_cell_count=12.0,
            gcs=15,
            age=72,
            admission_type=AdmissionType.ELECTIVE_SURGERY,
            severe_organ_insufficiency_or_immunocompromised=True,
        )
        result = calculate_apache2(params)
        assert result.value == 7
        assert "Mild severity" in result.interpretation

    def test_young_healthy_icu_patient(self):
        """Young, healthy patient with all normal values.
        APS = 0, Age 25 => 0, No chronic health => 0, Total = 0.
        """
        params = APACHE2Params(
            temperature=37.0,
            mean_arterial_pressure=85.0,
            heart_rate=75,
            respiratory_rate=14,
            fio2=0.21,
            pao2=95.0,
            paco2=None,
            arterial_ph=7.40,
            serum_sodium=140.0,
            serum_potassium=4.0,
            serum_creatinine=0.9,
            acute_renal_failure=False,
            hematocrit=42.0,
            white_blood_cell_count=7.0,
            gcs=15,
            age=25,
            admission_type=AdmissionType.NONOPERATIVE,
            severe_organ_insufficiency_or_immunocompromised=False,
        )
        result = calculate_apache2(params)
        assert result.value == 0
        assert "Low severity" in result.interpretation

    def test_ards_on_high_fio2(self):
        """ARDS patient on high FiO2 with high A-a gradient.
        - Temp 38.0 => 0
        - MAP 65 => +2
        - HR 115 => +2
        - RR 28 => +1
        - FiO2 0.8, PaCO2 35, PaO2 60: A-aDO2 = 0.8*713 - 35/0.8 - 60 = 570.4 - 43.75 - 60 = 466.65 => +3
        - pH 7.32 => +2
        - Na 145 => 0
        - K 3.8 => 0
        - Cr 1.8 => +2
        - Hct 38 => 0
        - WBC 16 => +1
        - GCS 11 => 15-11 = +4
        APS = 0+2+2+1+3+2+0+0+2+0+1+4 = 17
        Age 60 => +3
        Nonoperative, no chronic health => 0
        Total = 20
        """
        params = APACHE2Params(
            temperature=38.0,
            mean_arterial_pressure=65.0,
            heart_rate=115,
            respiratory_rate=28,
            fio2=0.8,
            pao2=60.0,
            paco2=35.0,
            arterial_ph=7.32,
            serum_sodium=145.0,
            serum_potassium=3.8,
            serum_creatinine=1.8,
            acute_renal_failure=False,
            hematocrit=38.0,
            white_blood_cell_count=16.0,
            gcs=11,
            age=60,
            admission_type=AdmissionType.NONOPERATIVE,
            severe_organ_insufficiency_or_immunocompromised=False,
        )
        result = calculate_apache2(params)
        assert result.value == 20
        assert "Severe" in result.interpretation


# ===========================================================================
# TIER 2: Property-Based Fuzz Tests
# ===========================================================================

@pytest.mark.slow
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
@settings(max_examples=500)
def test_apache2_fuzz_valid_range(
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
    """APACHE II score is always within valid bounds [0, 71] for any valid input."""
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
    assert isinstance(result.value, int)
    assert 0 <= result.value <= 71
    assert result.interpretation
    assert len(result.interpretation) > 0
    assert "APACHE II score is" in result.interpretation
    assert result.evidence.source_doi == "10.1097/00003246-198510000-00009"


@pytest.mark.slow
@given(
    temperature=st.floats(min_value=20.0, max_value=45.0),
)
@settings(max_examples=200)
def test_temperature_score_always_0_to_4(temperature):
    """Temperature score is always 0-4."""
    score = _score_temperature(temperature)
    assert 0 <= score <= 4


@pytest.mark.slow
@given(
    gcs=st.integers(min_value=3, max_value=15),
)
@settings(max_examples=100)
def test_gcs_score_always_0_to_12(gcs):
    """GCS component is always 0-12."""
    score = _score_gcs(gcs)
    assert 0 <= score <= 12


@pytest.mark.slow
@given(
    cr=st.floats(min_value=0.1, max_value=15.0),
    arf=st.booleans(),
)
@settings(max_examples=200)
def test_creatinine_score_bounded(cr, arf):
    """Creatinine score is 0-8 (doubled with ARF)."""
    score = _score_creatinine(cr, arf)
    assert 0 <= score <= 8

# Related guidelines: ssc_sepsis_2021 (sepsis management, ICU severity assessment)
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class AdmissionType(str, Enum):
    """Type of ICU admission for chronic health point assignment."""
    NONOPERATIVE = "nonoperative"
    EMERGENCY_SURGERY = "emergency_surgery"
    ELECTIVE_SURGERY = "elective_surgery"


class APACHE2Params(BaseModel):
    """Parameters to calculate the APACHE II (Acute Physiology and Chronic Health
    Evaluation II) score. Uses the worst values recorded during the first 24 hours
    of ICU admission per the original Knaus et al. 1985 methodology.
    """

    # --- A. Acute Physiology Score (APS) variables ---
    temperature: float = Field(
        ...,
        description="Core/rectal temperature in degrees Celsius. Use the most abnormal value in first 24h of ICU admission."
    )
    mean_arterial_pressure: float = Field(
        ...,
        description="Mean arterial pressure (MAP) in mmHg. Use the most abnormal value in first 24h of ICU admission."
    )
    heart_rate: int = Field(
        ...,
        description="Heart rate (ventricular response) in beats per minute. Use the most abnormal value in first 24h of ICU admission."
    )
    respiratory_rate: int = Field(
        ...,
        description="Respiratory rate in breaths per minute (ventilated or non-ventilated). Use the most abnormal value in first 24h of ICU admission."
    )
    fio2: float = Field(
        ...,
        ge=0.21,
        le=1.0,
        description="Fraction of inspired oxygen (FiO2) as a decimal (0.21-1.0). Determines whether A-aDO2 or PaO2 is used for oxygenation scoring."
    )
    pao2: float = Field(
        ...,
        description="Partial pressure of arterial oxygen (PaO2) in mmHg."
    )
    paco2: Optional[float] = Field(
        None,
        description="Partial pressure of arterial CO2 (PaCO2) in mmHg. Required when FiO2 >= 0.5 to calculate the A-a gradient."
    )
    arterial_ph: float = Field(
        ...,
        description="Arterial blood pH."
    )
    serum_sodium: float = Field(
        ...,
        description="Serum sodium (Na+) in mEq/L."
    )
    serum_potassium: float = Field(
        ...,
        description="Serum potassium (K+) in mEq/L."
    )
    serum_creatinine: float = Field(
        ...,
        description="Serum creatinine in mg/dL."
    )
    acute_renal_failure: bool = Field(
        False,
        description="Whether the patient has acute renal failure (ARF). If True, the creatinine score is doubled per APACHE II methodology."
    )
    hematocrit: float = Field(
        ...,
        description="Hematocrit in percent (%)."
    )
    white_blood_cell_count: float = Field(
        ...,
        description="White blood cell (WBC) count in thousands per mm3 (x10^3/mm3)."
    )
    gcs: int = Field(
        ...,
        ge=3,
        le=15,
        description="Glasgow Coma Scale score (3-15). GCS component = 15 - actual GCS."
    )

    # --- B. Age Points ---
    age: int = Field(
        ...,
        description="Patient age in years."
    )

    # --- C. Chronic Health Points ---
    admission_type: AdmissionType = Field(
        ...,
        description="Type of admission: 'nonoperative' (medical), 'emergency_surgery', or 'elective_surgery'. Affects chronic health point weighting."
    )
    severe_organ_insufficiency_or_immunocompromised: bool = Field(
        False,
        description=(
            "History of severe organ system insufficiency or immunocompromised state. "
            "Includes: liver (biopsy-proven cirrhosis, portal hypertension, prior hepatic failure/encephalopathy/coma), "
            "cardiovascular (NYHA Class IV), respiratory (chronic restrictive/obstructive/vascular disease with severe exercise limitation, "
            "documented chronic hypoxia/hypercapnia/polycythemia/pulmonary hypertension, ventilator dependence), "
            "renal (receiving chronic dialysis), or immunocompromised (therapy suppressing resistance to infection, "
            "e.g. immunosuppression, chemotherapy, radiation, long-term high-dose steroids, or disease sufficiently advanced "
            "to suppress resistance, e.g. leukemia, lymphoma, AIDS)."
        )
    )


def _score_temperature(temp: float) -> int:
    """Score rectal/core temperature (degrees C) per APACHE II table."""
    if temp >= 41.0:
        return 4
    elif temp >= 39.0:
        return 3
    elif temp >= 38.5:
        return 1
    elif temp >= 36.0:
        return 0
    elif temp >= 34.0:
        return 1
    elif temp >= 32.0:
        return 2
    elif temp >= 30.0:
        return 3
    else:  # < 30
        return 4


def _score_map(map_val: float) -> int:
    """Score mean arterial pressure (mmHg) per APACHE II table."""
    if map_val >= 160:
        return 4
    elif map_val >= 130:
        return 3
    elif map_val >= 110:
        return 2
    elif map_val >= 70:
        return 0
    elif map_val >= 50:
        return 2
    else:  # < 50
        return 4


def _score_heart_rate(hr: int) -> int:
    """Score heart rate (ventricular response, bpm) per APACHE II table."""
    if hr >= 180:
        return 4
    elif hr >= 140:
        return 3
    elif hr >= 110:
        return 2
    elif hr >= 70:
        return 0
    elif hr >= 55:
        return 2
    elif hr >= 40:
        return 3
    else:  # < 40
        return 4


def _score_respiratory_rate(rr: int) -> int:
    """Score respiratory rate (breaths/min) per APACHE II table."""
    if rr >= 50:
        return 4
    elif rr >= 35:
        return 3
    elif rr >= 25:
        return 1
    elif rr >= 12:
        return 0
    elif rr >= 10:
        return 1
    elif rr >= 6:
        return 2
    else:  # < 6
        return 4


def _score_oxygenation(fio2: float, pao2: float, paco2: Optional[float]) -> int:
    """Score oxygenation per APACHE II table.

    If FiO2 >= 0.5: use A-aDO2 = (FiO2 * 713) - (PaCO2 / 0.8) - PaO2
    If FiO2 < 0.5: use PaO2 directly.
    """
    if fio2 >= 0.5:
        # Calculate A-a gradient; PaCO2 required
        if paco2 is None:
            # If PaCO2 is not provided when FiO2 >= 0.5, default to PaO2 scoring
            # as a safety fallback (clinical documentation should include PaCO2)
            if pao2 > 70:
                return 0
            elif pao2 >= 61:
                return 1
            elif pao2 >= 55:
                return 3
            else:
                return 4
        aa_gradient = (fio2 * 713.0) - (paco2 / 0.8) - pao2
        if aa_gradient < 0:
            aa_gradient = 0.0
        if aa_gradient >= 500:
            return 4
        elif aa_gradient >= 350:
            return 3
        elif aa_gradient >= 200:
            return 2
        else:  # < 200
            return 0
    else:
        # FiO2 < 0.5: use PaO2
        if pao2 > 70:
            return 0
        elif pao2 >= 61:
            return 1
        elif pao2 >= 55:
            return 3
        else:  # < 55
            return 4


def _score_arterial_ph(ph: float) -> int:
    """Score arterial pH per APACHE II table."""
    if ph >= 7.7:
        return 4
    elif ph >= 7.6:
        return 3
    elif ph >= 7.5:
        return 1
    elif ph >= 7.33:
        return 0
    elif ph >= 7.25:
        return 2
    elif ph >= 7.15:
        return 3
    else:  # < 7.15
        return 4


def _score_sodium(na: float) -> int:
    """Score serum sodium (mEq/L) per APACHE II table."""
    if na >= 180:
        return 4
    elif na >= 160:
        return 3
    elif na >= 155:
        return 2
    elif na >= 150:
        return 1
    elif na >= 130:
        return 0
    elif na >= 120:
        return 2
    elif na >= 111:
        return 3
    else:  # <= 110
        return 4


def _score_potassium(k: float) -> int:
    """Score serum potassium (mEq/L) per APACHE II table."""
    if k >= 7.0:
        return 4
    elif k >= 6.0:
        return 3
    elif k >= 5.5:
        return 1
    elif k >= 3.5:
        return 0
    elif k >= 3.0:
        return 1
    elif k >= 2.5:
        return 2
    else:  # < 2.5
        return 4


def _score_creatinine(cr: float, acute_renal_failure: bool) -> int:
    """Score serum creatinine (mg/dL) per APACHE II table.
    Points are doubled if acute renal failure is present.
    """
    if cr >= 3.5:
        points = 4
    elif cr >= 2.0:
        points = 3
    elif cr >= 1.5:
        points = 2
    elif cr >= 0.6:
        points = 0
    else:  # < 0.6
        points = 2

    if acute_renal_failure:
        points *= 2
    return points


def _score_hematocrit(hct: float) -> int:
    """Score hematocrit (%) per APACHE II table."""
    if hct >= 60:
        return 4
    elif hct >= 50:
        return 2
    elif hct >= 46:
        return 1
    elif hct >= 30:
        return 0
    elif hct >= 20:
        return 2
    else:  # < 20
        return 4


def _score_wbc(wbc: float) -> int:
    """Score white blood cell count (x10^3/mm3) per APACHE II table."""
    if wbc >= 40:
        return 4
    elif wbc >= 20:
        return 2
    elif wbc >= 15:
        return 1
    elif wbc >= 3:
        return 0
    elif wbc >= 1:
        return 2
    else:  # < 1
        return 4


def _score_gcs(gcs: int) -> int:
    """GCS component of APACHE II = 15 - actual GCS."""
    return 15 - gcs


def _score_age(age: int) -> int:
    """Age points per APACHE II table."""
    if age <= 44:
        return 0
    elif age <= 54:
        return 2
    elif age <= 64:
        return 3
    elif age <= 74:
        return 5
    else:  # >= 75
        return 6


def _score_chronic_health(
    admission_type: AdmissionType,
    severe_organ_insufficiency_or_immunocompromised: bool
) -> int:
    """Chronic health points per APACHE II table.

    If the patient has a history of severe organ system insufficiency or is
    immunocompromised:
    - Nonoperative or emergency postoperative: +5
    - Elective postoperative: +2
    Otherwise: 0
    """
    if not severe_organ_insufficiency_or_immunocompromised:
        return 0
    if admission_type == AdmissionType.ELECTIVE_SURGERY:
        return 2
    # nonoperative or emergency_surgery
    return 5


def calculate_apache2(params: APACHE2Params) -> ClinicalResult:
    """
    Calculates the APACHE II (Acute Physiology and Chronic Health Evaluation II) score.
    Estimates ICU mortality risk based on 12 acute physiologic variables, age, and
    chronic health status during the first 24 hours of ICU admission.
    Reference: Knaus WA et al. Crit Care Med. 1985;13(10):818-829.
    """
    # A. Acute Physiology Score (APS): sum of 12 variable scores
    aps = 0
    aps += _score_temperature(params.temperature)
    aps += _score_map(params.mean_arterial_pressure)
    aps += _score_heart_rate(params.heart_rate)
    aps += _score_respiratory_rate(params.respiratory_rate)
    aps += _score_oxygenation(params.fio2, params.pao2, params.paco2)
    aps += _score_arterial_ph(params.arterial_ph)
    aps += _score_sodium(params.serum_sodium)
    aps += _score_potassium(params.serum_potassium)
    aps += _score_creatinine(params.serum_creatinine, params.acute_renal_failure)
    aps += _score_hematocrit(params.hematocrit)
    aps += _score_wbc(params.white_blood_cell_count)
    aps += _score_gcs(params.gcs)

    # B. Age Points
    age_points = _score_age(params.age)

    # C. Chronic Health Points
    chronic_health_points = _score_chronic_health(
        params.admission_type,
        params.severe_organ_insufficiency_or_immunocompromised
    )

    # Total APACHE II score
    score = aps + age_points + chronic_health_points

    # Evidence from the original derivation study
    evidence = Evidence(
        source_doi="10.1097/00003246-198510000-00009",
        level="Derivation & Validation Study",
        description=(
            "APACHE II: A severity of disease classification system. "
            "Knaus WA, Draper EA, Wagner DP, Zimmerman JE. "
            "Crit Care Med. 1985;13(10):818-829."
        )
    )

    # Interpretation based on score ranges and approximate mortality from original study
    # The original paper showed mortality increases with score; approximate non-operative
    # mortality rates are used here for general guidance. Actual mortality prediction
    # requires disease-specific coefficients not included in the point score alone.
    if score <= 4:
        interpretation = (
            f"APACHE II score is {score} (APS: {aps}, Age: {age_points}, "
            f"Chronic Health: {chronic_health_points}). "
            f"Low severity. Approximate non-operative death rate ~4%. "
            f"Continue standard ICU monitoring and supportive care."
        )
    elif score <= 9:
        interpretation = (
            f"APACHE II score is {score} (APS: {aps}, Age: {age_points}, "
            f"Chronic Health: {chronic_health_points}). "
            f"Mild severity. Approximate non-operative death rate ~8%. "
            f"Close monitoring advised with reassessment of clinical trajectory."
        )
    elif score <= 14:
        interpretation = (
            f"APACHE II score is {score} (APS: {aps}, Age: {age_points}, "
            f"Chronic Health: {chronic_health_points}). "
            f"Moderate severity. Approximate non-operative death rate ~15%. "
            f"Intensify monitoring and consider escalation of supportive therapies."
        )
    elif score <= 19:
        interpretation = (
            f"APACHE II score is {score} (APS: {aps}, Age: {age_points}, "
            f"Chronic Health: {chronic_health_points}). "
            f"Moderately severe. Approximate non-operative death rate ~25%. "
            f"Aggressive ICU management warranted. Consider goals-of-care discussion."
        )
    elif score <= 24:
        interpretation = (
            f"APACHE II score is {score} (APS: {aps}, Age: {age_points}, "
            f"Chronic Health: {chronic_health_points}). "
            f"Severe. Approximate non-operative death rate ~40%. "
            f"High-intensity ICU care required. Reassess treatment plan frequently."
        )
    elif score <= 29:
        interpretation = (
            f"APACHE II score is {score} (APS: {aps}, Age: {age_points}, "
            f"Chronic Health: {chronic_health_points}). "
            f"Very severe. Approximate non-operative death rate ~55%. "
            f"Maximal ICU support indicated. Goals-of-care discussion strongly recommended."
        )
    elif score <= 34:
        interpretation = (
            f"APACHE II score is {score} (APS: {aps}, Age: {age_points}, "
            f"Chronic Health: {chronic_health_points}). "
            f"Critical. Approximate non-operative death rate ~73%. "
            f"Extremely high mortality risk. Multidisciplinary team discussion recommended."
        )
    else:  # score > 34
        interpretation = (
            f"APACHE II score is {score} (APS: {aps}, Age: {age_points}, "
            f"Chronic Health: {chronic_health_points}). "
            f"Extremely critical. Approximate non-operative death rate >85%. "
            f"Very high mortality risk. Palliative care consultation and goals-of-care "
            f"discussion should be prioritized."
        )

    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="9264-3",
        fhir_system="http://loinc.org",
        fhir_display="APACHE II score"
    )

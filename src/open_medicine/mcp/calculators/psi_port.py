# Related guidelines: ats_idsa_cap_2019 (severity_assessment section)
from typing import Optional
from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class PSIPortParams(BaseModel):
    """Parameters to calculate the PSI/PORT (Pneumonia Severity Index) score
    for community-acquired pneumonia risk stratification.

    The PSI uses a two-step algorithm:
    - Step 1: Patients age <=50 with no comorbidities and stable vitals are
      classified as Risk Class I (lowest risk) without point calculation.
    - Step 2: All other patients receive a point score based on demographics,
      comorbidities, physical examination, and laboratory findings.
    """

    # --- Demographics ---
    age: int = Field(..., description="Patient age in years")
    is_female: bool = Field(..., description="Is the patient female? Females receive age - 10 points.")
    nursing_home_resident: bool = Field(
        False,
        description="Is the patient a nursing home resident? (+10 points)"
    )

    # --- Comorbid Conditions ---
    neoplastic_disease: bool = Field(
        False,
        description="Active neoplastic disease: any cancer except basal or squamous cell carcinoma of the skin that was active at the time of presentation or diagnosed within one year of presentation (+30 points)"
    )
    liver_disease: bool = Field(
        False,
        description="Liver disease: clinical or histologic diagnosis of cirrhosis or other form of chronic liver disease such as chronic active hepatitis (+20 points)"
    )
    congestive_heart_failure: bool = Field(
        False,
        description="Congestive heart failure: systolic or diastolic ventricular dysfunction documented by history, physical examination, chest radiograph, echocardiogram, or other imaging study (+10 points)"
    )
    cerebrovascular_disease: bool = Field(
        False,
        description="Cerebrovascular disease: clinical diagnosis of stroke or transient ischemic attack (TIA), or stroke documented by CT or MRI (+10 points)"
    )
    renal_disease: bool = Field(
        False,
        description="Renal disease: history of chronic renal disease or abnormal BUN and creatinine documented in medical record (+10 points)"
    )

    # --- Physical Examination Findings ---
    altered_mental_status: bool = Field(
        False,
        description="Altered mental status: disorientation with respect to person, place, or time that is not known to be chronic, stupor, or coma (+20 points)"
    )
    respiratory_rate: int = Field(
        ...,
        description="Respiratory rate in breaths per minute (>=30 adds +20 points)"
    )
    systolic_bp: int = Field(
        ...,
        description="Systolic blood pressure in mmHg (<90 adds +20 points)"
    )
    temperature_celsius: float = Field(
        ...,
        description="Body temperature in degrees Celsius (<35 or >=40 adds +15 points)"
    )
    pulse: int = Field(
        ...,
        description="Pulse/heart rate in beats per minute (>=125 adds +10 points)"
    )

    # --- Laboratory and Radiographic Findings ---
    # These are Optional because not all patients have all labs at presentation.
    # If not provided, they are assumed normal (0 points).
    arterial_ph: Optional[float] = Field(
        None,
        description="Arterial blood pH (<7.35 adds +30 points). If not available, assumed normal."
    )
    bun: Optional[float] = Field(
        None,
        description="Blood urea nitrogen (BUN) in mg/dL (>=30 adds +20 points). If not available, assumed normal."
    )
    sodium: Optional[float] = Field(
        None,
        description="Serum sodium in mmol/L (<130 adds +20 points). If not available, assumed normal."
    )
    glucose: Optional[float] = Field(
        None,
        description="Serum glucose in mg/dL (>=250 adds +10 points). If not available, assumed normal."
    )
    hematocrit: Optional[float] = Field(
        None,
        description="Hematocrit in percent (%) (<30 adds +10 points). If not available, assumed normal."
    )
    pao2: Optional[float] = Field(
        None,
        description="Partial pressure of arterial oxygen (PaO2) in mmHg (<60 adds +10 points). If not available, assumed normal."
    )
    pleural_effusion: bool = Field(
        False,
        description="Pleural effusion on chest radiograph (+10 points)"
    )


def _is_risk_class_i(params: PSIPortParams) -> bool:
    """Step 1: Determine if a patient qualifies for Risk Class I.

    Risk Class I is assigned when ALL of the following are true:
    - Age <= 50 years
    - No neoplastic disease
    - No liver disease
    - No congestive heart failure
    - No cerebrovascular disease
    - No renal disease
    - No altered mental status
    - Pulse < 125/min
    - Respiratory rate < 30/min
    - Systolic BP >= 90 mmHg
    - Temperature >= 35 and < 40 degrees Celsius
    """
    if params.age > 50:
        return False

    # Check comorbidities
    if any([
        params.neoplastic_disease,
        params.liver_disease,
        params.congestive_heart_failure,
        params.cerebrovascular_disease,
        params.renal_disease,
    ]):
        return False

    # Check physical exam findings
    if params.altered_mental_status:
        return False
    if params.pulse >= 125:
        return False
    if params.respiratory_rate >= 30:
        return False
    if params.systolic_bp < 90:
        return False
    if params.temperature_celsius < 35.0 or params.temperature_celsius >= 40.0:
        return False

    return True


def _calculate_psi_points(params: PSIPortParams) -> int:
    """Step 2: Calculate the total PSI point score for patients not in Class I.

    Point assignment per Fine MJ et al. NEJM 1997.
    """
    score = 0

    # --- Demographics ---
    # Age: males get age in years as points; females get age - 10
    if params.is_female:
        score += params.age - 10
    else:
        score += params.age

    # Nursing home resident: +10
    if params.nursing_home_resident:
        score += 10

    # --- Comorbid Conditions ---
    if params.neoplastic_disease:
        score += 30
    if params.liver_disease:
        score += 20
    if params.congestive_heart_failure:
        score += 10
    if params.cerebrovascular_disease:
        score += 10
    if params.renal_disease:
        score += 10

    # --- Physical Examination Findings ---
    if params.altered_mental_status:
        score += 20
    if params.respiratory_rate >= 30:
        score += 20
    if params.systolic_bp < 90:
        score += 20
    if params.temperature_celsius < 35.0 or params.temperature_celsius >= 40.0:
        score += 15
    if params.pulse >= 125:
        score += 10

    # --- Laboratory and Radiographic Findings ---
    if params.arterial_ph is not None and params.arterial_ph < 7.35:
        score += 30
    if params.bun is not None and params.bun >= 30:
        score += 20
    if params.sodium is not None and params.sodium < 130:
        score += 20
    if params.glucose is not None and params.glucose >= 250:
        score += 10
    if params.hematocrit is not None and params.hematocrit < 30:
        score += 10
    if params.pao2 is not None and params.pao2 < 60:
        score += 10
    if params.pleural_effusion:
        score += 10

    return score


def calculate_psi_port(params: PSIPortParams) -> ClinicalResult:
    """
    Calculates the PSI/PORT (Pneumonia Severity Index) score for community-acquired
    pneumonia risk stratification. Predicts 30-day mortality and guides the initial
    site-of-care decision (outpatient vs. inpatient).

    Reference: Fine MJ et al. N Engl J Med. 1997;336(4):243-250.
    """
    evidence = Evidence(
        source_doi="10.1056/NEJM199701233360402",
        level="Derivation & Validation Study",
        description=(
            "A prediction rule to identify low-risk patients with community-acquired pneumonia. "
            "Fine MJ, Auble TE, Yealy DM, et al. N Engl J Med. 1997;336(4):243-250."
        )
    )

    # Step 1: Check if patient qualifies for Risk Class I
    if _is_risk_class_i(params):
        return ClinicalResult(
            value=0,
            interpretation=(
                "PSI/PORT Risk Class I (score N/A - assigned by step 1 algorithm). "
                "30-day mortality 0.1-0.4%. "
                "Low risk. Outpatient treatment is generally appropriate."
            ),
            evidence=evidence,
            # LOINC approximation: no exact LOINC code exists for PSI/PORT score;
            # using the CURB-65 part code as the closest pneumonia severity assessment.
            fhir_code="LP419467-4",
            fhir_system="http://loinc.org",
            fhir_display="Pneumonia Severity Index [PSI/PORT]"
        )

    # Step 2: Calculate point score and determine risk class
    score = _calculate_psi_points(params)

    if score <= 70:
        risk_class = "II"
        mortality = "0.6-0.7%"
        risk_level = "Low risk"
        recommendation = "Outpatient treatment is generally appropriate."
    elif score <= 90:
        risk_class = "III"
        mortality = "0.9-2.8%"
        risk_level = "Low risk"
        recommendation = (
            "Consider brief observation admission or outpatient treatment with close follow-up."
        )
    elif score <= 130:
        risk_class = "IV"
        mortality = "4-10%"
        risk_level = "Moderate risk"
        recommendation = "Inpatient admission is recommended."
    else:
        risk_class = "V"
        mortality = "27%"
        risk_level = "High risk"
        recommendation = (
            "Inpatient admission is recommended. Consider ICU-level care."
        )

    interpretation = (
        f"PSI/PORT score is {score}, Risk Class {risk_class}. "
        f"30-day mortality {mortality}. "
        f"{risk_level}. {recommendation}"
    )

    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        # LOINC approximation: no exact LOINC code exists for PSI/PORT score;
        # using the CURB-65 part code as the closest pneumonia severity assessment.
        fhir_code="LP419467-4",
        fhir_system="http://loinc.org",
        fhir_display="Pneumonia Severity Index [PSI/PORT]"
    )

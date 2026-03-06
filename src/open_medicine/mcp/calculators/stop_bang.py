# Related guidelines: asa_osa_perioperative_2014 (perioperative OSA screening section)
from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class STOPBangParams(BaseModel):
    """Parameters to calculate the STOP-Bang score for obstructive sleep apnea screening."""
    snoring: bool = Field(
        False,
        description="Do you snore loudly (louder than talking or loud enough to be heard through closed doors)?"
    )
    tired: bool = Field(
        False,
        description="Do you often feel tired, fatigued, or sleepy during the daytime?"
    )
    observed_apnea: bool = Field(
        False,
        description="Has anyone observed you stop breathing during your sleep?"
    )
    high_blood_pressure: bool = Field(
        False,
        description="Do you have or are you being treated for high blood pressure?"
    )
    bmi_over_35: bool = Field(
        False,
        description="Is the patient's BMI greater than 35 kg/m2?"
    )
    age_over_50: bool = Field(
        False,
        description="Is the patient older than 50 years?"
    )
    neck_circumference_over_40: bool = Field(
        False,
        description="Is the patient's neck circumference greater than 40 cm (approximately 16 inches)?"
    )
    male_gender: bool = Field(
        False,
        description="Is the patient male?"
    )


def calculate_stop_bang(params: STOPBangParams) -> ClinicalResult:
    """
    Calculates the STOP-Bang score for obstructive sleep apnea (OSA) screening.
    Reference: Chung F et al. Anesthesiology. 2008;108(5):812-821.
    """
    # Each criterion adds 1 point (total 0-8)
    score = sum([
        params.snoring,                     # S - Snoring
        params.tired,                       # T - Tired
        params.observed_apnea,              # O - Observed apnea
        params.high_blood_pressure,         # P - Pressure (high blood pressure)
        params.bmi_over_35,                 # B - BMI > 35
        params.age_over_50,                 # A - Age > 50
        params.neck_circumference_over_40,  # N - Neck circumference > 40 cm
        params.male_gender,                 # G - Gender (male)
    ])

    evidence = Evidence(
        source_doi="10.1097/ALN.0b013e31816d83e4",
        level="Derivation & Validation Study",
        description="STOP questionnaire: a tool to screen patients for obstructive sleep apnea. Chung F et al. Anesthesiology. 2008."
    )

    # Risk stratification per Chung F et al. Chest 2016 and original validation:
    # Low risk: 0-2, Intermediate risk: 3-4, High risk: 5-8
    if score <= 2:
        interpretation = (
            f"STOP-Bang score is {score}. Low risk for obstructive sleep apnea. "
            f"OSA is unlikely; routine perioperative precautions are sufficient."
        )
    elif score <= 4:
        interpretation = (
            f"STOP-Bang score is {score}. Intermediate risk for obstructive sleep apnea. "
            f"Consider further evaluation with polysomnography or home sleep testing. "
            f"Sensitivity of score >= 3 is 93% for moderate-to-severe OSA (AHI > 15) "
            f"and 100% for severe OSA (AHI > 30)."
        )
    else:
        interpretation = (
            f"STOP-Bang score is {score}. High risk for obstructive sleep apnea. "
            f"Strong recommendation for diagnostic polysomnography. "
            f"Perioperative precautions for OSA should be implemented including "
            f"continuous pulse oximetry and avoidance of supine positioning."
        )

    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        # LOINC approximation: No specific LOINC code exists for STOP-Bang score.
        # Using the LOINC panel code for sleep-disordered breathing screening.
        fhir_code="28633-6",
        fhir_system="http://loinc.org",
        fhir_display="STOP-Bang score for obstructive sleep apnea screening"
    )

from typing import Optional
from pydantic import BaseModel, Field
from open_medicine.mcp.base import ClinicalResult, Evidence

class CHADSVAScParams(BaseModel):
    """Parameters to calculate the CHA2DS2-VASc score. Missing values are assumed false/normal."""
    congestive_heart_failure: bool = Field(False, description="Congestive heart failure (or Left ventricular systolic dysfunction)")
    hypertension: bool = Field(False, description="Hypertension: blood pressure consistently >140/90 mmHg (or treated hypertension on medication)")
    age: int = Field(..., description="Age in years")
    diabetes: bool = Field(False, description="Diabetes mellitus")
    stroke_tia_thromboembolism: bool = Field(False, description="Prior Stroke, TIA, or Thromboembolism")
    vascular_disease: bool = Field(False, description="Vascular disease (e.g., prior myocardial infarction, peripheral artery disease, or aortic plaque)")
    female_sex: bool = Field(..., description="Is the patient female? (Sex category)")

def calculate_chadsvasc(params: CHADSVAScParams) -> ClinicalResult:
    """
    Calculates the CHA2DS2-VASc score for atrial fibrillation stroke risk.
    Returns a deterministic structured ClinicalResult, complete with source Evidence.
    """
    score = 0
    
    # C: Congestive heart failure
    if params.congestive_heart_failure:
        score += 1
        
    # H: Hypertension
    if params.hypertension:
        score += 1
        
    # A2/A: Age >= 75 (2 points) or 65-74 (1 point)
    if params.age >= 75:
        score += 2
    elif params.age >= 65:
        score += 1
        
    # D: Diabetes mellitus
    if params.diabetes:
        score += 1
        
    # S2: Stroke / TIA / thromboembolism
    if params.stroke_tia_thromboembolism:
        score += 2
        
    # V: Vascular disease
    if params.vascular_disease:
        score += 1
        
    # Sc: Sex category (female)
    if params.female_sex:
        score += 1

    evidence = Evidence(
        source_doi="10.1378/chest.09-1584",
        level="Derivation Study",
        description="Lip GYH et al. Refining clinical risk stratification for predicting stroke and thromboembolism in atrial fibrillation. Chest. 2010;137(2):263-272."
    )

    if params.female_sex:
        if score == 1:
            interpretation = f"The patient has a CHA2DS2-VASc score of {score}. For women, a score of 1 indicates low stroke risk. Oral anticoagulation is generally not recommended."
        elif score == 2:
            interpretation = f"The patient has a CHA2DS2-VASc score of {score}. For women, a score of 2 indicates moderate stroke risk. Oral anticoagulation may be considered reasonable based on shared decision-making."
        else:
            interpretation = f"The patient has a CHA2DS2-VASc score of {score}. For women, a score of >= 3 indicates high stroke risk. Oral anticoagulation is recommended."
    else:
        if score == 0:
            interpretation = f"The patient has a CHA2DS2-VASc score of {score}. For men, a score of 0 indicates low stroke risk. Oral anticoagulation is generally not recommended."
        elif score == 1:
            interpretation = f"The patient has a CHA2DS2-VASc score of {score}. For men, a score of 1 indicates moderate stroke risk. Oral anticoagulation may be considered reasonable based on shared decision-making."
        else:
            interpretation = f"The patient has a CHA2DS2-VASc score of {score}. For men, a score of >= 2 indicates high stroke risk. Oral anticoagulation is recommended."

    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="79423-0",
        fhir_system="http://loinc.org",
        fhir_display="CHA2DS2-VASc score"
    )

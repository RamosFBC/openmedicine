from typing import Optional
from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence

class SOFAParams(BaseModel):
    """Parameters to calculate the SOFA score. Missing values are assumed normal."""
    pao2_fio2: Optional[float] = Field(None, description="PaO2/FiO2 ratio in mmHg")
    spo2_fio2: Optional[float] = Field(None, description="SpO2/FiO2 ratio (used if PaO2 is missing)")
    platelets: Optional[float] = Field(None, description="Platelets count in x10^3/mm^3")
    bilirubin: Optional[float] = Field(None, description="Bilirubin level in mg/dL")
    map_pressure: Optional[float] = Field(None, description="Mean arterial pressure in mmHg")
    dopamine: Optional[float] = Field(None, description="Dopamine dose in mcg/kg/min")
    epinephrine: Optional[float] = Field(None, description="Epinephrine dose in mcg/kg/min")
    norepinephrine: Optional[float] = Field(None, description="Norepinephrine dose in mcg/kg/min")
    vasopressin: Optional[float] = Field(None, description="Vasopressin dose in U/min")
    phenylephrine: Optional[float] = Field(None, description="Phenylephrine dose in mcg/kg/min")
    gcs: Optional[int] = Field(None, description="Glasgow Coma Scale score (3-15)")
    creatinine: Optional[float] = Field(None, description="Creatinine level in mg/dL")
    urine_output: Optional[float] = Field(None, description="Urine output in mL/day")

def calculate_sofa(params: SOFAParams) -> ClinicalResult:
    """
    Calculates the Sequential Organ Failure Assessment (SOFA) score.
    Returns a deterministic structured ClinicalResult, complete with source Evidence.
    """
    score = 0
    
    # Respiration
    if params.pao2_fio2 is not None:
        if params.pao2_fio2 < 100:
            score += 4
        elif params.pao2_fio2 < 200:
            score += 3
        elif params.pao2_fio2 < 300:
            score += 2
        elif params.pao2_fio2 < 400:
            score += 1
    elif params.spo2_fio2 is not None:
        if params.spo2_fio2 < 150:
            score += 4
        elif params.spo2_fio2 < 235:
            score += 3
        elif params.spo2_fio2 < 315:
            score += 2
        elif params.spo2_fio2 < 400:
            score += 1
            
    # Coagulation
    if params.platelets is not None:
        if params.platelets < 20:
            score += 4
        elif params.platelets < 50:
            score += 3
        elif params.platelets < 100:
            score += 2
        elif params.platelets < 150:
            score += 1
            
    # Liver
    if params.bilirubin is not None:
        if params.bilirubin >= 12.0:
            score += 4
        elif params.bilirubin >= 6.0:
            score += 3
        elif params.bilirubin >= 2.0:
            score += 2
        elif params.bilirubin >= 1.2:
            score += 1

    # Cardiovascular
    vaso_score = 0
    if (params.dopamine and params.dopamine > 15) or \
       (params.epinephrine and params.epinephrine > 0.1) or \
       (params.norepinephrine and params.norepinephrine > 0.1) or \
       (params.phenylephrine and params.phenylephrine > 0.1):
        vaso_score = 4
    elif (params.dopamine and params.dopamine > 5) or \
         (params.epinephrine and params.epinephrine <= 0.1) or \
         (params.norepinephrine and params.norepinephrine <= 0.1) or \
         (params.vasopressin and params.vasopressin > 0) or \
         (params.phenylephrine and params.phenylephrine <= 0.1):
        vaso_score = 3
    elif (params.dopamine and params.dopamine <= 5):
        vaso_score = 2
    elif params.map_pressure is not None and params.map_pressure < 70:
        vaso_score = 1
    score += vaso_score

    # Central nervous system
    if params.gcs is not None:
        if params.gcs < 6:
            score += 4
        elif params.gcs <= 9:
            score += 3
        elif params.gcs <= 12:
            score += 2
        elif params.gcs <= 14:
            score += 1

    # Renal
    if params.creatinine is not None:
        if params.creatinine >= 5.0 or (params.urine_output is not None and params.urine_output < 200):
            score += 4
        elif params.creatinine >= 3.5 or (params.urine_output is not None and params.urine_output < 500):
            score += 3
        elif params.creatinine >= 2.0:
            score += 2
        elif params.creatinine >= 1.2:
            score += 1
    elif params.urine_output is not None:
        if params.urine_output < 200:
            score += 4
        elif params.urine_output < 500:
            score += 3

    evidence = Evidence(
        source_doi="10.1007/BF01709751",
        level="Validation Study",
        description="The SOFA (Sepsis-related Organ Failure Assessment) score to describe organ dysfunction/failure (1996)."
    )

    if score <= 1:
        interpretation = f"The patient has a SOFA score of {score}, indicating a low mortality risk (< 10%). Organ function is generally preserved, but continuous monitoring is advised if underlying sepsis is suspected."
    elif score <= 3:
        interpretation = f"The patient has a SOFA score of {score}, indicating an increased mortality risk (~10%). There is evidence of mild organ dysfunction; early intervention and close observation are recommended."
    elif score <= 5:
        interpretation = f"The patient has a SOFA score of {score}, indicating a significant mortality risk (~20%). Moderate single or multiple organ dysfunction is present, necessitating prompt therapeutic management and critical care observation."
    elif score <= 7:
        interpretation = f"The patient has a SOFA score of {score}, indicating a high mortality risk (~30%). Severe organ dysfunction is evident, requiring aggressive critical care support to prevent further deterioration."
    elif score <= 9:
        interpretation = f"The patient has a SOFA score of {score}, indicating a very high mortality risk (~40-50%). The patient is in critical condition with substantial multi-organ failure, demanding maximal intensive care interventions."
    elif score <= 11:
        interpretation = f"The patient has a SOFA score of {score}, indicating a severe mortality risk (> 60%). The presence of profound multi-organ failure suggests a poor prognosis despite advanced life support."
    elif score <= 14:
        interpretation = f"The patient has a SOFA score of {score}, indicating an extreme mortality risk (> 80%). The patient is experiencing severe, highly critical multi-organ failure with a very high likelihood of mortality."
    else:
        interpretation = f"The patient has a SOFA score of {score}, indicating a near certain mortality risk (> 90%). The patient is in an extreme systemic collapse with near-complete failure of multiple organ systems."
        
    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="69442-2",
        fhir_system="http://loinc.org",
        fhir_display="Sequential Organ Failure Assessment [SOFA]"
    )

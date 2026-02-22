from typing import Optional
from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence

class SOFAParams(BaseModel):
    """Parameters to calculate the SOFA score."""
    pao2_fio2: float = Field(..., description="PaO2/FiO2 ratio in mmHg")
    platelets: float = Field(..., description="Platelets count in x10^3/mm^3")
    bilirubin: float = Field(..., description="Bilirubin level in mg/dL")
    map_pressure: Optional[float] = Field(None, description="Mean arterial pressure in mmHg")
    dopamine: Optional[float] = Field(None, description="Dopamine dose in mcg/kg/min")
    epinephrine: Optional[float] = Field(None, description="Epinephrine dose in mcg/kg/min")
    norepinephrine: Optional[float] = Field(None, description="Norepinephrine dose in mcg/kg/min")
    gcs: int = Field(..., description="Glasgow Coma Scale score (3-15)")
    creatinine: float = Field(..., description="Creatinine level in mg/dL")
    urine_output: Optional[float] = Field(None, description="Urine output in mL/day")

def calculate_sofa(params: SOFAParams) -> ClinicalResult:
    """
    Calculates the Sequential Organ Failure Assessment (SOFA) score.
    Returns a deterministic structured ClinicalResult, complete with source Evidence.
    """
    score = 0
    
    # Respiration
    if params.pao2_fio2 < 100:
        score += 4
    elif params.pao2_fio2 < 200:
        score += 3
    elif params.pao2_fio2 < 300:
        score += 2
    elif params.pao2_fio2 < 400:
        score += 1
        
    # Coagulation
    if params.platelets < 20:
        score += 4
    elif params.platelets < 50:
        score += 3
    elif params.platelets < 100:
        score += 2
    elif params.platelets < 150:
        score += 1
        
    # Liver
    if params.bilirubin >= 12.0:
        score += 4
    elif params.bilirubin >= 6.0:
        score += 3
    elif params.bilirubin >= 2.0:
        score += 2
    elif params.bilirubin >= 1.2:
        score += 1

    # Cardiovascular
    if (params.dopamine and params.dopamine > 15) or (params.epinephrine and params.epinephrine > 0.1) or (params.norepinephrine and params.norepinephrine > 0.1):
        score += 4
    elif (params.dopamine and params.dopamine > 5) or (params.epinephrine and params.epinephrine <= 0.1) or (params.norepinephrine and params.norepinephrine <= 0.1):
        score += 3
    elif (params.dopamine and params.dopamine <= 5):
        score += 2
    elif params.map_pressure and params.map_pressure < 70:
        score += 1

    # Central nervous system
    if params.gcs < 6:
        score += 4
    elif params.gcs <= 9:
        score += 3
    elif params.gcs <= 12:
        score += 2
    elif params.gcs <= 14:
        score += 1

    # Renal
    if params.creatinine >= 5.0 or (params.urine_output is not None and params.urine_output < 200):
        score += 4
    elif params.creatinine >= 3.5 or (params.urine_output is not None and params.urine_output < 500):
        score += 3
    elif params.creatinine >= 2.0:
        score += 2
    elif params.creatinine >= 1.2:
        score += 1

    evidence = Evidence(
        source_doi="10.1007/BF01709751",
        level="Validation Study",
        description="The SOFA (Sepsis-related Organ Failure Assessment) score to describe organ dysfunction/failure (1996)."
    )

    interpretation = "Higher scores are associated with an increased probability of mortality."
    
    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="69442-2",
        fhir_system="http://loinc.org",
        fhir_display="Sequential Organ Failure Assessment [SOFA]"
    )

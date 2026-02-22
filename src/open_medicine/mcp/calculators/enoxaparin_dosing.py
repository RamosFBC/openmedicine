from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence
from enum import Enum

class EnoxaparinIndication(str, Enum):
    VTE_TREATMENT = "vte_treatment"
    VTE_PROPHYLAXIS = "vte_prophylaxis"

class EnoxaparinDosingParams(BaseModel):
    """Parameters to calculate Enoxaparin dosing based on CrCl and weight."""
    crcl: float = Field(..., description="Estimated Creatinine Clearance (CrCl) in mL/min")
    weight: float = Field(..., description="Patient weight in kg")
    indication: EnoxaparinIndication = Field(..., description="The clinical indication for Enoxaparin")

def calculate_enoxaparin_dosing(params: EnoxaparinDosingParams) -> ClinicalResult:
    """
    Determines the appropriate FDA-approved Enoxaparin (Lovenox) dosage
    based on weight, indication, and severe renal impairment adjustments.
    """
    crcl = params.crcl
    weight = params.weight
    ind = params.indication
    
    dose_str = ""
    
    if ind == EnoxaparinIndication.VTE_PROPHYLAXIS:
        if crcl >= 30:
            dose_str = "40 mg subcutaneously once daily (or 30 mg twice daily depending on specific surgical risk)."
        else:
            dose_str = "30 mg subcutaneously once daily."
            
    elif ind == EnoxaparinIndication.VTE_TREATMENT:
        standard_mg = round(1.0 * weight, 1) # 1 mg/kg
        if crcl >= 30:
            dose_str = f"{standard_mg} mg subcutaneously every 12 hours (1 mg/kg) OR {round(1.5 * weight, 1)} mg subcutaneously once daily (1.5 mg/kg)."
        else:
            dose_str = f"{standard_mg} mg subcutaneously ONCE daily (1 mg/kg)."

    interpretation = f"With a CrCl of {crcl} mL/min and weight of {weight} kg for indication '{ind.value}', the recommended Enoxaparin (Lovenox) dosage is: {dose_str}"

    evidence = Evidence(
        source_doi="FDA Package Insert",
        level="Clinical Guidelines",
        description="Enoxaparin prescribing information detailing renal dosage modifications for CrCl < 30 mL/min."
    )

    return ClinicalResult(
        value=crcl,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="2160-0",
        fhir_system="http://loinc.org",
        fhir_display="Creatinine renal clearance"
    )

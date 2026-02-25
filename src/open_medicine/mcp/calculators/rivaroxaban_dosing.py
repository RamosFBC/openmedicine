from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence
from enum import Enum

class RivaroxabanIndication(str, Enum):
    NVAF = "nvaf"
    VTE_TREATMENT = "vte_treatment"
    VTE_PROPHYLAXIS = "vte_prophylaxis"

class RivaroxabanDosingParams(BaseModel):
    """Parameters to calculate Rivaroxaban dosing based on CrCl."""
    crcl: float = Field(..., description="Estimated Creatinine Clearance (CrCl) in mL/min")
    indication: RivaroxabanIndication = Field(..., description="The clinical indication for Rivaroxaban")

def calculate_rivaroxaban_dosing(params: RivaroxabanDosingParams) -> ClinicalResult:
    """
    Determines the appropriate FDA-approved Rivaroxaban dosage based on
    creatinine clearance and the specific indication.
    """
    crcl = params.crcl
    ind = params.indication
    
    dose_str = ""
    
    if ind == RivaroxabanIndication.NVAF:
        if crcl > 50:
            dose_str = "20 mg once daily with the evening meal."
        elif 15 <= crcl <= 50:
            dose_str = "15 mg once daily with the evening meal."
        else:
            dose_str = "Avoid. Generally not recommended in ESRD / CrCl < 15 mL/min."
            
    elif ind == RivaroxabanIndication.VTE_TREATMENT:
        if crcl >= 30:
            dose_str = "15 mg twice daily for 21 days, followed by 20 mg once daily."
        elif 15 <= crcl < 30:
            dose_str = "Use with caution. Bleeding risk increased. (Standard: 15 mg twice daily for 21 days, followed by 20 mg once daily, but evaluate risk)."
        else:
            dose_str = "Avoid. Use is not recommended."
            
    elif ind == RivaroxabanIndication.VTE_PROPHYLAXIS:
        if crcl >= 30:
            dose_str = "10 mg once daily."
        else: # < 30
            dose_str = "Avoid. Use is not recommended."

    interpretation = f"With a CrCl of {crcl} mL/min for indication '{ind.value}', the recommended Rivaroxaban (Xarelto) dosage is: {dose_str}"

    evidence = Evidence(
        source_doi="10.1056/NEJMoa1009638",
        level="Randomized Controlled Trial",
        description="Patel MR et al. Rivaroxaban versus warfarin in nonvalvular atrial fibrillation (ROCKET AF). N Engl J Med. 2011;365(10):883-891."
    )

    return ClinicalResult(
        value=crcl, # Return the CrCl as the base value
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="2160-0", # Mapping to the renal function used
        fhir_system="http://loinc.org",
        fhir_display="Creatinine renal clearance"
    )

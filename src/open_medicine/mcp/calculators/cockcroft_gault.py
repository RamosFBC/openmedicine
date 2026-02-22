from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence

class CockcroftGaultParams(BaseModel):
    """Parameters to calculate the Cockcroft-Gault Creatinine Clearance (CrCl)."""
    age: int = Field(..., description="Age in years")
    weight: float = Field(..., description="Weight in kg")
    is_female: bool = Field(..., description="Is the patient female?")
    serum_creatinine: float = Field(..., description="Serum creatinine in mg/dL")

def calculate_cockcroft_gault(params: CockcroftGaultParams) -> ClinicalResult:
    """
    Calculates the estimated Creatinine Clearance (CrCl) using the
    1976 Cockcroft-Gault equation. This is the global standard for
    renal medication dosage adjustments.
    (Cockcroft DW, Gault MH. Nephron. 1976;16(1):31-41)
    Returns a ClinicalResult with interpretation and evidence.
    """
    # Math: [(140 - Age) * Weight] / (72 * SCr) * [0.85 if female]
    base_calc = ((140 - params.age) * params.weight) / (72 * params.serum_creatinine)
    
    if params.is_female:
        base_calc *= 0.85
        
    crcl_rounded = round(base_calc, 1)

    # General Renal Dosing Bands
    if crcl_rounded >= 50:
        interpretation = f"Estimated CrCl is {crcl_rounded} mL/min. >50 mL/min typically requires NO dosage adjustment for renally cleared medications."
    elif 10 <= crcl_rounded < 50:
        interpretation = f"Estimated CrCl is {crcl_rounded} mL/min. 10-50 mL/min typically requires moderate dosage reduction or extended dosing intervals for renally cleared medications."
    else:
        interpretation = f"Estimated CrCl is {crcl_rounded} mL/min. <10 mL/min suggests severe renal impairment or dialysis dependency. Significant dosage adjustments or avoidance of nephrotoxic drugs are required."

    evidence = Evidence(
        source_doi="10.1159/000180580",
        level="Validation Study",
        description="Prediction of Creatinine Clearance from Serum Creatinine (Cockcroft DW, Gault MH, 1976)"
    )

    return ClinicalResult(
        value=crcl_rounded,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="2160-0",
        fhir_system="http://loinc.org",
        fhir_display="Creatinine renal clearance"
    )

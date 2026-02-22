import math
from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence

class CKDEPIParams(BaseModel):
    """Parameters to calculate the 2021 race-free CKD-EPI GFR."""
    age: int = Field(..., description="Age in years")
    is_female: bool = Field(..., description="Is the patient female?")
    serum_creatinine: float = Field(..., description="Serum creatinine in mg/dL")

def calculate_ckd_epi(params: CKDEPIParams) -> ClinicalResult:
    """
    Calculates the estimated Glomerular Filtration Rate (eGFR) using the
    2021 CKD-EPI creatinine equation (without race).
    (Inker LA, et al. N Engl J Med 2021; 385:1737-1749)
    Returns a ClinicalResult with interpretation and evidence.
    """
    # 2021 Coefficients
    kappa = 0.7 if params.is_female else 0.9
    alpha = -0.241 if params.is_female else -0.302
    female_multiplier = 1.012 if params.is_female else 1.0
    
    scr_over_kappa = params.serum_creatinine / kappa
    min_term = min(scr_over_kappa, 1.0)
    max_term = max(scr_over_kappa, 1.0)

    # eGFR = 142 * min(Scr/κ, 1)^α * max(Scr/κ, 1)^-1.200 * 0.9938^Age * 1.012 [if female]
    egfr = (
        142.0 
        * (min_term ** alpha) 
        * (max_term ** -1.200) 
        * (0.9938 ** params.age) 
        * female_multiplier
    )
    
    egfr_rounded = round(egfr, 1)

    # KDIGO GFR Categories
    if egfr_rounded >= 90:
        interpretation = f"eGFR is {egfr_rounded} mL/min/1.73m2. Stage G1: Normal or high."
    elif 60 <= egfr_rounded < 90:
        interpretation = f"eGFR is {egfr_rounded} mL/min/1.73m2. Stage G2: Mildly decreased."
    elif 45 <= egfr_rounded < 60:
        interpretation = f"eGFR is {egfr_rounded} mL/min/1.73m2. Stage G3a: Mildly to moderately decreased."
    elif 30 <= egfr_rounded < 45:
        interpretation = f"eGFR is {egfr_rounded} mL/min/1.73m2. Stage G3b: Moderately to severely decreased."
    elif 15 <= egfr_rounded < 30:
        interpretation = f"eGFR is {egfr_rounded} mL/min/1.73m2. Stage G4: Severely decreased."
    else:
        interpretation = f"eGFR is {egfr_rounded} mL/min/1.73m2. Stage G5: Kidney failure."

    evidence = Evidence(
        source_doi="10.1056/NEJMoa2102953",
        level="Validation Study",
        description="New Creatinine- and Cystatin C-Based Equations to Estimate GFR without Race (CKD-EPI 2021)"
    )

    return ClinicalResult(
        value=egfr_rounded,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="62238-1",
        fhir_system="http://loinc.org",
        fhir_display="Glomerular filtration rate/1.73 sq M.predicted"
    )

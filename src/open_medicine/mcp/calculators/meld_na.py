import math
from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class MELDNaParams(BaseModel):
    """Parameters to calculate the MELD-Na Score."""
    creatinine: float = Field(..., description="Serum creatinine in mg/dL")
    bilirubin: float = Field(..., description="Total bilirubin in mg/dL")
    inr: float = Field(..., description="International Normalized Ratio")
    sodium: float = Field(..., description="Serum sodium in mEq/L")
    on_dialysis: bool = Field(False, description="On dialysis (≥2 sessions/week or CVVHD ≥24h in past week)")


def calculate_meld_na(params: MELDNaParams) -> ClinicalResult:
    """
    Calculates the MELD-Na (Model for End-Stage Liver Disease with Sodium) score.
    Reference: Kim WR et al. Hepatology 2008.
    """
    # Apply bounds per UNOS policy
    cr = params.creatinine
    if params.on_dialysis:
        cr = 4.0
    cr = max(cr, 1.0)
    cr = min(cr, 4.0)

    bili = max(params.bilirubin, 1.0)
    inr = max(params.inr, 1.0)

    # Cap sodium
    na = max(params.sodium, 125.0)
    na = min(na, 137.0)

    # MELD(i) = 0.957 × ln(Cr) + 0.378 × ln(Bili) + 1.120 × ln(INR) + 0.643
    # Then multiply by 10 and round
    meld_i = 0.957 * math.log(cr) + 0.378 * math.log(bili) + 1.120 * math.log(inr) + 0.643
    meld_i = round(meld_i * 10)

    # Ensure MELD(i) has a floor of 1 for the Na adjustment
    meld_i = max(meld_i, 1)

    # MELD-Na = MELD(i) - Na - [0.025 × MELD(i) × (140 - Na)] + 140
    meld_na = meld_i - na - (0.025 * meld_i * (140.0 - na)) + 140.0
    meld_na = round(meld_na)

    # Final bounds: 6-40
    meld_na = max(meld_na, 6)
    meld_na = min(meld_na, 40)

    # Interpretation based on 90-day mortality estimates
    if meld_na <= 9:
        interpretation = f"MELD-Na score is {meld_na}. Low 90-day mortality risk (~1.9%)."
    elif meld_na <= 19:
        interpretation = f"MELD-Na score is {meld_na}. Moderate 90-day mortality risk (~6%)."
    elif meld_na <= 29:
        interpretation = f"MELD-Na score is {meld_na}. High 90-day mortality risk (~19.6%)."
    elif meld_na <= 39:
        interpretation = f"MELD-Na score is {meld_na}. Very high 90-day mortality risk (~52.6%)."
    else:
        interpretation = f"MELD-Na score is {meld_na}. Maximum score; very high 90-day mortality risk (~71.3%)."

    evidence = Evidence(
        source_doi="10.1002/hep.22023",
        level="Derivation & Validation Study",
        description="Hyponatremia and Mortality among Patients on the Liver-Transplant Waiting List (Kim WR et al. Hepatology 2008)"
    )

    return ClinicalResult(
        value=meld_na,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="75622-1",
        fhir_system="http://loinc.org",
        fhir_display="MELD-Na score"
    )

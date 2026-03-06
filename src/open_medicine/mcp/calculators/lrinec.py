from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class LRINECParams(BaseModel):
    """Parameters to calculate the LRINEC (Laboratory Risk Indicator for Necrotizing Fasciitis) score."""
    crp: float = Field(..., description="C-reactive protein (CRP) in mg/L")
    wbc: float = Field(..., description="White blood cell count in x10^3/uL (thousands per microliter)")
    hemoglobin: float = Field(..., description="Hemoglobin in g/dL")
    sodium: float = Field(..., description="Serum sodium in mEq/L (mmol/L)")
    creatinine: float = Field(..., description="Serum creatinine in mg/dL")
    glucose: float = Field(..., description="Serum glucose in mg/dL")


def calculate_lrinec(params: LRINECParams) -> ClinicalResult:
    """
    Calculates the LRINEC (Laboratory Risk Indicator for Necrotizing Fasciitis) score.
    Distinguishes necrotizing fasciitis from other soft tissue infections using six
    routine laboratory values.
    Reference: Wong CH et al. Crit Care Med. 2004;32(7):1535-1541.
    """
    score = 0

    # CRP (mg/L): <150 = 0 points, >=150 = 4 points
    if params.crp >= 150:
        score += 4

    # WBC (x10^3/uL): <15 = 0 points, 15-25 = 1 point, >25 = 2 points
    if params.wbc > 25:
        score += 2
    elif params.wbc >= 15:
        score += 1

    # Hemoglobin (g/dL): >13.5 = 0 points, 11-13.5 = 1 point, <11 = 2 points
    if params.hemoglobin < 11:
        score += 2
    elif params.hemoglobin <= 13.5:
        score += 1

    # Sodium (mEq/L): >=135 = 0 points, <135 = 2 points
    if params.sodium < 135:
        score += 2

    # Creatinine (mg/dL): <=1.6 = 0 points, >1.6 = 2 points
    if params.creatinine > 1.6:
        score += 2

    # Glucose (mg/dL): <=180 = 0 points, >180 = 1 point
    if params.glucose > 180:
        score += 1

    evidence = Evidence(
        source_doi="10.1097/01.CCM.0000121422.83937.48",
        level="Derivation & Validation Study",
        description="The LRINEC score: a tool for distinguishing necrotizing fasciitis from other soft tissue infections."
    )

    if score <= 5:
        interpretation = (
            f"LRINEC score is {score}. Low risk (<50% probability of necrotizing fasciitis). "
            f"Necrotizing fasciitis is unlikely but cannot be excluded clinically. "
            f"Note: ~10% of confirmed NF cases had LRINEC <6."
        )
    elif score <= 7:
        interpretation = (
            f"LRINEC score is {score}. Moderate risk (50-75% probability of necrotizing fasciitis). "
            f"Consider urgent surgical consultation and advanced imaging (CT/MRI). "
            f"Maintain high clinical suspicion."
        )
    else:
        interpretation = (
            f"LRINEC score is {score}. High risk (>75% probability of necrotizing fasciitis). "
            f"Strongly predictive of necrotizing fasciitis. "
            f"Urgent surgical exploration recommended. Do not delay for imaging."
        )

    # No LOINC observation code exists for the LRINEC score.
    # Setting fhir_code to None to avoid misrepresenting the output concept.
    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code=None,
        fhir_system="http://loinc.org",
        fhir_display="LRINEC (Laboratory Risk Indicator for Necrotizing Fasciitis) score"
    )

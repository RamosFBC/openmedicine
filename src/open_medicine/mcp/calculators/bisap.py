from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class BISAPParams(BaseModel):
    """Parameters to calculate the BISAP Score for acute pancreatitis severity."""
    bun: float = Field(..., description="Blood Urea Nitrogen (BUN) in mg/dL")
    gcs: int = Field(..., ge=3, le=15, description="Glasgow Coma Scale score (3-15)")
    age: int = Field(..., description="Age in years")
    pleural_effusion: bool = Field(..., description="Pleural effusion present on imaging")
    # SIRS components
    temperature: float = Field(..., description="Body temperature in °C")
    heart_rate: int = Field(..., description="Heart rate in beats per minute")
    respiratory_rate: int = Field(..., description="Respiratory rate in breaths per minute")
    wbc: float = Field(..., description="White blood cell count in cells/µL (e.g., 13000)")
    pco2: float = Field(40.0, description="Arterial pCO2 in mmHg (used as alternative to RR for SIRS)")


def calculate_bisap(params: BISAPParams) -> ClinicalResult:
    """
    Calculates the BISAP (Bedside Index for Severity in Acute Pancreatitis) score.

    Reference: Wu BU et al. Gut. 2008;57(12):1698-1703.
    """
    score = 0

    # B: BUN > 25 mg/dL
    if params.bun > 25:
        score += 1

    # I: Impaired mental status (GCS < 15)
    if params.gcs < 15:
        score += 1

    # S: SIRS (≥2 of 4 criteria)
    sirs_count = 0
    if params.temperature > 38 or params.temperature < 36:
        sirs_count += 1
    if params.heart_rate > 90:
        sirs_count += 1
    if params.respiratory_rate > 20 or params.pco2 < 32:
        sirs_count += 1
    if params.wbc > 12000 or params.wbc < 4000:
        sirs_count += 1
    if sirs_count >= 2:
        score += 1

    # A: Age > 60
    if params.age > 60:
        score += 1

    # P: Pleural effusion
    if params.pleural_effusion:
        score += 1

    evidence = Evidence(
        source_doi="10.1136/gut.2008.150938",
        level="Derivation & Validation Study",
        description="The early prediction of mortality in acute pancreatitis: a large population-based study."
    )

    mortality_map = {0: "~1%", 1: "~2%", 2: "~4%", 3: "~8%", 4: "~15%", 5: "~25%"}
    mortality = mortality_map[score]

    if score <= 1:
        interpretation = f"BISAP Score is {score}. Low risk. Estimated mortality {mortality}."
    elif score <= 2:
        interpretation = f"BISAP Score is {score}. Moderate risk. Estimated mortality {mortality}. Close monitoring recommended."
    else:
        interpretation = f"BISAP Score is {score}. High risk. Estimated mortality {mortality}. Consider ICU admission and aggressive management."

    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="LP419518-4",  # LOINC approximation: no specific BISAP code exists
        fhir_system="http://loinc.org",
        fhir_display="BISAP Score"
    )

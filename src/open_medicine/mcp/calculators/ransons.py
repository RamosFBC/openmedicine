from typing import Optional
from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class RansonsParams(BaseModel):
    """Parameters to calculate Ranson's Criteria for acute pancreatitis severity."""
    # Admission criteria (required)
    age: int = Field(..., description="Age in years")
    wbc: float = Field(..., description="White blood cell count in cells/µL")
    blood_glucose: float = Field(..., description="Blood glucose in mg/dL")
    ldh: float = Field(..., description="Lactate dehydrogenase (LDH) in IU/L")
    ast: float = Field(..., description="Aspartate aminotransferase (AST) in IU/L")
    # 48-hour criteria (optional — may not be available yet)
    hematocrit_decrease: Optional[float] = Field(None, description="Hematocrit decrease from admission in percentage points (e.g., 12 means 12% drop)")
    bun_increase: Optional[float] = Field(None, description="BUN increase from admission in mg/dL")
    calcium: Optional[float] = Field(None, description="Serum calcium in mg/dL")
    pao2: Optional[float] = Field(None, description="Arterial PaO2 in mmHg")
    base_deficit: Optional[float] = Field(None, description="Base deficit in mEq/L (positive value indicates deficit)")
    fluid_sequestration: Optional[float] = Field(None, description="Estimated fluid sequestration in liters")


def calculate_ransons(params: RansonsParams) -> ClinicalResult:
    """
    Calculates Ranson's Criteria for acute pancreatitis severity.
    Returns admission-only score if 48-hour criteria are not provided.

    Reference: Ranson JH et al. Surg Gynecol Obstet. 1974;139:69-81.
    """
    score = 0
    has_48h = False

    # Admission criteria
    if params.age > 55:
        score += 1
    if params.wbc > 16000:
        score += 1
    if params.blood_glucose > 200:
        score += 1
    if params.ldh > 350:
        score += 1
    if params.ast > 250:
        score += 1

    admission_score = score

    # 48-hour criteria
    if params.hematocrit_decrease is not None:
        has_48h = True
        if params.hematocrit_decrease > 10:
            score += 1
    if params.bun_increase is not None:
        has_48h = True
        if params.bun_increase > 5:
            score += 1
    if params.calcium is not None:
        has_48h = True
        if params.calcium < 8:
            score += 1
    if params.pao2 is not None:
        has_48h = True
        if params.pao2 < 60:
            score += 1
    if params.base_deficit is not None:
        has_48h = True
        if params.base_deficit > 4:
            score += 1
    if params.fluid_sequestration is not None:
        has_48h = True
        if params.fluid_sequestration > 6:
            score += 1

    evidence = Evidence(
        source_doi="10.1097/00000658-197401000-00001",
        level="Derivation & Validation Study",
        description="Prognostic signs and the role of operative management in acute pancreatitis."
    )

    if has_48h:
        score_label = f"Ranson's Score is {score} (admission: {admission_score}, 48h criteria included)"
    else:
        score_label = f"Ranson's Score is {score} (admission criteria only, 48h criteria pending)"

    if score <= 2:
        interpretation = f"{score_label}. Predicted mortality ~2%. Mild pancreatitis."
    elif score <= 4:
        interpretation = f"{score_label}. Predicted mortality ~15%. Moderate severity."
    elif score <= 6:
        interpretation = f"{score_label}. Predicted mortality ~40%. Severe pancreatitis. ICU admission recommended."
    else:
        interpretation = f"{score_label}. Predicted mortality approaching 100%. Critical severity. Aggressive ICU management required."

    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="LP419518-4",  # LOINC approximation: no specific Ranson's code exists
        fhir_system="http://loinc.org",
        fhir_display="Ranson's Criteria score"
    )

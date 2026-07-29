from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from open_medicine.mcp.base import ClinicalResult, Evidence

# Related guidelines: nice_ugib_2012 (risk_assessment, endoscopic_management sections)

class RockallComorbidity(str, Enum):
    NONE = "none"
    MAJOR = "major"
    RENAL_LIVER_MALIGNANCY = "renal_liver_malignancy"


class RockallDiagnosis(str, Enum):
    MALLORY_WEISS = "mallory_weiss"
    OTHER = "other"
    MALIGNANCY = "malignancy"


class RockallStigmata(str, Enum):
    NONE = "none"
    PRESENT = "present"


class RockallParams(BaseModel):
    """Parameters to calculate the Rockall Score for upper GI bleeding."""
    age: int = Field(..., description="Age in years")
    pulse: int = Field(..., description="Heart rate in beats per minute")
    systolic_bp: int = Field(..., description="Systolic blood pressure in mmHg")
    comorbidity: RockallComorbidity = Field(RockallComorbidity.NONE, description="Comorbidity: none, major (CHF/IHD/major comorbidity), or renal_liver_malignancy (renal failure, liver failure, disseminated malignancy)")
    diagnosis: Optional[RockallDiagnosis] = Field(None, description="Endoscopic diagnosis: mallory_weiss, other, or malignancy. Leave empty for pre-endoscopy score only.")
    stigmata: Optional[RockallStigmata] = Field(None, description="Stigmata of recent hemorrhage: none (clean base/dark spot) or present (blood/clot/visible vessel/spurting). Leave empty for pre-endoscopy score only.")


def calculate_rockall(params: RockallParams) -> ClinicalResult:
    """
    Calculates the Rockall Score for rebleeding and mortality risk after upper GI bleeding.
    Returns pre-endoscopy score if endoscopic findings are not provided.

    Reference: Rockall TA et al. Gut. 1996;38(3):316-321.
    """
    score = 0

    # Age
    if params.age >= 80:
        score += 2
    elif params.age >= 60:
        score += 1

    # Shock
    if params.systolic_bp < 100:
        score += 2
    elif params.pulse > 100:
        score += 1

    # Comorbidity
    if params.comorbidity == RockallComorbidity.RENAL_LIVER_MALIGNANCY:
        score += 3
    elif params.comorbidity == RockallComorbidity.MAJOR:
        score += 2

    pre_endoscopy_score = score
    is_full = params.diagnosis is not None or params.stigmata is not None

    # Post-endoscopy components
    if params.diagnosis is not None:
        if params.diagnosis == RockallDiagnosis.MALIGNANCY:
            score += 2
        elif params.diagnosis == RockallDiagnosis.OTHER:
            score += 1

    if params.stigmata is not None:
        if params.stigmata == RockallStigmata.PRESENT:
            score += 2

    evidence = Evidence(
        source_doi="10.1136/gut.38.3.316",
        level="Derivation & Validation Study",
        description="Risk assessment after acute upper gastrointestinal haemorrhage."
    )

    if is_full:
        score_label = f"Full Rockall Score is {score} (pre-endoscopy: {pre_endoscopy_score})"
    else:
        score_label = f"Pre-endoscopy Rockall Score is {score}"

    if score <= 2:
        interpretation = f"{score_label}. Low risk of rebleeding and mortality."
    elif score <= 4:
        interpretation = f"{score_label}. Moderate risk of rebleeding and mortality."
    else:
        interpretation = f"{score_label}. High risk of rebleeding and mortality. Intensive monitoring and intervention recommended."

    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="LP419518-4",  # LOINC approximation: no specific Rockall code exists
        fhir_system="http://loinc.org",
        fhir_display="Rockall Score"
    )

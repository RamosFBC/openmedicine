from enum import Enum
from pydantic import BaseModel, Field
from open_medicine.mcp.base import ClinicalResult, Evidence


class ABCD2ClinicalFeature(str, Enum):
    UNILATERAL_WEAKNESS = "unilateral_weakness"
    SPEECH_DISTURBANCE = "speech_disturbance"
    OTHER = "other"


class ABCD2Duration(str, Enum):
    GE_60_MIN = "ge_60_min"
    TEN_TO_59_MIN = "10_to_59_min"
    LT_10_MIN = "lt_10_min"


class ABCD2Params(BaseModel):
    """Parameters to calculate the ABCD2 Score for TIA stroke risk."""
    age_ge_60: bool = Field(..., description="Age ≥ 60 years")
    bp_ge_140_90: bool = Field(..., description="Blood pressure ≥ 140/90 mmHg at initial evaluation")
    clinical_features: ABCD2ClinicalFeature = Field(..., description="Clinical features: unilateral_weakness (2pts), speech_disturbance without weakness (1pt), other (0pts)")
    duration: ABCD2Duration = Field(..., description="Duration of TIA symptoms: ge_60_min (2pts), 10_to_59_min (1pt), lt_10_min (0pts)")
    diabetes: bool = Field(False, description="History of diabetes mellitus")


def calculate_abcd2(params: ABCD2Params) -> ClinicalResult:
    """
    Calculates the ABCD2 Score for risk of stroke after TIA.
    Reference: Johnston SC et al. Lancet. 2007;369(9558):283-292.
    """
    score = 0

    # A: Age
    if params.age_ge_60:
        score += 1

    # B: Blood pressure
    if params.bp_ge_140_90:
        score += 1

    # C: Clinical features
    if params.clinical_features == ABCD2ClinicalFeature.UNILATERAL_WEAKNESS:
        score += 2
    elif params.clinical_features == ABCD2ClinicalFeature.SPEECH_DISTURBANCE:
        score += 1

    # D: Duration
    if params.duration == ABCD2Duration.GE_60_MIN:
        score += 2
    elif params.duration == ABCD2Duration.TEN_TO_59_MIN:
        score += 1

    # D2: Diabetes
    if params.diabetes:
        score += 1

    evidence = Evidence(
        source_doi="10.1016/S0140-6736(07)60150-0",
        level="Derivation & Validation Study",
        description="Validation and refinement of scores to predict very early stroke risk after TIA (Johnston SC et al., Lancet 2007)"
    )

    if score <= 3:
        risk = "Low risk (1.0% 2-day stroke risk)"
    elif score <= 5:
        risk = "Moderate risk (4.1% 2-day stroke risk)"
    else:
        risk = "High risk (8.1% 2-day stroke risk)"

    interpretation = f"ABCD2 score is {score}. {risk}."

    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="72090-4",  # LOINC approximation: no exact ABCD2 code; using stroke risk assessment
        fhir_system="http://loinc.org",
        fhir_display="ABCD2 score"
    )

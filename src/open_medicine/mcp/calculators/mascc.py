from enum import Enum
from pydantic import BaseModel, Field
from open_medicine.mcp.base import ClinicalResult, Evidence


class BurdenOfIllness(str, Enum):
    """Burden of febrile neutropenia at presentation, assessed as general clinical status."""
    NONE_OR_MILD = "none_or_mild"
    MODERATE = "moderate"
    SEVERE = "severe"


class CancerType(str, Enum):
    """Type of underlying malignancy and fungal infection history."""
    SOLID_TUMOR = "solid_tumor"
    HEMATOLOGIC_NO_FUNGAL = "hematologic_no_prior_fungal"
    HEMATOLOGIC_PRIOR_FUNGAL = "hematologic_prior_fungal"


class MASCCParams(BaseModel):
    """Parameters to calculate the MASCC Risk Index for febrile neutropenia."""
    burden_of_illness: BurdenOfIllness = Field(
        ...,
        description=(
            "Burden of febrile neutropenia at presentation: "
            "'none_or_mild' = no or mild symptoms, "
            "'moderate' = moderate symptoms, "
            "'severe' = severe symptoms or moribund. "
            "Only one category applies (not cumulative)."
        )
    )
    hypotension: bool = Field(
        ...,
        description="Systolic blood pressure < 90 mmHg at presentation"
    )
    active_copd: bool = Field(
        False,
        description=(
            "Active chronic obstructive pulmonary disease (COPD), "
            "including chronic bronchitis, emphysema, or need for "
            "oxygen therapy, corticosteroids, and/or bronchodilators"
        )
    )
    cancer_type: CancerType = Field(
        ...,
        description=(
            "Type of underlying malignancy: "
            "'solid_tumor' = solid tumor of any type, "
            "'hematologic_no_prior_fungal' = hematologic malignancy without prior fungal infection, "
            "'hematologic_prior_fungal' = hematologic malignancy with prior fungal infection"
        )
    )
    dehydration: bool = Field(
        False,
        description="Dehydration requiring IV fluid resuscitation at presentation"
    )
    outpatient_status: bool = Field(
        ...,
        description="Patient was an outpatient at onset of febrile neutropenia"
    )
    age: int = Field(
        ...,
        description="Age in years"
    )


def calculate_mascc(params: MASCCParams) -> ClinicalResult:
    """
    Calculates the MASCC (Multinational Association for Supportive Care in Cancer)
    Risk Index for identifying low-risk febrile neutropenia patients.

    Reference: Klastersky J et al. J Clin Oncol. 2000;18(16):3038-3051.
    """
    score = 0

    # Burden of illness (mutually exclusive, not cumulative)
    # None or mild symptoms: +5, Moderate: +3, Severe: 0
    if params.burden_of_illness == BurdenOfIllness.NONE_OR_MILD:
        score += 5
    elif params.burden_of_illness == BurdenOfIllness.MODERATE:
        score += 3
    # Severe adds 0 points

    # No hypotension (systolic BP >= 90 mmHg): +5
    if not params.hypotension:
        score += 5

    # No active COPD: +4
    if not params.active_copd:
        score += 4

    # Cancer type (mutually exclusive)
    # Solid tumor or hematologic without prior fungal: +4
    # Hematologic with prior fungal infection: 0
    if params.cancer_type in (CancerType.SOLID_TUMOR, CancerType.HEMATOLOGIC_NO_FUNGAL):
        score += 4

    # No dehydration requiring IV fluids: +3
    if not params.dehydration:
        score += 3

    # Outpatient at fever onset: +3
    if params.outpatient_status:
        score += 3

    # Age < 60 years: +2
    if params.age < 60:
        score += 2

    evidence = Evidence(
        source_doi="10.1200/JCO.2000.18.16.3038",
        level="Derivation & Validation Study",
        description=(
            "The Multinational Association for Supportive Care in Cancer risk index: "
            "A multinational scoring system for identifying low-risk febrile neutropenic "
            "cancer patients. Klastersky J et al. J Clin Oncol. 2000."
        )
    )

    if score >= 21:
        interpretation = (
            f"MASCC Risk Index is {score}. Low risk for serious complications of febrile "
            f"neutropenia (positive predictive value 91%, specificity 68%, sensitivity 71%). "
            f"Consider outpatient management with oral empiric antibiotics if clinically appropriate."
        )
    else:
        interpretation = (
            f"MASCC Risk Index is {score}. High risk for serious complications of febrile "
            f"neutropenia. Requires inpatient admission and intravenous empiric antibiotic therapy."
        )

    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        # No LOINC observation code exists for the MASCC Risk Index score.
        # LP419468-2 is a LOINC Part code (not an observation code), so using
        # None to avoid semantic misrepresentation.
        fhir_code=None,
        fhir_system=None,
        fhir_display="MASCC Risk Index score"
    )

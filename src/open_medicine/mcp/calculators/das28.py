import math
from enum import Enum
from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence

# Related guidelines: acr_ra_2021 (disease activity assessment)


class DAS28Variant(str, Enum):
    """DAS28 formula variant selection."""
    ESR = "esr"
    CRP = "crp"


class DAS28Params(BaseModel):
    """Parameters to calculate the DAS28 (Disease Activity Score 28) for Rheumatoid Arthritis."""
    tender_joint_count: int = Field(
        ...,
        ge=0,
        le=28,
        description="Number of tender joints out of 28 assessed (0-28)"
    )
    swollen_joint_count: int = Field(
        ...,
        ge=0,
        le=28,
        description="Number of swollen joints out of 28 assessed (0-28)"
    )
    esr: float = Field(
        None,
        description="Erythrocyte sedimentation rate in mm/hr. Required when variant is 'esr'."
    )
    crp: float = Field(
        None,
        description="C-reactive protein in mg/L. Required when variant is 'crp'."
    )
    global_health: float = Field(
        ...,
        ge=0,
        le=100,
        description="Patient global health assessment on 100mm visual analogue scale (0=best, 100=worst)"
    )
    variant: DAS28Variant = Field(
        DAS28Variant.ESR,
        description="Formula variant: 'esr' for DAS28-ESR (default) or 'crp' for DAS28-CRP"
    )


def calculate_das28(params: DAS28Params) -> ClinicalResult:
    """
    Calculates the DAS28 (Disease Activity Score 28) for rheumatoid arthritis.
    Supports both DAS28-ESR and DAS28-CRP variants.
    Reference: Prevoo MLL et al. Arthritis Rheum. 1995;38(1):44-48.
    DAS28-CRP validated by Wells G et al. Ann Rheum Dis. 2009;68(6):954-960.
    """
    # Validate that the required acute phase reactant is provided
    if params.variant == DAS28Variant.ESR:
        if params.esr is None:
            return ClinicalResult(
                value=None,
                interpretation="DAS28-ESR requires an ESR value. Please provide the erythrocyte sedimentation rate (mm/hr).",
                evidence=Evidence(
                    source_doi="10.1002/art.1780380107",
                    level="Derivation & Validation Study",
                    description="Prevoo MLL et al. Modified disease activity scores that include twenty-eight-joint counts. Arthritis Rheum. 1995;38(1):44-48."
                ),
                fhir_code="75633-8",
                fhir_system="http://loinc.org",
                fhir_display="Rheumatoid arthritis disease activity score"
            )
        if params.esr <= 0:
            return ClinicalResult(
                value=None,
                interpretation="DAS28-ESR cannot be calculated: ESR must be greater than 0 mm/hr.",
                evidence=Evidence(
                    source_doi="10.1002/art.1780380107",
                    level="Derivation & Validation Study",
                    description="Prevoo MLL et al. Modified disease activity scores that include twenty-eight-joint counts. Arthritis Rheum. 1995;38(1):44-48."
                ),
                fhir_code="75633-8",
                fhir_system="http://loinc.org",
                fhir_display="Rheumatoid arthritis disease activity score"
            )
    else:
        if params.crp is None:
            return ClinicalResult(
                value=None,
                interpretation="DAS28-CRP requires a CRP value. Please provide the C-reactive protein level (mg/L).",
                evidence=Evidence(
                    source_doi="10.1136/ard.2007.075945",
                    level="Validation Study",
                    description="Wells G et al. Validation of the 28-joint Disease Activity Score (DAS28) and EULAR response criteria based on CRP. Ann Rheum Dis. 2009;68(6):954-960."
                ),
                fhir_code="75633-8",
                fhir_system="http://loinc.org",
                fhir_display="Rheumatoid arthritis disease activity score"
            )
        if params.crp < 0:
            return ClinicalResult(
                value=None,
                interpretation="DAS28-CRP cannot be calculated: CRP must be >= 0 mg/L.",
                evidence=Evidence(
                    source_doi="10.1136/ard.2007.075945",
                    level="Validation Study",
                    description="Wells G et al. Validation of the 28-joint Disease Activity Score (DAS28) and EULAR response criteria based on CRP. Ann Rheum Dis. 2009;68(6):954-960."
                ),
                fhir_code="75633-8",
                fhir_system="http://loinc.org",
                fhir_display="Rheumatoid arthritis disease activity score"
            )

    # Calculate DAS28
    tjc_component = 0.56 * math.sqrt(params.tender_joint_count)
    sjc_component = 0.28 * math.sqrt(params.swollen_joint_count)
    gh_component = 0.014 * params.global_health

    if params.variant == DAS28Variant.ESR:
        # DAS28-ESR = 0.56*sqrt(TJC28) + 0.28*sqrt(SJC28) + 0.70*ln(ESR) + 0.014*GH
        apr_component = 0.70 * math.log(params.esr)
        das28 = tjc_component + sjc_component + apr_component + gh_component
        variant_label = "DAS28-ESR"
        source_doi = "10.1002/art.1780380107"
        evidence = Evidence(
            source_doi=source_doi,
            level="Derivation & Validation Study",
            description="Prevoo MLL et al. Modified disease activity scores that include twenty-eight-joint counts. Arthritis Rheum. 1995;38(1):44-48."
        )
    else:
        # DAS28-CRP = 0.56*sqrt(TJC28) + 0.28*sqrt(SJC28) + 0.36*ln(CRP+1) + 0.014*GH + 0.96
        apr_component = 0.36 * math.log(params.crp + 1)
        das28 = tjc_component + sjc_component + apr_component + gh_component + 0.96
        variant_label = "DAS28-CRP"
        source_doi = "10.1136/ard.2007.075945"
        evidence = Evidence(
            source_doi=source_doi,
            level="Validation Study",
            description="Wells G et al. Validation of the 28-joint Disease Activity Score (DAS28) and EULAR response criteria based on CRP. Ann Rheum Dis. 2009;68(6):954-960."
        )

    # Floor at 0 — negative DAS28 is not clinically meaningful
    # (can occur mathematically with very low ESR, e.g. ln(0.1) < 0)
    das28 = round(max(das28, 0.0), 2)

    # Interpret using validated thresholds
    # Prevoo 1995 / van Gestel 1996 / Fransen 2005:
    # Remission: DAS28 < 2.6
    # Low disease activity: 2.6 <= DAS28 <= 3.2
    # Moderate disease activity: 3.2 < DAS28 <= 5.1
    # High disease activity: DAS28 > 5.1
    if das28 < 2.6:
        activity_level = "Remission"
        recommendation = "Continue current therapy; monitor for sustained remission."
    elif das28 <= 3.2:
        activity_level = "Low disease activity"
        recommendation = "Consider maintaining current therapy; assess for treatment optimization."
    elif das28 <= 5.1:
        activity_level = "Moderate disease activity"
        recommendation = "Consider treatment escalation per treat-to-target strategy."
    else:
        activity_level = "High disease activity"
        recommendation = "Treatment escalation or change is recommended per treat-to-target strategy."

    interpretation = (
        f"{variant_label} is {das28}. {activity_level}. {recommendation}"
    )

    return ClinicalResult(
        value=das28,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="75633-8",
        fhir_system="http://loinc.org",
        fhir_display="Rheumatoid arthritis disease activity score"
    )

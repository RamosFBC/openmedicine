# Related guidelines: apa_aud_2018 (assessment_and_screening, psychosocial_and_combined_treatment sections)

from pydantic import BaseModel, Field
from open_medicine.mcp.base import ClinicalResult, Evidence


class AUDITCParams(BaseModel):
    """Parameters to calculate the AUDIT-C (Alcohol Use Disorders Identification Test - Consumption) score."""

    frequency: int = Field(
        ...,
        ge=0,
        le=4,
        description=(
            "How often do you have a drink containing alcohol? "
            "0=Never, 1=Monthly or less, 2=2-4 times a month, "
            "3=2-3 times a week, 4=4 or more times a week"
        ),
    )
    typical_quantity: int = Field(
        ...,
        ge=0,
        le=4,
        description=(
            "How many standard drinks containing alcohol do you have on a typical day when you are drinking? "
            "0=1-2, 1=3-4, 2=5-6, 3=7-9, 4=10 or more"
        ),
    )
    binge_frequency: int = Field(
        ...,
        ge=0,
        le=4,
        description=(
            "How often do you have six or more drinks on one occasion? "
            "0=Never, 1=Less than monthly, 2=Monthly, 3=Weekly, "
            "4=Daily or almost daily"
        ),
    )
    is_male: bool = Field(
        ...,
        description="Is the patient male? Required for sex-specific screening thresholds.",
    )


def calculate_audit_c(params: AUDITCParams) -> ClinicalResult:
    """
    Calculates the AUDIT-C (Alcohol Use Disorders Identification Test - Consumption) score.
    A validated 3-item alcohol screening questionnaire for hazardous drinking and alcohol use disorders.
    Reference: Bush K, Kivlahan DR, McDonell MB, Fihn SD, Bradley KA. Arch Intern Med. 1998;158(16):1789-1795.
    """
    # Sum all 3 items (each scored 0-4, total range 0-12)
    score = params.frequency + params.typical_quantity + params.binge_frequency

    evidence = Evidence(
        source_doi="10.1001/archinte.158.16.1789",
        level="Derivation & Validation Study",
        description=(
            "The AUDIT alcohol consumption questions (AUDIT-C): an effective brief "
            "screening test for problem drinking (Bush K et al., Arch Intern Med 1998)"
        ),
    )

    # Sex-specific screening thresholds from Bush et al. 1998:
    # Men: >= 4 is positive screen (sensitivity 0.86, specificity 0.89)
    # Women: >= 3 is positive screen (sensitivity 0.73, specificity 0.91)
    positive_threshold = 4 if params.is_male else 3

    if score == 0:
        screen_result = "Negative screen (non-drinker)"
        action = "No further alcohol screening needed at this time."
    elif score < positive_threshold:
        screen_result = "Negative screen (low-risk drinking)"
        action = "Drinking appears within lower-risk limits. Reassess periodically."
    elif score <= 7:
        screen_result = "Positive screen (hazardous drinking)"
        action = (
            "Brief intervention recommended. Assess with full AUDIT or clinical interview "
            "to evaluate for alcohol use disorder."
        )
    else:
        # Score 8-12: high likelihood of alcohol dependence / severe AUD
        screen_result = "Positive screen (likely alcohol dependence or severe alcohol use disorder)"
        action = (
            "Further diagnostic evaluation strongly recommended. Consider full AUDIT, "
            "DSM-5 criteria assessment, and referral to addiction specialist."
        )

    sex_label = "male" if params.is_male else "female"
    interpretation = (
        f"AUDIT-C score is {score} (threshold for positive screen in "
        f"{sex_label} patients: >= {positive_threshold}). {screen_result}. {action}"
    )

    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="75626-2",
        fhir_system="http://loinc.org",
        fhir_display="Total score [AUDIT-C]",
    )

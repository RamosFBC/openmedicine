# Related guidelines: ats_idsa_cap_2019 (severity_assessment section), bts_cap_2009 (severity_assessment section)
from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class CRB65Params(BaseModel):
    """Parameters to calculate the CRB-65 pneumonia severity score (no lab required)."""
    confusion: bool = Field(
        ...,
        description="New mental confusion (Abbreviated Mental Test Score <= 8, or new disorientation in person, place, or time)"
    )
    respiratory_rate: int = Field(
        ...,
        description="Respiratory rate in breaths per minute"
    )
    systolic_bp: int = Field(
        ...,
        description="Systolic blood pressure in mmHg"
    )
    diastolic_bp: int = Field(
        ...,
        description="Diastolic blood pressure in mmHg"
    )
    age: int = Field(
        ...,
        description="Age in years"
    )


def calculate_crb65(params: CRB65Params) -> ClinicalResult:
    """
    Calculates the CRB-65 score for community-acquired pneumonia severity.
    A simplified bedside score (no lab tests required) predicting 30-day mortality.
    Reference: Bauer TT et al. J Intern Med. 2006;260(1):93-101.
    """
    score = 0

    # C: Confusion
    if params.confusion:
        score += 1

    # R: Respiratory rate >= 30 breaths/min
    if params.respiratory_rate >= 30:
        score += 1

    # B: Blood pressure -- systolic < 90 OR diastolic <= 60
    if params.systolic_bp < 90 or params.diastolic_bp <= 60:
        score += 1

    # 65: Age >= 65 years
    if params.age >= 65:
        score += 1

    evidence = Evidence(
        source_doi="10.1111/j.1365-2796.2006.01657.x",
        level="Validation Study",
        description="CRB-65 predicts death from community-acquired pneumonia. Bauer TT et al. J Intern Med. 2006."
    )

    # Risk stratification per Bauer 2006 and BTS CAP guidelines
    if score == 0:
        interpretation = (
            f"CRB-65 score is {score}. Low risk (30-day mortality ~1.2%). "
            "Likely suitable for home treatment. Consider outpatient management."
        )
    elif score <= 2:
        interpretation = (
            f"CRB-65 score is {score}. Intermediate risk (30-day mortality ~8.2%). "
            "Consider hospital referral and assessment, particularly if score is 2."
        )
    else:
        interpretation = (
            f"CRB-65 score is {score}. High risk (30-day mortality ~31.3%). "
            "Urgent hospital admission required. Consider ICU admission if score is 4."
        )

    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        # LOINC approximation: no specific CRB-65 LOINC code exists; using CURB-65 panel code
        fhir_code="LP419467-4",
        fhir_system="http://loinc.org",
        fhir_display="CRB-65 score"
    )

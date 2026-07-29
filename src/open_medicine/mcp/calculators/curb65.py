# Related guidelines: bts_cap_2009 (severity_assessment section), ats_idsa_cap_2019 (severity_assessment section)
from pydantic import BaseModel, Field
from open_medicine.mcp.base import ClinicalResult, Evidence


class CURB65Params(BaseModel):
    """Parameters to calculate the CURB-65 pneumonia severity score."""
    confusion: bool = Field(..., description="New mental confusion (Abbreviated Mental Test Score <= 8, or new disorientation in person, place, or time)")
    bun: float = Field(..., description="Blood Urea Nitrogen (BUN) in mg/dL")
    respiratory_rate: int = Field(..., description="Respiratory rate in breaths per minute")
    systolic_bp: int = Field(..., description="Systolic blood pressure in mmHg")
    diastolic_bp: int = Field(..., description="Diastolic blood pressure in mmHg")
    age: int = Field(..., description="Age in years")


def calculate_curb65(params: CURB65Params) -> ClinicalResult:
    """
    Calculates the CURB-65 score for community-acquired pneumonia severity.

    Reference: Lim WS et al. Thorax. 2003;58(5):377-382.
    """
    score = 0

    # C: Confusion
    if params.confusion:
        score += 1

    # U: Urea / BUN > 20 mg/dL (equivalent to > 7 mmol/L)
    if params.bun > 20:
        score += 1

    # R: Respiratory rate >= 30
    if params.respiratory_rate >= 30:
        score += 1

    # B: Blood pressure — systolic < 90 OR diastolic <= 60
    if params.systolic_bp < 90 or params.diastolic_bp <= 60:
        score += 1

    # 65: Age >= 65
    if params.age >= 65:
        score += 1

    evidence = Evidence(
        source_doi="10.1136/thorax.58.5.377",
        level="Derivation & Validation Study",
        description="Defining community acquired pneumonia severity on presentation to hospital: an international derivation and validation study."
    )

    if score <= 1:
        interpretation = f"CURB-65 score is {score}. Low risk (30-day mortality ~1.5%). Consider outpatient treatment."
    elif score == 2:
        interpretation = f"CURB-65 score is {score}. Moderate risk (30-day mortality ~9.2%). Consider short inpatient stay or hospital-supervised outpatient treatment."
    else:
        interpretation = f"CURB-65 score is {score}. High risk (30-day mortality ~22%). Manage as severe pneumonia with urgent hospital admission. Consider ICU if score 4-5."

    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="LP419467-4",
        fhir_system="http://loinc.org",
        fhir_display="CURB-65 score"
    )

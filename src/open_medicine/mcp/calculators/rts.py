from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class RTSParams(BaseModel):
    """Parameters to calculate the Revised Trauma Score (RTS)."""
    gcs: int = Field(..., description="Glasgow Coma Scale score (3-15)", ge=3, le=15)
    systolic_bp: int = Field(..., description="Systolic blood pressure in mmHg", ge=0)
    respiratory_rate: int = Field(..., description="Respiratory rate in breaths per minute", ge=0)


def _code_gcs(gcs: int) -> int:
    if gcs >= 13:
        return 4
    elif gcs >= 9:
        return 3
    elif gcs >= 6:
        return 2
    elif gcs >= 4:
        return 1
    else:
        return 0


def _code_sbp(sbp: int) -> int:
    if sbp > 89:
        return 4
    elif sbp >= 76:
        return 3
    elif sbp >= 50:
        return 2
    elif sbp >= 1:
        return 1
    else:
        return 0


def _code_rr(rr: int) -> int:
    if 10 <= rr <= 29:
        return 4
    elif rr > 29:
        return 3
    elif 6 <= rr <= 9:
        return 2
    elif 1 <= rr <= 5:
        return 1
    else:
        return 0


def calculate_rts(params: RTSParams) -> ClinicalResult:
    """
    Calculates the Revised Trauma Score (RTS) for triage and outcome prediction in trauma.
    Reference: Champion HR et al. J Trauma 1989;29:623-629.
    """
    gcs_coded = _code_gcs(params.gcs)
    sbp_coded = _code_sbp(params.systolic_bp)
    rr_coded = _code_rr(params.respiratory_rate)

    simple_rts = gcs_coded + sbp_coded + rr_coded
    weighted_rts = round(0.9368 * gcs_coded + 0.7326 * sbp_coded + 0.2908 * rr_coded, 4)

    # Triage category based on simple RTS
    if simple_rts == 12:
        triage = "Delayed (minor injuries)"
    elif simple_rts == 11:
        triage = "Urgent"
    elif simple_rts == 0:
        triage = "Deceased"
    else:  # ≤10
        triage = "Immediate (life-threatening)"

    interpretation = (
        f"Weighted RTS: {weighted_rts}. Simple RTS: {simple_rts}/12 "
        f"(GCS coded={gcs_coded}, SBP coded={sbp_coded}, RR coded={rr_coded}). "
        f"Triage category: {triage}."
    )

    evidence = Evidence(
        source_doi="10.1097/00005373-198905000-00017",
        level="Derivation & Validation Study",
        description="A Revision of the Trauma Score (Champion HR et al. J Trauma 1989)"
    )

    return ClinicalResult(
        value=weighted_rts,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="75412-4",  # LOINC approximation: Revised trauma score
        fhir_system="http://loinc.org",
        fhir_display="Revised trauma score"
    )

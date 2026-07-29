# Related guidelines: aha_aap_nrp_2020 (neonatal resuscitation, Apgar assessment timing)
from pydantic import BaseModel, Field
from open_medicine.mcp.base import ClinicalResult, Evidence


class ApgarParams(BaseModel):
    """Parameters to calculate the Apgar Score for neonatal assessment."""
    appearance: int = Field(
        ...,
        ge=0,
        le=2,
        description=(
            "Skin color (Appearance). Scoring: "
            "0 = Blue or pale all over, "
            "1 = Blue extremities with pink body (acrocyanosis), "
            "2 = Entirely pink (no cyanosis)."
        ),
    )
    pulse: int = Field(
        ...,
        ge=0,
        le=2,
        description=(
            "Heart rate (Pulse). Scoring: "
            "0 = Absent (no heartbeat), "
            "1 = Below 100 beats per minute, "
            "2 = 100 beats per minute or greater."
        ),
    )
    grimace: int = Field(
        ...,
        ge=0,
        le=2,
        description=(
            "Reflex irritability (Grimace) in response to stimulation. Scoring: "
            "0 = No response, "
            "1 = Grimace or weak cry, "
            "2 = Cry, cough, or sneeze (vigorous response)."
        ),
    )
    activity: int = Field(
        ...,
        ge=0,
        le=2,
        description=(
            "Muscle tone (Activity). Scoring: "
            "0 = Limp (no tone), "
            "1 = Some flexion of extremities, "
            "2 = Active motion with good flexion."
        ),
    )
    respiration: int = Field(
        ...,
        ge=0,
        le=2,
        description=(
            "Respiratory effort (Respiration). Scoring: "
            "0 = Absent (not breathing), "
            "1 = Slow, irregular, weak cry or gasping, "
            "2 = Good effort, strong cry."
        ),
    )


def calculate_apgar(params: ApgarParams) -> ClinicalResult:
    """
    Calculates the Apgar Score for rapid assessment of newborn condition at birth.
    Each of five criteria is scored 0-2, yielding a total of 0-10.
    Reference: Apgar V. Curr Res Anesth Analg. 1953;32(4):260-267.
    """
    # 1. Compute total score (sum of five components, each 0-2)
    score = (
        params.appearance
        + params.pulse
        + params.grimace
        + params.activity
        + params.respiration
    )

    # 2. Build Evidence with DOI from original 1953 study
    evidence = Evidence(
        source_doi="10.1213/00000539-195301000-00041",
        level="Derivation & Validation Study",
        description=(
            "A proposal for a new method of evaluation of the newborn infant. "
            "(Apgar V, Curr Res Anesth Analg 1953)"
        ),
    )

    # 3. Interpret result using validated thresholds
    #    Original 1953 paper: 0-2 = poor, 3-7 = fair, 8-10 = good
    #    Modern consensus (AAP/ACOG 2015, NRP 2020):
    #      7-10 = Reassuring
    #      4-6  = Moderately abnormal
    #      0-3  = Low (critically low in full-term/late preterm infants)
    if score >= 7:
        interpretation = (
            f"Apgar Score is {score}. Reassuring. "
            f"The newborn is in good condition. "
            f"Continue routine post-delivery care."
        )
    elif score >= 4:
        interpretation = (
            f"Apgar Score is {score}. Moderately abnormal. "
            f"The newborn may require some resuscitative measures "
            f"(e.g., stimulation, supplemental oxygen, suctioning). "
            f"Reassess at 5-minute intervals."
        )
    else:
        interpretation = (
            f"Apgar Score is {score}. Low (critically low). "
            f"Immediate resuscitation is indicated. "
            f"Reassess at 5-minute intervals for up to 20 minutes per NRP guidelines."
        )

    # 4. Return ClinicalResult with FHIR metadata
    # LOINC 9274-2 = "5 minute Apgar Score" (most standard clinical time point)
    # Alternative: 9272-6 = "1 minute Apgar Score"
    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="9274-2",
        fhir_system="http://loinc.org",
        fhir_display="5 minute Apgar Score",
    )

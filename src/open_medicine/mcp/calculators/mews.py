from enum import Enum
from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence

# Related guidelines: (none currently in registry; MEWS predates NEWS2 — see rcp_news2_2017)


class AVPULevel(str, Enum):
    """AVPU consciousness level scale."""
    ALERT = "alert"
    VOICE = "voice"
    PAIN = "pain"
    UNRESPONSIVE = "unresponsive"


class MEWSParams(BaseModel):
    """Parameters to calculate the Modified Early Warning Score (MEWS)."""
    systolic_bp: int = Field(..., description="Systolic blood pressure in mmHg")
    heart_rate: int = Field(..., description="Heart rate in beats per minute")
    respiratory_rate: int = Field(..., description="Respiratory rate in breaths per minute")
    temperature: float = Field(..., description="Body temperature in degrees Celsius")
    avpu: AVPULevel = Field(..., description="Level of consciousness on AVPU scale: Alert, Voice, Pain, Unresponsive")


def _score_systolic_bp(bp: int) -> int:
    """Score systolic blood pressure per Subbe et al. 2001."""
    if bp <= 70:
        return 3
    elif bp <= 80:
        return 2
    elif bp <= 100:
        return 1
    elif bp <= 199:
        return 0
    else:
        # >= 200
        return 2


def _score_heart_rate(hr: int) -> int:
    """Score heart rate per Subbe et al. 2001."""
    if hr < 40:
        return 2
    elif hr <= 50:
        return 1
    elif hr <= 100:
        return 0
    elif hr <= 110:
        return 1
    elif hr <= 129:
        return 2
    else:
        # >= 130
        return 3


def _score_respiratory_rate(rr: int) -> int:
    """Score respiratory rate per Subbe et al. 2001."""
    if rr < 9:
        return 2
    elif rr <= 14:
        return 0
    elif rr <= 20:
        return 1
    elif rr <= 29:
        return 2
    else:
        # >= 30
        return 3


def _score_temperature(temp: float) -> int:
    """Score temperature per Subbe et al. 2001."""
    if temp < 35.0:
        return 2
    elif temp <= 38.4:
        return 0
    else:
        # >= 38.5
        return 2


def _score_avpu(level: AVPULevel) -> int:
    """Score AVPU consciousness level per Subbe et al. 2001."""
    if level == AVPULevel.ALERT:
        return 0
    elif level == AVPULevel.VOICE:
        return 1
    elif level == AVPULevel.PAIN:
        return 2
    else:
        # Unresponsive
        return 3


def calculate_mews(params: MEWSParams) -> ClinicalResult:
    """
    Calculates the Modified Early Warning Score (MEWS).
    Bedside tool to identify medical patients at risk of clinical deterioration.
    Reference: Subbe CP et al. QJM. 2001;94(10):521-526.
    """
    sbp_score = _score_systolic_bp(params.systolic_bp)
    hr_score = _score_heart_rate(params.heart_rate)
    rr_score = _score_respiratory_rate(params.respiratory_rate)
    temp_score = _score_temperature(params.temperature)
    avpu_score = _score_avpu(params.avpu)

    total_score = sbp_score + hr_score + rr_score + temp_score + avpu_score

    evidence = Evidence(
        source_doi="10.1093/qjmed/94.10.521",
        level="Derivation & Validation Study",
        description="Subbe CP et al. Validation of a modified Early Warning Score in medical admissions. QJM. 2001;94(10):521-526."
    )

    if total_score >= 5:
        interpretation = (
            f"MEWS is {total_score}. High risk. "
            f"Score >=5 is associated with increased risk of death (OR 5.4), "
            f"ICU admission (OR 10.9), and HDU admission (OR 3.3). "
            f"Immediate clinical review and consider higher level of care."
        )
    elif total_score >= 4:
        interpretation = (
            f"MEWS is {total_score}. Increased risk. "
            f"Score approaching critical threshold. "
            f"Notify ward physician and increase monitoring frequency."
        )
    elif total_score >= 2:
        interpretation = (
            f"MEWS is {total_score}. Moderate risk. "
            f"Increase monitoring frequency. "
            f"Consider clinical review if score is increasing."
        )
    else:
        interpretation = (
            f"MEWS is {total_score}. Low risk. "
            f"Continue routine monitoring. "
            f"Reassess per institutional protocol."
        )

    return ClinicalResult(
        value=total_score,
        interpretation=interpretation,
        evidence=evidence,
        # LOINC approximation: no dedicated LOINC or SNOMED CT code for MEWS;
        # using NEWS2 SNOMED CT concept as nearest early warning score proxy
        fhir_code="1104051000000101",
        fhir_system="http://snomed.info/sct",
        fhir_display="Early warning score total score"
    )

from enum import Enum
from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence

# Related guidelines: rcp_news2_2017 (scoring_system, clinical_response sections)

class SpO2Scale(str, Enum):
    SCALE_1 = "scale_1"
    SCALE_2 = "scale_2"


class ConsciousnessLevel(str, Enum):
    ALERT = "alert"
    CONFUSION = "confusion"
    VOICE = "voice"
    PAIN = "pain"
    UNRESPONSIVE = "unresponsive"


class NEWS2Params(BaseModel):
    """Parameters to calculate the National Early Warning Score 2 (NEWS2)."""
    respiration_rate: int = Field(..., description="Respiration rate in breaths per minute")
    spo2: int = Field(..., description="Oxygen saturation (SpO2) as percentage (0-100)")
    spo2_scale: SpO2Scale = Field(SpO2Scale.SCALE_1, description="SpO2 scoring scale. Scale 1 for most patients; Scale 2 for confirmed hypercapnic respiratory failure on prescribed O2")
    on_supplemental_o2: bool = Field(..., description="Whether the patient is receiving supplemental oxygen")
    systolic_bp: int = Field(..., description="Systolic blood pressure in mmHg")
    pulse: int = Field(..., description="Heart rate in beats per minute")
    consciousness: ConsciousnessLevel = Field(..., description="Level of consciousness (ACVPU scale)")
    temperature: float = Field(..., description="Body temperature in degrees Celsius")


def _score_respiration(rate: int) -> int:
    if rate <= 8:
        return 3
    elif rate <= 11:
        return 1
    elif rate <= 20:
        return 0
    elif rate <= 24:
        return 2
    else:
        return 3


def _score_spo2_scale1(spo2: int) -> int:
    if spo2 <= 91:
        return 3
    elif spo2 <= 93:
        return 2
    elif spo2 <= 95:
        return 1
    else:
        return 0


def _score_spo2_scale2(spo2: int, on_o2: bool) -> int:
    if spo2 <= 83:
        return 3
    elif spo2 <= 85:
        return 2
    elif spo2 <= 87:
        return 1
    elif spo2 <= 92 and not on_o2:
        return 0
    elif spo2 <= 92 and on_o2:
        # 88-92 on O2: not explicitly in the 88-92 "on air" range
        # Per NEWS2: 88-92 on air = 0; on O2 we continue to check higher ranges
        return 0
    elif spo2 <= 94 and on_o2:
        return 1
    elif spo2 <= 96 and on_o2:
        return 2
    elif spo2 >= 97 and on_o2:
        return 3
    else:
        # 93+ on air for scale 2
        return 0


def _score_supplemental_o2(on_o2: bool) -> int:
    return 2 if on_o2 else 0


def _score_systolic_bp(bp: int) -> int:
    if bp <= 90:
        return 3
    elif bp <= 100:
        return 2
    elif bp <= 110:
        return 1
    elif bp <= 219:
        return 0
    else:
        return 3


def _score_pulse(pulse: int) -> int:
    if pulse <= 40:
        return 3
    elif pulse <= 50:
        return 1
    elif pulse <= 90:
        return 0
    elif pulse <= 110:
        return 1
    elif pulse <= 130:
        return 2
    else:
        return 3


def _score_consciousness(level: ConsciousnessLevel) -> int:
    if level == ConsciousnessLevel.ALERT:
        return 0
    return 3


def _score_temperature(temp: float) -> int:
    if temp <= 35.0:
        return 3
    elif temp <= 36.0:
        return 1
    elif temp <= 38.0:
        return 0
    elif temp <= 39.0:
        return 1
    else:
        return 2


def calculate_news2(params: NEWS2Params) -> ClinicalResult:
    """
    Calculates the National Early Warning Score 2 (NEWS2).
    Standardised assessment of acute illness severity in the NHS.
    Reference: Royal College of Physicians. NEWS2, 2017.
    """
    individual_scores = []

    resp_score = _score_respiration(params.respiration_rate)
    individual_scores.append(resp_score)

    if params.spo2_scale == SpO2Scale.SCALE_1:
        spo2_score = _score_spo2_scale1(params.spo2)
    else:
        spo2_score = _score_spo2_scale2(params.spo2, params.on_supplemental_o2)
    individual_scores.append(spo2_score)

    o2_score = _score_supplemental_o2(params.on_supplemental_o2)
    individual_scores.append(o2_score)

    bp_score = _score_systolic_bp(params.systolic_bp)
    individual_scores.append(bp_score)

    pulse_score = _score_pulse(params.pulse)
    individual_scores.append(pulse_score)

    consciousness_score = _score_consciousness(params.consciousness)
    individual_scores.append(consciousness_score)

    temp_score = _score_temperature(params.temperature)
    individual_scores.append(temp_score)

    total_score = sum(individual_scores)
    max_single = max(individual_scores)

    evidence = Evidence(
        source_doi="10.7861/clinmedicine.17-6-s68",
        level="Guideline",
        description="National Early Warning Score (NEWS) 2. Royal College of Physicians, 2017."
    )

    if total_score >= 7:
        risk = "high"
        interpretation = (
            f"NEWS2 score is {total_score}. High clinical risk. "
            f"Urgent or emergency response recommended. "
            f"Continuous monitoring and urgent clinical review required."
        )
    elif total_score >= 5 or max_single >= 3:
        risk = "medium"
        reason = "aggregate 5-6" if total_score >= 5 else "3 in single parameter"
        interpretation = (
            f"NEWS2 score is {total_score}. Medium clinical risk ({reason}). "
            f"Key threshold for urgent ward-based response. "
            f"Urgent review by clinician with core competencies in acute illness."
        )
    else:
        risk = "low"
        interpretation = (
            f"NEWS2 score is {total_score}. Low clinical risk. "
            f"Continue routine monitoring. "
            f"Minimum 12-hourly observations recommended."
        )

    return ClinicalResult(
        value=total_score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="1104051000000101",
        fhir_system="http://snomed.info/sct",
        fhir_display="Royal College of Physicians NEWS2 (National Early Warning Score 2) total score"
    )

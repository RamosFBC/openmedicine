# Related guidelines: aua_bph_2023 (BPH evaluation and management)

from typing import Optional

from pydantic import BaseModel, Field
from open_medicine.mcp.base import ClinicalResult, Evidence


class IPSSParams(BaseModel):
    """Parameters to calculate the International Prostate Symptom Score (IPSS).

    The IPSS consists of 7 symptom questions (each scored 0-5) plus one optional
    Quality of Life (QoL) question (scored 0-6). The 7 symptom questions assess
    lower urinary tract symptoms (LUTS) over the past month. The QoL question
    assesses the patient's perceived bother from urinary symptoms.
    """

    incomplete_emptying: int = Field(
        ...,
        ge=0,
        le=5,
        description=(
            "Over the past month, how often have you had the sensation of not "
            "emptying your bladder completely after you finished urinating? "
            "0=Not at all, 1=Less than 1 time in 5, 2=Less than half the time, "
            "3=About half the time, 4=More than half the time, 5=Almost always"
        ),
    )
    frequency: int = Field(
        ...,
        ge=0,
        le=5,
        description=(
            "Over the past month, how often have you had to urinate again less "
            "than two hours after you finished urinating? "
            "0=Not at all, 1=Less than 1 time in 5, 2=Less than half the time, "
            "3=About half the time, 4=More than half the time, 5=Almost always"
        ),
    )
    intermittency: int = Field(
        ...,
        ge=0,
        le=5,
        description=(
            "Over the past month, how often have you found you stopped and "
            "started again several times when you urinated? "
            "0=Not at all, 1=Less than 1 time in 5, 2=Less than half the time, "
            "3=About half the time, 4=More than half the time, 5=Almost always"
        ),
    )
    urgency: int = Field(
        ...,
        ge=0,
        le=5,
        description=(
            "Over the past month, how often have you found it difficult to "
            "postpone urination? "
            "0=Not at all, 1=Less than 1 time in 5, 2=Less than half the time, "
            "3=About half the time, 4=More than half the time, 5=Almost always"
        ),
    )
    weak_stream: int = Field(
        ...,
        ge=0,
        le=5,
        description=(
            "Over the past month, how often have you had a weak urinary stream? "
            "0=Not at all, 1=Less than 1 time in 5, 2=Less than half the time, "
            "3=About half the time, 4=More than half the time, 5=Almost always"
        ),
    )
    straining: int = Field(
        ...,
        ge=0,
        le=5,
        description=(
            "Over the past month, how often have you had to push or strain to "
            "begin urination? "
            "0=Not at all, 1=Less than 1 time in 5, 2=Less than half the time, "
            "3=About half the time, 4=More than half the time, 5=Almost always"
        ),
    )
    nocturia: int = Field(
        ...,
        ge=0,
        le=5,
        description=(
            "Over the past month, how many times did you most typically get up "
            "to urinate from the time you went to bed at night until the time "
            "you got up in the morning? "
            "0=None, 1=1 time, 2=2 times, 3=3 times, 4=4 times, 5=5 or more times"
        ),
    )
    quality_of_life: Optional[int] = Field(
        None,
        ge=0,
        le=6,
        description=(
            "Quality of Life due to urinary symptoms (optional). "
            "If you were to spend the rest of your life with your urinary "
            "condition just the way it is now, how would you feel about that? "
            "0=Delighted, 1=Pleased, 2=Mostly satisfied, 3=Mixed (about equally "
            "satisfied and dissatisfied), 4=Mostly dissatisfied, 5=Unhappy, "
            "6=Terrible"
        ),
    )


def calculate_ipss(params: IPSSParams) -> ClinicalResult:
    """
    Calculates the International Prostate Symptom Score (IPSS).
    A validated 7-item self-report measure for assessing lower urinary tract
    symptom severity in benign prostatic hyperplasia (BPH).
    Reference: Barry MJ et al. J Urol. 1992;148(5):1549-1557.
    """
    # 1. Compute total symptom score (sum of 7 items, each 0-5, range 0-35)
    score = (
        params.incomplete_emptying
        + params.frequency
        + params.intermittency
        + params.urgency
        + params.weak_stream
        + params.straining
        + params.nocturia
    )

    # 2. Build Evidence with DOI from the original AUA Symptom Index study
    evidence = Evidence(
        source_doi="10.1016/S0022-5347(17)36966-5",
        level="Derivation & Validation Study",
        description=(
            "The American Urological Association Symptom Index for Benign "
            "Prostatic Hyperplasia. Barry MJ et al. J Urol. 1992."
        ),
    )

    # 3. Interpret result using the validated severity thresholds
    #    (Barry et al. 1992; adopted by WHO as IPSS):
    #    0-7 = Mild, 8-19 = Moderate, 20-35 = Severe
    if score <= 7:
        severity = "Mild symptoms"
        action = (
            "Watchful waiting with lifestyle and behavioral modifications "
            "(e.g., fluid management, bladder training) is appropriate. "
            "Reassess periodically."
        )
    elif score <= 19:
        severity = "Moderate symptoms"
        action = (
            "Medical therapy should be considered. Options include alpha-blockers, "
            "5-alpha-reductase inhibitors, or combination therapy. "
            "Urology referral recommended if symptoms are bothersome."
        )
    else:
        severity = "Severe symptoms"
        action = (
            "Urology referral is recommended. Medical management with alpha-blockers "
            "and/or 5-alpha-reductase inhibitors; surgical intervention (e.g., TURP, "
            "laser therapy) should be considered if medical therapy is insufficient."
        )

    interpretation = f"IPSS is {score}. {severity} (0-35 scale). {action}"

    # 4. Append Quality of Life interpretation if provided
    if params.quality_of_life is not None:
        qol_labels = {
            0: "Delighted",
            1: "Pleased",
            2: "Mostly satisfied",
            3: "Mixed",
            4: "Mostly dissatisfied",
            5: "Unhappy",
            6: "Terrible",
        }
        qol_label = qol_labels.get(params.quality_of_life, "Unknown")
        interpretation += (
            f" Quality of Life (QoL) score is {params.quality_of_life} "
            f"({qol_label})."
        )

    # 5. Return ClinicalResult with FHIR metadata
    # LOINC 80976-4: International Prostate Symptom Score [IPSS]
    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="80976-4",
        fhir_system="http://loinc.org",
        fhir_display="International Prostate Symptom Score [IPSS]",
    )

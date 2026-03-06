# Related guidelines: apa_mdd_2023 (depression treatment)
# Related guidelines: acog_perinatal_depression_2018 (screening section)

from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class EPDSParams(BaseModel):
    """Parameters to calculate the Edinburgh Postnatal Depression Scale (EPDS).

    Each item is scored 0-3 based on symptom frequency over the past 7 days.
    Items 1, 2, and 4 are forward-scored (0 = best, 3 = worst).
    Items 3, 5, 6, 7, 8, 9, and 10 are reverse-scored in the original
    questionnaire, but the input to this calculator should always be the
    final scored value (0 = no symptom, 3 = maximum symptom).
    """

    laugh: int = Field(
        ...,
        ge=0,
        le=3,
        description=(
            "I have been able to laugh and see the funny side of things: "
            "0=As much as I always could, 1=Not quite so much now, "
            "2=Definitely not so much now, 3=Not at all"
        ),
    )
    enjoyment: int = Field(
        ...,
        ge=0,
        le=3,
        description=(
            "I have looked forward with enjoyment to things: "
            "0=As much as I ever did, 1=Rather less than I used to, "
            "2=Definitely less than I used to, 3=Hardly at all"
        ),
    )
    self_blame: int = Field(
        ...,
        ge=0,
        le=3,
        description=(
            "I have blamed myself unnecessarily when things went wrong: "
            "0=No never, 1=Not very often, 2=Yes some of the time, "
            "3=Yes most of the time"
        ),
    )
    anxious: int = Field(
        ...,
        ge=0,
        le=3,
        description=(
            "I have been anxious or worried for no good reason: "
            "0=No not at all, 1=Hardly ever, 2=Yes sometimes, "
            "3=Yes very often"
        ),
    )
    scared: int = Field(
        ...,
        ge=0,
        le=3,
        description=(
            "I have felt scared or panicky for no very good reason: "
            "0=No not at all, 1=No not much, 2=Yes sometimes, "
            "3=Yes quite a lot"
        ),
    )
    things_on_top: int = Field(
        ...,
        ge=0,
        le=3,
        description=(
            "Things have been getting on top of me: "
            "0=No I have been coping as well as ever, "
            "1=No most of the time I have coped quite well, "
            "2=Yes sometimes I haven't been coping as well as usual, "
            "3=Yes most of the time I haven't been able to cope at all"
        ),
    )
    difficulty_sleeping: int = Field(
        ...,
        ge=0,
        le=3,
        description=(
            "I have been so unhappy that I have had difficulty sleeping: "
            "0=No not at all, 1=Not very often, 2=Yes sometimes, "
            "3=Yes most of the time"
        ),
    )
    sad: int = Field(
        ...,
        ge=0,
        le=3,
        description=(
            "I have felt sad or miserable: "
            "0=No not at all, 1=Not very often, 2=Yes quite often, "
            "3=Yes most of the time"
        ),
    )
    crying: int = Field(
        ...,
        ge=0,
        le=3,
        description=(
            "I have been so unhappy that I have been crying: "
            "0=No never, 1=Only occasionally, 2=Yes quite often, "
            "3=Yes most of the time"
        ),
    )
    self_harm: int = Field(
        ...,
        ge=0,
        le=3,
        description=(
            "The thought of harming myself has occurred to me: "
            "0=Never, 1=Hardly ever, 2=Sometimes, 3=Yes quite often"
        ),
    )


def calculate_epds(params: EPDSParams) -> ClinicalResult:
    """
    Calculates the Edinburgh Postnatal Depression Scale (EPDS).
    A 10-item self-report screening tool for postnatal depression, validated
    for use during pregnancy and the postpartum period.
    Reference: Cox JL, Holden JM, Sagovsky R. Br J Psychiatry. 1987;150:782-786.
    """
    # 1. Sum all 10 items (each scored 0-3, total range 0-30)
    score = (
        params.laugh
        + params.enjoyment
        + params.self_blame
        + params.anxious
        + params.scared
        + params.things_on_top
        + params.difficulty_sleeping
        + params.sad
        + params.crying
        + params.self_harm
    )

    # 2. Build Evidence with DOI from original derivation study
    evidence = Evidence(
        source_doi="10.1192/bjp.150.6.782",
        level="Derivation & Validation Study",
        description=(
            "Detection of postnatal depression: development of the 10-item "
            "Edinburgh Postnatal Depression Scale "
            "(Cox JL, Holden JM, Sagovsky R. Br J Psychiatry 1987)"
        ),
    )

    # 3. Interpret result using validated thresholds from Cox et al. 1987
    # The original paper established a threshold of 12/13 for probable
    # depression (sensitivity 86%, specificity 78%).
    # A lower threshold of 9/10 is recommended for screening to maximize
    # sensitivity (Cox & Holden, 2003).

    # Self-harm flag: item 10 score > 0 warrants immediate safety assessment
    self_harm_flag = ""
    if params.self_harm > 0:
        self_harm_flag = (
            " SAFETY ALERT: Item 10 (self-harm thoughts) scored "
            f"{params.self_harm}/3. Immediate safety assessment is indicated."
        )

    if score <= 9:
        severity = "Low risk (negative screen)"
        action = (
            "Depression unlikely based on screening. "
            "Continue routine clinical monitoring."
        )
    elif score <= 12:
        severity = "Possible depression"
        action = (
            "Score suggests possible depressive symptoms. "
            "Further clinical assessment recommended. "
            "Repeat screening in 2-4 weeks and consider referral for "
            "diagnostic evaluation."
        )
    else:
        severity = "Probable depression (positive screen)"
        action = (
            "Score above the validated threshold of 12/13 (sensitivity 86%, "
            "specificity 78%). Comprehensive diagnostic evaluation for "
            "major depressive disorder is recommended. "
            "Consider referral to a mental health specialist."
        )

    interpretation = f"EPDS score is {score}. {severity}. {action}{self_harm_flag}"

    # 4. Return ClinicalResult with FHIR metadata
    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="71354-5",
        fhir_system="http://loinc.org",
        fhir_display="Edinburgh Postnatal Depression Scale [EPDS]",
    )

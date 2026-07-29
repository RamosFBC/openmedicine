# Related guidelines: apa_aud_2018 (assessment_and_screening section)

from pydantic import BaseModel, Field
from open_medicine.mcp.base import ClinicalResult, Evidence


class CIWAArParams(BaseModel):
    """Parameters to calculate the CIWA-Ar (Clinical Institute Withdrawal
    Assessment for Alcohol, Revised) score.

    Each item is rated by the clinician based on observation and patient
    interview. Items 1-9 are scored 0 (none) to 7 (most severe). Item 10
    (orientation/clouding of sensorium) is scored 0-4.
    """

    nausea_vomiting: int = Field(
        ...,
        ge=0,
        le=7,
        description=(
            "Nausea and vomiting. "
            "0 = no nausea and no vomiting, "
            "1 = mild nausea with no vomiting, "
            "4 = intermittent nausea with dry heaves, "
            "7 = constant nausea, frequent dry heaves and vomiting"
        ),
    )
    tremor: int = Field(
        ...,
        ge=0,
        le=7,
        description=(
            "Tremor (arms extended and fingers spread apart). "
            "0 = no tremor, "
            "1 = not visible but can be felt fingertip to fingertip, "
            "4 = moderate given patient's arms are extended, "
            "7 = severe even with arms not extended"
        ),
    )
    paroxysmal_sweats: int = Field(
        ...,
        ge=0,
        le=7,
        description=(
            "Paroxysmal sweats (observation). "
            "0 = no sweat visible, "
            "1 = barely perceptible sweating or palms moist, "
            "4 = beads of sweat obvious on forehead, "
            "7 = drenching sweats"
        ),
    )
    anxiety: int = Field(
        ...,
        ge=0,
        le=7,
        description=(
            "Anxiety (observation and inquiry: 'Do you feel nervous?'). "
            "0 = no anxiety, at ease, "
            "1 = mildly anxious, "
            "4 = moderately anxious or guarded, so anxiety is inferred, "
            "7 = equivalent to acute panic states as seen in severe "
            "delirium or acute schizophrenic reactions"
        ),
    )
    agitation: int = Field(
        ...,
        ge=0,
        le=7,
        description=(
            "Agitation (observation). "
            "0 = normal activity, "
            "1 = somewhat more than normal activity, "
            "4 = moderately fidgety and restless, "
            "7 = paces back and forth during interview or constantly "
            "thrashes about"
        ),
    )
    tactile_disturbances: int = Field(
        ...,
        ge=0,
        le=7,
        description=(
            "Tactile disturbances (inquiry: 'Have you any itching, pins "
            "and needles sensations, any burning, any numbness, or do you "
            "feel bugs crawling on or under your skin?'). "
            "0 = none, "
            "1 = very mild itching/pins and needles/burning/numbness, "
            "2 = mild itching/pins and needles/burning/numbness, "
            "3 = moderate itching/pins and needles/burning/numbness, "
            "4 = moderately severe hallucinations, "
            "5 = severe hallucinations, "
            "6 = extremely severe hallucinations, "
            "7 = continuous hallucinations"
        ),
    )
    auditory_disturbances: int = Field(
        ...,
        ge=0,
        le=7,
        description=(
            "Auditory disturbances (inquiry: 'Are you more aware of "
            "sounds around you? Are they harsh? Do they frighten you? "
            "Are you hearing anything that is disturbing to you? Are "
            "you hearing things you know are not there?'). "
            "0 = not present, "
            "1 = very mild harshness or ability to frighten, "
            "2 = mild harshness or ability to frighten, "
            "3 = moderate harshness or ability to frighten, "
            "4 = moderately severe hallucinations, "
            "5 = severe hallucinations, "
            "6 = extremely severe hallucinations, "
            "7 = continuous hallucinations"
        ),
    )
    visual_disturbances: int = Field(
        ...,
        ge=0,
        le=7,
        description=(
            "Visual disturbances (inquiry: 'Does the light appear to "
            "be too bright? Is its color different? Does it hurt your "
            "eyes? Are you seeing anything that is disturbing to you? "
            "Are you seeing things you know are not there?'). "
            "0 = not present, "
            "1 = very mild sensitivity, "
            "2 = mild sensitivity, "
            "3 = moderate sensitivity, "
            "4 = moderately severe hallucinations, "
            "5 = severe hallucinations, "
            "6 = extremely severe hallucinations, "
            "7 = continuous hallucinations"
        ),
    )
    headache: int = Field(
        ...,
        ge=0,
        le=7,
        description=(
            "Headache, fullness in head (inquiry: 'Does your head feel "
            "different? Does it feel like there is a band around your "
            "head?' Do not rate for dizziness or lightheadedness). "
            "0 = not present, "
            "1 = very mild, "
            "2 = mild, "
            "3 = moderate, "
            "4 = moderately severe, "
            "5 = severe, "
            "6 = very severe, "
            "7 = extremely severe"
        ),
    )
    orientation: int = Field(
        ...,
        ge=0,
        le=4,
        description=(
            "Orientation and clouding of sensorium (inquiry: 'What day "
            "is this? Where are you? Who am I?'). "
            "0 = oriented and can do serial additions, "
            "1 = cannot do serial additions or is uncertain about date, "
            "2 = date uncertain by more than 2 calendar days, "
            "3 = disoriented for date by more than 2 calendar days, "
            "4 = disoriented for place and/or person"
        ),
    )


def calculate_ciwa_ar(params: CIWAArParams) -> ClinicalResult:
    """
    Calculates the CIWA-Ar (Clinical Institute Withdrawal Assessment for
    Alcohol, Revised) total score for grading severity of alcohol withdrawal.

    Reference: Sullivan JT, Sykora K, Schneiderman J, Naranjo CA, Sellers EM.
    Assessment of alcohol withdrawal: the revised Clinical Institute Withdrawal
    Assessment for Alcohol scale (CIWA-Ar). Br J Addict. 1989;84(11):1353-1357.
    """
    # 1. Compute total score (sum of all 10 items)
    #    Items 1-9: 0-7 each (max 63), Item 10 (orientation): 0-4
    #    Maximum possible score: 67
    score = (
        params.nausea_vomiting
        + params.tremor
        + params.paroxysmal_sweats
        + params.anxiety
        + params.agitation
        + params.tactile_disturbances
        + params.auditory_disturbances
        + params.visual_disturbances
        + params.headache
        + params.orientation
    )

    # 2. Build Evidence with DOI from original derivation study
    evidence = Evidence(
        source_doi="10.1111/j.1360-0443.1989.tb00737.x",
        level="Derivation & Validation Study",
        description=(
            "Assessment of alcohol withdrawal: the revised Clinical "
            "Institute Withdrawal Assessment for Alcohol scale (CIWA-Ar). "
            "Sullivan JT et al. Br J Addict. 1989."
        ),
    )

    # 3. Interpret result using validated severity thresholds
    #    Thresholds from Sullivan et al. 1989 and widely adopted in
    #    clinical practice (MDCalc, ASAM, institutional protocols):
    #    - Score <= 8: absent or minimal withdrawal
    #    - Score 9-15: mild to moderate withdrawal
    #    - Score 16-20: moderate to severe withdrawal (some risk of
    #      complications)
    #    - Score > 20: severe withdrawal (high risk for delirium tremens
    #      and seizures)
    if score <= 8:
        interpretation = (
            f"CIWA-Ar score is {score}/67. Absent or minimal withdrawal "
            f"(score 0-8). Pharmacologic treatment is generally not needed. "
            f"Supportive care and monitoring are appropriate. Reassess "
            f"periodically."
        )
    elif score <= 15:
        interpretation = (
            f"CIWA-Ar score is {score}/67. Mild to moderate withdrawal "
            f"(score 9-15). Consider symptom-triggered benzodiazepine "
            f"therapy. Close monitoring with serial CIWA-Ar assessments "
            f"every 1-2 hours is recommended."
        )
    elif score <= 20:
        interpretation = (
            f"CIWA-Ar score is {score}/67. Moderate to severe withdrawal "
            f"(score 16-20). Benzodiazepine treatment is indicated. "
            f"Frequent reassessment with CIWA-Ar every 1 hour. Consider "
            f"higher level of care if symptoms are not controlled."
        )
    else:
        # score > 20
        interpretation = (
            f"CIWA-Ar score is {score}/67. Severe withdrawal "
            f"(score >20). High risk for delirium tremens and withdrawal "
            f"seizures. Aggressive benzodiazepine therapy and intensive "
            f"monitoring are required. ICU-level care should be strongly "
            f"considered."
        )

    # 4. Return ClinicalResult with FHIR metadata
    #    No dedicated LOINC code exists for the CIWA-Ar total score.
    #    Using None to avoid semantic misrepresentation.
    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code=None,
        fhir_system=None,
        fhir_display="CIWA-Ar (Clinical Institute Withdrawal Assessment for Alcohol, Revised) total score",
    )

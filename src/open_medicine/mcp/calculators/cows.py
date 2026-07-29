from pydantic import BaseModel, Field
from open_medicine.mcp.base import ClinicalResult, Evidence


class COWSParams(BaseModel):
    """Parameters to calculate the Clinical Opiate Withdrawal Scale (COWS)."""

    resting_pulse_rate: int = Field(
        ...,
        ge=0,
        le=4,
        description=(
            "Resting pulse rate score. "
            "0 = Pulse rate 80 or below; "
            "1 = Pulse rate 81-100; "
            "2 = Pulse rate 101-120; "
            "4 = Pulse rate greater than 120."
        ),
    )
    sweating: int = Field(
        ...,
        ge=0,
        le=4,
        description=(
            "Sweating over past half hour not accounted for by room temperature or patient activity. "
            "0 = No report of chills or flushing; "
            "1 = Subjective report of chills or flushing; "
            "2 = Flushed or observable moistness on face; "
            "3 = Beads of sweat on brow or face; "
            "4 = Sweat streaming off face."
        ),
    )
    restlessness: int = Field(
        ...,
        ge=0,
        le=5,
        description=(
            "Restlessness observation during assessment. "
            "0 = Able to sit still; "
            "1 = Reports difficulty sitting still, but is able to do so; "
            "3 = Frequent shifting or extraneous movements of legs/arms; "
            "5 = Unable to sit still for more than a few seconds."
        ),
    )
    pupil_size: int = Field(
        ...,
        ge=0,
        le=5,
        description=(
            "Pupil size. "
            "0 = Pupils pinned or normal size for room light; "
            "1 = Pupils possibly larger than normal for room light; "
            "2 = Pupils moderately dilated; "
            "5 = Pupils so dilated that only the rim of the iris is visible."
        ),
    )
    bone_or_joint_aches: int = Field(
        ...,
        ge=0,
        le=4,
        description=(
            "Bone or joint aches. If patient was having pain previously, only the "
            "additional component attributed to opioid withdrawal is scored. "
            "0 = Not present; "
            "1 = Mild diffuse discomfort; "
            "2 = Patient reports severe diffuse aching of joints/muscles; "
            "4 = Patient is rubbing joints or muscles and is unable to sit still "
            "because of discomfort."
        ),
    )
    runny_nose_or_tearing: int = Field(
        ...,
        ge=0,
        le=4,
        description=(
            "Runny nose or tearing. Not accounted for by cold symptoms or allergies. "
            "0 = Not present; "
            "1 = Nasal stuffiness or unusually moist eyes; "
            "2 = Nose running or tearing; "
            "4 = Nose constantly running or tears streaming down cheeks."
        ),
    )
    gi_upset: int = Field(
        ...,
        ge=0,
        le=5,
        description=(
            "GI upset over last half hour. "
            "0 = No GI symptoms; "
            "1 = Stomach cramps; "
            "2 = Nausea or loose stool; "
            "3 = Vomiting or diarrhea; "
            "5 = Multiple episodes of diarrhea or vomiting."
        ),
    )
    tremor: int = Field(
        ...,
        ge=0,
        le=4,
        description=(
            "Tremor: observation of outstretched hands. "
            "0 = No tremor; "
            "1 = Tremor can be felt, but not observed; "
            "2 = Slight tremor observable; "
            "4 = Gross tremor or muscle twitching."
        ),
    )
    yawning: int = Field(
        ...,
        ge=0,
        le=4,
        description=(
            "Yawning: observation during assessment. "
            "0 = No yawning; "
            "1 = Yawning once or twice during assessment; "
            "2 = Yawning three or more times during assessment; "
            "4 = Yawning several times per minute."
        ),
    )
    anxiety_or_irritability: int = Field(
        ...,
        ge=0,
        le=4,
        description=(
            "Anxiety or irritability. "
            "0 = None; "
            "1 = Patient reports increasing irritability or anxiousness; "
            "2 = Patient obviously irritable or anxious; "
            "4 = Patient so irritable or anxious that participation in the "
            "assessment is difficult."
        ),
    )
    gooseflesh_skin: int = Field(
        ...,
        ge=0,
        le=5,
        description=(
            "Gooseflesh skin. "
            "0 = Skin is smooth; "
            "3 = Piloerection of skin can be felt or hairs standing up on arms; "
            "5 = Prominent piloerection."
        ),
    )


def calculate_cows(params: COWSParams) -> ClinicalResult:
    """
    Calculates the Clinical Opiate Withdrawal Scale (COWS) total score.
    Quantifies the severity of opiate withdrawal to guide buprenorphine induction
    and other treatment decisions.
    Reference: Wesson DR, Ling W. J Psychoactive Drugs. 2003.
    """
    score = (
        params.resting_pulse_rate
        + params.sweating
        + params.restlessness
        + params.pupil_size
        + params.bone_or_joint_aches
        + params.runny_nose_or_tearing
        + params.gi_upset
        + params.tremor
        + params.yawning
        + params.anxiety_or_irritability
        + params.gooseflesh_skin
    )

    evidence = Evidence(
        source_doi="10.1080/02791072.2003.10400007",
        level="Validation Study",
        description=(
            "The Clinical Opiate Withdrawal Scale (COWS). "
            "Wesson DR, Ling W. J Psychoactive Drugs. 2003;35(2):253-259."
        ),
    )

    if score < 5:
        severity = "No active withdrawal"
        recommendation = (
            "Score below threshold for active withdrawal. "
            "Continue monitoring; buprenorphine induction typically not yet indicated."
        )
    elif score <= 12:
        severity = "Mild withdrawal"
        recommendation = (
            "Mild withdrawal present. "
            "Some clinicians may consider starting buprenorphine induction at this level. "
            "Continue serial COWS monitoring."
        )
    elif score <= 24:
        severity = "Moderate withdrawal"
        recommendation = (
            "Moderate withdrawal present. "
            "Buprenorphine induction is generally appropriate. "
            "Symptomatic treatment may also be warranted."
        )
    elif score <= 36:
        severity = "Moderately severe withdrawal"
        recommendation = (
            "Moderately severe withdrawal. "
            "Buprenorphine induction is indicated. "
            "Aggressive symptomatic management recommended."
        )
    else:
        severity = "Severe withdrawal"
        recommendation = (
            "Severe withdrawal. "
            "Urgent buprenorphine induction is indicated. "
            "Intensive symptomatic management and close monitoring required."
        )

    interpretation = (
        f"COWS total score is {score}. "
        f"Classification: {severity}. "
        f"{recommendation}"
    )

    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        # No LOINC observation code exists for the COWS total score.
        # LOINC 77114-9 could not be verified in the LOINC database,
        # so using None to avoid semantic misrepresentation.
        fhir_code=None,
        fhir_system=None,
        fhir_display="Clinical Opiate Withdrawal Scale total score",
    )

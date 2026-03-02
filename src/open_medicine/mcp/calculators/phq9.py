# Related guidelines: apa_mdd_2023 (depression screening and treatment)

from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class PHQ9Params(BaseModel):
    """Parameters to calculate the Patient Health Questionnaire-9 (PHQ-9) depression severity score."""

    interest_pleasure: int = Field(
        ...,
        ge=0,
        le=3,
        description="Little interest or pleasure in doing things: 0=Not at all, 1=Several days, 2=More than half the days, 3=Nearly every day",
    )
    feeling_down: int = Field(
        ...,
        ge=0,
        le=3,
        description="Feeling down, depressed, or hopeless: 0=Not at all, 1=Several days, 2=More than half the days, 3=Nearly every day",
    )
    sleep: int = Field(
        ...,
        ge=0,
        le=3,
        description="Trouble falling or staying asleep, or sleeping too much: 0=Not at all, 1=Several days, 2=More than half the days, 3=Nearly every day",
    )
    energy: int = Field(
        ...,
        ge=0,
        le=3,
        description="Feeling tired or having little energy: 0=Not at all, 1=Several days, 2=More than half the days, 3=Nearly every day",
    )
    appetite: int = Field(
        ...,
        ge=0,
        le=3,
        description="Poor appetite or overeating: 0=Not at all, 1=Several days, 2=More than half the days, 3=Nearly every day",
    )
    self_esteem: int = Field(
        ...,
        ge=0,
        le=3,
        description="Feeling bad about yourself, or that you are a failure or have let yourself or your family down: 0=Not at all, 1=Several days, 2=More than half the days, 3=Nearly every day",
    )
    concentration: int = Field(
        ...,
        ge=0,
        le=3,
        description="Trouble concentrating on things, such as reading the newspaper or watching television: 0=Not at all, 1=Several days, 2=More than half the days, 3=Nearly every day",
    )
    psychomotor: int = Field(
        ...,
        ge=0,
        le=3,
        description="Moving or speaking so slowly that other people could have noticed, or the opposite being so fidgety or restless: 0=Not at all, 1=Several days, 2=More than half the days, 3=Nearly every day",
    )
    suicidal_ideation: int = Field(
        ...,
        ge=0,
        le=3,
        description="Thoughts that you would be better off dead or of hurting yourself in some way: 0=Not at all, 1=Several days, 2=More than half the days, 3=Nearly every day",
    )


def calculate_phq9(params: PHQ9Params) -> ClinicalResult:
    """
    Calculates the Patient Health Questionnaire-9 (PHQ-9) depression severity score.
    A validated 9-item self-report measure for screening and monitoring depression severity.
    Reference: Kroenke K, Spitzer RL, Williams JB. J Gen Intern Med. 2001;16(9):606-613.
    """
    # Sum all 9 items (each scored 0-3, total range 0-27)
    score = (
        params.interest_pleasure
        + params.feeling_down
        + params.sleep
        + params.energy
        + params.appetite
        + params.self_esteem
        + params.concentration
        + params.psychomotor
        + params.suicidal_ideation
    )

    evidence = Evidence(
        source_doi="10.1046/j.1525-1497.2001.016009606.x",
        level="Derivation & Validation Study",
        description="The PHQ-9: validity of a brief depression severity measure (Kroenke K et al., J Gen Intern Med 2001)",
    )

    # Severity thresholds from Kroenke et al. 2001, Table 3
    # Proposed treatment actions from Kroenke & Spitzer, Psychiatric Annals 2002
    if score <= 4:
        severity = "Minimal depression"
        action = "No treatment action required."
    elif score <= 9:
        severity = "Mild depression"
        action = "Watchful waiting; repeat PHQ-9 at follow-up."
    elif score <= 14:
        severity = "Moderate depression"
        action = "Treatment plan, considering counseling, follow-up, and/or pharmacotherapy."
    elif score <= 19:
        severity = "Moderately severe depression"
        action = "Active treatment with pharmacotherapy and/or psychotherapy."
    else:
        severity = "Severe depression"
        action = "Immediate initiation of pharmacotherapy and, if severe impairment or poor response to therapy, expedited referral to a mental health specialist for psychotherapy and/or collaborative management."

    interpretation = f"PHQ-9 score is {score}. {severity}. {action}"

    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="44261-6",
        fhir_system="http://loinc.org",
        fhir_display="Patient Health Questionnaire 9 item (PHQ-9) total score [Reported]",
    )

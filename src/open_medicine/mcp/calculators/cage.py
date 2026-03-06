# Related guidelines: apa_aud_2018 (assessment_and_screening, fda_approved_medications sections)

from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class CAGEParams(BaseModel):
    """Parameters to calculate the CAGE Questionnaire score for alcohol screening."""

    cut_down: bool = Field(
        ...,
        description=(
            "Have you ever felt you should Cut down on your drinking? "
            "True=Yes, False=No"
        ),
    )
    annoyed: bool = Field(
        ...,
        description=(
            "Have people Annoyed you by criticizing your drinking? "
            "True=Yes, False=No"
        ),
    )
    guilty: bool = Field(
        ...,
        description=(
            "Have you ever felt bad or Guilty about your drinking? "
            "True=Yes, False=No"
        ),
    )
    eye_opener: bool = Field(
        ...,
        description=(
            "Have you ever had a drink first thing in the morning to steady "
            "your nerves or to get rid of a hangover (Eye-opener)? "
            "True=Yes, False=No"
        ),
    )


def calculate_cage(params: CAGEParams) -> ClinicalResult:
    """
    Calculates the CAGE Questionnaire score for alcohol use screening.
    A validated 4-item clinical interview tool for detecting alcoholism.
    Reference: Ewing JA. JAMA. 1984;252(14):1905-1907.
    """
    # Each "Yes" answer = 1 point; total range 0-4
    score = sum([
        params.cut_down,
        params.annoyed,
        params.guilty,
        params.eye_opener,
    ])

    evidence = Evidence(
        source_doi="10.1001/jama.1984.03350140051025",
        level="Derivation & Validation Study",
        description=(
            "Detecting alcoholism: The CAGE questionnaire "
            "(Ewing JA, JAMA 1984)"
        ),
    )

    # Interpretation thresholds from Ewing 1984:
    # Score >= 2: clinically significant, suggests need for further evaluation
    # Sensitivity ~90%, specificity ~93% for detecting alcohol problems at >= 2
    # Dhalla & Kopec (2007) systematic review: pooled sensitivity 0.71, specificity 0.90
    if score == 0:
        screen_result = "Negative screen"
        action = (
            "No positive responses. Low likelihood of an alcohol use problem. "
            "No further evaluation needed at this time."
        )
    elif score == 1:
        screen_result = "Negative screen (sub-threshold)"
        action = (
            "One positive response is below the clinical threshold (>= 2). "
            "Low probability of alcohol use disorder, but clinical judgment "
            "should guide further assessment if concern exists."
        )
    elif score == 2:
        screen_result = "Positive screen (clinically significant)"
        action = (
            "Score meets clinical threshold. Further evaluation recommended "
            "with a comprehensive alcohol assessment (e.g., full AUDIT, "
            "DSM-5 criteria) to determine if an alcohol use disorder is present."
        )
    elif score == 3:
        screen_result = "Positive screen (high suspicion)"
        action = (
            "High probability of alcohol use disorder. Detailed diagnostic "
            "evaluation with DSM-5 criteria strongly recommended. Consider "
            "referral to addiction medicine or psychiatry."
        )
    else:
        # score == 4
        screen_result = "Positive screen (very high suspicion)"
        action = (
            "All four CAGE items endorsed. Very high probability of alcohol "
            "use disorder. Immediate comprehensive assessment and referral "
            "to addiction specialist recommended."
        )

    interpretation = (
        f"CAGE score is {score}/4. {screen_result}. {action}"
    )

    # No dedicated LOINC code exists for the CAGE questionnaire total score.
    # LOINC 72109-2 represents AUDIT-C (a different screening tool), so using
    # None to avoid semantic misrepresentation. fhir_display preserved for
    # human readability.
    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code=None,
        fhir_system=None,
        fhir_display="CAGE Questionnaire score",
    )

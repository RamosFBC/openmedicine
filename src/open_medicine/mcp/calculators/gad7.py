# No related guidelines in the current registry.
from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class GAD7Params(BaseModel):
    """Parameters to calculate the Generalized Anxiety Disorder 7-item (GAD-7) score.

    Each item asks: 'Over the last 2 weeks, how often have you been bothered
    by the following problems?' and is scored 0 (not at all), 1 (several days),
    2 (more than half the days), or 3 (nearly every day).
    """

    feeling_nervous: int = Field(
        ...,
        ge=0,
        le=3,
        description=(
            "Feeling nervous, anxious, or on edge. "
            "0 = not at all, 1 = several days, 2 = more than half the days, "
            "3 = nearly every day"
        ),
    )
    cannot_stop_worrying: int = Field(
        ...,
        ge=0,
        le=3,
        description=(
            "Not being able to stop or control worrying. "
            "0 = not at all, 1 = several days, 2 = more than half the days, "
            "3 = nearly every day"
        ),
    )
    worrying_too_much: int = Field(
        ...,
        ge=0,
        le=3,
        description=(
            "Worrying too much about different things. "
            "0 = not at all, 1 = several days, 2 = more than half the days, "
            "3 = nearly every day"
        ),
    )
    trouble_relaxing: int = Field(
        ...,
        ge=0,
        le=3,
        description=(
            "Trouble relaxing. "
            "0 = not at all, 1 = several days, 2 = more than half the days, "
            "3 = nearly every day"
        ),
    )
    being_restless: int = Field(
        ...,
        ge=0,
        le=3,
        description=(
            "Being so restless that it is hard to sit still. "
            "0 = not at all, 1 = several days, 2 = more than half the days, "
            "3 = nearly every day"
        ),
    )
    easily_annoyed: int = Field(
        ...,
        ge=0,
        le=3,
        description=(
            "Becoming easily annoyed or irritable. "
            "0 = not at all, 1 = several days, 2 = more than half the days, "
            "3 = nearly every day"
        ),
    )
    feeling_afraid: int = Field(
        ...,
        ge=0,
        le=3,
        description=(
            "Feeling afraid, as if something awful might happen. "
            "0 = not at all, 1 = several days, 2 = more than half the days, "
            "3 = nearly every day"
        ),
    )


def calculate_gad7(params: GAD7Params) -> ClinicalResult:
    """
    Calculates the GAD-7 total score for generalized anxiety disorder screening.

    The GAD-7 is a validated 7-item self-report questionnaire used to screen for
    and measure the severity of generalized anxiety disorder (GAD) in primary
    care and clinical research settings.

    Reference: Spitzer RL, Kroenke K, Williams JBW, Lowe B. A brief measure for
    assessing generalized anxiety disorder: the GAD-7. Arch Intern Med. 2006;
    166(10):1092-1097.
    """
    # 1. Compute total score (sum of all 7 items, each 0-3)
    score = (
        params.feeling_nervous
        + params.cannot_stop_worrying
        + params.worrying_too_much
        + params.trouble_relaxing
        + params.being_restless
        + params.easily_annoyed
        + params.feeling_afraid
    )

    # 2. Build Evidence with DOI from the original derivation and validation study
    evidence = Evidence(
        source_doi="10.1001/archinte.166.10.1092",
        level="Derivation & Validation Study",
        description=(
            "A brief measure for assessing generalized anxiety disorder: "
            "the GAD-7. Spitzer et al. Arch Intern Med. 2006."
        ),
    )

    # 3. Interpret result using the published severity thresholds
    #    (Spitzer et al. 2006, Table 3): 0-4 minimal, 5-9 mild, 10-14 moderate,
    #    15-21 severe. Cut-point >= 10 optimal for GAD screening
    #    (sensitivity 89%, specificity 82%).
    if score <= 4:
        interpretation = (
            f"GAD-7 score is {score}. Minimal anxiety (0-4). "
            "No clinical action required; routine monitoring as appropriate."
        )
    elif score <= 9:
        interpretation = (
            f"GAD-7 score is {score}. Mild anxiety (5-9). "
            "Monitor symptoms; consider re-assessment in 4 weeks. "
            "Follow up with a mental health professional as indicated."
        )
    elif score <= 14:
        interpretation = (
            f"GAD-7 score is {score}. Moderate anxiety (10-14). "
            "Score meets the optimal screening threshold (>=10) for "
            "generalized anxiety disorder (sensitivity 89%, specificity 82%). "
            "Further diagnostic evaluation is recommended."
        )
    else:
        interpretation = (
            f"GAD-7 score is {score}. Severe anxiety (15-21). "
            "Score well above the screening threshold for generalized anxiety "
            "disorder. Active treatment with psychotherapy and/or "
            "pharmacotherapy is likely warranted. Referral to a mental health "
            "professional is recommended."
        )

    # 4. Return ClinicalResult with FHIR metadata
    #    LOINC 70274-6: Generalized anxiety disorder 7 item (GAD-7) total score
    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="70274-6",
        fhir_system="http://loinc.org",
        fhir_display="Generalized anxiety disorder 7 item (GAD-7) total score [Reported.PHQ]",
    )

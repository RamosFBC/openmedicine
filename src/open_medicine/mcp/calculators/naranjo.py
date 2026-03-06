from enum import Enum
from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class NaranjoResponse(str, Enum):
    """Three-option response for each Naranjo scale question."""
    YES = "yes"
    NO = "no"
    DO_NOT_KNOW = "do_not_know"


class NaranjoParams(BaseModel):
    """Parameters to calculate the Naranjo Adverse Drug Reaction (ADR) Probability Scale."""

    previous_conclusive_reports: NaranjoResponse = Field(
        ...,
        description=(
            "Are there previous conclusive reports on this reaction? "
            "(Yes=+1, No=0, Do not know=0)"
        ),
    )
    event_after_drug: NaranjoResponse = Field(
        ...,
        description=(
            "Did the adverse event appear after the suspected drug was administered? "
            "(Yes=+2, No=-1, Do not know=0)"
        ),
    )
    improvement_on_discontinuation: NaranjoResponse = Field(
        ...,
        description=(
            "Did the adverse event improve when the drug was discontinued "
            "or a specific antagonist was administered? "
            "(Yes=+1, No=0, Do not know=0)"
        ),
    )
    reappearance_on_rechallenge: NaranjoResponse = Field(
        ...,
        description=(
            "Did the adverse event reappear when the drug was readministered? "
            "(Yes=+2, No=-1, Do not know=0)"
        ),
    )
    alternative_causes: NaranjoResponse = Field(
        ...,
        description=(
            "Are there alternative causes that could on their own have caused "
            "the reaction? "
            "(Yes=-1, No=+2, Do not know=0)"
        ),
    )
    reaction_with_placebo: NaranjoResponse = Field(
        ...,
        description=(
            "Did the reaction reappear when a placebo was given? "
            "(Yes=-1, No=+1, Do not know=0)"
        ),
    )
    drug_in_toxic_concentration: NaranjoResponse = Field(
        ...,
        description=(
            "Was the drug detected in blood or other fluids in concentrations "
            "known to be toxic? "
            "(Yes=+1, No=0, Do not know=0)"
        ),
    )
    severity_dose_related: NaranjoResponse = Field(
        ...,
        description=(
            "Was the reaction more severe when the dose was increased or less "
            "severe when the dose was decreased? "
            "(Yes=+1, No=0, Do not know=0)"
        ),
    )
    similar_prior_reaction: NaranjoResponse = Field(
        ...,
        description=(
            "Did the patient have a similar reaction to the same or similar "
            "drugs in any previous exposure? "
            "(Yes=+1, No=0, Do not know=0)"
        ),
    )
    confirmed_by_objective_evidence: NaranjoResponse = Field(
        ...,
        description=(
            "Was the adverse event confirmed by any objective evidence? "
            "(Yes=+1, No=0, Do not know=0)"
        ),
    )


def _score_response(response: NaranjoResponse, yes_val: int, no_val: int) -> int:
    """Return the score for a given response. Do not know always scores 0."""
    if response == NaranjoResponse.YES:
        return yes_val
    elif response == NaranjoResponse.NO:
        return no_val
    else:
        return 0


def calculate_naranjo(params: NaranjoParams) -> ClinicalResult:
    """
    Calculates the Naranjo Adverse Drug Reaction (ADR) Probability Scale.
    Estimates the probability that an adverse event is caused by a drug
    rather than other factors.
    Reference: Naranjo CA et al. Clin Pharmacol Ther. 1981;30(2):239-245.
    """
    # Scoring per original publication (Naranjo et al., 1981)
    # Each question has specific Yes/No/Do-not-know point values.
    # Total range: -4 to +13

    # Q1: Previous conclusive reports? (Yes=+1, No=0)
    score = _score_response(params.previous_conclusive_reports, 1, 0)

    # Q2: Event after drug administration? (Yes=+2, No=-1)
    score += _score_response(params.event_after_drug, 2, -1)

    # Q3: Improvement on discontinuation or antagonist? (Yes=+1, No=0)
    score += _score_response(params.improvement_on_discontinuation, 1, 0)

    # Q4: Reappearance on rechallenge? (Yes=+2, No=-1)
    score += _score_response(params.reappearance_on_rechallenge, 2, -1)

    # Q5: Alternative causes? (Yes=-1, No=+2)
    score += _score_response(params.alternative_causes, -1, 2)

    # Q6: Reaction with placebo? (Yes=-1, No=+1)
    score += _score_response(params.reaction_with_placebo, -1, 1)

    # Q7: Drug in toxic concentration? (Yes=+1, No=0)
    score += _score_response(params.drug_in_toxic_concentration, 1, 0)

    # Q8: Severity dose-related? (Yes=+1, No=0)
    score += _score_response(params.severity_dose_related, 1, 0)

    # Q9: Similar prior reaction? (Yes=+1, No=0)
    score += _score_response(params.similar_prior_reaction, 1, 0)

    # Q10: Confirmed by objective evidence? (Yes=+1, No=0)
    score += _score_response(params.confirmed_by_objective_evidence, 1, 0)

    evidence = Evidence(
        source_doi="10.1038/clpt.1981.154",
        level="Derivation & Validation Study",
        description=(
            "A method for estimating the probability of adverse drug reactions "
            "(Naranjo CA et al., Clin Pharmacol Ther 1981)"
        ),
    )

    # Interpretation thresholds from Naranjo et al. 1981:
    #   >= 9  : Definite ADR
    #   5 - 8 : Probable ADR
    #   1 - 4 : Possible ADR
    #   <= 0  : Doubtful ADR
    if score >= 9:
        category = "Definite"
        action = (
            "The adverse drug reaction followed a reasonable temporal sequence "
            "after drug administration, shows a recognized response pattern, "
            "and was confirmed by withdrawal and rechallenge. "
            "Report to pharmacovigilance."
        )
    elif score >= 5:
        category = "Probable"
        action = (
            "The adverse drug reaction followed a reasonable temporal sequence, "
            "shows a recognized response pattern, and was confirmed by drug "
            "withdrawal but not rechallenge. Consider drug discontinuation "
            "and alternative therapy."
        )
    elif score >= 1:
        category = "Possible"
        action = (
            "The adverse drug reaction followed a reasonable temporal sequence "
            "but could also be explained by the patient's disease or other drugs. "
            "Further evaluation is warranted. Consider monitoring or rechallenge "
            "if clinically appropriate."
        )
    else:
        category = "Doubtful"
        action = (
            "The event is likely related to factors other than the suspected drug. "
            "Drug causality is unlikely based on available evidence."
        )

    interpretation = (
        f"Naranjo ADR Probability Scale score is {score}. "
        f"{category} adverse drug reaction. {action}"
    )

    # No dedicated LOINC code exists for the Naranjo ADR Probability Scale.
    # Using None to avoid semantic misrepresentation, consistent with other
    # questionnaire-based scores (e.g., CAGE) that lack LOINC panel codes.
    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code=None,  # No LOINC code for Naranjo ADR scale
        fhir_system=None,
        fhir_display="Naranjo Adverse Drug Reaction Probability Scale score",
    )

# No related guidelines in registry for oncology performance status
from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class ECOGParams(BaseModel):
    """Parameters to calculate the ECOG (Eastern Cooperative Oncology Group) Performance Status."""
    performance_status: int = Field(
        ...,
        ge=0,
        le=5,
        description=(
            "ECOG Performance Status grade from 0 to 5. "
            "0 = Fully active, able to carry on all pre-disease performance without restriction. "
            "1 = Restricted in physically strenuous activity but ambulatory and able to carry out "
            "work of a light or sedentary nature. "
            "2 = Ambulatory and capable of all self-care but unable to carry out any work activities; "
            "up and about more than 50% of waking hours. "
            "3 = Capable of only limited self-care; confined to bed or chair more than 50% of waking hours. "
            "4 = Completely disabled; cannot carry on any self-care; totally confined to bed or chair. "
            "5 = Dead."
        ),
    )


def calculate_ecog(params: ECOGParams) -> ClinicalResult:
    """
    Records and interprets the ECOG (Eastern Cooperative Oncology Group) Performance Status.
    Used in oncology to assess functional status, guide treatment decisions,
    and determine clinical trial eligibility.
    Reference: Oken MM et al. Am J Clin Oncol. 1982;5(6):649-655.
    """
    score = params.performance_status

    evidence = Evidence(
        source_doi="10.1097/00000421-198212000-00014",
        level="Validation Study",
        description=(
            "Toxicity and response criteria of the Eastern Cooperative Oncology Group. "
            "(Oken MM et al., Am J Clin Oncol 1982)"
        ),
    )

    # Grade definitions from original Oken et al. 1982 publication
    grade_definitions = {
        0: "Fully active, able to carry on all pre-disease performance without restriction.",
        1: "Restricted in physically strenuous activity but ambulatory and able to carry out work of a light or sedentary nature.",
        2: "Ambulatory and capable of all self-care but unable to carry out any work activities; up and about more than 50% of waking hours.",
        3: "Capable of only limited self-care; confined to bed or chair more than 50% of waking hours.",
        4: "Completely disabled; cannot carry on any self-care; totally confined to bed or chair.",
        5: "Dead.",
    }

    # Clinical interpretation with functional category and treatment implications
    if score == 0:
        functional_category = "Asymptomatic"
        clinical_implication = (
            "Patient is fully functional. Eligible for all standard therapies and clinical trials."
        )
    elif score == 1:
        functional_category = "Symptomatic, fully ambulatory"
        clinical_implication = (
            "Patient is symptomatic but ambulatory. Generally eligible for most chemotherapy regimens and clinical trials."
        )
    elif score == 2:
        functional_category = "Symptomatic, in bed less than 50% of the day"
        clinical_implication = (
            "Patient is ambulatory and capable of self-care but unable to work. "
            "May be eligible for less intensive treatment regimens. Many clinical trials require ECOG 0-2."
        )
    elif score == 3:
        functional_category = "Symptomatic, in bed more than 50% of the day"
        clinical_implication = (
            "Limited self-care ability with significant functional impairment. "
            "Only limited, well-tolerated therapies should be considered. Consider palliative care referral."
        )
    elif score == 4:
        functional_category = "Bedbound"
        clinical_implication = (
            "Completely disabled with no self-care ability. "
            "Active antineoplastic therapy is generally not recommended. Focus on supportive and palliative care."
        )
    else:  # score == 5
        functional_category = "Dead"
        clinical_implication = "Patient is deceased."

    interpretation = (
        f"ECOG Performance Status is {score} ({functional_category}). "
        f"{grade_definitions[score]} "
        f"{clinical_implication}"
    )

    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="89247-1",
        fhir_system="http://loinc.org",
        fhir_display="ECOG Performance Status score",
    )

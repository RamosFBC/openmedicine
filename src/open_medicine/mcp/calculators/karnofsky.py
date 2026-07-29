# Related guidelines: none
from pydantic import BaseModel, Field
from open_medicine.mcp.base import ClinicalResult, Evidence


# Mapping of KPS scores to their standard definitions
# Source: Karnofsky DA, Burchenal JH. Evaluation of Chemotherapeutic Agents. 1949.
KPS_DEFINITIONS: dict[int, str] = {
    100: "Normal; no complaints; no evidence of disease.",
    90: "Able to carry on normal activity; minor signs or symptoms of disease.",
    80: "Normal activity with effort; some signs or symptoms of disease.",
    70: "Cares for self; unable to carry on normal activity or to do active work.",
    60: "Requires occasional assistance, but is able to care for most personal needs.",
    50: "Requires considerable assistance and frequent medical care.",
    40: "Disabled; requires special care and assistance.",
    30: "Severely disabled; hospital admission is indicated although death not imminent.",
    20: "Very sick; hospital admission necessary; active supportive treatment necessary.",
    10: "Moribund; fatal processes progressing rapidly.",
    0: "Dead.",
}

VALID_KPS_SCORES = sorted(KPS_DEFINITIONS.keys())


class KarnofskyParams(BaseModel):
    """Parameters to calculate the Karnofsky Performance Status (KPS) score."""

    kps_score: int = Field(
        ...,
        description=(
            "Karnofsky Performance Status score as assessed by clinician. "
            "Must be a value from 0 to 100 in increments of 10. "
            "100 = Normal, no complaints; 90 = Minor signs/symptoms; "
            "80 = Normal activity with effort; 70 = Cares for self, unable to work; "
            "60 = Requires occasional assistance; 50 = Requires considerable assistance; "
            "40 = Disabled, requires special care; 30 = Severely disabled, hospitalization indicated; "
            "20 = Very sick, hospitalization necessary; 10 = Moribund; 0 = Dead."
        ),
        ge=0,
        le=100,
    )


def calculate_karnofsky(params: KarnofskyParams) -> ClinicalResult:
    """
    Records and interprets the Karnofsky Performance Status (KPS) score.
    The KPS quantifies a patient's general functional status on an 11-point scale
    (0-100 in increments of 10), commonly used in oncology to assess fitness for
    chemotherapy and to estimate prognosis.
    Reference: Schag CC et al. J Clin Oncol. 1984.
    """
    score = params.kps_score

    # Validate that the score is a multiple of 10
    if score % 10 != 0:
        return ClinicalResult(
            value=None,
            interpretation=(
                f"Invalid KPS score: {score}. The Karnofsky Performance Status "
                "must be a value from 0 to 100 in increments of 10."
            ),
            evidence=Evidence(
                source_doi="10.1200/JCO.1984.2.3.187",
                level="Validation Study",
                description=(
                    "Karnofsky performance status revisited: reliability, validity, "
                    "and guidelines. Schag CC et al. J Clin Oncol. 1984;2(3):187-193."
                ),
            ),
        )

    definition = KPS_DEFINITIONS[score]

    # Determine functional status category (three-tier grouping from original scale)
    if score >= 80:
        category = "Able to carry on normal activity and to work; no special care needed"
    elif score >= 50:
        category = "Unable to work; able to live at home and care for most personal needs; varying amount of assistance needed"
    else:
        # 0-40
        category = "Unable to care for self; requires equivalent of institutional or hospital care; disease may be progressing rapidly"

    interpretation = (
        f"Karnofsky Performance Status is {score}%. "
        f"Definition: {definition} "
        f"Functional category: {category}."
    )

    evidence = Evidence(
        source_doi="10.1200/JCO.1984.2.3.187",
        level="Validation Study",
        description=(
            "Karnofsky performance status revisited: reliability, validity, "
            "and guidelines. Schag CC et al. J Clin Oncol. 1984;2(3):187-193."
        ),
    )

    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="89243-0",
        fhir_system="http://loinc.org",
        fhir_display="Karnofsky Performance Status score",
    )

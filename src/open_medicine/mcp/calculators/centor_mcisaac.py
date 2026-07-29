# Related guidelines: none
from pydantic import BaseModel, Field
from open_medicine.mcp.base import ClinicalResult, Evidence


class CentorMcIsaacParams(BaseModel):
    """Parameters to calculate the Modified Centor (McIsaac) Score for Strep Pharyngitis."""
    age: int = Field(..., description="Age in years (validated for ages >= 3)")
    tonsillar_swelling_or_exudate: bool = Field(
        ..., description="Tonsillar swelling or exudates present on exam"
    )
    tender_anterior_cervical_lymphadenopathy: bool = Field(
        ..., description="Tender or swollen anterior cervical lymph nodes present on exam"
    )
    fever: bool = Field(
        ..., description="Temperature >38 C (100.4 F) or history of fever"
    )
    absence_of_cough: bool = Field(
        ..., description="Cough is absent (patient does NOT have a cough)"
    )


def calculate_centor_mcisaac(params: CentorMcIsaacParams) -> ClinicalResult:
    """
    Calculates the Modified Centor (McIsaac) Score for estimating the
    probability of group A streptococcal (GAS) pharyngitis.

    The original Centor criteria (1981) included four clinical findings:
    tonsillar exudates, tender anterior cervical lymphadenopathy, fever,
    and absence of cough. McIsaac et al. (1998) added an age modifier
    to improve diagnostic accuracy across age groups.

    Reference: McIsaac WJ et al. CMAJ. 1998;158(1):75-83. PMID: 9475915.
    """
    # Age validation: McIsaac 1998 derivation study included patients aged
    # 3-76 years; patients under 3 were explicitly excluded.
    if params.age < 3:
        return ClinicalResult(
            value=None,
            interpretation=(
                "Modified Centor (McIsaac) Score is only validated for ages >= 3. "
                "Patients under 3 years were excluded from the derivation study."
            ),
            evidence=Evidence(
                source_doi="PMID:9475915",
                level="Derivation & Validation Study",
                description="McIsaac WJ et al. A clinical score to reduce unnecessary antibiotic use in patients with sore throat. CMAJ. 1998;158(1):75-83."
            ),
            # No specific LOINC observation code exists for the Centor/McIsaac score.
            # LP419468-2 is a LOINC Part code (not an observation code) and should not
            # be used in FHIR Observation resources. Setting to None until a proper
            # LOINC observation code is registered.
            fhir_code=None,
            fhir_system=None,
            fhir_display="Modified Centor (McIsaac) score"
        )

    score = 0

    # Criterion 1: Tonsillar swelling or exudates (+1)
    if params.tonsillar_swelling_or_exudate:
        score += 1

    # Criterion 2: Tender/swollen anterior cervical lymphadenopathy (+1)
    if params.tender_anterior_cervical_lymphadenopathy:
        score += 1

    # Criterion 3: Fever >38 C or history of fever (+1)
    if params.fever:
        score += 1

    # Criterion 4: Absence of cough (+1)
    if params.absence_of_cough:
        score += 1

    # Criterion 5: Age adjustment
    # Age 3-14: +1 point
    # Age 15-44: 0 points
    # Age >=45: -1 point
    if params.age < 15:
        score += 1
    elif params.age >= 45:
        score -= 1

    evidence = Evidence(
        source_doi="PMID:9475915",
        level="Derivation & Validation Study",
        description="McIsaac WJ et al. A clinical score to reduce unnecessary antibiotic use in patients with sore throat. CMAJ. 1998;158(1):75-83."
    )

    # Interpretation based on validated risk strata
    if score <= 0:
        interpretation = (
            f"Modified Centor (McIsaac) Score is {score}. "
            f"Very low risk of GAS pharyngitis (1-2.5%). "
            f"No further testing or antibiotics necessary. "
            f"Symptomatic treatment recommended."
        )
    elif score == 1:
        interpretation = (
            f"Modified Centor (McIsaac) Score is {score}. "
            f"Low risk of GAS pharyngitis (5-10%). "
            f"No further testing or antibiotics necessary. "
            f"Consider rapid antigen detection test (RADT) only if high clinical suspicion."
        )
    elif score == 2:
        interpretation = (
            f"Modified Centor (McIsaac) Score is {score}. "
            f"Moderate risk of GAS pharyngitis (11-17%). "
            f"Perform rapid antigen detection test (RADT) and/or throat culture. "
            f"Treat with antibiotics only if test is positive."
        )
    elif score == 3:
        interpretation = (
            f"Modified Centor (McIsaac) Score is {score}. "
            f"Moderately high risk of GAS pharyngitis (28-35%). "
            f"Perform rapid antigen detection test (RADT) and/or throat culture. "
            f"Treat with antibiotics only if test is positive."
        )
    else:  # score >= 4
        interpretation = (
            f"Modified Centor (McIsaac) Score is {score}. "
            f"High risk of GAS pharyngitis (51-53%). "
            f"Perform rapid antigen detection test (RADT) and/or throat culture. "
            f"Consider empiric antibiotic therapy or treat if test is positive."
        )

    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        # No specific LOINC observation code exists for the Centor/McIsaac score.
        # LP419468-2 is a LOINC Part code (not an observation code) and should not
        # be used in FHIR Observation resources. Setting to None until a proper
        # LOINC observation code is registered.
        fhir_code=None,
        fhir_system=None,
        fhir_display="Modified Centor (McIsaac) score"
    )

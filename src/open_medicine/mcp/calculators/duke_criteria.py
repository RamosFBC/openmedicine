# Related guidelines: aha_endocarditis_2015 (diagnosis section)

from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class DukeCriteriaParams(BaseModel):
    """Parameters to evaluate the Modified Duke Criteria for diagnosis of Infective Endocarditis (IE)."""

    # --- Pathological Criteria ---
    pathological_vegetation: bool = Field(
        False,
        description=(
            "Microorganisms demonstrated by culture or histologic examination "
            "of a vegetation, a vegetation that has embolized, or an intracardiac "
            "abscess specimen."
        ),
    )
    pathological_lesions: bool = Field(
        False,
        description=(
            "Vegetation or intracardiac abscess confirmed by histologic examination "
            "showing active endocarditis."
        ),
    )

    # --- Major Clinical Criteria ---
    # Major 1: Blood culture positive for IE
    blood_culture_typical_organisms: bool = Field(
        False,
        description=(
            "Typical microorganisms consistent with IE from 2 separate blood cultures: "
            "Viridans streptococci, Streptococcus gallolyticus (bovis), HACEK group, "
            "Staphylococcus aureus, or community-acquired enterococci in the absence "
            "of a primary focus."
        ),
    )
    blood_culture_persistently_positive: bool = Field(
        False,
        description=(
            "Persistently positive blood cultures defined as: recovery of a microorganism "
            "consistent with IE from blood cultures drawn more than 12 hours apart; or "
            "all of 3 or a majority of >=4 separate cultures of blood (with first and "
            "last sample drawn at least 1 hour apart)."
        ),
    )
    coxiella_burnetii: bool = Field(
        False,
        description=(
            "Single positive blood culture for Coxiella burnetii or anti-phase I IgG "
            "antibody titer >1:800."
        ),
    )

    # Major 2: Evidence of endocardial involvement
    echocardiogram_positive: bool = Field(
        False,
        description=(
            "Positive echocardiogram for IE defined as: oscillating intracardiac mass "
            "on valve or supporting structures, in the path of regurgitant jets, or on "
            "implanted material in the absence of an alternative anatomic explanation; "
            "or abscess; or new partial dehiscence of prosthetic valve."
        ),
    )
    new_valvular_regurgitation: bool = Field(
        False,
        description=(
            "New valvular regurgitation (worsening or changing of pre-existing murmur "
            "not sufficient)."
        ),
    )

    # --- Minor Clinical Criteria ---
    predisposing_condition: bool = Field(
        False,
        description=(
            "Predisposing heart condition (e.g., prosthetic valve, previous IE, "
            "congenital heart disease, valvular heart disease) or injection drug use."
        ),
    )
    fever: bool = Field(
        False,
        description="Fever: temperature greater than 38 degrees C (100.4 degrees F).",
    )
    vascular_phenomena: bool = Field(
        False,
        description=(
            "Vascular phenomena: major arterial emboli, septic pulmonary infarcts, "
            "mycotic aneurysm, intracranial hemorrhage, conjunctival hemorrhages, "
            "or Janeway lesions."
        ),
    )
    immunologic_phenomena: bool = Field(
        False,
        description=(
            "Immunologic phenomena: glomerulonephritis, Osler nodes, Roth spots, "
            "or positive rheumatoid factor."
        ),
    )
    microbiological_evidence_minor: bool = Field(
        False,
        description=(
            "Microbiological evidence: positive blood culture but does not meet a major "
            "criterion as noted above, or serological evidence of active infection with "
            "organism consistent with IE."
        ),
    )


def calculate_duke_criteria(params: DukeCriteriaParams) -> ClinicalResult:
    """
    Evaluates the Modified Duke Criteria for the diagnosis of Infective Endocarditis.
    Classifies patients as Definite IE, Possible IE, or Rejected IE based on
    pathological and clinical (major + minor) criteria.

    Reference: Li JS et al. Clin Infect Dis. 2000;30(4):633-638.
    """

    # --- Count pathological criteria ---
    pathological_criteria_met = params.pathological_vegetation or params.pathological_lesions

    # --- Count major clinical criteria ---
    # Major criterion 1: Positive blood cultures for IE
    # Any one of the three blood-culture sub-criteria counts as one major criterion
    major_blood_culture = (
        params.blood_culture_typical_organisms
        or params.blood_culture_persistently_positive
        or params.coxiella_burnetii
    )

    # Major criterion 2: Evidence of endocardial involvement
    major_endocardial = (
        params.echocardiogram_positive
        or params.new_valvular_regurgitation
    )

    major_count = int(major_blood_culture) + int(major_endocardial)

    # --- Count minor clinical criteria ---
    minor_count = sum([
        params.predisposing_condition,
        params.fever,
        params.vascular_phenomena,
        params.immunologic_phenomena,
        params.microbiological_evidence_minor,
    ])

    # --- Classification per Modified Duke Criteria (Li JS et al., 2000) ---
    # Definite IE (Pathological): pathological criteria met
    # Definite IE (Clinical): 2 major, OR 1 major + 3 minor, OR 5 minor
    # Possible IE: 1 major + 1 minor, OR 3 minor
    # Rejected: firm alternative diagnosis, resolution with <=4 days antibiotics,
    #   no pathologic evidence with <4 days antibiotics, or does not meet possible

    if pathological_criteria_met:
        classification = "Definite"
        basis = "pathological"
    elif major_count == 2:
        classification = "Definite"
        basis = "clinical (2 major criteria)"
    elif major_count == 1 and minor_count >= 3:
        classification = "Definite"
        basis = "clinical (1 major + 3 minor criteria)"
    elif major_count == 0 and minor_count >= 5:
        classification = "Definite"
        basis = "clinical (5 minor criteria)"
    elif major_count == 1 and minor_count >= 1:
        classification = "Possible"
        basis = "clinical (1 major + 1-2 minor criteria)"
    elif major_count == 0 and minor_count >= 3:
        classification = "Possible"
        basis = "clinical (3 minor criteria)"
    else:
        classification = "Rejected"
        basis = "does not meet criteria for possible or definite IE"

    # Build Evidence
    evidence = Evidence(
        source_doi="10.1086/313753",
        level="Validation Study",
        description=(
            "Li JS et al. Proposed modifications to the Duke criteria for the "
            "diagnosis of infective endocarditis. Clin Infect Dis. 2000;30(4):633-638."
        ),
    )

    # Build interpretation
    criteria_summary = f"{major_count} major and {minor_count} minor clinical criteria met"
    if pathological_criteria_met:
        criteria_summary = f"Pathological criteria met; {criteria_summary}"

    if classification == "Definite":
        interpretation = (
            f"Modified Duke Criteria classification: {classification} Infective "
            f"Endocarditis ({basis}). {criteria_summary}. "
            f"Initiate appropriate antimicrobial therapy and consider surgical "
            f"consultation based on clinical presentation."
        )
    elif classification == "Possible":
        interpretation = (
            f"Modified Duke Criteria classification: {classification} Infective "
            f"Endocarditis ({basis}). {criteria_summary}. "
            f"Further workup is recommended. Consider repeat blood cultures, "
            f"advanced imaging, or transesophageal echocardiography (TEE) to "
            f"clarify diagnosis."
        )
    else:
        interpretation = (
            f"Modified Duke Criteria classification: {classification} "
            f"({basis}). {criteria_summary}. "
            f"Infective endocarditis is unlikely by these criteria. Consider "
            f"alternative diagnoses. Note: clinical judgment should still prevail; "
            f"rejected classification also applies if a firm alternative diagnosis "
            f"is established or symptoms resolve with <=4 days of antibiotics."
        )

    return ClinicalResult(
        value=classification,
        interpretation=interpretation,
        evidence=evidence,
        # No LOINC observation code exists for Duke Criteria classification.
        # LOINC 75325-1 represents "Symptom" (not a diagnostic classification),
        # so using None to avoid semantic misrepresentation.
        fhir_code=None,
        fhir_system=None,
        fhir_display="Modified Duke Criteria classification",
    )

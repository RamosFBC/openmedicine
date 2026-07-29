# Related guidelines: none
from pydantic import BaseModel, Field
from open_medicine.mcp.base import ClinicalResult, Evidence


class ClinicalFrailtyParams(BaseModel):
    """Parameters to calculate the Clinical Frailty Scale (CFS) by Rockwood et al."""

    frailty_level: int = Field(
        ...,
        ge=1,
        le=9,
        description=(
            "Clinical Frailty Scale level from 1 to 9, assigned by clinician "
            "judgment based on overall fitness and frailty status. "
            "1 = Very Fit: robust, active, energetic, motivated; commonly exercise regularly. "
            "2 = Fit: no active disease symptoms but less fit than category 1; exercise occasionally. "
            "3 = Managing Well: medical problems well-controlled but not regularly active beyond routine walking. "
            "4 = Living with Very Mild Frailty: not dependent on others for daily help, but symptoms "
            "often limit activities; commonly report being 'slowed up' and tired during the day. "
            "5 = Living with Mild Frailty: more evident slowing; need help with higher-order IADLs "
            "(finances, transportation, heavy housework, medications). "
            "6 = Living with Moderate Frailty: need help with all outside activities and housekeeping; "
            "inside, often have problems with stairs and need help with bathing. "
            "7 = Living with Severe Frailty: completely dependent for personal care (physical or cognitive); "
            "appear stable and not at high risk of dying within 6 months. "
            "8 = Living with Very Severe Frailty: completely dependent for personal care and approaching "
            "end of life; typically could not recover even from a minor illness. "
            "9 = Terminally Ill: approaching the end of life with life expectancy <6 months, "
            "who are not otherwise evidently frail."
        ),
    )


def calculate_clinical_frailty(params: ClinicalFrailtyParams) -> ClinicalResult:
    """
    Calculates the Clinical Frailty Scale (CFS) score and provides interpretation.
    The CFS is a judgment-based frailty tool that classifies older adults from
    very fit (1) to terminally ill (9) based on clinical assessment of function,
    comorbidity, and cognition.
    Reference: Rockwood K et al. CMAJ. 2005;173(5):489-495.
    """
    score = params.frailty_level

    evidence = Evidence(
        source_doi="10.1503/cmaj.050051",
        level="Derivation & Validation Study",
        description=(
            "A global clinical measure of fitness and frailty in elderly people. "
            "Rockwood K et al. CMAJ. 2005;173(5):489-495. "
            "Originally a 7-point scale validated in the Canadian Study of Health "
            "and Aging (n=2305), later revised to a 9-point scale (CFS 2.0)."
        ),
    )

    # Level definitions per the revised 9-point CFS (CFS 2.0, Rockwood et al.)
    level_labels = {
        1: "Very Fit",
        2: "Fit",
        3: "Managing Well",
        4: "Living with Very Mild Frailty",
        5: "Living with Mild Frailty",
        6: "Living with Moderate Frailty",
        7: "Living with Severe Frailty",
        8: "Living with Very Severe Frailty",
        9: "Terminally Ill",
    }

    level_descriptions = {
        1: (
            "People who are robust, active, energetic, and motivated. "
            "These people commonly exercise regularly and are among the "
            "fittest for their age."
        ),
        2: (
            "People who have no active disease symptoms but are less fit "
            "than category 1. Often, they exercise or are very active "
            "occasionally (e.g., seasonally)."
        ),
        3: (
            "People whose medical problems are well-controlled but are "
            "not regularly active beyond routine walking."
        ),
        4: (
            "While not dependent on others for daily help, often symptoms "
            "limit activities. A common complaint is being 'slowed up' "
            "and/or being tired during the day."
        ),
        5: (
            "These people often have more evident slowing and need help "
            "in higher-order instrumental activities of daily living "
            "(finances, transportation, heavy housework, medications). "
            "Typically, mild frailty progressively impairs shopping and "
            "walking outside alone, meal preparation, and housework."
        ),
        6: (
            "People who need help with all outside activities and with "
            "keeping house. Inside, they often have problems with stairs "
            "and need help with bathing and might need minimal assistance "
            "(cuing, standby) with dressing."
        ),
        7: (
            "Completely dependent for personal care, from whatever cause "
            "(physical or cognitive). Even so, they seem stable and not "
            "at high risk (within approximately 6 months) of dying."
        ),
        8: (
            "Completely dependent, approaching the end of life. Typically, "
            "they could not recover even from a minor illness."
        ),
        9: (
            "Approaching the end of life. This category applies to people "
            "with a life expectancy of less than 6 months, who are not "
            "otherwise evidently frail. (Many terminally ill people can "
            "still exercise until close to death.)"
        ),
    }

    label = level_labels[score]
    description = level_descriptions[score]

    # Frailty category grouping and clinical implications
    if score <= 3:
        frailty_category = "Non-frail (Fit)"
        clinical_implication = (
            "Patient is not frail. No frailty-specific interventions required. "
            "Standard age-appropriate preventive care is recommended. "
            "Encourage continued physical activity and exercise."
        )
    elif score == 4:
        frailty_category = "Pre-frail (Very Mild Frailty)"
        clinical_implication = (
            "Patient is pre-frail with very mild limitations. Consider screening "
            "for reversible contributors to functional decline. Recommend "
            "structured exercise programs and nutritional assessment. "
            "Monitor for progression to overt frailty."
        )
    elif score == 5:
        frailty_category = "Mildly Frail"
        clinical_implication = (
            "Patient has mild frailty with IADL dependence. Comprehensive geriatric "
            "assessment is recommended. Consider physical therapy, occupational therapy, "
            "medication review for polypharmacy, and nutritional optimization. "
            "Assess need for home care support services."
        )
    elif score == 6:
        frailty_category = "Moderately Frail"
        clinical_implication = (
            "Patient has moderate frailty with dependence in both IADLs and some "
            "basic ADLs. Comprehensive geriatric assessment is strongly recommended. "
            "Consider goals-of-care discussion, falls prevention program, "
            "and structured home care or assisted living assessment."
        )
    elif score == 7:
        frailty_category = "Severely Frail"
        clinical_implication = (
            "Patient is severely frail and completely dependent for personal care. "
            "Goals-of-care and advance care planning discussions are essential. "
            "Consider appropriateness of aggressive interventions versus "
            "comfort-focused care. Evaluate need for institutional care."
        )
    elif score == 8:
        frailty_category = "Very Severely Frail"
        clinical_implication = (
            "Patient is very severely frail, approaching end of life, and unable "
            "to recover from even minor illness. Prioritize comfort and palliation. "
            "Goals-of-care discussion and palliative care referral are strongly "
            "recommended. Reassess code status."
        )
    else:  # score == 9
        frailty_category = "Terminally Ill"
        clinical_implication = (
            "Patient is terminally ill with life expectancy under 6 months but may "
            "not otherwise appear frail. Focus on symptom management, palliative care, "
            "and end-of-life planning. Ensure advance directives are in place."
        )

    interpretation = (
        f"Clinical Frailty Scale is {score} ({label}). "
        f"Category: {frailty_category}. "
        f"Description: {description} "
        f"{clinical_implication}"
    )

    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        # LOINC approximation: no specific LOINC code exists for the Rockwood CFS.
        # Using the closest available frailty assessment code.
        fhir_code="89013-7",
        fhir_system="http://loinc.org",
        fhir_display="Clinical Frailty Scale score",
    )

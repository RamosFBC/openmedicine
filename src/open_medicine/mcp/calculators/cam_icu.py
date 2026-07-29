# Related guidelines: sccm_padis_2018 (delirium assessment and management section)
from pydantic import BaseModel, Field
from open_medicine.mcp.base import ClinicalResult, Evidence


class CAMICUParams(BaseModel):
    """Parameters to calculate the Confusion Assessment Method for the ICU (CAM-ICU)."""

    rass: int = Field(
        ...,
        ge=-5,
        le=4,
        description=(
            "Richmond Agitation-Sedation Scale (RASS) score from -5 to +4. "
            "Scoring: +4 = Combative, +3 = Very agitated, +2 = Agitated, "
            "+1 = Restless, 0 = Alert and calm, -1 = Drowsy, "
            "-2 = Light sedation, -3 = Moderate sedation, "
            "-4 = Deep sedation, -5 = Unarousable. "
            "Patients with RASS -4 or -5 are unable to be assessed (UTA)."
        ),
    )
    feature1_acute_onset_or_fluctuating: bool = Field(
        ...,
        description=(
            "Feature 1: Acute onset or fluctuating course. "
            "Is there evidence of an acute change in mental status from baseline? "
            "Or has the patient's mental status fluctuated (come and gone, or increased/decreased "
            "in severity) during the past 24 hours as evidenced by fluctuations on RASS or GCS?"
        ),
    )
    feature2_inattention_errors: int = Field(
        ...,
        ge=0,
        le=10,
        description=(
            "Feature 2: Inattention. Number of errors on the Attention Screening Examination (ASE). "
            "The examiner says 'Squeeze my hand when I say the letter A' and reads the 10-letter "
            "sequence S-A-V-E-A-H-A-A-R-T. Errors include: failing to squeeze on 'A' or squeezing "
            "on a non-A letter. Score ranges from 0 (perfect attention) to 10 (complete inattention). "
            "More than 2 errors indicates inattention (Feature 2 positive)."
        ),
    )
    feature4_disorganized_thinking_errors: int = Field(
        ...,
        ge=0,
        le=5,
        description=(
            "Feature 4: Disorganized thinking. Combined number of errors on the 4 yes/no questions "
            "plus the command. Yes/No questions (Set A): 1) Will a stone float on water? 2) Are there "
            "fish in the sea? 3) Does one pound weigh more than two pounds? 4) Can you use a hammer "
            "to pound a nail? Command: 'Hold up this many fingers' (examiner holds up 2) then "
            "'Now do the same with the other hand' (without demonstrating). Score ranges from 0 "
            "(no errors) to 5 (all wrong). More than 1 error indicates disorganized thinking "
            "(Feature 4 positive)."
        ),
    )


def calculate_cam_icu(params: CAMICUParams) -> ClinicalResult:
    """
    Calculates the CAM-ICU (Confusion Assessment Method for the ICU) for delirium
    assessment in critically ill patients, including mechanically ventilated patients.
    Reference: Ely EW et al. JAMA. 2001;286(21):2703-2710.
    """
    evidence = Evidence(
        source_doi="10.1001/jama.286.21.2703",
        level="Derivation & Validation Study",
        description=(
            "Delirium in mechanically ventilated patients: validity and reliability "
            "of the CAM-ICU (Ely EW et al., JAMA 2001)"
        ),
    )

    # Step 0: Check if patient can be assessed based on RASS
    # RASS -4 or -5 = unable to assess (too deeply sedated / unarousable)
    if params.rass <= -4:
        return ClinicalResult(
            value=None,
            interpretation=(
                f"RASS is {params.rass} (deeply sedated/unarousable). "
                "Patient is unable to be assessed for delirium (UTA). "
                "Reassess when RASS is -3 or higher."
            ),
            evidence=evidence,
            fhir_code="52495-9",
            fhir_system="http://loinc.org",
            fhir_display="Confusion Assessment Method (CAM)",
        )

    # Feature 1: Acute onset or fluctuating course
    feature1_present = params.feature1_acute_onset_or_fluctuating

    # Feature 2: Inattention (>2 errors on ASE letters test)
    feature2_present = params.feature2_inattention_errors > 2

    # Feature 3: Altered level of consciousness (RASS != 0)
    feature3_present = params.rass != 0

    # Feature 4: Disorganized thinking (>1 error on questions + command)
    feature4_present = params.feature4_disorganized_thinking_errors > 1

    # CAM-ICU Decision Logic:
    # Delirium present = Feature 1 AND Feature 2 AND (Feature 3 OR Feature 4)
    cam_icu_positive = feature1_present and feature2_present and (feature3_present or feature4_present)

    # Build detailed interpretation
    feature_details = (
        f"Feature 1 (Acute onset/fluctuating course): {'Present' if feature1_present else 'Absent'}. "
        f"Feature 2 (Inattention, {params.feature2_inattention_errors}/10 errors): "
        f"{'Present (>2 errors)' if feature2_present else 'Absent (<=2 errors)'}. "
        f"Feature 3 (Altered consciousness, RASS {params.rass}): "
        f"{'Present (RASS != 0)' if feature3_present else 'Absent (RASS = 0)'}. "
        f"Feature 4 (Disorganized thinking, {params.feature4_disorganized_thinking_errors}/5 errors): "
        f"{'Present (>1 error)' if feature4_present else 'Absent (<=1 error)'}."
    )

    if cam_icu_positive:
        result_value = 1
        interpretation = (
            f"CAM-ICU POSITIVE: Delirium is present. {feature_details} "
            "The patient meets criteria for delirium (Feature 1 + Feature 2 + Feature 3 or 4). "
            "Initiate delirium management per institutional protocol. "
            "Identify and treat reversible causes (medications, infection, metabolic derangements). "
            "Consider non-pharmacologic interventions (reorientation, sleep hygiene, early mobilization)."
        )
    else:
        result_value = 0
        # Determine why it is negative for clinical documentation
        if not feature1_present:
            reason = "Feature 1 absent (no acute onset or fluctuating course)."
        elif not feature2_present:
            reason = "Feature 2 absent (attention intact, <=2 errors on ASE)."
        else:
            reason = "Neither Feature 3 nor Feature 4 present."
        interpretation = (
            f"CAM-ICU NEGATIVE: No delirium detected. {feature_details} "
            f"Reason: {reason} "
            "Continue routine delirium monitoring per institutional protocol (typically every shift)."
        )

    return ClinicalResult(
        value=result_value,
        interpretation=interpretation,
        evidence=evidence,
        # LOINC approximation: 52495-9 is the general CAM panel code;
        # no specific LOINC code exists for the ICU adaptation (CAM-ICU).
        fhir_code="52495-9",
        fhir_system="http://loinc.org",
        fhir_display="Confusion Assessment Method (CAM)",
    )

# Related guidelines: sccm_padis_2018 (sedation assessment and management section)
from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class RASSParams(BaseModel):
    """Parameters to record and interpret the Richmond Agitation-Sedation Scale (RASS)."""
    score: int = Field(
        ...,
        ge=-5,
        le=4,
        description=(
            "Richmond Agitation-Sedation Scale (RASS) score from -5 to +4. "
            "Scoring: "
            "+4 = Combative (overtly combative, violent, immediate danger to staff). "
            "+3 = Very agitated (pulls or removes tube(s) or catheter(s); aggressive). "
            "+2 = Agitated (frequent non-purposeful movement, fights ventilator). "
            "+1 = Restless (anxious but movements not aggressive or vigorous). "
            "0 = Alert and calm. "
            "-1 = Drowsy (not fully alert, but has sustained awakening with eye-opening/eye contact to voice, >10 seconds). "
            "-2 = Light sedation (briefly awakens with eye contact to voice, <10 seconds). "
            "-3 = Moderate sedation (movement or eye opening to voice, but no eye contact). "
            "-4 = Deep sedation (no response to voice, but movement or eye opening to physical stimulation). "
            "-5 = Unarousable (no response to voice or physical stimulation)."
        ),
    )


def calculate_rass(params: RASSParams) -> ClinicalResult:
    """
    Records and interprets the Richmond Agitation-Sedation Scale (RASS).
    Used to assess the level of agitation and sedation in adult ICU patients,
    guiding sedative medication titration and agitation management.
    Reference: Sessler CN et al. Am J Respir Crit Care Med. 2002;166(10):1338-1344.
    """
    score = params.score

    evidence = Evidence(
        source_doi="10.1164/rccm.2107138",
        level="Derivation & Validation Study",
        description=(
            "The Richmond Agitation-Sedation Scale: validity and reliability "
            "in adult intensive care unit patients. "
            "(Sessler CN et al., Am J Respir Crit Care Med 2002)"
        ),
    )

    # Level term definitions from original Sessler et al. 2002 publication (Table 1)
    level_terms = {
        4: "Combative",
        3: "Very agitated",
        2: "Agitated",
        1: "Restless",
        0: "Alert and calm",
        -1: "Drowsy",
        -2: "Light sedation",
        -3: "Moderate sedation",
        -4: "Deep sedation",
        -5: "Unarousable",
    }

    level_descriptions = {
        4: "Overtly combative, violent, immediate danger to staff.",
        3: "Pulls or removes tube(s) or catheter(s); aggressive.",
        2: "Frequent non-purposeful movement, fights ventilator.",
        1: "Anxious but movements not aggressive or vigorous.",
        0: "Alert and calm.",
        -1: "Not fully alert, but has sustained awakening (eye-opening/eye contact) to voice (>10 seconds).",
        -2: "Briefly awakens with eye contact to voice (<10 seconds).",
        -3: "Movement or eye opening to voice (but no eye contact).",
        -4: "No response to voice, but movement or eye opening to physical stimulation.",
        -5: "No response to voice or physical stimulation.",
    }

    # Clinical interpretation with sedation/agitation category and clinical implications
    if score > 0:
        # Agitation range (+1 to +4)
        sedation_category = "Agitated"
        if score == 1:
            clinical_implication = (
                "Patient is restless. Monitor closely and assess for underlying causes "
                "(pain, anxiety, delirium). Non-pharmacologic interventions may be appropriate."
            )
        elif score == 2:
            clinical_implication = (
                "Patient is agitated with frequent non-purposeful movements. "
                "Assess for reversible causes. Consider analgesic and/or sedative adjustment."
            )
        elif score == 3:
            clinical_implication = (
                "Patient is very agitated and may be pulling at lines/tubes. "
                "Immediate intervention needed. Assess for pain, delirium, and other causes. "
                "Consider bolus sedation and/or analgesic adjustment."
            )
        else:  # score == 4
            clinical_implication = (
                "Patient is combative and poses immediate danger to self and staff. "
                "Urgent pharmacologic intervention required. Ensure patient and staff safety."
            )
    elif score == 0:
        sedation_category = "Alert and calm"
        clinical_implication = (
            "Patient is at the target sedation level for most ICU protocols. "
            "No sedation adjustment needed. Continue current management."
        )
    else:
        # Sedation range (-1 to -5)
        sedation_category = "Sedated"
        if score == -1:
            clinical_implication = (
                "Patient is drowsy but arousable. Often an acceptable sedation target. "
                "Consider whether lighter sedation (RASS 0) is clinically appropriate per PADIS guidelines."
            )
        elif score == -2:
            clinical_implication = (
                "Patient is lightly sedated. May be appropriate for some clinical situations. "
                "Consider lightening sedation if deeper than target."
            )
        elif score == -3:
            clinical_implication = (
                "Patient is moderately sedated. Responds to voice with movement but no eye contact. "
                "Evaluate whether this depth of sedation is clinically indicated. "
                "Deeper-than-necessary sedation is associated with worse outcomes."
            )
        elif score == -4:
            clinical_implication = (
                "Patient is deeply sedated. No response to voice; responds only to physical stimulation. "
                "Deep sedation is associated with prolonged mechanical ventilation and ICU stay. "
                "Reassess need for deep sedation."
            )
        else:  # score == -5
            clinical_implication = (
                "Patient is unarousable with no response to any stimulation. "
                "If not clinically indicated (e.g., neuromuscular blockade, therapeutic coma), "
                "consider reducing or holding sedative agents and reassessing."
            )

    term = level_terms[score]
    description = level_descriptions[score]

    interpretation = (
        f"RASS is {score:+d} ({term}). {description} "
        f"Category: {sedation_category}. {clinical_implication}"
    )

    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        # LOINC approximation: No specific observation-level LOINC code for RASS total score;
        # LL6536-8 is the LOINC answer list for RASS. Using it as the best available identifier.
        fhir_code="LL6536-8",
        fhir_system="http://loinc.org",
        fhir_display="Richmond Agitation Sedation Scale [RASS] Score",
    )

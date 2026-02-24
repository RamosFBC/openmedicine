from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence

# Related guidelines: aha_asa_stroke_2019 (initial_assessment, thrombolysis, thrombectomy sections)


class NIHSSParams(BaseModel):
    """Parameters to calculate the NIH Stroke Scale (NIHSS)."""
    loc: int = Field(..., ge=0, le=3, description="1a. Level of Consciousness: 0=Alert, 1=Not alert but arousable, 2=Not alert, obtunded, 3=Unresponsive")
    loc_questions: int = Field(..., ge=0, le=2, description="1b. LOC Questions (month/age): 0=Both correct, 1=One correct, 2=Neither correct")
    loc_commands: int = Field(..., ge=0, le=2, description="1c. LOC Commands (open/close eyes, grip/release): 0=Both correct, 1=One correct, 2=Neither correct")
    best_gaze: int = Field(..., ge=0, le=2, description="2. Best Gaze (horizontal eye movements): 0=Normal, 1=Partial gaze palsy, 2=Forced deviation or total gaze paresis")
    visual_fields: int = Field(..., ge=0, le=3, description="3. Visual Fields: 0=No visual loss, 1=Partial hemianopia, 2=Complete hemianopia, 3=Bilateral hemianopia (blind)")
    facial_palsy: int = Field(..., ge=0, le=3, description="4. Facial Palsy: 0=Normal, 1=Minor paralysis, 2=Partial paralysis, 3=Complete paralysis")
    left_arm_motor: int = Field(..., ge=0, le=4, description="5a. Left Arm Motor (hold at 90/45 degrees): 0=No drift, 1=Drift, 2=Some effort against gravity, 3=No effort against gravity, 4=No movement")
    right_arm_motor: int = Field(..., ge=0, le=4, description="5b. Right Arm Motor: 0=No drift, 1=Drift, 2=Some effort against gravity, 3=No effort against gravity, 4=No movement")
    left_leg_motor: int = Field(..., ge=0, le=4, description="6a. Left Leg Motor (hold at 30 degrees): 0=No drift, 1=Drift, 2=Some effort against gravity, 3=No effort against gravity, 4=No movement")
    right_leg_motor: int = Field(..., ge=0, le=4, description="6b. Right Leg Motor: 0=No drift, 1=Drift, 2=Some effort against gravity, 3=No effort against gravity, 4=No movement")
    limb_ataxia: int = Field(..., ge=0, le=2, description="7. Limb Ataxia: 0=Absent, 1=Present in one limb, 2=Present in two or more limbs")
    sensory: int = Field(..., ge=0, le=2, description="8. Sensory: 0=Normal, 1=Mild-moderate sensory loss, 2=Severe or total sensory loss")
    best_language: int = Field(..., ge=0, le=3, description="9. Best Language (Aphasia): 0=No aphasia, 1=Mild-moderate aphasia, 2=Severe aphasia, 3=Mute/global aphasia")
    dysarthria: int = Field(..., ge=0, le=2, description="10. Dysarthria: 0=Normal, 1=Mild-moderate, 2=Severe/anarthria")
    extinction_inattention: int = Field(..., ge=0, le=2, description="11. Extinction/Inattention (Neglect): 0=No abnormality, 1=Inattention to one modality, 2=Profound hemi-inattention")


def calculate_nihss(params: NIHSSParams) -> ClinicalResult:
    """
    Calculates the NIH Stroke Scale (NIHSS) for quantifying neurological deficit in acute stroke.
    Reference: Brott T et al. Stroke. 1989;20(7):864-870.
    """
    score = (
        params.loc + params.loc_questions + params.loc_commands +
        params.best_gaze + params.visual_fields + params.facial_palsy +
        params.left_arm_motor + params.right_arm_motor +
        params.left_leg_motor + params.right_leg_motor +
        params.limb_ataxia + params.sensory +
        params.best_language + params.dysarthria + params.extinction_inattention
    )

    evidence = Evidence(
        source_doi="10.1161/01.STR.20.7.864",
        level="Derivation & Validation Study",
        description="Measurements of acute cerebral infarction: a clinical examination scale (Brott T et al., Stroke 1989)"
    )

    if score == 0:
        severity = "No stroke symptoms"
    elif score <= 4:
        severity = "Minor stroke"
    elif score <= 15:
        severity = "Moderate stroke"
    elif score <= 20:
        severity = "Moderate-to-severe stroke"
    else:
        severity = "Severe stroke"

    interpretation = f"NIHSS score is {score}. Classification: {severity}."

    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="72089-6",
        fhir_system="http://loinc.org",
        fhir_display="NIH Stroke Scale total score"
    )

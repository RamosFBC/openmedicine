from pydantic import BaseModel, Field
from open_medicine.mcp.base import ClinicalResult, Evidence


class CanadianCSpineParams(BaseModel):
    """Parameters to evaluate the Canadian C-Spine Rule for cervical spine imaging."""
    age: int = Field(..., description="Patient age in years")
    dangerous_mechanism: bool = Field(False, description="Dangerous mechanism of injury (fall ≥1m/5 stairs, axial load to head, high-speed MVC, rollover, ejection, motorized recreational vehicle, bicycle collision)")
    paresthesias: bool = Field(False, description="Paresthesias (tingling/numbness) in extremities")
    simple_rear_end_mvc: bool = Field(False, description="Simple rear-end MVC (excludes pushed into oncoming traffic, hit by bus/large truck, rollover, hit by high-speed vehicle)")
    sitting_in_ed: bool = Field(False, description="Patient is sitting position in the emergency department")
    ambulatory: bool = Field(False, description="Patient was ambulatory at any time since injury")
    delayed_onset_pain: bool = Field(False, description="Delayed onset of neck pain (not immediate)")
    no_midline_tenderness: bool = Field(False, description="Absence of midline cervical spine tenderness on palpation")
    can_rotate_neck_45: bool = Field(False, description="Patient is able to actively rotate neck 45° to the left and right")


def calculate_canadian_cspine(params: CanadianCSpineParams) -> ClinicalResult:
    """
    Evaluates the Canadian C-Spine Rule for cervical spine clearance in alert, stable trauma patients.
    Reference: Stiell IG et al. JAMA. 2001;286(15):1841-1848.
    """
    evidence = Evidence(
        source_doi="10.1001/jama.286.15.1841",
        level="Derivation & Validation Study",
        description="Stiell IG et al. The Canadian C-Spine Rule for Radiography in Alert and Stable Trauma Patients. JAMA. 2001;286(15):1841-1848."
    )

    # Step 1: Any high-risk factor mandating imaging?
    high_risk = params.age >= 65 or params.dangerous_mechanism or params.paresthesias
    if high_risk:
        return ClinicalResult(
            value=1.0,
            interpretation="Imaging REQUIRED. High-risk factor present (age ≥65, dangerous mechanism, or paresthesias). C-spine imaging is indicated.",
            evidence=evidence,
            fhir_code="36962-5",
            fhir_system="http://loinc.org",
            fhir_display="Cervical spine X-ray"
        )

    # Step 2: Any low-risk factor allowing safe ROM assessment?
    has_low_risk = (
        params.simple_rear_end_mvc
        or params.sitting_in_ed
        or params.ambulatory
        or params.delayed_onset_pain
        or params.no_midline_tenderness
    )
    if not has_low_risk:
        return ClinicalResult(
            value=1.0,
            interpretation="Imaging REQUIRED. No low-risk factor present to allow safe assessment of range of motion. C-spine imaging is indicated.",
            evidence=evidence,
            fhir_code="36962-5",
            fhir_system="http://loinc.org",
            fhir_display="Cervical spine X-ray"
        )

    # Step 3: Able to actively rotate neck 45°?
    if not params.can_rotate_neck_45:
        return ClinicalResult(
            value=1.0,
            interpretation="Imaging REQUIRED. Patient unable to actively rotate neck 45° left and right. C-spine imaging is indicated.",
            evidence=evidence,
            fhir_code="36962-5",
            fhir_system="http://loinc.org",
            fhir_display="Cervical spine X-ray"
        )

    return ClinicalResult(
        value=0.0,
        interpretation="No imaging required. Patient has no high-risk factors, has low-risk factors allowing ROM assessment, and can actively rotate neck 45°. C-spine can be clinically cleared.",
        evidence=evidence,
        fhir_code="36962-5",
        fhir_system="http://loinc.org",
        fhir_display="Cervical spine X-ray"
    )

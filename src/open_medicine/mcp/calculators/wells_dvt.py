from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class WellsDVTParams(BaseModel):
    """Parameters to calculate the Wells score for DVT probability."""
    active_cancer: bool = Field(False, description="Active cancer (treatment ongoing, within 6 months, or palliative)")
    paralysis_or_casting: bool = Field(False, description="Paralysis, paresis, or recent plaster immobilization of the lower extremities")
    bedridden_or_major_surgery: bool = Field(False, description="Recently bedridden for ≥3 days or major surgery requiring general/regional anesthesia within 12 weeks")
    tenderness_along_deep_veins: bool = Field(False, description="Localized tenderness along the distribution of the deep venous system")
    entire_leg_swollen: bool = Field(False, description="Entire leg swollen")
    calf_swelling_gt_3cm: bool = Field(False, description="Calf swelling >3 cm compared to asymptomatic side (measured 10 cm below tibial tuberosity)")
    pitting_edema: bool = Field(False, description="Pitting edema confined to the symptomatic leg")
    collateral_superficial_veins: bool = Field(False, description="Collateral superficial veins (non-varicose)")
    previously_documented_dvt: bool = Field(False, description="Previously documented DVT")
    alternative_diagnosis_likely: bool = Field(False, description="Alternative diagnosis at least as likely as DVT (-2 points)")


def calculate_wells_dvt(params: WellsDVTParams) -> ClinicalResult:
    """
    Calculates the Wells score for deep vein thrombosis (DVT) probability.
    Reference: Wells PS et al. Lancet. 1997;350(9094):1795-1798.
    """
    score = sum([
        params.active_cancer,
        params.paralysis_or_casting,
        params.bedridden_or_major_surgery,
        params.tenderness_along_deep_veins,
        params.entire_leg_swollen,
        params.calf_swelling_gt_3cm,
        params.pitting_edema,
        params.collateral_superficial_veins,
        params.previously_documented_dvt,
    ])

    if params.alternative_diagnosis_likely:
        score -= 2

    evidence = Evidence(
        source_doi="10.1016/S0140-6736(97)08140-3",
        level="Derivation Study",
        description="Wells PS et al. Value of assessment of pretest probability of deep-vein thrombosis in clinical management. Lancet. 1997;350(9094):1795-1798."
    )

    if score <= 0:
        interpretation = f"Wells DVT score is {score}. Low probability of DVT. Consider D-dimer testing to rule out DVT."
    elif score <= 2:
        interpretation = f"Wells DVT score is {score}. Moderate probability of DVT. Consider D-dimer testing or ultrasound."
    else:
        interpretation = f"Wells DVT score is {score}. High probability of DVT. Ultrasound recommended; consider empiric anticoagulation while awaiting results."

    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        # LOINC approximation: no specific Wells DVT LOINC; using generic DVT risk assessment
        fhir_code="96309-4",
        fhir_system="http://loinc.org",
        fhir_display="Wells DVT score"
    )

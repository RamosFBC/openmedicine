from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class TIMISTEMIParams(BaseModel):
    """Parameters to calculate the TIMI Risk Score for STEMI."""
    age: int = Field(..., description="Age in years")
    diabetes_or_hypertension_or_angina: bool = Field(False, description="History of diabetes, hypertension, or angina")
    systolic_bp_lt_100: bool = Field(False, description="Systolic blood pressure < 100 mmHg")
    heart_rate_gt_100: bool = Field(False, description="Heart rate > 100 bpm")
    killip_class_ii_iv: bool = Field(False, description="Killip class II-IV (signs of heart failure)")
    weight_lt_67kg: bool = Field(False, description="Body weight < 67 kg")
    anterior_st_elevation_or_lbbb: bool = Field(False, description="Anterior ST elevation or left bundle branch block")
    time_to_treatment_gt_4h: bool = Field(False, description="Time to treatment > 4 hours")


def calculate_timi_stemi(params: TIMISTEMIParams) -> ClinicalResult:
    """
    Calculates the TIMI Risk Score for STEMI (30-day mortality prediction).
    Reference: Morrow DA et al. Circulation. 2000.
    """
    score = 0

    # Age: ≥75 = 3pts, 65-74 = 2pts
    if params.age >= 75:
        score += 3
    elif params.age >= 65:
        score += 2

    # DM/HTN/angina
    if params.diabetes_or_hypertension_or_angina:
        score += 1

    # SBP < 100
    if params.systolic_bp_lt_100:
        score += 3

    # HR > 100
    if params.heart_rate_gt_100:
        score += 2

    # Killip II-IV
    if params.killip_class_ii_iv:
        score += 2

    # Weight < 67 kg
    if params.weight_lt_67kg:
        score += 1

    # Anterior ST elevation or LBBB
    if params.anterior_st_elevation_or_lbbb:
        score += 1

    # Time to treatment > 4h
    if params.time_to_treatment_gt_4h:
        score += 1

    evidence = Evidence(
        source_doi="10.1161/01.CIR.102.17.2031",
        level="Derivation & Validation Study",
        description="TIMI risk score for ST-elevation myocardial infarction (Morrow DA et al., Circulation, 2000)"
    )

    # Approximate mortality risk by score (from original paper)
    mortality_estimates = {
        0: "0.8%", 1: "1.6%", 2: "2.2%", 3: "4.4%", 4: "7.3%",
        5: "12.4%", 6: "16.1%", 7: "23.4%", 8: "26.8%"
    }
    mort = mortality_estimates.get(score, ">30%")

    interpretation = (
        f"TIMI STEMI Risk Score is {score}/14. "
        f"Estimated 30-day mortality: {mort}. "
        f"Higher scores indicate greater mortality risk and may warrant more aggressive intervention."
    )

    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="96574-7",  # LOINC approximation: Acute cardiac risk assessment panel
        fhir_system="http://loinc.org",
        fhir_display="TIMI risk score for STEMI"
    )

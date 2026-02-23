from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class PERCParams(BaseModel):
    """Parameters for the PERC (Pulmonary Embolism Rule-out Criteria) rule.
    Each field represents whether the criterion is MET (positive/abnormal).
    All criteria must be NEGATIVE (False) to rule out PE."""
    age_gte_50: bool = Field(False, description="Age ≥ 50 years")
    heart_rate_gte_100: bool = Field(False, description="Heart rate ≥ 100 bpm")
    spo2_lt_95: bool = Field(False, description="SpO2 < 95% on room air")
    unilateral_leg_swelling: bool = Field(False, description="Unilateral leg swelling")
    hemoptysis: bool = Field(False, description="Hemoptysis")
    recent_surgery_or_trauma: bool = Field(False, description="Recent surgery or trauma (within 4 weeks)")
    prior_dvt_pe: bool = Field(False, description="Prior DVT or PE")
    estrogen_use: bool = Field(False, description="Hormone estrogen use (oral contraceptives, HRT, etc.)")


def calculate_perc(params: PERCParams) -> ClinicalResult:
    """
    Applies the PERC rule for pulmonary embolism rule-out.
    All 8 criteria must be negative (absent) to safely rule out PE without further testing.
    Reference: Kline JA et al. J Thromb Haemost. 2004;2(8):1247-1255.
    """
    criteria_positive = sum([
        params.age_gte_50,
        params.heart_rate_gte_100,
        params.spo2_lt_95,
        params.unilateral_leg_swelling,
        params.hemoptysis,
        params.recent_surgery_or_trauma,
        params.prior_dvt_pe,
        params.estrogen_use,
    ])

    evidence = Evidence(
        source_doi="10.1111/j.1538-7836.2004.00985.x",
        level="Derivation & Validation Study",
        description="Prospective multicenter evaluation of the pulmonary embolism rule-out criteria. Kline JA et al. J Thromb Haemost. 2004."
    )

    if criteria_positive == 0:
        interpretation = "PERC rule: All 8 criteria are negative. PE can be ruled out without further workup in low-risk patients."
    else:
        interpretation = f"PERC rule: {criteria_positive} of 8 criteria positive. PE cannot be ruled out by PERC. Further diagnostic testing (D-dimer, CTPA) is indicated."

    return ClinicalResult(
        value=criteria_positive,
        interpretation=interpretation,
        evidence=evidence,
        # LOINC approximation: no specific PERC LOINC code
        fhir_code="96307-8",
        fhir_system="http://loinc.org",
        fhir_display="PERC rule score"
    )

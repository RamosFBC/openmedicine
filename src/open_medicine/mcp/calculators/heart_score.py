from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence

# Related guidelines: aha_acc_chest_pain_2021 (risk_stratification, acute_management sections)


class HEARTScoreParams(BaseModel):
    """Parameters to calculate the HEART Score for chest pain evaluation."""
    history: int = Field(..., ge=0, le=2, description="History score: 0 = slightly suspicious, 1 = moderately suspicious, 2 = highly suspicious")
    ecg: int = Field(..., ge=0, le=2, description="ECG score: 0 = normal, 1 = non-specific repolarization disturbance, 2 = significant ST deviation")
    age: int = Field(..., description="Age in years")
    risk_factor_count: int = Field(0, ge=0, description="Number of risk factors (HTN, DM, smoking, obesity BMI>30, family hx CAD, hypercholesterolemia)")
    history_of_atherosclerosis: bool = Field(False, description="History of atherosclerotic disease (prior PCI/CABG, stroke/TIA, peripheral arterial disease)")
    troponin: int = Field(..., ge=0, le=2, description="Troponin score: 0 = ≤normal limit, 1 = 1-3x normal limit, 2 = >3x normal limit")


def calculate_heart_score(params: HEARTScoreParams) -> ClinicalResult:
    """
    Calculates the HEART Score for major adverse cardiac events (MACE) risk in chest pain patients.
    Reference: Six AJ et al. Neth Heart J. 2008.
    """
    score = 0

    # History
    score += params.history

    # ECG
    score += params.ecg

    # Age
    if params.age >= 65:
        score += 2
    elif params.age >= 45:
        score += 1
    # <45 = 0

    # Risk factors
    if params.history_of_atherosclerosis or params.risk_factor_count >= 3:
        score += 2
    elif params.risk_factor_count >= 1:
        score += 1
    # 0 risk factors = 0

    # Troponin
    score += params.troponin

    evidence = Evidence(
        source_doi="10.1007/BF03086144",
        level="Derivation & Validation Study",
        description="A rapid initial observation based on HEART score (Six AJ et al., Neth Heart J, 2008)"
    )

    if score <= 3:
        interpretation = (
            f"HEART Score is {score}. Low risk (0-3): 1.7% risk of MACE at 6 weeks. "
            "Consider early discharge with outpatient follow-up."
        )
    elif score <= 6:
        interpretation = (
            f"HEART Score is {score}. Moderate risk (4-6): 16.6% risk of MACE at 6 weeks. "
            "Consider admission for observation and further workup."
        )
    else:
        interpretation = (
            f"HEART Score is {score}. High risk (7-10): 50.7% risk of MACE at 6 weeks. "
            "Early invasive strategy recommended."
        )

    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        # No exact LOINC for HEART score; using approximation
        fhir_code="96574-7",  # LOINC approximation: Acute cardiac risk assessment panel
        fhir_system="http://loinc.org",
        fhir_display="HEART score"
    )

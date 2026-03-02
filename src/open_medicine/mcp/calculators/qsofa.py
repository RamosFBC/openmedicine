from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence

# Related guidelines: sepsis3_2016 (qsofa_screening section), ssc_sepsis_2021 (screening_and_early_management section)

class QSOFAParams(BaseModel):
    """Parameters to calculate the qSOFA (Quick SOFA) score."""
    respiratory_rate: int = Field(..., description="Respiratory rate in breaths per minute")
    systolic_blood_pressure: int = Field(..., description="Systolic blood pressure in mmHg")
    altered_mentation: bool = Field(..., description="Altered mentation (GCS < 15)")


def calculate_qsofa(params: QSOFAParams) -> ClinicalResult:
    """
    Calculates the Quick Sequential Organ Failure Assessment (qSOFA) score.
    Bedside screening tool for sepsis-related poor outcomes.
    Reference: Seymour CW et al. JAMA. 2016.
    """
    score = 0
    if params.respiratory_rate >= 22:
        score += 1
    if params.systolic_blood_pressure <= 100:
        score += 1
    if params.altered_mentation:
        score += 1

    evidence = Evidence(
        source_doi="10.1001/jama.2016.0288",
        level="Derivation & Validation Study",
        description="Assessment of clinical criteria for sepsis (Sepsis-3). Seymour CW et al. JAMA 2016."
    )

    if score <= 1:
        interpretation = (
            f"qSOFA score is {score}. Low risk. "
            f"Not suggestive of high risk for in-hospital mortality from sepsis. "
            f"Continue clinical monitoring as appropriate."
        )
    else:
        interpretation = (
            f"qSOFA score is {score}. High risk. "
            f"Score ≥2 suggests high risk of poor outcome in patients with suspected infection. "
            f"Prompt further assessment for organ dysfunction and consider ICU-level care."
        )

    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="96792-0",
        fhir_system="http://loinc.org",
        fhir_display="qSOFA (Quick Sequential Organ Failure Assessment) score"
    )

from pydantic import BaseModel, Field
from open_medicine.mcp.base import ClinicalResult, Evidence


class PaduaParams(BaseModel):
    """Parameters for the Padua VTE Prediction Score for medical patients."""
    # 3-point factors
    active_cancer: bool = Field(False, description="Active cancer (local or distant metastases and/or chemotherapy or radiotherapy in the previous 6 months)")
    previous_vte: bool = Field(False, description="Previous VTE (excluding superficial vein thrombosis)")
    reduced_mobility: bool = Field(False, description="Reduced mobility (anticipated bed rest with bathroom privileges for at least 3 days)")
    known_thrombophilia: bool = Field(False, description="Known thrombophilic condition (antithrombin, protein C or S deficiency, Factor V Leiden, prothrombin G20210A mutation, antiphospholipid syndrome)")

    # 2-point factors
    recent_trauma_or_surgery: bool = Field(False, description="Recent (≤ 1 month) trauma and/or surgery")

    # 1-point factors
    age_70_or_older: bool = Field(False, description="Age ≥ 70 years")
    heart_or_respiratory_failure: bool = Field(False, description="Heart and/or respiratory failure")
    acute_mi_or_stroke: bool = Field(False, description="Acute MI and/or ischemic stroke")
    acute_infection_or_rheumatic: bool = Field(False, description="Acute infection and/or rheumatologic disorder")
    obesity: bool = Field(False, description="Obesity (BMI ≥ 30 kg/m²)")
    ongoing_hormonal_treatment: bool = Field(False, description="Ongoing hormonal treatment")


def calculate_padua(params: PaduaParams) -> ClinicalResult:
    """
    Calculates the Padua Prediction Score for VTE risk in hospitalized medical patients.
    Reference: Barbar S et al. J Thromb Haemost. 2010;8(11):2450-2457.
    """
    score = (
        3 * sum([
            params.active_cancer,
            params.previous_vte,
            params.reduced_mobility,
            params.known_thrombophilia,
        ])
        + 2 * params.recent_trauma_or_surgery
        + sum([
            params.age_70_or_older,
            params.heart_or_respiratory_failure,
            params.acute_mi_or_stroke,
            params.acute_infection_or_rheumatic,
            params.obesity,
            params.ongoing_hormonal_treatment,
        ])
    )

    evidence = Evidence(
        source_doi="10.1111/j.1538-7836.2010.04044.x",
        level="Derivation & Validation Study",
        description="A risk assessment model for the identification of hospitalized medical patients at risk for venous thromboembolism: the Padua Prediction Score. Barbar S et al. J Thromb Haemost. 2010."
    )

    if score < 4:
        interpretation = f"Padua score is {score}. Low VTE risk (< 4). Pharmacological prophylaxis not generally recommended."
    else:
        interpretation = f"Padua score is {score}. High VTE risk (≥ 4). Pharmacological thromboprophylaxis is recommended."

    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="96309-4",  # LOINC approximation: VTE risk assessment
        fhir_system="http://loinc.org",
        fhir_display="Padua VTE prediction score"
    )

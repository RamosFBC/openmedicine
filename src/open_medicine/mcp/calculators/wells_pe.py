from pydantic import BaseModel, Field
from open_medicine.mcp.base import ClinicalResult, Evidence

# Related guidelines: wells_pe_2000 (pre_test_probability, diagnostic_algorithm sections)

class WellsPEParams(BaseModel):
    """Parameters to calculate the Wells score for pulmonary embolism probability."""
    clinical_signs_dvt: bool = Field(False, description="Clinical signs and symptoms of DVT (minimum of leg swelling and pain with palpation of the deep veins) — 3 points")
    pe_most_likely_diagnosis: bool = Field(False, description="PE is the #1 diagnosis, or equally likely — 3 points")
    heart_rate_gt_100: bool = Field(False, description="Heart rate greater than 100 bpm — 1.5 points")
    immobilization_or_surgery: bool = Field(False, description="Immobilization (≥3 days) or surgery in the previous 4 weeks — 1.5 points")
    previous_dvt_pe: bool = Field(False, description="Previous objectively diagnosed DVT or PE — 1.5 points")
    hemoptysis: bool = Field(False, description="Hemoptysis — 1 point")
    malignancy: bool = Field(False, description="Malignancy (on treatment, treated in last 6 months, or palliative) — 1 point")


def calculate_wells_pe(params: WellsPEParams) -> ClinicalResult:
    """
    Calculates the Wells score for pulmonary embolism (simplified two-tier model).
    Reference: Wells PS et al. Thromb Haemost. 2000;83(3):416-420.
    """
    score = 0.0

    if params.clinical_signs_dvt:
        score += 3.0
    if params.pe_most_likely_diagnosis:
        score += 3.0
    if params.heart_rate_gt_100:
        score += 1.5
    if params.immobilization_or_surgery:
        score += 1.5
    if params.previous_dvt_pe:
        score += 1.5
    if params.hemoptysis:
        score += 1.0
    if params.malignancy:
        score += 1.0

    evidence = Evidence(
        source_doi="10.1055/s-0037-1613870",
        level="Validation Study",
        description="Derivation of a simple clinical model to categorize patients' probability of pulmonary embolism. Wells PS et al. Thromb Haemost. 2000."
    )

    if score <= 4.0:
        interpretation = f"Wells PE score is {score}. PE unlikely. Consider D-dimer testing; if negative, PE can be excluded."
    else:
        interpretation = f"Wells PE score is {score}. PE likely. CT pulmonary angiography (CTPA) is recommended."

    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        # LOINC approximation: no specific Wells PE LOINC
        fhir_code="96308-6",
        fhir_system="http://loinc.org",
        fhir_display="Wells PE score"
    )

from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence

# Related guidelines: nice_ugib_2012 (risk_assessment, resuscitation, endoscopic_management sections)

class GlasgowBlatchfordParams(BaseModel):
    """Parameters to calculate the Glasgow-Blatchford Bleeding Score (GBS)."""
    bun: float = Field(..., description="Blood Urea Nitrogen (BUN) in mg/dL")
    hemoglobin: float = Field(..., description="Hemoglobin in g/dL")
    systolic_bp: int = Field(..., description="Systolic blood pressure in mmHg")
    pulse: int = Field(..., description="Heart rate in beats per minute")
    is_male: bool = Field(..., description="Is the patient male?")
    melena: bool = Field(False, description="Presentation with melena (dark/tarry stools)")
    syncope: bool = Field(False, description="Presentation with syncope")
    hepatic_disease: bool = Field(False, description="Known hepatic disease")
    cardiac_failure: bool = Field(False, description="Known cardiac failure")


def calculate_glasgow_blatchford(params: GlasgowBlatchfordParams) -> ClinicalResult:
    """
    Calculates the Glasgow-Blatchford Bleeding Score (GBS) for risk stratification
    in upper gastrointestinal bleeding.

    Reference: Blatchford O et al. Lancet. 2000;356(9238):1318-1321.
    """
    score = 0

    # BUN (mg/dL)
    if params.bun >= 70:
        score += 6
    elif params.bun >= 28:
        score += 4
    elif params.bun >= 22.4:
        score += 3
    elif params.bun >= 18.2:
        score += 2

    # Hemoglobin (g/dL) — sex-specific
    if params.is_male:
        if params.hemoglobin < 10:
            score += 6
        elif params.hemoglobin < 12:
            score += 3
        elif params.hemoglobin < 13:
            score += 1
    else:
        if params.hemoglobin < 10:
            score += 6
        elif params.hemoglobin < 12:
            score += 1

    # Systolic BP (mmHg)
    if params.systolic_bp < 90:
        score += 3
    elif params.systolic_bp < 100:
        score += 2
    elif params.systolic_bp < 110:
        score += 1

    # Pulse >= 100
    if params.pulse >= 100:
        score += 1

    # Other markers (1 point each)
    if params.melena:
        score += 1
    if params.syncope:
        score += 1
    if params.hepatic_disease:
        score += 1
    if params.cardiac_failure:
        score += 1

    evidence = Evidence(
        source_doi="10.1016/S0140-6736(00)02816-6",
        level="Derivation & Validation Study",
        description="A risk score to predict need for treatment for upper-gastrointestinal haemorrhage."
    )

    if score == 0:
        interpretation = f"Glasgow-Blatchford Score is {score}. Very low risk. Consider outpatient management."
    elif score <= 1:
        interpretation = f"Glasgow-Blatchford Score is {score}. Low risk. Consider outpatient management with close follow-up."
    elif score <= 6:
        interpretation = f"Glasgow-Blatchford Score is {score}. Moderate risk. Hospital admission and further evaluation recommended."
    else:
        interpretation = f"Glasgow-Blatchford Score is {score}. High risk (≥7). Urgent intervention likely needed."

    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="LP419518-4",  # LOINC approximation: no specific GBS code exists
        fhir_system="http://loinc.org",
        fhir_display="Glasgow-Blatchford Bleeding Score"
    )

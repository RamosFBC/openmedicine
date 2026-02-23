from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence
from enum import Enum


class WarfarinIndication(str, Enum):
    AF_VTE = "af_vte"
    MECHANICAL_VALVE = "mechanical_valve"


class WarfarinInitiationParams(BaseModel):
    """Parameters to determine Warfarin initial dosing guidance."""
    age: int = Field(..., description="Age in years")
    has_liver_disease: bool = Field(False, description="Presence of liver disease")
    has_heart_failure: bool = Field(False, description="Presence of heart failure")
    is_malnourished: bool = Field(False, description="Patient is malnourished or has poor nutritional status")
    has_drug_interactions: bool = Field(False, description="Concomitant use of drugs that increase warfarin sensitivity (e.g., amiodarone, fluconazole)")
    indication: WarfarinIndication = Field(..., description="Clinical indication: af_vte or mechanical_valve")


def calculate_warfarin_initiation(params: WarfarinInitiationParams) -> ClinicalResult:
    """
    Provides initial Warfarin dosing guidance based on patient risk factors
    and indication-specific INR targets.
    Reference: CHEST 2012 Guidelines (Holbrook et al.).
    """
    age = params.age
    ind = params.indication

    # Determine risk factors for dose reduction
    risk_factors = []
    if age > 60:
        risk_factors.append("age > 60")
    if params.has_liver_disease:
        risk_factors.append("liver disease")
    if params.has_heart_failure:
        risk_factors.append("heart failure")
    if params.is_malnourished:
        risk_factors.append("malnourished")
    if params.has_drug_interactions:
        risk_factors.append("drug interactions")

    # Determine dose
    if len(risk_factors) > 0:
        dose_mg = 2.5
        dose_rationale = f"Lower initial dose due to: {', '.join(risk_factors)}."
    elif age <= 50:
        dose_mg = 7.5
        dose_rationale = "Higher initial dose may be considered for younger patients without risk factors (clinician discretion)."
    else:
        dose_mg = 5.0
        dose_rationale = "Standard initial dose for adults without risk factors."

    # Target INR by indication
    if ind == WarfarinIndication.AF_VTE:
        target_inr = "2.0-3.0"
    else:
        target_inr = "2.5-3.5"

    interpretation = (
        f"Warfarin initiation for a {age}-year-old patient with indication '{ind.value}': "
        f"Recommended starting dose: {dose_mg} mg daily. {dose_rationale} "
        f"Target INR: {target_inr}. Monitor INR frequently during initiation."
    )

    evidence = Evidence(
        source_doi="10.1378/chest.11-2295",
        level="Guideline",
        description="CHEST 2012: Evidence-Based Management of Anticoagulant Therapy (Holbrook et al.)."
    )

    return ClinicalResult(
        value=dose_mg,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="2160-0",  # LOINC approximation: no specific warfarin dose code
        fhir_system="http://loinc.org",
        fhir_display="Warfarin dose"
    )

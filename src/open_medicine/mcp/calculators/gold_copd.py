from typing import Optional
from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class GOLDCOPDParams(BaseModel):
    """Parameters for GOLD 2024 COPD combined assessment."""
    fev1_percent_predicted: float = Field(..., description="FEV1 as percentage of predicted value")
    exacerbations_past_year: int = Field(..., ge=0, description="Number of moderate exacerbations in the past year")
    hospitalizations_past_year: int = Field(..., ge=0, description="Number of exacerbations leading to hospitalization in the past year")
    mmrc_dyspnea: int = Field(..., ge=0, le=4, description="Modified Medical Research Council dyspnea scale (0-4)")
    cat_score: Optional[int] = Field(None, ge=0, le=40, description="COPD Assessment Test score (0-40). If not provided, mMRC is used for symptom assessment.")


def calculate_gold_copd(params: GOLDCOPDParams) -> ClinicalResult:
    """
    Calculates GOLD 2024 COPD combined assessment: spirometric grade + ABE group.
    Reference: Global Initiative for Chronic Obstructive Lung Disease (GOLD) 2024 Report.
    """
    # 1. Spirometric grade based on FEV1 % predicted
    fev1 = params.fev1_percent_predicted
    if fev1 >= 80:
        spirometric_grade = 1
        grade_desc = "GOLD 1 (Mild): FEV1 ≥ 80% predicted"
    elif fev1 >= 50:
        spirometric_grade = 2
        grade_desc = "GOLD 2 (Moderate): 50% ≤ FEV1 < 80% predicted"
    elif fev1 >= 30:
        spirometric_grade = 3
        grade_desc = "GOLD 3 (Severe): 30% ≤ FEV1 < 50% predicted"
    else:
        spirometric_grade = 4
        grade_desc = "GOLD 4 (Very Severe): FEV1 < 30% predicted"

    # 2. Determine symptom burden
    if params.cat_score is not None:
        high_symptoms = params.cat_score >= 10
    else:
        high_symptoms = params.mmrc_dyspnea >= 2

    # 3. Determine ABE group (GOLD 2024)
    exac = params.exacerbations_past_year
    hosp = params.hospitalizations_past_year

    if exac >= 2 or hosp >= 1:
        group = "E"
        group_desc = "Group E: ≥2 moderate exacerbations or ≥1 hospitalization. Pharmacotherapy escalation recommended."
    elif high_symptoms:
        group = "B"
        group_desc = "Group B: Low exacerbation risk with high symptom burden. Bronchodilator therapy recommended."
    else:
        group = "A"
        group_desc = "Group A: Low exacerbation risk with low symptom burden. Bronchodilator as needed."

    evidence = Evidence(
        source_doi="GOLD 2024 Report",
        level="Guideline",
        description="Global Initiative for Chronic Obstructive Lung Disease (GOLD) 2024 Report: Global Strategy for the Diagnosis, Management, and Prevention of COPD."
    )

    interpretation = (
        f"Spirometric classification: {grade_desc}. "
        f"{group_desc}"
    )

    # Encode as spirometric_grade * 10 + group ordinal for a combined numeric value
    group_ordinal = {"A": 1, "B": 2, "E": 3}[group]
    value = spirometric_grade

    return ClinicalResult(
        value=value,
        interpretation=interpretation,
        evidence=evidence,
        # No specific LOINC for GOLD combined assessment
        fhir_code="80382-5",  # LOINC approximation: COPD assessment panel
        fhir_system="http://loinc.org",
        fhir_display="GOLD COPD combined assessment"
    )

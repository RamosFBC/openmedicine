import math
from typing import Optional
from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence

# Related guidelines: none


class CharlsonParams(BaseModel):
    """Parameters to calculate the Charlson Comorbidity Index (CCI).

    Nineteen comorbid conditions are scored with weights of 1, 2, 3, or 6.
    An optional age adjustment adds 1 point per decade over 50 (max 4 points).
    Missing comorbidities are assumed absent (False).
    """

    # --- 1-point conditions ---
    myocardial_infarction: bool = Field(
        False,
        description="History of definite or probable myocardial infarction (ECG and/or enzyme changes)",
    )
    congestive_heart_failure: bool = Field(
        False,
        description="Exertional or paroxysmal nocturnal dyspnea responsive to digitalis, diuretics, or afterload reducing agents",
    )
    peripheral_vascular_disease: bool = Field(
        False,
        description="Intermittent claudication, bypass for arterial insufficiency, gangrene, acute arterial insufficiency, or untreated thoracic/abdominal aneurysm >= 6 cm",
    )
    cerebrovascular_disease: bool = Field(
        False,
        description="History of cerebrovascular accident (CVA) with minor or no residua, or transient ischemic attack (TIA)",
    )
    dementia: bool = Field(
        False,
        description="Chronic cognitive deficit",
    )
    chronic_pulmonary_disease: bool = Field(
        False,
        description="Dyspnea on mild/moderate exertion with or without treatment; or chronic hypoxia, hypercapnia, polycythemia, or pulmonary hypertension (>40 mmHg)",
    )
    connective_tissue_disease: bool = Field(
        False,
        description="Systemic lupus erythematosus, polymyositis, mixed connective tissue disease, polymyalgia rheumatica, or moderate-to-severe rheumatoid arthritis",
    )
    peptic_ulcer_disease: bool = Field(
        False,
        description="Patients who have required treatment for peptic ulcer disease (including bleeding ulcers)",
    )
    mild_liver_disease: bool = Field(
        False,
        description="Chronic hepatitis or cirrhosis without portal hypertension (includes fatty liver, hepatitis carriers, chronic active hepatitis)",
    )
    uncomplicated_diabetes: bool = Field(
        False,
        description="Diabetes treated with insulin or oral hypoglycemics, without end-organ damage",
    )

    # --- 2-point conditions ---
    hemiplegia: bool = Field(
        False,
        description="Hemiplegia or paraplegia",
    )
    moderate_severe_renal_disease: bool = Field(
        False,
        description="Serum creatinine > 3 mg/dL, dialysis, transplantation, or uremic syndrome",
    )
    diabetes_with_end_organ_damage: bool = Field(
        False,
        description="Diabetes mellitus with retinopathy, neuropathy, nephropathy, or poorly controlled glycemia",
    )
    solid_tumor: bool = Field(
        False,
        description="Solid tumor without documented metastases, but initially treated within the last 5 years (excluding non-melanoma skin cancer)",
    )
    leukemia: bool = Field(
        False,
        description="Acute or chronic myelogenous or lymphocytic leukemia",
    )
    lymphoma: bool = Field(
        False,
        description="Lymphomas including Hodgkin disease, lymphosarcoma, Waldenstrom macroglobulinemia, multiple myeloma",
    )

    # --- 3-point condition ---
    moderate_severe_liver_disease: bool = Field(
        False,
        description="Cirrhosis with portal hypertension (with or without variceal bleeding) or hepatic encephalopathy",
    )

    # --- 6-point conditions ---
    metastatic_solid_tumor: bool = Field(
        False,
        description="Metastatic solid tumor",
    )
    aids: bool = Field(
        False,
        description="AIDS (not merely HIV positive without clinical manifestation)",
    )

    # --- Age (optional, for age-adjusted CCI) ---
    age: Optional[int] = Field(
        None,
        description="Age in years (optional). If provided, adds 1 point per decade over age 50, up to a maximum of 4 age points. Omit for the unadjusted CCI.",
    )


def calculate_charlson(params: CharlsonParams) -> ClinicalResult:
    """
    Calculates the Charlson Comorbidity Index (CCI).
    Predicts 10-year mortality based on weighted comorbid conditions.
    Reference: Charlson ME et al. J Chronic Dis. 1987;40(5):373-383.
    """

    # 1. Compute comorbidity score
    score = 0

    # 1-point conditions
    if params.myocardial_infarction:
        score += 1
    if params.congestive_heart_failure:
        score += 1
    if params.peripheral_vascular_disease:
        score += 1
    if params.cerebrovascular_disease:
        score += 1
    if params.dementia:
        score += 1
    if params.chronic_pulmonary_disease:
        score += 1
    if params.connective_tissue_disease:
        score += 1
    if params.peptic_ulcer_disease:
        score += 1
    if params.mild_liver_disease:
        score += 1
    if params.uncomplicated_diabetes:
        score += 1

    # 2-point conditions
    if params.hemiplegia:
        score += 2
    if params.moderate_severe_renal_disease:
        score += 2
    if params.diabetes_with_end_organ_damage:
        score += 2
    if params.solid_tumor:
        score += 2
    if params.leukemia:
        score += 2
    if params.lymphoma:
        score += 2

    # 3-point condition
    if params.moderate_severe_liver_disease:
        score += 3

    # 6-point conditions
    if params.metastatic_solid_tumor:
        score += 6
    if params.aids:
        score += 6

    # Age adjustment (if age provided)
    age_points = 0
    if params.age is not None:
        if params.age >= 80:
            age_points = 4
        elif params.age >= 70:
            age_points = 3
        elif params.age >= 60:
            age_points = 2
        elif params.age >= 50:
            age_points = 1

    total_score = score + age_points

    # 2. Build Evidence
    evidence = Evidence(
        source_doi="10.1016/0021-9681(87)90171-8",
        level="Derivation & Validation Study",
        description="Charlson ME et al. A new method of classifying prognostic comorbidity in longitudinal studies: development and validation. J Chronic Dis. 1987;40(5):373-383.",
    )

    # 3. Compute estimated 10-year survival using the Charlson formula
    # Formula: 10-year survival = 0.983 ^ exp(CCI * 0.9)
    estimated_10yr_survival = round(
        0.983 ** math.exp(total_score * 0.9) * 100, 1
    )

    # 4. Interpret result using validated risk strata
    if params.age is not None:
        score_label = f"Charlson Comorbidity Index (age-adjusted) is {total_score} (comorbidity score {score}, age points {age_points})"
    else:
        score_label = f"Charlson Comorbidity Index is {total_score}"

    if total_score == 0:
        interpretation = (
            f"{score_label}. No comorbidity burden. "
            f"Estimated 10-year survival: {estimated_10yr_survival}%. "
            f"Low predicted mortality risk."
        )
    elif total_score <= 2:
        interpretation = (
            f"{score_label}. Low comorbidity burden. "
            f"Estimated 10-year survival: {estimated_10yr_survival}%. "
            f"Consider comorbidity impact on treatment planning."
        )
    elif total_score <= 4:
        interpretation = (
            f"{score_label}. Moderate comorbidity burden. "
            f"Estimated 10-year survival: {estimated_10yr_survival}%. "
            f"Comorbidity may significantly affect prognosis and treatment decisions."
        )
    else:
        interpretation = (
            f"{score_label}. High comorbidity burden. "
            f"Estimated 10-year survival: {estimated_10yr_survival}%. "
            f"Comorbidities are likely to substantially impact prognosis. Consider goals of care discussion."
        )

    # 5. Return ClinicalResult with FHIR metadata
    # No LOINC observation code exists for the Charlson Comorbidity Index score.
    # LOINC 75618-9 "Comorbid condition" was previously used but represents
    # individual comorbid conditions (input data), not a composite comorbidity
    # index (output concept). Setting to None until a proper LOINC observation
    # code is registered for the CCI.
    return ClinicalResult(
        value=total_score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code=None,
        fhir_system=None,
        fhir_display="Charlson Comorbidity Index",
    )

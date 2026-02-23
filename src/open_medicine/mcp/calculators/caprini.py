from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class CapriniParams(BaseModel):
    """Parameters for the Caprini VTE Risk Assessment Score."""
    # 1-point factors
    age_41_60: bool = Field(False, description="Age 41-60 years")
    minor_surgery: bool = Field(False, description="Minor surgery planned")
    bmi_over_25: bool = Field(False, description="BMI > 25 kg/m²")
    swollen_legs: bool = Field(False, description="Swollen legs (current)")
    varicose_veins: bool = Field(False, description="Varicose veins")
    pregnancy_or_postpartum: bool = Field(False, description="Pregnancy or postpartum (<1 month)")
    history_unexplained_stillborn_or_recurrent_abortion: bool = Field(False, description="History of unexplained stillborn infant, recurrent spontaneous abortion (≥3), or premature birth with toxemia or growth-restricted infant")
    ocp_or_hrt: bool = Field(False, description="Oral contraceptives or hormone replacement therapy")
    sepsis: bool = Field(False, description="Sepsis (< 1 month)")
    serious_lung_disease: bool = Field(False, description="Serious lung disease including pneumonia (< 1 month)")
    abnormal_pulmonary_function: bool = Field(False, description="Abnormal pulmonary function (COPD)")
    acute_mi: bool = Field(False, description="Acute myocardial infarction")
    chf: bool = Field(False, description="Congestive heart failure (< 1 month)")
    inflammatory_bowel_disease: bool = Field(False, description="History of inflammatory bowel disease")
    medical_patient_at_bed_rest: bool = Field(False, description="Medical patient currently at bed rest")

    # 2-point factors
    age_61_74: bool = Field(False, description="Age 61-74 years")
    arthroscopic_surgery: bool = Field(False, description="Arthroscopic surgery")
    major_open_surgery: bool = Field(False, description="Major open surgery (> 45 minutes)")
    laparoscopic_surgery: bool = Field(False, description="Laparoscopic surgery (> 45 minutes)")
    malignancy: bool = Field(False, description="Malignancy (present or previous)")
    confined_to_bed: bool = Field(False, description="Confined to bed > 72 hours")
    immobilizing_plaster_cast: bool = Field(False, description="Immobilizing plaster cast (< 1 month)")
    central_venous_access: bool = Field(False, description="Central venous access")

    # 3-point factors
    age_75_or_older: bool = Field(False, description="Age ≥ 75 years")
    history_dvt_pe: bool = Field(False, description="History of DVT/PE")
    family_history_thrombosis: bool = Field(False, description="Family history of thrombosis")
    factor_v_leiden: bool = Field(False, description="Factor V Leiden positive")
    prothrombin_20210a: bool = Field(False, description="Prothrombin 20210A positive")
    lupus_anticoagulant: bool = Field(False, description="Lupus anticoagulant positive")
    anticardiolipin_antibodies: bool = Field(False, description="Anticardiolipin antibodies elevated")
    elevated_homocysteine: bool = Field(False, description="Elevated serum homocysteine")
    hit: bool = Field(False, description="Heparin-induced thrombocytopenia (HIT)")
    other_thrombophilia: bool = Field(False, description="Other congenital or acquired thrombophilia")

    # 5-point factors
    stroke: bool = Field(False, description="Stroke (< 1 month)")
    multiple_trauma: bool = Field(False, description="Multiple trauma (< 1 month)")
    acute_spinal_cord_injury: bool = Field(False, description="Acute spinal cord injury/paralysis (< 1 month)")
    major_lower_extremity_arthroplasty: bool = Field(False, description="Elective major lower extremity arthroplasty")


def calculate_caprini(params: CapriniParams) -> ClinicalResult:
    """
    Calculates the Caprini VTE Risk Assessment Score for surgical patients.
    Reference: Caprini JA. Dis Mon. 2005;51(2-3):70-78.
    """
    # 1-point items
    score = sum([
        params.age_41_60,
        params.minor_surgery,
        params.bmi_over_25,
        params.swollen_legs,
        params.varicose_veins,
        params.pregnancy_or_postpartum,
        params.history_unexplained_stillborn_or_recurrent_abortion,
        params.ocp_or_hrt,
        params.sepsis,
        params.serious_lung_disease,
        params.abnormal_pulmonary_function,
        params.acute_mi,
        params.chf,
        params.inflammatory_bowel_disease,
        params.medical_patient_at_bed_rest,
    ])

    # 2-point items
    score += 2 * sum([
        params.age_61_74,
        params.arthroscopic_surgery,
        params.major_open_surgery,
        params.laparoscopic_surgery,
        params.malignancy,
        params.confined_to_bed,
        params.immobilizing_plaster_cast,
        params.central_venous_access,
    ])

    # 3-point items
    score += 3 * sum([
        params.age_75_or_older,
        params.history_dvt_pe,
        params.family_history_thrombosis,
        params.factor_v_leiden,
        params.prothrombin_20210a,
        params.lupus_anticoagulant,
        params.anticardiolipin_antibodies,
        params.elevated_homocysteine,
        params.hit,
        params.other_thrombophilia,
    ])

    # 5-point items
    score += 5 * sum([
        params.stroke,
        params.multiple_trauma,
        params.acute_spinal_cord_injury,
        params.major_lower_extremity_arthroplasty,
    ])

    evidence = Evidence(
        source_doi="10.1016/j.disamonth.2005.02.002",
        level="Validation Study",
        description="Thrombosis risk assessment as a guide to quality patient care. Caprini JA. Dis Mon. 2005."
    )

    if score == 0:
        interpretation = f"Caprini score is {score}. Lowest VTE risk. Early ambulation recommended."
    elif score <= 2:
        interpretation = f"Caprini score is {score}. Low VTE risk. Consider intermittent pneumatic compression (IPC)."
    elif score <= 4:
        interpretation = f"Caprini score is {score}. Moderate VTE risk. Pharmacological prophylaxis and/or IPC recommended."
    else:
        interpretation = f"Caprini score is {score}. High VTE risk (≥5). Pharmacological prophylaxis plus IPC recommended; consider extended prophylaxis."

    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="96309-4",  # LOINC approximation: VTE risk assessment
        fhir_system="http://loinc.org",
        fhir_display="Caprini VTE risk score"
    )

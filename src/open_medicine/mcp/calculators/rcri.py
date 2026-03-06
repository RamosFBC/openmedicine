# Related guidelines: acc_aha_perioperative_2014 (risk_assessment, stepwise_cardiac_assessment sections)

from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class RCRIParams(BaseModel):
    """Parameters to calculate the Revised Cardiac Risk Index (RCRI / Lee Index)."""

    high_risk_surgery: bool = Field(
        False,
        description=(
            "High-risk surgical procedure: intraperitoneal, intrathoracic, "
            "or suprainguinal vascular surgery"
        ),
    )
    history_of_ischemic_heart_disease: bool = Field(
        False,
        description=(
            "History of ischemic heart disease: history of myocardial infarction, "
            "positive exercise test, current chest pain considered due to myocardial "
            "ischemia, use of nitrate therapy, or ECG with pathological Q waves"
        ),
    )
    history_of_congestive_heart_failure: bool = Field(
        False,
        description=(
            "History of congestive heart failure: history of pulmonary edema, "
            "bilateral rales or S3 gallop, paroxysmal nocturnal dyspnea, or "
            "chest radiograph showing pulmonary vascular redistribution"
        ),
    )
    history_of_cerebrovascular_disease: bool = Field(
        False,
        description="History of cerebrovascular disease: prior transient ischemic attack (TIA) or stroke",
    )
    preoperative_insulin_treatment: bool = Field(
        False,
        description="Diabetes mellitus requiring preoperative insulin treatment",
    )
    preoperative_creatinine_above_2: bool = Field(
        False,
        description="Preoperative serum creatinine >2.0 mg/dL (>176.8 micromol/L)",
    )


def calculate_rcri(params: RCRIParams) -> ClinicalResult:
    """
    Calculates the Revised Cardiac Risk Index (RCRI / Lee Index).
    Estimates risk of major cardiac complications after noncardiac surgery.
    Reference: Lee TH et al. Circulation. 1999;100(10):1043-1049.
    """
    # 1. Compute score: 1 point per criterion present
    score = sum([
        params.high_risk_surgery,
        params.history_of_ischemic_heart_disease,
        params.history_of_congestive_heart_failure,
        params.history_of_cerebrovascular_disease,
        params.preoperative_insulin_treatment,
        params.preoperative_creatinine_above_2,
    ])

    # 2. Build Evidence with DOI from original derivation & validation study
    evidence = Evidence(
        source_doi="10.1161/01.CIR.100.10.1043",
        level="Derivation & Validation Study",
        description=(
            "Lee TH et al. Derivation and prospective validation of a simple index "
            "for prediction of cardiac risk of major noncardiac surgery. "
            "Circulation. 1999;100(10):1043-1049."
        ),
    )

    # 3. Interpret result using validated risk strata from the original paper
    #    Risk classes (I-IV) correspond to 0, 1, 2, >=3 predictors
    #    Estimated major cardiac event rates from the Lee 1999 validation cohort
    #    (n=1,422): 0.4%, 0.9%, 6.6%, 11% respectively.
    #    Note: derivation cohort rates were 0.5%, 1.3%, 4%, 9%.
    if score == 0:
        interpretation = (
            f"RCRI score is {score} (Class I). "
            "Estimated risk of major cardiac events: 0.4% (validation cohort). "
            "Low risk. Standard perioperative management is appropriate."
        )
    elif score == 1:
        interpretation = (
            f"RCRI score is {score} (Class II). "
            "Estimated risk of major cardiac events: 0.9% (validation cohort). "
            "Low risk. Proceed with surgery with standard monitoring."
        )
    elif score == 2:
        interpretation = (
            f"RCRI score is {score} (Class III). "
            "Estimated risk of major cardiac events: 6.6% (validation cohort). "
            "Elevated risk. Consider further evaluation based on functional capacity "
            "and surgery-specific risk per ACC/AHA perioperative guidelines."
        )
    else:  # score >= 3
        interpretation = (
            f"RCRI score is {score} (Class IV). "
            "Estimated risk of major cardiac events: 11% (validation cohort). "
            "Elevated risk. Further cardiac evaluation recommended; consider "
            "pharmacologic stress testing if functional capacity is poor or unknown, "
            "per ACC/AHA perioperative guidelines."
        )

    # 4. Return ClinicalResult with FHIR metadata
    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        # No LOINC code exists for the Revised Cardiac Risk Index (RCRI).
        # Code 96574-7 was previously used but is not a valid LOINC code.
        # The nearest code 96574-9 is for the LACE index (readmission risk),
        # which is a different tool. Setting to None until a proper LOINC
        # observation code is registered for the RCRI.
        fhir_code=None,
        fhir_system=None,
        fhir_display="Revised Cardiac Risk Index",
    )

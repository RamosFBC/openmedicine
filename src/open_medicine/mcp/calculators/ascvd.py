import math
from typing import Literal
from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence

# Related guidelines: acc_aha_ascvd_2013 (risk_assessment, interpretation sections)

class ASCVDParams(BaseModel):
    """Parameters to calculate the ASCVD 10-year risk score."""
    is_male: bool = Field(..., description="Is the patient male?")
    is_black: bool = Field(..., description="Is the patient African American/Black?")
    smoker: bool = Field(..., description="Is the patient a current smoker?")
    hypertensive: bool = Field(..., description="Is the patient on treatment for hypertension?")
    diabetic: bool = Field(..., description="Does the patient have diabetes?")
    age: int = Field(..., description="Age in years (40-79)")
    systolic_blood_pressure: int = Field(..., description="Systolic blood pressure in mmHg")
    total_cholesterol: int = Field(..., description="Total cholesterol in mg/dL")
    hdl_cholesterol: int = Field(..., description="HDL cholesterol in mg/dL")

def calculate_ascvd(params: ASCVDParams) -> ClinicalResult:
    """
    Calculates the 10-year ASCVD (Atherosclerotic Cardiovascular Disease) risk
    using the 2013 ACC/AHA Pooled Cohort Equations.
    Returns a ClinicalResult with interpretation and evidence.
    """
    if params.age < 40 or params.age > 79:
        return ClinicalResult(
            value=None,
            interpretation="ASCVD risk score is only validated for ages 40 through 79.",
            evidence=Evidence(
                 source_doi="10.1161/01.cir.0000437741.48606.98",
                 level="Guideline",
                 description="2013 ACC/AHA Guideline on the Assessment of Cardiovascular Risk"
            ),
            fhir_code="79423-0",
            fhir_system="http://loinc.org",
            fhir_display="Cardiovascular disease 10Y risk [Type]" # Close LOINC approximation
        )

    ln_age = math.log(params.age)
    ln_total_chol = math.log(params.total_cholesterol)
    ln_hdl = math.log(params.hdl_cholesterol)
    
    tr_ln_sbp = math.log(params.systolic_blood_pressure) if params.hypertensive else 0
    nt_ln_sbp = 0 if params.hypertensive else math.log(params.systolic_blood_pressure)
    
    age_total_chol = ln_age * ln_total_chol
    age_hdl = ln_age * ln_hdl
    age_tr_sbp = ln_age * tr_ln_sbp
    age_nt_sbp = ln_age * nt_ln_sbp
    age_smoke = ln_age if params.smoker else 0

    if params.is_black and not params.is_male:
        # African American Female
        s010_ret = 0.95334
        mnxb_ret = 86.6081
        predict_ret = (
            17.1141 * ln_age
            + 0.9396 * ln_total_chol
            + -18.9196 * ln_hdl
            + 4.4748 * age_hdl
            + 29.2907 * tr_ln_sbp
            + -6.4321 * age_tr_sbp
            + 27.8197 * nt_ln_sbp
            + -6.0873 * age_nt_sbp
            + (0.6908 if params.smoker else 0)
            + (0.8738 if params.diabetic else 0)
        )
    elif not params.is_black and not params.is_male:
        # White / Other Female
        s010_ret = 0.96652
        mnxb_ret = -29.1817
        predict_ret = (
            -29.799 * ln_age
            + 4.884 * (ln_age ** 2)
            + 13.54 * ln_total_chol
            + -3.114 * age_total_chol
            + -13.578 * ln_hdl
            + 3.149 * age_hdl
            + 2.019 * tr_ln_sbp
            + 1.957 * nt_ln_sbp
            + (7.574 if params.smoker else 0)
            + -1.665 * age_smoke
            + (0.661 if params.diabetic else 0)
        )
    elif params.is_black and params.is_male:
        # African American Male
        s010_ret = 0.89536
        mnxb_ret = 19.5425
        predict_ret = (
            2.469 * ln_age
            + 0.302 * ln_total_chol
            + -0.307 * ln_hdl
            + 1.916 * tr_ln_sbp
            + 1.809 * nt_ln_sbp
            + (0.549 if params.smoker else 0)
            + (0.645 if params.diabetic else 0)
        )
    else:
        # White / Other Male
        s010_ret = 0.91436
        mnxb_ret = 61.1816
        predict_ret = (
            12.344 * ln_age
            + 11.853 * ln_total_chol
            + -2.664 * age_total_chol
            + -7.99 * ln_hdl
            + 1.769 * age_hdl
            + 1.797 * tr_ln_sbp
            + 1.764 * nt_ln_sbp
            + (7.837 if params.smoker else 0)
            + -1.795 * age_smoke
            + (0.658 if params.diabetic else 0)
        )

    # Calculate actual percentage
    pct = 1 - (s010_ret ** math.exp(predict_ret - mnxb_ret))
    risk_percentage = round(pct * 100 * 10) / 10

    # PMC8943256 threshold interpretation
    if risk_percentage < 5.0:
        interpretation = f"The patient has an estimated 10-year ASCVD risk of {risk_percentage}%, which is considered Low Risk. Emphasize lifestyle optimization."
    elif risk_percentage < 7.5:
        interpretation = f"The patient has an estimated 10-year ASCVD risk of {risk_percentage}%, which is considered Borderline Risk. Consider primary prevention strategies."
    elif risk_percentage < 20.0:
        interpretation = f"The patient has an estimated 10-year ASCVD risk of {risk_percentage}%, which is considered Intermediate Risk. Statin therapy consideration is indicated."
    else:
        interpretation = f"The patient has an estimated 10-year ASCVD risk of {risk_percentage}%, which is considered High Risk. Statin therapy is definitely recommended."

    evidence = Evidence(
        source_doi="10.1016/j.ajpc.2021.100335",
        level="Guideline / Algorithm",
        description="Atherosclerotic cardiovascular disease risk assessment: An American Society for Preventive Cardiology clinical practice statement (2013 ACC/AHA Pooled Cohort Equations)"
    )

    return ClinicalResult(
        value=risk_percentage,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="79423-0",
        fhir_system="http://loinc.org",
        fhir_display="Cardiovascular disease 10Y risk [Type]"
    )

import math
from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence

# Related guidelines: acc_aha_cholesterol_2018 (cardiovascular risk assessment and statin therapy)


class FraminghamParams(BaseModel):
    """Parameters to calculate the Framingham Risk Score (2008 General CVD 10-year risk)."""

    is_female: bool = Field(
        ...,
        description="Is the patient female? True for female, False for male.",
    )
    age: int = Field(
        ...,
        description="Age in years. The score is validated for ages 30-74.",
    )
    total_cholesterol: int = Field(
        ...,
        description="Total cholesterol in mg/dL.",
    )
    hdl_cholesterol: int = Field(
        ...,
        description="HDL cholesterol in mg/dL.",
    )
    systolic_blood_pressure: int = Field(
        ...,
        description="Systolic blood pressure in mmHg.",
    )
    is_treated_for_hypertension: bool = Field(
        ...,
        description="Is the patient currently on treatment for hypertension?",
    )
    is_smoker: bool = Field(
        ...,
        description="Is the patient a current smoker?",
    )


def calculate_framingham(params: FraminghamParams) -> ClinicalResult:
    """
    Calculates the Framingham Risk Score for 10-year general cardiovascular
    disease (CVD) risk using the 2008 D'Agostino et al. model.

    Predicts 10-year risk of first CVD event including coronary death,
    myocardial infarction, coronary insufficiency, angina, ischemic stroke,
    hemorrhagic stroke, TIA, peripheral artery disease, and heart failure.

    Reference: D'Agostino RB et al. Circulation. 2008;117(6):743-753.
    """
    evidence = Evidence(
        source_doi="10.1161/CIRCULATIONAHA.107.699579",
        level="Derivation & Validation Study",
        description=(
            "D'Agostino RB et al. General cardiovascular risk profile for use "
            "in primary care: the Framingham Heart Study. "
            "Circulation. 2008;117(6):743-753."
        ),
    )

    # Validate age range (score only validated 30-74)
    if params.age < 30 or params.age > 74:
        return ClinicalResult(
            value=None,
            interpretation=(
                "Framingham Risk Score is only validated for ages 30 through 74. "
                f"Patient age {params.age} is outside this range."
            ),
            evidence=evidence,
            fhir_code="65853-4",
            fhir_system="http://loinc.org",
            fhir_display="General cardiovascular disease 10Y risk [#] Framingham.D'Agostino",
        )

    # Log-transform continuous inputs
    ln_age = math.log(params.age)
    ln_total_chol = math.log(params.total_cholesterol)
    ln_hdl = math.log(params.hdl_cholesterol)
    ln_sbp = math.log(params.systolic_blood_pressure)

    if params.is_female:
        # Female coefficients from D'Agostino et al. 2008, Table 4
        # (model without diabetes, as used by Medscape/QxMD/standard implementations)
        beta_age = 2.32888
        beta_tc = 1.20904
        beta_hdl = -0.70833
        beta_sbp_treated = 2.82263
        beta_sbp_untreated = 2.76157
        beta_smoking = 0.52873
        mean_beta_x = 26.1931
        baseline_survival = 0.95012
    else:
        # Male coefficients from D'Agostino et al. 2008, Table 4
        beta_age = 3.06117
        beta_tc = 1.12370
        beta_hdl = -0.93263
        beta_sbp_treated = 1.99881
        beta_sbp_untreated = 1.93303
        beta_smoking = 0.65451
        mean_beta_x = 23.9802
        baseline_survival = 0.88936

    # Select SBP coefficient based on treatment status
    beta_sbp = beta_sbp_treated if params.is_treated_for_hypertension else beta_sbp_untreated

    # Calculate individual sum of beta * X
    individual_sum = (
        beta_age * ln_age
        + beta_tc * ln_total_chol
        + beta_hdl * ln_hdl
        + beta_sbp * ln_sbp
        + beta_smoking * (1 if params.is_smoker else 0)
    )

    # Calculate 10-year CVD risk using Cox model
    # Risk = 1 - S0(10)^exp(individual_sum - mean_beta_x)
    exponent = individual_sum - mean_beta_x
    risk = 1.0 - (baseline_survival ** math.exp(exponent))
    risk_percentage = round(risk * 100, 1)

    # Clamp to valid range [0, 100]
    risk_percentage = max(0.0, min(100.0, risk_percentage))

    # Risk interpretation thresholds
    # Per ACC/AHA and standard clinical practice:
    # < 10% = Low risk
    # 10-20% = Intermediate risk
    # > 20% = High risk
    sex_label = "female" if params.is_female else "male"
    if risk_percentage < 10.0:
        interpretation = (
            f"Framingham 10-year CVD risk is {risk_percentage}% "
            f"({sex_label}, age {params.age}). "
            f"Low risk (<10%). "
            f"Emphasize lifestyle modifications including diet, exercise, "
            f"and smoking cessation if applicable."
        )
    elif risk_percentage <= 20.0:
        interpretation = (
            f"Framingham 10-year CVD risk is {risk_percentage}% "
            f"({sex_label}, age {params.age}). "
            f"Intermediate risk (10-20%). "
            f"Consider additional risk assessment and risk factor modification. "
            f"Statin therapy may be considered based on individual risk factors."
        )
    else:
        interpretation = (
            f"Framingham 10-year CVD risk is {risk_percentage}% "
            f"({sex_label}, age {params.age}). "
            f"High risk (>20%). "
            f"Aggressive risk factor modification recommended. "
            f"Statin therapy and intensive lifestyle interventions are indicated."
        )

    return ClinicalResult(
        value=risk_percentage,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="65853-4",
        fhir_system="http://loinc.org",
        fhir_display="General cardiovascular disease 10Y risk [#] Framingham.D'Agostino",
    )

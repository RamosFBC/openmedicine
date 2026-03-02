import math
from typing import Optional
from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence

# Related guidelines: endocrine_osteoporosis_2020 (risk_assessment_and_diagnosis, pharmacotherapy sections)
# NOTE: The exact FRAX algorithm is proprietary. This implementation uses a
# simplified estimation based on published relative risks from the Kanis et al.
# meta-analyses and US (Caucasian) baseline fracture/mortality rates.
# The approach follows the methodology described in:
#   - Kanis et al. Osteoporos Int. 2008;19(4):385-397 (FRAX model description)
#   - Kanis et al. Osteoporos Int. 2007;18(8):1033-1046 (clinical risk factors)
#   - Kanis et al. Curr Osteoporos Rep. 2009;7:127-133 (algorithm description)


class FRAXParams(BaseModel):
    """Parameters to calculate the FRAX 10-year fracture risk estimation (US Caucasian model)."""

    age: int = Field(
        ...,
        description="Age in years. FRAX is validated for ages 40-90.",
    )
    is_female: bool = Field(
        ...,
        description="Is the patient female? True for female, False for male.",
    )
    weight_kg: float = Field(
        ...,
        description="Body weight in kilograms.",
    )
    height_cm: float = Field(
        ...,
        description="Height in centimeters.",
    )
    prior_fracture: bool = Field(
        False,
        description=(
            "Previous fragility fracture (including morphometric vertebral fracture). "
            "A prior fracture denotes a fracture occurring spontaneously or from "
            "trauma which, in a healthy individual, would not have resulted in a fracture."
        ),
    )
    parent_hip_fracture: bool = Field(
        False,
        description="History of hip fracture in the patient's mother or father.",
    )
    current_smoking: bool = Field(
        False,
        description="Patient is a current smoker.",
    )
    glucocorticoids: bool = Field(
        False,
        description=(
            "Currently exposed to oral glucocorticoids or has been exposed to "
            "oral glucocorticoids for more than 3 months at a dose equivalent "
            "to prednisolone >=5 mg daily."
        ),
    )
    rheumatoid_arthritis: bool = Field(
        False,
        description="Confirmed diagnosis of rheumatoid arthritis.",
    )
    secondary_osteoporosis: bool = Field(
        False,
        description=(
            "Disorders strongly associated with osteoporosis including type I "
            "(insulin-dependent) diabetes, osteogenesis imperfecta in adults, "
            "untreated long-standing hyperthyroidism, hypogonadism or premature "
            "menopause (<45 years), chronic malnutrition or malabsorption, "
            "and chronic liver disease."
        ),
    )
    alcohol_3_or_more: bool = Field(
        False,
        description="Alcohol intake of 3 or more units per day.",
    )
    femoral_neck_bmd_tscore: Optional[float] = Field(
        None,
        description=(
            "Femoral neck BMD T-score (optional). If not provided, the "
            "calculation is performed without BMD using BMI as a surrogate."
        ),
    )


def calculate_frax(params: FRAXParams) -> ClinicalResult:
    """
    Calculates the estimated FRAX 10-year probability of major osteoporotic
    fracture and hip fracture for US Caucasian population.

    This is a simplified implementation based on published relative risks from
    the Kanis et al. meta-analyses. The original FRAX algorithm is proprietary.
    Results should be considered estimates and verified against the official FRAX
    tool (fraxplus.org) for clinical decision-making.

    Reference: Kanis JA et al. Osteoporos Int. 2008;19(4):385-397.
    """
    evidence = Evidence(
        source_doi="10.1007/s00198-007-0543-5",
        level="Derivation & Validation Study",
        description=(
            "Kanis JA et al. FRAX and the assessment of fracture probability "
            "in men and women from the UK. Osteoporos Int. 2008;19(4):385-397. "
            "Simplified estimation using published relative risks from Kanis meta-analyses."
        ),
    )

    # Validate age range
    if params.age < 40 or params.age > 90:
        return ClinicalResult(
            value=None,
            interpretation=(
                f"FRAX is only validated for ages 40 through 90. "
                f"Patient age {params.age} is outside this range."
            ),
            evidence=evidence,
            fhir_code="90265-0",
            fhir_system="http://loinc.org",
            fhir_display="Major osteoporotic fracture 10-year probability [Likelihood] Fracture Risk Assessment",
        )

    # Validate weight/height
    if params.weight_kg <= 0 or params.height_cm <= 0:
        return ClinicalResult(
            value=None,
            interpretation="Weight and height must be positive values.",
            evidence=evidence,
            fhir_code="90265-0",
            fhir_system="http://loinc.org",
            fhir_display="Major osteoporotic fracture 10-year probability [Likelihood] Fracture Risk Assessment",
        )

    # Calculate BMI
    height_m = params.height_cm / 100.0
    bmi = params.weight_kg / (height_m ** 2)

    # -----------------------------------------------------------------------
    # US Caucasian baseline 10-year fracture probabilities by age and sex
    # WITHOUT any clinical risk factors and at BMI 25 kg/m^2.
    # These values are derived from the Kanis et al. 2008 paper (Tables 2a/2b)
    # and calibrated to US hip fracture incidence (Looker et al. NCHS) and
    # US mortality rates (UN sources).
    #
    # Format: {age: (hip_fracture_%, major_osteoporotic_fracture_%)}
    # Values are interpolated from published FRAX reference tables for the
    # US Caucasian model.
    # -----------------------------------------------------------------------
    _BASELINE_FEMALE = {
        40: (0.1, 2.9),
        45: (0.1, 3.3),
        50: (0.2, 3.5),
        55: (0.3, 4.5),
        60: (0.7, 6.1),
        65: (1.3, 7.6),
        70: (2.3, 10.0),
        75: (4.0, 13.0),
        80: (7.0, 17.0),
        85: (10.0, 20.0),
        90: (12.0, 21.0),
    }

    _BASELINE_MALE = {
        40: (0.1, 2.3),
        45: (0.1, 2.6),
        50: (0.1, 2.7),
        55: (0.2, 3.2),
        60: (0.4, 4.0),
        65: (0.8, 5.2),
        70: (1.3, 6.6),
        75: (2.1, 8.5),
        80: (3.4, 10.0),
        85: (5.0, 11.0),
        90: (6.0, 11.0),
    }

    baseline_table = _BASELINE_FEMALE if params.is_female else _BASELINE_MALE

    # Interpolate baseline probabilities for the patient's exact age
    ages = sorted(baseline_table.keys())
    clamped_age = max(ages[0], min(ages[-1], params.age))

    if clamped_age in baseline_table:
        base_hip, base_mof = baseline_table[clamped_age]
    else:
        # Linear interpolation between bracketing ages
        lower_age = max(a for a in ages if a <= clamped_age)
        upper_age = min(a for a in ages if a >= clamped_age)
        if lower_age == upper_age:
            base_hip, base_mof = baseline_table[lower_age]
        else:
            fraction = (clamped_age - lower_age) / (upper_age - lower_age)
            lh, lm = baseline_table[lower_age]
            uh, um = baseline_table[upper_age]
            base_hip = lh + fraction * (uh - lh)
            base_mof = lm + fraction * (um - lm)

    # -----------------------------------------------------------------------
    # Published relative risks from Kanis meta-analyses
    # These are age-averaged relative risks used in the FRAX model.
    # Sources:
    #   Prior fracture: Kanis et al. Bone. 2004;35(2):375-382
    #   Parental hip fx: Kanis et al. JBMR. 2004;19(10):1672-1680
    #   Smoking: Kanis et al. Osteoporos Int. 2005;16(2):155-162
    #   Glucocorticoids: Kanis et al. JBMR. 2004;19(6):893-899
    #   Rheumatoid arthritis: Kanis et al. Osteoporos Int. 2007;18(8):1033-1046
    #   Alcohol: Kanis et al. Osteoporos Int. 2005;16(7):737-742
    #   BMD per SD: Johnell et al. JBMR. 2005;20(7):1185-1194
    #
    # Two sets: (hip_fracture_RR, major_osteoporotic_fracture_RR)
    # -----------------------------------------------------------------------
    RR_PRIOR_FRACTURE = (1.85, 1.62)
    RR_PARENT_HIP_FRACTURE = (1.49, 1.18)
    RR_SMOKING = (1.84, 1.29)
    RR_GLUCOCORTICOIDS = (2.31, 1.66)
    RR_RHEUMATOID_ARTHRITIS = (1.95, 1.49)
    RR_ALCOHOL_3_PLUS = (1.68, 1.38)

    # BMI adjustment: protective effect of higher BMI on hip fracture.
    # Per the Kanis model, BMI of 25 is the reference point. Each unit of BMI
    # above or below 25 changes the relative risk. The published data shows
    # approximately a 4-fold reduction in hip fracture from BMI 20 to 40
    # (De Laet et al. Osteoporos Int. 2005;16:1330-1338).
    # Log-linear model: RR = exp(-0.069 * (BMI - 25)) for hip fracture
    # For MOF, the effect is smaller: RR = exp(-0.030 * (BMI - 25))
    # These coefficients approximate the published gradient of risk per unit BMI.
    bmi_rr_hip = math.exp(-0.069 * (bmi - 25.0))
    bmi_rr_mof = math.exp(-0.030 * (bmi - 25.0))

    # BMD T-score adjustment (optional)
    # Per Johnell et al. 2005, the gradient of risk (RR per SD decrease in
    # femoral neck BMD) is approximately 2.6 for hip fracture and 1.6 for MOF.
    # When BMD is provided, it replaces the BMI adjustment for fracture risk.
    if params.femoral_neck_bmd_tscore is not None:
        # RR per SD decrease (T-score is negative for low BMD)
        # A T-score of 0 is the reference (young healthy adult mean).
        # Each SD decrease (more negative T-score) increases risk.
        sd_decrease = -params.femoral_neck_bmd_tscore  # positive value = low BMD
        bmd_rr_hip = 2.6 ** sd_decrease if sd_decrease > 0 else 1.0 / (2.6 ** abs(sd_decrease))
        bmd_rr_mof = 1.6 ** sd_decrease if sd_decrease > 0 else 1.0 / (1.6 ** abs(sd_decrease))
        # When BMD is available, replace BMI effect (BMI effect is largely
        # mediated through BMD)
        bmi_rr_hip = 1.0
        bmi_rr_mof = 1.0
    else:
        bmd_rr_hip = 1.0
        bmd_rr_mof = 1.0

    # -----------------------------------------------------------------------
    # Calculate combined relative risk (multiplicative model)
    # -----------------------------------------------------------------------
    combined_rr_hip = bmi_rr_hip * bmd_rr_hip
    combined_rr_mof = bmi_rr_mof * bmd_rr_mof

    if params.prior_fracture:
        combined_rr_hip *= RR_PRIOR_FRACTURE[0]
        combined_rr_mof *= RR_PRIOR_FRACTURE[1]

    if params.parent_hip_fracture:
        combined_rr_hip *= RR_PARENT_HIP_FRACTURE[0]
        combined_rr_mof *= RR_PARENT_HIP_FRACTURE[1]

    if params.current_smoking:
        combined_rr_hip *= RR_SMOKING[0]
        combined_rr_mof *= RR_SMOKING[1]

    if params.glucocorticoids:
        combined_rr_hip *= RR_GLUCOCORTICOIDS[0]
        combined_rr_mof *= RR_GLUCOCORTICOIDS[1]

    if params.rheumatoid_arthritis:
        combined_rr_hip *= RR_RHEUMATOID_ARTHRITIS[0]
        combined_rr_mof *= RR_RHEUMATOID_ARTHRITIS[1]

    # Secondary osteoporosis: only contributes when BMD is not entered.
    # In the FRAX model, secondary osteoporosis has the same weight as
    # rheumatoid arthritis when BMD is not available (Kanis et al. 2008).
    if params.secondary_osteoporosis and params.femoral_neck_bmd_tscore is None:
        combined_rr_hip *= RR_RHEUMATOID_ARTHRITIS[0]
        combined_rr_mof *= RR_RHEUMATOID_ARTHRITIS[1]

    if params.alcohol_3_or_more:
        combined_rr_hip *= RR_ALCOHOL_3_PLUS[0]
        combined_rr_mof *= RR_ALCOHOL_3_PLUS[1]

    # -----------------------------------------------------------------------
    # Apply relative risks to baseline probabilities
    # Convert percentage probabilities to raw probabilities for calculation,
    # then convert back. Use the exponential transform to handle the
    # multiplicative risk model applied to baseline rates:
    #   adjusted_prob = 1 - (1 - baseline_prob)^RR
    # This ensures probabilities remain in [0, 1].
    # -----------------------------------------------------------------------
    base_hip_prob = base_hip / 100.0
    base_mof_prob = base_mof / 100.0

    # Apply RR using the hazard-based approach:
    # If baseline 10-year probability = 1 - S(10) where S is survival,
    # then with RR multiplier: adjusted = 1 - S(10)^RR = 1 - (1-baseline)^RR
    adjusted_hip_prob = 1.0 - (1.0 - base_hip_prob) ** combined_rr_hip
    adjusted_mof_prob = 1.0 - (1.0 - base_mof_prob) ** combined_rr_mof

    # Convert to percentages and round to 1 decimal place
    hip_risk_pct = round(adjusted_hip_prob * 100.0, 1)
    mof_risk_pct = round(adjusted_mof_prob * 100.0, 1)

    # Clamp to valid range
    hip_risk_pct = max(0.0, min(99.9, hip_risk_pct))
    mof_risk_pct = max(0.0, min(99.9, mof_risk_pct))

    # -----------------------------------------------------------------------
    # Interpretation based on NOF/AACE treatment thresholds
    # NOF recommends treatment when:
    #   - Hip fracture probability >= 3%
    #   - Major osteoporotic fracture probability >= 20%
    # -----------------------------------------------------------------------
    sex_label = "female" if params.is_female else "male"
    bmd_status = (
        f"femoral neck T-score {params.femoral_neck_bmd_tscore}"
        if params.femoral_neck_bmd_tscore is not None
        else "without BMD"
    )

    # Treatment threshold assessment
    meets_hip_threshold = hip_risk_pct >= 3.0
    meets_mof_threshold = mof_risk_pct >= 20.0

    if meets_hip_threshold or meets_mof_threshold:
        threshold_msg = (
            "Exceeds NOF/AACE pharmacologic treatment threshold "
            f"({'hip fracture >=3%' if meets_hip_threshold else ''}"
            f"{' and ' if meets_hip_threshold and meets_mof_threshold else ''}"
            f"{'MOF >=20%' if meets_mof_threshold else ''}). "
            "Consider pharmacologic treatment for osteoporosis (bisphosphonates, "
            "denosumab, or other agents) in addition to calcium and vitamin D supplementation."
        )
    else:
        threshold_msg = (
            "Below NOF/AACE pharmacologic treatment thresholds "
            "(hip fracture <3% and MOF <20%). "
            "Recommend lifestyle modifications, adequate calcium and vitamin D intake, "
            "weight-bearing exercise, and fall prevention strategies."
        )

    interpretation = (
        f"FRAX 10-year fracture risk estimation (US Caucasian {sex_label}, "
        f"age {params.age}, BMI {bmi:.1f}, {bmd_status}): "
        f"Major osteoporotic fracture probability {mof_risk_pct}%, "
        f"Hip fracture probability {hip_risk_pct}%. "
        f"{threshold_msg} "
        f"Note: This is a simplified estimation. Verify against the official "
        f"FRAX tool (fraxplus.org) for clinical decisions."
    )

    # The primary output value is MOF probability (the more commonly used
    # clinical decision value). Hip fracture probability is included in
    # the interpretation.
    return ClinicalResult(
        value=mof_risk_pct,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="90265-0",
        fhir_system="http://loinc.org",
        fhir_display="Major osteoporotic fracture 10-year probability [Likelihood] Fracture Risk Assessment",
    )

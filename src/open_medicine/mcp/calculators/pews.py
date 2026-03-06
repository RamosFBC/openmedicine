# Related guidelines: (none currently in registry; no dedicated PEWS guideline)
from enum import Enum
from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class PEWSAgeGroup(str, Enum):
    """Age group for Bedside PEWS age-specific vital sign thresholds."""
    ZERO_TO_3_MONTHS = "0_to_3_months"
    THREE_TO_12_MONTHS = "3_to_12_months"
    ONE_TO_4_YEARS = "1_to_4_years"
    FOUR_TO_12_YEARS = "4_to_12_years"
    OVER_12_YEARS = "over_12_years"


class RespiratoryEffort(str, Enum):
    """Respiratory effort assessment for Bedside PEWS."""
    NORMAL = "normal"
    MILD_INCREASE = "mild_increase"
    MODERATE_INCREASE = "moderate_increase"
    SEVERE_INCREASE_OR_APNOEA = "severe_increase_or_apnoea"


class PEWSParams(BaseModel):
    """Parameters to calculate the Bedside Paediatric Early Warning System (PEWS) score."""
    age_group: PEWSAgeGroup = Field(
        ...,
        description=(
            "Patient age group for age-specific vital sign thresholds. "
            "Options: 0_to_3_months, 3_to_12_months, 1_to_4_years, "
            "4_to_12_years, over_12_years."
        ),
    )
    heart_rate: int = Field(
        ...,
        ge=0,
        description="Heart rate in beats per minute",
    )
    systolic_bp: int = Field(
        ...,
        ge=0,
        description="Systolic blood pressure in mmHg",
    )
    capillary_refill_seconds: float = Field(
        ...,
        ge=0.0,
        description="Capillary refill time in seconds",
    )
    respiratory_rate: int = Field(
        ...,
        ge=0,
        description="Respiratory rate in breaths per minute",
    )
    respiratory_effort: RespiratoryEffort = Field(
        ...,
        description=(
            "Respiratory effort assessment. Scoring: "
            "normal = 0, mild_increase = 1, moderate_increase = 2, "
            "severe_increase_or_apnoea = 4."
        ),
    )
    spo2: int = Field(
        ...,
        ge=0,
        le=100,
        description="Transcutaneous oxygen saturation (SpO2) as percentage (0-100)",
    )
    oxygen_therapy: str = Field(
        "room_air",
        description=(
            "Oxygen therapy level. Options: "
            "'room_air' (score 0), "
            "'lt_4L_or_lt_50pct' (any supplemental O2 <4 L/min or <50%, score 1), "
            "'gte_4L_or_gte_50pct' (>=4 L/min or >=50%, score 2)."
        ),
    )


# ---------------------------------------------------------------------------
# Age-specific scoring tables from Parshuram et al. 2009 (Table 1)
# Each table maps age group -> (score_0_low, score_0_high,
#   score_1_high, score_1_low, score_2_high, score_2_low,
#   score_4_high, score_4_low)
# For heart rate and respiratory rate:
#   score 0 if value >low_0 and <high_0
#   score 1 if >=high_0 or <=low_0  (but not meeting score 2/4)
#   score 2 if >=high_2 or <=low_2  (but not meeting score 4)
#   score 4 if >=high_4 or <=low_4
# ---------------------------------------------------------------------------

# Heart rate thresholds: (normal_low, normal_high,
#   s1_high, s1_low, s2_high, s2_low, s4_high, s4_low)
# score 0: >s0_low and <s0_high
# score 1: >=s0_high or <=s0_low (not meeting 2/4)
# score 2: >=s2_high or <=s2_low (not meeting 4)
# score 4: >=s4_high or <=s4_low
_HR_THRESHOLDS = {
    PEWSAgeGroup.ZERO_TO_3_MONTHS:     (110, 150, 180, 90, 190, 80),
    PEWSAgeGroup.THREE_TO_12_MONTHS:   (100, 150, 170, 80, 180, 70),
    PEWSAgeGroup.ONE_TO_4_YEARS:       (90, 120, 150, 70, 170, 60),
    PEWSAgeGroup.FOUR_TO_12_YEARS:     (70, 110, 130, 60, 150, 50),
    PEWSAgeGroup.OVER_12_YEARS:        (60, 100, 120, 50, 140, 40),
}

# Systolic BP thresholds: same structure
_SBP_THRESHOLDS = {
    PEWSAgeGroup.ZERO_TO_3_MONTHS:     (60, 80, 100, 50, 130, 45),
    PEWSAgeGroup.THREE_TO_12_MONTHS:   (80, 100, 120, 70, 150, 60),
    PEWSAgeGroup.ONE_TO_4_YEARS:       (90, 110, 125, 75, 160, 65),
    PEWSAgeGroup.FOUR_TO_12_YEARS:     (90, 120, 140, 80, 170, 70),
    PEWSAgeGroup.OVER_12_YEARS:        (100, 130, 150, 85, 190, 75),
}

# Respiratory rate thresholds: same structure
_RR_THRESHOLDS = {
    PEWSAgeGroup.ZERO_TO_3_MONTHS:     (29, 61, 81, 19, 91, 15),
    PEWSAgeGroup.THREE_TO_12_MONTHS:   (24, 51, 71, 19, 81, 15),
    PEWSAgeGroup.ONE_TO_4_YEARS:       (19, 41, 61, 15, 71, 12),
    PEWSAgeGroup.FOUR_TO_12_YEARS:     (19, 31, 41, 14, 51, 10),
    PEWSAgeGroup.OVER_12_YEARS:        (11, 17, 23, 10, 30, 9),
}


def _score_vital_sign(value: int, thresholds: tuple) -> int:
    """Score a vital sign using Bedside PEWS age-specific thresholds.

    thresholds = (normal_low, normal_high, s2_high, s2_low, s4_high, s4_low)
    Score 0: value >normal_low and <normal_high
    Score 4: value >=s4_high or value <=s4_low
    Score 2: value >=s2_high or value <=s2_low (but not 4)
    Score 1: anything else abnormal (>=normal_high or <=normal_low)
    """
    normal_low, normal_high, s2_high, s2_low, s4_high, s4_low = thresholds

    # Check score 4 first (most extreme)
    if value >= s4_high or value <= s4_low:
        return 4
    # Check score 2
    if value >= s2_high or value <= s2_low:
        return 2
    # Check score 0 (normal range)
    if value > normal_low and value < normal_high:
        return 0
    # Score 1 (mildly abnormal: >=normal_high or <=normal_low, not meeting 2/4)
    return 1


def _score_capillary_refill(seconds: float) -> int:
    """Score capillary refill time per Bedside PEWS.
    <3 seconds = 0, >=3 seconds = 2.
    """
    if seconds < 3.0:
        return 0
    return 2


def _score_respiratory_effort(effort: RespiratoryEffort) -> int:
    """Score respiratory effort per Bedside PEWS.
    Normal = 0, Mild increase = 1, Moderate increase = 2,
    Severe increase or any apnoea = 4.
    """
    if effort == RespiratoryEffort.NORMAL:
        return 0
    elif effort == RespiratoryEffort.MILD_INCREASE:
        return 1
    elif effort == RespiratoryEffort.MODERATE_INCREASE:
        return 2
    else:
        return 4


def _score_spo2(spo2: int) -> int:
    """Score transcutaneous oxygen saturation per Bedside PEWS.
    >94% = 0, 91-94% = 1, <=90% = 2.
    """
    if spo2 > 94:
        return 0
    elif spo2 >= 91:
        return 1
    else:
        return 2


def _score_oxygen_therapy(therapy: str) -> int:
    """Score oxygen therapy per Bedside PEWS.
    Room air = 0, <4 L/min or <50% = 1, >=4 L/min or >=50% = 2.
    """
    if therapy == "room_air":
        return 0
    elif therapy == "lt_4L_or_lt_50pct":
        return 1
    elif therapy == "gte_4L_or_gte_50pct":
        return 2
    # Default to room air if unrecognized
    return 0


def calculate_pews(params: PEWSParams) -> ClinicalResult:
    """
    Calculates the Bedside Paediatric Early Warning System (PEWS) score.
    Identifies hospitalized children at risk for clinical deterioration
    using seven age-specific vital sign and clinical observation components.
    Reference: Parshuram CS et al. Crit Care. 2009;13(4):R163.
    """
    # 1. Compute each component score
    hr_score = _score_vital_sign(
        params.heart_rate, _HR_THRESHOLDS[params.age_group]
    )
    sbp_score = _score_vital_sign(
        params.systolic_bp, _SBP_THRESHOLDS[params.age_group]
    )
    crt_score = _score_capillary_refill(params.capillary_refill_seconds)
    rr_score = _score_vital_sign(
        params.respiratory_rate, _RR_THRESHOLDS[params.age_group]
    )
    effort_score = _score_respiratory_effort(params.respiratory_effort)
    spo2_score = _score_spo2(params.spo2)
    o2_score = _score_oxygen_therapy(params.oxygen_therapy)

    # 2. Total score (range 0-26)
    total_score = (
        hr_score + sbp_score + crt_score + rr_score
        + effort_score + spo2_score + o2_score
    )

    # 3. Build Evidence with DOI from original derivation study
    evidence = Evidence(
        source_doi="10.1186/cc7998",
        level="Derivation & Validation Study",
        description=(
            "Parshuram CS, Hutchison J, Middaugh K. Development and initial "
            "validation of the Bedside Paediatric Early Warning System score. "
            "Crit Care. 2009;13(4):R163."
        ),
    )

    # 4. Interpret result using thresholds from derivation and
    #    multicentre validation (Parshuram et al. Crit Care. 2011;15:R184)
    #    Score >=7: high risk (sensitivity 64%, specificity 91% in validation;
    #               median case-patient max score 8, IQR 5-12)
    #    Score >=4: moderate risk (increasing trend toward deterioration)
    #    Score <4: low risk (median control-patient max score 2, IQR 1-4)
    if total_score >= 7:
        interpretation = (
            f"Bedside PEWS score is {total_score}. High risk of clinical "
            f"deterioration. Immediate clinical review and consider urgent "
            f"ICU consultation. Score >=7 has sensitivity 64% and specificity "
            f"91% for identifying children requiring urgent ICU admission."
        )
    elif total_score >= 4:
        interpretation = (
            f"Bedside PEWS score is {total_score}. Moderate risk of clinical "
            f"deterioration. Increase monitoring frequency and notify senior "
            f"clinician. Scores in this range approach the critical threshold "
            f"for urgent ICU review."
        )
    else:
        interpretation = (
            f"Bedside PEWS score is {total_score}. Low risk. Continue routine "
            f"monitoring per institutional protocol. Median score in stable "
            f"inpatients is 2 (IQR 1-4)."
        )

    # 5. Return ClinicalResult with FHIR metadata
    # LOINC approximation: no dedicated LOINC code exists for Bedside PEWS;
    # using a generic early warning score concept
    return ClinicalResult(
        value=total_score,
        interpretation=interpretation,
        evidence=evidence,
        # LOINC approximation: no specific Bedside PEWS LOINC code exists;
        # using SNOMED CT early warning score concept as nearest proxy
        fhir_code="1104051000000101",
        fhir_system="http://snomed.info/sct",
        fhir_display="Paediatric early warning score",
    )

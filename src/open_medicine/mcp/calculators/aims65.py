from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence

# Related guidelines: nice_ugib_2012 (risk_assessment section)


class AIMS65Params(BaseModel):
    """Parameters to calculate the AIMS65 Score for upper GI bleeding mortality."""

    albumin_below_3: bool = Field(
        False,
        description="Serum albumin < 3.0 g/dL (< 30 g/L)",
    )
    inr_above_1_5: bool = Field(
        False,
        description="International Normalized Ratio (INR) > 1.5",
    )
    altered_mental_status: bool = Field(
        False,
        description=(
            "Altered mental status: GCS < 14, or documented "
            "disorientation, lethargy, stupor, or coma"
        ),
    )
    systolic_bp_90_or_less: bool = Field(
        False,
        description="Systolic blood pressure <= 90 mmHg",
    )
    age_65_or_older: bool = Field(
        False,
        description="Age >= 65 years",
    )


def calculate_aims65(params: AIMS65Params) -> ClinicalResult:
    """
    Calculates the AIMS65 Score for predicting in-hospital mortality,
    length of stay, and cost in acute upper gastrointestinal bleeding.

    Reference: Saltzman JR et al. Gastrointest Endosc. 2011;74(6):1215-1224.
    """
    # 1. Compute score: each criterion contributes 1 point (range 0-5)
    score = sum([
        params.albumin_below_3,         # A - Albumin < 3.0 g/dL
        params.inr_above_1_5,           # I - INR > 1.5
        params.altered_mental_status,    # M - altered Mental status
        params.systolic_bp_90_or_less,   # S - Systolic BP <= 90 mmHg
        params.age_65_or_older,          # 65 - age >= 65 years
    ])

    # 2. Build Evidence with DOI from the original derivation & validation study
    evidence = Evidence(
        source_doi="10.1016/j.gie.2011.03.1164",
        level="Derivation & Validation Study",
        description=(
            "AIMS65: A simple risk score that accurately predicts in-hospital "
            "mortality, length of stay, and cost in acute upper GI bleeding. "
            "Derived from 29,222 patients and validated in 32,504 patients."
        ),
    )

    # 3. Interpret result using validated mortality strata from the original paper
    #    Mortality rates (validation cohort): 0=0.3%, 1=1.2%, 2=5.3%,
    #    3=10.3%, 4=16.5%, 5=24.5%
    #    Clinical threshold: score >= 2 = high risk
    mortality_by_score = {
        0: 0.3,
        1: 1.2,
        2: 5.3,
        3: 10.3,
        4: 16.5,
        5: 24.5,
    }
    mortality_pct = mortality_by_score[score]

    if score == 0:
        interpretation = (
            f"AIMS65 Score is {score}. "
            f"In-hospital mortality ~{mortality_pct}%. "
            f"Low risk. Consider outpatient management or early discharge."
        )
    elif score == 1:
        interpretation = (
            f"AIMS65 Score is {score}. "
            f"In-hospital mortality ~{mortality_pct}%. "
            f"Low risk. Hospital admission for further evaluation."
        )
    elif score >= 2:
        interpretation = (
            f"AIMS65 Score is {score}. "
            f"In-hospital mortality ~{mortality_pct}%. "
            f"High risk (score >= 2). Intensive monitoring, "
            f"early endoscopy, and ICU-level care should be considered."
        )

    # 4. Return ClinicalResult with FHIR metadata
    # LOINC approximation: no specific AIMS65 code exists; using general
    # upper GI bleeding assessment panel code
    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="LP419518-4",  # LOINC approximation: no specific AIMS65 code exists
        fhir_system="http://loinc.org",
        fhir_display="AIMS65 Score",
    )

# Related guidelines: none currently in registry
from pydantic import BaseModel, Field
from open_medicine.mcp.base import ClinicalResult, Evidence


class FourTsHITParams(BaseModel):
    """Parameters to calculate the 4Ts score for Heparin-Induced Thrombocytopenia (HIT).

    Each of the four categories is scored 0, 1, or 2 points.
    The clinician must select the most appropriate score for each category
    based on clinical assessment.

    Scoring guide:
    - Thrombocytopenia: 2 = platelet fall >50% AND nadir >=20; 1 = platelet fall 30-50%, OR nadir 10-19, OR fall >50% due to surgery; 0 = platelet fall <30% OR nadir <10
    - Timing: 2 = clear onset days 5-10, OR <=1 day with heparin exposure within past 30 days; 1 = consistent with days 5-10 but unclear, OR onset after day 10, OR <=1 day with heparin exposure 30-100 days ago; 0 = fall <4 days without recent heparin exposure
    - Thrombosis: 2 = new thrombosis, skin necrosis, OR acute systemic reaction after IV heparin bolus; 1 = progressive/recurrent thrombosis, non-necrotizing skin lesions, OR suspected thrombosis not yet proven; 0 = none
    - Other causes: 2 = no other apparent cause; 1 = possible other cause; 0 = definite other cause present
    """

    thrombocytopenia: int = Field(
        ...,
        ge=0,
        le=2,
        description=(
            "Thrombocytopenia score (0-2). "
            "2 = platelet count fall >50% AND nadir >=20 x10^9/L; "
            "1 = platelet count fall 30-50%, OR nadir 10-19 x10^9/L, "
            "OR fall >50% due to surgery; "
            "0 = platelet count fall <30% OR nadir <10 x10^9/L"
        ),
    )
    timing: int = Field(
        ...,
        ge=0,
        le=2,
        description=(
            "Timing of platelet count fall score (0-2). "
            "2 = clear onset days 5-10 after heparin start, OR platelet fall "
            "<=1 day with heparin exposure within past 30 days; "
            "1 = consistent with days 5-10 fall but unclear, OR onset after "
            "day 10, OR fall <=1 day with heparin exposure 30-100 days ago; "
            "0 = platelet count fall <4 days without recent heparin exposure"
        ),
    )
    thrombosis: int = Field(
        ...,
        ge=0,
        le=2,
        description=(
            "Thrombosis or other sequelae score (0-2). "
            "2 = new confirmed thrombosis, skin necrosis, OR acute systemic "
            "reaction after IV heparin bolus; "
            "1 = progressive or recurrent thrombosis, non-necrotizing skin "
            "lesions, OR suspected thrombosis not yet proven; "
            "0 = none"
        ),
    )
    other_causes: int = Field(
        ...,
        ge=0,
        le=2,
        description=(
            "Other causes of thrombocytopenia score (0-2). "
            "2 = no other apparent cause of thrombocytopenia; "
            "1 = possible other cause is present; "
            "0 = definite other cause is present "
            "(e.g., sepsis, DIC, drug-induced, post-surgical)"
        ),
    )


def calculate_4ts_hit(params: FourTsHITParams) -> ClinicalResult:
    """
    Calculates the 4Ts score for pretest probability of Heparin-Induced
    Thrombocytopenia (HIT).

    The 4Ts score estimates the clinical probability of HIT by assessing
    four domains: Thrombocytopenia, Timing, Thrombosis, and oTher causes.
    A low score (0-3) effectively rules out HIT (NPV ~99.8%), while
    intermediate (4-5) and high (6-8) scores warrant further laboratory
    testing.

    Reference: Lo GK, Juhl D, Warkentin TE, et al. J Thromb Haemost. 2006;4(4):759-765.
    """
    # 1. Compute total score (sum of 4 categories, each 0-2, range 0-8)
    score = (
        params.thrombocytopenia
        + params.timing
        + params.thrombosis
        + params.other_causes
    )

    # 2. Build Evidence from the original validation study
    evidence = Evidence(
        source_doi="10.1111/j.1538-7836.2006.01787.x",
        level="Derivation & Validation Study",
        description=(
            "Lo GK, Juhl D, Warkentin TE, et al. Evaluation of pretest "
            "clinical score (4 T's) for the diagnosis of heparin-induced "
            "thrombocytopenia in two clinical settings. "
            "J Thromb Haemost. 2006;4(4):759-765."
        ),
    )

    # 3. Interpret result using validated thresholds
    if score <= 3:
        interpretation = (
            f"4Ts HIT score is {score}. Low pretest probability for HIT "
            f"(score 0-3). HIT is unlikely (NPV ~99.8%). "
            f"HIT laboratory testing is generally not recommended. "
            f"Consider alternative causes of thrombocytopenia."
        )
    elif score <= 5:
        interpretation = (
            f"4Ts HIT score is {score}. Intermediate pretest probability "
            f"for HIT (score 4-5). HIT is possible (PPV ~14%). "
            f"Send HIT antibody testing (immunoassay +/- functional assay). "
            f"Consider initiating non-heparin anticoagulation while awaiting "
            f"results if clinical suspicion is significant."
        )
    else:
        interpretation = (
            f"4Ts HIT score is {score}. High pretest probability for HIT "
            f"(score 6-8). HIT is likely (PPV ~64%). "
            f"Discontinue all heparin products immediately. Initiate "
            f"non-heparin anticoagulation (e.g., argatroban, bivalirudin, "
            f"fondaparinux). Send HIT antibody testing for confirmation."
        )

    # 4. Return ClinicalResult with FHIR metadata
    # LOINC approximation: no specific LOINC code exists for the 4Ts HIT score
    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="LP419518-4",
        fhir_system="http://loinc.org",
        fhir_display="4Ts score for heparin-induced thrombocytopenia",
    )

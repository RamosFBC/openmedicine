from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence

# Related guidelines: none


class ISTHDICParams(BaseModel):
    """Parameters to calculate the ISTH Overt DIC Score.

    Prerequisite: This score should only be applied in patients with an
    underlying disorder known to be associated with DIC (e.g., sepsis,
    malignancy, trauma, obstetric complications, severe immunological
    reactions, heat stroke).
    """

    platelet_count: int = Field(
        ...,
        ge=0,
        description=(
            "Platelet count in x10^9/L (x10^3/uL). "
            "Normal range typically 150-400 x10^9/L."
        ),
    )
    fibrin_marker_increase: int = Field(
        ...,
        ge=0,
        le=2,
        description=(
            "Degree of elevation of a fibrin-related marker such as D-dimer "
            "or fibrin degradation products (FDP). "
            "0 = no increase, 1 = moderate increase, 2 = strong increase. "
            "Interpretation of moderate vs strong increase depends on the "
            "local assay and institutional reference ranges."
        ),
    )
    pt_prolongation_seconds: float = Field(
        ...,
        ge=0.0,
        description=(
            "Prolongation of prothrombin time (PT) above the upper limit of "
            "the institutional normal range, expressed in seconds. "
            "For example, if the normal PT upper limit is 13.5 s and the "
            "patient's PT is 17.0 s, enter 3.5."
        ),
    )
    fibrinogen_level: float = Field(
        ...,
        ge=0.0,
        description=(
            "Fibrinogen level in g/L. Normal range is typically 2-4 g/L. "
            "Note: 1 g/L = 100 mg/dL."
        ),
    )


def calculate_isth_dic(params: ISTHDICParams) -> ClinicalResult:
    """
    Calculates the ISTH Overt DIC Score for diagnosis of disseminated
    intravascular coagulation in patients with a known underlying disorder.
    Reference: Taylor FB Jr et al. Thromb Haemost. 2001;86(5):1327-1330.
    """
    score = 0

    # 1. Platelet count scoring
    # >= 100 x10^9/L: 0 points
    # 50 to < 100 x10^9/L: 1 point
    # < 50 x10^9/L: 2 points
    if params.platelet_count < 50:
        score += 2
    elif params.platelet_count < 100:
        score += 1

    # 2. Elevated fibrin-related marker (e.g., D-dimer, FDP)
    # No increase (0): 0 points
    # Moderate increase (1): 2 points
    # Strong increase (2): 3 points
    if params.fibrin_marker_increase == 1:
        score += 2
    elif params.fibrin_marker_increase == 2:
        score += 3

    # 3. Prolonged prothrombin time (PT)
    # < 3 seconds above upper limit of normal: 0 points
    # >= 3 to < 6 seconds: 1 point
    # >= 6 seconds: 2 points
    if params.pt_prolongation_seconds >= 6:
        score += 2
    elif params.pt_prolongation_seconds >= 3:
        score += 1

    # 4. Fibrinogen level
    # >= 1 g/L: 0 points
    # < 1 g/L: 1 point
    if params.fibrinogen_level < 1.0:
        score += 1

    # Evidence from the original ISTH SSC publication
    evidence = Evidence(
        source_doi="10.1055/s-0037-1616068",
        level="Guideline",
        description=(
            "ISTH SSC scoring system for overt DIC. "
            "Taylor FB Jr, Toh CH, Hoots WK, Wada H, Levi M. "
            "Thromb Haemost. 2001;86(5):1327-1330."
        ),
    )

    # Interpretation based on validated threshold of >= 5
    if score >= 5:
        interpretation = (
            f"ISTH DIC score is {score}. Compatible with overt DIC "
            f"(score >= 5). Treat for DIC as appropriate and repeat scoring "
            f"daily to monitor response."
        )
    else:
        interpretation = (
            f"ISTH DIC score is {score}. Not compatible with overt DIC "
            f"(score < 5). This does not rule out non-overt (early) DIC. "
            f"Repeat scoring in 1-2 days if clinical suspicion persists."
        )

    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        # LOINC approximation: no specific LOINC code exists for the
        # composite ISTH DIC score. Using the intravascular coagulation
        # and fibrinolysis panel code as the closest match.
        fhir_code="98125-8",
        fhir_system="http://loinc.org",
        fhir_display="Intravascular coagulation and fibrinolysis panel",
    )

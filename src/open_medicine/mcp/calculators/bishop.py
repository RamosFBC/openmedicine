# No related guidelines in current registry
from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class BishopParams(BaseModel):
    """Parameters to calculate the Bishop Score for cervical favorability assessment."""

    dilation_cm: int = Field(
        ...,
        ge=0,
        le=6,
        description=(
            "Cervical dilation in centimeters (0-6). "
            "0 = closed, 1-2 cm, 3-4 cm, 5-6 cm."
        ),
    )
    effacement_pct: int = Field(
        ...,
        ge=0,
        le=100,
        description=(
            "Cervical effacement as a percentage (0-100). "
            "0-30% = 0 pts, 40-50% = 1 pt, 60-70% = 2 pts, >=80% = 3 pts."
        ),
    )
    station: int = Field(
        ...,
        ge=-3,
        le=2,
        description=(
            "Fetal station relative to ischial spines (-3 to +2). "
            "-3 = 0 pts, -2 = 1 pt, -1 or 0 = 2 pts, +1 or +2 = 3 pts."
        ),
    )
    consistency: int = Field(
        ...,
        ge=0,
        le=2,
        description=(
            "Cervical consistency (0 = firm, 1 = medium, 2 = soft)."
        ),
    )
    position: int = Field(
        ...,
        ge=0,
        le=2,
        description=(
            "Cervical position (0 = posterior, 1 = mid-position, 2 = anterior)."
        ),
    )


def calculate_bishop(params: BishopParams) -> ClinicalResult:
    """
    Calculates the Bishop Score for pre-induction cervical favorability.

    The Bishop Score assesses five cervical parameters (dilation, effacement,
    station, consistency, and position) to predict the likelihood of a successful
    vaginal delivery following labor induction. Total score ranges from 0 to 13.

    Reference: Bishop EH. Obstet Gynecol. 1964;24:266-268.
    """
    score = 0

    # Dilation (0-3 points)
    # Closed = 0, 1-2 cm = 1, 3-4 cm = 2, 5-6 cm = 3
    if params.dilation_cm == 0:
        score += 0
    elif params.dilation_cm <= 2:
        score += 1
    elif params.dilation_cm <= 4:
        score += 2
    else:
        score += 3

    # Effacement (0-3 points)
    # Published ranges: 0-30% = 0, 40-50% = 1, 60-70% = 2, >=80% = 3
    # Thresholds use <40, <60, <80 to correctly classify intermediate values
    # (31-39% -> 0 pts, 51-59% -> 1 pt, 71-79% -> 2 pts) per standard
    # implementations that treat the published ranges as contiguous bins.
    if params.effacement_pct < 40:
        score += 0
    elif params.effacement_pct < 60:
        score += 1
    elif params.effacement_pct < 80:
        score += 2
    else:
        score += 3

    # Station (0-3 points)
    # -3 = 0, -2 = 1, -1 or 0 = 2, +1 or +2 = 3
    if params.station == -3:
        score += 0
    elif params.station == -2:
        score += 1
    elif params.station <= 0:
        score += 2
    else:
        score += 3

    # Consistency (0-2 points): directly mapped from input
    # 0 = firm, 1 = medium, 2 = soft
    score += params.consistency

    # Position (0-2 points): directly mapped from input
    # 0 = posterior, 1 = mid-position, 2 = anterior
    score += params.position

    evidence = Evidence(
        source_doi="10.1097/00006250-196408000-00009",
        level="Derivation Study",
        description=(
            "Bishop EH. Pelvic Scoring for Elective Induction. "
            "Obstet Gynecol. 1964;24:266-268."
        ),
    )

    # Interpretation based on standard clinical thresholds
    # Bishop originally reported that scores >=9 allowed safe elective induction.
    # Modern practice uses >=8 as favorable and <=6 as unfavorable.
    if score >= 8:
        interpretation = (
            f"Bishop Score is {score}. Favorable cervix. "
            "High likelihood of successful vaginal delivery with induction. "
            "Cervical ripening is generally not needed."
        )
    elif score >= 6:
        interpretation = (
            f"Bishop Score is {score}. Moderately favorable cervix. "
            "Induction may be attempted; consider cervical ripening to improve success."
        )
    else:
        interpretation = (
            f"Bishop Score is {score}. Unfavorable cervix. "
            "Low likelihood of successful induction without cervical ripening. "
            "Cervical ripening agents (e.g., prostaglandins, mechanical dilators) "
            "are recommended prior to oxytocin induction."
        )

    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        # No dedicated LOINC code exists for the Bishop Score. LOINC 76504-0
        # ("Total score [HARK]") was previously used here in error — it represents
        # the Humiliation, Afraid, Rape, Kick interpersonal violence screening
        # tool, not the Bishop cervical favorability score. Setting fhir_code and
        # fhir_system to None until a proper LOINC observation code is registered.
        fhir_code=None,
        fhir_system=None,
        fhir_display="Bishop Score [Total]",
    )

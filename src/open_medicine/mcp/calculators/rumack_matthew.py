import math
from pydantic import BaseModel, Field
from open_medicine.mcp.base import ClinicalResult, Evidence


class RumackMatthewParams(BaseModel):
    """Parameters to evaluate acetaminophen toxicity using the Rumack-Matthew Nomogram."""
    serum_acetaminophen: float = Field(
        ...,
        description="Serum acetaminophen concentration in mcg/mL (micrograms per milliliter)"
    )
    hours_since_ingestion: float = Field(
        ...,
        description=(
            "Hours elapsed since acute acetaminophen ingestion. "
            "The nomogram is validated for 4-24 hours post-ingestion."
        )
    )


def calculate_rumack_matthew(params: RumackMatthewParams) -> ClinicalResult:
    """
    Evaluates acetaminophen toxicity risk using the Rumack-Matthew Nomogram.
    Plots serum acetaminophen concentration against time since ingestion to
    determine need for N-acetylcysteine (NAC) treatment.

    The nomogram applies only to single acute ingestions of immediate-release
    acetaminophen with a known time of ingestion.

    Reference: Rumack BH, Matthew H. Pediatrics. 1975;55(6):871-876.
    Treatment line: Rumack BH, Peterson RC, Koch GG, Amara IA.
    Arch Intern Med. 1981;141(3):380-385.
    """

    serum_level = params.serum_acetaminophen
    hours = params.hours_since_ingestion

    evidence = Evidence(
        source_doi="10.1542/peds.55.6.871",
        level="Derivation & Validation Study",
        description=(
            "Rumack BH, Matthew H. Acetaminophen poisoning and toxicity. "
            "Pediatrics. 1975;55(6):871-876."
        )
    )

    # The nomogram is only validated for 4-24 hours post-ingestion.
    # Before 4 hours, absorption may be incomplete so levels are unreliable.
    # After 24 hours, the nomogram is not validated.
    if hours < 4:
        return ClinicalResult(
            value=serum_level,
            interpretation=(
                f"Serum acetaminophen is {serum_level} mcg/mL at {hours} hours "
                f"post-ingestion. The Rumack-Matthew nomogram is only validated "
                f"for levels drawn at 4-24 hours post-ingestion. Levels drawn "
                f"before 4 hours may not reflect peak absorption and cannot be "
                f"reliably interpreted using the nomogram. Redraw level at or "
                f"after 4 hours post-ingestion."
            ),
            evidence=evidence,
            fhir_code=None,
            fhir_system=None,
            fhir_display="Rumack-Matthew nomogram risk assessment"
        )

    if hours > 24:
        return ClinicalResult(
            value=serum_level,
            interpretation=(
                f"Serum acetaminophen is {serum_level} mcg/mL at {hours} hours "
                f"post-ingestion. The Rumack-Matthew nomogram is only validated "
                f"for 4-24 hours post-ingestion. Beyond 24 hours, clinical "
                f"assessment should rely on hepatic function tests (AST, ALT, "
                f"INR) and clinical status rather than the nomogram."
            ),
            evidence=evidence,
            fhir_code=None,
            fhir_system=None,
            fhir_display="Rumack-Matthew nomogram risk assessment"
        )

    # --- Rumack-Matthew Nomogram Lines ---
    # All lines use exponential decay with a 4-hour half-life starting at t=4h.
    # Formula: C_threshold = C0 * (0.5)^((t - 4) / 4)
    #
    # Treatment line (150 line): C0 = 150 mcg/mL at 4 hours
    #   Created by the FDA as 25% below the original 200 line.
    #   Standard of care in the US, Canada, and Australia for NAC initiation.
    #
    # Probable hepatotoxicity line (200 line): C0 = 200 mcg/mL at 4 hours
    #   Original Rumack-Matthew line from the 1975 paper.

    exponent = (hours - 4.0) / 4.0

    treatment_threshold = 150.0 * math.pow(0.5, exponent)
    probable_toxicity_threshold = 200.0 * math.pow(0.5, exponent)

    treatment_threshold_rounded = round(treatment_threshold, 1)
    probable_toxicity_rounded = round(probable_toxicity_threshold, 1)

    # Classify serum level relative to nomogram lines
    if serum_level >= probable_toxicity_threshold:
        risk_zone = "above_probable"
    elif serum_level >= treatment_threshold:
        risk_zone = "above_treatment"
    else:
        risk_zone = "below_treatment"

    # Build interpretation
    if risk_zone == "above_probable":
        interpretation = (
            f"Serum acetaminophen is {serum_level} mcg/mL at {hours} hours "
            f"post-ingestion. Level is ABOVE the probable hepatotoxicity line "
            f"({probable_toxicity_rounded} mcg/mL at {hours}h) and above the "
            f"treatment line ({treatment_threshold_rounded} mcg/mL at {hours}h). "
            f"Probable hepatotoxicity. Initiate N-acetylcysteine (NAC) "
            f"immediately. Obtain baseline hepatic panel (AST, ALT, INR, "
            f"creatinine) and monitor serially."
        )
    elif risk_zone == "above_treatment":
        interpretation = (
            f"Serum acetaminophen is {serum_level} mcg/mL at {hours} hours "
            f"post-ingestion. Level is ABOVE the treatment line "
            f"({treatment_threshold_rounded} mcg/mL at {hours}h) but below the "
            f"probable hepatotoxicity line "
            f"({probable_toxicity_rounded} mcg/mL at {hours}h). "
            f"Possible hepatotoxicity. Initiate N-acetylcysteine (NAC) "
            f"treatment. Obtain baseline hepatic panel (AST, ALT, INR, "
            f"creatinine) and monitor."
        )
    else:
        interpretation = (
            f"Serum acetaminophen is {serum_level} mcg/mL at {hours} hours "
            f"post-ingestion. Level is BELOW the treatment line "
            f"({treatment_threshold_rounded} mcg/mL at {hours}h). "
            f"Hepatotoxicity is unlikely based on the nomogram. "
            f"NAC treatment is generally not indicated. "
            f"Clinical judgment should still be applied, especially if "
            f"ingestion time is uncertain or co-ingestants are suspected."
        )

    return ClinicalResult(
        value=serum_level,
        interpretation=interpretation,
        evidence=evidence,
        # No LOINC observation code exists for the Rumack-Matthew nomogram
        # risk assessment output. LOINC 3298-7 represents the input measurement
        # (serum acetaminophen level), not the output concept, so using None
        # to avoid semantic misrepresentation.
        fhir_code=None,
        fhir_system=None,
        fhir_display="Rumack-Matthew nomogram risk assessment"
    )

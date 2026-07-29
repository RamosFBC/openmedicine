# Related guidelines: aba_burn_2016 (burn_assessment section)
from pydantic import BaseModel, Field
from open_medicine.mcp.base import ClinicalResult, Evidence


class TBSAParams(BaseModel):
    """Parameters to calculate Total Body Surface Area (TBSA) burned using the Wallace Rule of Nines.

    Each field represents a body region. Set to True if that region has a burn
    involving partial-thickness (2nd degree) or full-thickness (3rd degree) injury.
    For the adult Rule of Nines, superficial (1st degree) burns are typically
    excluded from TBSA calculation for fluid resuscitation purposes.

    Half-region fields (e.g. anterior_trunk, posterior_trunk) allow more granular
    input when only part of a standard region is burned.
    """

    head_and_neck: bool = Field(
        False,
        description="Head and neck burned (9% TBSA). Includes entire head, face, and neck.",
    )
    anterior_trunk: bool = Field(
        False,
        description="Anterior trunk burned (18% TBSA). Chest and abdomen.",
    )
    posterior_trunk: bool = Field(
        False,
        description="Posterior trunk burned (18% TBSA). Upper and lower back.",
    )
    left_upper_extremity: bool = Field(
        False,
        description="Left upper extremity burned (9% TBSA). Includes entire arm and hand.",
    )
    right_upper_extremity: bool = Field(
        False,
        description="Right upper extremity burned (9% TBSA). Includes entire arm and hand.",
    )
    left_lower_extremity: bool = Field(
        False,
        description="Left lower extremity burned (18% TBSA). Includes entire leg and foot.",
    )
    right_lower_extremity: bool = Field(
        False,
        description="Right lower extremity burned (18% TBSA). Includes entire leg and foot.",
    )
    perineum: bool = Field(
        False,
        description="Perineum/genitalia burned (1% TBSA).",
    )


def calculate_tbsa(params: TBSAParams) -> ClinicalResult:
    """
    Calculates the estimated Total Body Surface Area (TBSA) burned using the
    Wallace Rule of Nines for adult patients.

    The Rule of Nines divides the adult body into anatomical regions that are
    approximately 9% of TBSA (or multiples thereof):
      - Head and neck: 9%
      - Each upper extremity: 9%
      - Anterior trunk: 18%
      - Posterior trunk: 18%
      - Each lower extremity: 18%
      - Perineum: 1%

    Reference: Wallace AB. The exposure treatment of burns. Lancet. 1951;1(6653):501-504.
    """
    # Calculate TBSA by summing affected regions
    tbsa = 0.0

    if params.head_and_neck:
        tbsa += 9.0
    if params.anterior_trunk:
        tbsa += 18.0
    if params.posterior_trunk:
        tbsa += 18.0
    if params.left_upper_extremity:
        tbsa += 9.0
    if params.right_upper_extremity:
        tbsa += 9.0
    if params.left_lower_extremity:
        tbsa += 18.0
    if params.right_lower_extremity:
        tbsa += 18.0
    if params.perineum:
        tbsa += 1.0

    # Build evidence from the original Wallace 1951 paper
    evidence = Evidence(
        source_doi="10.1016/S0140-6736(51)91975-7",
        level="Derivation Study",
        description=(
            "Wallace AB. The exposure treatment of burns. "
            "Lancet. 1951;1(6653):501-504."
        ),
    )

    # Interpret the result based on ABA burn severity classification
    # Minor burn: <10% TBSA in adults (partial-thickness), <5% full-thickness
    # Moderate burn: 10-20% TBSA (partial-thickness), <10% full-thickness
    # Major burn: >20% TBSA (partial-thickness), >10% full-thickness, or
    #   burns involving face, hands, feet, genitalia, perineum, major joints
    if tbsa == 0.0:
        interpretation = (
            "TBSA burned is 0%. No burn areas selected. "
            "Verify assessment is complete."
        )
    elif tbsa < 10.0:
        interpretation = (
            f"TBSA burned is {tbsa}% (Rule of Nines). "
            f"Minor burn. Typically managed as outpatient if partial-thickness "
            f"and no high-risk areas involved. "
            f"Consider burn center referral if face, hands, feet, genitalia, "
            f"perineum, or major joints are involved."
        )
    elif tbsa <= 20.0:
        interpretation = (
            f"TBSA burned is {tbsa}% (Rule of Nines). "
            f"Moderate burn. IV fluid resuscitation indicated. "
            f"Consider burn center referral per ABA criteria. "
            f"Parkland formula: {round(4.0 * 70 * tbsa)} mL LR over 24h "
            f"for a 70 kg patient (adjust for actual weight)."
        )
    else:
        interpretation = (
            f"TBSA burned is {tbsa}% (Rule of Nines). "
            f"Major burn (>20% TBSA). Immediate IV fluid resuscitation required. "
            f"Burn center transfer indicated per ABA referral criteria. "
            f"Parkland formula: {round(4.0 * 70 * tbsa)} mL LR over 24h "
            f"for a 70 kg patient (adjust for actual weight)."
        )

    return ClinicalResult(
        value=tbsa,
        interpretation=interpretation,
        evidence=evidence,
        # LOINC approximation: no exact LOINC code for "TBSA burned percentage"
        # Using 8277-6 (Body surface area) as nearest approximation since the
        # output represents a percentage of total body surface area.
        fhir_code="8277-6",
        fhir_system="http://loinc.org",
        fhir_display="Body surface area",
    )

# Related guidelines: ada_dka_hhs_2024 (diagnosis section)
from typing import Optional
from pydantic import BaseModel, Field
from open_medicine.mcp.base import ClinicalResult, Evidence


class AnionGapParams(BaseModel):
    """Parameters to calculate the serum anion gap."""
    sodium: float = Field(..., description="Serum sodium (Na) in mEq/L")
    chloride: float = Field(..., description="Serum chloride (Cl) in mEq/L")
    bicarbonate: float = Field(..., description="Serum bicarbonate (HCO3) in mEq/L")
    albumin: Optional[float] = Field(None, description="Serum albumin in g/dL. If provided, corrected anion gap is calculated: AG + 2.5 × (4.0 - albumin).")


def calculate_anion_gap(params: AnionGapParams) -> ClinicalResult:
    """
    Calculates the serum anion gap, with optional albumin correction.
    AG = Na - (Cl + HCO3). Corrected AG = AG + 2.5 × (4.0 - albumin).
    Reference: Kraut JA, Madias NE. NEJM 2007.
    """
    ag = params.sodium - (params.chloride + params.bicarbonate)
    ag_rounded = round(ag, 1)

    if params.albumin is not None:
        corrected_ag = ag + 2.5 * (4.0 - params.albumin)
        corrected_ag_rounded = round(corrected_ag, 1)

        parts = [f"Anion gap is {ag_rounded} mEq/L. Albumin-corrected anion gap is {corrected_ag_rounded} mEq/L."]
        if corrected_ag_rounded > 12:
            parts.append("Elevated corrected anion gap. Suggests high anion gap metabolic acidosis (HAGMA). Consider lactic acidosis, ketoacidosis, toxic ingestions, or renal failure.")
        elif corrected_ag_rounded >= 8:
            parts.append("Normal corrected anion gap (8-12 mEq/L).")
        else:
            parts.append("Low corrected anion gap (<8 mEq/L). Consider hypoalbuminemia (already corrected), lab error, or paraproteinemia.")

        result_value = corrected_ag_rounded
    else:
        parts = [f"Anion gap is {ag_rounded} mEq/L."]
        if ag_rounded > 12:
            parts.append("Elevated anion gap (>12 mEq/L). Suggests high anion gap metabolic acidosis (HAGMA). Consider lactic acidosis, ketoacidosis, toxic ingestions, or renal failure. Note: consider albumin correction if albumin is low.")
        elif ag_rounded >= 8:
            parts.append("Normal anion gap (8-12 mEq/L).")
        else:
            parts.append("Low anion gap (<8 mEq/L). Consider hypoalbuminemia, lab error, or paraproteinemia.")

        result_value = ag_rounded

    interpretation = " ".join(parts)

    evidence = Evidence(
        source_doi="10.1056/NEJMra066466",
        level="Review",
        description="Kraut JA, Madias NE. Serum anion gap: its uses and limitations in clinical medicine. NEJM 2007."
    )

    return ClinicalResult(
        value=result_value,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="33037-3",  # LOINC: Anion gap in Serum or Plasma
        fhir_system="http://loinc.org",
        fhir_display="Anion gap in Serum or Plasma"
    )

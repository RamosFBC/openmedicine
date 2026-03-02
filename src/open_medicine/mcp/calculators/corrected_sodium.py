# Related guidelines: ada_dka_hhs_2024 (diagnosis, fluid_resuscitation sections)
from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class CorrectedSodiumParams(BaseModel):
    """Parameters to calculate corrected sodium for hyperglycemia."""
    sodium: float = Field(..., description="Measured serum sodium (Na) in mEq/L")
    glucose: float = Field(..., description="Serum glucose in mg/dL")


def calculate_corrected_sodium(params: CorrectedSodiumParams) -> ClinicalResult:
    """
    Calculates corrected sodium for hyperglycemia.
    Katz formula: Corrected Na = Na + 1.6 × [(Glucose - 100) / 100]
    Hillier formula (glucose >400): Corrected Na = Na + 2.4 × [(Glucose - 100) / 100]
    Reference: Katz MA. NEJM 1973.
    """
    correction_katz = 1.6 * ((params.glucose - 100) / 100.0)
    corrected_na_katz = params.sodium + correction_katz
    corrected_na_katz_rounded = round(corrected_na_katz, 1)

    parts = [f"Corrected sodium (Katz) = {corrected_na_katz_rounded} mEq/L."]

    if params.glucose > 400:
        correction_hillier = 2.4 * ((params.glucose - 100) / 100.0)
        corrected_na_hillier = params.sodium + correction_hillier
        corrected_na_hillier_rounded = round(corrected_na_hillier, 1)
        parts.append(f"Glucose >400 mg/dL: Hillier correction may be more accurate. Corrected sodium (Hillier) = {corrected_na_hillier_rounded} mEq/L.")

    if corrected_na_katz_rounded > 145:
        parts.append("Corrected sodium is elevated (>145 mEq/L). True hypernatremia despite measured hyponatremia.")
    elif corrected_na_katz_rounded >= 135:
        parts.append("Corrected sodium is normal (135-145 mEq/L). Dilutional hyponatremia from hyperglycemia.")
    else:
        parts.append("Corrected sodium remains low (<135 mEq/L). True hyponatremia in addition to hyperglycemia.")

    evidence = Evidence(
        source_doi="10.1056/NEJM197304052881404",
        level="Derivation & Validation Study",
        description="Katz MA. Hyperglycemia-induced hyponatremia — calculation of expected serum sodium depression. NEJM 1973."
    )

    return ClinicalResult(
        value=corrected_na_katz_rounded,
        interpretation=" ".join(parts),
        evidence=evidence,
        fhir_code="2951-2",  # LOINC: Sodium in Serum or Plasma
        fhir_system="http://loinc.org",
        fhir_display="Sodium [Moles/volume] in Serum or Plasma"
    )

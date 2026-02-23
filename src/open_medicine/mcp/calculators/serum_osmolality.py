from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class SerumOsmolalityParams(BaseModel):
    """Parameters to calculate serum osmolality."""
    sodium: float = Field(..., description="Serum sodium (Na) in mEq/L")
    glucose: float = Field(..., description="Serum glucose in mg/dL")
    bun: float = Field(..., description="Blood urea nitrogen (BUN) in mg/dL")


def calculate_serum_osmolality(params: SerumOsmolalityParams) -> ClinicalResult:
    """
    Calculates serum osmolality.
    Formula: Osm = 2×Na + Glucose/18 + BUN/2.8
    Reference: Purssell RA et al. Ann Emerg Med 2001.
    """
    osm = 2 * params.sodium + params.glucose / 18.0 + params.bun / 2.8
    osm_rounded = round(osm, 1)

    parts = [f"Calculated serum osmolality is {osm_rounded} mOsm/kg."]
    if osm_rounded > 295:
        parts.append("Elevated (>295 mOsm/kg). Consider hypernatremia, hyperglycemia, uremia, or toxic alcohol ingestion.")
    elif osm_rounded >= 275:
        parts.append("Normal range (275-295 mOsm/kg).")
    else:
        parts.append("Low (<275 mOsm/kg). Consider hyponatremia or overhydration.")

    evidence = Evidence(
        source_doi="10.1067/mem.2001.119455",
        level="Validation Study",
        description="Purssell RA et al. Derivation and validation of a formula to calculate the contribution of ethanol to the osmolal gap. Ann Emerg Med 2001."
    )

    return ClinicalResult(
        value=osm_rounded,
        interpretation=" ".join(parts),
        evidence=evidence,
        fhir_code="2692-2",  # LOINC: Osmolality of Serum or Plasma
        fhir_system="http://loinc.org",
        fhir_display="Osmolality of Serum or Plasma"
    )

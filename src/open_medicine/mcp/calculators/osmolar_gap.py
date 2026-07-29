from pydantic import BaseModel, Field
from open_medicine.mcp.base import ClinicalResult, Evidence


class OsmolarGapParams(BaseModel):
    """Parameters to calculate the osmolar gap."""
    measured_osmolality: float = Field(..., description="Measured serum osmolality in mOsm/kg")
    sodium: float = Field(..., description="Serum sodium (Na) in mEq/L")
    glucose: float = Field(..., description="Serum glucose in mg/dL")
    bun: float = Field(..., description="Blood urea nitrogen (BUN) in mg/dL")


def calculate_osmolar_gap(params: OsmolarGapParams) -> ClinicalResult:
    """
    Calculates the osmolar gap (measured - calculated osmolality).
    Reference: Smithline N, Gardner KD. JAMA. 1976;236(14):1594-1597.
    """
    calculated_osm = 2 * params.sodium + params.glucose / 18.0 + params.bun / 2.8
    osm_gap = params.measured_osmolality - calculated_osm
    osm_gap_rounded = round(osm_gap, 1)

    parts = [f"Osmolar gap is {osm_gap_rounded} mOsm/kg (measured {params.measured_osmolality}, calculated {round(calculated_osm, 1)})."]
    if osm_gap_rounded > 10:
        parts.append("Elevated osmolar gap (>10 mOsm/kg). Consider toxic alcohol ingestion (methanol, ethylene glycol), ethanol, or other unmeasured osmoles.")
    elif osm_gap_rounded >= -10:
        parts.append("Normal osmolar gap (-10 to 10 mOsm/kg).")
    else:
        parts.append("Negative osmolar gap. Consider lab error or hypoproteinemia.")

    evidence = Evidence(
        source_doi="10.1001/jama.1976.03270150050029",
        level="Derivation Study",
        description="Smithline N, Gardner KD. Gaps -- anionic and osmolal. JAMA. 1976;236(14):1594-1597."
    )

    return ClinicalResult(
        value=osm_gap_rounded,
        interpretation=" ".join(parts),
        evidence=evidence,
        fhir_code="2693-0",  # LOINC: Osmolal gap in Serum or Plasma
        fhir_system="http://loinc.org",
        fhir_display="Osmolal gap in Serum or Plasma"
    )

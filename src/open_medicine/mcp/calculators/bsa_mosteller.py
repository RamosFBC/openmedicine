import math
from pydantic import BaseModel, Field
from open_medicine.mcp.base import ClinicalResult, Evidence


class BSAMostellerParams(BaseModel):
    """Parameters to calculate Body Surface Area using the Mosteller formula."""
    height_cm: float = Field(..., description="Height in centimeters")
    weight_kg: float = Field(..., description="Body weight in kilograms")


def calculate_bsa_mosteller(params: BSAMostellerParams) -> ClinicalResult:
    """
    Calculates Body Surface Area (BSA) using the Mosteller formula.
    BSA (m²) = √[(height_cm × weight_kg) / 3600]
    Reference: Mosteller RD. N Engl J Med 1987; 317:1098.
    """
    bsa = math.sqrt((params.height_cm * params.weight_kg) / 3600.0)
    bsa_rounded = round(bsa, 2)

    if bsa_rounded < 1.5:
        interpretation = (
            f"BSA is {bsa_rounded} m². Below typical adult range (1.5-2.2 m²). "
            f"Consider adjusted dosing for body size."
        )
    elif bsa_rounded <= 2.2:
        interpretation = (
            f"BSA is {bsa_rounded} m². Within normal adult range (1.5-2.2 m²)."
        )
    else:
        interpretation = (
            f"BSA is {bsa_rounded} m². Above typical adult range (1.5-2.2 m²). "
            f"Consider adjusted dosing for body size."
        )

    evidence = Evidence(
        source_doi="10.1056/NEJM198710223171717",
        level="Validation Study",
        description="Simplified Calculation of Body-Surface Area (Mosteller RD, NEJM 1987)"
    )

    return ClinicalResult(
        value=bsa_rounded,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="3140-1",
        fhir_system="http://loinc.org",
        fhir_display="Body surface area Derived from formula"
    )

from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class ParklandParams(BaseModel):
    """Parameters to calculate the Parkland Formula for burn fluid resuscitation."""
    weight_kg: float = Field(..., description="Patient body weight in kilograms", gt=0)
    tbsa_percent: float = Field(..., description="Total body surface area burned (%)", ge=0, le=100)


def calculate_parkland(params: ParklandParams) -> ClinicalResult:
    """
    Calculates the Parkland Formula for fluid resuscitation in burn patients.
    Total 24h fluid (mL) = 4 × weight (kg) × %TBSA burned.
    Reference: Baxter CR. Surg Clin North Am 1978;58:1313-1322.
    """
    total_24h = 4.0 * params.weight_kg * params.tbsa_percent
    first_8h = total_24h / 2.0
    next_16h = total_24h / 2.0
    rate_first_8h = round(first_8h / 8.0, 1)
    rate_next_16h = round(next_16h / 16.0, 1)

    interpretation = (
        f"Total 24h fluid: {round(total_24h, 1)} mL of Lactated Ringer's solution. "
        f"First 8 hours: {round(first_8h, 1)} mL ({rate_first_8h} mL/hr). "
        f"Next 16 hours: {round(next_16h, 1)} mL ({rate_next_16h} mL/hr). "
        f"Based on {params.weight_kg} kg and {params.tbsa_percent}% TBSA burn."
    )

    evidence = Evidence(
        source_doi="10.1016/S0039-6109(16)41607-7",
        level="Derivation & Validation Study",
        description="Fluid volume and electrolyte changes of the early postburn period (Baxter CR. Surg Clin North Am 1978)"
    )

    return ClinicalResult(
        value=total_24h,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="8710-0",  # LOINC approximation: fluid input 24h
        fhir_system="http://loinc.org",
        fhir_display="Fluid input 24 hour"
    )

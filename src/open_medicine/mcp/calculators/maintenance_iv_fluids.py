# Related guidelines: none
from pydantic import BaseModel, Field
from open_medicine.mcp.base import ClinicalResult, Evidence


class MaintenanceIVFluidsParams(BaseModel):
    """Parameters to calculate maintenance IV fluid rate using the Holliday-Segar method (4-2-1 rule)."""
    weight_kg: float = Field(
        ...,
        description="Patient body weight in kilograms",
        gt=0,
    )


def calculate_maintenance_iv_fluids(params: MaintenanceIVFluidsParams) -> ClinicalResult:
    """
    Calculates maintenance IV fluid requirements using the Holliday-Segar method.
    Provides both hourly (4-2-1 rule) and daily (100-50-20 rule) fluid rates.
    Reference: Holliday MA, Segar WE. Pediatrics. 1957;19(5):823-832.
    """
    weight = params.weight_kg

    # --- Hourly rate: 4-2-1 rule (mL/hr) ---
    # First 10 kg: 4 mL/kg/hr
    # Next 10 kg (11-20 kg): 2 mL/kg/hr
    # Each kg above 20 kg: 1 mL/kg/hr
    if weight <= 10:
        hourly_rate = 4.0 * weight
    elif weight <= 20:
        hourly_rate = 40.0 + 2.0 * (weight - 10.0)
    else:
        hourly_rate = 60.0 + 1.0 * (weight - 20.0)

    hourly_rate = round(hourly_rate, 1)

    # --- Daily rate: 100-50-20 rule (mL/day) ---
    # First 10 kg: 100 mL/kg/day
    # Next 10 kg (11-20 kg): 50 mL/kg/day
    # Each kg above 20 kg: 20 mL/kg/day
    if weight <= 10:
        daily_rate = 100.0 * weight
    elif weight <= 20:
        daily_rate = 1000.0 + 50.0 * (weight - 10.0)
    else:
        daily_rate = 1500.0 + 20.0 * (weight - 20.0)

    daily_rate = round(daily_rate, 1)

    interpretation = (
        f"Maintenance IV fluid rate: {hourly_rate} mL/hr ({daily_rate} mL/day). "
        f"Calculated using the Holliday-Segar 4-2-1 rule for a {weight} kg patient. "
        f"Administer as isotonic crystalloid (e.g., D5 0.2-0.45% NaCl with 20 mEq/L KCl). "
        f"Adjust for ongoing losses, fever, or reduced needs (e.g., post-operative, renal/cardiac impairment)."
    )

    evidence = Evidence(
        source_doi="10.1542/peds.19.5.823",
        level="Derivation Study",
        description=(
            "Holliday MA, Segar WE. The maintenance need for water in parenteral "
            "fluid therapy. Pediatrics. 1957;19(5):823-832."
        ),
    )

    return ClinicalResult(
        value=hourly_rate,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="8710-0",  # LOINC approximation: no exact code for maintenance fluid rate; 8710-0 = fluid input 24h volume
        fhir_system="http://loinc.org",
        fhir_display="Fluid input 24 hour",
    )

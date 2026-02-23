from typing import Optional
from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class HeparinDosingParams(BaseModel):
    """Parameters to calculate weight-based IV heparin dosing (Raschke protocol)."""
    weight_kg: float = Field(..., description="Body weight in kilograms")
    aptt: Optional[float] = Field(None, description="Current aPTT in seconds. If None, returns initial dosing only.")


def calculate_heparin_dosing(params: HeparinDosingParams) -> ClinicalResult:
    """
    Determines weight-based IV unfractionated heparin dosing using the
    Raschke protocol. Provides initial bolus/infusion and aPTT-based adjustments.
    Reference: Raschke et al. Ann Intern Med 1993.
    """
    weight = params.weight_kg
    aptt = params.aptt

    initial_bolus = round(80 * weight, 1)
    initial_infusion = round(18 * weight, 1)

    if aptt is None:
        interpretation = (
            f"Weight-based heparin protocol for {weight} kg patient: "
            f"Initial bolus: {initial_bolus} units IV, "
            f"Initial infusion: {initial_infusion} units/hr."
        )
        value = initial_infusion
    else:
        if aptt < 35:
            bolus = round(80 * weight, 1)
            rate_change = round(4 * weight, 1)
            new_infusion = round(initial_infusion + rate_change, 1)
            adjustment = (
                f"aPTT {aptt}s (<35s): Bolus {bolus} units IV, "
                f"increase infusion by {rate_change} units/hr (new rate: +4 units/kg/hr)."
            )
        elif aptt <= 45:
            bolus = round(40 * weight, 1)
            rate_change = round(2 * weight, 1)
            new_infusion = round(initial_infusion + rate_change, 1)
            adjustment = (
                f"aPTT {aptt}s (35-45s): Bolus {bolus} units IV, "
                f"increase infusion by {rate_change} units/hr (new rate: +2 units/kg/hr)."
            )
        elif aptt <= 70:
            adjustment = f"aPTT {aptt}s (46-70s): Therapeutic range. No change."
            new_infusion = initial_infusion
        elif aptt <= 90:
            rate_change = round(2 * weight, 1)
            new_infusion = round(initial_infusion - rate_change, 1)
            adjustment = (
                f"aPTT {aptt}s (71-90s): Decrease infusion by {rate_change} units/hr "
                f"(-2 units/kg/hr)."
            )
        else:
            rate_change = round(3 * weight, 1)
            new_infusion = round(initial_infusion - rate_change, 1)
            adjustment = (
                f"aPTT {aptt}s (>90s): Hold infusion for 1 hour, then decrease by "
                f"{rate_change} units/hr (-3 units/kg/hr)."
            )
        value = new_infusion

        interpretation = (
            f"Weight-based heparin protocol for {weight} kg patient. "
            f"Initial bolus: {initial_bolus} units IV, initial infusion: {initial_infusion} units/hr. "
            f"Adjustment: {adjustment}"
        )

    evidence = Evidence(
        source_doi="10.7326/0003-4819-119-9-199311010-00007",
        level="Validation Study",
        description="Raschke et al. Weight-based heparin dosing nomogram. Ann Intern Med 1993."
    )

    return ClinicalResult(
        value=value,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="3298-0",
        fhir_system="http://loinc.org",
        fhir_display="Heparin dose"
    )

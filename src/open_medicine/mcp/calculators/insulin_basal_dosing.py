from typing import Optional
from pydantic import BaseModel, Field
from open_medicine.mcp.base import ClinicalResult, Evidence


class InsulinBasalDosingParams(BaseModel):
    """Parameters for basal insulin initiation and titration in Type 2 DM."""
    weight_kg: float = Field(..., description="Body weight in kilograms")
    current_dose: Optional[float] = Field(
        None, description="Current basal insulin dose in units/day. If None, calculates starting dose."
    )
    fasting_glucose: Optional[float] = Field(
        None, description="Fasting blood glucose in mg/dL. Used for titration when current_dose is provided."
    )


def calculate_insulin_basal_dosing(params: InsulinBasalDosingParams) -> ClinicalResult:
    """
    Calculates basal insulin initiation dose or titration adjustment for Type 2 DM.
    Based on ADA Standards of Care 2024.
    Reference: ADA Standards of Care 2024. DOI: 10.2337/dc24-S009
    """
    evidence = Evidence(
        source_doi="10.2337/dc24-S009",
        level="Guideline",
        description="ADA Standards of Care in Diabetes 2024 — Pharmacologic Approaches to Glycemic Treatment"
    )

    # Starting dose calculation
    if params.current_dose is None:
        weight_based = round(0.2 * params.weight_kg, 1)
        recommended = max(10.0, weight_based)
        low_range = round(0.1 * params.weight_kg, 1)
        high_range = weight_based

        interpretation = (
            f"Basal insulin initiation: recommended starting dose is {recommended} units/day. "
            f"Weight-based range: {low_range}-{high_range} units/day "
            f"(0.1-0.2 units/kg/day for {params.weight_kg} kg). "
            f"Minimum starting dose is 10 units/day per ADA guidelines. "
            f"Titrate every 3-7 days based on fasting glucose targets (70-110 mg/dL)."
        )

        return ClinicalResult(
            value=recommended,
            interpretation=interpretation,
            evidence=evidence,
            # No specific LOINC for insulin dosing recommendation; approximate
            fhir_code="46716-4",  # LOINC approximation: medication dose recommendation
            fhir_system="http://loinc.org",
            fhir_display="Insulin dose"
        )

    # Titration
    current = params.current_dose

    if params.fasting_glucose is None:
        interpretation = (
            f"Current basal insulin dose is {current} units/day. "
            f"Provide fasting glucose to calculate titration adjustment."
        )
        return ClinicalResult(
            value=current,
            interpretation=interpretation,
            evidence=evidence,
            fhir_code="46716-4",
            fhir_system="http://loinc.org",
            fhir_display="Insulin dose"
        )

    fg = params.fasting_glucose

    if fg > 180:
        adjustment = 4
        new_dose = current + adjustment
        action = f"Increase by {adjustment} units"
        reason = f"fasting glucose {fg} mg/dL is significantly above target"
    elif fg >= 141:
        adjustment = 2
        new_dose = current + adjustment
        action = f"Increase by {adjustment} units"
        reason = f"fasting glucose {fg} mg/dL is above target"
    elif fg >= 111:
        adjustment = 1
        new_dose = current + adjustment
        action = f"Increase by {adjustment} unit"
        reason = f"fasting glucose {fg} mg/dL is slightly above target"
    elif fg >= 70:
        adjustment = 0
        new_dose = current
        action = "No change"
        reason = f"fasting glucose {fg} mg/dL is at target (70-110 mg/dL)"
    elif fg >= 54:
        adjustment = -2
        new_dose = max(current + adjustment, 0)
        action = f"Decrease by 2 units (or 10-20% reduction)"
        reason = f"fasting glucose {fg} mg/dL indicates hypoglycemia risk"
    else:
        adjustment = -4
        new_dose = max(current + adjustment, 0)
        action = f"Decrease by 4 units (or 20-40% reduction)"
        reason = f"fasting glucose {fg} mg/dL indicates significant hypoglycemia"

    new_dose = round(new_dose, 1)

    interpretation = (
        f"Current dose: {current} units/day. Fasting glucose: {fg} mg/dL. "
        f"{action} — {reason}. "
        f"Recommended new dose: {new_dose} units/day. "
        f"Reassess in 3-7 days."
    )

    return ClinicalResult(
        value=new_dose,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="46716-4",
        fhir_system="http://loinc.org",
        fhir_display="Insulin dose"
    )

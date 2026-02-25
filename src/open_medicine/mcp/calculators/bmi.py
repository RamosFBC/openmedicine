from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class BMIParams(BaseModel):
    """Parameters to calculate Body Mass Index (BMI)."""
    weight_kg: float = Field(..., description="Body weight in kilograms")
    height_cm: float = Field(..., description="Height in centimeters")


def calculate_bmi(params: BMIParams) -> ClinicalResult:
    """
    Calculates Body Mass Index (BMI).
    Formula: BMI = weight(kg) / height(m)²
    Reference: WHO classification.
    """
    height_m = params.height_cm / 100.0
    if height_m <= 0:
        return ClinicalResult(
            value=None,
            interpretation="Invalid height. Height must be greater than 0.",
            evidence=Evidence(source_doi="10.1016/S0140-6736(03)15268-3", level="Guideline", description="WHO Expert Consultation. Appropriate body-mass index for Asian populations and its implications for policy and intervention strategies. Lancet. 2004;363(9403):157-163."),
            fhir_code="39156-5",
            fhir_system="http://loinc.org",
            fhir_display="Body mass index (BMI) [Ratio]"
        )

    bmi = params.weight_kg / (height_m ** 2)
    bmi_rounded = round(bmi, 1)

    if bmi_rounded >= 40:
        category = "Obesity class III (≥40)"
    elif bmi_rounded >= 35:
        category = "Obesity class II (35-39.9)"
    elif bmi_rounded >= 30:
        category = "Obesity class I (30-34.9)"
    elif bmi_rounded >= 25:
        category = "Overweight (25-29.9)"
    elif bmi_rounded >= 18.5:
        category = "Normal weight (18.5-24.9)"
    else:
        category = "Underweight (<18.5)"

    interpretation = f"BMI is {bmi_rounded} kg/m². WHO category: {category}."

    evidence = Evidence(
        source_doi="10.1016/S0140-6736(03)15268-3",
        level="Guideline",
        description="WHO Expert Consultation. Appropriate body-mass index for Asian populations and its implications for policy and intervention strategies. Lancet. 2004;363(9403):157-163."
    )

    return ClinicalResult(
        value=bmi_rounded,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="39156-5",  # LOINC: Body mass index
        fhir_system="http://loinc.org",
        fhir_display="Body mass index (BMI) [Ratio]"
    )

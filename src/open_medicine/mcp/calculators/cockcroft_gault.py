# Related guidelines: kdigo_aki_2012 (definition_and_staging section)
from typing import Literal

from pydantic import BaseModel, Field

from open_medicine.mcp.base import ClinicalResult, Evidence


class CockcroftGaultParams(BaseModel):
    """Parameters to calculate the Cockcroft-Gault Creatinine Clearance (CrCl)."""
    age: int = Field(..., description="Age in years", ge=18, le=120)
    weight: float = Field(..., description="Weight in kg", gt=0, le=500)
    weight_type: Literal["actual"] = Field(
        ..., description="Weight basis; MVP supports actual body weight only"
    )
    is_female: bool = Field(..., description="Is the patient female?")
    serum_creatinine: float = Field(
        ..., description="Serum creatinine in mg/dL", gt=0, le=100
    )


def calculate_cockcroft_gault(params: CockcroftGaultParams) -> ClinicalResult:
    """
    Calculates the estimated Creatinine Clearance (CrCl) using the
    1976 Cockcroft-Gault equation. This is the global standard for
    renal medication dosage adjustments.
    (Cockcroft DW, Gault MH. Nephron. 1976;16(1):31-41)
    Returns a ClinicalResult with interpretation and evidence.
    """
    # Math: [(140 - Age) * Weight] / (72 * SCr) * [0.85 if female]
    base_calc = ((140 - params.age) * params.weight) / (72 * params.serum_creatinine)
    
    if params.is_female:
        base_calc *= 0.85
        
    crcl_rounded = round(base_calc, 1)

    interpretation = (
        f"Estimated Cockcroft-Gault CrCl is {crcl_rounded} mL/min using actual body weight. "
        "This estimate assumes stable serum creatinine, is not validated in acute kidney injury, "
        "and may be inaccurate at extremes of body size or muscle mass."
    )

    evidence = Evidence(
        source_doi="10.1159/000180580",
        level="Validation Study",
        description=(
            "Prediction of Creatinine Clearance from Serum Creatinine "
            "(Cockcroft DW, Gault MH, 1976)"
        ),
    )

    return ClinicalResult(
        value=crcl_rounded,
        component_breakdown={"weight_type": params.weight_type},
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="2160-0",
        fhir_system="http://loinc.org",
        fhir_display="Creatinine renal clearance"
    )

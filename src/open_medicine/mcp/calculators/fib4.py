import math
from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class FIB4Params(BaseModel):
    """Parameters to calculate the FIB-4 Index."""
    age: int = Field(..., description="Age in years")
    ast: float = Field(..., description="Aspartate aminotransferase (AST) in U/L")
    alt: float = Field(..., description="Alanine aminotransferase (ALT) in U/L")
    platelets: float = Field(..., description="Platelet count in 10^9/L")


def calculate_fib4(params: FIB4Params) -> ClinicalResult:
    """
    Calculates the FIB-4 Index for liver fibrosis staging.
    Reference: Sterling RK et al. Hepatology 2006.
    """
    if params.alt <= 0 or params.platelets <= 0:
        return ClinicalResult(
            value=None,
            interpretation="FIB-4 cannot be calculated: ALT and platelets must be > 0.",
            evidence=Evidence(
                source_doi="10.1002/hep.21178",
                level="Derivation & Validation Study",
                description="A Simple Noninvasive Index Can Predict Both Significant Fibrosis and Cirrhosis in Patients With Chronic Hepatitis C (Sterling RK et al. Hepatology 2006)"
            ),
            fhir_code="96154-5",
            fhir_system="http://loinc.org",
            fhir_display="FIB-4 index"  # LOINC approximation: fibrosis index
        )

    # FIB-4 = (Age × AST) / (Platelets × √ALT)
    fib4 = (params.age * params.ast) / (params.platelets * math.sqrt(params.alt))
    fib4 = round(fib4, 2)

    # Age validation warning
    age_warning = ""
    if params.age < 35 or params.age > 65:
        age_warning = " Note: FIB-4 is validated for ages 35-65; interpret with caution."

    # Interpretation
    if fib4 < 1.30:
        interpretation = f"FIB-4 index is {fib4}. Low risk of advanced fibrosis (F0-F1).{age_warning}"
    elif fib4 <= 2.67:
        interpretation = f"FIB-4 index is {fib4}. Indeterminate risk; further evaluation recommended.{age_warning}"
    else:
        interpretation = f"FIB-4 index is {fib4}. High risk of advanced fibrosis (F3-F4).{age_warning}"

    evidence = Evidence(
        source_doi="10.1002/hep.21178",
        level="Derivation & Validation Study",
        description="A Simple Noninvasive Index Can Predict Both Significant Fibrosis and Cirrhosis in Patients With Chronic Hepatitis C (Sterling RK et al. Hepatology 2006)"
    )

    return ClinicalResult(
        value=fib4,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="96154-5",
        fhir_system="http://loinc.org",
        fhir_display="FIB-4 index"
    )

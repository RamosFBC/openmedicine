from enum import Enum
from pydantic import BaseModel, Field
from open_medicine.mcp.base import ClinicalResult, Evidence

# Related guidelines: aasld_cirrhosis_2023 (staging, complications sections)


class AscitesGrade(str, Enum):
    NONE = "none"
    MILD = "mild"
    SEVERE = "severe"


class EncephalopathyGrade(str, Enum):
    NONE = "none"
    GRADE_1_2 = "grade_1_2"
    GRADE_3_4 = "grade_3_4"


class ChildPughParams(BaseModel):
    """Parameters to calculate the Child-Pugh Score."""
    bilirubin: float = Field(..., description="Total bilirubin in mg/dL")
    albumin: float = Field(..., description="Serum albumin in g/dL")
    inr: float = Field(..., description="International Normalized Ratio")
    ascites: AscitesGrade = Field(..., description="Ascites severity: none, mild (mild/moderate), severe (severe/refractory)")
    encephalopathy: EncephalopathyGrade = Field(..., description="Hepatic encephalopathy grade: none, grade_1_2, grade_3_4")
    is_primary_biliary_cholangitis: bool = Field(False, description="Use PBC-specific bilirubin thresholds")


def calculate_child_pugh(params: ChildPughParams) -> ClinicalResult:
    """
    Calculates the Child-Pugh score for hepatic function classification.
    Reference: Pugh RNH et al. Br J Surg. 1973.
    """
    score = 0

    # Bilirubin
    if params.is_primary_biliary_cholangitis:
        if params.bilirubin < 4:
            score += 1
        elif params.bilirubin <= 10:
            score += 2
        else:
            score += 3
    else:
        if params.bilirubin < 2:
            score += 1
        elif params.bilirubin <= 3:
            score += 2
        else:
            score += 3

    # Albumin
    if params.albumin > 3.5:
        score += 1
    elif params.albumin >= 2.8:
        score += 2
    else:
        score += 3

    # INR
    if params.inr < 1.7:
        score += 1
    elif params.inr <= 2.3:
        score += 2
    else:
        score += 3

    # Ascites
    if params.ascites == AscitesGrade.NONE:
        score += 1
    elif params.ascites == AscitesGrade.MILD:
        score += 2
    else:
        score += 3

    # Encephalopathy
    if params.encephalopathy == EncephalopathyGrade.NONE:
        score += 1
    elif params.encephalopathy == EncephalopathyGrade.GRADE_1_2:
        score += 2
    else:
        score += 3

    # Classification
    if score <= 6:
        child_class = "A"
        survival = "~100%"
    elif score <= 9:
        child_class = "B"
        survival = "~80%"
    else:
        child_class = "C"
        survival = "~45%"

    interpretation = (
        f"Child-Pugh score is {score} (Class {child_class}). "
        f"Estimated 1-year survival: {survival}."
    )

    evidence = Evidence(
        source_doi="10.1002/bjs.1800600817",
        level="Derivation & Validation Study",
        description="Transection of the oesophagus for bleeding oesophageal varices (Pugh RNH et al. Br J Surg. 1973)"
    )

    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="80204-3",
        fhir_system="http://loinc.org",
        fhir_display="Child-Pugh score"  # LOINC approximation: closest match for Child-Pugh
    )

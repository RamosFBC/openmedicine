from typing import Optional

from pydantic import BaseModel, Field

from open_medicine.mcp.base import ClinicalError, ClinicalResult, Evidence, ResultStatus


class CHADSVAScParams(BaseModel):
    congestive_heart_failure: Optional[bool] = Field(
        ...,
        description=(
            "Required congestive heart failure or left ventricular dysfunction status; "
            "use null when unknown."
        ),
    )
    hypertension: Optional[bool] = Field(
        ...,
        description="Required history of hypertension; use null when unknown.",
    )
    age: int = Field(
        ...,
        ge=0,
        le=120,
        description="Required patient age in completed years (0-120).",
    )
    diabetes: Optional[bool] = Field(
        ...,
        description="Required diabetes mellitus status; use null when unknown.",
    )
    stroke_tia_thromboembolism: Optional[bool] = Field(
        ...,
        description=(
            "Required history of stroke, TIA, or systemic thromboembolism; "
            "use null when unknown."
        ),
    )
    vascular_disease: Optional[bool] = Field(
        ...,
        description=(
            "Required vascular disease status (prior myocardial infarction, peripheral "
            "artery disease, or aortic plaque); use null when unknown."
        ),
    )
    female_sex: Optional[bool] = Field(
        ...,
        description="Required female sex-category status; use null when unknown.",
    )


def calculate_chadsvasc(params: CHADSVAScParams) -> ClinicalResult:
    component_names = (
        "congestive_heart_failure",
        "hypertension",
        "diabetes",
        "stroke_tia_thromboembolism",
        "vascular_disease",
        "female_sex",
    )
    raw = {name: getattr(params, name) for name in component_names}
    components = {
        name: None if value is None else int(value)
        for name, value in raw.items()
    }
    if params.age >= 75:
        components["age"] = 2
    elif params.age >= 65:
        components["age"] = 1
    else:
        components["age"] = 0

    if params.stroke_tia_thromboembolism is True:
        components["stroke_tia_thromboembolism"] = 2

    unknown = [name for name, value in raw.items() if value is None]
    evidence = Evidence(
        source_doi="10.1161/CIR.0000000000001193",
        level="Clinical Guideline",
        description="2023 ACC/AHA/ACCP/HRS atrial fibrillation guideline.",
    )
    if unknown:
        return ClinicalResult(
            status=ResultStatus.INSUFFICIENT_DATA,
            value=None,
            component_breakdown=components,
            errors=[
                ClinicalError(
                    code="insufficient_data",
                    message="One or more components are unknown.",
                    details={"unknown_components": unknown},
                )
            ],
            interpretation=(
                "CHA2DS2-VASc score cannot be calculated until all components "
                "are known."
            ),
            evidence=evidence,
        )

    score = sum(components.values())
    return ClinicalResult(
        value=score,
        component_breakdown=components,
        interpretation=(
            f"CHA2DS2-VASc score is {score}; component contributions are provided "
            "in the breakdown."
        ),
        evidence=evidence,
        fhir_code="79423-0",
        fhir_system="http://loinc.org",
        fhir_display="CHA2DS2-VASc score",
    )

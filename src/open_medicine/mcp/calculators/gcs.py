from typing import Optional

from pydantic import BaseModel, Field, model_validator

from open_medicine.mcp.base import ClinicalError, ClinicalResult, Evidence, ResultStatus


class GCSParams(BaseModel):
    eye_response: Optional[int] = Field(
        None,
        ge=1,
        le=4,
        description=(
            "Eye response score: 1=none, 2=to pressure, 3=to sound, "
            "4=spontaneous; or null when the component is non-testable; "
            "provide eye_non_testable_reason when null."
        ),
    )
    eye_non_testable_reason: Optional[str] = Field(
        None,
        description=(
            "Reason the eye component is non-testable (for example, orbital swelling); "
            "required when eye_response is null, otherwise null."
        ),
    )
    verbal_response: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description=(
            "Verbal response score: 1=none, 2=sounds, 3=words, 4=confused, "
            "5=orientated; or null when the component is non-testable; "
            "provide verbal_non_testable_reason when null."
        ),
    )
    verbal_non_testable_reason: Optional[str] = Field(
        None,
        description=(
            "Reason the verbal component is non-testable (for example, intubation); "
            "required when verbal_response is null, otherwise null."
        ),
    )
    motor_response: Optional[int] = Field(
        None,
        ge=1,
        le=6,
        description=(
            "Motor response score: 1=none, 2=extension, 3=abnormal flexion, "
            "4=normal flexion, 5=localising, 6=obey commands; or null when the "
            "component is non-testable; "
            "provide motor_non_testable_reason when null."
        ),
    )
    motor_non_testable_reason: Optional[str] = Field(
        None,
        description=(
            "Reason the motor component is non-testable (for example, paralysis); "
            "required when motor_response is null, otherwise null."
        ),
    )

    @model_validator(mode="after")
    def score_xor_reason(self):
        for name in ("eye", "verbal", "motor"):
            score = getattr(self, f"{name}_response")
            reason = getattr(self, f"{name}_non_testable_reason")
            if (score is None) == (reason is None or not reason.strip()):
                raise ValueError(
                    f"{name} requires exactly one of score or non-testable reason"
                )
        return self


_TERMS = {
    "eye": {4: "spontaneous", 3: "to sound", 2: "to pressure", 1: "none"},
    "verbal": {5: "orientated", 4: "confused", 3: "words", 2: "sounds", 1: "none"},
    "motor": {
        6: "obey commands",
        5: "localising",
        4: "normal flexion",
        3: "abnormal flexion",
        2: "extension",
        1: "none",
    },
}


def calculate_gcs(params: GCSParams) -> ClinicalResult:
    components, scores = {}, []
    for name in ("eye", "verbal", "motor"):
        score = getattr(params, f"{name}_response")
        reason = getattr(params, f"{name}_non_testable_reason")
        components[name] = {
            "score": score,
            "term": _TERMS[name].get(score),
            "non_testable_reason": reason,
        }
        if score is not None:
            scores.append(score)

    total = sum(scores) if len(scores) == 3 else None
    non_testable_components = {
        name: component["non_testable_reason"]
        for name, component in components.items()
        if component["non_testable_reason"] is not None
    }
    errors = []
    if non_testable_components:
        errors.append(
            ClinicalError(
                code="non_testable_component",
                message="One or more GCS components are non-testable.",
                details={"non_testable_components": non_testable_components},
            )
        )
    notation_parts = []
    for name, component in components.items():
        displayed_score = component["score"]
        if displayed_score is None:
            displayed_score = "NT"
        notation_parts.append(f"{name[0].upper()}{displayed_score}")
    notation = " ".join(notation_parts)

    if total is not None:
        interpretation = f"GCS components: {notation}. Total GCS is {total}."
    else:
        interpretation = (
            f"GCS components: {notation}. A total is not reported because at least "
            "one component is non-testable."
        )

    status = (
        ResultStatus.SUCCESS
        if total is not None
        else ResultStatus.INSUFFICIENT_DATA
    )
    return ClinicalResult(
        status=status,
        errors=errors,
        value=total,
        component_breakdown=components,
        interpretation=interpretation,
        evidence=Evidence(
            source_doi="10.1016/s0140-6736(74)91639-0",
            level="Derivation Study",
            description="Teasdale and Jennett Glasgow Coma Scale.",
        ),
        fhir_code="9269-2",
        fhir_system="http://loinc.org",
        fhir_display="Glasgow coma score total",
    )

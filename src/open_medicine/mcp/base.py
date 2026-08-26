from datetime import datetime, timezone
from enum import Enum
import json
import math
from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator


class Evidence(BaseModel):
    """Source evidence returned with a calculator result."""

    source_doi: Optional[str] = Field(
        None, description="The DOI of the original study or source"
    )
    authority: Optional[str] = None
    url: Optional[str] = None
    document_id: Optional[str] = None
    version_date: Optional[str] = None
    section: Optional[str] = None
    retrieved_at: Optional[str] = None
    content_hash: Optional[str] = None
    level: str = Field(description="Level of evidence, when available")
    description: str = Field(description="A brief description of the evidence")


class ResultStatus(str, Enum):
    SUCCESS = "success"
    INSUFFICIENT_DATA = "insufficient_data"
    ERROR = "error"


class ClinicalError(BaseModel):
    code: str
    message: str
    details: Any = None


class ClinicalResult(BaseModel):
    """Standard output for MCP medical calculators and clinical scores."""

    status: ResultStatus = ResultStatus.SUCCESS
    errors: list[ClinicalError] = Field(default_factory=list)
    value: Any = Field(description="The computed numeric or categorical value")
    component_breakdown: Optional[dict[str, Any]] = None
    interpretation: str = Field(description="Clinical interpretation of the result")
    evidence: Evidence = Field(description="The evidence backing this result")

    fhir_code: Optional[str] = Field(
        None, description="The specific FHIR code for this observation, such as LOINC"
    )
    fhir_system: Optional[str] = Field(
        None, description="The URL of the coding system, such as http://loinc.org"
    )
    fhir_display: Optional[str] = Field(
        None, description="The human-readable display of the code"
    )

    @model_validator(mode="after")
    def validate_status_contract(self):
        if self.status is ResultStatus.SUCCESS:
            if self.value is None:
                raise ValueError("SUCCESS results must include a value")
            if self.errors:
                raise ValueError("SUCCESS results must not include errors")
        else:
            if self.value is not None:
                raise ValueError(f"{self.status.name} results must not include a value")
            if not self.errors:
                raise ValueError(f"{self.status.name} results must include at least one error")
        return self

    def to_fhir(
        self, subject_reference: str, encounter_reference: Optional[str] = None
    ) -> dict:
        if not self.fhir_code or not self.fhir_system:
            raise ValueError("FHIR code and system are required")
        evidence_note = (
            f"Evidence: {self.evidence.description} | Level: {self.evidence.level}"
        )
        if self.evidence.source_doi:
            evidence_note += f" | DOI: {self.evidence.source_doi}"

        observation = {
            "resourceType": "Observation",
            "status": "final",
            "subject": {"reference": subject_reference},
            "effectiveDateTime": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "interpretation": [{"text": self.interpretation}],
            "note": [{"text": evidence_note}],
            "code": {
                "coding": [
                    {
                        "system": self.fhir_system,
                        "code": self.fhir_code,
                        "display": self.fhir_display or self.fhir_code,
                    }
                ]
            },
        }

        if self.status is ResultStatus.SUCCESS:
            if isinstance(self.value, bool):
                observation["valueBoolean"] = self.value
            elif isinstance(self.value, int):
                observation["valueInteger"] = self.value
            elif isinstance(self.value, float) and math.isfinite(self.value):
                observation["valueQuantity"] = {"value": self.value}
            elif isinstance(self.value, str):
                observation["valueString"] = self.value
            elif isinstance(self.value, (dict, list)):
                try:
                    observation["valueString"] = json.dumps(
                        self.value, sort_keys=True, separators=(",", ":"),
                        allow_nan=False,
                    )
                except (TypeError, ValueError) as exc:
                    raise ValueError("Unsupported FHIR observation value") from exc
            else:
                raise ValueError("Unsupported FHIR observation value")
        else:
            absent_code = (
                "not-performed"
                if self.status is ResultStatus.INSUFFICIENT_DATA
                else "error"
            )
            observation["dataAbsentReason"] = {
                "coding": [
                    {
                        "system": (
                            "http://terminology.hl7.org/CodeSystem/"
                            "data-absent-reason"
                        ),
                        "code": absent_code,
                    }
                ],
                "text": self.errors[0].message,
            }

        if encounter_reference:
            observation["encounter"] = {"reference": encounter_reference}

        return observation

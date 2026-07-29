from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    """Source evidence returned with a calculator result."""

    source_doi: str = Field(description="The DOI of the original study or source")
    level: str = Field(description="Level of evidence, when available")
    description: str = Field(description="A brief description of the evidence")


class ClinicalResult(BaseModel):
    """Standard output for MCP medical calculators and clinical scores."""

    value: Any = Field(description="The computed numeric or categorical value")
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

    def to_fhir(
        self, subject_reference: str, encounter_reference: Optional[str] = None
    ) -> dict:
        observation = {
            "resourceType": "Observation",
            "status": "final",
            "subject": {"reference": subject_reference},
            "effectiveDateTime": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "valueQuantity": {"value": self.value},
            "interpretation": [{"text": self.interpretation}],
            "note": [
                {
                    "text": (
                        f"Evidence: {self.evidence.description} | "
                        f"Level: {self.evidence.level} | "
                        f"DOI: {self.evidence.source_doi}"
                    )
                }
            ],
        }

        if encounter_reference:
            observation["encounter"] = {"reference": encounter_reference}

        if self.fhir_code and self.fhir_system:
            observation["code"] = {
                "coding": [
                    {
                        "system": self.fhir_system,
                        "code": self.fhir_code,
                        "display": self.fhir_display or self.fhir_code,
                    }
                ]
            }

        return observation

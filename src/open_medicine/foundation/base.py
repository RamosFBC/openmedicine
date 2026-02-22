from typing import Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class Evidence(BaseModel):
    """
    Evidence class to hold the scientific foundation of a clinical result.
    """
    source_doi: str = Field(description="The DOI of the original study or guideline")
    level: str = Field(description="Level of evidence (e.g., 1A, 2B, etc)")
    description: str = Field(description="A brief description of the evidence")

class ClinicalResult(BaseModel):
    """
    Standardizes the output of clinical tools (calculators, scores, guidelines).
    """
    value: Any = Field(description="The computed numeric or categorical value")
    interpretation: str = Field(description="Clinical interpretation of the result")
    evidence: Evidence = Field(description="The scientific evidence backing this result")
    
    # FHIR compliance metadata
    fhir_code: Optional[str] = Field(None, description="The specific FHIR code for this observation (e.g., LOINC)")
    fhir_system: Optional[str] = Field(None, description="The URL of the coding system (e.g., http://loinc.org)")
    fhir_display: Optional[str] = Field(None, description="The human-readable display of the code")

    def to_fhir(self, subject_reference: str, encounter_reference: Optional[str] = None) -> dict:
        """
        Converts the clinical result into a standard FHIR R4 Observation resource.
        The evidence is placed into the note element.
        """
        observation = {
            "resourceType": "Observation",
            "status": "final",
            "subject": {"reference": subject_reference},
            "effectiveDateTime": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "valueQuantity": {
                "value": self.value
            },
            "interpretation": [
                {
                    "text": self.interpretation
                }
            ],
            "note": [
                {
                    "text": f"Evidence: {self.evidence.description} | Level: {self.evidence.level} | DOI: {self.evidence.source_doi}"
                }
            ]
        }
        
        if encounter_reference:
            observation["encounter"] = {"reference": encounter_reference}
            
        if self.fhir_code and self.fhir_system:
            observation["code"] = {
                "coding": [
                    {
                        "system": self.fhir_system,
                        "code": self.fhir_code,
                        "display": self.fhir_display or self.fhir_code
                    }
                ]
            }
            
        return observation

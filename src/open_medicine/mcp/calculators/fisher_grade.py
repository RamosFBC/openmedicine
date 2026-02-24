from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class FisherGradeParams(BaseModel):
    """Parameters for the Fisher Grade CT classification of subarachnoid hemorrhage."""
    grade: int = Field(..., ge=1, le=4, description="Fisher Grade (1-4). 1=No blood on CT, 2=Diffuse thin (<1mm) SAH, 3=Localized clot/thick (>1mm) layer, 4=Intracerebral/intraventricular clot with diffuse or no SAH")


def calculate_fisher_grade(params: FisherGradeParams) -> ClinicalResult:
    """
    Calculates the Fisher Grade for CT classification of SAH and vasospasm risk.
    Reference: Fisher CM et al. Neurosurgery. 1980;6(1):1-9.
    """
    descriptions = {
        1: ("No blood detected on CT", "Low vasospasm risk"),
        2: ("Diffuse thin (<1mm) SAH", "Low-moderate vasospasm risk"),
        3: ("Localized clot and/or thick (>1mm) layer", "High vasospasm risk"),
        4: ("Intracerebral or intraventricular clot with diffuse or no SAH", "Low-moderate vasospasm risk"),
    }

    ct_finding, risk = descriptions[params.grade]

    evidence = Evidence(
        source_doi="Fisher CM et al. Neurosurgery 1980;6:1-9",
        level="Derivation & Validation Study",
        description="Relation of cerebral vasospasm to subarachnoid hemorrhage visualized by CT scanning (Fisher et al., 1980)"
    )

    interpretation = (
        f"Fisher Grade {params.grade}: {ct_finding}. {risk}."
    )

    return ClinicalResult(
        value=params.grade,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="LA9600-2",  # LOINC approximation: no exact Fisher Grade LOINC
        fhir_system="http://loinc.org",
        fhir_display="Fisher grade for subarachnoid hemorrhage"
    )

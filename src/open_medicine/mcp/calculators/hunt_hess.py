from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class HuntHessParams(BaseModel):
    """Parameters for the Hunt-Hess Scale grading of subarachnoid hemorrhage."""
    grade: int = Field(..., ge=1, le=5, description="Hunt-Hess Grade (1-5). 1=Asymptomatic/mild headache, 2=Moderate-severe headache/nuchal rigidity, 3=Drowsiness/confusion/mild focal deficit, 4=Stupor/moderate-severe hemiparesis, 5=Deep coma/decerebrate rigidity")


def calculate_hunt_hess(params: HuntHessParams) -> ClinicalResult:
    """
    Calculates the Hunt-Hess Scale for grading subarachnoid hemorrhage severity.
    Reference: Hunt WE, Hess RM. J Neurosurg. 1968;28:14-20.
    """
    descriptions = {
        1: ("Asymptomatic or mild headache, slight nuchal rigidity", "1%"),
        2: ("Moderate-to-severe headache, nuchal rigidity, no neurological deficit except cranial nerve palsy", "5%"),
        3: ("Drowsiness, confusion, or mild focal deficit", "19%"),
        4: ("Stupor, moderate-to-severe hemiparesis, possible early decerebrate rigidity", "42%"),
        5: ("Deep coma, decerebrate rigidity, moribund appearance", "77%"),
    }

    desc, mortality = descriptions[params.grade]

    evidence = Evidence(
        source_doi="10.3171/jns.1968.28.1.0014",
        level="Derivation & Validation Study",
        description="Hunt WE, Hess RM. Surgical risk as related to time of intervention in the repair of intracranial aneurysms. J Neurosurg. 1968;28(1):14-20."
    )

    interpretation = (
        f"Hunt-Hess Grade {params.grade}: {desc}. "
        f"Approximate surgical mortality: {mortality}."
    )

    return ClinicalResult(
        value=params.grade,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="LA9600-2",  # LOINC approximation: no exact Hunt-Hess LOINC; using SAH grading
        fhir_system="http://loinc.org",
        fhir_display="Hunt and Hess classification of subarachnoid hemorrhage"
    )

from pydantic import BaseModel, Field
from open_medicine.mcp.base import ClinicalResult, Evidence
from enum import Enum


class EdoxabanIndication(str, Enum):
    NVAF = "nvaf"
    VTE_TREATMENT = "vte_treatment"


class EdoxabanDosingParams(BaseModel):
    """Parameters to calculate Edoxaban (Savaysa) dosing."""
    crcl: float = Field(..., description="Estimated Creatinine Clearance (CrCl) in mL/min")
    weight_kg: float = Field(..., description="Body weight in kilograms")
    indication: EdoxabanIndication = Field(..., description="Clinical indication: nvaf or vte_treatment")
    concomitant_pgp_inhibitor: bool = Field(False, description="Concomitant use of a P-gp inhibitor")


def calculate_edoxaban_dosing(params: EdoxabanDosingParams) -> ClinicalResult:
    """
    Determines FDA-approved Edoxaban (Savaysa) dosage based on indication,
    renal function, weight, and concomitant P-gp inhibitor use.
    Reference: ENGAGE AF-TIMI 48 (Giugliano et al. NEJM 2013).
    """
    crcl = params.crcl
    weight = params.weight_kg
    ind = params.indication
    pgp = params.concomitant_pgp_inhibitor

    dose_str = ""

    if ind == EdoxabanIndication.NVAF:
        if crcl > 95:
            dose_str = "Not recommended. Edoxaban should not be used in NVAF patients with CrCl > 95 mL/min due to reduced efficacy."
        elif crcl > 50:
            dose_str = "60 mg once daily."
        elif 15 <= crcl <= 50:
            dose_str = "30 mg once daily (reduced dose for renal impairment)."
        else:
            dose_str = "Avoid. Not recommended when CrCl < 15 mL/min."

    elif ind == EdoxabanIndication.VTE_TREATMENT:
        # Dose reduction if CrCl 15-50, weight ≤60kg, or P-gp inhibitor
        needs_reduction = (15 <= crcl <= 50) or (weight <= 60) or pgp

        if crcl < 15:
            dose_str = "Avoid. Not recommended when CrCl < 15 mL/min."
        elif needs_reduction:
            reasons = []
            if 15 <= crcl <= 50:
                reasons.append("renal impairment")
            if weight <= 60:
                reasons.append(f"low body weight ({weight} kg)")
            if pgp:
                reasons.append("concomitant P-gp inhibitor")
            reason_str = ", ".join(reasons)
            dose_str = f"30 mg once daily (reduced due to {reason_str}), after 5-10 days of parenteral anticoagulant."
        else:
            dose_str = "60 mg once daily (after 5-10 days of parenteral anticoagulant)."

    interpretation = (
        f"With a CrCl of {crcl} mL/min, weight {weight} kg, for indication '{ind.value}'"
        f"{' with concomitant P-gp inhibitor' if pgp else ''}, "
        f"the recommended Edoxaban (Savaysa) dosage is: {dose_str}"
    )

    evidence = Evidence(
        source_doi="10.1056/NEJMoa1310907",
        level="Validation Study",
        description="ENGAGE AF-TIMI 48 trial & FDA Package Insert. Edoxaban dosing for NVAF and VTE."
    )

    return ClinicalResult(
        value=crcl,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="2160-0",
        fhir_system="http://loinc.org",
        fhir_display="Creatinine renal clearance"
    )

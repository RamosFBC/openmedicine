from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence
from enum import Enum


class DabigatranIndication(str, Enum):
    NVAF = "nvaf"
    VTE_TREATMENT = "vte_treatment"


class DabigatranDosingParams(BaseModel):
    """Parameters to calculate Dabigatran (Pradaxa) dosing."""
    crcl: float = Field(..., description="Estimated Creatinine Clearance (CrCl) in mL/min")
    indication: DabigatranIndication = Field(..., description="Clinical indication: nvaf or vte_treatment")
    concomitant_pgp_inhibitor: bool = Field(False, description="Concomitant use of a P-gp inhibitor (e.g., dronedarone, systemic ketoconazole)")


def calculate_dabigatran_dosing(params: DabigatranDosingParams) -> ClinicalResult:
    """
    Determines FDA-approved Dabigatran (Pradaxa) dosage based on indication,
    renal function, and concomitant P-gp inhibitor use.
    Reference: RE-LY trial (Connolly et al. NEJM 2009).
    """
    crcl = params.crcl
    ind = params.indication
    pgp = params.concomitant_pgp_inhibitor

    dose_str = ""

    if ind == DabigatranIndication.NVAF:
        if pgp:
            # With P-gp inhibitor (dronedarone, systemic ketoconazole)
            if crcl > 50:
                dose_str = "75 mg twice daily (dose reduced due to concomitant P-gp inhibitor)."
            elif 30 <= crcl <= 50:
                dose_str = "75 mg twice daily (dose reduced due to concomitant P-gp inhibitor and moderate renal impairment)."
            else:
                dose_str = "Avoid. Concomitant use with P-gp inhibitor is not recommended when CrCl < 30 mL/min."
        else:
            # Without P-gp inhibitor
            if crcl > 30:
                dose_str = "150 mg twice daily."
            elif 15 <= crcl <= 30:
                dose_str = "75 mg twice daily (reduced dose for severe renal impairment)."
            else:
                dose_str = "Avoid. Not recommended when CrCl < 15 mL/min."

    elif ind == DabigatranIndication.VTE_TREATMENT:
        if crcl >= 30:
            dose_str = "150 mg twice daily (after 5-10 days of parenteral anticoagulant therapy)."
        else:
            dose_str = "Avoid. Not recommended when CrCl < 30 mL/min for VTE treatment."

    interpretation = (
        f"With a CrCl of {crcl} mL/min for indication '{ind.value}'"
        f"{' with concomitant P-gp inhibitor' if pgp else ''}, "
        f"the recommended Dabigatran (Pradaxa) dosage is: {dose_str}"
    )

    evidence = Evidence(
        source_doi="10.1056/NEJMoa0905561",
        level="Validation Study",
        description="RE-LY trial & FDA Package Insert. Dabigatran dosing for NVAF and VTE with renal and P-gp inhibitor adjustments."
    )

    return ClinicalResult(
        value=crcl,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="2160-0",
        fhir_system="http://loinc.org",
        fhir_display="Creatinine renal clearance"
    )

from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class CorrectedCalciumParams(BaseModel):
    """Parameters to calculate albumin-corrected calcium."""
    calcium: float = Field(..., description="Measured serum calcium in mg/dL")
    albumin: float = Field(..., description="Serum albumin in g/dL")


def calculate_corrected_calcium(params: CorrectedCalciumParams) -> ClinicalResult:
    """
    Calculates albumin-corrected calcium.
    Corrected Ca = Measured Ca + 0.8 × (4.0 - Albumin)
    Reference: Payne RB et al. BMJ 1973.
    """
    corrected_ca = params.calcium + 0.8 * (4.0 - params.albumin)
    corrected_ca_rounded = round(corrected_ca, 1)

    parts = [f"Corrected calcium = {corrected_ca_rounded} mg/dL (measured {params.calcium}, albumin {params.albumin})."]

    if corrected_ca_rounded > 10.5:
        parts.append("Hypercalcemia (>10.5 mg/dL). Consider hyperparathyroidism, malignancy, vitamin D excess, or granulomatous disease.")
    elif corrected_ca_rounded >= 8.5:
        parts.append("Normal corrected calcium (8.5-10.5 mg/dL).")
    else:
        parts.append("Hypocalcemia (<8.5 mg/dL). Consider hypoparathyroidism, vitamin D deficiency, CKD, or pancreatitis.")

    evidence = Evidence(
        source_doi="10.1136/bmj.4.5893.643",
        level="Derivation & Validation Study",
        description="Payne RB et al. Interpretation of serum calcium in patients with abnormal serum proteins. BMJ 1973."
    )

    return ClinicalResult(
        value=corrected_ca_rounded,
        interpretation=" ".join(parts),
        evidence=evidence,
        fhir_code="29265-6",  # LOINC: Calcium corrected for albumin in Serum or Plasma
        fhir_system="http://loinc.org",
        fhir_display="Calcium.albumin corrected [Mass/volume] in Serum or Plasma"
    )

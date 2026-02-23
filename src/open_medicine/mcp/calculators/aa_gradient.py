from typing import Optional
from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class AaGradientParams(BaseModel):
    """Parameters to calculate the Alveolar-arterial (A-a) oxygen gradient."""
    fio2: float = Field(..., description="Fraction of inspired oxygen (e.g. 0.21 for room air)")
    pao2: float = Field(..., description="Arterial partial pressure of oxygen (PaO2) in mmHg")
    paco2: float = Field(..., description="Arterial partial pressure of carbon dioxide (PaCO2) in mmHg")
    atmospheric_pressure: float = Field(760.0, description="Atmospheric pressure in mmHg (default 760 at sea level)")
    age: Optional[int] = Field(None, description="Age in years. Used to estimate normal A-a gradient (≈ Age/4 + 4).")


def calculate_aa_gradient(params: AaGradientParams) -> ClinicalResult:
    """
    Calculates the Alveolar-arterial (A-a) oxygen gradient.
    A-a = [FiO2 × (Patm - 47) - (PaCO2 / 0.8)] - PaO2
    Reference: Standard respiratory physiology (alveolar gas equation).
    """
    # Alveolar oxygen: PAO2 = FiO2 × (Patm - PH2O) - PaCO2/R
    pao2_alveolar = params.fio2 * (params.atmospheric_pressure - 47.0) - (params.paco2 / 0.8)
    aa_gradient = pao2_alveolar - params.pao2
    aa_rounded = round(aa_gradient, 1)

    # Interpretation
    parts = [f"A-a gradient is {aa_rounded} mmHg."]

    if params.age is not None:
        expected_upper = round(params.age / 4.0 + 4.0, 1)
        parts.append(f"Expected normal upper limit for age {params.age}: ~{expected_upper} mmHg.")
        if aa_rounded > expected_upper:
            parts.append("Elevated A-a gradient. Consider V/Q mismatch, shunt, or diffusion impairment.")
        else:
            parts.append("Normal A-a gradient for age. If hypoxia is present, consider hypoventilation or low FiO2.")
    else:
        # General interpretation without age
        if aa_rounded > 15:
            parts.append("Elevated (>15 mmHg on room air). Consider V/Q mismatch, shunt, or diffusion impairment.")
        else:
            parts.append("Within normal range. If hypoxia is present, consider hypoventilation or low FiO2.")

    interpretation = " ".join(parts)

    evidence = Evidence(
        source_doi="10.1016/B978-0-323-55942-7.00041-1",
        level="Textbook Reference",
        description="Alveolar gas equation. Standard respiratory physiology reference."
    )

    return ClinicalResult(
        value=aa_rounded,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="19994-3",  # LOINC: Oxygen.alveolar-arterial difference
        fhir_system="http://loinc.org",
        fhir_display="Oxygen.alveolar - arterial [Partial pressure] difference in Unspecified specimen"
    )

from typing import Optional
from pydantic import BaseModel, Field
from open_medicine.mcp.base import ClinicalResult, Evidence


class WintersFormulaParams(BaseModel):
    """Parameters for Winter's formula (expected pCO2 in metabolic acidosis)."""
    bicarbonate: float = Field(..., description="Serum bicarbonate (HCO3) in mEq/L")
    paco2: Optional[float] = Field(None, description="Measured arterial pCO2 in mmHg. If provided, compares actual vs expected.")


def calculate_winters_formula(params: WintersFormulaParams) -> ClinicalResult:
    """
    Calculates expected pCO2 in metabolic acidosis using Winter's formula.
    Expected pCO2 = 1.5 × HCO3 + 8 (±2)
    Reference: Albert MS et al. Ann Intern Med 1967.
    """
    expected_pco2 = 1.5 * params.bicarbonate + 8.0
    expected_pco2_rounded = round(expected_pco2, 1)
    lower = round(expected_pco2 - 2, 1)
    upper = round(expected_pco2 + 2, 1)

    parts = [f"Expected pCO2 = {expected_pco2_rounded} mmHg (range {lower}-{upper})."]

    if params.paco2 is not None:
        parts.append(f"Measured pCO2 = {params.paco2} mmHg.")
        if params.paco2 > upper:
            parts.append("Measured pCO2 is above expected range. Concurrent respiratory acidosis (inadequate respiratory compensation).")
        elif params.paco2 < lower:
            parts.append("Measured pCO2 is below expected range. Concurrent respiratory alkalosis (superimposed hyperventilation).")
        else:
            parts.append("Measured pCO2 is within expected range. Appropriate respiratory compensation for metabolic acidosis.")

    evidence = Evidence(
        source_doi="10.7326/0003-4819-66-2-312",
        level="Derivation & Validation Study",
        description="Albert MS et al. Quantitative displacement of acid-base equilibrium in metabolic acidosis. Ann Intern Med 1967."
    )

    return ClinicalResult(
        value=expected_pco2_rounded,
        interpretation=" ".join(parts),
        evidence=evidence,
        fhir_code="2021-4",  # LOINC: Carbon dioxide [Partial pressure] in Arterial blood
        fhir_system="http://loinc.org",
        fhir_display="Carbon dioxide [Partial pressure] in Arterial blood"
    )

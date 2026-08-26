from pydantic import BaseModel, Field
from open_medicine.mcp.base import ClinicalError, ClinicalResult, Evidence, ResultStatus


class NAFLDFibrosisParams(BaseModel):
    """Parameters to calculate the NAFLD Fibrosis Score (NFS)."""
    age: int = Field(..., description="Age in years")
    bmi: float = Field(..., description="Body mass index in kg/m²")
    impaired_fasting_glucose_or_diabetes: bool = Field(..., description="Impaired fasting glucose or diagnosed diabetes")
    ast: float = Field(..., description="Aspartate aminotransferase (AST) in U/L")
    alt: float = Field(..., description="Alanine aminotransferase (ALT) in U/L")
    platelets: float = Field(..., description="Platelet count in 10^9/L")
    albumin: float = Field(..., description="Serum albumin in g/dL")


def calculate_nafld_fibrosis(params: NAFLDFibrosisParams) -> ClinicalResult:
    """
    Calculates the NAFLD Fibrosis Score (NFS).
    Reference: Angulo P et al. Hepatology 2007.
    """
    if params.alt <= 0:
        return ClinicalResult(
            status=ResultStatus.ERROR,
            errors=[ClinicalError(code="invalid_alt", message="ALT must be greater than 0.")],
            value=None,
            interpretation="NFS cannot be calculated: ALT must be > 0.",
            evidence=Evidence(
                source_doi="10.1002/hep.21496",
                level="Derivation & Validation Study",
                description="The NAFLD Fibrosis Score: A Noninvasive System That Identifies Liver Fibrosis in Patients with NAFLD (Angulo P et al. Hepatology 2007)"
            ),
            fhir_code="96155-2",
            fhir_system="http://loinc.org",
            fhir_display="NAFLD fibrosis score"
        )

    ifg_dm = 1.0 if params.impaired_fasting_glucose_or_diabetes else 0.0
    ast_alt_ratio = params.ast / params.alt

    nfs = (
        -1.675
        + 0.037 * params.age
        + 0.094 * params.bmi
        + 1.13 * ifg_dm
        + 0.99 * ast_alt_ratio
        - 0.013 * params.platelets
        - 0.66 * params.albumin
    )
    nfs = round(nfs, 3)

    if nfs < -1.455:
        interpretation = f"NAFLD Fibrosis Score is {nfs}. Low probability of advanced fibrosis (F0-F2)."
    elif nfs <= 0.676:
        interpretation = f"NAFLD Fibrosis Score is {nfs}. Indeterminate; further evaluation recommended."
    else:
        interpretation = f"NAFLD Fibrosis Score is {nfs}. High probability of advanced fibrosis (F3-F4)."

    evidence = Evidence(
        source_doi="10.1002/hep.21496",
        level="Derivation & Validation Study",
        description="The NAFLD Fibrosis Score: A Noninvasive System That Identifies Liver Fibrosis in Patients with NAFLD (Angulo P et al. Hepatology 2007)"
    )

    return ClinicalResult(
        value=nfs,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="96155-2",
        fhir_system="http://loinc.org",
        fhir_display="NAFLD fibrosis score"
    )

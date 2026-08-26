import json
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field

from open_medicine.mcp.base import ClinicalError, ClinicalResult, Evidence, ResultStatus


class RenalMetric(str, Enum):
    CRCL = "crcl"
    EGFR = "egfr"


class RenalDoseAdjustmentParams(BaseModel):
    """Parameters for renal dose adjustment lookup."""
    drug_name: str = Field(
        ..., description="Generic drug name (e.g., 'vancomycin', 'gabapentin')"
    )
    renal_value: float = Field(
        ...,
        ge=0,
        description="Renal function value (CrCl in mL/min or eGFR in mL/min/1.73m2)",
    )
    renal_metric: RenalMetric = Field(
        ..., description="Which renal metric is provided: 'crcl' or 'egfr'"
    )
    strict_metric: bool = Field(
        True,
        description="Reject a renal metric other than the product label metric",
    )


# Load drug database once at module level
_DATA_PATH = Path(__file__).parent / "data" / "renal_dose_adjustments.json"
with open(_DATA_PATH) as f:
    _DRUG_DB: dict = json.load(f)


def _get_unit(metric: RenalMetric) -> str:
    return "mL/min" if metric == RenalMetric.CRCL else "mL/min/1.73m2"


def _build_mismatch_warning(input_metric: RenalMetric, label_metric: str) -> str:
    label_name = "CrCl (Cockcroft-Gault)" if label_metric == "crcl" else "eGFR (CKD-EPI)"
    input_name = "eGFR (CKD-EPI)" if input_metric == RenalMetric.EGFR else "CrCl (Cockcroft-Gault)"
    return (
        f"FDA label specifies {label_name}. "
        f"{input_name} was provided. Values may diverge in elderly, obese, "
        f"or malnourished patients. Consider calculating {label_name} for this drug."
    )


def calculate_renal_dose_adjustment(params: RenalDoseAdjustmentParams) -> ClinicalResult:
    drug_key = params.drug_name.strip().lower()
    available_drugs = sorted(_DRUG_DB.keys())

    # Drug not found
    if drug_key not in _DRUG_DB:
        return ClinicalResult(
            status=ResultStatus.ERROR,
            errors=[
                ClinicalError(
                    code="drug_not_found",
                    message=f"Drug '{params.drug_name}' not found.",
                    details={"available_drugs": available_drugs},
                )
            ],
            value=None,
            interpretation=(
                f"Drug '{params.drug_name}' not found. Available drugs: "
                f"{', '.join(available_drugs)}"
            ),
            evidence=Evidence(
                source_doi=None,
                level="No evidence available",
                description="Drug not in renal dose adjustment database.",
            ),
        )

    drug = _DRUG_DB[drug_key]
    label_metric = drug["label_renal_metric"]
    metric_match = params.renal_metric.value == label_metric
    mismatch_warning = None
    if not metric_match:
        mismatch_warning = _build_mismatch_warning(params.renal_metric, label_metric)
    if not metric_match and params.strict_metric:
        return ClinicalResult(
            status=ResultStatus.ERROR,
            errors=[
                ClinicalError(
                    code="renal_metric_mismatch",
                    message=mismatch_warning,
                    details={
                        "provided_metric": params.renal_metric.value,
                        "required_metric": label_metric,
                    },
                )
            ],
            value=None,
            interpretation=mismatch_warning,
            evidence=Evidence(
                source_doi=drug["source_doi"],
                level=drug["evidence_level"],
                description=drug["source_description"],
            ),
        )

    # Find matching tier (tiers ordered descending by min, first match wins)
    matched_tier = None
    for tier in drug["tiers"]:
        tier_max = tier["max"] if tier["max"] is not None else float("inf")
        if tier["min"] <= params.renal_value <= tier_max:
            matched_tier = tier
            break

    # Should not happen if tiers cover 0-infinity, but handle gracefully
    if matched_tier is None:
        matched_tier = drug["tiers"][-1]  # fallback to lowest tier

    # Build renal category label
    tier_max_label = str(matched_tier["max"]) if matched_tier["max"] is not None else "+"
    metric_label = "CrCl" if label_metric == "crcl" else "eGFR"
    renal_category = f"{metric_label} {matched_tier['min']}-{tier_max_label}"

    value = {
        "drug_name": drug["drug_name"],
        "brand_names": drug["brand_names"],
        "drug_class": drug["drug_class"],
        "renal_input": {
            "metric": params.renal_metric.value,
            "value": params.renal_value,
            "unit": _get_unit(params.renal_metric),
        },
        "label_renal_metric": label_metric,
        "metric_match": metric_match,
        "metric_mismatch_warning": mismatch_warning,
        "renal_category": renal_category,
        "normal_dose": drug["normal_dose"],
        "adjusted_dose": matched_tier["dose"],
        "adjustment_type": matched_tier["adjustment_type"],
        "requires_tdm": drug["requires_tdm"],
        "monitoring_parameters": drug.get("monitoring_parameters"),
        "dialysis_note": matched_tier.get("dialysis_note"),
        "hepatic_interaction_flag": drug.get("hepatic_interaction_flag", False),
        "warnings": matched_tier.get("warnings", []),
    }

    interpretation = (
        f"For {drug['drug_name']} ({', '.join(drug['brand_names'])}) with "
        f"{params.renal_metric.value.upper()} {params.renal_value} "
        f"{_get_unit(params.renal_metric)}: "
        f"Recommended dose: {matched_tier['dose']}. "
        f"Adjustment: {matched_tier['adjustment_type']}."
    )
    if mismatch_warning:
        interpretation += f" WARNING: {mismatch_warning}"
    if matched_tier.get("dialysis_note"):
        interpretation += f" Dialysis: {matched_tier['dialysis_note']}."

    evidence = Evidence(
        source_doi=drug["source_doi"],
        level=drug["evidence_level"],
        description=drug["source_description"],
    )

    return ClinicalResult(
        value=value,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="29463-7",
        fhir_system="http://loinc.org",
        fhir_display="Medication dose",
    )

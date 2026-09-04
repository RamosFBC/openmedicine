import json
import math
from enum import Enum
from importlib.resources import files

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
        allow_inf_nan=False,
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
_DATA_RESOURCE = files("open_medicine.mcp.calculators").joinpath(
    "data/renal_dose_adjustments.json"
)
_DRUG_DB: dict = json.loads(_DATA_RESOURCE.read_text(encoding="utf-8"))


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


def _select_tier(tiers: list[dict], renal_value: float) -> dict:
    """Select a continuous renal tier by its inclusive lower threshold."""
    invalid = not tiers
    if not invalid:
        try:
            mins = [tier["min"] for tier in tiers]
            invalid = (
                any(
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(value)
                    or value < 0
                    for value in mins
                )
                or mins != sorted(mins, reverse=True)
                or len(set(mins)) != len(mins)
                or mins[-1] != 0
                or tiers[0]["max"] is not None
                or any(
                    isinstance(lower["max"], bool)
                    or not isinstance(lower["max"], (int, float))
                    or not math.isfinite(lower["max"])
                    or lower["max"] != higher["min"] - 1
                    for higher, lower in zip(tiers, tiers[1:])
                )
            )
        except (KeyError, TypeError):
            invalid = True
    if invalid:
        raise ValueError("Invalid renal tier configuration")

    for tier in tiers:
        if renal_value >= tier["min"]:
            return tier
    raise ValueError("Invalid renal tier configuration")


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
    matched_tier = _select_tier(drug["tiers"], params.renal_value)

    # Express the continuous thresholds used for selection, rather than the
    # legacy integer-only max labels stored in the source data.
    metric_label = "CrCl" if label_metric == "crcl" else "eGFR"
    tier_index = drug["tiers"].index(matched_tier)
    if tier_index == 0:
        renal_category = f"{metric_label} >= {matched_tier['min']}"
    else:
        upper_threshold = drug["tiers"][tier_index - 1]["min"]
        renal_category = (
            f"{matched_tier['min']} <= {metric_label} < {upper_threshold}"
        )

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
    )

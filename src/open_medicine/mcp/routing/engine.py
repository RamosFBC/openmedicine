"""Clinical routing engine — assess a clinical scenario and recommend tools to run."""
import json
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from open_medicine.foundation.base import ClinicalResult, Evidence


class ScenarioParams(BaseModel):
    """Parameters for clinical scenario assessment."""
    conditions: list[str] = Field(..., description="List of clinical conditions/presentations (e.g., ['atrial_fibrillation', 'ckd'])")
    age: Optional[int] = Field(None, description="Patient age in years")
    sex: Optional[str] = Field(None, description="Patient sex ('male' or 'female')")
    medications: Optional[list[str]] = Field(None, description="Current medications")


_RULES_PATH = Path(__file__).parent / "data" / "rules.json"
with open(_RULES_PATH, "r", encoding="utf-8") as f:
    _RULES: dict = json.load(f)


def assess_clinical_scenario(params: ScenarioParams) -> ClinicalResult:
    """Assess a clinical scenario and return prioritized tool recommendations."""
    condition_rules = _RULES.get("condition_rules", {})

    all_actions: list[dict[str, Any]] = []
    all_warnings: list[str] = []
    matched_conditions: list[str] = []

    for condition in params.conditions:
        condition_lower = condition.strip().lower()
        if condition_lower in condition_rules:
            rule = condition_rules[condition_lower]
            matched_conditions.append(condition_lower)
            all_actions.extend(rule["actions"])
            all_warnings.extend(rule.get("warnings", []))

    # Deduplicate actions by tool_id, keeping lowest priority
    seen_tools: dict[str, dict[str, Any]] = {}
    for action in all_actions:
        tid = action["tool_id"]
        if tid not in seen_tools or action["priority"] < seen_tools[tid]["priority"]:
            seen_tools[tid] = action

    # Re-sort and re-number priorities
    deduped = sorted(seen_tools.values(), key=lambda a: a["priority"])
    for i, action in enumerate(deduped, 1):
        action["priority"] = i

    # Deduplicate warnings
    unique_warnings = list(dict.fromkeys(all_warnings))

    value = {
        "matched_conditions": matched_conditions,
        "recommended_actions": deduped,
        "warnings": unique_warnings,
    }

    if matched_conditions:
        interpretation = (
            f"Clinical scenario assessment for: {', '.join(matched_conditions)}. "
            f"{len(deduped)} recommended actions identified. "
            f"Execute in priority order for systematic evaluation."
        )
    else:
        interpretation = (
            f"No matching routing rules for conditions: {', '.join(params.conditions)}. "
            f"Consider using search_medical_knowledge to discover relevant tools."
        )

    evidence = Evidence(
        source_doi="10.1161/CIR.0000000000001193",
        level="Clinical Routing Engine",
        description="OpenMedicine deterministic routing rules based on clinical practice guidelines.",
    )

    return ClinicalResult(
        value=value,
        interpretation=interpretation,
        evidence=evidence,
    )

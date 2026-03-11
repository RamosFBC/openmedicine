"""Differential diagnosis engine — search and retrieve clinical differentials."""
import json
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from open_medicine.foundation.base import ClinicalResult, Evidence
from open_medicine.mcp.search_utils import tokenized_search


class DifferentialParams(BaseModel):
    """Parameters for retrieving a differential diagnosis."""
    differential_id: str = Field(..., description="The differential ID (e.g., 'chest_pain')")
    age: Optional[int] = Field(None, description="Patient age in years")
    sex: Optional[str] = Field(None, description="Patient sex ('male' or 'female')")


_DATA_DIR = Path(__file__).parent / "data"


def _load_all_differentials() -> dict[str, dict[str, Any]]:
    """Load all differential JSON files from the data directory."""
    differentials = {}
    for fp in _DATA_DIR.glob("*.json"):
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
        differentials[data["differential_id"]] = data
    return differentials


_DIFFERENTIAL_DB = _load_all_differentials()


def search_differentials(query: str) -> list[dict[str, Any]]:
    """Search differentials using tokenized matching with clinical synonym expansion."""
    items = []
    for diff_id, diff in _DIFFERENTIAL_DB.items():
        keywords = " ".join(k for k in diff.get("keywords", []))
        items.append({
            "differential_id": diff_id,
            "title": diff["title"],
            "description": diff["description"],
            "doi": diff["source_doi"],
            "searchable_text": f"{diff_id} {diff['title']} {diff['description']} {keywords}",
        })

    results = tokenized_search(query, items)
    for r in results:
        r.pop("_score", None)
    return results


def get_differential(params: DifferentialParams) -> ClinicalResult:
    """Retrieve a full differential diagnosis with ranked diagnoses."""
    if params.differential_id not in _DIFFERENTIAL_DB:
        available = sorted(_DIFFERENTIAL_DB.keys())
        return ClinicalResult(
            value={"status": "not_found", "available_differentials": available},
            interpretation=f"Differential '{params.differential_id}' not found. Available: {', '.join(available)}",
            evidence=Evidence(
                source_doi="N/A",
                level="N/A",
                description="Differential not in database.",
            ),
        )

    diff = _DIFFERENTIAL_DB[params.differential_id]

    # Build the diagnoses list with optional age/sex annotations
    diagnoses = []
    for dx in diff["diagnoses"]:
        entry = {
            "name": dx["name"],
            "likelihood": dx["likelihood"],
            "key_features": dx["key_features"],
            "red_flags": dx.get("red_flags", []),
            "recommended_tests": dx["recommended_tests"],
            "related_guidelines": dx.get("related_guidelines", []),
        }

        # Add contextual notes based on age/sex if modifiers exist
        notes = []
        if params.age and dx.get("age_modifier"):
            notes.append(f"Age context: {dx['age_modifier']}")
        if params.sex and dx.get("sex_modifier"):
            notes.append(f"Sex context: {dx['sex_modifier']}")
        if notes:
            entry["contextual_notes"] = notes

        diagnoses.append(entry)

    # Sort: must_not_miss first, then less_common, then common
    priority = {"must_not_miss": 0, "less_common": 1, "common": 2}
    diagnoses.sort(key=lambda d: priority.get(d["likelihood"], 99))

    also_consider = diff.get("also_consider", [])
    clinical_reasoning_prompt = diff.get("clinical_reasoning_prompt", "")

    value = {
        "differential_id": diff["differential_id"],
        "title": diff["title"],
        "diagnoses": diagnoses,
        "also_consider": also_consider,
        "clinical_reasoning_prompt": clinical_reasoning_prompt,
    }

    must_not_miss = [d["name"] for d in diagnoses if d["likelihood"] == "must_not_miss"]
    interpretation = (
        f"{diff['title']}: {len(diagnoses)} evidence-based diagnoses ranked by clinical priority. "
        f"Must-not-miss: {', '.join(must_not_miss)}. "
        f"Also consider {len(also_consider)} additional rare/atypical diagnoses listed in also_consider. "
        f"{clinical_reasoning_prompt}"
    )

    evidence = Evidence(
        source_doi=diff["source_doi"],
        level=diff["evidence_level"],
        description=diff["source_description"],
    )

    return ClinicalResult(
        value=value,
        interpretation=interpretation,
        evidence=evidence,
    )

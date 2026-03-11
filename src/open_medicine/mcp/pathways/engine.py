"""Treatment pathway engine — search and retrieve evidence-based treatment pathways."""
import json
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from open_medicine.foundation.base import ClinicalResult, Evidence
from open_medicine.mcp.search_utils import tokenized_search


class PathwayParams(BaseModel):
    """Parameters for retrieving a treatment pathway."""
    pathway_id: str = Field(..., description="The pathway ID (e.g., 'afib_anticoagulation')")
    contraindications: Optional[list[str]] = Field(None, description="List of contraindication keys (e.g., ['active_major_bleeding'])")


_DATA_DIR = Path(__file__).parent / "data"


def _load_all_pathways() -> dict[str, dict[str, Any]]:
    """Load all pathway JSON files from the data directory."""
    pathways = {}
    for fp in _DATA_DIR.glob("*.json"):
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
        pathways[data["pathway_id"]] = data
    return pathways


_PATHWAY_DB = _load_all_pathways()


def search_pathways(query: str) -> list[dict[str, Any]]:
    """Search pathways using tokenized matching with clinical synonym expansion."""
    items = []
    for pw_id, pw in _PATHWAY_DB.items():
        keywords = " ".join(k for k in pw.get("keywords", []))
        items.append({
            "pathway_id": pw_id,
            "title": pw["title"],
            "description": pw["description"],
            "doi": pw["source_doi"],
            "searchable_text": f"{pw_id} {pw['title']} {pw['description']} {keywords}",
        })

    results = tokenized_search(query, items)
    for r in results:
        r.pop("_score", None)
    return results


def get_pathway(params: PathwayParams) -> ClinicalResult:
    """Retrieve a full treatment pathway with decision tree."""
    if params.pathway_id not in _PATHWAY_DB:
        available = sorted(_PATHWAY_DB.keys())
        return ClinicalResult(
            value={"status": "not_found", "available_pathways": available},
            interpretation=f"Pathway '{params.pathway_id}' not found. Available: {', '.join(available)}",
            evidence=Evidence(
                source_doi="N/A",
                level="N/A",
                description="Pathway not in database.",
            ),
        )

    pw = _PATHWAY_DB[params.pathway_id]

    # Check contraindications
    warnings = []
    if params.contraindications:
        contra_map = pw.get("contraindication_warnings", {})
        for c in params.contraindications:
            if c in contra_map:
                warnings.append(contra_map[c])

    value = {
        "pathway_id": pw["pathway_id"],
        "title": pw["title"],
        "steps": pw["steps"],
        "contraindication_warnings": warnings,
    }

    interpretation = (
        f"{pw['title']}: {len(pw['steps'])} steps from assessment to treatment. "
        f"Follow decision points at each step to navigate the pathway."
    )
    if warnings:
        interpretation += f" WARNINGS: {'; '.join(warnings)}"

    evidence = Evidence(
        source_doi=pw["source_doi"],
        level=pw["evidence_level"],
        description=pw["source_description"],
    )

    return ClinicalResult(
        value=value,
        interpretation=interpretation,
        evidence=evidence,
    )

import json
import os
from pathlib import Path
from typing import Any

from open_medicine.foundation.base import ClinicalResult, Evidence
from open_medicine.mcp.search_utils import tokenized_search


# Resolve absolute paths relative to this package
_GUIDELINES_DIR = Path(__file__).resolve().parent.parent / "guidelines"
_REGISTRY_PATH = _GUIDELINES_DIR / "registry.json"
_CONTENT_DIR = _GUIDELINES_DIR / "content"


def _load_registry() -> list[dict[str, Any]]:
    """Load the guideline metadata registry from disk."""
    with open(_REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def search_guidelines(query: str) -> list[dict[str, Any]]:
    """
    Search the guideline registry by matching the query against
    guideline titles, topic keywords, organization, and id using
    tokenized matching with clinical synonym expansion.
    """
    registry = _load_registry()

    items = []
    for guideline in registry:
        topics = " ".join(t for t in guideline.get("topics", []))
        items.append({
            "guideline_id": guideline["id"],
            "title": guideline["title"],
            "doi": guideline["doi"],
            "year": guideline.get("year"),
            "organization": guideline.get("organization"),
            "available_sections": guideline["sections"],
            "searchable_text": f"{guideline['id']} {guideline['title']} {guideline.get('organization', '')} {topics}",
        })

    results = tokenized_search(query, items)
    for r in results:
        r.pop("_score", None)
    return results


def retrieve_guideline(guideline_id: str, section: str) -> ClinicalResult:
    """
    Retrieve the curated content of a specific guideline section.
    Returns a ClinicalResult with the markdown text as interpretation
    and the guideline DOI as evidence.
    """
    registry = _load_registry()

    # Find the guideline metadata
    guideline_meta = None
    for g in registry:
        if g["id"] == guideline_id:
            guideline_meta = g
            break

    if guideline_meta is None:
        raise ValueError(
            f"Guideline '{guideline_id}' not found. "
            f"Available guidelines: {[g['id'] for g in registry]}"
        )

    if section not in guideline_meta["sections"]:
        raise ValueError(
            f"Section '{section}' not found in guideline '{guideline_id}'. "
            f"Available sections: {guideline_meta['sections']}"
        )

    # Read the content file
    content_path = _CONTENT_DIR / guideline_id / f"{section}.md"
    if not content_path.exists():
        raise FileNotFoundError(
            f"Content file not found: {content_path}. "
            f"The guideline section has not been curated yet."
        )

    with open(content_path, "r", encoding="utf-8") as f:
        content = f.read()

    evidence = Evidence(
        source_doi=guideline_meta["doi"],
        level="Clinical Practice Guideline",
        description=guideline_meta["title"]
    )

    return ClinicalResult(
        value=f"{guideline_id}/{section}",
        interpretation=content,
        evidence=evidence
    )

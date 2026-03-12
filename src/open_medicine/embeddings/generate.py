"""Generate embeddings for all searchable content in OpenMedicine.

Run: uv run python -m open_medicine.embeddings.generate
Requires: OPENAI_API_KEY environment variable.
"""
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx

from open_medicine.mcp.registry import CALCULATOR_REGISTRY
from open_medicine.mcp.differentials.engine import _DIFFERENTIAL_DB


_OUTPUT_PATH = Path(__file__).parent / "data" / "embeddings.json"


def _get_embeddings_batch(texts: list[str], api_key: str) -> list[list[float]]:
    """Get embeddings for a batch of texts from OpenAI API."""
    response = httpx.post(
        "https://api.openai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"input": texts, "model": "text-embedding-3-small"},
        timeout=60.0,
    )
    response.raise_for_status()
    data = response.json()["data"]
    # Sort by index to maintain order
    data.sort(key=lambda x: x["index"])
    return [d["embedding"] for d in data]


def _collect_items() -> list[dict[str, Any]]:
    """Collect all searchable items with their text."""
    items = []

    # Calculators
    for calc_id, tool in CALCULATOR_REGISTRY.items():
        items.append({
            "id": calc_id,
            "domain": "calculator",
            "text": f"{calc_id}: {tool.description}",
        })

    # Guidelines
    from open_medicine.mcp.guideline_engine import _load_registry
    for g in _load_registry():
        topics = ", ".join(g.get("topics", []))
        items.append({
            "id": g["id"],
            "domain": "guideline",
            "text": f"{g['id']}: {g['title']}. Topics: {topics}",
        })

    # Differentials
    for diff_id, diff in _DIFFERENTIAL_DB.items():
        keywords = ", ".join(diff.get("keywords", []))
        items.append({
            "id": diff_id,
            "domain": "differential",
            "text": f"{diff_id}: {diff['title']}. {diff['description']}. Keywords: {keywords}",
        })

    return items


def main() -> None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable required.", file=sys.stderr)
        sys.exit(1)

    items = _collect_items()
    print(f"Generating embeddings for {len(items)} items...")

    texts = [item["text"] for item in items]

    # Batch in groups of 100 (API limit is 2048)
    all_embeddings: list[list[float]] = []
    batch_size = 100
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        print(f"  Batch {i // batch_size + 1}: {len(batch)} items...")
        embeddings = _get_embeddings_batch(batch, api_key)
        all_embeddings.extend(embeddings)

    # Build output
    output = {}
    for item, embedding in zip(items, all_embeddings):
        output[item["id"]] = {
            "text": item["text"],
            "domain": item["domain"],
            "embedding": embedding,
        }

    # Write to file
    _OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f)

    print(f"Wrote {len(output)} embeddings to {_OUTPUT_PATH}")
    print(f"File size: {_OUTPUT_PATH.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()

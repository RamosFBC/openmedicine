"""Semantic search over pre-computed embeddings."""
import json
import math
import os
from pathlib import Path
from typing import Any, Optional


_DATA_PATH = Path(__file__).parent / "data" / "embeddings.json"


def load_embeddings() -> dict[str, Any]:
    """Load pre-computed embeddings from the shipped JSON file."""
    if not _DATA_PATH.exists():
        return {}
    with open(_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _get_query_embedding(query: str) -> Optional[list[float]]:
    """Get embedding for a query string via API. Returns None if no API key."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None

    import httpx
    response = httpx.post(
        "https://api.openai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"input": query, "model": "text-embedding-3-small"},
        timeout=10.0,
    )
    response.raise_for_status()
    return response.json()["data"][0]["embedding"]


def semantic_search(
    query: str,
    domain: str = "all",
    top_k: int = 10,
) -> Optional[list[dict[str, Any]]]:
    """
    Search pre-computed embeddings for items matching the query.

    Args:
        query: Search query string.
        domain: Filter by domain — 'calculator', 'guideline', 'differential',
                'pathway', or 'all'.
        top_k: Number of top results to return.

    Returns:
        List of ranked results with id, domain, text, and score.
        Returns None if embeddings or API are unavailable (signals fallback).
    """
    embeddings = load_embeddings()
    if not embeddings:
        return None

    query_embedding = _get_query_embedding(query)
    if query_embedding is None:
        return None

    scored = []
    for item_id, item in embeddings.items():
        if domain != "all" and item.get("domain") != domain:
            continue
        score = _cosine_similarity(query_embedding, item["embedding"])
        scored.append({
            "id": item_id,
            "domain": item.get("domain", "unknown"),
            "text": item.get("text", ""),
            "score": round(score, 4),
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]

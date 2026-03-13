from __future__ import annotations
import httpx

VOYAGE_API_URL = "https://api.voyageai.com/v1/embeddings"


def embed_texts(
    texts: list[str],
    api_key: str,
    model: str = "voyage-3-lite",
    input_type: str = "document",
    batch_size: int = 128,
) -> list[list[float]]:
    """Embed a list of texts using the Voyage AI API."""
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = httpx.post(
            VOYAGE_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "input": batch,
                "model": model,
                "input_type": input_type,
            },
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()["data"]
        all_embeddings.extend(item["embedding"] for item in data)

    return all_embeddings


def embed_query(
    text: str,
    api_key: str,
    model: str = "voyage-3-lite",
) -> list[float]:
    """Embed a single query text for similarity search."""
    results = embed_texts([text], api_key=api_key, model=model, input_type="query")
    return results[0]

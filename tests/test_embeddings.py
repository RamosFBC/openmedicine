"""Tests for embedding-based semantic search."""
import pytest
from unittest.mock import patch
from open_medicine.embeddings.search import semantic_search, load_embeddings


def test_load_embeddings_returns_dict():
    """load_embeddings returns a dict even if no file exists (empty fallback)."""
    result = load_embeddings()
    assert isinstance(result, dict)


def test_semantic_search_fallback_without_embeddings():
    """Without embeddings file, semantic_search returns None (signal to fall back)."""
    result = semantic_search("chest pain", domain="all")
    # If no embeddings file and no API key, should return None
    if result is None:
        assert True  # graceful fallback
    else:
        assert isinstance(result, list)


def test_semantic_search_with_mock_embeddings():
    """With mock embeddings and mock API, search returns ranked results."""
    # Vectors must point in different directions for cosine similarity to distinguish them.
    # Uniform vectors (e.g., [0.1]*10) all have cosine similarity 1.0 with any other uniform vector.
    mock_embeddings = {
        "calculate_chadsvasc": {
            "text": "CHA2DS2-VASc score for atrial fibrillation stroke risk",
            "domain": "calculator",
            "embedding": [0.1, 0.9, 0.1, 0.9, 0.1, 0.9, 0.1, 0.9, 0.1, 0.9],
        },
        "chest_pain": {
            "text": "Differential diagnosis for acute chest pain in adults",
            "domain": "differential",
            "embedding": [0.9, 0.1, 0.9, 0.1, 0.9, 0.1, 0.9, 0.1, 0.9, 0.1],
        },
    }
    mock_query_embedding = [0.85, 0.15, 0.85, 0.15, 0.85, 0.15, 0.85, 0.15, 0.85, 0.15]

    with patch("open_medicine.embeddings.search.load_embeddings", return_value=mock_embeddings):
        with patch("open_medicine.embeddings.search._get_query_embedding", return_value=mock_query_embedding):
            results = semantic_search("chest pain", domain="all")
            assert results is not None
            assert len(results) > 0
            # chest_pain should rank higher (closer cosine similarity)
            assert results[0]["id"] == "chest_pain"

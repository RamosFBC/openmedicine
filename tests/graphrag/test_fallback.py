import pytest
from unittest.mock import MagicMock, patch, call
from open_medicine.graphrag.reasoning.fallback import FallbackEngine
from open_medicine.graphrag.reasoning.types import ClinicalQuery, GraphRAGResult


class TestFallbackEngine:
    def test_returns_llm_synthesis_source(self):
        conn = MagicMock()
        # First call: vector search results, Second call: graph context
        conn.execute_read.side_effect = [
            [
                {
                    "ec_id": "c1", "ec_text": "Apixaban 5mg twice daily for AF.",
                    "ec_section": "dosing", "score": 0.92,
                    "g_title": "AF Guideline", "g_doi": "10.1/af",
                },
            ],
            [
                {
                    "text": "Apixaban 5mg twice daily for AF.",
                    "parent_text": "Full section on anticoagulation.",
                    "related_nodes": [],
                },
            ],
        ]
        engine = FallbackEngine(conn, voyage_api_key="test-key")

        with patch.object(engine, "_embed_query", return_value=[0.1, 0.2]):
            with patch.object(engine, "_synthesize") as mock_synth:
                mock_synth.return_value = "Based on the AF guideline, apixaban 5mg BID is recommended."
                result = engine.query(ClinicalQuery(intent="dosing", concepts=["apixaban"]))

        assert result.source == "llm_synthesis"
        assert result.synthesis is not None
        assert result.confidence == "medium"
        assert len(result.evidence) > 0

    def test_no_chunks_returns_low_confidence(self):
        conn = MagicMock()
        conn.execute_read.return_value = []
        engine = FallbackEngine(conn, voyage_api_key="test-key")

        with patch.object(engine, "_embed_query", return_value=[0.1]):
            result = engine.query(ClinicalQuery(intent="dosing", concepts=["unknowndrug"]))

        assert result.confidence == "low"
        assert result.synthesis is None

    def test_uses_vector_search_query(self):
        conn = MagicMock()
        conn.execute_read.return_value = []
        engine = FallbackEngine(conn, voyage_api_key="test-key")

        with patch.object(engine, "_embed_query", return_value=[0.1, 0.2]) as mock_embed:
            engine.query(ClinicalQuery(intent="dosing", concepts=["apixaban"]))

        mock_embed.assert_called_once()
        cypher_call = conn.execute_read.call_args[0][0]
        assert "vector" in cypher_call.lower()

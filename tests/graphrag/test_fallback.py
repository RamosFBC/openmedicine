import pytest
from unittest.mock import MagicMock, patch
from open_medicine.graphrag.reasoning.fallback import FallbackEngine
from open_medicine.graphrag.reasoning.types import ClinicalQuery, GraphRAGResult


class TestFallbackEngine:
    def test_returns_llm_synthesis_source(self):
        conn = MagicMock()
        # Mock vector search returning chunks
        conn.execute_read.return_value = [
            {
                "ec_id": "c1", "ec_text": "Apixaban 5mg twice daily for AF.",
                "ec_section": "dosing", "score": 0.92,
                "g_title": "AF Guideline", "g_doi": "10.1/af",
                "ln_page": 10,
            }
        ]
        engine = FallbackEngine(conn)
        query = ClinicalQuery(intent="dosing", concepts=["apixaban"])

        with patch.object(engine, "_synthesize") as mock_synth:
            mock_synth.return_value = "Based on the AF guideline, apixaban 5mg BID is recommended."
            result = engine.query(query)

        assert result.source == "llm_synthesis"
        assert result.synthesis is not None
        assert result.confidence == "medium"
        assert len(result.evidence) > 0

    def test_no_chunks_returns_low_confidence(self):
        conn = MagicMock()
        conn.execute_read.return_value = []
        engine = FallbackEngine(conn)
        query = ClinicalQuery(intent="dosing", concepts=["unknowndrug"])

        result = engine.query(query)
        assert result.confidence == "low"
        assert result.synthesis is None

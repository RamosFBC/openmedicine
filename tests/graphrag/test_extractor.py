import json
import time
import pytest
from unittest.mock import patch, MagicMock
from open_medicine.graphrag.ingestion.extractor import extract_logic_nodes, _call_llm_with_retry
from open_medicine.graphrag.graph.schema import LogicNodeType


MOCK_LLM_RESPONSE = json.dumps([
    {
        "id": "ln_test_001",
        "type": "contraindication",
        "conditions": [{"variable": "pregnancy", "operator": "==", "threshold": "true"}],
        "action": "contraindicated",
        "action_detail": "ACE inhibitors are contraindicated in pregnancy",
        "strength": "Strong/A",
        "guideline_id": "test_htn_2024",
        "page": 1,
        "concepts": [{"name": "lisinopril", "type": "drug"}],
    }
])


class TestExtractor:
    @patch("open_medicine.graphrag.ingestion.extractor._call_llm")
    def test_extracts_logic_node(self, mock_llm):
        mock_llm.return_value = MOCK_LLM_RESPONSE
        results = extract_logic_nodes(
            chunk_text="ACE inhibitors are contraindicated in pregnancy.",
            parent_context="1. Pharmacotherapy",
            guideline_id="test_htn_2024",
            page=1,
        )
        assert len(results) == 1
        assert results[0].logic_node.type == LogicNodeType.CONTRAINDICATION
        assert results[0].logic_node.action == "contraindicated"

    @patch("open_medicine.graphrag.ingestion.extractor._call_llm")
    def test_empty_chunk_returns_empty(self, mock_llm):
        mock_llm.return_value = "[]"
        results = extract_logic_nodes(
            chunk_text="This section describes general principles.",
            parent_context="Introduction",
            guideline_id="test_htn_2024",
            page=1,
        )
        assert len(results) == 0

    @patch("open_medicine.graphrag.ingestion.extractor._call_llm")
    def test_invalid_json_returns_empty(self, mock_llm):
        mock_llm.return_value = "not valid json"
        results = extract_logic_nodes(
            chunk_text="Some text.",
            parent_context="Section",
            guideline_id="g",
            page=1,
        )
        assert len(results) == 0

    @patch("open_medicine.graphrag.ingestion.extractor._call_llm")
    def test_invalid_schema_filtered_out(self, mock_llm):
        mock_llm.return_value = json.dumps([
            {"id": "bad", "type": "invalid_type", "action": "x"},
        ])
        results = extract_logic_nodes(
            chunk_text="Text.", parent_context="S",
            guideline_id="g", page=1,
        )
        assert len(results) == 0


class TestRetry:
    @patch("open_medicine.graphrag.ingestion.extractor._call_llm")
    def test_retries_on_rate_limit(self, mock_llm):
        import anthropic
        mock_llm.side_effect = [
            anthropic.RateLimitError("rate limited", response=MagicMock(status_code=429), body=None),
            "[]",
        ]
        result = _call_llm_with_retry("prompt", max_retries=3, base_delay=0.01)
        assert result == "[]"
        assert mock_llm.call_count == 2

    @patch("open_medicine.graphrag.ingestion.extractor._call_llm")
    def test_raises_after_max_retries(self, mock_llm):
        import anthropic
        mock_llm.side_effect = anthropic.RateLimitError(
            "rate limited", response=MagicMock(status_code=429), body=None,
        )
        with pytest.raises(anthropic.RateLimitError):
            _call_llm_with_retry("prompt", max_retries=2, base_delay=0.01)
        assert mock_llm.call_count == 2

    @patch("open_medicine.graphrag.ingestion.extractor._call_llm")
    def test_no_retry_on_other_errors(self, mock_llm):
        mock_llm.side_effect = ValueError("bad input")
        with pytest.raises(ValueError):
            _call_llm_with_retry("prompt", max_retries=3, base_delay=0.01)
        assert mock_llm.call_count == 1

"""Tests for unified MCP server — verify all 10 tools are listed."""
import pytest
import asyncio
import json
from unittest.mock import patch
from open_medicine.mcp.server import handle_list_tools, handle_call_tool


@pytest.fixture
def tools():
    return asyncio.get_event_loop().run_until_complete(handle_list_tools())


class TestToolRegistration:
    def test_tool_count(self, tools):
        """Should have 10 tools (2 calculator + 8 graph)."""
        assert len(tools) == 10

    def test_calculator_tools_present(self, tools):
        names = [t.name for t in tools]
        assert "search_clinical_calculators" in names
        assert "execute_clinical_calculator" in names

    def test_graph_tools_present(self, tools):
        names = [t.name for t in tools]
        assert "check_drug_dosing" in names
        assert "check_contraindications" in names
        assert "check_drug_interaction" in names
        assert "check_monitoring_requirements" in names
        assert "find_treatment_options" in names
        assert "query_clinical_graph" in names
        assert "fetch_evidence_chunk" in names
        assert "list_available_guidelines" in names

    def test_removed_tools_not_present(self, tools):
        """Guidelines, differentials, and semantic search removed."""
        names = [t.name for t in tools]
        assert "search_guidelines" not in names
        assert "retrieve_guideline" not in names
        assert "search_differential_diagnosis" not in names
        assert "get_differential_diagnosis" not in names
        assert "search_medical_knowledge" not in names


class TestCalculatorToolExecution:
    def test_search_calculators_returns_results(self):
        result = asyncio.get_event_loop().run_until_complete(
            handle_call_tool("search_clinical_calculators", {"query": "kidney"})
        )
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert "matches" in data

    def test_execute_unknown_calculator_returns_error(self):
        result = asyncio.get_event_loop().run_until_complete(
            handle_call_tool("execute_clinical_calculator", {
                "calculator_id": "nonexistent",
                "parameters": {}
            })
        )
        assert "Error" in result[0].text or "Unknown" in result[0].text


class TestGraphToolDegradation:
    def test_graph_tool_returns_unavailable_when_no_engine(self):
        with patch("open_medicine.mcp.graphrag_tools.get_graph_engine", return_value=None):
            result = asyncio.get_event_loop().run_until_complete(
                handle_call_tool("check_drug_dosing", {"drug": "lisinopril"})
            )
            data = json.loads(result[0].text)
            assert data["status"] == "unavailable"

    def test_unknown_tool_raises(self):
        with pytest.raises(ValueError, match="Unknown tool"):
            asyncio.get_event_loop().run_until_complete(
                handle_call_tool("nonexistent_tool", {})
            )

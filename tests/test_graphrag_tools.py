"""Tests for graphrag tool integration in unified MCP server."""
import pytest
from unittest.mock import MagicMock, patch


class TestGraphRAGToolsAvailability:
    def test_graphrag_tools_list_returns_8_tools(self):
        from open_medicine.mcp.graphrag_tools import GRAPHRAG_TOOL_DEFINITIONS
        assert len(GRAPHRAG_TOOL_DEFINITIONS) == 8

    def test_graphrag_tool_names(self):
        from open_medicine.mcp.graphrag_tools import GRAPHRAG_TOOL_DEFINITIONS
        names = [t["name"] for t in GRAPHRAG_TOOL_DEFINITIONS]
        assert "check_drug_dosing" in names
        assert "check_contraindications" in names
        assert "check_drug_interaction" in names
        assert "check_monitoring_requirements" in names
        assert "find_treatment_options" in names
        assert "query_clinical_graph" in names
        assert "fetch_evidence_chunk" in names
        assert "list_available_guidelines" in names


class TestGraphRAGEngineInit:
    def test_unavailable_message_returned_when_no_engine(self):
        from open_medicine.mcp.graphrag_tools import handle_graph_tool_call
        with patch("open_medicine.mcp.graphrag_tools.get_graph_engine", return_value=None):
            result = handle_graph_tool_call("check_drug_dosing", {"drug": "lisinopril"})
            assert "unavailable" in result.lower()

    def test_engine_available_with_mock_connection(self):
        from open_medicine.mcp.graphrag_tools import get_graph_engine
        mock_conn = MagicMock()
        with patch("open_medicine.mcp.graphrag_tools.GraphConnection", return_value=mock_conn), \
             patch("open_medicine.mcp.graphrag_tools.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="neo4j",
                neo4j_password="test",
            )
            engine = get_graph_engine(force_reinit=True)
            assert engine is not None

"""Tests for the calculator-only MCP server."""
import asyncio
import importlib.util
import json

import pytest

from open_medicine.mcp import ClinicalResult, Evidence
from open_medicine.mcp.server import handle_call_tool, handle_list_tools


@pytest.fixture
def tools():
    return asyncio.run(handle_list_tools())


class TestToolRegistration:
    def test_tool_count(self, tools):
        assert len(tools) == 2

    def test_calculator_tools_present(self, tools):
        names = [tool.name for tool in tools]
        assert names == ["search_clinical_calculators", "execute_clinical_calculator"]

    def test_non_calculator_tools_not_present(self, tools):
        names = [tool.name for tool in tools]
        removed_tools = {
            "search_guidelines",
            "retrieve_guideline",
            "search_differential_diagnosis",
            "get_differential_diagnosis",
            "search_medical_knowledge",
            "check_drug_dosing",
            "check_contraindications",
            "check_drug_interaction",
            "check_monitoring_requirements",
            "find_treatment_options",
            "query_clinical_graph",
            "fetch_evidence_chunk",
            "list_available_guidelines",
        }
        assert removed_tools.isdisjoint(names)

    def test_non_mcp_namespaces_not_packaged(self):
        assert importlib.util.find_spec("open_medicine.foundation") is None
        assert importlib.util.find_spec("open_medicine.workbench") is None

    def test_result_types_live_under_mcp_namespace(self):
        assert ClinicalResult.__module__ == "open_medicine.mcp.base"
        assert Evidence.__module__ == "open_medicine.mcp.base"


class TestCalculatorToolExecution:
    def test_search_calculators_returns_results(self):
        result = asyncio.run(
            handle_call_tool("search_clinical_calculators", {"query": "kidney"})
        )
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert "matches" in data
        assert data["matches"]

    def test_execute_calculator_returns_clinical_result(self):
        result = asyncio.run(
            handle_call_tool(
                "execute_clinical_calculator",
                {
                    "calculator_id": "calculate_bmi",
                    "parameters": {"weight_kg": 70, "height_cm": 175},
                },
            )
        )
        data = json.loads(result[0].text)
        assert data["value"] == pytest.approx(22.9, abs=0.01)
        assert data["evidence"]["source_doi"]

    def test_execute_unknown_calculator_returns_error(self):
        result = asyncio.run(
            handle_call_tool(
                "execute_clinical_calculator",
                {"calculator_id": "nonexistent", "parameters": {}},
            )
        )
        assert "Unknown calculator_id" in result[0].text

    def test_unknown_tool_raises(self):
        with pytest.raises(ValueError, match="Unknown tool"):
            asyncio.run(handle_call_tool("nonexistent_tool", {}))

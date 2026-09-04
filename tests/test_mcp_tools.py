"""Tests for the calculator-only MCP server."""
import asyncio
import importlib.util
import json

import pytest
import mcp.types as types

from open_medicine.mcp import ClinicalResult, Evidence
from open_medicine.mcp.server import handle_call_tool, handle_list_tools, server


def call_through_transport(name, arguments):
    request = types.CallToolRequest(
        params=types.CallToolRequestParams(name=name, arguments=arguments)
    )
    response = asyncio.run(server.request_handlers[types.CallToolRequest](request))
    return response.root


@pytest.fixture
def tools():
    return asyncio.run(handle_list_tools())


class TestToolRegistration:
    def test_tool_count(self, tools):
        assert len(tools) == 2

    def test_calculator_tools_present(self, tools):
        names = [tool.name for tool in tools]
        assert names == ["search_clinical_calculators", "execute_clinical_calculator"]

    def test_environment_allowlist_exposes_only_execution_tool(self, monkeypatch):
        monkeypatch.setenv(
            "OPEN_MEDICINE_MCP_TOOL_ALLOWLIST", "execute_clinical_calculator")
        names = [tool.name for tool in asyncio.run(handle_list_tools())]
        assert names == ["execute_clinical_calculator"]

    def test_unknown_or_empty_environment_allowlist_fails_closed(self, monkeypatch):
        for value in ("", "future_tool", "execute_clinical_calculator,future_tool"):
            monkeypatch.setenv("OPEN_MEDICINE_MCP_TOOL_ALLOWLIST", value)
            with pytest.raises(ValueError, match="tool allowlist"):
                asyncio.run(handle_list_tools())

    def test_calculator_scope_exposes_exact_gcs_execution_schema(self, monkeypatch):
        monkeypatch.setenv(
            "OPEN_MEDICINE_MCP_TOOL_ALLOWLIST", "execute_clinical_calculator")
        monkeypatch.setenv(
            "OPEN_MEDICINE_MCP_CALCULATOR_ID", "calculate_gcs")

        [tool] = asyncio.run(handle_list_tools())
        schema = tool.inputSchema
        assert tool.name == "execute_clinical_calculator"
        assert "calculate_gcs" in tool.description
        assert schema["required"] == ["calculator_id", "parameters"]
        assert "calculate_gcs" in schema["properties"]["calculator_id"]["description"]
        assert schema["properties"]["calculator_id"]["examples"] == ["calculate_gcs"]
        parameters = schema["properties"]["parameters"]
        assert parameters["anyOf"][1] == {}
        object_contract = parameters["anyOf"][0]
        assert object_contract["type"] == "object"
        assert object_contract["required"] == [
            "eye_response", "eye_non_testable_reason",
            "verbal_response", "verbal_non_testable_reason",
            "motor_response", "motor_non_testable_reason",
        ]
        assert set(object_contract["properties"]) == set(object_contract["required"])
        assert all(set(value) == {"description"}
                   for value in object_contract["properties"].values())
        assert "1=none" in object_contract["properties"]["eye_response"]["description"]
        assert "6=obey commands" in object_contract["properties"]["motor_response"]["description"]

    def test_invalid_calculator_scope_fails_closed(self, monkeypatch):
        for value in ("", "calculate_gcs,calculate_bmi", " calculate_gcs", "future"):
            monkeypatch.setenv("OPEN_MEDICINE_MCP_CALCULATOR_ID", value)
            with pytest.raises(ValueError, match="calculator scope"):
                asyncio.run(handle_list_tools())

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
    def test_environment_allowlist_rejects_hidden_tool_calls(self, monkeypatch):
        monkeypatch.setenv(
            "OPEN_MEDICINE_MCP_TOOL_ALLOWLIST", "execute_clinical_calculator")
        with pytest.raises(ValueError, match="not enabled"):
            asyncio.run(handle_call_tool(
                "search_clinical_calculators", {"query": "Glasgow"}))

    def test_calculator_scope_rejects_other_calculator(self, monkeypatch):
        monkeypatch.setenv("OPEN_MEDICINE_MCP_CALCULATOR_ID", "calculate_gcs")
        result = asyncio.run(handle_call_tool(
            "execute_clinical_calculator",
            {"calculator_id": "calculate_bmi", "parameters": {
                "weight_kg": 70, "height_cm": 175,
            }},
        ))
        assert result.isError is True
        assert result.structuredContent["errors"][0]["code"] == "calculator_not_enabled"

    def test_calculator_scope_requires_explicit_complete_payload(self, monkeypatch):
        monkeypatch.setenv("OPEN_MEDICINE_MCP_CALCULATOR_ID", "calculate_gcs")
        result = asyncio.run(handle_call_tool(
            "execute_clinical_calculator",
            {"calculator_id": "calculate_gcs", "parameters": {
                "eye_response": 4,
                "verbal_response": 5,
                "motor_response": 6,
            }},
        ))
        assert result.isError is True
        assert result.structuredContent["errors"][0]["code"] == "validation_error"

    def test_calculator_scope_executes_complete_gcs_payload(self, monkeypatch):
        monkeypatch.setenv("OPEN_MEDICINE_MCP_CALCULATOR_ID", "calculate_gcs")
        result = asyncio.run(handle_call_tool(
            "execute_clinical_calculator",
            {"calculator_id": "calculate_gcs", "parameters": {
                "eye_response": 4,
                "eye_non_testable_reason": None,
                "verbal_response": 5,
                "verbal_non_testable_reason": None,
                "motor_response": 6,
                "motor_non_testable_reason": None,
            }},
        ))
        assert result.isError is False
        assert result.structuredContent["value"] == 15

    def test_search_calculators_returns_results(self):
        result = call_through_transport("search_clinical_calculators", {"query": "kidney"})
        assert isinstance(result, types.CallToolResult)
        assert result.isError is False
        data = result.structuredContent
        assert "matches" in data
        assert data["matches"]
        assert json.loads(result.content[0].text) == data

    def test_execute_calculator_returns_clinical_result(self):
        result = call_through_transport(
                "execute_clinical_calculator",
                {
                    "calculator_id": "calculate_bmi",
                    "parameters": {"weight_kg": 70, "height_cm": 175},
                },
        )
        assert result.isError is False
        data = result.structuredContent
        assert data["value"] == pytest.approx(22.9, abs=0.01)
        assert data["evidence"]["source_doi"]

    def test_execute_unknown_calculator_returns_error(self):
        result = call_through_transport(
                "execute_clinical_calculator",
                {"calculator_id": "nonexistent", "parameters": {}},
        )
        assert result.isError is True
        assert result.structuredContent["errors"][0]["code"] == "unknown_calculator"

    def test_validation_error_is_safe_and_transport_error(self):
        secret = "do-not-echo-this-secret"
        result = call_through_transport(
            "execute_clinical_calculator",
            {"calculator_id": "calculate_bmi", "parameters": {
                "weight_kg": secret, "height_cm": 175,
            }},
        )
        serialized = json.dumps(result.structuredContent)
        assert result.isError is True
        assert result.structuredContent["errors"][0]["code"] == "validation_error"
        assert secret not in serialized
        assert "input" not in serialized and "ctx" not in serialized

    def test_execution_exception_is_transport_error(self, monkeypatch):
        tool = __import__("open_medicine.mcp.server", fromlist=["CALCULATOR_REGISTRY"]).CALCULATOR_REGISTRY["calculate_bmi"]
        monkeypatch.setattr(tool, "execute_function", lambda params: 1 / 0)
        result = call_through_transport(
            "execute_clinical_calculator",
            {"calculator_id": "calculate_bmi", "parameters": {
                "weight_kg": 70, "height_cm": 175,
            }},
        )
        assert result.isError is True
        assert result.structuredContent["errors"][0]["code"] == "execution_error"

    @pytest.mark.parametrize(
        "calculator_id,parameters,expected_status",
        [
            ("calculate_renal_dose_adjustment", {
                "drug_name": "not-a-drug", "renal_value": 50,
                "renal_metric": "crcl",
            }, "error"),
            ("calculate_gcs", {
                "eye_response": None, "eye_non_testable_reason": "swelling",
                "verbal_response": 5, "motor_response": 6,
            }, "insufficient_data"),
        ],
    )
    def test_clinical_failure_status_is_transport_error(
        self, calculator_id, parameters, expected_status
    ):
        result = call_through_transport(
            "execute_clinical_calculator",
            {"calculator_id": calculator_id, "parameters": parameters},
        )
        assert result.isError is True
        assert result.structuredContent["status"] == expected_status

    def test_unknown_tool_raises(self):
        with pytest.raises(ValueError, match="Unknown tool"):
            asyncio.run(handle_call_tool("nonexistent_tool", {}))

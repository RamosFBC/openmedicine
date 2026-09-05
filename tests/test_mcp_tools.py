"""Tests for the calculator-only MCP server."""
import asyncio
import copy
import importlib.util
import itertools
import json

import pytest
import mcp.types as types
from jsonschema import validate

from open_medicine.mcp import ClinicalResult, Evidence
from open_medicine.mcp.calculators.gcs import GCSParams, calculate_gcs
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
        assert schema["additionalProperties"] is False
        calculator_id = schema["properties"]["calculator_id"]
        assert calculator_id["type"] == "string"
        assert calculator_id["const"] == "calculate_gcs"
        assert "calculate_gcs" in calculator_id["description"]
        parameters = schema["properties"]["parameters"]
        assert parameters["type"] == "object"
        assert parameters["additionalProperties"] is False
        assert parameters["required"] == [
            "eye_response", "eye_non_testable_reason",
            "verbal_response", "verbal_non_testable_reason",
            "motor_response", "motor_non_testable_reason",
        ]
        assert set(parameters["properties"]) == set(parameters["required"])
        for component, maximum in (("eye", 4), ("verbal", 5), ("motor", 6)):
            score = parameters["properties"][f"{component}_response"]
            assert score["anyOf"] == [
                {"maximum": maximum, "minimum": 1, "type": "integer"},
                {"type": "null"},
            ]
            reason = parameters["properties"][f"{component}_non_testable_reason"]
            assert reason["anyOf"] == [
                {"maxLength": 256, "minLength": 1, "type": "string"},
                {"type": "null"},
            ]
        assert "1=none" in parameters["properties"]["eye_response"]["description"]
        assert "6=obey commands" in parameters["properties"]["motor_response"]["description"]

        output_schema = tool.outputSchema
        assert output_schema is not None
        assert output_schema["type"] == "object"
        assert output_schema["additionalProperties"] is False
        assert set(output_schema["required"]) == set(output_schema["properties"])

    def test_invalid_calculator_scope_fails_closed(self, monkeypatch):
        for value in ("", "calculate_gcs,calculate_bmi", " calculate_gcs", "future"):
            monkeypatch.setenv("OPEN_MEDICINE_MCP_CALCULATOR_ID", value)
            with pytest.raises(ValueError, match="calculator scope"):
                asyncio.run(handle_list_tools())

    def test_gcs_output_schema_accepts_entire_valid_domain(self, monkeypatch):
        monkeypatch.setenv("OPEN_MEDICINE_MCP_CALCULATOR_ID", "calculate_gcs")
        execute = next(
            tool for tool in asyncio.run(handle_list_tools())
            if tool.name == "execute_clinical_calculator"
        )
        validated = {"success": 0, "insufficient_data": 0}
        for eye, verbal, motor in itertools.product(
            [None, *range(1, 5)],
            [None, *range(1, 6)],
            [None, *range(1, 7)],
        ):
            scores = {"eye": eye, "verbal": verbal, "motor": motor}
            parameters = {}
            for name, score in scores.items():
                parameters[f"{name}_response"] = score
                parameters[f"{name}_non_testable_reason"] = (
                    None if score is not None else f"{name} blocked"
                )
            payload = calculate_gcs(GCSParams(**parameters)).model_dump(mode="json")
            validate(payload, execute.outputSchema)
            validated[payload["status"]] += 1

        assert validated == {"success": 120, "insufficient_data": 90}

    def test_non_gcs_calculator_scope_description_matches_selected_contract(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPEN_MEDICINE_MCP_CALCULATOR_ID", "calculate_bmi")
        execute = next(
            tool for tool in asyncio.run(handle_list_tools())
            if tool.name == "execute_clinical_calculator"
        )
        description = execute.inputSchema["properties"]["parameters"]["description"]
        assert "calculate_bmi" in execute.description
        assert "exactly 2 advertised" in description
        assert "GCS" not in description

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

        tool = next(
            tool for tool in asyncio.run(handle_list_tools())
            if tool.name == "execute_clinical_calculator"
        )
        validate(result.structuredContent, tool.outputSchema)

    def test_calculator_scope_rejects_invalid_server_output(self, monkeypatch):
        monkeypatch.setenv("OPEN_MEDICINE_MCP_CALCULATOR_ID", "calculate_gcs")
        tool = __import__(
            "open_medicine.mcp.server", fromlist=["CALCULATOR_REGISTRY"]
        ).CALCULATOR_REGISTRY["calculate_gcs"]

        class InvalidResult:
            def model_dump(self, *, mode):
                assert mode == "json"
                return {
                    "status": "success",
                    "errors": [],
                    "value": 999,
                    "unexpected": "must-not-cross-server-boundary",
                }

        monkeypatch.setattr(tool, "execute_function", lambda params: InvalidResult())
        result = call_through_transport(
            "execute_clinical_calculator",
            {"calculator_id": "calculate_gcs", "parameters": {
                "eye_response": 4,
                "eye_non_testable_reason": None,
                "verbal_response": 5,
                "verbal_non_testable_reason": None,
                "motor_response": 6,
                "motor_non_testable_reason": None,
            }},
        )

        assert result.isError is True
        assert result.structuredContent == {
            "status": "error",
            "errors": [{
                "code": "output_validation_error",
                "message": "Calculator output failed server validation.",
                "details": None,
            }],
        }
        assert "999" not in repr(result)
        assert "must-not-cross-server-boundary" not in repr(result)

    @pytest.mark.parametrize(
        "malformation",
        [
            "success_with_non_testable_component",
            "term_score_mismatch",
            "insufficient_all_scored",
            "wrong_total",
            "wrong_non_testable_component",
            "wrong_non_testable_reason",
        ],
    )
    def test_calculator_scope_rejects_semantically_invalid_server_output(
        self, monkeypatch, malformation
    ):
        monkeypatch.setenv("OPEN_MEDICINE_MCP_CALCULATOR_ID", "calculate_gcs")
        arguments = {"calculator_id": "calculate_gcs", "parameters": {
            "eye_response": 4,
            "eye_non_testable_reason": None,
            "verbal_response": 5,
            "verbal_non_testable_reason": None,
            "motor_response": 6,
            "motor_non_testable_reason": None,
        }}
        valid = asyncio.run(handle_call_tool(
            "execute_clinical_calculator", arguments
        )).structuredContent
        malformed = copy.deepcopy(valid)
        if malformation == "success_with_non_testable_component":
            malformed["component_breakdown"]["eye"] = {
                "score": None,
                "term": None,
                "non_testable_reason": "blocked",
            }
        elif malformation == "term_score_mismatch":
            malformed["component_breakdown"]["eye"]["term"] = "none"
        elif malformation == "insufficient_all_scored":
            malformed.update({
                "status": "insufficient_data",
                "errors": [{
                    "code": "non_testable_component",
                    "message": "One or more GCS components are non-testable.",
                    "details": {"non_testable_components": {"eye": "blocked"}},
                }],
                "value": None,
            })
        elif malformation == "wrong_total":
            malformed["value"] = 3
        else:
            malformed["component_breakdown"]["eye"] = {
                "score": None,
                "term": None,
                "non_testable_reason": "actual reason",
            }
            reported_component = (
                "motor" if malformation == "wrong_non_testable_component" else "eye"
            )
            malformed.update({
                "status": "insufficient_data",
                "errors": [{
                    "code": "non_testable_component",
                    "message": "One or more GCS components are non-testable.",
                    "details": {"non_testable_components": {
                        reported_component: "claimed reason",
                    }},
                }],
                "value": None,
            })

        tool = __import__(
            "open_medicine.mcp.server", fromlist=["CALCULATOR_REGISTRY"]
        ).CALCULATOR_REGISTRY["calculate_gcs"]

        class MalformedResult:
            def model_dump(self, *, mode):
                assert mode == "json"
                return malformed

        monkeypatch.setattr(tool, "execute_function", lambda params: MalformedResult())
        result = call_through_transport("execute_clinical_calculator", arguments)

        assert result.isError is True
        assert result.structuredContent["errors"][0]["code"] == "output_validation_error"
        assert "blocked" not in repr(result)

    def test_calculator_scope_returns_non_testable_gcs_as_successful_transport(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPEN_MEDICINE_MCP_CALCULATOR_ID", "calculate_gcs")
        result = call_through_transport(
            "execute_clinical_calculator",
            {"calculator_id": "calculate_gcs", "parameters": {
                "eye_response": None,
                "eye_non_testable_reason": "orbital swelling",
                "verbal_response": 5,
                "verbal_non_testable_reason": None,
                "motor_response": 6,
                "motor_non_testable_reason": None,
            }},
        )
        assert result.isError is False
        assert result.structuredContent["status"] == "insufficient_data"
        assert result.structuredContent["value"] is None
        tool = next(
            tool for tool in asyncio.run(handle_list_tools())
            if tool.name == "execute_clinical_calculator"
        )
        validate(result.structuredContent, tool.outputSchema)

    @pytest.mark.parametrize("invalid_score", ["4", 4.0, True])
    def test_calculator_scope_rejects_coerced_gcs_scores(
        self, monkeypatch, invalid_score
    ):
        monkeypatch.setenv("OPEN_MEDICINE_MCP_CALCULATOR_ID", "calculate_gcs")
        result = asyncio.run(handle_call_tool(
            "execute_clinical_calculator",
            {"calculator_id": "calculate_gcs", "parameters": {
                "eye_response": invalid_score,
                "eye_non_testable_reason": None,
                "verbal_response": 5,
                "verbal_non_testable_reason": None,
                "motor_response": 6,
                "motor_non_testable_reason": None,
            }},
        ))
        assert result.isError is True
        assert result.structuredContent["errors"][0]["code"] == "validation_error"

    @pytest.mark.parametrize("extra_location", ["top", "parameters"])
    def test_calculator_scope_rejects_unknown_fields(
        self, monkeypatch, extra_location
    ):
        monkeypatch.setenv("OPEN_MEDICINE_MCP_CALCULATOR_ID", "calculate_gcs")
        arguments = {"calculator_id": "calculate_gcs", "parameters": {
            "eye_response": 4,
            "eye_non_testable_reason": None,
            "verbal_response": 5,
            "verbal_non_testable_reason": None,
            "motor_response": 6,
            "motor_non_testable_reason": None,
        }}
        arguments["unexpected"] = "value"
        if extra_location == "parameters":
            arguments.pop("unexpected")
            arguments["parameters"]["unexpected"] = "value"
        result = asyncio.run(handle_call_tool("execute_clinical_calculator", arguments))
        assert result.isError is True
        assert result.structuredContent["errors"][0]["code"] == "validation_error"

    def test_transport_tool_cache_does_not_leak_environment_scope(self, monkeypatch):
        monkeypatch.setenv("OPEN_MEDICINE_MCP_CALCULATOR_ID", "calculate_gcs")
        asyncio.run(server.request_handlers[types.ListToolsRequest](None))
        monkeypatch.delenv("OPEN_MEDICINE_MCP_CALCULATOR_ID")

        result = call_through_transport(
            "execute_clinical_calculator",
            {"calculator_id": "calculate_bmi", "parameters": {
                "weight_kg": 70, "height_cm": 175,
            }},
        )

        assert result.isError is False
        assert result.structuredContent["value"] == pytest.approx(22.9, abs=0.01)

    def test_transport_refreshes_unscoped_cache_before_scoped_validation(
        self, monkeypatch
    ):
        monkeypatch.delenv("OPEN_MEDICINE_MCP_CALCULATOR_ID", raising=False)
        asyncio.run(server.request_handlers[types.ListToolsRequest](None))
        monkeypatch.setenv("OPEN_MEDICINE_MCP_CALCULATOR_ID", "calculate_gcs")

        result = call_through_transport(
            "execute_clinical_calculator",
            {"calculator_id": "calculate_gcs", "parameters": {
                "eye_response": "4",
                "eye_non_testable_reason": None,
                "verbal_response": 5,
                "verbal_non_testable_reason": None,
                "motor_response": 6,
                "motor_non_testable_reason": None,
            }},
        )

        assert result.isError is True
        assert result.structuredContent["errors"][0]["code"] == "validation_error"

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

    def test_clinical_error_status_is_transport_error(self):
        result = call_through_transport(
            "execute_clinical_calculator",
            {"calculator_id": "calculate_renal_dose_adjustment", "parameters": {
                "drug_name": "not-a-drug", "renal_value": 50,
                "renal_metric": "crcl",
            }},
        )
        assert result.isError is True
        assert result.structuredContent["status"] == "error"

    def test_valid_call_recovers_after_scoped_validation_failure(self, monkeypatch):
        monkeypatch.setenv("OPEN_MEDICINE_MCP_CALCULATOR_ID", "calculate_gcs")
        invalid = call_through_transport(
            "execute_clinical_calculator",
            {"calculator_id": "calculate_gcs", "parameters": {}},
        )
        valid = call_through_transport(
            "execute_clinical_calculator",
            {"calculator_id": "calculate_gcs", "parameters": {
                "eye_response": 4, "eye_non_testable_reason": None,
                "verbal_response": 5, "verbal_non_testable_reason": None,
                "motor_response": 6, "motor_non_testable_reason": None,
            }},
        )
        assert invalid.isError is True
        assert valid.isError is False
        assert valid.structuredContent["value"] == 15

    def test_unknown_tool_raises(self):
        with pytest.raises(ValueError, match="Unknown tool"):
            asyncio.run(handle_call_tool("nonexistent_tool", {}))

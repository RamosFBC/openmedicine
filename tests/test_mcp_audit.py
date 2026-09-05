import asyncio
import json
import stat

import pytest
import mcp.types as types

import open_medicine.mcp.server as server_module
from open_medicine.mcp.server import handle_list_tools, server


def _enable_scoped_audit(monkeypatch, path):
    monkeypatch.setenv("OPEN_MEDICINE_MCP_CALCULATOR_ID", "calculate_gcs")
    monkeypatch.setenv(
        "OPEN_MEDICINE_MCP_TOOL_ALLOWLIST", "execute_clinical_calculator"
    )
    monkeypatch.setenv("OPEN_MEDICINE_MCP_AUDIT_LOG_PATH", str(path))
    monkeypatch.setenv("OPEN_MEDICINE_MCP_AUDIT_LOG_ALLOWLIST", str(path))


def _valid_arguments():
    return {"calculator_id": "calculate_gcs", "parameters": {
        "eye_response": 4, "eye_non_testable_reason": None,
        "verbal_response": 5, "verbal_non_testable_reason": None,
        "motor_response": 6, "motor_non_testable_reason": None,
    }}


def _call_through_transport(name, arguments):
    request = types.CallToolRequest(
        params=types.CallToolRequestParams(name=name, arguments=arguments)
    )
    return asyncio.run(
        server.request_handlers[types.CallToolRequest](request)
    ).root


def test_audit_is_disabled_by_default(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPEN_MEDICINE_MCP_AUDIT_LOG_PATH", raising=False)
    monkeypatch.delenv("OPEN_MEDICINE_MCP_AUDIT_LOG_ALLOWLIST", raising=False)
    asyncio.run(handle_list_tools())
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("missing", ["path", "allowlist"])
def test_audit_requires_path_to_be_explicitly_allowlisted(
    monkeypatch, tmp_path, missing
):
    path = tmp_path / "audit.jsonl"
    monkeypatch.setenv("OPEN_MEDICINE_MCP_AUDIT_LOG_PATH", str(path))
    monkeypatch.setenv("OPEN_MEDICINE_MCP_AUDIT_LOG_ALLOWLIST", str(path))
    if missing == "path":
        monkeypatch.setenv(
            "OPEN_MEDICINE_MCP_AUDIT_LOG_PATH", str(tmp_path / "other.jsonl")
        )
    else:
        monkeypatch.delenv("OPEN_MEDICINE_MCP_AUDIT_LOG_ALLOWLIST")
    with pytest.raises(ValueError, match="audit log"):
        asyncio.run(handle_list_tools())
    assert not path.exists()


def test_audit_requires_exact_scoped_benchmark_server(monkeypatch, tmp_path):
    path = tmp_path / "audit.jsonl"
    monkeypatch.setenv("OPEN_MEDICINE_MCP_AUDIT_LOG_PATH", str(path))
    monkeypatch.setenv("OPEN_MEDICINE_MCP_AUDIT_LOG_ALLOWLIST", str(path))
    monkeypatch.delenv("OPEN_MEDICINE_MCP_CALCULATOR_ID", raising=False)
    with pytest.raises(ValueError, match="benchmark scope"):
        asyncio.run(handle_list_tools())
    monkeypatch.setenv("OPEN_MEDICINE_MCP_CALCULATOR_ID", "calculate_gcs")
    monkeypatch.setenv(
        "OPEN_MEDICINE_MCP_TOOL_ALLOWLIST", "search_clinical_calculators"
    )
    with pytest.raises(ValueError, match="benchmark scope"):
        asyncio.run(handle_list_tools())


def test_audit_logs_exact_bounded_calls_and_errors_privately(monkeypatch, tmp_path):
    path = tmp_path / "audit.jsonl"
    _enable_scoped_audit(monkeypatch, path)
    valid = _valid_arguments()
    asyncio.run(handle_list_tools())
    success = _call_through_transport("execute_clinical_calculator", valid)
    invalid = _valid_arguments()
    invalid["parameters"]["eye_response"] = "4"
    failure = _call_through_transport("execute_clinical_calculator", invalid)

    assert success.isError is False
    assert failure.isError is True
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    events = [json.loads(line) for line in path.read_text().splitlines()]
    event_names = [event["event"] for event in events]
    assert event_names.count("list_tools") >= 1
    assert event_names.count("call_received") == 2
    assert event_names.count("call_completed") == 2
    assert event_names.count("error") == 1
    received = [event for event in events if event["event"] == "call_received"]
    completed = [event for event in events if event["event"] == "call_completed"]
    errors = [event for event in events if event["event"] == "error"]
    assert all(event["timestamp"].endswith("Z") for event in events)
    assert received[0]["request"] == {
        "name": "execute_clinical_calculator", "arguments": valid,
    }
    assert completed[0]["result"]["structuredContent"]["value"] == 15
    assert errors[0]["result"]["isError"] is True


def test_audit_redacts_credential_fields_and_bounds_values(monkeypatch, tmp_path):
    path = tmp_path / "audit.jsonl"
    _enable_scoped_audit(monkeypatch, path)
    arguments = _valid_arguments()
    arguments["credential"] = "never-log-me"
    arguments["oversized"] = "x" * 1000
    _call_through_transport("execute_clinical_calculator", arguments)
    serialized = path.read_text()
    assert "never-log-me" not in serialized
    assert "x" * 513 not in serialized
    assert "[REDACTED]" in serialized


def test_audit_preserves_exact_insufficient_data_result(monkeypatch, tmp_path):
    path = tmp_path / "audit.jsonl"
    _enable_scoped_audit(monkeypatch, path)
    arguments = _valid_arguments()
    arguments["parameters"]["eye_response"] = None
    arguments["parameters"]["eye_non_testable_reason"] = "orbital swelling"
    result = _call_through_transport("execute_clinical_calculator", arguments)
    completed = [
        event for event in map(json.loads, path.read_text().splitlines())
        if event["event"] == "call_completed"
    ][0]
    assert result.isError is False
    assert result.structuredContent["status"] == "insufficient_data"
    assert completed["result"]["structuredContent"] == result.structuredContent


def test_audit_retries_short_writes(monkeypatch, tmp_path):
    path = tmp_path / "audit.jsonl"
    _enable_scoped_audit(monkeypatch, path)
    real_write = server_module.os.write

    def short_write(fd, data):
        return real_write(fd, data[:10])

    monkeypatch.setattr(server_module.os, "write", short_write)
    asyncio.run(handle_list_tools())
    events = [json.loads(line) for line in path.read_text().splitlines()]
    assert events[0]["event"] == "list_tools"

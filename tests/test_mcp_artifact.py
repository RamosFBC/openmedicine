from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
import stat

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from open_medicine.mcp.artifact import build_deterministic_zipapp, runtime_tree_sha256


ROOT = Path(__file__).parents[1]
SOURCE = ROOT / "src"
PYTHON = ROOT / ".venv/bin/python3"


def test_runtime_tree_hash_changes_for_any_runtime_byte(tmp_path):
    package = tmp_path / "open_medicine"
    package.mkdir()
    source = package / "__init__.py"
    source.write_text("VALUE = 1\n")
    before = runtime_tree_sha256(tmp_path)
    source.write_text("VALUE = 2\n")
    assert runtime_tree_sha256(tmp_path) != before


def test_deterministic_zipapp_is_byte_reproducible_and_source_bound(tmp_path):
    first = tmp_path / "first.pyz"
    second = tmp_path / "second.pyz"
    build_deterministic_zipapp(SOURCE, PYTHON, first)
    build_deterministic_zipapp(SOURCE, PYTHON, second)
    assert first.read_bytes() == second.read_bytes()
    assert hashlib.sha256(first.read_bytes()).hexdigest() == hashlib.sha256(second.read_bytes()).hexdigest()


def test_zipapp_live_stdio_lists_only_allowlisted_tool_and_executes_gcs(tmp_path):
    artifact = tmp_path / "open-medicine-mcp.pyz"
    audit_log = tmp_path / "synthetic-gcs-audit.jsonl"
    build_deterministic_zipapp(SOURCE, PYTHON, artifact)

    async def exercise():
        params = StdioServerParameters(
            command=str(artifact),
            env={
                "OPEN_MEDICINE_MCP_TOOL_ALLOWLIST": "execute_clinical_calculator",
                "OPEN_MEDICINE_MCP_CALCULATOR_ID": "calculate_gcs",
                "OPEN_MEDICINE_MCP_AUDIT_LOG_PATH": str(audit_log),
                "OPEN_MEDICINE_MCP_AUDIT_LOG_ALLOWLIST": str(audit_log),
            },
        )
        async with stdio_client(params) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                tools = await session.list_tools()
                result = await session.call_tool("execute_clinical_calculator", {
                    "calculator_id": "calculate_gcs",
                    "parameters": {
                        "eye_response": 4,
                        "eye_non_testable_reason": None,
                        "verbal_response": 5,
                        "verbal_non_testable_reason": None,
                        "motor_response": 6,
                        "motor_non_testable_reason": None,
                    },
                })
                return [tool.name for tool in tools.tools], result

    names, result = asyncio.run(exercise())
    assert names == ["execute_clinical_calculator"]
    assert result.isError is False
    assert result.structuredContent["value"] == 15
    assert stat.S_IMODE(audit_log.stat().st_mode) == 0o600
    events = [json.loads(line) for line in audit_log.read_text().splitlines()]
    event_names = [event["event"] for event in events]
    assert event_names[0] == "startup"
    assert "list_tools" in event_names
    assert "call_received" in event_names
    assert "call_completed" in event_names
    assert event_names[-1] == "shutdown"
    received = next(event for event in events if event["event"] == "call_received")
    completed = next(event for event in events if event["event"] == "call_completed")
    assert received["request"]["arguments"]["parameters"]["eye_response"] == 4
    assert completed["result"]["structuredContent"]["value"] == 15


def test_scoped_zipapp_never_reflects_rejected_values(tmp_path):
    artifact = tmp_path / "open-medicine-mcp.pyz"
    build_deterministic_zipapp(SOURCE, PYTHON, artifact)
    sentinel = "SENTINEL_SECRET_f93c"

    async def exercise():
        params = StdioServerParameters(
            command=str(artifact),
            env={
                "OPEN_MEDICINE_MCP_TOOL_ALLOWLIST": "execute_clinical_calculator",
                "OPEN_MEDICINE_MCP_CALCULATOR_ID": "calculate_gcs",
            },
        )
        async with stdio_client(params) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                return await session.call_tool("execute_clinical_calculator", {
                    "calculator_id": "calculate_gcs",
                    "parameters": {
                        "eye_response": sentinel,
                        "eye_non_testable_reason": None,
                        "verbal_response": 5,
                        "verbal_non_testable_reason": None,
                        "motor_response": 6,
                        "motor_non_testable_reason": None,
                    },
                })

    result = asyncio.run(exercise())
    persisted_surface = repr(result)
    assert result.isError is True
    assert sentinel not in persisted_surface
    assert "calculator parameters failed validation" in persisted_surface.lower()

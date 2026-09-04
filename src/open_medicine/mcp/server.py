import asyncio
import hashlib
import json
import os

from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types
from pydantic import ValidationError

from open_medicine import __version__
from open_medicine.mcp.registry import CALCULATOR_REGISTRY
from open_medicine.mcp.search_utils import tokenized_search


def _schema_hash(schema: dict) -> str:
    canonical = json.dumps(schema, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


def _error(code: str, message: str, details=None) -> dict:
    return {
        "status": "error",
        "errors": [{"code": code, "message": message, "details": details}],
    }


def _result(payload: dict, *, is_error: bool = False) -> types.CallToolResult:
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=json.dumps(payload, indent=2))],
        structuredContent=payload,
        isError=is_error,
    )


server = Server("open-medicine")
_TOOL_NAMES = frozenset({
    "search_clinical_calculators", "execute_clinical_calculator"})


def _enabled_tool_names() -> frozenset[str]:
    raw = os.environ.get("OPEN_MEDICINE_MCP_TOOL_ALLOWLIST")
    if raw is None:
        return _TOOL_NAMES
    values = raw.split(",")
    if (any(not value or value != value.strip() for value in values)
            or len(values) != len(set(values)) or not set(values) <= _TOOL_NAMES):
        raise ValueError("invalid OpenMedicine MCP tool allowlist")
    return frozenset(values)


def _scoped_calculator_id() -> str | None:
    raw = os.environ.get("OPEN_MEDICINE_MCP_CALCULATOR_ID")
    if raw is None:
        return None
    if (not raw or raw != raw.strip() or "," in raw
            or raw not in CALCULATOR_REGISTRY):
        raise ValueError("invalid OpenMedicine MCP calculator scope")
    return raw


def _execution_contract() -> tuple[str, dict]:
    calculator_id = _scoped_calculator_id()
    if calculator_id is None:
        return (
            "Executes a medical calculator by ID using a validated JSON parameter payload.",
            {
                "type": "object",
                "properties": {
                    "calculator_id": {
                        "type": "string",
                        "description": (
                            "The exact calculator ID returned by "
                            "search_clinical_calculators."
                        ),
                    },
                    "parameters": {
                        "type": "object",
                        "description": (
                            "A flat JSON payload matching the calculator's JSON Schema."
                        ),
                    },
                },
                "required": ["calculator_id", "parameters"],
            },
        )
    tool_def = CALCULATOR_REGISTRY[calculator_id]
    strict_parameters = json.loads(json.dumps(tool_def.schema))
    fields = list(tool_def.pydantic_model.model_fields)
    parameter_properties = {
        field: {
            "description": strict_parameters["properties"][field]["description"],
        }
        for field in fields
    }
    return (
        f"Executes the exact enabled calculator {calculator_id}. "
        "Use the advertised point-valued parameter contract; provide every field, "
        "using null only where its description permits it. Inputs are validated "
        "strictly by the server without echoing rejected values.",
        {
            "type": "object",
            "properties": {
                "calculator_id": {
                    "description": (
                        f"MUST be exactly {calculator_id}; do not substitute a synonym."
                    ),
                    "examples": [calculator_id],
                },
                "parameters": {
                    "description": (
                        "MUST be an object containing exactly the six advertised "
                        "GCS fields. Values are validated strictly by the server."
                    ),
                    "anyOf": [
                        {
                            "type": "object",
                            "properties": parameter_properties,
                            "required": fields,
                        },
                        {},
                    ],
                },
            },
            "required": ["calculator_id", "parameters"],
        },
    )


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    execution_description, execution_schema = _execution_contract()
    return [tool for tool in [
        types.Tool(
            name="search_clinical_calculators",
            description=(
                "Searches the calculator registry by keyword and returns calculator "
                "IDs with their required JSON Schemas."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Keywords to match against clinical calculators "
                            "(e.g. 'kidney function', 'stroke risk')."
                        ),
                    }
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="execute_clinical_calculator",
            description=execution_description,
            inputSchema=execution_schema,
        ),
    ] if tool.name in _enabled_tool_names()]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> types.CallToolResult:
    if name not in _TOOL_NAMES:
        raise ValueError(f"Unknown tool: {name}")
    if name not in _enabled_tool_names():
        raise ValueError(f"Tool is not enabled: {name}")
    args = arguments or {}

    if name == "search_clinical_calculators":
        query = args.get("query", "")
        items = [
            {
                "calculator_id": calc_id,
                "description": tool_def.description,
                "required_schema": tool_def.schema,
                "schema_hash": _schema_hash(tool_def.schema),
                "provenance": {
                    "package": "open-medicine",
                    "version": __version__,
                    "calculator_id": calc_id,
                },
                "searchable_text": f"{calc_id} {tool_def.description}",
            }
            for calc_id, tool_def in CALCULATOR_REGISTRY.items()
        ]
        results = tokenized_search(query, items)
        for result in results:
            result.pop("_score", None)
        payload = {"package_version": __version__, "matches": results}
        return _result(payload)

    if name == "execute_clinical_calculator":
        calc_id = args.get("calculator_id")
        params_dict = args.get("parameters", {})
        scoped_calculator = _scoped_calculator_id()
        if scoped_calculator is not None and calc_id != scoped_calculator:
            return _result(
                _error(
                    "calculator_not_enabled",
                    "Requested calculator is outside the configured MCP scope.",
                ),
                is_error=True,
            )
        if not calc_id or calc_id not in CALCULATOR_REGISTRY:
            return _result(
                _error("unknown_calculator", f"Unknown calculator_id '{calc_id}'."),
                is_error=True,
            )

        tool_def = CALCULATOR_REGISTRY[calc_id]
        if (scoped_calculator is not None
                and (not isinstance(params_dict, dict)
                     or set(params_dict) != set(tool_def.pydantic_model.model_fields))):
            return _result(
                _error(
                    "validation_error",
                    "Calculator parameters failed validation.",
                    [{
                        "type": "field_set_mismatch",
                        "loc": ["parameters"],
                        "msg": "Payload must contain exactly the advertised fields.",
                    }],
                ),
                is_error=True,
            )
        try:
            model_instance = tool_def.pydantic_model(**params_dict)
            result = tool_def.execute_function(model_instance)
            payload = result.model_dump(mode="json")
            return _result(
                payload,
                is_error=payload.get("status") in {"error", "insufficient_data"},
            )
        except ValidationError as exc:
            safe_details = [
                {key: error[key] for key in ("type", "loc", "msg") if key in error}
                for error in exc.errors(include_url=False)
            ]
            for detail in safe_details:
                if "loc" in detail:
                    detail["loc"] = list(detail["loc"])
            return _result(
                _error(
                    "validation_error",
                    "Calculator parameters failed validation.",
                    safe_details,
                ),
                is_error=True,
            )
        except Exception as exc:
            return _result(
                _error(
                    "execution_error",
                    "Calculator execution failed.",
                    {"exception_type": type(exc).__name__},
                ),
                is_error=True,
            )

    raise ValueError(f"Unknown tool: {name}")


async def main_async():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="open-medicine",
                server_version=__version__,
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()

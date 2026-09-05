import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os

import jsonschema
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types
from pydantic import ValidationError

from open_medicine import __version__
from open_medicine.mcp.registry import CALCULATOR_REGISTRY
from open_medicine.mcp.search_utils import tokenized_search


_AUDIT_PATH_ENV = "OPEN_MEDICINE_MCP_AUDIT_LOG_PATH"
_AUDIT_ALLOWLIST_ENV = "OPEN_MEDICINE_MCP_AUDIT_LOG_ALLOWLIST"
_SENSITIVE_KEYS = ("authorization", "cookie", "credential", "password", "secret", "token", "api_key")


def _audit_path() -> str | None:
    raw_path = os.environ.get(_AUDIT_PATH_ENV)
    raw_allowlist = os.environ.get(_AUDIT_ALLOWLIST_ENV)
    if raw_path is None and raw_allowlist is None:
        return None
    if not raw_path or not raw_allowlist:
        raise ValueError("audit log path requires an explicit allowlist")
    if (os.environ.get("OPEN_MEDICINE_MCP_CALCULATOR_ID") != "calculate_gcs"
            or os.environ.get("OPEN_MEDICINE_MCP_TOOL_ALLOWLIST")
            != "execute_clinical_calculator"):
        raise ValueError("audit log requires the exact GCS benchmark scope")
    path = os.path.abspath(raw_path)
    allowed = raw_allowlist.split(os.pathsep)
    if (not os.path.isabs(raw_path) or not path.endswith(".jsonl")
            or any(not item or not os.path.isabs(item) for item in allowed)
            or path not in {os.path.abspath(item) for item in allowed}):
        raise ValueError("audit log path is not allowlisted")
    return path


def _bounded_audit_value(value, *, depth: int = 0):
    if depth >= 8:
        return "[MAX_DEPTH]"
    if isinstance(value, dict):
        bounded = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= 64:
                bounded["[TRUNCATED]"] = len(value) - 64
                break
            key_string = str(key)[:128]
            if any(marker in key_string.lower() for marker in _SENSITIVE_KEYS):
                bounded[key_string] = "[REDACTED]"
            else:
                bounded[key_string] = _bounded_audit_value(item, depth=depth + 1)
        return bounded
    if isinstance(value, (list, tuple)):
        return [
            _bounded_audit_value(item, depth=depth + 1)
            for item in value[:64]
        ]
    if isinstance(value, str):
        return value if len(value) <= 512 else value[:512] + "[TRUNCATED]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return f"[{type(value).__name__}]"


def _audit_event(event: str, **data) -> None:
    path = _audit_path()
    if path is None:
        return
    bounded_data = _bounded_audit_value(data)
    if not isinstance(bounded_data, dict):  # pragma: no cover - kwargs are a dict
        raise TypeError("audit event data must be an object")
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "event": event,
        **bounded_data,
    }
    encoded = (json.dumps(
        record, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ) + "\n").encode()
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    flags |= getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    try:
        os.fchmod(fd, 0o600)
        remaining = memoryview(encoded)
        while remaining:
            written = os.write(fd, remaining)
            if written <= 0:  # pragma: no cover - defensive OS contract check
                raise OSError("audit log write made no progress")
            remaining = remaining[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


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


_GCS_TERMS = {
    "eye": ("none", "to pressure", "to sound", "spontaneous"),
    "verbal": ("none", "sounds", "words", "confused", "orientated"),
    "motor": (
        "none", "extension", "abnormal flexion", "normal flexion",
        "localising", "obey commands",
    ),
}


def _nullable(schema: dict) -> dict:
    return {"anyOf": [schema, {"type": "null"}]}


def _gcs_output_schema() -> dict:
    nullable_string = _nullable({"type": "string"})

    def component_schema(maximum: int, terms: tuple[str, ...]) -> dict:
        scored_variants = [
            {
                "properties": {
                    "score": {"const": score},
                    "term": {"const": term},
                    "non_testable_reason": {"type": "null"},
                },
            }
            for score, term in zip(range(1, maximum + 1), terms)
        ]
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "score": _nullable({
                    "type": "integer", "minimum": 1, "maximum": maximum,
                }),
                "term": _nullable({"type": "string", "enum": list(terms)}),
                "non_testable_reason": _nullable({
                    "type": "string", "minLength": 1, "maxLength": 256,
                }),
            },
            "required": ["score", "term", "non_testable_reason"],
            "oneOf": [
                *scored_variants,
                {
                    "properties": {
                        "score": {"type": "null"},
                        "term": {"type": "null"},
                        "non_testable_reason": {
                            "type": "string", "minLength": 1, "maxLength": 256,
                        },
                    },
                },
            ],
        }

    evidence_properties = {
        key: nullable_string
        for key in (
            "source_doi", "authority", "url", "document_id", "version_date",
            "section", "retrieved_at", "content_hash",
        )
    }
    evidence_properties.update({
        "level": {"type": "string"},
        "description": {"type": "string"},
    })
    non_testable_components = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            name: {"type": "string", "minLength": 1, "maxLength": 256}
            for name in ("eye", "verbal", "motor")
        },
        "minProperties": 1,
    }
    error_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "code": {"const": "non_testable_component", "type": "string"},
            "message": {"type": "string"},
            "details": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "non_testable_components": non_testable_components,
                },
                "required": ["non_testable_components"],
            },
        },
        "required": ["code", "message", "details"],
    }
    properties = {
        "status": {"type": "string", "enum": ["success", "insufficient_data"]},
        "errors": {"type": "array", "items": error_schema, "maxItems": 1},
        "value": _nullable({"type": "integer", "minimum": 3, "maximum": 15}),
        "component_breakdown": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "eye": component_schema(4, _GCS_TERMS["eye"]),
                "verbal": component_schema(5, _GCS_TERMS["verbal"]),
                "motor": component_schema(6, _GCS_TERMS["motor"]),
            },
            "required": ["eye", "verbal", "motor"],
        },
        "interpretation": {"type": "string"},
        "evidence": {
            "type": "object",
            "additionalProperties": False,
            "properties": evidence_properties,
            "required": list(evidence_properties),
        },
        "fhir_code": nullable_string,
        "fhir_system": nullable_string,
        "fhir_display": nullable_string,
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": list(properties),
        "allOf": [{
            "if": {"properties": {"status": {"const": "success"}}},
            "then": {"properties": {
                "errors": {"maxItems": 0},
                "value": {"type": "integer", "minimum": 3, "maximum": 15},
                "component_breakdown": {"properties": {
                    name: {"properties": {
                        "score": {"type": "integer"},
                        "non_testable_reason": {"type": "null"},
                    }}
                    for name in ("eye", "verbal", "motor")
                }},
            }},
            "else": {"properties": {
                "errors": {"minItems": 1},
                "value": {"type": "null"},
                "component_breakdown": {"anyOf": [
                    {"properties": {
                        name: {"properties": {"score": {"type": "null"}}},
                    }}
                    for name in ("eye", "verbal", "motor")
                ]},
            }},
        }],
    }


def _validate_gcs_output(payload: dict) -> None:
    jsonschema.validate(instance=payload, schema=_gcs_output_schema())
    components = payload["component_breakdown"]
    non_testable = {
        name: component["non_testable_reason"]
        for name, component in components.items()
        if component["score"] is None
    }
    if payload["status"] == "success":
        total = sum(component["score"] for component in components.values())
        if payload["value"] != total:
            raise ValueError("GCS total does not match component scores")
    else:
        reported = payload["errors"][0]["details"]["non_testable_components"]
        if reported != non_testable:
            raise ValueError("GCS non-testable details do not match components")


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
    strict_parameters["additionalProperties"] = False
    strict_parameters["required"] = fields
    strict_parameters.pop("title", None)
    for field_schema in strict_parameters["properties"].values():
        field_schema.pop("default", None)
        field_schema.pop("title", None)
    return (
        f"Executes the exact enabled calculator {calculator_id}. "
        "Use the advertised point-valued parameter contract; provide every field, "
        "using null only where its description permits it. Inputs are validated "
        "strictly by the server without echoing rejected values.",
        {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "calculator_id": {
                    "type": "string",
                    "const": calculator_id,
                    "description": (
                        f"MUST be exactly {calculator_id}; do not substitute a synonym."
                    ),
                },
                "parameters": {
                    **strict_parameters,
                    "description": (
                        f"MUST contain exactly {len(fields)} advertised fields for "
                        f"{calculator_id}. "
                        "Values are validated strictly by the server."
                    ),
                },
            },
            "required": ["calculator_id", "parameters"],
        },
    )


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    execution_description, execution_schema = _execution_contract()
    scoped_calculator = _scoped_calculator_id()
    tools = [tool for tool in [
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
            outputSchema=(
                _gcs_output_schema()
                if scoped_calculator == "calculate_gcs"
                else None
            ),
        ),
    ] if tool.name in _enabled_tool_names()]
    _audit_event("list_tools", tools=[tool.model_dump(mode="json") for tool in tools])
    return tools


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
        scoped_calculator = _scoped_calculator_id()
        if (scoped_calculator is not None
                and set(args) != {"calculator_id", "parameters"}):
            return _result(
                _error(
                    "validation_error",
                    "Calculator parameters failed validation.",
                    [{
                        "type": "field_set_mismatch",
                        "loc": [],
                        "msg": "Payload must contain exactly the advertised fields.",
                    }],
                ),
                is_error=True,
            )
        calc_id = args.get("calculator_id")
        params_dict = args.get("parameters", {})
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
            if scoped_calculator == "calculate_gcs":
                try:
                    _validate_gcs_output(payload)
                except (jsonschema.ValidationError, ValueError):
                    return _result(
                        _error(
                            "output_validation_error",
                            "Calculator output failed server validation.",
                        ),
                        is_error=True,
                    )
            return _result(
                payload,
                is_error=payload.get("status") == "error",
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


_call_tool_request_handler = server.request_handlers[types.CallToolRequest]


async def _audited_call_tool_request(request: types.CallToolRequest):
    if request.params.name == "execute_clinical_calculator":
        cached_tool = server._tool_cache.get(request.params.name)
        expected_schema = _execution_contract()[1]
        if cached_tool is not None and cached_tool.inputSchema != expected_schema:
            server._tool_cache.pop(request.params.name, None)
    _audit_event(
        "call_received",
        request={
            "name": request.params.name,
            "arguments": request.params.arguments or {},
        },
    )
    response = await _call_tool_request_handler(request)
    result = response.root
    if (isinstance(result, types.CallToolResult) and result.isError
            and result.structuredContent is None
            and result.content and isinstance(result.content[0], types.TextContent)
            and result.content[0].text.startswith("Input validation error:")):
        result = _result(
            _error(
                "validation_error",
                "Calculator parameters failed validation.",
            ),
            is_error=True,
        )
        response = types.ServerResult(result)
    audit_result = result.model_dump(
        mode="json", by_alias=True, exclude_none=True,
    )
    if isinstance(result, types.CallToolResult) and result.isError:
        _audit_event("error", result=audit_result)
    _audit_event("call_completed", result=audit_result)
    return response


server.request_handlers[types.CallToolRequest] = _audited_call_tool_request


async def main_async():
    _audit_event(
        "startup",
        server={"name": "open-medicine", "version": __version__},
    )
    try:
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
    except Exception as exc:
        _audit_event("error", error={"exception_type": type(exc).__name__})
        raise
    finally:
        _audit_event("shutdown")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()

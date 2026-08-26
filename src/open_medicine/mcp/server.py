import asyncio
import hashlib
import json

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


def _error(code: str, message: str, details=None) -> str:
    payload = {
        "status": "error",
        "errors": [{"code": code, "message": message, "details": details}],
    }
    return json.dumps(payload, indent=2)


server = Server("open-medicine")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
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
            description=(
                "Executes a medical calculator by ID using a validated JSON parameter "
                "payload."
            ),
            inputSchema={
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
                        "description": "A flat JSON payload matching the calculator's JSON Schema.",
                    },
                },
                "required": ["calculator_id", "parameters"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
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
        return [
            types.TextContent(type="text", text=json.dumps(payload, indent=2))
        ]

    if name == "execute_clinical_calculator":
        calc_id = args.get("calculator_id")
        params_dict = args.get("parameters", {})
        if not calc_id or calc_id not in CALCULATOR_REGISTRY:
            return [
                types.TextContent(
                    type="text",
                    text=_error("unknown_calculator", f"Unknown calculator_id '{calc_id}'."),
                )
            ]

        tool_def = CALCULATOR_REGISTRY[calc_id]
        try:
            model_instance = tool_def.pydantic_model(**params_dict)
            result = tool_def.execute_function(model_instance)
            return [
                types.TextContent(type="text", text=result.model_dump_json(indent=2))
            ]
        except ValidationError as exc:
            return [
                types.TextContent(
                    type="text",
                    text=_error(
                        "validation_error",
                        "Calculator parameters failed validation.",
                        exc.errors(
                            include_url=False,
                            include_context=False,
                            include_input=False,
                        ),
                    ),
                )
            ]
        except Exception as exc:
            return [
                types.TextContent(
                    type="text",
                    text=_error(
                        "execution_error",
                        "Calculator execution failed.",
                        {"exception_type": type(exc).__name__},
                    ),
                )
            ]

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

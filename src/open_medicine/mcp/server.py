import asyncio
import json

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

from open_medicine.mcp.registry import CALCULATOR_REGISTRY
from open_medicine.mcp.search_utils import tokenized_search
from open_medicine.mcp.graphrag_tools import (
    GRAPHRAG_TOOL_DEFINITIONS,
    handle_graph_tool_call,
)

_GRAPH_TOOL_NAMES = {t["name"] for t in GRAPHRAG_TOOL_DEFINITIONS}

server = Server("open-medicine")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    tools = [
        types.Tool(
            name="search_clinical_calculators",
            description="Searches the internal registry for available clinical calculators based on keywords. Returns the calculator ID and its required JSON Schema.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keywords to match against clinical calculators (e.g. 'kidney function', 'stroke risk').",
                    }
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="execute_clinical_calculator",
            description="Executes a specific clinical calculator using its ID and a validated JSON dictionary of parameters matching its schema.",
            inputSchema={
                "type": "object",
                "properties": {
                    "calculator_id": {
                        "type": "string",
                        "description": "The exact ID string of the calculator returned from the search_clinical_calculators tool.",
                    },
                    "parameters": {
                        "type": "object",
                        "description": "A flat JSON payload containing the exact key-value pairs requested by the calculator's JSON schema.",
                    },
                },
                "required": ["calculator_id", "parameters"],
            },
        ),
    ]
    for t in GRAPHRAG_TOOL_DEFINITIONS:
        tools.append(
            types.Tool(name=t["name"], description=t["description"], inputSchema=t["inputSchema"])
        )
    return tools


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
                "searchable_text": f"{calc_id} {tool_def.description}",
            }
            for calc_id, tool_def in CALCULATOR_REGISTRY.items()
        ]
        results = tokenized_search(query, items)
        for r in results:
            r.pop("_score", None)
        return [
            types.TextContent(type="text", text=json.dumps({"matches": results}, indent=2))
        ]

    if name == "execute_clinical_calculator":
        calc_id = args.get("calculator_id")
        params_dict = args.get("parameters", {})
        if not calc_id or calc_id not in CALCULATOR_REGISTRY:
            return [
                types.TextContent(
                    type="text",
                    text=f"Error: Unknown calculator_id '{calc_id}'. Please use search_clinical_calculators first.",
                )
            ]
        tool_def = CALCULATOR_REGISTRY[calc_id]
        try:
            model_instance = tool_def.pydantic_model(**params_dict)
            result = tool_def.execute_function(model_instance)
            return [types.TextContent(type="text", text=result.model_dump_json(indent=2))]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error executing {calc_id}: {e}")]

    if name in _GRAPH_TOOL_NAMES:
        result_text = handle_graph_tool_call(name, args)
        return [types.TextContent(type="text", text=result_text)]

    raise ValueError(f"Unknown tool: {name}")


async def main_async():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="open-medicine",
                server_version="0.11.0",
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

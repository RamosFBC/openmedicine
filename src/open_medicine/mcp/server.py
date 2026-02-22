import asyncio
from contextlib import asynccontextmanager
from typing import Any

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

from open_medicine.mcp.registry import CALCULATOR_REGISTRY
from open_medicine.mcp.guideline_engine import search_guidelines, retrieve_guideline

# Initialize the MCP Server
server = Server("open-medicine")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List meta-tools facilitating scalable execution across clinical algorithms and guideline retrieval.
    """
    return [
        types.Tool(
            name="search_clinical_calculators",
            description="Searches the internal registry for available clinical calculators based on keywords. Returns the calculator ID and its required JSON Schema.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keywords to match against clinical calculators (e.g. 'kidney function', 'stroke risk')."
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="execute_clinical_calculator",
            description="Executes a specific clinical calculator using its ID and a validated JSON dictionary of parameters matching its schema.",
            inputSchema={
                "type": "object",
                "properties": {
                    "calculator_id": {
                        "type": "string",
                        "description": "The exact ID string of the calculator returned from the search_clinical_calculators tool."
                    },
                    "parameters": {
                        "type": "object",
                        "description": "A flat JSON payload containing the exact key-value pairs requested by the calculator's JSON schema."
                    }
                },
                "required": ["calculator_id", "parameters"]
            }
        ),
        types.Tool(
            name="search_guidelines",
            description="Searches the clinical guideline knowledge base by topic keywords. Returns matching guideline IDs, titles, DOIs, and available sections for retrieval.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keywords to search for (e.g. 'atrial fibrillation anticoagulation', 'pneumonia severity', 'CKD staging')."
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="retrieve_guideline",
            description="Retrieves the full curated content of a specific clinical guideline section. Use search_guidelines first to discover available guideline IDs and sections.",
            inputSchema={
                "type": "object",
                "properties": {
                    "guideline_id": {
                        "type": "string",
                        "description": "The exact guideline ID returned from search_guidelines (e.g. 'acc_aha_af_2023')."
                    },
                    "section": {
                        "type": "string",
                        "description": "The section name to retrieve (e.g. 'anticoagulation', 'severity_assessment')."
                    }
                },
                "required": ["guideline_id", "section"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.
    """
    if name == "search_clinical_calculators":
        query = (arguments or {}).get("query", "").lower()
        results = []
        for calc_id, tool_def in CALCULATOR_REGISTRY.items():
            # A simple substring match against the ID and the description
            if query in calc_id.lower() or query in tool_def.description.lower():
                results.append({
                    "calculator_id": calc_id,
                    "description": tool_def.description,
                    "required_schema": tool_def.schema
                })
        
        import json
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"matches": results}, indent=2)
            )
        ]

    elif name == "execute_clinical_calculator":
        calc_id = (arguments or {}).get("calculator_id")
        params_dict = (arguments or {}).get("parameters", {})
        
        if not calc_id or calc_id not in CALCULATOR_REGISTRY:
            return [
                types.TextContent(
                    type="text",
                    text=f"Error: Unknown calculator_id '{calc_id}'. Please use search_clinical_calculators first."
                )
            ]
            
        tool_def = CALCULATOR_REGISTRY[calc_id]
        try:
            # Map the raw dict directly into the Pydantic boundary
            model_instance = tool_def.pydantic_model(**params_dict)
            result = tool_def.execute_function(model_instance)
            return [
                types.TextContent(
                    type="text",
                    text=result.model_dump_json(indent=2)
                )
            ]
        except Exception as e:
            return [
                types.TextContent(
                    type="text",
                    text=f"Error executing {calc_id}: {e}"
                )
            ]

    elif name == "search_guidelines":
        query = (arguments or {}).get("query", "")
        results = search_guidelines(query)
        import json
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"matches": results}, indent=2)
            )
        ]

    elif name == "retrieve_guideline":
        guideline_id = (arguments or {}).get("guideline_id", "")
        section = (arguments or {}).get("section", "")
        try:
            result = retrieve_guideline(guideline_id, section)
            return [
                types.TextContent(
                    type="text",
                    text=result.model_dump_json(indent=2)
                )
            ]
        except (ValueError, FileNotFoundError) as e:
            return [
                types.TextContent(
                    type="text",
                    text=f"Error: {e}"
                )
            ]

    else:
        raise ValueError(f"Unknown tool: {name}")

async def main_async():
    """
    Main entry point for running the server over stdio.
    """
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="open-medicine",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

def main():
    """Synchronous entry point."""
    asyncio.run(main_async())

if __name__ == "__main__":
    main()

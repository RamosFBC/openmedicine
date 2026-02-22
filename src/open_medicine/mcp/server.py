import asyncio
from contextlib import asynccontextmanager
from typing import Any

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

from open_medicine.mcp.calculators.sofa import calculate_sofa, SOFAParams
from open_medicine.mcp.calculators.chadsvasc import calculate_chadsvasc, CHADSVAScParams
from open_medicine.mcp.calculators.ascvd import calculate_ascvd, ASCVDParams
from open_medicine.mcp.calculators.ckd_epi import calculate_ckd_epi, CKDEPIParams
from open_medicine.mcp.calculators.cockcroft_gault import calculate_cockcroft_gault, CockcroftGaultParams
from open_medicine.mcp.calculators.rivaroxaban_dosing import calculate_rivaroxaban_dosing, RivaroxabanDosingParams
from open_medicine.mcp.calculators.enoxaparin_dosing import calculate_enoxaparin_dosing, EnoxaparinDosingParams
from open_medicine.mcp.calculators.gcs import calculate_gcs, GCSParams

# Initialize the MCP Server
server = Server("open-medicine")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List two meta-tools facilitating scalable execution across hundreds of clinical algorithms.
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

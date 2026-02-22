import asyncio
from contextlib import asynccontextmanager
from typing import Any

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

from open_medicine.mcp.calculators.sofa import calculate_sofa, SOFAParams
from open_medicine.mcp.calculators.chadsvasc import calculate_chadsvasc, CHADSVAScParams

# Initialize the MCP Server
server = Server("open-medicine")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools provided by the Open Medicine MCP server.
    """
    return [
        types.Tool(
            name="calculate_sofa",
            description="Calculates the Sequential Organ Failure Assessment (SOFA) score. Missing values are assumed normal.",
            inputSchema=SOFAParams.model_json_schema()
        ),
        types.Tool(
            name="calculate_chadsvasc",
            description="Calculates the CHA2DS2-VASc score for atrial fibrillation stroke risk. Missing values are assumed false/normal.",
            inputSchema=CHADSVAScParams.model_json_schema()
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.
    """
    if name == "calculate_sofa":
        try:
            params = SOFAParams(**(arguments or {}))
            result = calculate_sofa(params)
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
                    text=f"Error calculating SOFA score: {e}"
                )
            ]
            
    elif name == "calculate_chadsvasc":
        try:
            params = CHADSVAScParams(**(arguments or {}))
            result = calculate_chadsvasc(params)
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
                    text=f"Error calculating CHA2DS2-VASc score: {e}"
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

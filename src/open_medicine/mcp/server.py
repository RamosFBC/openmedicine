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
        ),
        types.Tool(
            name="calculate_ascvd",
            description="Calculates the 10-year ASCVD (Atherosclerotic Cardiovascular Disease) risk using the 2013 ACC/AHA Pooled Cohort Equations.",
            inputSchema=ASCVDParams.model_json_schema()
        ),
        types.Tool(
            name="calculate_ckd_epi",
            description="Calculates the estimated Glomerular Filtration Rate (eGFR) using the 2021 CKD-EPI creatinine equation (without race).",
            inputSchema=CKDEPIParams.model_json_schema()
        ),
        types.Tool(
            name="calculate_cockcroft_gault",
            description="Calculates the estimated Creatinine Clearance (CrCl) using the Cockcroft-Gault equation for renal medication dosage adjustments.",
            inputSchema=CockcroftGaultParams.model_json_schema()
        ),
        types.Tool(
            name="calculate_rivaroxaban_dosing",
            description="Calculates the FDA-approved Rivaroxaban (Xarelto) dosage based on Creatinine Clearance (CrCl) and indication.",
            inputSchema=RivaroxabanDosingParams.model_json_schema()
        ),
        types.Tool(
            name="calculate_enoxaparin_dosing",
            description="Calculates the FDA-approved Enoxaparin (Lovenox) dosage based on weight, Creatinine Clearance (CrCl), and indication.",
            inputSchema=EnoxaparinDosingParams.model_json_schema()
        ),
        types.Tool(
            name="calculate_gcs",
            description="Calculates the Glasgow Coma Scale (GCS) score based on eye, verbal, and motor responses.",
            inputSchema=GCSParams.model_json_schema()
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
            
    elif name == "calculate_ascvd":
        try:
            params = ASCVDParams(**(arguments or {}))
            result = calculate_ascvd(params)
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
                    text=f"Error calculating ASCVD score: {e}"
                )
            ]
            
    elif name == "calculate_ckd_epi":
        try:
            params = CKDEPIParams(**(arguments or {}))
            result = calculate_ckd_epi(params)
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
                    text=f"Error calculating CKD-EPI: {e}"
                )
            ]
            
    elif name == "calculate_cockcroft_gault":
        try:
            params = CockcroftGaultParams(**(arguments or {}))
            result = calculate_cockcroft_gault(params)
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
                    text=f"Error calculating Cockcroft-Gault CrCl: {e}"
                )
            ]
            
    elif name == "calculate_rivaroxaban_dosing":
        try:
            params = RivaroxabanDosingParams(**(arguments or {}))
            result = calculate_rivaroxaban_dosing(params)
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
                    text=f"Error calculating Rivaroxaban dosing: {e}"
                )
            ]

    elif name == "calculate_enoxaparin_dosing":
        try:
            params = EnoxaparinDosingParams(**(arguments or {}))
            result = calculate_enoxaparin_dosing(params)
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
                    text=f"Error calculating Enoxaparin dosing: {e}"
                )
            ]
            
    elif name == "calculate_gcs":
        try:
            params = GCSParams(**(arguments or {}))
            result = calculate_gcs(params)
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
                    text=f"Error calculating Glasgow Coma Scale: {e}"
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

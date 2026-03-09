import asyncio
from contextlib import asynccontextmanager
from typing import Any

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

from open_medicine.mcp.registry import CALCULATOR_REGISTRY
from open_medicine.mcp.guideline_engine import search_guidelines, retrieve_guideline
from open_medicine.mcp.differentials.engine import search_differentials, get_differential, DifferentialParams
from open_medicine.mcp.pathways.engine import search_pathways, get_pathway, PathwayParams

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
        ),
        types.Tool(
            name="search_differential_diagnosis",
            description="Searches available differential diagnoses by symptoms, presentations, or keywords. Returns matching differential IDs and descriptions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keywords to match against differential diagnoses (e.g. 'chest pain', 'dyspnea', 'headache')."
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="get_differential_diagnosis",
            description="Retrieves a full ranked differential diagnosis with must-not-miss conditions, key features, red flags, and recommended tests/calculators. Use search_differential_diagnosis first to find the ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "differential_id": {
                        "type": "string",
                        "description": "The exact differential ID returned from search_differential_diagnosis."
                    },
                    "age": {
                        "type": "integer",
                        "description": "Patient age in years (optional, for age-specific annotations)."
                    },
                    "sex": {
                        "type": "string",
                        "description": "Patient sex — 'male' or 'female' (optional, for sex-specific annotations)."
                    }
                },
                "required": ["differential_id"]
            }
        ),
        types.Tool(
            name="search_treatment_pathways",
            description="Searches available evidence-based treatment pathways by diagnosis or keywords. Returns matching pathway IDs and descriptions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keywords to match against treatment pathways (e.g. 'atrial fibrillation anticoagulation', 'DVT treatment')."
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="get_treatment_pathway",
            description="Retrieves a full evidence-based treatment pathway with step-by-step decision tree, medication options, dose calculators, and guideline citations. Use search_treatment_pathways first to find the ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pathway_id": {
                        "type": "string",
                        "description": "The exact pathway ID returned from search_treatment_pathways."
                    },
                    "contraindications": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of contraindication keys (e.g. ['active_major_bleeding']). Pathway will include warnings for matched contraindications."
                    }
                },
                "required": ["pathway_id"]
            }
        ),
        types.Tool(
            name="search_medical_knowledge",
            description="Unified semantic search across ALL OpenMedicine content — calculators, guidelines, differential diagnoses, and treatment pathways. Returns categorized ranked results. This is the primary entry point for discovering relevant clinical tools. Falls back to keyword search if semantic search is unavailable.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language clinical query (e.g. 'patient with chest pain and shortness of breath', 'anticoagulation in CKD')."
                    },
                    "domain": {
                        "type": "string",
                        "enum": ["all", "calculator", "guideline", "differential", "pathway"],
                        "description": "Optional filter by content type. Default: 'all'."
                    }
                },
                "required": ["query"]
            }
        ),
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

    elif name == "search_differential_diagnosis":
        query = (arguments or {}).get("query", "")
        results = search_differentials(query)
        import json
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"matches": results}, indent=2)
            )
        ]

    elif name == "get_differential_diagnosis":
        diff_id = (arguments or {}).get("differential_id", "")
        age = (arguments or {}).get("age")
        sex = (arguments or {}).get("sex")
        try:
            params = DifferentialParams(
                differential_id=diff_id,
                age=age,
                sex=sex,
            )
            result = get_differential(params)
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
                    text=f"Error: {e}"
                )
            ]

    elif name == "search_treatment_pathways":
        query = (arguments or {}).get("query", "")
        results = search_pathways(query)
        import json
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"matches": results}, indent=2)
            )
        ]

    elif name == "get_treatment_pathway":
        pw_id = (arguments or {}).get("pathway_id", "")
        contras = (arguments or {}).get("contraindications")
        try:
            params = PathwayParams(
                pathway_id=pw_id,
                contraindications=contras,
            )
            result = get_pathway(params)
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
                    text=f"Error: {e}"
                )
            ]

    elif name == "search_medical_knowledge":
        query = (arguments or {}).get("query", "")
        domain = (arguments or {}).get("domain", "all")

        # Try semantic search first
        from open_medicine.embeddings.search import semantic_search
        results = semantic_search(query, domain=domain)

        if results is not None:
            import json
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({"search_type": "semantic", "matches": results}, indent=2)
                )
            ]

        # Fallback: aggregate keyword search across all domains
        query_lower = query.lower()
        matches = []

        if domain in ("all", "calculator"):
            for calc_id, tool_def in CALCULATOR_REGISTRY.items():
                if query_lower in calc_id.lower() or query_lower in tool_def.description.lower():
                    matches.append({"id": calc_id, "domain": "calculator", "text": tool_def.description})

        if domain in ("all", "guideline"):
            for g in search_guidelines(query):
                matches.append({"id": g["guideline_id"], "domain": "guideline", "text": g["title"]})

        if domain in ("all", "differential"):
            for d in search_differentials(query):
                matches.append({"id": d["differential_id"], "domain": "differential", "text": d["title"]})

        if domain in ("all", "pathway"):
            for p in search_pathways(query):
                matches.append({"id": p["pathway_id"], "domain": "pathway", "text": p["title"]})

        import json
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"search_type": "keyword", "matches": matches}, indent=2)
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

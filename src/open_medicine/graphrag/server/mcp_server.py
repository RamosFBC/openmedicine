from __future__ import annotations

import asyncio
import json

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

from open_medicine.graphrag.config import get_settings
from open_medicine.graphrag.graph.connection import GraphConnection
from open_medicine.graphrag.graph.queries_v2 import ReasoningQueries
from open_medicine.graphrag.reasoning.engine_v2 import ReasoningEngine
from open_medicine.graphrag.reasoning.types_v2 import ClinicalQuery

TOOL_DEFINITIONS = [
    {
        "name": "check_drug_dosing",
        "description": "Get dosing recommendation for a drug given patient variables. Returns evidence-backed rules from clinical guidelines.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "drug": {"type": "string", "description": "Drug name (e.g. 'apixaban', 'lisinopril')"},
                "patient_vars": {"type": "object", "description": "Patient variables (e.g. {eGFR: 20, age: 80, weight_kg: 55})"},
            },
            "required": ["drug"],
        },
    },
    {
        "name": "check_contraindications",
        "description": "Check if an intervention is contraindicated given patient variables.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "intervention": {"type": "string", "description": "Drug or procedure to check"},
                "patient_vars": {"type": "object", "description": "Patient variables"},
            },
            "required": ["intervention"],
        },
    },
    {
        "name": "check_drug_interaction",
        "description": "Check for interactions between two drugs.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "drug_a": {"type": "string"},
                "drug_b": {"type": "string"},
                "patient_vars": {"type": "object", "description": "Optional patient variables"},
            },
            "required": ["drug_a", "drug_b"],
        },
    },
    {
        "name": "check_monitoring_requirements",
        "description": "Get lab/test monitoring requirements for an intervention.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "intervention": {"type": "string"},
                "patient_vars": {"type": "object"},
            },
            "required": ["intervention"],
        },
    },
    {
        "name": "find_treatment_options",
        "description": "Find recommended treatments for a condition given patient variables.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "condition": {"type": "string"},
                "patient_vars": {"type": "object"},
            },
            "required": ["condition"],
        },
    },
    {
        "name": "query_clinical_graph",
        "description": "Structured query across the clinical knowledge graph. Use for advanced or exploratory queries.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "intent": {"type": "string", "enum": ["dosing", "contraindication", "interaction", "monitoring", "treatment_selection", "diagnostic_criteria"]},
                "concepts": {"type": "array", "items": {"type": "string"}},
                "patient_vars": {"type": "object"},
                "guideline_filter": {"type": "string", "description": "Optional: scope to a specific guideline ID"},
                "include_source_text": {"type": "boolean", "default": True},
            },
            "required": ["intent", "concepts"],
        },
    },
    {
        "name": "fetch_evidence_chunk",
        "description": "Retrieve the exact source text for a citation by chunk ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "chunk_id": {"type": "string", "description": "The evidence chunk ID from a previous query result"},
            },
            "required": ["chunk_id"],
        },
    },
]

_INTENT_MAP = {
    "check_drug_dosing": ("dosing", lambda a: [a["drug"]]),
    "check_contraindications": ("contraindication", lambda a: [a["intervention"]]),
    "check_drug_interaction": ("interaction", lambda a: [a["drug_a"], a["drug_b"]]),
    "check_monitoring_requirements": ("monitoring", lambda a: [a["intervention"]]),
    "find_treatment_options": ("treatment_selection", lambda a: [a["condition"]]),
}


def create_mcp_server() -> Server:
    settings = get_settings()
    server = Server("open-medicine-graphrag")
    conn = GraphConnection(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    engine = ReasoningEngine(conn)

    def _query(q: ClinicalQuery) -> str:
        result = engine.query(q)
        return result.model_dump_json(indent=2)

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        return [
            types.Tool(name=t["name"], description=t["description"], inputSchema=t["inputSchema"])
            for t in TOOL_DEFINITIONS
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
        args = arguments or {}

        if name in _INTENT_MAP:
            intent, get_concepts = _INTENT_MAP[name]
            q = ClinicalQuery(
                intent=intent,
                concepts=get_concepts(args),
                patient_vars=args.get("patient_vars", {}),
            )
            return [types.TextContent(type="text", text=_query(q))]

        if name == "query_clinical_graph":
            q = ClinicalQuery(**{k: v for k, v in args.items() if v is not None})
            return [types.TextContent(type="text", text=_query(q))]

        if name == "fetch_evidence_chunk":
            cypher, params = ReasoningQueries.get_evidence_chunk(args["chunk_id"])
            rows = conn.execute_read(cypher, params)
            return [types.TextContent(
                type="text",
                text=json.dumps(rows[0] if rows else {"error": "Not found"}, indent=2),
            )]

        raise ValueError(f"Unknown tool: {name}")

    return server


async def main_async() -> None:
    server = create_mcp_server()
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="open-medicine-graphrag",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()

from __future__ import annotations

import asyncio
import json
import warnings

warnings.warn(
    "open-medicine-graphrag is deprecated. Use open-medicine-mcp instead, "
    "which includes all graph tools. This entry point will be removed in v1.0.",
    DeprecationWarning,
    stacklevel=2,
)

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
        "description": (
            "Get evidence-based dosing recommendations for a drug. "
            "Returns starting dose, target dose, max dose, frequency, and titration schedule "
            "from clinical guidelines. Evaluates patient variables (eGFR, weight, age) "
            "against dosing conditions. Includes DOI citations."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "drug": {
                    "type": "string",
                    "description": "Drug name (e.g. 'apixaban', 'lisinopril', 'carvedilol')",
                },
                "patient_vars": {
                    "type": "object",
                    "description": (
                        "Patient variables as key-value pairs "
                        '(e.g. {"eGFR": 20, "age": 80, "weight_kg": 55, "potassium": 4.8})'
                    ),
                },
            },
            "required": ["drug"],
        },
    },
    {
        "name": "check_contraindications",
        "description": (
            "Check if a drug or procedure is contraindicated for a patient. "
            "Returns contraindication severity (ABSOLUTE, MAJOR, MINOR) and evidence quality. "
            "ABSOLUTE contraindications must never be overridden. "
            "Evaluates patient variables against contraindication conditions."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "intervention": {
                    "type": "string",
                    "description": "Drug or procedure to check (e.g. 'lisinopril', 'sacubitril_valsartan')",
                },
                "patient_vars": {
                    "type": "object",
                    "description": (
                        'Patient variables (e.g. {"history_of_angioedema": true, "potassium": 5.5})'
                    ),
                },
            },
            "required": ["intervention"],
        },
    },
    {
        "name": "check_drug_interaction",
        "description": (
            "Check for interactions between two drugs. "
            "Returns interaction severity (ABSOLUTE, MAJOR, MINOR), mechanism, and clinical effect. "
            "ABSOLUTE interactions are hard contraindications — the drugs must not be co-prescribed."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "drug_a": {"type": "string", "description": "First drug name"},
                "drug_b": {"type": "string", "description": "Second drug name"},
                "patient_vars": {
                    "type": "object",
                    "description": "Optional patient variables for context",
                },
            },
            "required": ["drug_a", "drug_b"],
        },
    },
    {
        "name": "check_monitoring_requirements",
        "description": (
            "Get lab monitoring requirements for a drug or procedure. "
            "Returns which labs to monitor, how often, alert thresholds, and stop thresholds. "
            "Critical for ongoing medication management."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "intervention": {
                    "type": "string",
                    "description": "Drug or procedure name",
                },
                "patient_vars": {
                    "type": "object",
                    "description": "Optional patient variables",
                },
            },
            "required": ["intervention"],
        },
    },
    {
        "name": "find_treatment_options",
        "description": (
            "Find recommended treatments for a clinical condition. "
            "Returns drugs and drug classes ranked by recommendation strength "
            "(strong > moderate > weak) and evidence quality (high > moderate > low). "
            "Evaluates patient eligibility criteria."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "condition": {
                    "type": "string",
                    "description": "Clinical condition (e.g. 'heart_failure_reduced_ef', 'atrial_fibrillation')",
                },
                "patient_vars": {
                    "type": "object",
                    "description": (
                        'Patient variables to evaluate eligibility (e.g. {"lvef": 30, "egfr": 45})'
                    ),
                },
            },
            "required": ["condition"],
        },
    },
    {
        "name": "query_clinical_graph",
        "description": (
            "Advanced structured query across the clinical knowledge graph. "
            "Supports all intent types: dosing, contraindication, interaction, monitoring, "
            "treatment_selection, diagnostic_criteria, prevention, referral, device_therapy, "
            "lifestyle, discharge, follow_up. Use this for multi-concept queries or when "
            "you need to scope results to a specific guideline."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "enum": [
                        "dosing", "contraindication", "interaction", "monitoring",
                        "treatment_selection", "diagnostic_criteria", "prevention",
                        "referral", "device_therapy", "lifestyle", "discharge", "follow_up",
                    ],
                },
                "concepts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Clinical concepts to query",
                },
                "patient_vars": {
                    "type": "object",
                    "description": "Patient variables for condition evaluation",
                },
                "guideline_filter": {
                    "type": "string",
                    "description": "Optional guideline ID to scope results (e.g. 'aha_acc_hf_2022')",
                },
                "include_evidence": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include source text evidence chain",
                },
            },
            "required": ["intent", "concepts"],
        },
    },
    {
        "name": "fetch_evidence_chunk",
        "description": (
            "Retrieve the exact source text for an evidence citation by chunk ID. "
            "Use this to verify or display the original guideline text backing a recommendation. "
            "Chunk IDs are returned in query results under the 'evidence' field."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "chunk_id": {
                    "type": "string",
                    "description": "Evidence chunk ID from a previous query result",
                },
            },
            "required": ["chunk_id"],
        },
    },
    {
        "name": "list_available_guidelines",
        "description": (
            "List all clinical guidelines loaded in the knowledge graph. "
            "Returns guideline IDs, titles, DOIs, and publication years. "
            "Use guideline IDs to filter other queries via the guideline_filter parameter."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
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

        if name == "list_available_guidelines":
            cypher, params = ReasoningQueries.list_guidelines()
            rows = conn.execute_read(cypher, params)
            return [types.TextContent(
                type="text",
                text=json.dumps({"guidelines": rows}, indent=2),
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

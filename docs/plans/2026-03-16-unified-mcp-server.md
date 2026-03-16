# Unified MCP Server Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Merge the calculator MCP server (`mcp/server.py`) and GraphRAG MCP server (`graphrag/server/mcp_server.py`) into a single unified MCP server with 10 tools. Graph tools degrade gracefully when Neo4j is unavailable.

**Architecture:** The unified server lives in `mcp/server.py`. It imports calculator tools directly (existing code) and GraphRAG tools via a lazy-initialized engine wrapper that catches connection failures. The GraphRAG MCP server (`graphrag/server/mcp_server.py`) is preserved but marked deprecated, delegating to the unified server's graph tool logic.

**Tech Stack:** Python 3.10+, `mcp` SDK, `neo4j` driver (optional), `pydantic-settings` (optional)

---

### Task 1: Add graphrag optional import helper

**Files:**
- Create: `src/open_medicine/mcp/graphrag_tools.py`
- Test: `tests/test_graphrag_tools.py`

**Step 1: Write the failing test**

Create `tests/test_graphrag_tools.py`:

```python
"""Tests for graphrag tool integration in unified MCP server."""
import pytest
from unittest.mock import MagicMock, patch


class TestGraphRAGToolsAvailability:
    """Test that graph tools work when Neo4j is available and degrade when not."""

    def test_graphrag_tools_list_returns_8_tools(self):
        from open_medicine.mcp.graphrag_tools import GRAPHRAG_TOOL_DEFINITIONS
        assert len(GRAPHRAG_TOOL_DEFINITIONS) == 8

    def test_graphrag_tool_names(self):
        from open_medicine.mcp.graphrag_tools import GRAPHRAG_TOOL_DEFINITIONS
        names = [t["name"] for t in GRAPHRAG_TOOL_DEFINITIONS]
        assert "check_drug_dosing" in names
        assert "check_contraindications" in names
        assert "check_drug_interaction" in names
        assert "check_monitoring_requirements" in names
        assert "find_treatment_options" in names
        assert "query_clinical_graph" in names
        assert "fetch_evidence_chunk" in names
        assert "list_available_guidelines" in names


class TestGraphRAGEngineInit:
    """Test lazy engine initialization and graceful degradation."""

    def test_engine_unavailable_when_neo4j_not_installed(self):
        from open_medicine.mcp.graphrag_tools import get_graph_engine
        with patch.dict("sys.modules", {"neo4j": None}):
            # Force re-evaluation — engine should be None
            engine = get_graph_engine(force_reinit=True)
            assert engine is None

    def test_unavailable_message_returned_when_no_engine(self):
        from open_medicine.mcp.graphrag_tools import handle_graph_tool_call
        with patch("open_medicine.mcp.graphrag_tools.get_graph_engine", return_value=None):
            result = handle_graph_tool_call("check_drug_dosing", {"drug": "lisinopril"})
            assert "not configured" in result.lower() or "unavailable" in result.lower()

    def test_engine_available_with_mock_connection(self):
        from open_medicine.mcp.graphrag_tools import get_graph_engine
        mock_conn = MagicMock()
        with patch("open_medicine.mcp.graphrag_tools.GraphConnection", return_value=mock_conn), \
             patch("open_medicine.mcp.graphrag_tools.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="neo4j",
                neo4j_password="test",
            )
            engine = get_graph_engine(force_reinit=True)
            assert engine is not None
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_graphrag_tools.py -v`
Expected: FAIL with `ModuleNotFoundError` or `ImportError`

**Step 3: Write implementation**

Create `src/open_medicine/mcp/graphrag_tools.py`:

```python
"""GraphRAG tool definitions and engine wrapper for the unified MCP server.

Provides lazy initialization of the GraphRAG engine with graceful degradation
when Neo4j or graphrag dependencies are unavailable.
"""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── Tool definitions (static, always available) ─────────────────────────

GRAPHRAG_TOOL_DEFINITIONS = [
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

# ── Intent mapping (same as graphrag mcp_server.py) ─────────────────────

_INTENT_MAP: dict[str, tuple[str, Any]] = {
    "check_drug_dosing": ("dosing", lambda a: [a["drug"]]),
    "check_contraindications": ("contraindication", lambda a: [a["intervention"]]),
    "check_drug_interaction": ("interaction", lambda a: [a["drug_a"], a["drug_b"]]),
    "check_monitoring_requirements": ("monitoring", lambda a: [a["intervention"]]),
    "find_treatment_options": ("treatment_selection", lambda a: [a["condition"]]),
}

# ── Lazy engine singleton ───────────────────────────────────────────────

_engine_instance: Any = None
_conn_instance: Any = None
_init_attempted: bool = False


def get_graph_engine(force_reinit: bool = False) -> Any:
    """Return a ReasoningEngine instance, or None if GraphRAG is unavailable."""
    global _engine_instance, _conn_instance, _init_attempted

    if _init_attempted and not force_reinit:
        return _engine_instance

    _init_attempted = True
    _engine_instance = None
    _conn_instance = None

    try:
        from open_medicine.graphrag.config import get_settings
        from open_medicine.graphrag.graph.connection import GraphConnection
        from open_medicine.graphrag.reasoning.engine_v2 import ReasoningEngine

        settings = get_settings()
        _conn_instance = GraphConnection(
            settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password
        )
        _engine_instance = ReasoningEngine(_conn_instance)
        logger.info("GraphRAG engine initialized successfully")
    except Exception as e:
        logger.warning("GraphRAG unavailable: %s", e)
        _engine_instance = None

    return _engine_instance


def handle_graph_tool_call(name: str, arguments: dict[str, Any]) -> str:
    """Execute a graph tool and return JSON string result.

    Returns a clear error message if GraphRAG is not configured.
    """
    engine = get_graph_engine()
    if engine is None:
        return json.dumps({
            "error": "GraphRAG is not configured. Set GRAPHRAG_NEO4J_URI, "
                     "GRAPHRAG_NEO4J_USER, and GRAPHRAG_NEO4J_PASSWORD environment "
                     "variables and install the 'graphrag' extra "
                     "(uv sync --extra graphrag).",
            "tool": name,
            "status": "unavailable",
        }, indent=2)

    args = arguments or {}

    if name in _INTENT_MAP:
        from open_medicine.graphrag.reasoning.types_v2 import ClinicalQuery
        intent, get_concepts = _INTENT_MAP[name]
        q = ClinicalQuery(
            intent=intent,
            concepts=get_concepts(args),
            patient_vars=args.get("patient_vars", {}),
        )
        result = engine.query(q)
        return result.model_dump_json(indent=2)

    if name == "query_clinical_graph":
        from open_medicine.graphrag.reasoning.types_v2 import ClinicalQuery
        q = ClinicalQuery(**{k: v for k, v in args.items() if v is not None})
        result = engine.query(q)
        return result.model_dump_json(indent=2)

    if name == "fetch_evidence_chunk":
        from open_medicine.graphrag.graph.queries_v2 import ReasoningQueries
        cypher, params = ReasoningQueries.get_evidence_chunk(args["chunk_id"])
        rows = _conn_instance.execute_read(cypher, params)
        return json.dumps(rows[0] if rows else {"error": "Not found"}, indent=2)

    if name == "list_available_guidelines":
        from open_medicine.graphrag.graph.queries_v2 import ReasoningQueries
        cypher, params = ReasoningQueries.list_guidelines()
        rows = _conn_instance.execute_read(cypher, params)
        return json.dumps({"guidelines": rows}, indent=2)

    return json.dumps({"error": f"Unknown graph tool: {name}"})
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/test_graphrag_tools.py -v`
Expected: PASS (all 5 tests)

**Step 5: Commit**

```bash
git add src/open_medicine/mcp/graphrag_tools.py tests/test_graphrag_tools.py
git commit -m "feat(mcp): add graphrag tool wrapper with graceful degradation"
```

---

### Task 2: Rewrite unified MCP server

**Files:**
- Modify: `src/open_medicine/mcp/server.py`
- Modify: `tests/test_mcp_tools.py`

**Step 1: Write the failing test**

Replace `tests/test_mcp_tools.py` with:

```python
"""Tests for unified MCP server — verify all 10 tools are listed."""
import pytest
import asyncio
import json
from unittest.mock import patch, MagicMock
from open_medicine.mcp.server import handle_list_tools, handle_call_tool


@pytest.fixture
def tools():
    return asyncio.get_event_loop().run_until_complete(handle_list_tools())


class TestToolRegistration:
    def test_tool_count(self, tools):
        """Should have 10 tools (2 calculator + 8 graph)."""
        assert len(tools) == 10

    def test_calculator_tools_present(self, tools):
        names = [t.name for t in tools]
        assert "search_clinical_calculators" in names
        assert "execute_clinical_calculator" in names

    def test_graph_tools_present(self, tools):
        names = [t.name for t in tools]
        assert "check_drug_dosing" in names
        assert "check_contraindications" in names
        assert "check_drug_interaction" in names
        assert "check_monitoring_requirements" in names
        assert "find_treatment_options" in names
        assert "query_clinical_graph" in names
        assert "fetch_evidence_chunk" in names
        assert "list_available_guidelines" in names

    def test_removed_tools_not_present(self, tools):
        """Guidelines, differentials, and semantic search removed."""
        names = [t.name for t in tools]
        assert "search_guidelines" not in names
        assert "retrieve_guideline" not in names
        assert "search_differential_diagnosis" not in names
        assert "get_differential_diagnosis" not in names
        assert "search_medical_knowledge" not in names


class TestCalculatorToolExecution:
    def test_search_calculators_returns_results(self):
        result = asyncio.get_event_loop().run_until_complete(
            handle_call_tool("search_clinical_calculators", {"query": "kidney"})
        )
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert "matches" in data

    def test_execute_unknown_calculator_returns_error(self):
        result = asyncio.get_event_loop().run_until_complete(
            handle_call_tool("execute_clinical_calculator", {
                "calculator_id": "nonexistent",
                "parameters": {}
            })
        )
        assert "Error" in result[0].text or "Unknown" in result[0].text


class TestGraphToolDegradation:
    def test_graph_tool_returns_unavailable_when_no_engine(self):
        with patch("open_medicine.mcp.graphrag_tools.get_graph_engine", return_value=None):
            result = asyncio.get_event_loop().run_until_complete(
                handle_call_tool("check_drug_dosing", {"drug": "lisinopril"})
            )
            data = json.loads(result[0].text)
            assert data["status"] == "unavailable"

    def test_unknown_tool_raises(self):
        with pytest.raises(ValueError, match="Unknown tool"):
            asyncio.get_event_loop().run_until_complete(
                handle_call_tool("nonexistent_tool", {})
            )
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_mcp_tools.py -v`
Expected: FAIL (tool count is 7, not 10; graph tools missing)

**Step 3: Rewrite server.py**

Replace `src/open_medicine/mcp/server.py` with:

```python
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

# ── Tool names that belong to the graph layer ───────────────────────────
_GRAPH_TOOL_NAMES = {t["name"] for t in GRAPHRAG_TOOL_DEFINITIONS}

# ── MCP Server ──────────────────────────────────────────────────────────
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

    # Add graph tools
    for t in GRAPHRAG_TOOL_DEFINITIONS:
        tools.append(
            types.Tool(
                name=t["name"],
                description=t["description"],
                inputSchema=t["inputSchema"],
            )
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
            types.TextContent(
                type="text",
                text=json.dumps({"matches": results}, indent=2),
            )
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
            return [
                types.TextContent(type="text", text=result.model_dump_json(indent=2))
            ]
        except Exception as e:
            return [
                types.TextContent(type="text", text=f"Error executing {calc_id}: {e}")
            ]

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
```

**Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_mcp_tools.py -v`
Expected: PASS (all tests)

**Step 5: Commit**

```bash
git add src/open_medicine/mcp/server.py tests/test_mcp_tools.py
git commit -m "feat(mcp): unify calculator + graphrag into single MCP server"
```

---

### Task 3: Update GraphRAG MCP server to delegate

**Files:**
- Modify: `src/open_medicine/graphrag/server/mcp_server.py`
- Modify: `tests/graphrag/test_mcp_server.py`

**Step 1: Write the failing test**

Add deprecation test to `tests/graphrag/test_mcp_server.py`:

```python
class TestDeprecationNotice:
    def test_module_has_deprecation_warning(self):
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            import importlib
            import open_medicine.graphrag.server.mcp_server as mod
            importlib.reload(mod)
            deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(deprecation_warnings) >= 1
            assert "open-medicine-mcp" in str(deprecation_warnings[0].message)
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/graphrag/test_mcp_server.py::TestDeprecationNotice -v`
Expected: FAIL (no deprecation warning emitted)

**Step 3: Add deprecation warning to mcp_server.py**

Add at the top of `src/open_medicine/graphrag/server/mcp_server.py`, after the imports:

```python
import warnings
warnings.warn(
    "open-medicine-graphrag is deprecated. Use open-medicine-mcp instead, "
    "which includes all graph tools. This entry point will be removed in v1.0.",
    DeprecationWarning,
    stacklevel=2,
)
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/graphrag/test_mcp_server.py::TestDeprecationNotice -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/open_medicine/graphrag/server/mcp_server.py tests/graphrag/test_mcp_server.py
git commit -m "feat(graphrag): deprecate standalone graphrag MCP entry point"
```

---

### Task 4: Update pyproject.toml

**Files:**
- Modify: `pyproject.toml`

**Step 1: Update the graphrag extra to include core graphrag deps as optional for the main package**

In `pyproject.toml`, the `graphrag` extra already has the right deps. No changes needed to extras.

**Step 2: Verify entry points**

Keep both entry points (the deprecated one still works):

```toml
[project.scripts]
open-medicine-mcp = "open_medicine.mcp.server:main"
open-medicine-graphrag = "open_medicine.graphrag.server.mcp_server:main"
open-medicine-graphrag-ingest = "open_medicine.graphrag.ingest:main"
```

No code change needed here — the existing entry points are correct.

**Step 3: Commit (only if changes were made)**

Skip if no changes.

---

### Task 5: Run full test suite and fix breakages

**Step 1: Run calculator tests**

Run: `uv run python -m pytest tests/test_mcp_tools.py tests/test_graphrag_tools.py -v`
Expected: PASS

**Step 2: Run graphrag MCP tests**

Run: `uv run python -m pytest tests/graphrag/test_mcp_server.py -v`
Expected: PASS (existing tests still pass since `TOOL_DEFINITIONS` and `_INTENT_MAP` still exist in the old module)

**Step 3: Run calculator unit tests**

Run: `uv run python -m pytest tests/test_chadsvasc.py tests/test_wells_dvt.py -v`
Expected: PASS (calculators unaffected)

**Step 4: Fix any failures**

If any test references removed tools (guidelines, differentials, semantic search), update assertions.

**Step 5: Commit fixes**

```bash
git add -u
git commit -m "fix: resolve test breakages from MCP server unification"
```

---

### Task 6: Update .mcp.json for local development

**Files:**
- Modify: `.mcp.json` (if it references the old graphrag server separately)

**Step 1: Check current .mcp.json**

Read `.mcp.json` and update any references so that local Claude Code uses the unified `open-medicine-mcp` instead of separate servers.

**Step 2: Update config**

The unified server should be the only MCP server entry. The graphrag server entry can be removed since its tools are now in the unified server.

**Step 3: Commit**

```bash
git add .mcp.json
git commit -m "chore: update mcp config to use unified server"
```

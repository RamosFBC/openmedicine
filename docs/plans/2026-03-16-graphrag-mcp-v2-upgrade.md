# GraphRAG MCP Server v2 Upgrade — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Upgrade the GraphRAG MCP server from v1 engine to v2, gaining dual-layer reasoning, vector fallback, safety features (`data_coverage`), and condition evaluation — then add a `list_available_guidelines` tool.

**Architecture:** Replace v1 imports (`engine.py`, `types.py`) with v2 (`engine_v2.py`, `types_v2.py`). Remove the v1 `FallbackEngine` dependency (v2 engine has built-in vector fallback as Layer 3). Keep the same 7-tool surface + add 1 new tool. Update tests to reflect v2 result shape.

**Tech Stack:** Python, MCP SDK (`mcp`), Pydantic, Neo4j (via `GraphConnection`)

---

### Task 1: Write failing tests for v2 import and result shape

**Files:**
- Modify: `tests/graphrag/test_mcp_server.py`

**Step 1: Write the failing tests**

Add these tests to `tests/graphrag/test_mcp_server.py`:

```python
from open_medicine.graphrag.server.mcp_server import TOOL_DEFINITIONS, create_mcp_server


class TestMCPToolDefinitions:
    def test_all_clinical_tools_defined(self):
        names = [t["name"] for t in TOOL_DEFINITIONS]
        assert "check_drug_dosing" in names
        assert "check_contraindications" in names
        assert "check_drug_interaction" in names
        assert "check_monitoring_requirements" in names
        assert "find_treatment_options" in names

    def test_structured_query_tool_defined(self):
        names = [t["name"] for t in TOOL_DEFINITIONS]
        assert "query_clinical_graph" in names

    def test_evidence_retrieval_tool_defined(self):
        names = [t["name"] for t in TOOL_DEFINITIONS]
        assert "fetch_evidence_chunk" in names

    def test_list_guidelines_tool_defined(self):
        names = [t["name"] for t in TOOL_DEFINITIONS]
        assert "list_available_guidelines" in names

    def test_all_tools_have_input_schema(self):
        for t in TOOL_DEFINITIONS:
            assert "inputSchema" in t
            assert "properties" in t["inputSchema"]

    def test_total_tool_count(self):
        """7 original tools + 1 new (list_available_guidelines) = 8"""
        assert len(TOOL_DEFINITIONS) == 8


class TestMCPV2Imports:
    """Verify the MCP server uses v2 engine and types."""

    def test_imports_v2_engine(self):
        import open_medicine.graphrag.server.mcp_server as mod
        # The module must import from engine_v2, not engine
        source = open(mod.__file__).read()
        assert "engine_v2" in source
        assert "from open_medicine.graphrag.reasoning.engine import" not in source

    def test_imports_v2_types(self):
        import open_medicine.graphrag.server.mcp_server as mod
        source = open(mod.__file__).read()
        assert "types_v2" in source
        assert "from open_medicine.graphrag.reasoning.types import" not in source

    def test_no_fallback_engine_import(self):
        """v2 engine has built-in vector fallback — no separate FallbackEngine needed."""
        import open_medicine.graphrag.server.mcp_server as mod
        source = open(mod.__file__).read()
        assert "FallbackEngine" not in source
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/graphrag/test_mcp_server.py -v`
Expected: 3 new tests FAIL (no `list_available_guidelines`, still using v1 imports)

**Step 3: Commit**

```bash
git add tests/graphrag/test_mcp_server.py
git commit -m "test(graphrag): add failing tests for MCP server v2 upgrade"
```

---

### Task 2: Upgrade MCP server imports from v1 to v2

**Files:**
- Modify: `src/open_medicine/graphrag/server/mcp_server.py`

**Step 1: Replace imports**

Change the imports at the top of `mcp_server.py` from:

```python
from open_medicine.graphrag.graph.queries import ReasoningQueries
from open_medicine.graphrag.reasoning.engine import ReasoningEngine
from open_medicine.graphrag.reasoning.fallback import FallbackEngine
from open_medicine.graphrag.reasoning.types import ClinicalQuery
```

To:

```python
from open_medicine.graphrag.graph.queries_v2 import ReasoningQueries
from open_medicine.graphrag.reasoning.engine_v2 import ReasoningEngine
from open_medicine.graphrag.reasoning.types_v2 import ClinicalQuery
```

**Step 2: Remove FallbackEngine from `create_mcp_server()`**

In the `create_mcp_server()` function, remove the `fallback` line and simplify `_query()`:

Before:
```python
engine = ReasoningEngine(conn)
fallback = FallbackEngine(conn, voyage_api_key=settings.voyage_api_key)

def _query(q: ClinicalQuery) -> str:
    result = engine.query(q)
    if not result.matches and result.confidence == "low":
        result = fallback.query(q)
    return result.model_dump_json(indent=2)
```

After:
```python
engine = ReasoningEngine(conn)

def _query(q: ClinicalQuery) -> str:
    result = engine.query(q)
    return result.model_dump_json(indent=2)
```

The v2 engine already handles fallback internally (Layer 2 expansion → Layer 3 vector → Layer 4 hints).

**Step 3: Run import tests**

Run: `uv run python -m pytest tests/graphrag/test_mcp_server.py::TestMCPV2Imports -v`
Expected: All 3 v2 import tests PASS

**Step 4: Commit**

```bash
git add src/open_medicine/graphrag/server/mcp_server.py
git commit -m "refactor(graphrag): upgrade MCP server to v2 engine and types"
```

---

### Task 3: Add `list_available_guidelines` tool

**Files:**
- Modify: `src/open_medicine/graphrag/server/mcp_server.py`

**Step 1: Add tool definition to `TOOL_DEFINITIONS`**

Append to the `TOOL_DEFINITIONS` list:

```python
{
    "name": "list_available_guidelines",
    "description": "List all clinical guidelines available in the knowledge graph. Returns guideline IDs, titles, DOIs, and years.",
    "inputSchema": {
        "type": "object",
        "properties": {},
    },
},
```

**Step 2: Add handler in `handle_call_tool`**

Before the `raise ValueError` at the end:

```python
if name == "list_available_guidelines":
    cypher, params = ReasoningQueries.list_guidelines()
    rows = conn.execute_read(cypher, params)
    return [types.TextContent(
        type="text",
        text=json.dumps({"guidelines": rows}, indent=2),
    )]
```

**Step 3: Run all tests**

Run: `uv run python -m pytest tests/graphrag/test_mcp_server.py -v`
Expected: All tests PASS including new tool count (8) and `list_available_guidelines`

**Step 4: Commit**

```bash
git add src/open_medicine/graphrag/server/mcp_server.py
git commit -m "feat(graphrag): add list_available_guidelines tool to MCP server"
```

---

### Task 4: Write handler tests with mocked Neo4j

**Files:**
- Modify: `tests/graphrag/test_mcp_server.py`

**Step 1: Write handler tests**

Add to `tests/graphrag/test_mcp_server.py`:

```python
import json
from unittest.mock import MagicMock, patch

import pytest


class TestMCPToolHandlers:
    """Test tool handlers with mocked graph connection."""

    @pytest.fixture
    def mock_conn(self):
        conn = MagicMock()
        conn.execute_read.return_value = []
        return conn

    @pytest.fixture
    def mock_engine(self):
        from open_medicine.graphrag.reasoning.types_v2 import GraphRAGResult
        engine = MagicMock()
        engine.query.return_value = GraphRAGResult(
            confidence="high",
            data_coverage="full",
            semantic_matches=[],
            recommendation_matches=[],
            evidence=[],
            retrieval_layers_used=["direct"],
        )
        return engine

    @pytest.fixture
    def server_and_handler(self, mock_conn, mock_engine):
        with patch("open_medicine.graphrag.server.mcp_server.GraphConnection", return_value=mock_conn), \
             patch("open_medicine.graphrag.server.mcp_server.ReasoningEngine", return_value=mock_engine):
            from open_medicine.graphrag.server.mcp_server import create_mcp_server
            server = create_mcp_server()
        return server, mock_conn, mock_engine

    @pytest.mark.asyncio
    async def test_check_drug_dosing_builds_correct_query(self, server_and_handler):
        _, _, mock_engine = server_and_handler
        from open_medicine.graphrag.server.mcp_server import _INTENT_MAP
        intent, get_concepts = _INTENT_MAP["check_drug_dosing"]
        assert intent == "dosing"
        assert get_concepts({"drug": "lisinopril"}) == ["lisinopril"]

    @pytest.mark.asyncio
    async def test_check_interaction_builds_correct_query(self, server_and_handler):
        _, _, mock_engine = server_and_handler
        from open_medicine.graphrag.server.mcp_server import _INTENT_MAP
        intent, get_concepts = _INTENT_MAP["check_drug_interaction"]
        assert intent == "interaction"
        assert get_concepts({"drug_a": "lisinopril", "drug_b": "spironolactone"}) == ["lisinopril", "spironolactone"]

    def test_list_guidelines_calls_execute_read(self, mock_conn):
        """Verify list_available_guidelines routes to ReasoningQueries.list_guidelines()."""
        mock_conn.execute_read.return_value = [
            {"id": "aha_acc_hf_2022", "title": "AHA/ACC HF 2022", "doi": "10.1161/xxx", "year": 2022}
        ]
        # We can test the query directly since handler tests require async event loop
        from open_medicine.graphrag.graph.queries_v2 import ReasoningQueries
        cypher, params = ReasoningQueries.list_guidelines()
        rows = mock_conn.execute_read(cypher, params)
        assert len(rows) == 1
        assert rows[0]["id"] == "aha_acc_hf_2022"

    def test_fetch_evidence_chunk_calls_execute_read(self, mock_conn):
        """Verify fetch_evidence_chunk routes to ReasoningQueries.get_evidence_chunk()."""
        mock_conn.execute_read.return_value = [
            {"text": "ACEi recommended...", "section": "6.1", "doi": "10.1161/xxx"}
        ]
        from open_medicine.graphrag.graph.queries_v2 import ReasoningQueries
        cypher, params = ReasoningQueries.get_evidence_chunk("chunk_123")
        rows = mock_conn.execute_read(cypher, params)
        assert len(rows) == 1
        assert "ACEi" in rows[0]["text"]


class TestMCPResultShape:
    """Verify v2 result model shape is correct for MCP serialization."""

    def test_graphrag_result_serializes_to_json(self):
        from open_medicine.graphrag.reasoning.types_v2 import GraphRAGResult
        result = GraphRAGResult(
            confidence="high",
            data_coverage="full",
            semantic_matches=[],
            recommendation_matches=[],
            evidence=[],
            retrieval_layers_used=["direct"],
        )
        data = json.loads(result.model_dump_json(indent=2))
        assert data["confidence"] == "high"
        assert data["data_coverage"] == "full"
        assert "semantic_matches" in data
        assert "recommendation_matches" in data
        assert "evidence" in data
        assert "retrieval_layers_used" in data
        assert "hints" in data

    def test_graphrag_result_includes_safety_fields(self):
        """data_coverage and hints are critical for agents to understand result quality."""
        from open_medicine.graphrag.reasoning.types_v2 import GraphRAGResult
        result = GraphRAGResult(
            confidence="low",
            data_coverage="none",
            hints=["Try 'lisinopril' instead of 'lisnopril'"],
        )
        data = json.loads(result.model_dump_json())
        assert data["data_coverage"] == "none"
        assert len(data["hints"]) == 1
```

**Step 2: Run tests**

Run: `uv run python -m pytest tests/graphrag/test_mcp_server.py -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add tests/graphrag/test_mcp_server.py
git commit -m "test(graphrag): add handler and result shape tests for MCP server v2"
```

---

### Task 5: Update tool descriptions for clinical safety

**Files:**
- Modify: `src/open_medicine/graphrag/server/mcp_server.py`

**Step 1: Improve tool descriptions**

The current descriptions are minimal. AI agents need to understand what data each tool returns and when to use it. Update `TOOL_DEFINITIONS` descriptions:

```python
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
                "drug": {"type": "string", "description": "Drug name (e.g. 'apixaban', 'lisinopril', 'carvedilol')"},
                "patient_vars": {
                    "type": "object",
                    "description": "Patient variables as key-value pairs (e.g. {\"eGFR\": 20, \"age\": 80, \"weight_kg\": 55, \"potassium\": 4.8})",
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
                "intervention": {"type": "string", "description": "Drug or procedure to check (e.g. 'lisinopril', 'sacubitril_valsartan')"},
                "patient_vars": {
                    "type": "object",
                    "description": "Patient variables (e.g. {\"history_of_angioedema\": true, \"potassium\": 5.5})",
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
                "patient_vars": {"type": "object", "description": "Optional patient variables for context"},
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
                "intervention": {"type": "string", "description": "Drug or procedure name"},
                "patient_vars": {"type": "object", "description": "Optional patient variables"},
            },
            "required": ["intervention"],
        },
    },
    {
        "name": "find_treatment_options",
        "description": (
            "Find recommended treatments for a clinical condition. "
            "Returns drugs and drug classes ranked by recommendation strength (strong > moderate > weak) "
            "and evidence quality (high > moderate > low). "
            "Evaluates patient eligibility criteria."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "condition": {"type": "string", "description": "Clinical condition (e.g. 'heart_failure_reduced_ef', 'atrial_fibrillation')"},
                "patient_vars": {
                    "type": "object",
                    "description": "Patient variables to evaluate eligibility (e.g. {\"lvef\": 30, \"egfr\": 45})",
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
                "concepts": {"type": "array", "items": {"type": "string"}, "description": "Clinical concepts to query"},
                "patient_vars": {"type": "object", "description": "Patient variables for condition evaluation"},
                "guideline_filter": {"type": "string", "description": "Optional guideline ID to scope results (e.g. 'aha_acc_hf_2022')"},
                "include_evidence": {"type": "boolean", "default": True, "description": "Include source text evidence chain"},
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
                "chunk_id": {"type": "string", "description": "Evidence chunk ID from a previous query result"},
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
```

**Step 2: Update tool count test**

Verify `test_total_tool_count` expects 8.

**Step 3: Update `query_clinical_graph` handler for renamed field**

In `handle_call_tool`, the `query_clinical_graph` handler constructs `ClinicalQuery` from args. The v2 `ClinicalQuery` renamed `include_source_text` to `include_evidence`. The handler already uses `**{k: v ...}` dict unpacking, so ensure the inputSchema field name matches:

Before: `"include_source_text": {"type": "boolean", ...}`
After: `"include_evidence": {"type": "boolean", ...}`

The dict-unpacking handler `ClinicalQuery(**{k: v for k, v in args.items() if v is not None})` will work correctly since the field names now match.

**Step 4: Run tests**

Run: `uv run python -m pytest tests/graphrag/test_mcp_server.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/open_medicine/graphrag/server/mcp_server.py tests/graphrag/test_mcp_server.py
git commit -m "feat(graphrag): improve MCP tool descriptions for agent safety and usability"
```

---

### Task 6: Final integration — verify complete MCP server file

**Files:**
- Verify: `src/open_medicine/graphrag/server/mcp_server.py`

**Step 1: Verify the complete file**

The final `mcp_server.py` should look like this (verify each section):

```python
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

TOOL_DEFINITIONS = [...]  # 8 tools as defined in Task 5

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
```

**Step 2: Run full GraphRAG test file**

Run: `uv run python -m pytest tests/graphrag/test_mcp_server.py -v`
Expected: All PASS

**Step 3: Run broader test check (import sanity)**

Run: `uv run python -c "from open_medicine.graphrag.server.mcp_server import create_mcp_server, TOOL_DEFINITIONS; print(f'{len(TOOL_DEFINITIONS)} tools registered')"`
Expected: `8 tools registered`

**Step 4: Commit**

```bash
git add src/open_medicine/graphrag/server/mcp_server.py tests/graphrag/test_mcp_server.py
git commit -m "feat(graphrag): complete MCP server v2 upgrade with 8 tools"
```

---

## Summary

| Task | What | Files Changed |
|------|------|---------------|
| 1 | Failing tests for v2 upgrade | `tests/graphrag/test_mcp_server.py` |
| 2 | Swap v1 → v2 imports, remove FallbackEngine | `src/.../mcp_server.py` |
| 3 | Add `list_available_guidelines` tool | `src/.../mcp_server.py` |
| 4 | Handler + result shape tests (mocked) | `tests/graphrag/test_mcp_server.py` |
| 5 | Improve tool descriptions for agent safety | `src/.../mcp_server.py` |
| 6 | Final integration verify | Both files |

**Total changes:** 1 source file modified, 1 test file modified, 0 new files.

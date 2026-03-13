# GraphRAG Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a GraphRAG clinical decision support module that extracts logic nodes from guideline PDFs into a Neo4j knowledge graph, queryable via MCP tools and REST API.

**Architecture:** New `src/open_medicine/graphrag/` module, parallel to existing `mcp/`. Typed LogicNode reification in Neo4j. Deterministic graph traversal at runtime with LLM fallback. FastAPI REST + MCP-over-SSE.

**Tech Stack:** Neo4j 5.x, Docling, FastAPI, ScispaCy, Anthropic SDK, Pydantic v2

**Design Doc:** `docs/plans/2026-03-13-graphrag-design.md`

---

## Phase 1: Project Setup & Graph Schema (Foundation)

### Task 1: Add graphrag dependencies to pyproject.toml

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add the graphrag optional dependency group**

Add after the `embeddings` group in `pyproject.toml`:

```toml
graphrag = [
    "neo4j>=5.0.0",
    "docling>=2.0.0",
    "fastapi>=0.110.0",
    "uvicorn>=0.30.0",
    "scispacy>=0.5.0",
    "httpx>=0.27.0",
    "anthropic>=0.40.0",
]
```

**Step 2: Install and verify**

Run: `uv sync --extra graphrag --extra test`
Expected: All dependencies resolve successfully.

**Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "feat(graphrag): add graphrag optional dependencies"
```

---

### Task 2: Create config module

**Files:**
- Create: `src/open_medicine/graphrag/__init__.py`
- Create: `src/open_medicine/graphrag/config.py`

**Step 1: Create package init**

```python
# src/open_medicine/graphrag/__init__.py
"""GraphRAG Clinical Decision Support System."""
```

**Step 2: Write config module**

```python
# src/open_medicine/graphrag/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class GraphRAGSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GRAPHRAG_")

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "openmedicine"

    anthropic_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    api_keys: str = ""  # comma-separated
    rate_limit: int = 100
    port: int = 8000

    @property
    def valid_api_keys(self) -> set[str]:
        return {k.strip() for k in self.api_keys.split(",") if k.strip()}


def get_settings() -> GraphRAGSettings:
    return GraphRAGSettings()
```

**Step 3: Commit**

```bash
git add src/open_medicine/graphrag/
git commit -m "feat(graphrag): add config module with env-based settings"
```

---

### Task 3: Create graph schema Pydantic models

**Files:**
- Create: `src/open_medicine/graphrag/graph/__init__.py`
- Create: `src/open_medicine/graphrag/graph/schema.py`
- Create: `tests/graphrag/__init__.py`
- Create: `tests/graphrag/test_schema.py`

**Step 1: Write failing tests for schema validation**

```python
# tests/graphrag/test_schema.py
import pytest
from open_medicine.graphrag.graph.schema import (
    Concept, ConceptType,
    LogicNode, LogicNodeType, Condition,
    EvidenceChunk,
    Guideline,
    PatientVariable, VariableType,
)


class TestConcept:
    def test_valid_drug(self):
        c = Concept(id="apixaban", name="Apixaban", type=ConceptType.DRUG, snomed_code="703899003")
        assert c.id == "apixaban"
        assert c.type == ConceptType.DRUG

    def test_aliases_default_empty(self):
        c = Concept(id="x", name="X", type=ConceptType.DRUG)
        assert c.aliases == []

    def test_requires_id_and_name(self):
        with pytest.raises(Exception):
            Concept(type=ConceptType.DRUG)


class TestCondition:
    def test_valid_condition(self):
        c = Condition(variable="eGFR", operator="<", threshold=25, unit="mL/min")
        assert c.variable == "eGFR"
        assert c.threshold == 25

    def test_valid_operators(self):
        for op in ["<", "<=", ">", ">=", "==", "!="]:
            c = Condition(variable="x", operator=op, threshold=1)
            assert c.operator == op

    def test_invalid_operator(self):
        with pytest.raises(Exception):
            Condition(variable="x", operator="~", threshold=1)


class TestLogicNode:
    def test_valid_dosing_node(self):
        ln = LogicNode(
            id="ln_001",
            type=LogicNodeType.DOSING,
            conditions=[Condition(variable="eGFR", operator="<", threshold=25, unit="mL/min")],
            action="contraindicated",
            action_detail="Do not use if eGFR < 25",
            strength="Strong/A",
            guideline_id="acc_aha_af_2023",
            page=47,
        )
        assert ln.type == LogicNodeType.DOSING

    def test_valid_types(self):
        for t in ["dosing", "contraindication", "interaction", "monitoring", "treatment_selection", "diagnostic_criteria"]:
            assert LogicNodeType(t) == t

    def test_conditions_list_required(self):
        with pytest.raises(Exception):
            LogicNode(
                id="ln_001", type=LogicNodeType.DOSING,
                action="contraindicated", action_detail="x",
                strength="Strong/A", guideline_id="g", page=1,
            )


class TestEvidenceChunk:
    def test_valid_chunk(self):
        ec = EvidenceChunk(
            id="chunk_001", text="Apixaban should not be used...",
            guideline_id="acc_aha_af_2023", section="anticoagulation",
            page_start=47, page_end=47,
        )
        assert ec.guideline_id == "acc_aha_af_2023"

    def test_parent_chunk_optional(self):
        ec = EvidenceChunk(
            id="c1", text="t", guideline_id="g", section="s",
            page_start=1, page_end=1,
        )
        assert ec.parent_chunk_id is None


class TestGuideline:
    def test_valid_guideline(self):
        g = Guideline(
            id="acc_aha_af_2023",
            title="2023 ACC/AHA AF Guideline",
            doi="10.1161/CIR.0000000000001193",
            year=2023,
            organization="ACC/AHA",
            total_pages=287,
        )
        assert g.year == 2023


class TestPatientVariable:
    def test_valid_continuous(self):
        pv = PatientVariable(
            id="eGFR", name="Estimated GFR",
            unit="mL/min/1.73m²", type=VariableType.CONTINUOUS,
        )
        assert pv.type == VariableType.CONTINUOUS

    def test_valid_types(self):
        for t in ["continuous", "categorical", "boolean"]:
            assert VariableType(t) == t
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/graphrag/test_schema.py -v`
Expected: FAIL — modules don't exist yet.

**Step 3: Implement schema models**

```python
# src/open_medicine/graphrag/graph/__init__.py
"""Graph schema and Neo4j integration."""
```

```python
# src/open_medicine/graphrag/graph/schema.py
from __future__ import annotations
from enum import StrEnum
from pydantic import BaseModel, Field, field_validator


class ConceptType(StrEnum):
    DRUG = "drug"
    DISEASE = "disease"
    LAB = "lab"
    PROCEDURE = "procedure"
    SYMPTOM = "symptom"


class LogicNodeType(StrEnum):
    DOSING = "dosing"
    CONTRAINDICATION = "contraindication"
    INTERACTION = "interaction"
    MONITORING = "monitoring"
    TREATMENT_SELECTION = "treatment_selection"
    DIAGNOSTIC_CRITERIA = "diagnostic_criteria"


class VariableType(StrEnum):
    CONTINUOUS = "continuous"
    CATEGORICAL = "categorical"
    BOOLEAN = "boolean"


VALID_OPERATORS = {"<", "<=", ">", ">=", "==", "!="}


class Condition(BaseModel):
    variable: str = Field(description="Patient variable name, e.g. eGFR")
    operator: str = Field(description="Comparison operator")
    threshold: float | str = Field(description="Threshold value")
    unit: str | None = Field(default=None, description="Unit of measurement")

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v: str) -> str:
        if v not in VALID_OPERATORS:
            raise ValueError(f"Invalid operator '{v}'. Must be one of {VALID_OPERATORS}")
        return v


class Concept(BaseModel):
    id: str = Field(description="Canonical identifier")
    name: str = Field(description="Human-readable name")
    type: ConceptType = Field(description="Entity type")
    snomed_code: str | None = Field(default=None, description="SNOMED-CT code")
    loinc_code: str | None = Field(default=None, description="LOINC code")
    fhir_code: str | None = Field(default=None, description="FHIR code")
    aliases: list[str] = Field(default_factory=list, description="Alternative names")


class LogicNode(BaseModel):
    id: str = Field(description="Unique identifier")
    type: LogicNodeType = Field(description="Rule type")
    conditions: list[Condition] = Field(description="Conditions that trigger this rule")
    action: str = Field(description="Action to take")
    action_detail: str = Field(description="Human-readable explanation")
    strength: str = Field(description="Evidence strength (e.g. Strong/A)")
    guideline_id: str = Field(description="Source guideline ID")
    page: int = Field(description="Source page number")


class EvidenceChunk(BaseModel):
    id: str = Field(description="Deterministic hash ID")
    text: str = Field(description="Raw source text")
    guideline_id: str = Field(description="Source guideline ID")
    section: str = Field(description="Section name")
    page_start: int = Field(description="Start page")
    page_end: int = Field(description="End page")
    parent_chunk_id: str | None = Field(default=None, description="Parent chunk ID")
    embedding: list[float] | None = Field(default=None, description="Vector embedding")


class Guideline(BaseModel):
    id: str = Field(description="Unique guideline identifier")
    title: str = Field(description="Full guideline title")
    doi: str = Field(description="DOI of the guideline")
    year: int = Field(description="Publication year")
    organization: str = Field(description="Issuing organization")
    total_pages: int = Field(description="Total pages in source PDF")


class PatientVariable(BaseModel):
    id: str = Field(description="Variable identifier (e.g. eGFR)")
    name: str = Field(description="Human-readable name")
    unit: str = Field(description="Unit of measurement")
    loinc_code: str | None = Field(default=None, description="LOINC code")
    type: VariableType = Field(description="Variable type")
```

**Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/graphrag/test_schema.py -v`
Expected: All PASS.

**Step 5: Commit**

```bash
git add src/open_medicine/graphrag/graph/ tests/graphrag/
git commit -m "feat(graphrag): add graph schema Pydantic models with tests"
```

---

### Task 4: Neo4j connection manager

**Files:**
- Create: `src/open_medicine/graphrag/graph/connection.py`
- Create: `tests/graphrag/test_connection.py`

**Step 1: Write failing test**

```python
# tests/graphrag/test_connection.py
from unittest.mock import patch, MagicMock
from open_medicine.graphrag.graph.connection import GraphConnection


class TestGraphConnection:
    def test_creates_driver(self):
        with patch("neo4j.GraphDatabase.driver") as mock_driver:
            conn = GraphConnection(uri="bolt://localhost:7687", user="neo4j", password="test")
            mock_driver.assert_called_once_with("bolt://localhost:7687", auth=("neo4j", "test"))

    def test_close(self):
        with patch("neo4j.GraphDatabase.driver") as mock_driver:
            mock_instance = MagicMock()
            mock_driver.return_value = mock_instance
            conn = GraphConnection(uri="bolt://localhost:7687", user="neo4j", password="test")
            conn.close()
            mock_instance.close.assert_called_once()

    def test_context_manager(self):
        with patch("neo4j.GraphDatabase.driver") as mock_driver:
            mock_instance = MagicMock()
            mock_driver.return_value = mock_instance
            with GraphConnection(uri="bolt://localhost:7687", user="neo4j", password="test") as conn:
                assert conn is not None
            mock_instance.close.assert_called_once()

    def test_execute_query(self):
        with patch("neo4j.GraphDatabase.driver") as mock_driver:
            mock_instance = MagicMock()
            mock_session = MagicMock()
            mock_result = MagicMock()
            mock_result.data.return_value = [{"n": 1}]
            mock_session.run.return_value = mock_result
            mock_instance.session.return_value.__enter__ = lambda s: mock_session
            mock_instance.session.return_value.__exit__ = MagicMock(return_value=False)
            mock_driver.return_value = mock_instance

            conn = GraphConnection(uri="bolt://localhost:7687", user="neo4j", password="test")
            results = conn.execute_read("MATCH (n) RETURN n LIMIT 1")
            assert results == [{"n": 1}]
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/graphrag/test_connection.py -v`
Expected: FAIL — module doesn't exist.

**Step 3: Implement connection manager**

```python
# src/open_medicine/graphrag/graph/connection.py
from __future__ import annotations
from typing import Any
import neo4j


class GraphConnection:
    def __init__(self, uri: str, user: str, password: str) -> None:
        self._driver = neo4j.GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self._driver.close()

    def __enter__(self) -> GraphConnection:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def execute_read(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict]:
        with self._driver.session() as session:
            result = session.run(query, parameters or {})
            return result.data()

    def execute_write(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict]:
        with self._driver.session() as session:
            result = session.run(query, parameters or {})
            return result.data()

    def execute_write_tx(self, queries: list[tuple[str, dict[str, Any]]]) -> None:
        with self._driver.session() as session:
            with session.begin_transaction() as tx:
                for query, params in queries:
                    tx.run(query, params)
                tx.commit()
```

**Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/graphrag/test_connection.py -v`
Expected: All PASS.

**Step 5: Commit**

```bash
git add src/open_medicine/graphrag/graph/connection.py tests/graphrag/test_connection.py
git commit -m "feat(graphrag): add Neo4j connection manager"
```

---

### Task 5: Neo4j index and constraint creation

**Files:**
- Create: `src/open_medicine/graphrag/graph/indexes.py`
- Create: `tests/graphrag/test_indexes.py`

**Step 1: Write failing test**

```python
# tests/graphrag/test_indexes.py
from open_medicine.graphrag.graph.indexes import get_index_statements, get_constraint_statements


class TestIndexStatements:
    def test_constraints_include_all_node_types(self):
        stmts = get_constraint_statements()
        text = " ".join(stmts)
        for label in ["Concept", "LogicNode", "EvidenceChunk", "Guideline", "PatientVariable"]:
            assert label in text, f"Missing constraint for {label}"

    def test_indexes_include_key_properties(self):
        stmts = get_index_statements()
        text = " ".join(stmts)
        assert "snomed_code" in text
        assert "LogicNode" in text

    def test_returns_list_of_strings(self):
        for stmt in get_constraint_statements():
            assert isinstance(stmt, str)
            assert "CREATE" in stmt or "DROP" in stmt or stmt.startswith("CREATE")
```

**Step 2: Run to verify fail, then implement**

```python
# src/open_medicine/graphrag/graph/indexes.py


def get_constraint_statements() -> list[str]:
    return [
        "CREATE CONSTRAINT concept_id IF NOT EXISTS FOR (n:Concept) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT logic_node_id IF NOT EXISTS FOR (n:LogicNode) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT evidence_chunk_id IF NOT EXISTS FOR (n:EvidenceChunk) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT guideline_id IF NOT EXISTS FOR (n:Guideline) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT patient_variable_id IF NOT EXISTS FOR (n:PatientVariable) REQUIRE n.id IS UNIQUE",
    ]


def get_index_statements() -> list[str]:
    return [
        "CREATE INDEX concept_snomed IF NOT EXISTS FOR (n:Concept) ON (n.snomed_code)",
        "CREATE INDEX concept_type IF NOT EXISTS FOR (n:Concept) ON (n.type)",
        "CREATE INDEX logic_node_type IF NOT EXISTS FOR (n:LogicNode) ON (n.type)",
        "CREATE INDEX logic_node_guideline IF NOT EXISTS FOR (n:LogicNode) ON (n.guideline_id)",
        "CREATE FULLTEXT INDEX evidence_text IF NOT EXISTS FOR (n:EvidenceChunk) ON EACH [n.text]",
    ]
```

**Step 3: Run tests**

Run: `uv run python -m pytest tests/graphrag/test_indexes.py -v`
Expected: All PASS.

**Step 4: Commit**

```bash
git add src/open_medicine/graphrag/graph/indexes.py tests/graphrag/test_indexes.py
git commit -m "feat(graphrag): add Neo4j index and constraint definitions"
```

---

### Task 6: Docker Compose for local Neo4j

**Files:**
- Create: `docker-compose.yml`

**Step 1: Create docker-compose.yml**

```yaml
services:
  neo4j:
    image: neo4j:5-community
    ports:
      - "7687:7687"
      - "7474:7474"
    environment:
      NEO4J_AUTH: neo4j/openmedicine
      NEO4J_PLUGINS: '["apoc"]'
    volumes:
      - neo4j_data:/data

volumes:
  neo4j_data:
```

**Step 2: Commit**

```bash
git add docker-compose.yml
git commit -m "feat(graphrag): add docker-compose for local Neo4j"
```

---

## Phase 2: Ingestion Pipeline

### Task 7: PDF parser with Docling

**Files:**
- Create: `src/open_medicine/graphrag/ingestion/__init__.py`
- Create: `src/open_medicine/graphrag/ingestion/parser.py`
- Create: `tests/graphrag/test_parser.py`
- Create: `tests/graphrag/fixtures/sample_guideline.md` (synthetic test fixture)

**Step 1: Create synthetic test fixture**

Create a small markdown file simulating Docling output (we test parsing logic, not Docling itself):

```markdown
# Test Guideline for Hypertension 2024

## 1. Pharmacotherapy

### 1.1 First-Line Agents

ACE inhibitors (e.g., lisinopril 10-40 mg daily) are recommended as first-line therapy for hypertension in patients without contraindications.

**Contraindication:** ACE inhibitors are contraindicated in pregnancy and in patients with a history of angioedema.

### 1.2 Renal Dosing Adjustments

| Drug | eGFR 30-60 | eGFR < 30 |
|------|-----------|-----------|
| Lisinopril | 5-10 mg | 2.5-5 mg |
| Enalapril | 2.5-5 mg | 2.5 mg |

## 2. Monitoring

### 2.1 Lab Monitoring

Check serum creatinine and potassium within 1-2 weeks of initiating or titrating an ACE inhibitor.
```

**Step 2: Write failing tests**

```python
# tests/graphrag/test_parser.py
import pytest
from pathlib import Path
from open_medicine.graphrag.ingestion.parser import (
    ParsedSection, ParsedDocument, parse_markdown,
)

FIXTURES = Path(__file__).parent / "fixtures"


class TestParseMarkdown:
    def test_extracts_top_level_title(self):
        doc = parse_markdown(FIXTURES / "sample_guideline.md", guideline_id="test_htn_2024")
        assert doc.title == "Test Guideline for Hypertension 2024"
        assert doc.guideline_id == "test_htn_2024"

    def test_extracts_sections_with_hierarchy(self):
        doc = parse_markdown(FIXTURES / "sample_guideline.md", guideline_id="test_htn_2024")
        headings = [s.heading for s in doc.sections]
        assert "1. Pharmacotherapy" in headings
        assert "1.1 First-Line Agents" in headings
        assert "1.2 Renal Dosing Adjustments" in headings

    def test_section_levels(self):
        doc = parse_markdown(FIXTURES / "sample_guideline.md", guideline_id="test_htn_2024")
        section_map = {s.heading: s for s in doc.sections}
        assert section_map["1. Pharmacotherapy"].level == 2
        assert section_map["1.1 First-Line Agents"].level == 3

    def test_parent_heading_assigned(self):
        doc = parse_markdown(FIXTURES / "sample_guideline.md", guideline_id="test_htn_2024")
        section_map = {s.heading: s for s in doc.sections}
        assert section_map["1.1 First-Line Agents"].parent_heading == "1. Pharmacotherapy"

    def test_table_detected(self):
        doc = parse_markdown(FIXTURES / "sample_guideline.md", guideline_id="test_htn_2024")
        section_map = {s.heading: s for s in doc.sections}
        renal = section_map["1.2 Renal Dosing Adjustments"]
        assert len(renal.tables) > 0
        assert "Lisinopril" in str(renal.tables[0])

    def test_content_not_empty(self):
        doc = parse_markdown(FIXTURES / "sample_guideline.md", guideline_id="test_htn_2024")
        for s in doc.sections:
            assert len(s.content) > 0
```

**Step 3: Run tests to verify they fail**

Run: `uv run python -m pytest tests/graphrag/test_parser.py -v`
Expected: FAIL — module doesn't exist.

**Step 4: Implement parser**

```python
# src/open_medicine/graphrag/ingestion/__init__.py
"""Ingestion pipeline for PDF parsing, chunking, and extraction."""
```

```python
# src/open_medicine/graphrag/ingestion/parser.py
from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ParsedSection:
    heading: str
    level: int
    content: str
    tables: list[list[dict[str, str]]] = field(default_factory=list)
    parent_heading: str | None = None


@dataclass
class ParsedDocument:
    guideline_id: str
    title: str
    sections: list[ParsedSection] = field(default_factory=list)


def _parse_table(lines: list[str]) -> list[dict[str, str]]:
    """Parse a markdown table into list of row dicts."""
    if len(lines) < 3:
        return []
    headers = [h.strip() for h in lines[0].strip("|").split("|")]
    rows = []
    for line in lines[2:]:  # skip header + separator
        vals = [v.strip() for v in line.strip("|").split("|")]
        rows.append(dict(zip(headers, vals)))
    return rows


def parse_markdown(path: Path, guideline_id: str) -> ParsedDocument:
    """Parse a markdown file into a structured ParsedDocument."""
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")

    title = ""
    sections: list[ParsedSection] = []
    heading_stack: list[tuple[int, str]] = []  # (level, heading)

    current_heading = ""
    current_level = 0
    current_lines: list[str] = []

    def _flush():
        nonlocal current_heading, current_level, current_lines
        if not current_heading:
            return
        content_text = "\n".join(current_lines).strip()
        tables: list[list[dict[str, str]]] = []
        # Extract tables from content
        table_lines: list[str] = []
        non_table_lines: list[str] = []
        in_table = False
        for cl in current_lines:
            if "|" in cl and not in_table:
                in_table = True
                table_lines = [cl]
            elif in_table and "|" in cl:
                table_lines.append(cl)
            elif in_table:
                in_table = False
                parsed = _parse_table(table_lines)
                if parsed:
                    tables.append(parsed)
                table_lines = []
                non_table_lines.append(cl)
            else:
                non_table_lines.append(cl)
        if table_lines:
            parsed = _parse_table(table_lines)
            if parsed:
                tables.append(parsed)

        parent = None
        for lvl, hdg in reversed(heading_stack):
            if lvl < current_level:
                parent = hdg
                break

        sections.append(ParsedSection(
            heading=current_heading,
            level=current_level,
            content=content_text,
            tables=tables,
            parent_heading=parent,
        ))

    for line in lines:
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            _flush()
            current_level = len(heading_match.group(1))
            current_heading = heading_match.group(2).strip()
            current_lines = []
            if current_level == 1 and not title:
                title = current_heading
            else:
                # Update heading stack
                heading_stack = [(l, h) for l, h in heading_stack if l < current_level]
                heading_stack.append((current_level, current_heading))
        else:
            current_lines.append(line)

    _flush()

    # Remove the title section if it was the h1
    sections = [s for s in sections if s.heading != title]

    return ParsedDocument(guideline_id=guideline_id, title=title, sections=sections)
```

**Step 5: Run tests to verify they pass**

Run: `uv run python -m pytest tests/graphrag/test_parser.py -v`
Expected: All PASS.

**Step 6: Commit**

```bash
git add src/open_medicine/graphrag/ingestion/ tests/graphrag/test_parser.py tests/graphrag/fixtures/
git commit -m "feat(graphrag): add markdown parser with hierarchy and table extraction"
```

---

### Task 8: Hierarchical chunker

**Files:**
- Create: `src/open_medicine/graphrag/ingestion/chunker.py`
- Create: `tests/graphrag/test_chunker.py`

**Step 1: Write failing tests**

```python
# tests/graphrag/test_chunker.py
import pytest
from open_medicine.graphrag.ingestion.parser import ParsedSection, ParsedDocument
from open_medicine.graphrag.ingestion.chunker import chunk_document, Chunk


def _make_doc(sections: list[ParsedSection]) -> ParsedDocument:
    return ParsedDocument(guideline_id="test_001", title="Test", sections=sections)


class TestChunker:
    def test_short_section_becomes_single_child(self):
        doc = _make_doc([
            ParsedSection(heading="Section A", level=2, content="Short text.", parent_heading=None),
        ])
        chunks = chunk_document(doc)
        children = [c for c in chunks if c.parent_chunk_id is not None]
        parents = [c for c in chunks if c.parent_chunk_id is None]
        assert len(parents) == 1
        assert len(children) == 1

    def test_long_section_splits_into_children(self):
        long_text = "This is a sentence. " * 200  # ~800 tokens
        doc = _make_doc([
            ParsedSection(heading="Long Section", level=2, content=long_text, parent_heading=None),
        ])
        chunks = chunk_document(doc, max_tokens=200)
        children = [c for c in chunks if c.parent_chunk_id is not None]
        assert len(children) > 1

    def test_table_kept_atomic(self):
        doc = _make_doc([
            ParsedSection(
                heading="Table Section", level=2, content="Intro text.",
                tables=[[{"Drug": "A", "Dose": "10mg"}, {"Drug": "B", "Dose": "20mg"}]],
                parent_heading=None,
            ),
        ])
        chunks = chunk_document(doc)
        table_chunks = [c for c in chunks if "Drug" in c.text and "Dose" in c.text]
        assert len(table_chunks) >= 1

    def test_chunk_ids_deterministic(self):
        doc = _make_doc([
            ParsedSection(heading="S", level=2, content="Content here.", parent_heading=None),
        ])
        chunks1 = chunk_document(doc)
        chunks2 = chunk_document(doc)
        assert [c.id for c in chunks1] == [c.id for c in chunks2]

    def test_chunk_has_guideline_and_section(self):
        doc = _make_doc([
            ParsedSection(heading="My Section", level=2, content="Text.", parent_heading=None),
        ])
        chunks = chunk_document(doc)
        for c in chunks:
            assert c.guideline_id == "test_001"
            assert c.section == "My Section"
```

**Step 2: Run to verify fail, then implement**

```python
# src/open_medicine/graphrag/ingestion/chunker.py
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass, field
from open_medicine.graphrag.ingestion.parser import ParsedDocument


@dataclass
class Chunk:
    id: str
    text: str
    guideline_id: str
    section: str
    parent_chunk_id: str | None = None


def _hash_id(guideline_id: str, section: str, index: int, is_parent: bool) -> str:
    key = f"{guideline_id}:{section}:{index}:{'parent' if is_parent else 'child'}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _estimate_tokens(text: str) -> int:
    return len(text.split())


def _split_text(text: str, max_tokens: int, overlap: int = 50) -> list[str]:
    words = text.split()
    if len(words) <= max_tokens:
        return [text]
    chunks = []
    start = 0
    while start < len(words):
        end = start + max_tokens
        chunks.append(" ".join(words[start:end]))
        start = end - overlap
    return chunks


def chunk_document(doc: ParsedDocument, max_tokens: int = 400, overlap: int = 50) -> list[Chunk]:
    chunks: list[Chunk] = []

    for sec_idx, section in enumerate(doc.sections):
        parent_id = _hash_id(doc.guideline_id, section.heading, sec_idx, is_parent=True)

        # Parent chunk = full section content
        parent_text = section.content
        chunks.append(Chunk(
            id=parent_id,
            text=parent_text,
            guideline_id=doc.guideline_id,
            section=section.heading,
            parent_chunk_id=None,
        ))

        # Child chunks from text
        text_parts = _split_text(section.content, max_tokens, overlap)
        child_idx = 0
        for part in text_parts:
            child_id = _hash_id(doc.guideline_id, section.heading, child_idx, is_parent=False)
            chunks.append(Chunk(
                id=child_id,
                text=part,
                guideline_id=doc.guideline_id,
                section=section.heading,
                parent_chunk_id=parent_id,
            ))
            child_idx += 1

        # Table chunks (atomic)
        for table in section.tables:
            table_text = json.dumps(table, indent=2)
            child_id = _hash_id(doc.guideline_id, section.heading, child_idx, is_parent=False)
            chunks.append(Chunk(
                id=child_id,
                text=table_text,
                guideline_id=doc.guideline_id,
                section=section.heading,
                parent_chunk_id=parent_id,
            ))
            child_idx += 1

    return chunks
```

**Step 3: Run tests**

Run: `uv run python -m pytest tests/graphrag/test_chunker.py -v`
Expected: All PASS.

**Step 4: Commit**

```bash
git add src/open_medicine/graphrag/ingestion/chunker.py tests/graphrag/test_chunker.py
git commit -m "feat(graphrag): add hierarchical chunker with parent-child strategy"
```

---

### Task 9: Entity linker (SNOMED/LOINC mapping)

**Files:**
- Create: `src/open_medicine/graphrag/ingestion/linker.py`
- Create: `tests/graphrag/test_linker.py`

**Step 1: Write failing tests**

```python
# tests/graphrag/test_linker.py
from open_medicine.graphrag.ingestion.linker import link_entity, LinkedEntity


class TestLinker:
    def test_known_drug(self):
        result = link_entity("apixaban", "drug")
        assert result is not None
        assert result.snomed_code is not None
        assert result.canonical_name == "Apixaban"

    def test_known_lab(self):
        result = link_entity("eGFR", "lab")
        assert result is not None
        assert result.loinc_code is not None

    def test_unknown_entity_returns_none(self):
        result = link_entity("xyznonexistent", "drug")
        assert result is None

    def test_case_insensitive(self):
        r1 = link_entity("Apixaban", "drug")
        r2 = link_entity("apixaban", "drug")
        assert r1 is not None and r2 is not None
        assert r1.snomed_code == r2.snomed_code

    def test_alias_resolution(self):
        result = link_entity("Eliquis", "drug")
        assert result is not None
        assert result.canonical_name == "Apixaban"
```

**Step 2: Run to verify fail, then implement**

```python
# src/open_medicine/graphrag/ingestion/linker.py
from __future__ import annotations
from dataclasses import dataclass

# Curated mapping — expanded as guidelines are ingested.
# This is the entity dictionary for the 5 initial guidelines.

@dataclass
class LinkedEntity:
    canonical_name: str
    entity_type: str
    snomed_code: str | None = None
    loinc_code: str | None = None
    fhir_code: str | None = None


_DRUG_MAP: dict[str, LinkedEntity] = {
    "apixaban": LinkedEntity("Apixaban", "drug", snomed_code="703899003"),
    "eliquis": LinkedEntity("Apixaban", "drug", snomed_code="703899003"),
    "rivaroxaban": LinkedEntity("Rivaroxaban", "drug", snomed_code="703901006"),
    "xarelto": LinkedEntity("Rivaroxaban", "drug", snomed_code="703901006"),
    "warfarin": LinkedEntity("Warfarin", "drug", snomed_code="372756006"),
    "dabigatran": LinkedEntity("Dabigatran", "drug", snomed_code="700029008"),
    "edoxaban": LinkedEntity("Edoxaban", "drug", snomed_code="712519002"),
    "lisinopril": LinkedEntity("Lisinopril", "drug", snomed_code="386873009"),
    "enalapril": LinkedEntity("Enalapril", "drug", snomed_code="372658000"),
    "metoprolol": LinkedEntity("Metoprolol", "drug", snomed_code="372826007"),
    "amiodarone": LinkedEntity("Amiodarone", "drug", snomed_code="372821002"),
    "digoxin": LinkedEntity("Digoxin", "drug", snomed_code="387461009"),
    "atorvastatin": LinkedEntity("Atorvastatin", "drug", snomed_code="373444002"),
    "rosuvastatin": LinkedEntity("Rosuvastatin", "drug", snomed_code="412295007"),
    "heparin": LinkedEntity("Heparin", "drug", snomed_code="372877000"),
    "amoxicillin": LinkedEntity("Amoxicillin", "drug", snomed_code="372687004"),
    "azithromycin": LinkedEntity("Azithromycin", "drug", snomed_code="387531004"),
    "ceftriaxone": LinkedEntity("Ceftriaxone", "drug", snomed_code="372670001"),
    "furosemide": LinkedEntity("Furosemide", "drug", snomed_code="387475002"),
    "spironolactone": LinkedEntity("Spironolactone", "drug", snomed_code="387078006"),
    "sacubitril/valsartan": LinkedEntity("Sacubitril/Valsartan", "drug", snomed_code="716083005"),
    "entresto": LinkedEntity("Sacubitril/Valsartan", "drug", snomed_code="716083005"),
    "dapagliflozin": LinkedEntity("Dapagliflozin", "drug", snomed_code="703674005"),
    "empagliflozin": LinkedEntity("Empagliflozin", "drug", snomed_code="703894007"),
}

_LAB_MAP: dict[str, LinkedEntity] = {
    "egfr": LinkedEntity("eGFR", "lab", loinc_code="77147-7"),
    "creatinine": LinkedEntity("Creatinine", "lab", loinc_code="2160-0"),
    "potassium": LinkedEntity("Potassium", "lab", loinc_code="2823-3"),
    "sodium": LinkedEntity("Sodium", "lab", loinc_code="2951-2"),
    "bnp": LinkedEntity("BNP", "lab", loinc_code="42637-9"),
    "nt-probnp": LinkedEntity("NT-proBNP", "lab", loinc_code="33762-6"),
    "troponin": LinkedEntity("Troponin", "lab", loinc_code="6598-7"),
    "inr": LinkedEntity("INR", "lab", loinc_code="6301-6"),
    "ldl": LinkedEntity("LDL Cholesterol", "lab", loinc_code="13457-7"),
    "hdl": LinkedEntity("HDL Cholesterol", "lab", loinc_code="2085-9"),
    "total cholesterol": LinkedEntity("Total Cholesterol", "lab", loinc_code="2093-3"),
    "alt": LinkedEntity("ALT", "lab", loinc_code="1742-6"),
    "ast": LinkedEntity("AST", "lab", loinc_code="1920-8"),
    "hemoglobin": LinkedEntity("Hemoglobin", "lab", loinc_code="718-7"),
    "hba1c": LinkedEntity("HbA1c", "lab", loinc_code="4548-4"),
    "albumin": LinkedEntity("Albumin", "lab", loinc_code="1751-7"),
    "qtc": LinkedEntity("QTc Interval", "lab", loinc_code="8897-1"),
    "crcl": LinkedEntity("Creatinine Clearance", "lab", loinc_code="2164-2"),
}

_TYPE_MAPS = {
    "drug": _DRUG_MAP,
    "lab": _LAB_MAP,
}


def link_entity(name: str, entity_type: str) -> LinkedEntity | None:
    """Resolve a clinical entity name to its canonical form with codes."""
    mapping = _TYPE_MAPS.get(entity_type)
    if not mapping:
        return None
    return mapping.get(name.lower())
```

**Step 3: Run tests**

Run: `uv run python -m pytest tests/graphrag/test_linker.py -v`
Expected: All PASS.

**Step 4: Commit**

```bash
git add src/open_medicine/graphrag/ingestion/linker.py tests/graphrag/test_linker.py
git commit -m "feat(graphrag): add entity linker with SNOMED/LOINC dictionary"
```

---

### Task 10: LLM extraction agent

**Files:**
- Create: `src/open_medicine/graphrag/ingestion/extractor.py`
- Create: `tests/graphrag/test_extractor.py`

**Step 1: Write failing tests (mock LLM)**

```python
# tests/graphrag/test_extractor.py
import json
import pytest
from unittest.mock import patch, MagicMock
from open_medicine.graphrag.ingestion.extractor import extract_logic_nodes
from open_medicine.graphrag.graph.schema import LogicNodeType


MOCK_LLM_RESPONSE = json.dumps([
    {
        "id": "ln_test_001",
        "type": "contraindication",
        "conditions": [{"variable": "pregnancy", "operator": "==", "threshold": "true"}],
        "action": "contraindicated",
        "action_detail": "ACE inhibitors are contraindicated in pregnancy",
        "strength": "Strong/A",
        "guideline_id": "test_htn_2024",
        "page": 1,
        "concepts": [{"name": "lisinopril", "type": "drug"}],
    }
])


class TestExtractor:
    @patch("open_medicine.graphrag.ingestion.extractor._call_llm")
    def test_extracts_logic_node(self, mock_llm):
        mock_llm.return_value = MOCK_LLM_RESPONSE
        results = extract_logic_nodes(
            chunk_text="ACE inhibitors are contraindicated in pregnancy.",
            parent_context="1. Pharmacotherapy",
            guideline_id="test_htn_2024",
            page=1,
        )
        assert len(results) == 1
        assert results[0].logic_node.type == LogicNodeType.CONTRAINDICATION
        assert results[0].logic_node.action == "contraindicated"

    @patch("open_medicine.graphrag.ingestion.extractor._call_llm")
    def test_empty_chunk_returns_empty(self, mock_llm):
        mock_llm.return_value = "[]"
        results = extract_logic_nodes(
            chunk_text="This section describes general principles.",
            parent_context="Introduction",
            guideline_id="test_htn_2024",
            page=1,
        )
        assert len(results) == 0

    @patch("open_medicine.graphrag.ingestion.extractor._call_llm")
    def test_invalid_json_returns_empty(self, mock_llm):
        mock_llm.return_value = "not valid json"
        results = extract_logic_nodes(
            chunk_text="Some text.",
            parent_context="Section",
            guideline_id="g",
            page=1,
        )
        assert len(results) == 0

    @patch("open_medicine.graphrag.ingestion.extractor._call_llm")
    def test_invalid_schema_filtered_out(self, mock_llm):
        mock_llm.return_value = json.dumps([
            {"id": "bad", "type": "invalid_type", "action": "x"},
        ])
        results = extract_logic_nodes(
            chunk_text="Text.", parent_context="S",
            guideline_id="g", page=1,
        )
        assert len(results) == 0
```

**Step 2: Run to verify fail, then implement**

```python
# src/open_medicine/graphrag/ingestion/extractor.py
from __future__ import annotations
import json
import logging
from dataclasses import dataclass
from open_medicine.graphrag.graph.schema import LogicNode, Condition

logger = logging.getLogger(__name__)


@dataclass
class ConceptRef:
    name: str
    type: str


@dataclass
class ExtractionResult:
    logic_node: LogicNode
    concepts: list[ConceptRef]


EXTRACTION_PROMPT = """You are a clinical guideline extraction agent.

Given this text from a medical guideline, Section: {parent_context}:

---
{chunk_text}
---

Extract all clinical rules as a JSON array. Each rule must have:
- "id": unique string (use format "ln_<guideline>_<number>")
- "type": one of "dosing", "contraindication", "interaction", "monitoring", "treatment_selection", "diagnostic_criteria"
- "conditions": array of {{"variable": str, "operator": "<|<=|>|>=|==|!=", "threshold": number|string, "unit": str|null}}
- "action": type-specific action string
- "action_detail": human-readable explanation
- "strength": evidence strength (e.g. "Strong/A", "Moderate/B", "Weak/C", "Expert_Opinion")
- "guideline_id": "{guideline_id}"
- "page": {page}
- "concepts": array of {{"name": entity name, "type": "drug"|"disease"|"lab"|"procedure"|"symptom"}}

If no clinical rules are present, return an empty array [].
Return ONLY the JSON array, no other text."""


def _call_llm(prompt: str) -> str:
    """Call the LLM API. Separated for easy mocking."""
    import anthropic
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def extract_logic_nodes(
    chunk_text: str,
    parent_context: str,
    guideline_id: str,
    page: int,
) -> list[ExtractionResult]:
    """Extract LogicNodes from a text chunk using LLM."""
    prompt = EXTRACTION_PROMPT.format(
        chunk_text=chunk_text,
        parent_context=parent_context,
        guideline_id=guideline_id,
        page=page,
    )

    try:
        raw = _call_llm(prompt)
    except Exception:
        logger.exception("LLM call failed")
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("LLM returned invalid JSON")
        return []

    if not isinstance(data, list):
        return []

    results: list[ExtractionResult] = []
    for item in data:
        try:
            concepts = [ConceptRef(c["name"], c["type"]) for c in item.pop("concepts", [])]
            conditions = [Condition(**c) for c in item.get("conditions", [])]
            item["conditions"] = conditions
            logic_node = LogicNode(**item)
            results.append(ExtractionResult(logic_node=logic_node, concepts=concepts))
        except Exception:
            logger.warning("Skipping invalid extraction: %s", item)
            continue

    return results
```

**Step 3: Run tests**

Run: `uv run python -m pytest tests/graphrag/test_extractor.py -v`
Expected: All PASS.

**Step 4: Commit**

```bash
git add src/open_medicine/graphrag/ingestion/extractor.py tests/graphrag/test_extractor.py
git commit -m "feat(graphrag): add LLM extraction agent with typed LogicNode output"
```

---

### Task 11: Graph loader

**Files:**
- Create: `src/open_medicine/graphrag/ingestion/loader.py`
- Create: `tests/graphrag/test_loader.py`

**Step 1: Write failing tests (mock Neo4j connection)**

```python
# tests/graphrag/test_loader.py
from unittest.mock import MagicMock, call
from open_medicine.graphrag.ingestion.loader import load_guideline, LoadableGuideline
from open_medicine.graphrag.ingestion.chunker import Chunk
from open_medicine.graphrag.ingestion.extractor import ExtractionResult, ConceptRef
from open_medicine.graphrag.graph.schema import (
    LogicNode, LogicNodeType, Condition, Guideline,
)


def _make_loadable() -> LoadableGuideline:
    return LoadableGuideline(
        guideline=Guideline(
            id="test_001", title="Test", doi="10.1234/test",
            year=2024, organization="TEST", total_pages=10,
        ),
        chunks=[
            Chunk(id="parent_1", text="Full section text", guideline_id="test_001", section="S1"),
            Chunk(id="child_1", text="Child text", guideline_id="test_001", section="S1", parent_chunk_id="parent_1"),
        ],
        extractions=[
            ExtractionResult(
                logic_node=LogicNode(
                    id="ln_001", type=LogicNodeType.CONTRAINDICATION,
                    conditions=[Condition(variable="pregnancy", operator="==", threshold="true")],
                    action="contraindicated", action_detail="Do not use in pregnancy",
                    strength="Strong/A", guideline_id="test_001", page=1,
                ),
                concepts=[ConceptRef("lisinopril", "drug")],
            ),
        ],
    )


class TestLoader:
    def test_calls_execute_write_tx(self):
        conn = MagicMock()
        loadable = _make_loadable()
        load_guideline(conn, loadable)
        conn.execute_write_tx.assert_called()

    def test_generates_cypher_for_guideline_node(self):
        conn = MagicMock()
        loadable = _make_loadable()
        load_guideline(conn, loadable)
        queries = conn.execute_write_tx.call_args[0][0]
        cypher_strs = [q[0] for q in queries]
        assert any("Guideline" in s for s in cypher_strs)

    def test_generates_cypher_for_chunks(self):
        conn = MagicMock()
        loadable = _make_loadable()
        load_guideline(conn, loadable)
        queries = conn.execute_write_tx.call_args[0][0]
        cypher_strs = [q[0] for q in queries]
        assert any("EvidenceChunk" in s for s in cypher_strs)

    def test_generates_cypher_for_logic_nodes(self):
        conn = MagicMock()
        loadable = _make_loadable()
        load_guideline(conn, loadable)
        queries = conn.execute_write_tx.call_args[0][0]
        cypher_strs = [q[0] for q in queries]
        assert any("LogicNode" in s for s in cypher_strs)

    def test_generates_cypher_for_concepts(self):
        conn = MagicMock()
        loadable = _make_loadable()
        load_guideline(conn, loadable)
        queries = conn.execute_write_tx.call_args[0][0]
        cypher_strs = [q[0] for q in queries]
        assert any("Concept" in s for s in cypher_strs)
```

**Step 2: Run to verify fail, then implement**

```python
# src/open_medicine/graphrag/ingestion/loader.py
from __future__ import annotations
import json
from dataclasses import dataclass
from open_medicine.graphrag.graph.schema import Guideline
from open_medicine.graphrag.ingestion.chunker import Chunk
from open_medicine.graphrag.ingestion.extractor import ExtractionResult
from open_medicine.graphrag.ingestion.linker import link_entity
from open_medicine.graphrag.graph.connection import GraphConnection


@dataclass
class LoadableGuideline:
    guideline: Guideline
    chunks: list[Chunk]
    extractions: list[ExtractionResult]


def load_guideline(conn: GraphConnection, data: LoadableGuideline) -> None:
    """Load a complete guideline into Neo4j as a single transaction."""
    queries: list[tuple[str, dict]] = []

    # 1. Delete existing data for this guideline (idempotent)
    queries.append((
        "MATCH (n) WHERE n.guideline_id = $gid DETACH DELETE n",
        {"gid": data.guideline.id},
    ))
    queries.append((
        "MATCH (g:Guideline {id: $gid}) DETACH DELETE g",
        {"gid": data.guideline.id},
    ))

    # 2. Create Guideline node
    queries.append((
        "CREATE (g:Guideline {id: $id, title: $title, doi: $doi, year: $year, organization: $org, total_pages: $pages})",
        {
            "id": data.guideline.id, "title": data.guideline.title,
            "doi": data.guideline.doi, "year": data.guideline.year,
            "org": data.guideline.organization, "pages": data.guideline.total_pages,
        },
    ))

    # 3. Create EvidenceChunk nodes
    for chunk in data.chunks:
        queries.append((
            "CREATE (ec:EvidenceChunk {id: $id, text: $text, guideline_id: $gid, section: $section})",
            {"id": chunk.id, "text": chunk.text, "gid": chunk.guideline_id, "section": chunk.section},
        ))
        # BELONGS_TO edge
        queries.append((
            "MATCH (ec:EvidenceChunk {id: $cid}), (g:Guideline {id: $gid}) CREATE (ec)-[:BELONGS_TO]->(g)",
            {"cid": chunk.id, "gid": data.guideline.id},
        ))
        # CHILD_OF edge
        if chunk.parent_chunk_id:
            queries.append((
                "MATCH (child:EvidenceChunk {id: $cid}), (parent:EvidenceChunk {id: $pid}) CREATE (child)-[:CHILD_OF]->(parent)",
                {"cid": chunk.id, "pid": chunk.parent_chunk_id},
            ))

    # 4. Create LogicNode + Concept nodes
    for extraction in data.extractions:
        ln = extraction.logic_node
        conditions_json = json.dumps([c.model_dump() for c in ln.conditions])
        queries.append((
            "CREATE (ln:LogicNode {id: $id, type: $type, conditions: $conds, action: $action, "
            "action_detail: $detail, strength: $strength, guideline_id: $gid, page: $page})",
            {
                "id": ln.id, "type": ln.type.value, "conds": conditions_json,
                "action": ln.action, "detail": ln.action_detail,
                "strength": ln.strength, "gid": ln.guideline_id, "page": ln.page,
            },
        ))
        # DEFINED_BY edge
        queries.append((
            "MATCH (ln:LogicNode {id: $lid}), (g:Guideline {id: $gid}) CREATE (ln)-[:DEFINED_BY]->(g)",
            {"lid": ln.id, "gid": data.guideline.id},
        ))

        # Concept nodes + PARTICIPATES_IN edges
        for concept_ref in extraction.concepts:
            linked = link_entity(concept_ref.name, concept_ref.type)
            c_id = concept_ref.name.lower().replace(" ", "_")
            c_name = linked.canonical_name if linked else concept_ref.name
            snomed = linked.snomed_code if linked else None
            loinc = linked.loinc_code if linked else None

            queries.append((
                "MERGE (c:Concept {id: $id}) "
                "ON CREATE SET c.name = $name, c.type = $type, c.snomed_code = $snomed, c.loinc_code = $loinc",
                {"id": c_id, "name": c_name, "type": concept_ref.type, "snomed": snomed, "loinc": loinc},
            ))
            queries.append((
                "MATCH (c:Concept {id: $cid}), (ln:LogicNode {id: $lid}) "
                "CREATE (c)-[:PARTICIPATES_IN {role: $role}]->(ln)",
                {"cid": c_id, "lid": ln.id, "role": "intervention"},
            ))

    conn.execute_write_tx(queries)
```

**Step 3: Run tests**

Run: `uv run python -m pytest tests/graphrag/test_loader.py -v`
Expected: All PASS.

**Step 4: Commit**

```bash
git add src/open_medicine/graphrag/ingestion/loader.py tests/graphrag/test_loader.py
git commit -m "feat(graphrag): add graph loader with idempotent Neo4j writes"
```

---

## Phase 3: Reasoning Engine

### Task 12: Query/response types

**Files:**
- Create: `src/open_medicine/graphrag/reasoning/__init__.py`
- Create: `src/open_medicine/graphrag/reasoning/types.py`
- Create: `tests/graphrag/test_reasoning_types.py`

**Step 1: Write failing tests**

```python
# tests/graphrag/test_reasoning_types.py
import pytest
from open_medicine.graphrag.reasoning.types import (
    ClinicalQuery, GraphRAGResult, LogicNodeMatch, EvidenceCitation,
)


class TestClinicalQuery:
    def test_valid_query(self):
        q = ClinicalQuery(
            intent="dosing",
            concepts=["apixaban"],
            patient_vars={"eGFR": 20, "age": 80},
        )
        assert q.intent == "dosing"

    def test_patient_vars_optional(self):
        q = ClinicalQuery(intent="contraindication", concepts=["lisinopril"])
        assert q.patient_vars == {}


class TestGraphRAGResult:
    def test_graph_traversal_result(self):
        r = GraphRAGResult(
            source="graph_traversal",
            matches=[
                LogicNodeMatch(
                    logic_node_id="ln_001",
                    type="dosing",
                    action="contraindicated",
                    action_detail="Do not use",
                    strength="Strong/A",
                    conditions_met=True,
                    missing_variables=[],
                ),
            ],
            synthesis=None,
            evidence=[
                EvidenceCitation(
                    chunk_id="c1", text="Source text",
                    guideline_title="Test", doi="10.1234/test",
                    section="S1", page=1,
                ),
            ],
            confidence="high",
            missing_variables=[],
        )
        assert r.source == "graph_traversal"
        assert len(r.matches) == 1

    def test_llm_synthesis_result(self):
        r = GraphRAGResult(
            source="llm_synthesis",
            matches=[],
            synthesis="Based on the guidelines...",
            evidence=[],
            confidence="medium",
            missing_variables=["weight_kg"],
        )
        assert r.synthesis is not None
```

**Step 2: Run to verify fail, then implement**

```python
# src/open_medicine/graphrag/reasoning/__init__.py
"""Reasoning engine for graph traversal and LLM fallback."""
```

```python
# src/open_medicine/graphrag/reasoning/types.py
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field


class ClinicalQuery(BaseModel):
    intent: str = Field(description="Query type: dosing, contraindication, interaction, monitoring, treatment_selection, diagnostic_criteria")
    concepts: list[str] = Field(description="Clinical concepts to query (drug names, conditions, etc.)")
    patient_vars: dict[str, float | str | bool] = Field(default_factory=dict, description="Patient variables")
    guideline_filter: str | None = Field(default=None, description="Optional: scope to a specific guideline")
    include_source_text: bool = Field(default=True, description="Include raw source text in response")


class LogicNodeMatch(BaseModel):
    logic_node_id: str
    type: str
    action: str
    action_detail: str
    strength: str
    conditions_met: bool
    missing_variables: list[str] = Field(default_factory=list)


class EvidenceCitation(BaseModel):
    chunk_id: str
    text: str
    guideline_title: str
    doi: str
    section: str
    page: int


class GraphRAGResult(BaseModel):
    source: Literal["graph_traversal", "llm_synthesis"]
    matches: list[LogicNodeMatch]
    synthesis: str | None = None
    evidence: list[EvidenceCitation]
    confidence: Literal["high", "medium", "low"]
    missing_variables: list[str] = Field(default_factory=list)
```

**Step 3: Run tests**

Run: `uv run python -m pytest tests/graphrag/test_reasoning_types.py -v`
Expected: All PASS.

**Step 4: Commit**

```bash
git add src/open_medicine/graphrag/reasoning/ tests/graphrag/test_reasoning_types.py
git commit -m "feat(graphrag): add reasoning query/response type models"
```

---

### Task 13: Deterministic reasoning engine

**Files:**
- Create: `src/open_medicine/graphrag/reasoning/engine.py`
- Create: `tests/graphrag/test_engine.py`

**Step 1: Write failing tests**

```python
# tests/graphrag/test_engine.py
import json
import pytest
from unittest.mock import MagicMock
from open_medicine.graphrag.reasoning.engine import ReasoningEngine
from open_medicine.graphrag.reasoning.types import ClinicalQuery


def _mock_conn_with_results(results: list[dict]) -> MagicMock:
    conn = MagicMock()
    conn.execute_read.return_value = results
    return conn


class TestConditionEvaluation:
    def test_numeric_less_than_matches(self):
        engine = ReasoningEngine.__new__(ReasoningEngine)
        cond = {"variable": "eGFR", "operator": "<", "threshold": 30}
        assert engine._evaluate_condition(cond, {"eGFR": 20}) is True

    def test_numeric_less_than_no_match(self):
        engine = ReasoningEngine.__new__(ReasoningEngine)
        cond = {"variable": "eGFR", "operator": "<", "threshold": 30}
        assert engine._evaluate_condition(cond, {"eGFR": 50}) is False

    def test_equals_string(self):
        engine = ReasoningEngine.__new__(ReasoningEngine)
        cond = {"variable": "pregnancy", "operator": "==", "threshold": "true"}
        assert engine._evaluate_condition(cond, {"pregnancy": "true"}) is True

    def test_missing_variable(self):
        engine = ReasoningEngine.__new__(ReasoningEngine)
        cond = {"variable": "weight_kg", "operator": ">", "threshold": 60}
        result = engine._evaluate_condition(cond, {"eGFR": 20})
        assert result is None  # unknown


class TestReasoningEngine:
    def test_query_returns_graph_traversal_on_match(self):
        mock_results = [
            {
                "ln_id": "ln_001", "ln_type": "dosing", "ln_action": "contraindicated",
                "ln_detail": "Do not use", "ln_strength": "Strong/A",
                "ln_conditions": json.dumps([{"variable": "eGFR", "operator": "<", "threshold": 25}]),
                "ln_page": 47,
                "ec_id": "c1", "ec_text": "Source text here",
                "g_title": "AF Guideline", "g_doi": "10.1234/af", "g_year": 2023,
                "ec_section": "dosing",
            }
        ]
        conn = _mock_conn_with_results(mock_results)
        engine = ReasoningEngine(conn)
        query = ClinicalQuery(intent="dosing", concepts=["apixaban"], patient_vars={"eGFR": 20})
        result = engine.query(query)
        assert result.source == "graph_traversal"
        assert len(result.matches) == 1
        assert result.matches[0].conditions_met is True
        assert result.confidence == "high"

    def test_partial_match_flagged(self):
        mock_results = [
            {
                "ln_id": "ln_001", "ln_type": "dosing", "ln_action": "dose_adjust",
                "ln_detail": "Reduce dose", "ln_strength": "Strong/A",
                "ln_conditions": json.dumps([
                    {"variable": "eGFR", "operator": "<", "threshold": 30},
                    {"variable": "weight_kg", "operator": "<", "threshold": 60},
                ]),
                "ln_page": 47,
                "ec_id": "c1", "ec_text": "Source",
                "g_title": "Guideline", "g_doi": "10.1/x", "g_year": 2023,
                "ec_section": "dosing",
            }
        ]
        conn = _mock_conn_with_results(mock_results)
        engine = ReasoningEngine(conn)
        query = ClinicalQuery(intent="dosing", concepts=["apixaban"], patient_vars={"eGFR": 20})
        result = engine.query(query)
        assert result.matches[0].conditions_met is False
        assert "weight_kg" in result.matches[0].missing_variables

    def test_no_matches_returns_empty(self):
        conn = _mock_conn_with_results([])
        engine = ReasoningEngine(conn)
        query = ClinicalQuery(intent="dosing", concepts=["unknowndrug"])
        result = engine.query(query)
        assert result.source == "graph_traversal"
        assert len(result.matches) == 0
        assert result.confidence == "low"

    def test_results_ranked_by_year_and_strength(self):
        mock_results = [
            {
                "ln_id": "ln_old", "ln_type": "dosing", "ln_action": "initiate",
                "ln_detail": "Old rec", "ln_strength": "Weak/C",
                "ln_conditions": json.dumps([]),
                "ln_page": 10,
                "ec_id": "c1", "ec_text": "Old",
                "g_title": "Old Guide", "g_doi": "10.1/old", "g_year": 2018,
                "ec_section": "dosing",
            },
            {
                "ln_id": "ln_new", "ln_type": "dosing", "ln_action": "initiate",
                "ln_detail": "New rec", "ln_strength": "Strong/A",
                "ln_conditions": json.dumps([]),
                "ln_page": 20,
                "ec_id": "c2", "ec_text": "New",
                "g_title": "New Guide", "g_doi": "10.1/new", "g_year": 2023,
                "ec_section": "dosing",
            },
        ]
        conn = _mock_conn_with_results(mock_results)
        engine = ReasoningEngine(conn)
        query = ClinicalQuery(intent="dosing", concepts=["drug"])
        result = engine.query(query)
        assert result.matches[0].logic_node_id == "ln_new"
```

**Step 2: Run to verify fail, then implement**

```python
# src/open_medicine/graphrag/reasoning/engine.py
from __future__ import annotations
import json
import operator
from typing import Any
from open_medicine.graphrag.graph.connection import GraphConnection
from open_medicine.graphrag.reasoning.types import (
    ClinicalQuery, GraphRAGResult, LogicNodeMatch, EvidenceCitation,
)

STRENGTH_RANK = {"Strong/A": 0, "Moderate/B": 1, "Weak/C": 2, "Expert_Opinion": 3}
OPS = {
    "<": operator.lt, "<=": operator.le,
    ">": operator.gt, ">=": operator.ge,
    "==": operator.eq, "!=": operator.ne,
}


class ReasoningEngine:
    def __init__(self, conn: GraphConnection) -> None:
        self._conn = conn

    def _evaluate_condition(self, cond: dict, patient_vars: dict[str, Any]) -> bool | None:
        var = cond["variable"]
        if var not in patient_vars:
            return None  # unknown
        op_fn = OPS.get(cond["operator"])
        if not op_fn:
            return None
        try:
            return op_fn(float(patient_vars[var]), float(cond["threshold"]))
        except (ValueError, TypeError):
            return op_fn(str(patient_vars[var]), str(cond["threshold"]))

    def query(self, q: ClinicalQuery) -> GraphRAGResult:
        concept_ids = [c.lower().replace(" ", "_") for c in q.concepts]

        cypher = (
            "MATCH (c:Concept)-[:PARTICIPATES_IN]->(ln:LogicNode {type: $intent})"
            "-[:SOURCED_FROM]->(ec:EvidenceChunk)-[:BELONGS_TO]->(g:Guideline) "
            "WHERE c.id IN $concepts "
        )
        if q.guideline_filter:
            cypher += "AND ln.guideline_id = $gfilter "

        cypher += (
            "RETURN ln.id AS ln_id, ln.type AS ln_type, ln.action AS ln_action, "
            "ln.action_detail AS ln_detail, ln.strength AS ln_strength, "
            "ln.conditions AS ln_conditions, ln.page AS ln_page, "
            "ec.id AS ec_id, ec.text AS ec_text, ec.section AS ec_section, "
            "g.title AS g_title, g.doi AS g_doi, g.year AS g_year "
            "ORDER BY g.year DESC"
        )

        params: dict[str, Any] = {"intent": q.intent, "concepts": concept_ids}
        if q.guideline_filter:
            params["gfilter"] = q.guideline_filter

        rows = self._conn.execute_read(cypher, params)

        matches: list[LogicNodeMatch] = []
        evidence: list[EvidenceCitation] = []
        all_missing: list[str] = []

        for row in rows:
            conditions = json.loads(row["ln_conditions"]) if isinstance(row["ln_conditions"], str) else row["ln_conditions"]
            missing_vars: list[str] = []
            all_met = True

            for cond in conditions:
                result = self._evaluate_condition(cond, q.patient_vars)
                if result is None:
                    missing_vars.append(cond["variable"])
                    all_met = False
                elif not result:
                    all_met = False

            conditions_met = all_met and len(missing_vars) == 0

            matches.append(LogicNodeMatch(
                logic_node_id=row["ln_id"],
                type=row["ln_type"],
                action=row["ln_action"],
                action_detail=row["ln_detail"],
                strength=row["ln_strength"],
                conditions_met=conditions_met,
                missing_variables=missing_vars,
            ))
            all_missing.extend(missing_vars)

            evidence.append(EvidenceCitation(
                chunk_id=row["ec_id"],
                text=row["ec_text"],
                guideline_title=row["g_title"],
                doi=row["g_doi"],
                section=row["ec_section"],
                page=row["ln_page"],
            ))

        # Sort: full matches first, then by strength, then by year (already ordered)
        matches.sort(key=lambda m: (
            not m.conditions_met,
            STRENGTH_RANK.get(m.strength, 99),
        ))

        # Determine confidence
        full_matches = [m for m in matches if m.conditions_met]
        if full_matches:
            confidence = "high"
        elif matches:
            confidence = "medium"
        else:
            confidence = "low"

        return GraphRAGResult(
            source="graph_traversal",
            matches=matches,
            synthesis=None,
            evidence=evidence,
            confidence=confidence,
            missing_variables=list(set(all_missing)),
        )
```

**Step 3: Run tests**

Run: `uv run python -m pytest tests/graphrag/test_engine.py -v`
Expected: All PASS.

**Step 4: Commit**

```bash
git add src/open_medicine/graphrag/reasoning/engine.py tests/graphrag/test_engine.py
git commit -m "feat(graphrag): add deterministic reasoning engine with condition evaluation"
```

---

### Task 14: LLM fallback engine

**Files:**
- Create: `src/open_medicine/graphrag/reasoning/fallback.py`
- Create: `tests/graphrag/test_fallback.py`

**Step 1: Write failing tests**

```python
# tests/graphrag/test_fallback.py
import pytest
from unittest.mock import MagicMock, patch
from open_medicine.graphrag.reasoning.fallback import FallbackEngine
from open_medicine.graphrag.reasoning.types import ClinicalQuery, GraphRAGResult


class TestFallbackEngine:
    def test_returns_llm_synthesis_source(self):
        conn = MagicMock()
        # Mock vector search returning chunks
        conn.execute_read.return_value = [
            {
                "ec_id": "c1", "ec_text": "Apixaban 5mg twice daily for AF.",
                "ec_section": "dosing", "score": 0.92,
                "g_title": "AF Guideline", "g_doi": "10.1/af",
                "ln_page": 10,
            }
        ]
        engine = FallbackEngine(conn)
        query = ClinicalQuery(intent="dosing", concepts=["apixaban"])

        with patch.object(engine, "_synthesize") as mock_synth:
            mock_synth.return_value = "Based on the AF guideline, apixaban 5mg BID is recommended."
            result = engine.query(query)

        assert result.source == "llm_synthesis"
        assert result.synthesis is not None
        assert result.confidence == "medium"
        assert len(result.evidence) > 0

    def test_no_chunks_returns_low_confidence(self):
        conn = MagicMock()
        conn.execute_read.return_value = []
        engine = FallbackEngine(conn)
        query = ClinicalQuery(intent="dosing", concepts=["unknowndrug"])

        result = engine.query(query)
        assert result.confidence == "low"
        assert result.synthesis is None
```

**Step 2: Run to verify fail, then implement**

```python
# src/open_medicine/graphrag/reasoning/fallback.py
from __future__ import annotations
from open_medicine.graphrag.graph.connection import GraphConnection
from open_medicine.graphrag.reasoning.types import (
    ClinicalQuery, GraphRAGResult, EvidenceCitation,
)

SYNTHESIS_PROMPT = """You are a clinical guideline assistant. Answer ONLY based on the provided source texts.
If the sources do not contain enough information, say so explicitly.

Sources:
{sources}

Question: {question}

Requirements:
- Cite the specific guideline, section, and page for every claim
- Do not extrapolate beyond what the sources state
- Flag any uncertainty"""


class FallbackEngine:
    def __init__(self, conn: GraphConnection) -> None:
        self._conn = conn

    def _vector_search(self, query_text: str, top_k: int = 10) -> list[dict]:
        """Search EvidenceChunks by full-text index (vector index when available)."""
        cypher = (
            "CALL db.index.fulltext.queryNodes('evidence_text', $query) "
            "YIELD node, score "
            "MATCH (node)-[:BELONGS_TO]->(g:Guideline) "
            "OPTIONAL MATCH (ln:LogicNode)-[:SOURCED_FROM]->(node) "
            "RETURN node.id AS ec_id, node.text AS ec_text, node.section AS ec_section, "
            "score, g.title AS g_title, g.doi AS g_doi, "
            "COALESCE(ln.page, 0) AS ln_page "
            "LIMIT $limit"
        )
        return self._conn.execute_read(cypher, {"query": query_text, "limit": top_k})

    def _synthesize(self, question: str, sources: str) -> str:
        """Call LLM for synthesis."""
        import anthropic
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            messages=[{"role": "user", "content": SYNTHESIS_PROMPT.format(sources=sources, question=question)}],
        )
        return response.content[0].text

    def query(self, q: ClinicalQuery) -> GraphRAGResult:
        query_text = f"{q.intent} {' '.join(q.concepts)}"
        rows = self._vector_search(query_text)

        if not rows:
            return GraphRAGResult(
                source="llm_synthesis",
                matches=[],
                synthesis=None,
                evidence=[],
                confidence="low",
                missing_variables=[],
            )

        evidence = [
            EvidenceCitation(
                chunk_id=r["ec_id"], text=r["ec_text"],
                guideline_title=r["g_title"], doi=r["g_doi"],
                section=r["ec_section"], page=r["ln_page"],
            )
            for r in rows
        ]

        sources_text = "\n\n---\n\n".join(
            f"[{e.guideline_title}, {e.section}, p.{e.page}]\n{e.text}"
            for e in evidence
        )
        question = f"{q.intent}: {', '.join(q.concepts)}"
        if q.patient_vars:
            question += f" (patient: {q.patient_vars})"

        synthesis = self._synthesize(question, sources_text)

        return GraphRAGResult(
            source="llm_synthesis",
            matches=[],
            synthesis=synthesis,
            evidence=evidence,
            confidence="medium",
            missing_variables=[],
        )
```

**Step 3: Run tests**

Run: `uv run python -m pytest tests/graphrag/test_fallback.py -v`
Expected: All PASS.

**Step 4: Commit**

```bash
git add src/open_medicine/graphrag/reasoning/fallback.py tests/graphrag/test_fallback.py
git commit -m "feat(graphrag): add LLM fallback engine with vector search + synthesis"
```

---

## Phase 4: Server Layer (MCP + REST + Auth)

### Task 15: API key auth middleware

**Files:**
- Create: `src/open_medicine/graphrag/server/__init__.py`
- Create: `src/open_medicine/graphrag/server/auth.py`
- Create: `tests/graphrag/test_auth.py`

**Step 1: Write failing tests**

```python
# tests/graphrag/test_auth.py
import pytest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from open_medicine.graphrag.server.auth import require_api_key


class TestAuth:
    def _make_app(self, valid_keys: set[str]) -> TestClient:
        app = FastAPI()

        @app.get("/protected")
        async def protected(api_key: str = require_api_key(valid_keys)):
            return {"status": "ok"}

        @app.get("/health")
        async def health():
            return {"status": "healthy"}

        return TestClient(app)

    def test_valid_key_allowed(self):
        client = self._make_app({"test-key-123"})
        resp = client.get("/protected", headers={"Authorization": "Bearer test-key-123"})
        assert resp.status_code == 200

    def test_missing_key_rejected(self):
        client = self._make_app({"test-key-123"})
        resp = client.get("/protected")
        assert resp.status_code == 401

    def test_invalid_key_rejected(self):
        client = self._make_app({"test-key-123"})
        resp = client.get("/protected", headers={"Authorization": "Bearer wrong-key"})
        assert resp.status_code == 403

    def test_health_no_auth(self):
        client = self._make_app({"test-key-123"})
        resp = client.get("/health")
        assert resp.status_code == 200
```

**Step 2: Run to verify fail, then implement**

```python
# src/open_medicine/graphrag/server/__init__.py
"""GraphRAG server — MCP and REST API."""
```

```python
# src/open_medicine/graphrag/server/auth.py
from __future__ import annotations
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

_bearer = HTTPBearer(auto_error=False)


def require_api_key(valid_keys: set[str]):
    async def _check(credentials: HTTPAuthorizationCredentials | None = Security(_bearer)):
        if credentials is None:
            raise HTTPException(status_code=401, detail="Missing API key")
        if credentials.credentials not in valid_keys:
            raise HTTPException(status_code=403, detail="Invalid API key")
        return credentials.credentials
    return Depends(_check)
```

**Step 3: Run tests**

Run: `uv run python -m pytest tests/graphrag/test_auth.py -v`
Expected: All PASS.

**Step 4: Commit**

```bash
git add src/open_medicine/graphrag/server/ tests/graphrag/test_auth.py
git commit -m "feat(graphrag): add API key auth middleware"
```

---

### Task 16: REST API endpoints

**Files:**
- Create: `src/open_medicine/graphrag/server/rest_api.py`
- Create: `tests/graphrag/test_rest_api.py`

**Step 1: Write failing tests**

```python
# tests/graphrag/test_rest_api.py
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from open_medicine.graphrag.reasoning.types import GraphRAGResult


@pytest.fixture
def client():
    with patch("open_medicine.graphrag.server.rest_api.get_settings") as mock_settings:
        settings = MagicMock()
        settings.valid_api_keys = {"test-key"}
        settings.neo4j_uri = "bolt://localhost:7687"
        settings.neo4j_user = "neo4j"
        settings.neo4j_password = "test"
        mock_settings.return_value = settings

        with patch("open_medicine.graphrag.server.rest_api.GraphConnection"):
            with patch("open_medicine.graphrag.server.rest_api.ReasoningEngine") as mock_engine_cls:
                mock_engine = MagicMock()
                mock_engine.query.return_value = GraphRAGResult(
                    source="graph_traversal", matches=[], synthesis=None,
                    evidence=[], confidence="low", missing_variables=[],
                )
                mock_engine_cls.return_value = mock_engine

                with patch("open_medicine.graphrag.server.rest_api.FallbackEngine"):
                    from open_medicine.graphrag.server.rest_api import create_app
                    app = create_app()
                    yield TestClient(app)


class TestRESTAPI:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_dosing_requires_auth(self, client):
        resp = client.post("/v1/dosing", json={"drug": "apixaban"})
        assert resp.status_code == 401

    def test_dosing_with_auth(self, client):
        resp = client.post(
            "/v1/dosing",
            json={"drug": "apixaban", "patient_vars": {"eGFR": 20}},
            headers={"Authorization": "Bearer test-key"},
        )
        assert resp.status_code == 200
        assert "source" in resp.json()

    def test_contraindications_endpoint(self, client):
        resp = client.post(
            "/v1/contraindications",
            json={"intervention": "lisinopril", "patient_vars": {}},
            headers={"Authorization": "Bearer test-key"},
        )
        assert resp.status_code == 200

    def test_query_endpoint(self, client):
        resp = client.post(
            "/v1/query",
            json={"intent": "dosing", "concepts": ["apixaban"], "patient_vars": {"eGFR": 20}},
            headers={"Authorization": "Bearer test-key"},
        )
        assert resp.status_code == 200

    def test_guidelines_list(self, client):
        resp = client.get(
            "/v1/guidelines",
            headers={"Authorization": "Bearer test-key"},
        )
        assert resp.status_code == 200
```

**Step 2: Run to verify fail, then implement**

```python
# src/open_medicine/graphrag/server/rest_api.py
from __future__ import annotations
from fastapi import FastAPI, Depends
from pydantic import BaseModel, Field
from open_medicine.graphrag.config import get_settings
from open_medicine.graphrag.graph.connection import GraphConnection
from open_medicine.graphrag.reasoning.engine import ReasoningEngine
from open_medicine.graphrag.reasoning.fallback import FallbackEngine
from open_medicine.graphrag.reasoning.types import ClinicalQuery, GraphRAGResult
from open_medicine.graphrag.server.auth import require_api_key


class DosingRequest(BaseModel):
    drug: str
    patient_vars: dict[str, float | str | bool] = Field(default_factory=dict)
    guideline_filter: str | None = None


class ContraindicationRequest(BaseModel):
    intervention: str
    patient_vars: dict[str, float | str | bool] = Field(default_factory=dict)


class InteractionRequest(BaseModel):
    drug_a: str
    drug_b: str
    patient_vars: dict[str, float | str | bool] = Field(default_factory=dict)


class MonitoringRequest(BaseModel):
    intervention: str
    patient_vars: dict[str, float | str | bool] = Field(default_factory=dict)


class TreatmentRequest(BaseModel):
    condition: str
    patient_vars: dict[str, float | str | bool] = Field(default_factory=dict)


class QueryRequest(BaseModel):
    intent: str
    concepts: list[str]
    patient_vars: dict[str, float | str | bool] = Field(default_factory=dict)
    guideline_filter: str | None = None
    include_source_text: bool = True


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="OpenMedicine GraphRAG", version="0.1.0")

    conn = GraphConnection(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    engine = ReasoningEngine(conn)
    fallback = FallbackEngine(conn)
    auth = require_api_key(settings.valid_api_keys)

    def _query(q: ClinicalQuery) -> GraphRAGResult:
        result = engine.query(q)
        if not result.matches and result.confidence == "low":
            return fallback.query(q)
        return result

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    @app.get("/v1/guidelines", dependencies=[Depends(auth)])
    async def list_guidelines():
        rows = conn.execute_read("MATCH (g:Guideline) RETURN g.id AS id, g.title AS title, g.doi AS doi, g.year AS year")
        return {"guidelines": rows}

    @app.post("/v1/dosing", dependencies=[Depends(auth)])
    async def check_dosing(req: DosingRequest):
        q = ClinicalQuery(intent="dosing", concepts=[req.drug], patient_vars=req.patient_vars, guideline_filter=req.guideline_filter)
        return _query(q).model_dump()

    @app.post("/v1/contraindications", dependencies=[Depends(auth)])
    async def check_contraindications(req: ContraindicationRequest):
        q = ClinicalQuery(intent="contraindication", concepts=[req.intervention], patient_vars=req.patient_vars)
        return _query(q).model_dump()

    @app.post("/v1/interactions", dependencies=[Depends(auth)])
    async def check_interactions(req: InteractionRequest):
        q = ClinicalQuery(intent="interaction", concepts=[req.drug_a, req.drug_b], patient_vars=req.patient_vars)
        return _query(q).model_dump()

    @app.post("/v1/monitoring", dependencies=[Depends(auth)])
    async def check_monitoring(req: MonitoringRequest):
        q = ClinicalQuery(intent="monitoring", concepts=[req.intervention], patient_vars=req.patient_vars)
        return _query(q).model_dump()

    @app.post("/v1/treatments", dependencies=[Depends(auth)])
    async def find_treatments(req: TreatmentRequest):
        q = ClinicalQuery(intent="treatment_selection", concepts=[req.condition], patient_vars=req.patient_vars)
        return _query(q).model_dump()

    @app.post("/v1/query", dependencies=[Depends(auth)])
    async def query_graph(req: QueryRequest):
        q = ClinicalQuery(**req.model_dump())
        return _query(q).model_dump()

    @app.get("/v1/evidence/{chunk_id}", dependencies=[Depends(auth)])
    async def get_evidence(chunk_id: str):
        rows = conn.execute_read(
            "MATCH (ec:EvidenceChunk {id: $id})-[:BELONGS_TO]->(g:Guideline) "
            "RETURN ec.text AS text, ec.section AS section, g.title AS guideline, g.doi AS doi",
            {"id": chunk_id},
        )
        if not rows:
            return {"error": "Chunk not found"}
        return rows[0]

    return app
```

**Step 3: Run tests**

Run: `uv run python -m pytest tests/graphrag/test_rest_api.py -v`
Expected: All PASS.

**Step 4: Commit**

```bash
git add src/open_medicine/graphrag/server/rest_api.py tests/graphrag/test_rest_api.py
git commit -m "feat(graphrag): add FastAPI REST endpoints for all clinical query types"
```

---

### Task 17: MCP server tools

**Files:**
- Create: `src/open_medicine/graphrag/server/mcp_server.py`
- Create: `tests/graphrag/test_mcp_server.py`

**Step 1: Write failing tests**

```python
# tests/graphrag/test_mcp_server.py
from open_medicine.graphrag.server.mcp_server import TOOL_DEFINITIONS


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

    def test_all_tools_have_input_schema(self):
        for t in TOOL_DEFINITIONS:
            assert "inputSchema" in t
            assert "properties" in t["inputSchema"]

    def test_total_tool_count(self):
        assert len(TOOL_DEFINITIONS) == 7
```

**Step 2: Run to verify fail, then implement**

```python
# src/open_medicine/graphrag/server/mcp_server.py
from __future__ import annotations
import asyncio
import json
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types
from open_medicine.graphrag.config import get_settings
from open_medicine.graphrag.graph.connection import GraphConnection
from open_medicine.graphrag.reasoning.engine import ReasoningEngine
from open_medicine.graphrag.reasoning.fallback import FallbackEngine
from open_medicine.graphrag.reasoning.types import ClinicalQuery

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
    fallback = FallbackEngine(conn)

    def _query(q: ClinicalQuery) -> str:
        result = engine.query(q)
        if not result.matches and result.confidence == "low":
            result = fallback.query(q)
        return result.model_dump_json(indent=2)

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        return [types.Tool(name=t["name"], description=t["description"], inputSchema=t["inputSchema"]) for t in TOOL_DEFINITIONS]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
        args = arguments or {}

        if name in _INTENT_MAP:
            intent, get_concepts = _INTENT_MAP[name]
            q = ClinicalQuery(intent=intent, concepts=get_concepts(args), patient_vars=args.get("patient_vars", {}))
            return [types.TextContent(type="text", text=_query(q))]

        if name == "query_clinical_graph":
            q = ClinicalQuery(**{k: v for k, v in args.items() if v is not None})
            return [types.TextContent(type="text", text=_query(q))]

        if name == "fetch_evidence_chunk":
            rows = conn.execute_read(
                "MATCH (ec:EvidenceChunk {id: $id})-[:BELONGS_TO]->(g:Guideline) "
                "RETURN ec.text AS text, ec.section AS section, g.title AS guideline, g.doi AS doi",
                {"id": args["chunk_id"]},
            )
            return [types.TextContent(type="text", text=json.dumps(rows[0] if rows else {"error": "Not found"}, indent=2))]

        raise ValueError(f"Unknown tool: {name}")

    return server


async def main_async() -> None:
    server = create_mcp_server()
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream,
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
```

**Step 3: Run tests**

Run: `uv run python -m pytest tests/graphrag/test_mcp_server.py -v`
Expected: All PASS.

**Step 4: Commit**

```bash
git add src/open_medicine/graphrag/server/mcp_server.py tests/graphrag/test_mcp_server.py
git commit -m "feat(graphrag): add MCP server with 7 clinical tools"
```

---

### Task 18: FastAPI app factory with MCP-over-SSE

**Files:**
- Create: `src/open_medicine/graphrag/server/app.py`
- Create: `src/open_medicine/graphrag/server/__main__.py`

**Step 1: Implement app factory**

```python
# src/open_medicine/graphrag/server/app.py
from open_medicine.graphrag.server.rest_api import create_app

app = create_app()
```

```python
# src/open_medicine/graphrag/server/__main__.py
import uvicorn
from open_medicine.graphrag.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "open_medicine.graphrag.server.app:app",
        host="0.0.0.0",
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
```

**Step 2: Commit**

```bash
git add src/open_medicine/graphrag/server/app.py src/open_medicine/graphrag/server/__main__.py
git commit -m "feat(graphrag): add FastAPI app factory and server entrypoint"
```

---

## Phase 5: CLI, Deployment & Integration Testing

### Task 19: Ingestion CLI

**Files:**
- Create: `src/open_medicine/graphrag/ingest.py`

**Step 1: Implement CLI**

```python
# src/open_medicine/graphrag/ingest.py
"""CLI for ingesting guideline PDFs into the Neo4j knowledge graph."""
from __future__ import annotations
import argparse
import logging
from pathlib import Path

from open_medicine.graphrag.config import get_settings
from open_medicine.graphrag.graph.connection import GraphConnection
from open_medicine.graphrag.graph.indexes import get_constraint_statements, get_index_statements
from open_medicine.graphrag.graph.schema import Guideline
from open_medicine.graphrag.ingestion.parser import parse_markdown
from open_medicine.graphrag.ingestion.chunker import chunk_document
from open_medicine.graphrag.ingestion.extractor import extract_logic_nodes
from open_medicine.graphrag.ingestion.loader import LoadableGuideline, load_guideline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ensure_indexes(conn: GraphConnection) -> None:
    for stmt in get_constraint_statements():
        try:
            conn.execute_write(stmt)
        except Exception as e:
            logger.debug("Constraint may already exist: %s", e)
    for stmt in get_index_statements():
        try:
            conn.execute_write(stmt)
        except Exception as e:
            logger.debug("Index may already exist: %s", e)


def ingest_file(conn: GraphConnection, path: Path, guideline_id: str, doi: str, title: str = "", year: int = 2024, org: str = "") -> None:
    logger.info("Parsing %s", path)
    doc = parse_markdown(path, guideline_id=guideline_id)
    if title:
        doc.title = title

    logger.info("Chunking: %d sections", len(doc.sections))
    chunks = chunk_document(doc)
    logger.info("Created %d chunks", len(chunks))

    logger.info("Extracting logic nodes...")
    all_extractions = []
    child_chunks = [c for c in chunks if c.parent_chunk_id is not None]
    for i, chunk in enumerate(child_chunks):
        parent = next((p for p in chunks if p.id == chunk.parent_chunk_id), None)
        parent_ctx = parent.text[:200] if parent else ""
        results = extract_logic_nodes(chunk.text, parent_ctx, guideline_id, page=0)
        all_extractions.extend(results)
        if (i + 1) % 10 == 0:
            logger.info("  Processed %d/%d chunks, %d nodes extracted", i + 1, len(child_chunks), len(all_extractions))

    logger.info("Extracted %d logic nodes total", len(all_extractions))

    guideline = Guideline(
        id=guideline_id, title=doc.title, doi=doi,
        year=year, organization=org, total_pages=0,
    )
    loadable = LoadableGuideline(guideline=guideline, chunks=chunks, extractions=all_extractions)

    logger.info("Loading into Neo4j...")
    load_guideline(conn, loadable)
    logger.info("Done: %s loaded with %d nodes", guideline_id, len(all_extractions))


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a guideline into GraphRAG")
    parser.add_argument("--file", type=Path, required=True, help="Path to markdown file")
    parser.add_argument("--id", required=True, help="Guideline ID")
    parser.add_argument("--doi", required=True, help="Guideline DOI")
    parser.add_argument("--title", default="", help="Guideline title")
    parser.add_argument("--year", type=int, default=2024, help="Publication year")
    parser.add_argument("--org", default="", help="Organization")
    args = parser.parse_args()

    settings = get_settings()
    with GraphConnection(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password) as conn:
        ensure_indexes(conn)
        ingest_file(conn, args.file, args.id, args.doi, args.title, args.year, args.org)


if __name__ == "__main__":
    main()
```

**Step 2: Add script entry in pyproject.toml**

Add to `[project.scripts]`:

```toml
open-medicine-graphrag = "open_medicine.graphrag.server.__main__:main"
open-medicine-graphrag-ingest = "open_medicine.graphrag.ingest:main"
```

**Step 3: Commit**

```bash
git add src/open_medicine/graphrag/ingest.py pyproject.toml
git commit -m "feat(graphrag): add ingestion CLI and script entrypoints"
```

---

### Task 20: Dockerfile for Railway deployment

**Files:**
- Create: `Dockerfile.graphrag`

**Step 1: Create Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ src/

# Install dependencies
RUN uv sync --extra graphrag --no-dev

EXPOSE 8000

CMD ["uv", "run", "python", "-m", "open_medicine.graphrag.server", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 2: Commit**

```bash
git add Dockerfile.graphrag
git commit -m "feat(graphrag): add Dockerfile for Railway deployment"
```

---

### Task 21: Integration test with synthetic guideline

**Files:**
- Create: `tests/graphrag/test_e2e.py`

**Step 1: Write integration test (skipped without Neo4j)**

```python
# tests/graphrag/test_e2e.py
"""End-to-end integration test. Requires running Neo4j.
Run with: NEO4J_URI=bolt://localhost:7687 uv run python -m pytest tests/graphrag/test_e2e.py -v
"""
import os
import json
import pytest
from pathlib import Path

pytestmark = pytest.mark.skipif(
    not os.environ.get("NEO4J_URI"),
    reason="NEO4J_URI not set — skipping integration tests",
)


@pytest.fixture(scope="module")
def conn():
    from open_medicine.graphrag.graph.connection import GraphConnection
    uri = os.environ["NEO4J_URI"]
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "openmedicine")
    c = GraphConnection(uri, user, password)
    yield c
    c.close()


@pytest.fixture(scope="module", autouse=True)
def setup_graph(conn):
    """Load synthetic test guideline into Neo4j."""
    from open_medicine.graphrag.graph.indexes import get_constraint_statements, get_index_statements
    from open_medicine.graphrag.graph.schema import Guideline, LogicNode, LogicNodeType, Condition
    from open_medicine.graphrag.ingestion.chunker import Chunk
    from open_medicine.graphrag.ingestion.extractor import ExtractionResult, ConceptRef
    from open_medicine.graphrag.ingestion.loader import LoadableGuideline, load_guideline
    from open_medicine.graphrag.ingest import ensure_indexes

    ensure_indexes(conn)

    guideline = Guideline(
        id="test_syn_001", title="Synthetic Test Guideline",
        doi="10.1234/synthetic", year=2024, organization="TEST", total_pages=5,
    )
    chunks = [
        Chunk(id="syn_parent_1", text="Section on ACE inhibitor dosing in renal impairment.", guideline_id="test_syn_001", section="dosing"),
        Chunk(id="syn_child_1", text="Lisinopril should be reduced to 2.5-5mg in patients with eGFR < 30.", guideline_id="test_syn_001", section="dosing", parent_chunk_id="syn_parent_1"),
    ]
    extractions = [
        ExtractionResult(
            logic_node=LogicNode(
                id="ln_syn_001", type=LogicNodeType.DOSING,
                conditions=[Condition(variable="eGFR", operator="<", threshold=30, unit="mL/min")],
                action="dose_adjust", action_detail="Reduce lisinopril to 2.5-5mg daily",
                strength="Strong/A", guideline_id="test_syn_001", page=3,
            ),
            concepts=[ConceptRef("lisinopril", "drug")],
        ),
        ExtractionResult(
            logic_node=LogicNode(
                id="ln_syn_002", type=LogicNodeType.CONTRAINDICATION,
                conditions=[Condition(variable="pregnancy", operator="==", threshold="true")],
                action="contraindicated", action_detail="ACE inhibitors are contraindicated in pregnancy",
                strength="Strong/A", guideline_id="test_syn_001", page=4,
            ),
            concepts=[ConceptRef("lisinopril", "drug")],
        ),
    ]
    loadable = LoadableGuideline(guideline=guideline, chunks=chunks, extractions=extractions)
    load_guideline(conn, loadable)

    yield

    # Cleanup
    conn.execute_write("MATCH (n) WHERE n.guideline_id = 'test_syn_001' DETACH DELETE n")
    conn.execute_write("MATCH (g:Guideline {id: 'test_syn_001'}) DETACH DELETE g")


class TestE2E:
    def test_dosing_query_matches(self, conn):
        from open_medicine.graphrag.reasoning.engine import ReasoningEngine
        from open_medicine.graphrag.reasoning.types import ClinicalQuery

        engine = ReasoningEngine(conn)
        q = ClinicalQuery(intent="dosing", concepts=["lisinopril"], patient_vars={"eGFR": 20})
        result = engine.query(q)
        assert result.source == "graph_traversal"
        assert len(result.matches) > 0
        assert result.matches[0].conditions_met is True
        assert "2.5-5mg" in result.matches[0].action_detail

    def test_contraindication_query(self, conn):
        from open_medicine.graphrag.reasoning.engine import ReasoningEngine
        from open_medicine.graphrag.reasoning.types import ClinicalQuery

        engine = ReasoningEngine(conn)
        q = ClinicalQuery(intent="contraindication", concepts=["lisinopril"], patient_vars={"pregnancy": "true"})
        result = engine.query(q)
        assert len(result.matches) > 0
        assert result.matches[0].action == "contraindicated"

    def test_no_match_low_confidence(self, conn):
        from open_medicine.graphrag.reasoning.engine import ReasoningEngine
        from open_medicine.graphrag.reasoning.types import ClinicalQuery

        engine = ReasoningEngine(conn)
        q = ClinicalQuery(intent="dosing", concepts=["nonexistent_drug"])
        result = engine.query(q)
        assert result.confidence == "low"
        assert len(result.matches) == 0

    def test_evidence_chunk_retrievable(self, conn):
        rows = conn.execute_read(
            "MATCH (ec:EvidenceChunk {id: 'syn_child_1'})-[:BELONGS_TO]->(g:Guideline) "
            "RETURN ec.text AS text, g.doi AS doi"
        )
        assert len(rows) == 1
        assert "Lisinopril" in rows[0]["text"]
        assert rows[0]["doi"] == "10.1234/synthetic"
```

**Step 2: Commit**

```bash
git add tests/graphrag/test_e2e.py
git commit -m "feat(graphrag): add end-to-end integration test with synthetic guideline"
```

---

## Phase Summary

| Phase | Tasks | What it delivers |
|-------|-------|-----------------|
| 1: Foundation | 1-6 | Dependencies, config, Pydantic schema, Neo4j connection, indexes, Docker Compose |
| 2: Ingestion | 7-11 | PDF parser, chunker, entity linker, LLM extractor, graph loader |
| 3: Reasoning | 12-14 | Query types, deterministic engine, LLM fallback |
| 4: Server | 15-18 | Auth, REST API, MCP server, app factory |
| 5: CLI & Deploy | 19-21 | Ingestion CLI, Dockerfile, integration tests |

**Total: 21 tasks, ~5 commits per phase.**

After completing all tasks, the system is ready for:
1. `docker compose up -d` (start Neo4j)
2. `uv run python -m open_medicine.graphrag.ingest --file <guideline.md> --id <id> --doi <doi>` (ingest)
3. `uv run python -m open_medicine.graphrag.server` (serve REST + MCP)

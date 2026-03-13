# GraphRAG Architecture Redesign — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix all 8 architectural gaps identified in the redesign audit — missing edges, proper transactions, vector search, deduplication, conflict detection, dead letter queue.

**Architecture:** Refactor-by-layer approach. Foundation modules (schema, parser, chunker, types) are untouched. Connection, queries, loader, engine, and fallback are refactored. Two new modules added (embeddings, dead_letter).

**Tech Stack:** Neo4j 5.x (managed transactions, native vector index), Voyage AI embeddings (via httpx), Anthropic SDK (extraction + synthesis)

**Design Doc:** `docs/plans/2026-03-13-graphrag-architecture-redesign.md`

---

## Task R1: Update config with Voyage embedding defaults

**Files:**
- Modify: `src/open_medicine/graphrag/config.py`

**Step 1: Update config**

Replace the OpenAI embedding defaults with Voyage:

```python
# src/open_medicine/graphrag/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class GraphRAGSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GRAPHRAG_")

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "openmedicine"

    anthropic_api_key: str = ""
    voyage_api_key: str = ""
    embedding_model: str = "voyage-3-lite"
    embedding_dimensions: int = 1024

    api_keys: str = ""  # comma-separated
    rate_limit: int = 100
    port: int = 8000

    @property
    def valid_api_keys(self) -> set[str]:
        return {k.strip() for k in self.api_keys.split(",") if k.strip()}


def get_settings() -> GraphRAGSettings:
    return GraphRAGSettings()
```

**Step 2: Verify**

Run: `uv run python -c "from open_medicine.graphrag.config import get_settings; s = get_settings(); print(s.embedding_model, s.embedding_dimensions)"`
Expected: `voyage-3-lite 1024`

**Step 3: Commit**

```bash
git add src/open_medicine/graphrag/config.py
git commit -m "refactor(graphrag): update config to Voyage embedding defaults"
```

---

## Task R2: Refactor connection to managed transactions

**Files:**
- Modify: `src/open_medicine/graphrag/graph/connection.py`
- Modify: `tests/graphrag/test_connection.py`

**Step 1: Write updated tests**

The mock pattern changes — `session.execute_read(fn)` calls `fn(tx)` with a transaction object, so we mock `execute_read.side_effect` to call the passed function.

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

    def test_execute_read_uses_managed_transaction(self):
        with patch("neo4j.GraphDatabase.driver") as mock_driver:
            mock_instance = MagicMock()
            mock_session = MagicMock()
            mock_tx = MagicMock()
            mock_result = MagicMock()
            mock_result.data.return_value = [{"n": 1}]
            mock_tx.run.return_value = mock_result
            mock_session.execute_read.side_effect = lambda fn: fn(mock_tx)
            mock_instance.session.return_value.__enter__ = lambda s: mock_session
            mock_instance.session.return_value.__exit__ = MagicMock(return_value=False)
            mock_driver.return_value = mock_instance

            conn = GraphConnection(uri="bolt://localhost:7687", user="neo4j", password="test")
            results = conn.execute_read("MATCH (n) RETURN n LIMIT 1")
            assert results == [{"n": 1}]
            mock_session.execute_read.assert_called_once()

    def test_execute_write_uses_managed_transaction(self):
        with patch("neo4j.GraphDatabase.driver") as mock_driver:
            mock_instance = MagicMock()
            mock_session = MagicMock()
            mock_tx = MagicMock()
            mock_result = MagicMock()
            mock_result.data.return_value = []
            mock_tx.run.return_value = mock_result
            mock_session.execute_write.side_effect = lambda fn: fn(mock_tx)
            mock_instance.session.return_value.__enter__ = lambda s: mock_session
            mock_instance.session.return_value.__exit__ = MagicMock(return_value=False)
            mock_driver.return_value = mock_instance

            conn = GraphConnection(uri="bolt://localhost:7687", user="neo4j", password="test")
            conn.execute_write("CREATE (n:Test {id: 1})")
            mock_session.execute_write.assert_called_once()

    def test_execute_write_tx_runs_all_queries(self):
        with patch("neo4j.GraphDatabase.driver") as mock_driver:
            mock_instance = MagicMock()
            mock_session = MagicMock()
            mock_tx = MagicMock()
            mock_session.execute_write.side_effect = lambda fn: fn(mock_tx)
            mock_instance.session.return_value.__enter__ = lambda s: mock_session
            mock_instance.session.return_value.__exit__ = MagicMock(return_value=False)
            mock_driver.return_value = mock_instance

            conn = GraphConnection(uri="bolt://localhost:7687", user="neo4j", password="test")
            conn.execute_write_tx([
                ("CREATE (a:A {id: 1})", {}),
                ("CREATE (b:B {id: 2})", {}),
            ])
            assert mock_tx.run.call_count == 2
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/graphrag/test_connection.py -v`
Expected: FAIL — `execute_read` and `execute_write` tests fail because current code uses `session.run()` not `session.execute_read()`.

**Step 3: Update connection implementation**

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
            return session.execute_read(
                lambda tx: tx.run(query, parameters or {}).data()
            )

    def execute_write(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict]:
        with self._driver.session() as session:
            return session.execute_write(
                lambda tx: tx.run(query, parameters or {}).data()
            )

    def execute_write_tx(self, queries: list[tuple[str, dict[str, Any]]]) -> None:
        def _work(tx: Any) -> None:
            for query, params in queries:
                tx.run(query, params)
        with self._driver.session() as session:
            session.execute_write(_work)
```

**Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/graphrag/test_connection.py -v`
Expected: All PASS.

**Step 5: Commit**

```bash
git add src/open_medicine/graphrag/graph/connection.py tests/graphrag/test_connection.py
git commit -m "refactor(graphrag): use managed transactions for Neo4j cluster routing"
```

---

## Task R3: Update indexes with vector index and PatientVariable

**Files:**
- Modify: `src/open_medicine/graphrag/graph/indexes.py`
- Modify: `tests/graphrag/test_indexes.py`

**Step 1: Update tests**

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
            assert "CREATE" in stmt

    def test_vector_index_defined(self):
        stmts = get_index_statements()
        text = " ".join(stmts)
        assert "VECTOR" in text
        assert "evidence_embedding" in text
        assert "1024" in text

    def test_patient_variable_index(self):
        stmts = get_index_statements()
        text = " ".join(stmts)
        assert "PatientVariable" in text
        assert "loinc_code" in text
```

**Step 2: Run tests to verify new ones fail**

Run: `uv run python -m pytest tests/graphrag/test_indexes.py -v`
Expected: `test_vector_index_defined` and `test_patient_variable_index` FAIL.

**Step 3: Update indexes**

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
        "CREATE VECTOR INDEX evidence_embedding IF NOT EXISTS FOR (n:EvidenceChunk) ON (n.embedding) "
        "OPTIONS {indexConfig: {`vector.dimensions`: 1024, `vector.similarity_function`: 'cosine'}}",
        "CREATE INDEX patient_variable_loinc IF NOT EXISTS FOR (n:PatientVariable) ON (n.loinc_code)",
    ]
```

**Step 4: Run tests**

Run: `uv run python -m pytest tests/graphrag/test_indexes.py -v`
Expected: All PASS.

**Step 5: Commit**

```bash
git add src/open_medicine/graphrag/graph/indexes.py tests/graphrag/test_indexes.py
git commit -m "refactor(graphrag): add vector index and PatientVariable index"
```

---

## Task R4: Create dead letter queue module

**Files:**
- Create: `src/open_medicine/graphrag/ingestion/dead_letter.py`
- Create: `tests/graphrag/test_dead_letter.py`

**Step 1: Write failing tests**

```python
# tests/graphrag/test_dead_letter.py
import json
import pytest
from pathlib import Path
from open_medicine.graphrag.ingestion.dead_letter import DeadLetterQueue, FailedExtraction


class TestFailedExtraction:
    def test_serializable(self):
        f = FailedExtraction(
            guideline_id="g1", chunk_id="c1",
            chunk_text="Some text", error="LLM timeout",
            timestamp="2026-03-13T10:00:00",
        )
        data = json.loads(f.to_json())
        assert data["guideline_id"] == "g1"
        assert data["error"] == "LLM timeout"

    def test_from_json(self):
        f = FailedExtraction(
            guideline_id="g1", chunk_id="c1",
            chunk_text="Text", error="err",
            timestamp="2026-03-13T10:00:00",
        )
        restored = FailedExtraction.from_json(f.to_json())
        assert restored.guideline_id == f.guideline_id
        assert restored.chunk_id == f.chunk_id


class TestDeadLetterQueue:
    def test_append_creates_file(self, tmp_path):
        dlq = DeadLetterQueue(tmp_path / "failed.jsonl")
        dlq.append(FailedExtraction(
            guideline_id="g1", chunk_id="c1",
            chunk_text="Text", error="err",
            timestamp="2026-03-13T10:00:00",
        ))
        assert dlq.path.exists()

    def test_append_and_load(self, tmp_path):
        dlq = DeadLetterQueue(tmp_path / "failed.jsonl")
        dlq.append(FailedExtraction("g1", "c1", "Text1", "err1", "2026-03-13T10:00:00"))
        dlq.append(FailedExtraction("g1", "c2", "Text2", "err2", "2026-03-13T10:01:00"))
        items = dlq.load()
        assert len(items) == 2
        assert items[0].chunk_id == "c1"
        assert items[1].chunk_id == "c2"

    def test_load_empty_file(self, tmp_path):
        dlq = DeadLetterQueue(tmp_path / "nonexistent.jsonl")
        items = dlq.load()
        assert items == []

    def test_count(self, tmp_path):
        dlq = DeadLetterQueue(tmp_path / "failed.jsonl")
        assert dlq.count() == 0
        dlq.append(FailedExtraction("g1", "c1", "T", "e", "2026-03-13T10:00:00"))
        assert dlq.count() == 1
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/graphrag/test_dead_letter.py -v`
Expected: FAIL — module doesn't exist.

**Step 3: Implement dead letter queue**

```python
# src/open_medicine/graphrag/ingestion/dead_letter.py
from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class FailedExtraction:
    guideline_id: str
    chunk_id: str
    chunk_text: str
    error: str
    timestamp: str

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, raw: str) -> FailedExtraction:
        return cls(**json.loads(raw))


class DeadLetterQueue:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, failure: FailedExtraction) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(failure.to_json() + "\n")

    def load(self) -> list[FailedExtraction]:
        if not self.path.exists():
            return []
        items: list[FailedExtraction] = []
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    items.append(FailedExtraction.from_json(line))
        return items

    def count(self) -> int:
        if not self.path.exists():
            return 0
        with open(self.path, encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())
```

**Step 4: Run tests**

Run: `uv run python -m pytest tests/graphrag/test_dead_letter.py -v`
Expected: All PASS.

**Step 5: Commit**

```bash
git add src/open_medicine/graphrag/ingestion/dead_letter.py tests/graphrag/test_dead_letter.py
git commit -m "feat(graphrag): add dead letter queue for failed extractions"
```

---

## Task R5: Create embeddings client

**Files:**
- Create: `src/open_medicine/graphrag/ingestion/embeddings.py`
- Create: `tests/graphrag/test_embeddings.py`

**Step 1: Write failing tests**

```python
# tests/graphrag/test_embeddings.py
import pytest
from unittest.mock import patch, MagicMock
from open_medicine.graphrag.ingestion.embeddings import embed_texts, embed_query


class TestEmbedTexts:
    @patch("open_medicine.graphrag.ingestion.embeddings.httpx.post")
    def test_returns_list_of_vectors(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"embedding": [0.1, 0.2, 0.3]},
                {"embedding": [0.4, 0.5, 0.6]},
            ]
        }
        mock_post.return_value = mock_response

        result = embed_texts(["text one", "text two"], api_key="test-key")
        assert len(result) == 2
        assert result[0] == [0.1, 0.2, 0.3]
        assert result[1] == [0.4, 0.5, 0.6]

    @patch("open_medicine.graphrag.ingestion.embeddings.httpx.post")
    def test_calls_voyage_api(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"data": [{"embedding": [0.1]}]}
        mock_post.return_value = mock_response

        embed_texts(["text"], api_key="my-key", model="voyage-3-lite")
        call_kwargs = mock_post.call_args
        assert "api.voyageai.com" in call_kwargs[0][0]
        assert call_kwargs[1]["headers"]["Authorization"] == "Bearer my-key"
        assert call_kwargs[1]["json"]["model"] == "voyage-3-lite"

    @patch("open_medicine.graphrag.ingestion.embeddings.httpx.post")
    def test_batches_large_inputs(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"data": [{"embedding": [0.1]}] * 50}
        mock_post.return_value = mock_response

        texts = [f"text {i}" for i in range(150)]
        result = embed_texts(texts, api_key="key", batch_size=50)
        assert mock_post.call_count == 3
        assert len(result) == 150


class TestEmbedQuery:
    @patch("open_medicine.graphrag.ingestion.embeddings.embed_texts")
    def test_returns_single_vector(self, mock_embed):
        mock_embed.return_value = [[0.1, 0.2, 0.3]]
        result = embed_query("dosing apixaban", api_key="key")
        assert result == [0.1, 0.2, 0.3]
        mock_embed.assert_called_once_with(
            ["dosing apixaban"], api_key="key",
            model="voyage-3-lite", input_type="query",
        )
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/graphrag/test_embeddings.py -v`
Expected: FAIL — module doesn't exist.

**Step 3: Implement embeddings client**

```python
# src/open_medicine/graphrag/ingestion/embeddings.py
from __future__ import annotations
import httpx

VOYAGE_API_URL = "https://api.voyageai.com/v1/embeddings"


def embed_texts(
    texts: list[str],
    api_key: str,
    model: str = "voyage-3-lite",
    input_type: str = "document",
    batch_size: int = 128,
) -> list[list[float]]:
    """Embed a list of texts using the Voyage AI API."""
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = httpx.post(
            VOYAGE_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "input": batch,
                "model": model,
                "input_type": input_type,
            },
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()["data"]
        all_embeddings.extend(item["embedding"] for item in data)

    return all_embeddings


def embed_query(
    text: str,
    api_key: str,
    model: str = "voyage-3-lite",
) -> list[float]:
    """Embed a single query text for similarity search."""
    results = embed_texts([text], api_key=api_key, model=model, input_type="query")
    return results[0]
```

**Step 4: Run tests**

Run: `uv run python -m pytest tests/graphrag/test_embeddings.py -v`
Expected: All PASS.

**Step 5: Commit**

```bash
git add src/open_medicine/graphrag/ingestion/embeddings.py tests/graphrag/test_embeddings.py
git commit -m "feat(graphrag): add Voyage AI embedding client with batching"
```

---

## Task R6: Add PatientVariable map to linker

**Files:**
- Modify: `src/open_medicine/graphrag/ingestion/linker.py`
- Modify: `tests/graphrag/test_linker.py`

**Step 1: Add new tests**

Append to the existing test file:

```python
# Add to tests/graphrag/test_linker.py

from open_medicine.graphrag.ingestion.linker import link_variable, LinkedVariable


class TestVariableLinker:
    def test_known_variable(self):
        result = link_variable("eGFR")
        assert result is not None
        assert result.canonical_name == "eGFR"
        assert result.loinc_code == "77147-7"
        assert result.unit == "mL/min/1.73m²"
        assert result.var_type == "continuous"

    def test_case_insensitive(self):
        r1 = link_variable("EGFR")
        r2 = link_variable("egfr")
        assert r1 is not None and r2 is not None
        assert r1.loinc_code == r2.loinc_code

    def test_unknown_variable(self):
        result = link_variable("nonexistent_var")
        assert result is None

    def test_boolean_variable(self):
        result = link_variable("pregnancy")
        assert result is not None
        assert result.var_type == "boolean"

    def test_age_variable(self):
        result = link_variable("age")
        assert result is not None
        assert result.var_type == "continuous"
```

**Step 2: Run to verify new tests fail**

Run: `uv run python -m pytest tests/graphrag/test_linker.py -v`
Expected: `TestVariableLinker` tests FAIL — `link_variable` doesn't exist.

**Step 3: Add LinkedVariable and _VAR_MAP to linker**

Add to the end of `src/open_medicine/graphrag/ingestion/linker.py`:

```python
@dataclass
class LinkedVariable:
    canonical_name: str
    loinc_code: str | None
    unit: str
    var_type: str  # "continuous" | "categorical" | "boolean"


_VAR_MAP: dict[str, LinkedVariable] = {
    "egfr": LinkedVariable("eGFR", "77147-7", "mL/min/1.73m²", "continuous"),
    "creatinine": LinkedVariable("Creatinine", "2160-0", "mg/dL", "continuous"),
    "potassium": LinkedVariable("Potassium", "2823-3", "mEq/L", "continuous"),
    "sodium": LinkedVariable("Sodium", "2951-2", "mEq/L", "continuous"),
    "age": LinkedVariable("Age", None, "years", "continuous"),
    "weight_kg": LinkedVariable("Weight", "29463-7", "kg", "continuous"),
    "height_cm": LinkedVariable("Height", "8302-2", "cm", "continuous"),
    "bmi": LinkedVariable("BMI", "39156-5", "kg/m²", "continuous"),
    "inr": LinkedVariable("INR", "6301-6", "", "continuous"),
    "bnp": LinkedVariable("BNP", "42637-9", "pg/mL", "continuous"),
    "nt-probnp": LinkedVariable("NT-proBNP", "33762-6", "pg/mL", "continuous"),
    "lvef": LinkedVariable("LVEF", "10230-1", "%", "continuous"),
    "qtc": LinkedVariable("QTc", "8897-1", "ms", "continuous"),
    "crcl": LinkedVariable("CrCl", "2164-2", "mL/min", "continuous"),
    "hemoglobin": LinkedVariable("Hemoglobin", "718-7", "g/dL", "continuous"),
    "hba1c": LinkedVariable("HbA1c", "4548-4", "%", "continuous"),
    "ldl": LinkedVariable("LDL", "13457-7", "mg/dL", "continuous"),
    "alt": LinkedVariable("ALT", "1742-6", "U/L", "continuous"),
    "ast": LinkedVariable("AST", "1920-8", "U/L", "continuous"),
    "albumin": LinkedVariable("Albumin", "1751-7", "g/dL", "continuous"),
    "pregnancy": LinkedVariable("Pregnancy", None, "", "boolean"),
    "breastfeeding": LinkedVariable("Breastfeeding", None, "", "boolean"),
    "dialysis": LinkedVariable("Dialysis", None, "", "boolean"),
    "sex": LinkedVariable("Sex", "46098-0", "", "categorical"),
}


def link_variable(name: str) -> LinkedVariable | None:
    """Resolve a patient variable name to its canonical form with LOINC code."""
    return _VAR_MAP.get(name.lower())
```

**Step 4: Run tests**

Run: `uv run python -m pytest tests/graphrag/test_linker.py -v`
Expected: All PASS (old + new).

**Step 5: Commit**

```bash
git add src/open_medicine/graphrag/ingestion/linker.py tests/graphrag/test_linker.py
git commit -m "feat(graphrag): add PatientVariable linker with LOINC mapping"
```

---

## Task R7: Create centralized Cypher queries module

**Files:**
- Create: `src/open_medicine/graphrag/graph/queries.py`
- Create: `tests/graphrag/test_queries.py`

**Step 1: Write failing tests**

```python
# tests/graphrag/test_queries.py
import json
from open_medicine.graphrag.graph.queries import LoaderQueries, ReasoningQueries
from open_medicine.graphrag.graph.schema import (
    Guideline, LogicNode, LogicNodeType, Condition,
)


class TestLoaderQueries:
    def test_delete_guideline_returns_two_queries(self):
        queries = LoaderQueries.delete_guideline("g1")
        assert len(queries) == 2
        assert all("DELETE" in q[0] for q in queries)
        assert all(q[1]["gid"] == "g1" for q in queries)

    def test_create_guideline(self):
        g = Guideline(id="g1", title="T", doi="10.1/x", year=2024, organization="O", total_pages=10)
        cypher, params = LoaderQueries.create_guideline(g)
        assert "Guideline" in cypher
        assert params["id"] == "g1"

    def test_create_evidence_chunk(self):
        cypher, params = LoaderQueries.create_evidence_chunk("c1", "text", "g1", "s1")
        assert "EvidenceChunk" in cypher
        assert params["id"] == "c1"

    def test_create_sourced_from(self):
        cypher, params = LoaderQueries.create_sourced_from("ln1", "c1")
        assert "SOURCED_FROM" in cypher
        assert params["lid"] == "ln1"
        assert params["cid"] == "c1"

    def test_create_evaluates(self):
        cypher, params = LoaderQueries.create_evaluates("ln1", "eGFR")
        assert "EVALUATES" in cypher
        assert params["lid"] == "ln1"
        assert params["vid"] == "eGFR"

    def test_create_patient_variable(self):
        cypher, params = LoaderQueries.create_patient_variable("eGFR", "eGFR", "mL/min/1.73m²", "77147-7", "continuous")
        assert "PatientVariable" in cypher
        assert "MERGE" in cypher

    def test_create_conflicts_with(self):
        cypher, params = LoaderQueries.create_conflicts_with("ln1", "ln2", "newer")
        assert "CONFLICTS_WITH" in cypher
        assert params["resolution"] == "newer"

    def test_create_interacts_with(self):
        cypher, params = LoaderQueries.create_interacts_with("drug_a", "drug_b")
        assert "INTERACTS_WITH" in cypher

    def test_create_belongs_to(self):
        cypher, params = LoaderQueries.create_belongs_to("c1", "g1")
        assert "BELONGS_TO" in cypher

    def test_create_child_of(self):
        cypher, params = LoaderQueries.create_child_of("child", "parent")
        assert "CHILD_OF" in cypher

    def test_create_defined_by(self):
        cypher, params = LoaderQueries.create_defined_by("ln1", "g1")
        assert "DEFINED_BY" in cypher

    def test_create_participates_in(self):
        cypher, params = LoaderQueries.create_participates_in("c1", "ln1", "intervention")
        assert "PARTICIPATES_IN" in cypher
        assert params["role"] == "intervention"

    def test_create_logic_node(self):
        conds_json = json.dumps([{"variable": "eGFR", "operator": "<", "threshold": 25}])
        cypher, params = LoaderQueries.create_logic_node("ln1", "dosing", conds_json, "contraindicated", "Detail", "Strong/A", "g1", 10)
        assert "LogicNode" in cypher
        assert params["type"] == "dosing"

    def test_create_concept(self):
        cypher, params = LoaderQueries.create_concept("apixaban", "Apixaban", "drug", "703899003", None)
        assert "MERGE" in cypher
        assert "Concept" in cypher


class TestReasoningQueries:
    def test_find_logic_nodes_basic(self):
        cypher, params = ReasoningQueries.find_logic_nodes("dosing", ["apixaban"])
        assert "PARTICIPATES_IN" in cypher
        assert "SOURCED_FROM" in cypher
        assert params["intent"] == "dosing"
        assert params["concepts"] == ["apixaban"]

    def test_find_logic_nodes_with_filter(self):
        cypher, params = ReasoningQueries.find_logic_nodes("dosing", ["apixaban"], guideline_filter="af_2023")
        assert "gfilter" in params
        assert "guideline_id" in cypher

    def test_find_logic_nodes_returns_distinct(self):
        cypher, _ = ReasoningQueries.find_logic_nodes("dosing", ["x"])
        assert "DISTINCT" in cypher

    def test_vector_search(self):
        cypher, params = ReasoningQueries.vector_search([0.1, 0.2], limit=5)
        assert "vector" in cypher.lower()
        assert params["limit"] == 5

    def test_graph_enhanced_context(self):
        cypher, params = ReasoningQueries.graph_enhanced_context("c1")
        assert "CHILD_OF" in cypher
        assert "SOURCED_FROM" in cypher
        assert params["id"] == "c1"

    def test_get_evidence_chunk(self):
        cypher, params = ReasoningQueries.get_evidence_chunk("c1")
        assert "EvidenceChunk" in cypher
        assert params["id"] == "c1"

    def test_list_guidelines(self):
        cypher, params = ReasoningQueries.list_guidelines()
        assert "Guideline" in cypher

    def test_find_conflicts(self):
        cypher, params = ReasoningQueries.find_conflicts(["ln1", "ln2"])
        assert "CONFLICTS_WITH" in cypher
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/graphrag/test_queries.py -v`
Expected: FAIL — module doesn't exist.

**Step 3: Implement queries module**

```python
# src/open_medicine/graphrag/graph/queries.py
from __future__ import annotations
from open_medicine.graphrag.graph.schema import Guideline


class LoaderQueries:
    """Cypher builders for ingestion."""

    @staticmethod
    def delete_guideline(guideline_id: str) -> list[tuple[str, dict]]:
        return [
            ("MATCH (n) WHERE n.guideline_id = $gid DETACH DELETE n", {"gid": guideline_id}),
            ("MATCH (g:Guideline {id: $gid}) DETACH DELETE g", {"gid": guideline_id}),
        ]

    @staticmethod
    def create_guideline(guideline: Guideline) -> tuple[str, dict]:
        return (
            "CREATE (g:Guideline {id: $id, title: $title, doi: $doi, year: $year, "
            "organization: $org, total_pages: $pages})",
            {
                "id": guideline.id, "title": guideline.title,
                "doi": guideline.doi, "year": guideline.year,
                "org": guideline.organization, "pages": guideline.total_pages,
            },
        )

    @staticmethod
    def create_evidence_chunk(chunk_id: str, text: str, guideline_id: str, section: str) -> tuple[str, dict]:
        return (
            "CREATE (ec:EvidenceChunk {id: $id, text: $text, guideline_id: $gid, section: $section})",
            {"id": chunk_id, "text": text, "gid": guideline_id, "section": section},
        )

    @staticmethod
    def create_logic_node(
        node_id: str, node_type: str, conditions_json: str,
        action: str, action_detail: str, strength: str,
        guideline_id: str, page: int,
    ) -> tuple[str, dict]:
        return (
            "CREATE (ln:LogicNode {id: $id, type: $type, conditions: $conds, action: $action, "
            "action_detail: $detail, strength: $strength, guideline_id: $gid, page: $page})",
            {
                "id": node_id, "type": node_type, "conds": conditions_json,
                "action": action, "detail": action_detail,
                "strength": strength, "gid": guideline_id, "page": page,
            },
        )

    @staticmethod
    def create_concept(
        concept_id: str, name: str, concept_type: str,
        snomed_code: str | None, loinc_code: str | None,
    ) -> tuple[str, dict]:
        return (
            "MERGE (c:Concept {id: $id}) "
            "ON CREATE SET c.name = $name, c.type = $type, c.snomed_code = $snomed, c.loinc_code = $loinc",
            {"id": concept_id, "name": name, "type": concept_type, "snomed": snomed_code, "loinc": loinc_code},
        )

    @staticmethod
    def create_patient_variable(
        var_id: str, name: str, unit: str,
        loinc_code: str | None, var_type: str,
    ) -> tuple[str, dict]:
        return (
            "MERGE (pv:PatientVariable {id: $id}) "
            "ON CREATE SET pv.name = $name, pv.unit = $unit, pv.loinc_code = $loinc, pv.type = $type",
            {"id": var_id, "name": name, "unit": unit, "loinc": loinc_code, "type": var_type},
        )

    @staticmethod
    def create_belongs_to(chunk_id: str, guideline_id: str) -> tuple[str, dict]:
        return (
            "MATCH (ec:EvidenceChunk {id: $cid}), (g:Guideline {id: $gid}) "
            "CREATE (ec)-[:BELONGS_TO]->(g)",
            {"cid": chunk_id, "gid": guideline_id},
        )

    @staticmethod
    def create_child_of(child_id: str, parent_id: str) -> tuple[str, dict]:
        return (
            "MATCH (child:EvidenceChunk {id: $cid}), (parent:EvidenceChunk {id: $pid}) "
            "CREATE (child)-[:CHILD_OF]->(parent)",
            {"cid": child_id, "pid": parent_id},
        )

    @staticmethod
    def create_defined_by(logic_node_id: str, guideline_id: str) -> tuple[str, dict]:
        return (
            "MATCH (ln:LogicNode {id: $lid}), (g:Guideline {id: $gid}) "
            "CREATE (ln)-[:DEFINED_BY]->(g)",
            {"lid": logic_node_id, "gid": guideline_id},
        )

    @staticmethod
    def create_sourced_from(logic_node_id: str, chunk_id: str) -> tuple[str, dict]:
        return (
            "MATCH (ln:LogicNode {id: $lid}), (ec:EvidenceChunk {id: $cid}) "
            "CREATE (ln)-[:SOURCED_FROM]->(ec)",
            {"lid": logic_node_id, "cid": chunk_id},
        )

    @staticmethod
    def create_evaluates(logic_node_id: str, variable_id: str) -> tuple[str, dict]:
        return (
            "MATCH (ln:LogicNode {id: $lid}), (pv:PatientVariable {id: $vid}) "
            "CREATE (ln)-[:EVALUATES]->(pv)",
            {"lid": logic_node_id, "vid": variable_id},
        )

    @staticmethod
    def create_participates_in(concept_id: str, logic_node_id: str, role: str) -> tuple[str, dict]:
        return (
            "MATCH (c:Concept {id: $cid}), (ln:LogicNode {id: $lid}) "
            "CREATE (c)-[:PARTICIPATES_IN {role: $role}]->(ln)",
            {"cid": concept_id, "lid": logic_node_id, "role": role},
        )

    @staticmethod
    def create_conflicts_with(ln_a_id: str, ln_b_id: str, resolution: str) -> tuple[str, dict]:
        return (
            "MATCH (a:LogicNode {id: $aid}), (b:LogicNode {id: $bid}) "
            "CREATE (a)-[:CONFLICTS_WITH {resolution: $resolution}]->(b)",
            {"aid": ln_a_id, "bid": ln_b_id, "resolution": resolution},
        )

    @staticmethod
    def create_interacts_with(concept_a_id: str, concept_b_id: str) -> tuple[str, dict]:
        return (
            "MATCH (a:Concept {id: $aid}), (b:Concept {id: $bid}) "
            "MERGE (a)-[:INTERACTS_WITH]->(b)",
            {"aid": concept_a_id, "bid": concept_b_id},
        )

    @staticmethod
    def set_embedding(chunk_id: str, embedding: list[float]) -> tuple[str, dict]:
        return (
            "MATCH (ec:EvidenceChunk {id: $id}) SET ec.embedding = $embedding",
            {"id": chunk_id, "embedding": embedding},
        )


class ReasoningQueries:
    """Cypher builders for query-time traversal."""

    @staticmethod
    def find_logic_nodes(
        intent: str, concept_ids: list[str],
        guideline_filter: str | None = None,
    ) -> tuple[str, dict]:
        cypher = (
            "MATCH (c:Concept)-[:PARTICIPATES_IN]->(ln:LogicNode {type: $intent})"
            "-[:SOURCED_FROM]->(ec:EvidenceChunk)-[:BELONGS_TO]->(g:Guideline) "
            "WHERE c.id IN $concepts "
        )
        params: dict = {"intent": intent, "concepts": concept_ids}
        if guideline_filter:
            cypher += "AND ln.guideline_id = $gfilter "
            params["gfilter"] = guideline_filter
        cypher += (
            "RETURN DISTINCT ln.id AS ln_id, ln.type AS ln_type, ln.action AS ln_action, "
            "ln.action_detail AS ln_detail, ln.strength AS ln_strength, "
            "ln.conditions AS ln_conditions, ln.page AS ln_page, "
            "ec.id AS ec_id, ec.text AS ec_text, ec.section AS ec_section, "
            "g.title AS g_title, g.doi AS g_doi, g.year AS g_year "
            "ORDER BY g.year DESC"
        )
        return (cypher, params)

    @staticmethod
    def vector_search(query_embedding: list[float], limit: int = 10) -> tuple[str, dict]:
        return (
            "CALL db.index.vector.queryNodes('evidence_embedding', $limit, $embedding) "
            "YIELD node, score "
            "MATCH (node)-[:BELONGS_TO]->(g:Guideline) "
            "RETURN node.id AS ec_id, node.text AS ec_text, node.section AS ec_section, "
            "score, g.title AS g_title, g.doi AS g_doi "
            "ORDER BY score DESC",
            {"embedding": query_embedding, "limit": limit},
        )

    @staticmethod
    def graph_enhanced_context(chunk_id: str) -> tuple[str, dict]:
        return (
            "MATCH (ec:EvidenceChunk {id: $id}) "
            "OPTIONAL MATCH (ec)-[:CHILD_OF]->(parent:EvidenceChunk) "
            "OPTIONAL MATCH (ln:LogicNode)-[:SOURCED_FROM]->(ec) "
            "RETURN ec.text AS text, parent.text AS parent_text, "
            "collect(DISTINCT {id: ln.id, type: ln.type, action: ln.action, detail: ln.action_detail}) AS related_nodes",
            {"id": chunk_id},
        )

    @staticmethod
    def get_evidence_chunk(chunk_id: str) -> tuple[str, dict]:
        return (
            "MATCH (ec:EvidenceChunk {id: $id})-[:BELONGS_TO]->(g:Guideline) "
            "RETURN ec.text AS text, ec.section AS section, g.title AS guideline, g.doi AS doi",
            {"id": chunk_id},
        )

    @staticmethod
    def list_guidelines() -> tuple[str, dict]:
        return (
            "MATCH (g:Guideline) RETURN g.id AS id, g.title AS title, g.doi AS doi, g.year AS year",
            {},
        )

    @staticmethod
    def find_conflicts(logic_node_ids: list[str]) -> tuple[str, dict]:
        return (
            "MATCH (a:LogicNode)-[r:CONFLICTS_WITH]->(b:LogicNode) "
            "WHERE a.id IN $ids AND b.id IN $ids "
            "RETURN a.id AS winner_id, b.id AS loser_id, r.resolution AS resolution",
            {"ids": logic_node_ids},
        )
```

**Step 4: Run tests**

Run: `uv run python -m pytest tests/graphrag/test_queries.py -v`
Expected: All PASS.

**Step 5: Commit**

```bash
git add src/open_medicine/graphrag/graph/queries.py tests/graphrag/test_queries.py
git commit -m "feat(graphrag): add centralized Cypher query builders"
```

---

## Task R8: Add retry + dead letter queue to extractor

**Files:**
- Modify: `src/open_medicine/graphrag/ingestion/extractor.py`
- Modify: `tests/graphrag/test_extractor.py`

**Step 1: Add new tests**

Append to the existing test file:

```python
# Add to tests/graphrag/test_extractor.py
import time
from open_medicine.graphrag.ingestion.extractor import _call_llm_with_retry


class TestRetry:
    @patch("open_medicine.graphrag.ingestion.extractor._call_llm")
    def test_retries_on_rate_limit(self, mock_llm):
        import anthropic
        mock_llm.side_effect = [
            anthropic.RateLimitError("rate limited", response=MagicMock(status_code=429), body=None),
            "[]",
        ]
        result = _call_llm_with_retry("prompt", max_retries=3, base_delay=0.01)
        assert result == "[]"
        assert mock_llm.call_count == 2

    @patch("open_medicine.graphrag.ingestion.extractor._call_llm")
    def test_raises_after_max_retries(self, mock_llm):
        import anthropic
        mock_llm.side_effect = anthropic.RateLimitError(
            "rate limited", response=MagicMock(status_code=429), body=None,
        )
        with pytest.raises(anthropic.RateLimitError):
            _call_llm_with_retry("prompt", max_retries=2, base_delay=0.01)
        assert mock_llm.call_count == 2

    @patch("open_medicine.graphrag.ingestion.extractor._call_llm")
    def test_no_retry_on_other_errors(self, mock_llm):
        mock_llm.side_effect = ValueError("bad input")
        with pytest.raises(ValueError):
            _call_llm_with_retry("prompt", max_retries=3, base_delay=0.01)
        assert mock_llm.call_count == 1
```

**Step 2: Run to verify new tests fail**

Run: `uv run python -m pytest tests/graphrag/test_extractor.py -v`
Expected: `TestRetry` tests FAIL — `_call_llm_with_retry` doesn't exist.

**Step 3: Add retry wrapper to extractor**

Add after the existing `_call_llm` function in `src/open_medicine/graphrag/ingestion/extractor.py`:

```python
import time
import anthropic as _anthropic

def _call_llm_with_retry(
    prompt: str,
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> str:
    """Call LLM with exponential backoff on transient errors."""
    for attempt in range(max_retries):
        try:
            return _call_llm(prompt)
        except (_anthropic.RateLimitError, _anthropic.APIConnectionError):
            if attempt == max_retries - 1:
                raise
            time.sleep(base_delay * (2 ** attempt))
```

Also update `extract_logic_nodes` to use the retry wrapper — change `raw = _call_llm(prompt)` to `raw = _call_llm_with_retry(prompt)`.

**Step 4: Run tests**

Run: `uv run python -m pytest tests/graphrag/test_extractor.py -v`
Expected: All PASS (old + new).

**Step 5: Commit**

```bash
git add src/open_medicine/graphrag/ingestion/extractor.py tests/graphrag/test_extractor.py
git commit -m "feat(graphrag): add LLM retry with exponential backoff"
```

---

## Task R9: Refactor loader with all edges and embeddings

**Files:**
- Modify: `src/open_medicine/graphrag/ingestion/loader.py`
- Modify: `tests/graphrag/test_loader.py`

**Step 1: Rewrite tests**

```python
# tests/graphrag/test_loader.py
from unittest.mock import MagicMock, patch
from open_medicine.graphrag.ingestion.loader import load_guideline, LoadableGuideline, detect_conflicts
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
                source_chunk_id="child_1",
            ),
        ],
    )


class TestLoader:
    def test_calls_execute_write_tx(self):
        conn = MagicMock()
        load_guideline(conn, _make_loadable())
        conn.execute_write_tx.assert_called()

    def test_generates_sourced_from_edge(self):
        conn = MagicMock()
        load_guideline(conn, _make_loadable())
        queries = conn.execute_write_tx.call_args[0][0]
        cypher_strs = [q[0] for q in queries]
        assert any("SOURCED_FROM" in s for s in cypher_strs)

    def test_generates_evaluates_edge(self):
        conn = MagicMock()
        load_guideline(conn, _make_loadable())
        queries = conn.execute_write_tx.call_args[0][0]
        cypher_strs = [q[0] for q in queries]
        assert any("EVALUATES" in s for s in cypher_strs)

    def test_generates_patient_variable_node(self):
        conn = MagicMock()
        load_guideline(conn, _make_loadable())
        queries = conn.execute_write_tx.call_args[0][0]
        cypher_strs = [q[0] for q in queries]
        assert any("PatientVariable" in s for s in cypher_strs)

    def test_generates_all_edge_types(self):
        conn = MagicMock()
        load_guideline(conn, _make_loadable())
        queries = conn.execute_write_tx.call_args[0][0]
        cypher_strs = [q[0] for q in queries]
        for edge in ["BELONGS_TO", "CHILD_OF", "DEFINED_BY", "PARTICIPATES_IN", "SOURCED_FROM", "EVALUATES"]:
            assert any(edge in s for s in cypher_strs), f"Missing {edge} edge"

    def test_generates_guideline_and_chunks_and_logic_nodes(self):
        conn = MagicMock()
        load_guideline(conn, _make_loadable())
        queries = conn.execute_write_tx.call_args[0][0]
        cypher_strs = [q[0] for q in queries]
        for node in ["Guideline", "EvidenceChunk", "LogicNode", "Concept"]:
            assert any(node in s for s in cypher_strs), f"Missing {node} node"


class TestConflictDetection:
    def test_contradictory_actions_detected(self):
        extractions = [
            ExtractionResult(
                logic_node=LogicNode(
                    id="ln_a", type=LogicNodeType.DOSING,
                    conditions=[], action="initiate", action_detail="Start drug",
                    strength="Weak/C", guideline_id="g_old", page=1,
                ),
                concepts=[ConceptRef("apixaban", "drug")],
                source_chunk_id="c1",
            ),
            ExtractionResult(
                logic_node=LogicNode(
                    id="ln_b", type=LogicNodeType.DOSING,
                    conditions=[], action="contraindicated", action_detail="Do not use",
                    strength="Strong/A", guideline_id="g_new", page=1,
                ),
                concepts=[ConceptRef("apixaban", "drug")],
                source_chunk_id="c2",
            ),
        ]
        conflicts = detect_conflicts(extractions)
        assert len(conflicts) == 1
        assert conflicts[0][0] in ("ln_a", "ln_b")
        assert conflicts[0][1] in ("ln_a", "ln_b")

    def test_same_action_no_conflict(self):
        extractions = [
            ExtractionResult(
                logic_node=LogicNode(
                    id="ln_a", type=LogicNodeType.DOSING,
                    conditions=[], action="initiate", action_detail="Start",
                    strength="Strong/A", guideline_id="g1", page=1,
                ),
                concepts=[ConceptRef("apixaban", "drug")],
                source_chunk_id="c1",
            ),
            ExtractionResult(
                logic_node=LogicNode(
                    id="ln_b", type=LogicNodeType.DOSING,
                    conditions=[], action="initiate", action_detail="Also start",
                    strength="Moderate/B", guideline_id="g2", page=1,
                ),
                concepts=[ConceptRef("apixaban", "drug")],
                source_chunk_id="c2",
            ),
        ]
        conflicts = detect_conflicts(extractions)
        assert len(conflicts) == 0

    def test_different_types_no_conflict(self):
        extractions = [
            ExtractionResult(
                logic_node=LogicNode(
                    id="ln_a", type=LogicNodeType.DOSING,
                    conditions=[], action="initiate", action_detail="Start",
                    strength="Strong/A", guideline_id="g1", page=1,
                ),
                concepts=[ConceptRef("apixaban", "drug")],
                source_chunk_id="c1",
            ),
            ExtractionResult(
                logic_node=LogicNode(
                    id="ln_b", type=LogicNodeType.MONITORING,
                    conditions=[], action="monitor", action_detail="Check INR",
                    strength="Strong/A", guideline_id="g1", page=2,
                ),
                concepts=[ConceptRef("apixaban", "drug")],
                source_chunk_id="c2",
            ),
        ]
        conflicts = detect_conflicts(extractions)
        assert len(conflicts) == 0
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/graphrag/test_loader.py -v`
Expected: FAIL — `source_chunk_id` field missing from `ExtractionResult`, `detect_conflicts` doesn't exist.

**Step 3: Update ExtractionResult in extractor.py**

Add `source_chunk_id` field to `ExtractionResult`:

```python
@dataclass
class ExtractionResult:
    logic_node: LogicNode
    concepts: list[ConceptRef]
    source_chunk_id: str = ""
```

**Step 4: Rewrite loader**

```python
# src/open_medicine/graphrag/ingestion/loader.py
from __future__ import annotations
import json
from dataclasses import dataclass
from itertools import combinations
from open_medicine.graphrag.graph.schema import Guideline
from open_medicine.graphrag.graph.queries import LoaderQueries
from open_medicine.graphrag.ingestion.chunker import Chunk
from open_medicine.graphrag.ingestion.extractor import ExtractionResult
from open_medicine.graphrag.ingestion.linker import link_entity, link_variable
from open_medicine.graphrag.graph.connection import GraphConnection

CONTRADICTORY_ACTIONS = {
    frozenset({"initiate", "contraindicated"}),
    frozenset({"initiate", "avoid"}),
    frozenset({"dose_adjust", "contraindicated"}),
    frozenset({"prefer", "avoid"}),
    frozenset({"monitor", "contraindicated"}),
}

STRENGTH_RANK = {"Strong/A": 0, "Moderate/B": 1, "Weak/C": 2, "Expert_Opinion": 3}


@dataclass
class LoadableGuideline:
    guideline: Guideline
    chunks: list[Chunk]
    extractions: list[ExtractionResult]


def detect_conflicts(
    extractions: list[ExtractionResult],
) -> list[tuple[str, str, str]]:
    """Detect conflicting LogicNode pairs. Returns (winner_id, loser_id, resolution)."""
    conflicts: list[tuple[str, str, str]] = []

    # Group by (shared concept, type)
    by_key: dict[tuple[str, str], list[ExtractionResult]] = {}
    for ext in extractions:
        for concept in ext.concepts:
            key = (concept.name.lower(), ext.logic_node.type.value)
            by_key.setdefault(key, []).append(ext)

    for group in by_key.values():
        if len(group) < 2:
            continue
        for a, b in combinations(group, 2):
            action_pair = frozenset({a.logic_node.action, b.logic_node.action})
            if action_pair not in CONTRADICTORY_ACTIONS:
                continue

            # Determine winner
            a_year = int(a.logic_node.guideline_id.split("_")[-1]) if a.logic_node.guideline_id.split("_")[-1].isdigit() else 0
            b_year = int(b.logic_node.guideline_id.split("_")[-1]) if b.logic_node.guideline_id.split("_")[-1].isdigit() else 0

            if a_year != b_year:
                resolution = "newer"
                winner, loser = (a, b) if a_year > b_year else (b, a)
            else:
                resolution = "stronger"
                a_rank = STRENGTH_RANK.get(a.logic_node.strength, 99)
                b_rank = STRENGTH_RANK.get(b.logic_node.strength, 99)
                winner, loser = (a, b) if a_rank <= b_rank else (b, a)

            conflicts.append((winner.logic_node.id, loser.logic_node.id, resolution))

    return conflicts


def load_guideline(conn: GraphConnection, data: LoadableGuideline) -> None:
    """Load a complete guideline into Neo4j as a single transaction."""
    queries: list[tuple[str, dict]] = []

    # 1. Delete existing data (idempotent)
    queries.extend(LoaderQueries.delete_guideline(data.guideline.id))

    # 2. Create Guideline node
    queries.append(LoaderQueries.create_guideline(data.guideline))

    # 3. Create EvidenceChunk nodes + edges
    for chunk in data.chunks:
        queries.append(LoaderQueries.create_evidence_chunk(
            chunk.id, chunk.text, chunk.guideline_id, chunk.section,
        ))
        queries.append(LoaderQueries.create_belongs_to(chunk.id, data.guideline.id))
        if chunk.parent_chunk_id:
            queries.append(LoaderQueries.create_child_of(chunk.id, chunk.parent_chunk_id))

    # 4. Create LogicNode + Concept + PatientVariable nodes + all edges
    seen_variables: set[str] = set()
    for extraction in data.extractions:
        ln = extraction.logic_node
        conditions_json = json.dumps([c.model_dump() for c in ln.conditions])
        queries.append(LoaderQueries.create_logic_node(
            ln.id, ln.type.value, conditions_json,
            ln.action, ln.action_detail, ln.strength,
            ln.guideline_id, ln.page,
        ))
        queries.append(LoaderQueries.create_defined_by(ln.id, data.guideline.id))

        # SOURCED_FROM edge
        if extraction.source_chunk_id:
            queries.append(LoaderQueries.create_sourced_from(ln.id, extraction.source_chunk_id))

        # Concept nodes + PARTICIPATES_IN edges
        drug_concepts: list[str] = []
        for concept_ref in extraction.concepts:
            linked = link_entity(concept_ref.name, concept_ref.type)
            c_id = concept_ref.name.lower().replace(" ", "_")
            c_name = linked.canonical_name if linked else concept_ref.name
            snomed = linked.snomed_code if linked else None
            loinc = linked.loinc_code if linked else None

            queries.append(LoaderQueries.create_concept(c_id, c_name, concept_ref.type, snomed, loinc))
            queries.append(LoaderQueries.create_participates_in(c_id, ln.id, "intervention"))

            if concept_ref.type == "drug":
                drug_concepts.append(c_id)

        # INTERACTS_WITH edges for interaction-type LogicNodes
        if ln.type.value == "interaction" and len(drug_concepts) >= 2:
            for i in range(len(drug_concepts)):
                for j in range(i + 1, len(drug_concepts)):
                    queries.append(LoaderQueries.create_interacts_with(drug_concepts[i], drug_concepts[j]))

        # PatientVariable nodes + EVALUATES edges
        for cond in ln.conditions:
            var_name = cond.variable
            if var_name not in seen_variables:
                seen_variables.add(var_name)
                linked_var = link_variable(var_name)
                if linked_var:
                    queries.append(LoaderQueries.create_patient_variable(
                        var_name, linked_var.canonical_name,
                        linked_var.unit, linked_var.loinc_code, linked_var.var_type,
                    ))
                else:
                    queries.append(LoaderQueries.create_patient_variable(
                        var_name, var_name, "", None, "continuous",
                    ))
            queries.append(LoaderQueries.create_evaluates(ln.id, var_name))

    # 5. Conflict detection
    conflicts = detect_conflicts(data.extractions)
    for winner_id, loser_id, resolution in conflicts:
        queries.append(LoaderQueries.create_conflicts_with(winner_id, loser_id, resolution))

    conn.execute_write_tx(queries)
```

**Step 5: Run tests**

Run: `uv run python -m pytest tests/graphrag/test_loader.py -v`
Expected: All PASS.

**Step 6: Commit**

```bash
git add src/open_medicine/graphrag/ingestion/loader.py src/open_medicine/graphrag/ingestion/extractor.py tests/graphrag/test_loader.py
git commit -m "refactor(graphrag): loader creates all edges, PatientVariables, and detects conflicts"
```

---

## Task R10: Refactor reasoning engine with deduplication and conflicts

**Files:**
- Modify: `src/open_medicine/graphrag/reasoning/engine.py`
- Modify: `tests/graphrag/test_engine.py`

**Step 1: Update tests**

```python
# tests/graphrag/test_engine.py
import json
import pytest
from unittest.mock import MagicMock
from open_medicine.graphrag.reasoning.engine import ReasoningEngine
from open_medicine.graphrag.reasoning.types import ClinicalQuery


def _mock_conn_with_results(read_results: list[dict], conflict_results: list[dict] | None = None) -> MagicMock:
    conn = MagicMock()
    if conflict_results is not None:
        conn.execute_read.side_effect = [read_results, conflict_results]
    else:
        conn.execute_read.side_effect = [read_results, []]
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
        assert result is None


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

    def test_deduplication_by_logic_node_id(self):
        """Same LogicNode appearing via two EvidenceChunks should be deduplicated."""
        mock_results = [
            {
                "ln_id": "ln_001", "ln_type": "dosing", "ln_action": "dose_adjust",
                "ln_detail": "Reduce", "ln_strength": "Strong/A",
                "ln_conditions": json.dumps([]),
                "ln_page": 10,
                "ec_id": "c1", "ec_text": "Source 1",
                "g_title": "Guide", "g_doi": "10.1/x", "g_year": 2023,
                "ec_section": "dosing",
            },
            {
                "ln_id": "ln_001", "ln_type": "dosing", "ln_action": "dose_adjust",
                "ln_detail": "Reduce", "ln_strength": "Strong/A",
                "ln_conditions": json.dumps([]),
                "ln_page": 10,
                "ec_id": "c2", "ec_text": "Source 2",
                "g_title": "Guide", "g_doi": "10.1/x", "g_year": 2023,
                "ec_section": "dosing",
            },
        ]
        conn = _mock_conn_with_results(mock_results)
        engine = ReasoningEngine(conn)
        query = ClinicalQuery(intent="dosing", concepts=["drug"])
        result = engine.query(query)
        assert len(result.matches) == 1
        assert len(result.evidence) == 2  # both citations kept
```

**Step 2: Rewrite engine**

```python
# src/open_medicine/graphrag/reasoning/engine.py
from __future__ import annotations
import json
import operator
from typing import Any
from open_medicine.graphrag.graph.connection import GraphConnection
from open_medicine.graphrag.graph.queries import ReasoningQueries
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
            return None
        op_fn = OPS.get(cond["operator"])
        if not op_fn:
            return None
        try:
            return op_fn(float(patient_vars[var]), float(cond["threshold"]))
        except (ValueError, TypeError):
            return op_fn(str(patient_vars[var]), str(cond["threshold"]))

    def query(self, q: ClinicalQuery) -> GraphRAGResult:
        concept_ids = [c.lower().replace(" ", "_") for c in q.concepts]

        cypher, params = ReasoningQueries.find_logic_nodes(
            q.intent, concept_ids, q.guideline_filter,
        )
        rows = self._conn.execute_read(cypher, params)

        # Deduplicate by ln_id, collect evidence
        seen: dict[str, dict] = {}
        evidence_map: dict[str, list[EvidenceCitation]] = {}

        for row in rows:
            ln_id = row["ln_id"]
            citation = EvidenceCitation(
                chunk_id=row["ec_id"], text=row["ec_text"],
                guideline_title=row["g_title"], doi=row["g_doi"],
                section=row["ec_section"], page=row["ln_page"],
            )
            if ln_id not in seen:
                seen[ln_id] = row
                evidence_map[ln_id] = []
            evidence_map[ln_id].append(citation)

        # Build matches
        matches: list[LogicNodeMatch] = []
        all_evidence: list[EvidenceCitation] = []
        all_missing: list[str] = []

        for ln_id, row in seen.items():
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
                logic_node_id=ln_id,
                type=row["ln_type"],
                action=row["ln_action"],
                action_detail=row["ln_detail"],
                strength=row["ln_strength"],
                conditions_met=conditions_met,
                missing_variables=missing_vars,
            ))
            all_evidence.extend(evidence_map[ln_id])
            all_missing.extend(missing_vars)

        # Check for CONFLICTS_WITH among matched nodes
        if len(matches) >= 2:
            matched_ids = [m.logic_node_id for m in matches]
            conflict_cypher, conflict_params = ReasoningQueries.find_conflicts(matched_ids)
            conflict_rows = self._conn.execute_read(conflict_cypher, conflict_params)
            loser_ids = {r["loser_id"] for r in conflict_rows}
            for m in matches:
                if m.logic_node_id in loser_ids:
                    m.conditions_met = False
                    m.action_detail += " [superseded by newer/stronger guideline]"

        # Sort: full matches first, then by strength
        matches.sort(key=lambda m: (
            not m.conditions_met,
            STRENGTH_RANK.get(m.strength, 99),
        ))

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
            evidence=all_evidence,
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
git commit -m "refactor(graphrag): engine uses queries.py, deduplicates, resolves conflicts"
```

---

## Task R11: Refactor fallback with vector search and graph-enhanced retrieval

**Files:**
- Modify: `src/open_medicine/graphrag/reasoning/fallback.py`
- Modify: `tests/graphrag/test_fallback.py`

**Step 1: Update tests**

```python
# tests/graphrag/test_fallback.py
import pytest
from unittest.mock import MagicMock, patch, call
from open_medicine.graphrag.reasoning.fallback import FallbackEngine
from open_medicine.graphrag.reasoning.types import ClinicalQuery, GraphRAGResult


class TestFallbackEngine:
    def test_returns_llm_synthesis_source(self):
        conn = MagicMock()
        # First call: vector search results, Second call: graph context
        conn.execute_read.side_effect = [
            [
                {
                    "ec_id": "c1", "ec_text": "Apixaban 5mg twice daily for AF.",
                    "ec_section": "dosing", "score": 0.92,
                    "g_title": "AF Guideline", "g_doi": "10.1/af",
                },
            ],
            [
                {
                    "text": "Apixaban 5mg twice daily for AF.",
                    "parent_text": "Full section on anticoagulation.",
                    "related_nodes": [],
                },
            ],
        ]
        engine = FallbackEngine(conn, voyage_api_key="test-key")

        with patch.object(engine, "_embed_query", return_value=[0.1, 0.2]):
            with patch.object(engine, "_synthesize") as mock_synth:
                mock_synth.return_value = "Based on the AF guideline, apixaban 5mg BID is recommended."
                result = engine.query(query=ClinicalQuery(intent="dosing", concepts=["apixaban"]))

        assert result.source == "llm_synthesis"
        assert result.synthesis is not None
        assert result.confidence == "medium"
        assert len(result.evidence) > 0

    def test_no_chunks_returns_low_confidence(self):
        conn = MagicMock()
        conn.execute_read.return_value = []
        engine = FallbackEngine(conn, voyage_api_key="test-key")

        with patch.object(engine, "_embed_query", return_value=[0.1]):
            result = engine.query(ClinicalQuery(intent="dosing", concepts=["unknowndrug"]))

        assert result.confidence == "low"
        assert result.synthesis is None

    def test_uses_vector_search_query(self):
        conn = MagicMock()
        conn.execute_read.return_value = []
        engine = FallbackEngine(conn, voyage_api_key="test-key")

        with patch.object(engine, "_embed_query", return_value=[0.1, 0.2]) as mock_embed:
            engine.query(ClinicalQuery(intent="dosing", concepts=["apixaban"]))

        mock_embed.assert_called_once()
        cypher_call = conn.execute_read.call_args[0][0]
        assert "vector" in cypher_call.lower()
```

**Step 2: Rewrite fallback**

```python
# src/open_medicine/graphrag/reasoning/fallback.py
from __future__ import annotations
from open_medicine.graphrag.graph.connection import GraphConnection
from open_medicine.graphrag.graph.queries import ReasoningQueries
from open_medicine.graphrag.ingestion.embeddings import embed_query
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
    def __init__(self, conn: GraphConnection, voyage_api_key: str = "") -> None:
        self._conn = conn
        self._voyage_api_key = voyage_api_key

    def _embed_query(self, text: str) -> list[float]:
        return embed_query(text, api_key=self._voyage_api_key)

    def _synthesize(self, question: str, sources: str) -> str:
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
        query_vector = self._embed_query(query_text)

        cypher, params = ReasoningQueries.vector_search(query_vector)
        rows = self._conn.execute_read(cypher, params)

        if not rows:
            return GraphRAGResult(
                source="llm_synthesis", matches=[],
                synthesis=None, evidence=[],
                confidence="low", missing_variables=[],
            )

        # Graph-enhanced: get parent context for each chunk
        enhanced_sources: list[str] = []
        evidence: list[EvidenceCitation] = []
        for r in rows:
            ctx_cypher, ctx_params = ReasoningQueries.graph_enhanced_context(r["ec_id"])
            ctx_rows = self._conn.execute_read(ctx_cypher, ctx_params)

            chunk_text = r["ec_text"]
            parent_text = ""
            if ctx_rows and ctx_rows[0].get("parent_text"):
                parent_text = ctx_rows[0]["parent_text"]

            source_block = f"[{r['g_title']}, {r['ec_section']}]\n"
            if parent_text:
                source_block += f"Context: {parent_text[:200]}...\n"
            source_block += chunk_text
            enhanced_sources.append(source_block)

            evidence.append(EvidenceCitation(
                chunk_id=r["ec_id"], text=r["ec_text"],
                guideline_title=r["g_title"], doi=r["g_doi"],
                section=r["ec_section"], page=0,
            ))

        sources_text = "\n\n---\n\n".join(enhanced_sources)
        question = f"{q.intent}: {', '.join(q.concepts)}"
        if q.patient_vars:
            question += f" (patient: {q.patient_vars})"

        synthesis = self._synthesize(question, sources_text)

        return GraphRAGResult(
            source="llm_synthesis", matches=[],
            synthesis=synthesis, evidence=evidence,
            confidence="medium", missing_variables=[],
        )
```

**Step 3: Run tests**

Run: `uv run python -m pytest tests/graphrag/test_fallback.py -v`
Expected: All PASS.

**Step 4: Run full graphrag test suite**

Run: `uv run python -m pytest tests/graphrag/ -v`
Expected: All PASS.

**Step 5: Commit**

```bash
git add src/open_medicine/graphrag/reasoning/fallback.py tests/graphrag/test_fallback.py
git commit -m "refactor(graphrag): fallback uses vector search and graph-enhanced retrieval"
```

---

## Phase Summary

| Task | What it fixes | Gap # |
|------|-------------|-------|
| R1 | Config → Voyage defaults | Setup |
| R2 | Connection → managed transactions | #5 |
| R3 | Indexes → vector + PatientVariable | #2, #3 |
| R4 | Dead letter queue (new module) | Resilience |
| R5 | Embeddings client (new module) | #3 |
| R6 | Linker → PatientVariable map | #2 |
| R7 | Queries module (new) | #4 |
| R8 | Extractor → retry + DLQ | Resilience |
| R9 | Loader → all edges + conflicts | #1, #2, #7, #8 |
| R10 | Engine → dedup + conflicts + queries.py | #4, #6, #7 |
| R11 | Fallback → vector search + graph context | #3, #4 |

**All 8 gaps addressed. 11 tasks, ~11 commits.**

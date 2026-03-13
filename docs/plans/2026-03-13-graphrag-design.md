# GraphRAG Clinical Decision Support System — Design Document

**Date:** 2026-03-13
**Status:** Approved
**Module:** `src/open_medicine/graphrag/`

## 1. System Overview

Build a high-precision Clinical Decision Support System (CDSS) that navigates 100,000+ pages of medical guidelines by constructing a Neo4j knowledge graph from real guideline PDFs. The system transitions from document retrieval to logic traversal — reasoning over typed clinical rules extracted from source texts.

### Relationship to Existing System

**Parallel track.** The existing guideline system (`mcp/guidelines/`) remains untouched. The GraphRAG module is a new, independent module that shares only `foundation/` models (`ClinicalResult`, `Evidence`). No imports between `graphrag/` and `mcp/`.

### Core Decisions

| Decision | Choice |
|---|---|
| Migration strategy | Parallel track, new module |
| Source data | Real guideline PDFs from the internet |
| Graph DB | Neo4j (required) |
| Entity linking | SNOMED/LOINC/FHIR codes (no UMLS) |
| Extraction | LLM-driven at ingestion time |
| Runtime model | Deterministic graph traversal, LLM fallback |
| MCP tools | High-level clinical tools + structured query |
| Hosting | Neo4j Aura + Railway |
| API transport | REST (FastAPI) + MCP over SSE |
| Auth | Simple API key |
| Initial guidelines | 5 (AF, CKD, CAP, HF, ASCVD) |
| Ingestion | Admin/developer only |
| Approach | Hybrid typed LogicNode reification |

## 2. Module Structure

```
src/open_medicine/
├── foundation/          # Existing — shared models (ClinicalResult, Evidence)
├── mcp/                 # Existing — current calculators, guidelines, differentials
├── embeddings/          # Existing — optional semantic search
└── graphrag/            # NEW
    ├── ingestion/       # PDF parsing, chunking, extraction pipeline
    │   ├── parser.py        # Layout-aware PDF → hierarchical chunks
    │   ├── chunker.py       # Parent-child chunk strategy
    │   ├── extractor.py     # LLM-driven logic node extraction
    │   ├── linker.py        # Entity → SNOMED/LOINC/FHIR code mapping
    │   └── loader.py        # Chunk + LogicNode → Neo4j writer
    ├── graph/           # Neo4j schema, queries, connection
    │   ├── schema.py        # Node/edge type definitions (Pydantic)
    │   ├── connection.py    # Neo4j driver management
    │   ├── queries.py       # Cypher query builders per LogicNode type
    │   └── indexes.py       # Index/constraint creation
    ├── reasoning/       # The query engine
    │   ├── engine.py        # Deterministic graph traversal
    │   ├── fallback.py      # LLM fallback when no logic node matches
    │   └── types.py         # Query/response models
    ├── server/          # API layer
    │   ├── mcp_server.py    # MCP tools (clinical + structured query)
    │   ├── rest_api.py      # FastAPI REST endpoints
    │   ├── auth.py          # API key middleware
    │   └── app.py           # FastAPI app factory
    └── config.py        # Neo4j URI, API keys, model settings
```

## 3. Neo4j Graph Schema

### Node Types

**Concept** — Any clinical entity (drug, disease, lab test, procedure, symptom).

```
(:Concept {
  id: str,                  # canonical identifier
  name: str,                # human-readable name
  type: "drug" | "disease" | "lab" | "procedure" | "symptom",
  snomed_code: str | null,
  loinc_code: str | null,
  fhir_code: str | null,
  aliases: list[str]
})
```

**LogicNode** — A single clinical rule extracted from a guideline. Typed with a fixed schema per type.

```
(:LogicNode {
  id: str,                  # e.g. "ln_af_apixaban_renal_001"
  type: "dosing" | "contraindication" | "interaction" | "monitoring" | "treatment_selection" | "diagnostic_criteria",
  conditions: list[dict],   # [{"variable": "eGFR", "operator": "<", "threshold": 25, "unit": "mL/min"}]
  action: str,              # type-specific action value
  action_detail: str,       # human-readable explanation
  strength: "Strong/A" | "Moderate/B" | "Weak/C" | "Expert_Opinion",
  guideline_id: str,
  page: int
})
```

**EvidenceChunk** — Raw source text backing a LogicNode.

```
(:EvidenceChunk {
  id: str,                  # deterministic hash of guideline_id + page + position
  text: str,
  guideline_id: str,
  section: str,
  page_start: int,
  page_end: int,
  parent_chunk_id: str | null,
  embedding: list[float]    # for vector fallback search
})
```

**Guideline** — Source document metadata.

```
(:Guideline {
  id: str,
  title: str,
  doi: str,
  year: int,
  organization: str,
  total_pages: int
})
```

**PatientVariable** — Canonical variable definitions (vocabulary, not per-patient).

```
(:PatientVariable {
  id: str,                  # e.g. "eGFR"
  name: str,
  unit: str,
  loinc_code: str | null,
  type: "continuous" | "categorical" | "boolean"
})
```

### Edge Types

```
(Concept)-[:PARTICIPATES_IN {role: "intervention"|"target"|"modifier"}]->(LogicNode)
(LogicNode)-[:SOURCED_FROM]->(EvidenceChunk)
(LogicNode)-[:DEFINED_BY]->(Guideline)
(LogicNode)-[:EVALUATES]->(PatientVariable)
(LogicNode)-[:CONFLICTS_WITH {resolution: "newer"|"stronger"}]->(LogicNode)
(EvidenceChunk)-[:BELONGS_TO]->(Guideline)
(EvidenceChunk)-[:CHILD_OF]->(EvidenceChunk)
(Concept)-[:INTERACTS_WITH]->(Concept)
```

### LogicNode Type Schemas

| Type | Required Fields | Action Values |
|---|---|---|
| `dosing` | drug, dose, route, frequency, conditions | `initiate`, `dose_adjust`, `max_dose`, `contraindicated` |
| `contraindication` | intervention, conditions | `contraindicated`, `avoid`, `caution` |
| `interaction` | drug_a, drug_b, severity | `contraindicated`, `monitor`, `dose_adjust` |
| `monitoring` | intervention, lab/test, frequency | `monitor`, `recheck`, `discontinue_if` |
| `treatment_selection` | condition, options, criteria | `prefer`, `alternative`, `avoid` |
| `diagnostic_criteria` | condition, criteria_list, threshold | `diagnose`, `rule_out`, `further_testing` |

### Indexes

- Unique constraints: `Concept.id`, `LogicNode.id`, `EvidenceChunk.id`, `Guideline.id`
- Property indexes: `Concept.snomed_code`, `Concept.type`, `LogicNode.type`, `LogicNode.guideline_id`
- Full-text index: `EvidenceChunk.text`
- Vector index: `EvidenceChunk.embedding` (Neo4j 5.x native)

## 4. Ingestion Pipeline

Four-stage pipeline, run by admin/developer via CLI.

### Stage 1: PDF Parsing (`parser.py`)

**Tool:** Docling (preferred) or Marker as fallback.

Output models:
- `ParsedDocument` → `ParsedPage` → `ParsedSection`
- Preserves heading hierarchy, serializes tables as structured JSON
- Maintains page numbers, strips headers/footers/references

### Stage 2: Hierarchical Chunking (`chunker.py`)

Parent-child strategy:
- Parent: full section (e.g., "4.2 Anticoagulation in CKD")
- Child: individual paragraph or table (200-500 tokens)
- Tables kept atomic (never split)
- 50-token overlap between consecutive children
- Deterministic chunk IDs (hash of guideline_id + page + position)

### Stage 3: Extraction (`extractor.py`)

LLM-driven (Claude) with structured output:
1. Send child chunk + parent context to LLM with typed extraction prompt
2. LLM returns zero or more `LogicNode` candidates as structured JSON
3. Pydantic validation per LogicNode type
4. Entity linking via `linker.py` → SNOMED/LOINC codes

Validation gates:
- Schema validation (Pydantic)
- At least one Concept resolvable to SNOMED/LOINC
- Conditions use recognized PatientVariable names
- Duplicate detection across overlapping chunks

### Stage 4: Graph Loading (`loader.py`)

1. Create Guideline node
2. Create EvidenceChunk nodes (parent + children) with CHILD_OF and BELONGS_TO edges
3. Create/merge Concept nodes (dedup by SNOMED code)
4. Create LogicNode nodes with edges to Concepts, EvidenceChunks, Guideline
5. Create/merge PatientVariable nodes, link via EVALUATES
6. Generate embeddings for EvidenceChunk nodes, store in vector index
7. Detect conflicting LogicNode pairs, create CONFLICTS_WITH edges

**Idempotency:** Re-running on the same guideline replaces all nodes for that guideline_id (delete-then-recreate in a transaction).

### CLI

```bash
uv run python -m open_medicine.graphrag.ingest --pdf path/to/guideline.pdf --id <id> --doi "<doi>"
uv run python -m open_medicine.graphrag.ingest --url "https://..." --id <id> --doi "<doi>"
uv run python -m open_medicine.graphrag.ingest --id <id> --extract-only
uv run python -m open_medicine.graphrag.validate
```

## 5. Reasoning Engine

### Two-Tier Resolution

```
Agent Query → Parse patient variables → Graph Traversal (deterministic)
  ├── Found → Return LogicNode(s) + EvidenceChunk citation
  └── Not found → Vector search EvidenceChunks → Graph-enhanced retrieval → LLM synthesis + citations
```

### Deterministic Path (primary)

Input: `ClinicalQuery(intent, concepts, patient_vars)`

1. Resolve concepts to Concept nodes (by name, alias, or SNOMED code)
2. Find LogicNodes connected to those concepts with matching type
3. Evaluate conditions against patient_vars (in Python, not Cypher)
4. Rank: full match > partial match, stronger evidence > weaker, newer > older
5. Resolve CONFLICTS_WITH edges by strategy
6. Return matched LogicNodes with EvidenceChunk text as citation

### LLM Fallback Path

Triggered when deterministic path returns zero full matches:

1. Vector search on EvidenceChunk embeddings (top-10)
2. Graph walk: find parent chunks and sibling LogicNodes for context
3. LLM synthesis with constrained prompt (cite-only, no extrapolation)
4. Response tagged as `source: "llm_synthesis"` (vs `"graph_traversal"`)

### Response Model

```python
class GraphRAGResult(BaseModel):
    source: Literal["graph_traversal", "llm_synthesis"]
    matches: list[LogicNodeMatch]
    synthesis: str | None
    evidence: list[EvidenceCitation]
    confidence: Literal["high", "medium", "low"]
    missing_variables: list[str]
```

Wraps into `ClinicalResult` for MCP compatibility.

## 6. MCP Tools & REST API

### High-Level Clinical Tools

| Tool | Params |
|---|---|
| `check_drug_dosing` | `drug`, `patient_vars` |
| `check_contraindications` | `intervention`, `patient_vars` |
| `check_drug_interaction` | `drug_a`, `drug_b`, `patient_vars` (opt) |
| `check_monitoring_requirements` | `intervention`, `patient_vars` (opt) |
| `find_treatment_options` | `condition`, `patient_vars` |

### Structured Query Tool

```
query_clinical_graph(intent, concepts, patient_vars, guideline_filter, include_source_text)
```

### Source Retrieval Tool

```
fetch_evidence_chunk(chunk_id) → {text, guideline, section, page, doi}
```

### REST API

```
POST /v1/dosing
POST /v1/contraindications
POST /v1/interactions
POST /v1/monitoring
POST /v1/treatments
POST /v1/query
GET  /v1/evidence/{id}
GET  /v1/guidelines
GET  /health
```

Auth: `Authorization: Bearer <api_key>` on all endpoints except `/health`.
MCP Transport: SSE at `/mcp`.

### Entrypoints

```bash
uv run python -m open_medicine.graphrag.server.mcp_server    # stdio MCP
uv run python -m open_medicine.graphrag.server.app --host 0.0.0.0 --port 8000  # REST + MCP-over-SSE
```

## 7. Dependencies & Configuration

### Dependencies

```toml
[project.optional-dependencies]
graphrag = [
    "neo4j>=5.0.0",
    "docling>=2.0.0",
    "fastapi>=0.110.0",
    "uvicorn>=0.30.0",
    "scispacy>=0.5.0",
    "httpx>=0.27.0",
]
```

Installed via `uv sync --extra graphrag`.

### Environment Variables

```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=...
ANTHROPIC_API_KEY=...
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
GRAPHRAG_API_KEYS=key1,key2,key3
GRAPHRAG_RATE_LIMIT=100
GRAPHRAG_PORT=8000
```

### Local Development

```yaml
# docker-compose.yml
services:
  neo4j:
    image: neo4j:5-community
    ports: ["7687:7687", "7474:7474"]
    environment:
      NEO4J_AUTH: neo4j/openmedicine
      NEO4J_PLUGINS: '["apoc"]'
    volumes: [neo4j_data:/data]
volumes:
  neo4j_data:
```

### Railway Deployment

`Dockerfile.graphrag` with `uv sync --extra graphrag`. Neo4j via Aura (managed cloud).

## 8. Testing Strategy

### Unit Tests

- **Ingestion** (`tests/graphrag/test_ingestion.py`): parser output structure, chunk sizes/hierarchy, extraction validation, loader Cypher correctness
- **Schema** (`tests/graphrag/test_schema.py`): Pydantic model validation per LogicNode type
- **Reasoning** (`tests/graphrag/test_reasoning.py`): condition evaluation, ranking, conflict resolution, fallback trigger logic
- **API** (`tests/graphrag/test_api.py`): MCP tool input/output, REST auth/rate-limiting, response format

### Integration Tests

- **End-to-end** (`tests/graphrag/test_e2e.py`): requires Neo4j, ingest synthetic guideline, query via MCP tools. Skipped in CI unless `NEO4J_URI` set.
- **Extraction quality** (`tests/graphrag/test_extraction_quality.py`): golden set of 10-20 expected LogicNodes per guideline, precision/recall after ingestion.

### Test Fixtures

Synthetic mini-guideline with known rules, loaded directly into Neo4j (bypasses PDF parsing) for deterministic tests.

### CI

```bash
# Unit tests (no Neo4j)
uv run python -m pytest tests/graphrag/ -v --ignore=tests/graphrag/test_e2e.py

# Full suite (with Neo4j)
NEO4J_URI=bolt://localhost:7687 uv run python -m pytest tests/graphrag/ -v
```

## 9. Initial Guideline Corpus

| # | Guideline | Key Logic Density |
|---|---|---|
| 1 | ACC/AHA Atrial Fibrillation 2023 | Anticoagulation decision trees, renal dosing |
| 2 | KDIGO CKD 2024 | Lab thresholds (eGFR, albumin, K+), medication by stage |
| 3 | ATS/IDSA CAP 2019 | Antibiotic selection with comorbidity branching |
| 4 | ESC Heart Failure 2023 | Multi-drug titration, contraindication cascades |
| 5 | ACC/AHA Cholesterol/ASCVD 2018 | Statin intensity decision tree |

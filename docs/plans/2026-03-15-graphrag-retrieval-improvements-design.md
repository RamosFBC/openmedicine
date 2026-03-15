# GraphRAG Retrieval Improvements Design

**Date:** 2026-03-15
**Status:** Approved
**Scope:** ReasoningEngine v2 retrieval resilience

## Problem

The ReasoningEngine v2 uses intent-routed, one-hop semantic edge traversal. This covers
~60% of 2025/2026 GraphRAG best practices. Key gaps:

- **No multi-hop expansion** — querying a DrugClass misses member drug edges (and vice versa)
- **No vector fallback** — returns empty when graph traversal finds nothing, despite having 649 EvidenceChunks with source text
- **No actionable empty results** — agents get `confidence="low"` with no guidance on reformulation
- **No provenance transparency** — agents can't tell which retrieval strategy produced each result

## Approach: Layered Fallback Chain

Keep the current intent-routed engine as the fast path. Add layers that activate only when
the previous layer returns insufficient results. Deterministic first, fuzzy second.

```
ClinicalQuery
    │
    ├── Intent routing (unchanged)
    │
    ▼
┌─────────────────────────────┐
│  Layer 1: Direct Graph      │  One-hop semantic edges (current)
│  ~5ms, free                 │  INDICATED_FOR, CONTRAINDICATED_IN, etc.
└─────────┬───────────────────┘
          │ results < min_threshold?
          ▼
┌─────────────────────────────┐
│  Layer 2: Multi-Hop         │  DrugClass↔member + Disease↔stage
│  Expansion  ~10ms, free     │  Reuses Layer 1 queries with expanded IDs
└─────────┬───────────────────┘
          │ still 0 results?
          ▼
┌─────────────────────────────┐
│  Layer 3: Vector Fallback   │  Embed query → search EvidenceChunks
│  ~60ms, ~$0.0001            │  Traverse chunk→rec→entity
└─────────┬───────────────────┘
          │ still 0 results?
          ▼
┌─────────────────────────────┐
│  Layer 4: Empty + Hints     │  Fuzzy concept match
│  ~2ms, free                 │  Suggest alternative intents/concepts
└─────────────────────────────┘
```

## Layer Details

### Layer 1: Direct Graph (unchanged)

Current one-hop semantic edge traversal via `_INTENT_TO_QUERY` routing.
No changes. This remains the fast path for ~90% of queries.

### Layer 2: Multi-Hop Expansion

Activates when Layer 1 returns fewer than `min_results_threshold` results.

**DrugClass ↔ Member expansion:**
- Querying a DrugClass → also query INDICATED_FOR/CONTRAINDICATED_IN/MONITORED_BY on its member drugs
- Querying a Drug → also check parent DrugClass edges
- Uses existing `find_drug_class_members()` and `find_drug_class()` queries

**Disease hierarchy expansion:**
- Querying a disease subtype (HFrEF) → also traverse STAGE_OF to parent (Heart Failure)
- Querying a parent disease → also check subtypes

**Deduplication:** By `(entity_id, edge_type)` — Layer 1 results take priority.

**No new Cypher queries.** Reuses existing Layer 1 queries with different entry point IDs.

### Layer 3: Vector Fallback

Activates when Layers 1+2 return 0 results.

1. Embed query text `"{intent} {concept1} {concept2}"` via Voyage AI (`embed_query()`)
2. Run vector search over EvidenceChunk embeddings (existing index `evidence_embedding`)
3. Traverse from matched chunks to connected entities:

```cypher
CALL db.index.vector.queryNodes('evidence_embedding', $limit, $embedding)
YIELD node, score
MATCH (rec:Recommendation)-[:SOURCED_FROM]->(node)
MATCH (rec)-[:RECOMMENDS]->(entity)
WHERE rec.type = $rec_type
RETURN labels(entity)[0] AS entity_type, entity.id AS entity_id,
       entity.name AS entity_name, rec.strength AS strength,
       rec.evidence_quality AS evidence_quality, score
ORDER BY score DESC
```

**Graceful degradation:** If embeddings aren't loaded (no VOYAGE_API_KEY), Layer 3 returns
empty and the engine continues to Layer 4. No crash.

**No LLM synthesis.** Returns structured `SemanticMatch` results, not prose. The agent
handles synthesis.

### Layer 4: Empty Result with Hints

Deterministic, template-based hints (no LLM):

- **Concept not found:** `"Concept 'X' not in terminology. Similar: [fuzzy matches]"`
- **Unsupported intent:** `"Intent 'X' not routed. Try: treatment_selection, contraindication, dosing, monitoring, interaction"`
- **No edges:** `"'X' exists but has no INDICATED_FOR edges. Try intent='dosing' or check related drug class."`

Fuzzy matching via substring/prefix against terminology canonical names and aliases.

## Type Changes

### SemanticMatch — add source_layer

```python
source_layer: str = Field(
    default="direct",
    description="Which retrieval layer produced this: direct, expanded, vector"
)
```

### GraphRAGResult — add retrieval_layers_used and hints

```python
retrieval_layers_used: list[str] = Field(
    default_factory=list,
    description="Layers that contributed results: ['direct', 'expanded', 'vector']"
)
hints: list[str] = Field(
    default_factory=list,
    description="Reformulation suggestions when results are empty"
)
```

### ClinicalQuery — add min_results_threshold

```python
min_results_threshold: int = Field(
    default=1,
    description="Minimum results before triggering fallback layers"
)
```

### Sort order

Final results sorted by: source_layer priority (direct > expanded > vector),
then conditions_met, then strength rank.

## Ingestion Pipeline Change

### New CLI command: embed

```bash
uv run python -m open_medicine.graphrag.ingest_v2 embed
```

Fetches all EvidenceChunks without embeddings, calls Voyage AI in batches,
writes embeddings back to Neo4j.

### Pipeline placement: Phase 4.6

```
Phase 4:   Load into Neo4j
Phase 4.5: Generate test scenarios
Phase 4.6: Generate embeddings       ← NEW
Phase 5:   Validate
```

Cost: 649 chunks × ~100 tokens = ~65K tokens. < $0.01 per ingestion at Voyage-3-lite pricing.

If VOYAGE_API_KEY is missing, skip with a warning. Layer 3 degrades gracefully.

## Testing Strategy

### Unit tests (no Neo4j)

- Layer 2 expansion logic: drug→class and class→members resolution
- Layer 4 hints: fuzzy matching, unsupported intent suggestions
- Sort order: direct > expanded > vector ordering
- Deduplication: same entity from two layers keeps Layer 1 version
- Type changes: new fields have correct defaults

### Integration tests (Neo4j required)

- Fallback chain end-to-end: valid disease → Layer 1; DrugClass with no direct edges → Layer 2; nonsense query → Layer 4
- Vector fallback: query that misses Layers 1+2 but matches evidence text → Layer 3

### Scenario tests

- Expansion scenarios: DrugClass queries returning member drug results
- Negative scenarios: queries that should return hints, not false positives

## Not Included (YAGNI)

- **Community detection / global search** — not needed for point-of-care agent queries
- **Query rewriting / NLU** — the LLM agent already structures queries
- **Agentic self-correcting loop** — the outer agent handles retries
- **RRF re-ranking** — layer ordering is sufficient for clinical auditability

## Files Modified

- `src/open_medicine/graphrag/reasoning/engine_v2.py` — fallback chain, expansion, vector integration
- `src/open_medicine/graphrag/reasoning/types_v2.py` — new fields
- `src/open_medicine/graphrag/graph/queries_v2.py` — one new vector+entity query
- `src/open_medicine/graphrag/ingest_v2.py` — `embed` CLI command
- `.claude/commands/ingest-guideline.md` — Phase 4.6
- `tests/graphrag/test_engine_v2.py` — new test file

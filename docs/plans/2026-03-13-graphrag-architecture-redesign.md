# GraphRAG Architecture Redesign

**Date:** 2026-03-13
**Status:** Approved
**Context:** After implementing Phase 1-3 of the original plan, an architecture audit identified 8 gaps between the design doc and implementation. This redesign addresses all of them.

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Scope | All 8 gaps fixed | Full design-doc compliance |
| Conditions modeling | JSON property + EVALUATES edges | Queryability via edges, simple evaluation in Python |
| Embedding provider | Anthropic Voyage (via anthropic SDK) | Single-vendor stack, already a dependency |
| Retry strategy | Exponential backoff + dead letter queue | Ingestion is expensive, can't lose chunks silently |
| Approach | Refactor by layer | Foundation modules (schema, parser, chunker, linker, types) are solid; fix connection, loader, engine, fallback |

## Gap Analysis

### Critical (system won't work)

1. **Missing SOURCED_FROM edge** — Loader never creates `(LogicNode)-[:SOURCED_FROM]->(EvidenceChunk)`. Reasoning engine queries it. Dead query.
2. **Missing EVALUATES edge** — `(LogicNode)-[:EVALUATES]->(PatientVariable)` never created. No PatientVariable nodes at all.
3. **No embedding generation** — `EvidenceChunk.embedding` never populated. Fallback uses BM25 fulltext, not vector similarity.

### Architectural (wrong patterns)

4. **No `queries.py`** — Cypher hardcoded inline across files instead of centralized builders.
5. **Raw `session.run()`** — Should use `session.execute_read/write(tx_fn)` for cluster routing and managed transaction retry.
6. **No deduplication** — Same LogicNode returned multiple times if connected to multiple EvidenceChunks.
7. **No CONFLICTS_WITH** — Cross-guideline conflict detection never implemented.
8. **No INTERACTS_WITH** — Drug-drug interaction edges never created.

## Section 1: Graph Connection

Replace raw `session.run()` with proper managed transactions:

```python
class GraphConnection:
    def execute_read(self, query, params) -> list[dict]:
        with self._driver.session() as session:
            return session.execute_read(lambda tx: tx.run(query, params).data())

    def execute_write(self, query, params) -> list[dict]:
        with self._driver.session() as session:
            return session.execute_write(lambda tx: tx.run(query, params).data())

    def execute_write_tx(self, queries) -> None:
        def _work(tx):
            for query, params in queries:
                tx.run(query, params)
        with self._driver.session() as session:
            session.execute_write(_work)
```

Benefits: automatic retry on transient errors (leader elections), proper read/write routing in clusters (Neo4j Aura).

## Section 2: Centralized Cypher Queries

New file `graph/queries.py` with two classes:

**LoaderQueries** — Cypher builders for ingestion:
- `delete_guideline`, `create_guideline`, `create_evidence_chunk`
- `create_logic_node`, `create_concept`, `create_patient_variable`
- Edge builders: `create_sourced_from`, `create_evaluates`, `create_belongs_to`, `create_child_of`, `create_defined_by`, `create_participates_in`, `create_conflicts_with`, `create_interacts_with`

**ReasoningQueries** — Cypher builders for query-time traversal:
- `find_logic_nodes` (with optional guideline filter)
- `vector_search` (Neo4j native vector index)
- `graph_enhanced_context` (parent chunks + sibling LogicNodes)
- `get_evidence_chunk`, `list_guidelines`

Each method returns `(cypher_string, params_dict)`. Cypher is testable in isolation.

## Section 3: Loader Redesign

### New edges created

| Edge | From → To | When Created |
|------|-----------|-------------|
| `SOURCED_FROM` | LogicNode → EvidenceChunk | For each extraction, link to source chunk |
| `EVALUATES` | LogicNode → PatientVariable | For each condition variable in the LogicNode |
| `CONFLICTS_WITH` | LogicNode → LogicNode | Post-load: same concept + same type + contradictory actions |
| `INTERACTS_WITH` | Concept → Concept | When LogicNode type=interaction has two drug concepts |

### PatientVariable creation

Extract variable names from LogicNode conditions, create/merge PatientVariable nodes. Linker extended with `_VAR_MAP` mapping variable names to canonical forms with LOINC codes.

### Embedding generation

New `ingestion/embeddings.py` — Voyage embedding client via Anthropic SDK. Called after chunk creation, vectors stored on EvidenceChunk nodes. Config defaults: `voyage-3-lite`, 1024 dimensions.

### Dead letter queue

New `ingestion/dead_letter.py`:
- `FailedExtraction` dataclass (guideline_id, chunk_id, chunk_text, error, timestamp)
- `DeadLetterQueue` class — appends JSON lines to `failed_extractions.jsonl`, loadable for retry

### Retry wrapper

`_call_llm_with_retry(prompt, max_retries=3, base_delay=1.0)` — exponential backoff, catches `RateLimitError` and `APIConnectionError`. On final failure, writes to dead letter queue instead of silently dropping.

### Conflict detection (post-load pass)

```
For each pair of LogicNodes sharing a Concept and type:
  If actions contradict (e.g., "initiate" vs "contraindicated"):
    Compare guideline year → newer wins (resolution="newer")
    If same year, compare strength → stronger wins (resolution="stronger")
    Create CONFLICTS_WITH edge with resolution metadata
```

## Section 4: Reasoning Engine Redesign

### Deduplication

Group rows by `ln_id`, merge evidence into lists per match. Prevents same LogicNode appearing multiple times.

### CONFLICTS_WITH resolution

After collecting matches, check for CONFLICTS_WITH edges between matched pairs. Mark the losing node and annotate `action_detail`.

### Fallback: real vector search

Replace BM25 fulltext with Neo4j 5.x native vector search:
```cypher
CALL db.index.vector.queryNodes('evidence_embedding', $k, $query_vector)
YIELD node, score
```

Query text embedded at query time using same Voyage model. New `_embed_query(text) -> list[float]` method on FallbackEngine.

### Graph-enhanced retrieval

After vector search returns top-K chunks, walk graph for parent chunks and sibling LogicNodes:
```cypher
MATCH (ec:EvidenceChunk {id: $id})
OPTIONAL MATCH (ec)-[:CHILD_OF]->(parent:EvidenceChunk)
OPTIONAL MATCH (ln:LogicNode)-[:SOURCED_FROM]->(ec)
RETURN parent.text, collect(ln) as related_nodes
```

## Section 5: Updated Indexes

Add to `indexes.py`:
- Vector index: `evidence_embedding` (1024 dims, cosine similarity)
- Property index: `PatientVariable.loinc_code`

## Section 6: File Change Map

| File | Action | What Changes |
|------|--------|-------------|
| `graph/connection.py` | Modify | Managed transactions |
| `graph/queries.py` | Create | All Cypher builders |
| `graph/indexes.py` | Modify | Vector + PatientVariable indexes |
| `ingestion/extractor.py` | Modify | Retry + dead letter queue |
| `ingestion/linker.py` | Modify | Add `_VAR_MAP` |
| `ingestion/loader.py` | Modify | All edges, PatientVariable nodes, embeddings |
| `ingestion/embeddings.py` | Create | Voyage embedding client |
| `ingestion/dead_letter.py` | Create | Dead letter queue |
| `reasoning/engine.py` | Modify | queries.py, dedup, conflicts |
| `reasoning/fallback.py` | Modify | Vector search, graph-enhanced retrieval |
| `config.py` | Modify | Voyage defaults |
| `tests/graphrag/test_*.py` | Modify | Updated tests |
| `tests/graphrag/test_queries.py` | Create | Cypher builder tests |
| `tests/graphrag/test_embeddings.py` | Create | Embedding client tests |
| `tests/graphrag/test_dead_letter.py` | Create | Dead letter queue tests |

**Untouched:** `schema.py`, `parser.py`, `chunker.py`, `types.py`, all `__init__.py` files.

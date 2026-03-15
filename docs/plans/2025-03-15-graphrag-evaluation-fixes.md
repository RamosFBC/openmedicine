# GraphRAG Evaluation Fixes — Design & Implementation Plan

**Date**: 2025-03-15
**Context**: Clinical case evaluation (`scripts/evaluate_clinical_case.py`) revealed 5 limitations in the GraphRAG retrieval pipeline. This plan fixes all 5 across both the query engine and the ingestion pipeline.

## Issues

| # | Issue | Root Cause | Files |
|---|-------|-----------|-------|
| L1 | INTERACTS_WITH edges silently dropped for DrugClass pairs | `create_interacts_with()` Cypher hardcodes `:Drug` on both sides | `queries_v2.py`, `loader_v2.py` |
| L2 | `diagnostic_criteria` intent returns empty | No dedicated query method; `_query_generic` requires 3 mandatory edges | `engine_v2.py`, `queries_v2.py` |
| L3 | Patient variable case mismatch (`egfr` ≠ `eGFR`) | `_evaluate_condition()` uses exact string match | `engine_v2.py` |
| L4 | Missing variables conflated with failed conditions | `conditions_met=False` when variables missing, even if no condition actually failed | `engine_v2.py` |
| L5 | `_query_interactions()` only tries `"drug"` entity type | Never tries `link_entity(_, "drug_class")` | `engine_v2.py` |

## Implementation Tasks

### Task 1: Fix interaction edge creation in loader (L1)

**TDD: Write failing tests first.**

Tests in `tests/graphrag/test_queries_v2.py`:
- `test_create_interacts_with_accepts_labels` — verify Cypher uses dynamic labels
- `test_create_interacts_with_drug_class_pair` — verify DrugClass↔DrugClass edge creation

Tests in `tests/graphrag/test_linker_v2.py` or `tests/graphrag/test_loader_v2.py`:
- `test_interaction_edge_uses_entity_labels` — verify `_create_interacts_with` passes labels

**Implementation:**

1. `queries_v2.py` — `LoaderQueries.create_interacts_with()`:
   - Add `source_label: str = "Drug"` and `target_label: str = "Drug"` params
   - Change Cypher: `MATCH (a:{source_label} {id: $aid}), (b:{target_label} {id: $bid})`

2. `loader_v2.py` — `_create_interacts_with()`:
   - Pass `drug_a.node_label` and `drug_b.node_label` to the query builder

**Verify**: `uv run python -m pytest tests/graphrag/test_queries_v2.py tests/graphrag/test_loader_v2.py -v`

### Task 2: Fix interaction query and engine routing (L5)

**TDD: Write failing tests first.**

Tests in `tests/graphrag/test_queries_v2.py`:
- `test_find_interactions_accepts_entity_label` — verify Cypher uses dynamic label
- `test_find_interactions_matches_drug_and_drugclass` — verify OTHER side matches both types

Tests in `tests/graphrag/test_engine_v2.py`:
- `test_interaction_tries_drug_class_fallback` — mock link_entity to return None for "drug", valid for "drug_class"
- `test_interaction_returns_drug_class_results` — verify results include DrugClass interactions

**Implementation:**

1. `queries_v2.py` — `ReasoningQueries.find_interactions()`:
   - Add `entity_label: str = "Drug"` param
   - Change Cypher: `MATCH (d:{entity_label} {id: $did})-[r:INTERACTS_WITH]-(other)`
   - Add `WHERE other:Drug OR other:DrugClass` to match both types
   - Return `labels(other)[0] AS entity_type` for the matched node

2. `engine_v2.py` — `_query_interactions()`:
   - Try `link_entity(concept, "drug")` first
   - If None, try `link_entity(concept, "drug_class")`
   - Pass `entity.node_label` to `find_interactions()`

**Verify**: `uv run python -m pytest tests/graphrag/test_engine_v2.py tests/graphrag/test_queries_v2.py -v`

### Task 3: Add diagnostic_criteria query method (L2)

**TDD: Write failing tests first.**

Tests in `tests/graphrag/test_queries_v2.py`:
- `test_find_diagnostic_criteria_cypher` — verify Cypher pattern for DIAGNOSED_BY

Tests in `tests/graphrag/test_engine_v2.py`:
- `test_diagnostic_criteria_routed_to_dedicated_method` — verify intent routes correctly
- `test_diagnostic_criteria_returns_labs_and_procedures` — mock graph returns Lab/Procedure nodes
- `test_diagnostic_criteria_falls_back_to_generic` — when no DIAGNOSED_BY edges, tries generic

**Implementation:**

1. `queries_v2.py` — Add `ReasoningQueries.find_diagnostic_criteria()`:
   ```
   MATCH (dis:Disease {id: $did})-[:DIAGNOSED_BY]->(tgt)
   WHERE tgt:Lab OR tgt:Procedure
   RETURN labels(tgt)[0] AS entity_type, tgt.id AS entity_id,
          tgt.name AS entity_name
   ```

2. `engine_v2.py`:
   - Add `"diagnostic_criteria": "_query_diagnostic_criteria"` to `_INTENT_TO_QUERY`
   - New method `_query_diagnostic_criteria()`:
     - Link disease concepts
     - Query DIAGNOSED_BY edges (Layer 1)
     - If insufficient results, fall back to `_query_generic()` for Layer 2 Recommendation data
     - Return combined results

**Verify**: `uv run python -m pytest tests/graphrag/test_engine_v2.py tests/graphrag/test_queries_v2.py -v`

### Task 4: Fix patient variable case normalization (L3)

**TDD: Write failing tests first.**

Tests in `tests/graphrag/test_engine_v2.py`:
- `test_condition_evaluation_case_insensitive` — `egfr` matches condition with `eGFR`
- `test_condition_evaluation_mixed_case` — `LVEF` matches `lvef` and vice versa

**Implementation:**

In `engine_v2.py` — `_evaluate_match_conditions()`:
- Build normalized dict: `norm_vars = {k.lower(): v for k, v in patient_vars.items()}`
- Pass `norm_vars` to `_evaluate_condition()` instead of `patient_vars`

In `_evaluate_condition()`:
- Look up `var.lower()` in the (already lowercased) dict

**Verify**: `uv run python -m pytest tests/graphrag/test_engine_v2.py -v`

### Task 5: Separate missing variables from failed conditions (L4)

**TDD: Write failing tests first.**

Tests in `tests/graphrag/test_engine_v2.py`:
- `test_missing_vars_only_does_not_fail_conditions` — missing vars but no failed condition → `conditions_met=True`
- `test_failed_condition_sets_conditions_met_false` — explicit failure → `conditions_met=False`
- `test_confidence_high_when_only_missing_vars` — confidence="high" when matches exist with only missing (not failed) conditions

**Implementation:**

In `engine_v2.py` — `_evaluate_match_conditions()`:
- Track `any_failed = False` separately from missing
- `conditions_met = not any_failed` (True even if some vars missing)
- Missing variables still populated for transparency

In `_build_result()`:
- `full_matches = [m for m in matches if m.conditions_met]` — now includes matches with missing vars but no failures
- Confidence logic unchanged (high if full_matches, medium if matches but none met, low if empty)

**Verify**: `uv run python -m pytest tests/graphrag/test_engine_v2.py -v`

### Task 6: Update evaluation script expectations

Update `scripts/evaluate_clinical_case.py`:
- Q6 (interactions): increase `min_results` to 1, add `must_find` for ACEi-related interactions
- Q8 (diagnostic_criteria): add `must_find` for LVEF-related diagnostic labs
- Q1/Q4: expect `confidence="high"` after L3+L4 fixes

**Verify**: Script runs but may fail until graph is re-ingested (Task 7).

### Task 7: Re-ingest guideline to create missing edges

Run the migrate command to reload the HF guideline with the fixed loader:
```bash
uv run python -m open_medicine.graphrag.ingest_v2 migrate \
  --jsonl data/cache/consolidated.jsonl \
  --file data/guidelines/aha_acc_hf_2022.md \
  --id aha_acc_hf_2022 \
  --doi "10.1161/CIR.0000000000001063" \
  --title "2022 AHA/ACC/HFSA Guideline for the Management of Heart Failure" \
  --year 2022 \
  --org "AHA/ACC/HFSA"
```

Then validate:
```bash
uv run python -m open_medicine.graphrag.ingest_v2 validate
```

Check that INTERACTS_WITH edge count > 0 and DIAGNOSED_BY edges exist.

### Task 8: Run full evaluation and verify improvements

```bash
uv run python scripts/evaluate_clinical_case.py
```

Expected improvements:
- Q1/Q4: confidence="high" (L3+L4 fix)
- Q6: interactions found (L1+L5 fix)
- Q8: diagnostic criteria results (L2 fix)

### Task 9: Run full test suite

```bash
uv run python -m pytest -v
```

Ensure no regressions across all 2873+ tests.

## Batch Plan

- **Batch 1** (Tasks 1-3): Interaction pipeline + diagnostic_criteria — the two structural fixes
- **Batch 2** (Tasks 4-6): Condition evaluation + evaluation script — the condition logic fixes
- **Batch 3** (Tasks 7-9): Re-ingest + end-to-end validation

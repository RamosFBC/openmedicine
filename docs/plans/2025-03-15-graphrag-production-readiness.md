# GraphRAG Production Readiness Fix Plan

**Date**: 2025-03-15
**Status**: Approved for implementation
**Root cause**: Clinical decision support evaluation (Maria Santos case) exposed 7 categories of failure that would make the system unsafe for clinical use.

## Problem Summary

The graph has good data (944 nodes, 4367 edges) but the engine can't reach it. Three architectural gaps cause silent failures:

1. **No class-level inheritance** — drug queries miss class-level edges
2. **Terminology resolution gaps** — common clinical terms don't resolve
3. **Missing edge types** — DIAGNOSED_BY exists in schema but not in graph

---

## Fix 1: Class-Level Edge Inheritance in Engine

**Problem**: Querying "Lisinopril monitoring" returns 0 results. The MONITORED_BY edges are on ACE Inhibitor (the drug class), not on Lisinopril (the drug). Same pattern affects interactions, contraindications, and dosing.

**Impact**: Physicians get no monitoring/interaction guidance for specific drugs they prescribe.

**Files**: `src/open_medicine/graphrag/reasoning/engine_v2.py`

**Implementation**:
- In each intent handler (`_query_monitoring`, `_query_interactions`, `_query_contraindications`, `_query_dosing`):
  1. Query the drug node directly (existing behavior)
  2. If zero results, look up the drug's class via `MEMBER_OF` edge in the graph
  3. Re-query using the class node ID
- Add a helper method `_get_parent_classes(entity_id: str) -> list[tuple[str, str]]` that runs:
  ```cypher
  MATCH (d {id: $id})-[:MEMBER_OF]->(c) RETURN c.id, c.name, labels(c)[0]
  ```
- Use existing `_is_known_entity()` pattern — try drug first, fall back to class

**Tests**:
- `test_monitoring_inherits_from_class`: Query "Lisinopril" monitoring, expect Potassium/Creatinine/eGFR from ACE Inhibitor class
- `test_interaction_inherits_from_class`: Query "Spironolactone" interactions, expect MRA-level interactions
- `test_direct_match_skips_inheritance`: Query "Spironolactone" monitoring (has direct edges), verify no class lookup

**Verification**: Run `scripts/clinical_decision_support.py` — Steps 3 and 5 should return results for Spironolactone interactions and Lisinopril monitoring.

---

## Fix 2: Terminology Expansion

**Problem**: "NSAIDs", "Calcium Channel Blockers", "beta-blockers" fail entity resolution. The terminology JSON files don't include these common clinical aliases.

**Impact**: Can't warn about NSAIDs in HF (Class III: Harm) or check CCB contraindications.

**Files**: `src/open_medicine/graphrag/terminology/drug_classes.json`, `src/open_medicine/graphrag/terminology/drugs.json`

**Implementation**:
- Add to `drug_classes.json`:
  - `"NSAIDs"` entry with aliases `["NSAID", "Nsaid", "Non-Steroidal Anti-Inflammatory Drug", "non-steroidal anti-inflammatory"]`
  - `"Calcium Channel Blocker"` parent entry with aliases `["CCB", "CCBs", "Calcium Channel Blockers", "calcium channel blocker"]`
- Ensure existing entries have common abbreviation aliases:
  - Beta Blocker: add `"BB"`, `"beta-blockers"`, `"β-blocker"`
  - ACE Inhibitor: add `"ACEi"`, `"ACE inhibitors"` (verify existing)
  - ARNi: add `"ARNI"`, `"arni"`, `"sacubitril-valsartan"`

**Also**: Verify that the graph node names match the terminology canonical names. Currently graph has "Nsaid" but terminology would resolve "NSAIDs" → we need both sides to agree.

**Tests**:
- `test_nsaid_resolves`: `link_entity("NSAIDs", "drug_class")` returns known entity
- `test_ccb_resolves`: `link_entity("Calcium Channel Blockers", "drug_class")` returns known entity
- `test_common_abbreviations`: Test ACEi, ARNi, BB, CCB, MRA, SGLT2i all resolve

**Verification**: Run `scripts/clinical_decision_support.py` — Step 2 should return contraindication data for CCBs and NSAIDs.

---

## Fix 3: Variable Name Alias Resolution

**Problem**: Graph stores conditions with `HF_type`, patient vars use `heart_failure_type`. Case normalization catches `LVEF` vs `lvef` but not semantic aliases.

**Impact**: Condition evaluation reports variables as "missing" when the data IS provided under a different name. This causes false "CONDITIONS NOT MET" flags.

**Files**: `src/open_medicine/graphrag/reasoning/engine_v2.py`

**Implementation**:
- Add a `_VARIABLE_ALIASES` dict mapping common alternative names to canonical forms:
  ```python
  _VARIABLE_ALIASES = {
      "heart_failure_type": "hf_type",
      "ejection_fraction": "lvef",
      "ef": "lvef",
      "gfr": "egfr",
      "estimated_gfr": "egfr",
      "k": "potassium",
      "k+": "potassium",
      "na": "sodium",
      "na+": "sodium",
      "sbp": "systolic_bp",
      "dbp": "diastolic_bp",
      "hr": "heart_rate",
      "bmi": "body_mass_index",
  }
  ```
- In `_evaluate_match_conditions()`, normalize BOTH the patient var keys AND the condition variable names through the alias map before comparison.

**Tests**:
- `test_variable_alias_heart_failure_type`: Patient vars with `heart_failure_type` match condition `HF_type`
- `test_variable_alias_ef`: Patient vars with `ejection_fraction` match condition `LVEF`
- `test_canonical_still_works`: Patient vars with `lvef` still match condition `LVEF`

**Verification**: Run evaluation — treatments requiring `HF_type` should show as "met" not "missing" when `heart_failure_type` is provided.

---

## Fix 4: DIAGNOSED_BY Edge Creation in Loader

**Problem**: Zero DIAGNOSED_BY edges in graph despite the schema defining the type and the extractor potentially producing diagnostic_criteria relationships.

**Impact**: The diagnostic_criteria intent returns zero results, falling back to generic query.

**Files**: `src/open_medicine/graphrag/ingestion/loader_v2.py`

**Implementation**:
- Check if the extractor produces `DIAGNOSED_BY` relationships in the JSONL output
  - If yes: the loader is dropping them — find and fix the filter
  - If no: the extractor prompt doesn't ask for diagnostic criteria relationships — update the extraction prompt
- In loader, add `_create_diagnosed_by()` handler analogous to existing `_create_monitored_by()`
- Map extracted diagnostic relationships to DIAGNOSED_BY edges with props (sensitivity, specificity, when_to_order)

**Tests**:
- `test_loader_creates_diagnosed_by`: Mock extraction with DIAGNOSED_BY relationship, verify Cypher generated
- Integration: After re-ingestion, verify `MATCH ()-[r:DIAGNOSED_BY]->() RETURN count(r)` > 0

**Verification**: Run `scripts/clinical_decision_support.py` — Step 6 should return diagnostic criteria for Heart Failure.

---

## Fix 5: Post-Ingestion Validation

**Problem**: No automated check after loading data. Gaps like missing edge types go undetected until a clinical query fails silently.

**Files**: New file `src/open_medicine/graphrag/ingestion/validator.py`

**Implementation**:
- Create a `validate_graph()` function that checks:
  1. **Edge type coverage**: every semantic edge type in `SEMANTIC_EDGE_TYPES` has at least 1 edge
  2. **Node label coverage**: every label in `CLINICAL_LABELS` has at least 1 node
  3. **Orphan check**: no nodes with zero edges (except EvidenceChunk which may be vector-only)
  4. **Terminology match**: sample 10 drug/disease nodes, verify they resolve via `link_entity()`
  5. **Interaction density**: warn if INTERACTS_WITH < 10 edges
  6. **Monitoring density**: warn if MONITORED_BY < 10 edges
- Run automatically at end of `loader_v2.py` load process
- Print PASS/WARN/FAIL summary

**Tests**:
- `test_validator_catches_missing_edge_type`: Mock graph missing DIAGNOSED_BY, verify FAIL
- `test_validator_passes_complete_graph`: Mock graph with all edge types, verify PASS

---

## Fix 6: Engine Hint Improvement

**Problem**: When entity resolution fails, hints say "Concept 'Spironolactone' not found in graph. Similar: Spironolactone (drug)" — it found the similar name but still returned 0 results. The hint is misleading.

**Files**: `src/open_medicine/graphrag/reasoning/engine_v2.py`

**Implementation**:
- When fuzzy match finds a similar concept, AUTO-RETRY the query with the matched concept instead of just hinting
- Only generate a hint if the retry also returns 0 results
- This handles case-sensitivity, minor spelling variations, and plural/singular differences

**Tests**:
- `test_fuzzy_auto_retry`: Query "spironolactone" (lowercase), verify it auto-retries with "Spironolactone" and returns results
- `test_fuzzy_no_infinite_loop`: Query with no match, verify hint generated without retry loop

---

## Implementation Order

| Priority | Fix | Effort | Safety Impact |
|----------|-----|--------|---------------|
| P0 | Fix 1: Class inheritance | Medium | Critical — unblocks monitoring + interaction queries for all drugs |
| P0 | Fix 2: Terminology expansion | Small | Critical — unblocks NSAIDs/CCBs contraindication warnings |
| P0 | Fix 3: Variable aliases | Small | High — fixes false "CONDITIONS NOT MET" flags |
| P1 | Fix 4: DIAGNOSED_BY edges | Medium | High — enables diagnostic criteria intent |
| P1 | Fix 6: Fuzzy auto-retry | Small | Medium — handles entity resolution edge cases |
| P2 | Fix 5: Post-ingestion validation | Medium | Preventive — catches future gaps automatically |

**P0 fixes first** — these are the ones that cause silent clinical safety failures.

## Verification

After all fixes, run both evaluation scripts:
```bash
set -a && source .env && set +a
export SSL_CERT_FILE=$(uv run python -c "import certifi; print(certifi.where())")
uv run python scripts/evaluate_clinical_case.py      # Must be 8/8 PASS
uv run python scripts/clinical_decision_support.py    # Must be 7/7 DATA AVAILABLE
```

Success criteria:
- `evaluate_clinical_case.py`: 8/8 PASS (maintained)
- `clinical_decision_support.py`: 7/7 decision points return graph data (currently 5/7)
- Spironolactone interactions: >0 results
- Lisinopril monitoring: >0 results (via class inheritance)
- NSAIDs contraindication: >0 results
- Heart Failure diagnostic criteria: >0 results
- No false "CONDITIONS NOT MET" for treatments patient qualifies for

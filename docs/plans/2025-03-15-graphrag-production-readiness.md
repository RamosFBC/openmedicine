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

## Fix 7: Incremental Graph Updates (Patch Mode)

**Problem**: Every improvement requires a full `migrate` (wipe + reload). This is destructive, slow, and loses any manual corrections or edges added outside the extraction pipeline. As the graph grows with multiple guidelines, wiping everything to fix one guideline's edges is unacceptable.

**Current behavior**:
- `migrate` = `MATCH (n) DETACH DELETE n` + full reload — nuclear option
- `load` = `delete_guideline(id)` + reload that guideline — per-guideline idempotent, but still deletes ALL of that guideline's edges before recreating
- No way to add a single edge, patch a node property, or add a new relationship type without re-running the entire extraction+link+load pipeline

**What we need**: Three levels of incremental update:

### Level 1: Patch Operations (CLI commands)

Add individual nodes, edges, or properties without touching existing data.

**Files**: `src/open_medicine/graphrag/ingest_v2.py`, `src/open_medicine/graphrag/graph/queries_v2.py`

**New CLI commands**:
```bash
# Add a single edge between existing nodes
ingest_v2 add-edge --source "rxnorm:9997" --target "loinc:2823-3" \
  --type MONITORED_BY --props '{"frequency": "weekly"}'

# Add a node
ingest_v2 add-node --label Drug --id "rxnorm:12345" --name "NewDrug" \
  --props '{"rxnorm_code": "12345"}'

# Patch node properties (MERGE + SET, not destructive)
ingest_v2 patch-node --id "rxnorm:9997" --set '{"aliases": ["Aldactone", "spironolactone", "MRA"]}'

# Add edges from a JSONL patch file (batch)
ingest_v2 apply-patch --file patches/2025-03-15-add-monitoring-edges.jsonl
```

**Implementation**:
- Add `PatchQueries` static class with:
  ```python
  @staticmethod
  def add_edge(source_id: str, source_label: str, target_id: str, target_label: str,
               edge_type: str, props: dict) -> CypherStatement:
      return (
          f"MATCH (a:{source_label} {{id: $sid}}), (b:{target_label} {{id: $tid}}) "
          f"MERGE (a)-[r:{edge_type}]->(b) "
          "SET r += $props",
          {"sid": source_id, "tid": target_id, "props": props},
      )

  @staticmethod
  def patch_node(node_id: str, label: str, props: dict) -> CypherStatement:
      return (
          f"MATCH (n:{label} {{id: $id}}) SET n += $props",
          {"id": node_id, "props": props},
      )
  ```
- Patch file format (JSONL):
  ```json
  {"op": "add_edge", "source": "rxnorm:9997", "source_label": "Drug", "target": "loinc:2823-3", "target_label": "Lab", "edge_type": "MONITORED_BY", "props": {"frequency": "weekly"}}
  {"op": "add_node", "label": "DrugClass", "id": "atc:M01A", "name": "NSAIDs", "props": {"atc_code": "M01A", "aliases": ["NSAID", "non-steroidal anti-inflammatory"]}}
  {"op": "patch_node", "id": "drug_class:nsaid", "label": "DrugClass", "props": {"atc_code": "M01A"}}
  ```
- Validate: each op checks that referenced nodes exist before creating edges. Fail loudly if source/target missing.

### Level 2: Guideline-Scoped Reload (existing, improved)

The current `load` command already does per-guideline idempotent reload (delete_guideline + recreate). This is correct for re-ingesting a guideline after improving the extraction pipeline.

**Improvement needed**: Change `delete_guideline()` to preserve shared clinical nodes (Drug, Disease, Lab, etc.) — only delete Recommendation, EvidenceChunk, and guideline-scoped edges. Currently it deletes recommendations scoped by `guideline_id` which is correct, but the clinical nodes created by one guideline may be reused by another. This already works because nodes use MERGE, but we should verify edge preservation.

**Add a `--dry-run` flag** to `load` that shows what would be deleted/created without executing:
```bash
ingest_v2 load --jsonl ... --file ... --id aha_hf_2022 --dry-run
# Output: Would delete 537 Recommendations, 200 EvidenceChunks
#         Would create 537 Recommendations, 200 EvidenceChunks, 4367 edges
#         Would preserve: 150 Drug nodes, 50 Disease nodes (shared)
```

### Level 3: Diff-Based Update

For the case where we improve the extraction pipeline and want to re-ingest without losing manual patches.

**Files**: New file `src/open_medicine/graphrag/ingestion/differ.py`

**Implementation**:
- Before deleting, snapshot current graph state for the guideline:
  ```python
  def snapshot_guideline(conn, guideline_id) -> GuidelineSnapshot:
      """Capture current nodes + edges scoped to a guideline."""
      nodes = conn.execute_read(
          "MATCH (rec:Recommendation {guideline_id: $gid})-[*1..2]-(n) "
          "RETURN DISTINCT n.id, labels(n), properties(n)", {"gid": guideline_id}
      )
      edges = conn.execute_read(
          "MATCH (rec:Recommendation {guideline_id: $gid})-[*1..2]-(a)-[r]-(b) "
          "RETURN a.id, type(r), b.id, properties(r)", {"gid": guideline_id}
      )
      return GuidelineSnapshot(nodes=nodes, edges=edges)
  ```
- After reload, diff against snapshot:
  ```python
  def diff_snapshots(before: GuidelineSnapshot, after: GuidelineSnapshot) -> GraphDiff:
      """Find edges/nodes that were in before but not in after (lost patches)."""
      lost_edges = before.edges - after.edges
      new_edges = after.edges - before.edges
      return GraphDiff(lost=lost_edges, added=new_edges)
  ```
- Report lost edges so the user can decide whether to re-apply patches:
  ```
  Reload complete. Diff:
    +120 new edges (from improved extraction)
    -3 edges lost (manual patches):
      Drug:rxnorm:9997 --MONITORED_BY--> Lab:loinc:6298-4 (manual)
      Drug:rxnorm:9997 --MONITORED_BY--> Lab:loinc:2823-3 (manual)
      DrugClass:nsaid --INTERACTS_WITH--> DrugClass:loop_diuretic (manual)
    Re-apply lost patches? [y/n]
  ```

### Patch Tracking

Add a `_source` property to edges created via patch operations:
```cypher
MERGE (a)-[r:MONITORED_BY]->(b) SET r += $props, r._source = 'patch', r._patch_date = $date
```

This allows:
- Distinguishing extraction-derived edges from manual patches
- Preserving patches during guideline reload (don't delete edges where `_source = 'patch'`)
- Auditing what was manually added vs. auto-generated

**Tests**:
- `test_add_edge_creates_relationship`: Patch op creates edge between existing nodes
- `test_add_edge_fails_for_missing_node`: Patch op errors if source/target doesn't exist
- `test_patch_preserves_existing_properties`: SET += doesn't overwrite existing props
- `test_reload_preserves_patch_edges`: After guideline reload, edges with `_source=patch` survive
- `test_dry_run_shows_diff`: `--dry-run` outputs correct counts without modifying graph
- `test_diff_detects_lost_patches`: Diff correctly identifies edges lost during reload

---

## Implementation Order

| Priority | Fix | Effort | Safety Impact |
|----------|-----|--------|---------------|
| P0 | Fix 1: Class inheritance | Medium | Critical — unblocks monitoring + interaction queries for all drugs |
| P0 | Fix 2: Terminology expansion | Small | Critical — unblocks NSAIDs/CCBs contraindication warnings |
| P0 | Fix 3: Variable aliases | Small | High — fixes false "CONDITIONS NOT MET" flags |
| P1 | Fix 4: DIAGNOSED_BY edges | Medium | High — enables diagnostic criteria intent |
| P1 | Fix 6: Fuzzy auto-retry | Small | Medium — handles entity resolution edge cases |
| P1 | Fix 7a: Patch operations (Level 1) | Medium | High — enables adding edges without full reload |
| P2 | Fix 5: Post-ingestion validation | Medium | Preventive — catches future gaps automatically |
| P2 | Fix 7b: Dry-run + diff (Levels 2-3) | Large | Operational — prevents data loss during upgrades |

**P0 fixes first** — these are the ones that cause silent clinical safety failures.
**P1 Fix 7a is high priority** — without patch mode, every fix to the graph requires a full re-ingestion cycle (extract → link → load), which is slow, expensive (LLM calls), and destructive.

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

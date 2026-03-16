# GraphRAG Clinical Scenario Fixes

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the 3 production issues discovered by the clinical scenario test against the live Neo4j graph.

**Architecture:** Three independent fixes targeting (1) entity ID normalization in the graph, (2) Layer 2 evidence retrieval query, and (3) DrugClass-level monitoring edge propagation. All fixes are backward-compatible.

**Tech Stack:** Python, Neo4j Cypher, pytest

---

## Background

The clinical scenario test (`tests/graphrag/test_clinical_scenario.py`) runs against the live Neo4j Aura graph and tests real-world heart failure clinical decisions. Three tests revealed production gaps:

1. **NSAID Entity ID Mismatch** — Terminology resolves "NSAID" to `atc:M01A` but the graph node has ID `drug_class:nsaid` (created by pre-terminology ingestion). The engine can't find INTERACTS_WITH edges because it queries by `atc:M01A`.

2. **Layer 2 Evidence Fetch Gap** — `_fetch_evidence_for_matches` calls `find_recommendations_for_entity(entity_id, entity_type)` but returns empty. The query uses `MATCH (rec)-[:RECOMMENDS]->(tgt:{entity_label} {id: $eid})` with inner MATCHes for SOURCED_FROM and DEFINED_BY — any missing link in this chain causes 0 results even when evidence exists.

3. **MRA Monitoring Gap** — Spironolactone has MONITORED_BY edges (K+, Cr, eGFR) but the MRA DrugClass node has none. So Eplerenone (MEMBER_OF→MRA) can't inherit monitoring via class inheritance. The fix is to propagate monitoring edges from member drugs to their parent DrugClass.

---

### Task 1: Fix NSAID Entity ID Mismatch (Graph Normalization Script)

**Root cause:** The graph was loaded before the terminology system existed. Nodes have IDs like `drug_class:nsaid` instead of `atc:M01A`. The linker resolves names to terminology IDs, but those IDs don't match graph nodes.

**Fix approach:** Write a migration script that re-IDs graph nodes to match terminology. This is a one-time Cypher migration + a post-ingestion validation check.

**Files:**
- Create: `scripts/graphrag/normalize_entity_ids.py`
- Modify: `src/open_medicine/graphrag/ingestion/validator.py` (add ID-mismatch check)
- Test: `tests/graphrag/test_clinical_scenario.py` (existing NSAID test should pass after migration)

**Step 1: Write the normalization script**

```python
# scripts/graphrag/normalize_entity_ids.py
"""One-time migration: re-ID graph nodes to match terminology IDs.

For each DrugClass/Drug/Disease/Lab node in the graph, looks up its name
in the terminology database. If the terminology ID differs from the graph
node's current ID, renames the node (creates new node with correct ID,
copies properties and edges, deletes old node).

Usage:
    source .env
    uv run python scripts/graphrag/normalize_entity_ids.py --dry-run
    uv run python scripts/graphrag/normalize_entity_ids.py
"""
```

The script should:
1. Connect to Neo4j using env vars (`GRAPHRAG_NEO4J_URI`, `GRAPHRAG_NEO4J_USER`, `GRAPHRAG_NEO4J_PASSWORD`)
2. For each label (Drug, DrugClass, Disease, Lab, Procedure, Device):
   - Query all nodes: `MATCH (n:{Label}) RETURN n.id AS id, n.name AS name`
   - For each node, call `link_entity(name, entity_type)` to get the terminology ID
   - If `linked.node_id != graph_node_id`: flag as mismatch
3. In `--dry-run` mode: print mismatches without changing anything
4. In write mode: for each mismatch, run Cypher to:
   - Create new node with correct ID and copy all properties
   - Copy all incoming and outgoing edges to new node
   - Delete old node

**Step 2: Run the script in dry-run mode against live graph**

```bash
source .env && uv run python scripts/graphrag/normalize_entity_ids.py --dry-run
```

Expected: prints list of mismatched IDs (at minimum `drug_class:nsaid` → `atc:M01A`)

**Step 3: Run the migration**

```bash
source .env && uv run python scripts/graphrag/normalize_entity_ids.py
```

**Step 4: Verify the NSAID interaction test passes**

```bash
source .env && uv run python -m pytest tests/graphrag/test_clinical_scenario.py::TestDrugInteractions -v
```

Expected: PASS

**Step 5: Add ID-mismatch check to validator**

In `validator.py`, add a check that samples 10 nodes per label and verifies their IDs match what the terminology would assign. This prevents future ingestion from creating mismatched IDs.

**Step 6: Commit**

```bash
git add scripts/graphrag/normalize_entity_ids.py src/open_medicine/graphrag/ingestion/validator.py
git commit -m "fix(graphrag): normalize entity IDs to match terminology database"
```

---

### Task 2: Fix Layer 2 Evidence Fetch (`_fetch_evidence_for_matches`)

**Root cause:** `find_recommendations_for_entity` uses three consecutive `MATCH` clauses (RECOMMENDS, SOURCED_FROM, DEFINED_BY). If ANY of these edges is missing for a recommendation, the entire row is excluded — this is an inner join across all three. Evidence exists but the join chain is broken.

**Fix approach:** Change the SOURCED_FROM and DEFINED_BY joins to OPTIONAL MATCH so that recommendations are still returned even if evidence or guideline links are incomplete.

**Files:**
- Modify: `src/open_medicine/graphrag/graph/queries_v2.py:825-848` (`find_recommendations_for_entity`)
- Test: `tests/graphrag/test_clinical_scenario.py` (existing evidence DOI test should pass)

**Step 1: Write a failing test**

Add a unit test in `tests/graphrag/test_queries_v2.py` that verifies `find_recommendations_for_entity` returns results even when SOURCED_FROM edge is missing.

```python
def test_find_recommendations_returns_without_evidence_chunk():
    """Recommendations without SOURCED_FROM should still be returned."""
    cypher, params = ReasoningQueries.find_recommendations_for_entity(
        "rxnorm:123", "Drug"
    )
    # The query should use OPTIONAL MATCH for evidence/guideline
    assert "OPTIONAL MATCH" in cypher
```

**Step 2: Run test to verify it fails**

```bash
uv run python -m pytest tests/graphrag/test_queries_v2.py::test_find_recommendations_returns_without_evidence_chunk -v
```

Expected: FAIL (current query uses `MATCH` not `OPTIONAL MATCH`)

**Step 3: Fix the query**

In `queries_v2.py`, change `find_recommendations_for_entity`:

```python
@staticmethod
def find_recommendations_for_entity(
    entity_id: str,
    entity_label: str,
    rec_type: str | None = None,
) -> CypherStatement:
    """All recommendations that reference a specific entity."""
    cypher = (
        f"MATCH (rec:Recommendation)-[:RECOMMENDS]->(tgt:{entity_label} {{id: $eid}}) "
        "OPTIONAL MATCH (rec)-[:SOURCED_FROM]->(ec:EvidenceChunk) "
        "OPTIONAL MATCH (rec)-[:DEFINED_BY]->(g:Guideline) "
    )
    params: dict = {"eid": entity_id}
    if rec_type:
        cypher += "WHERE rec.type = $rtype "
        params["rtype"] = rec_type
    cypher += (
        "RETURN rec.id AS rec_id, rec.type AS rec_type, "
        "rec.action AS action, rec.action_detail AS detail, "
        "rec.strength AS strength, rec.evidence_quality AS evidence_quality, "
        "ec.text AS source_text, ec.section AS section, "
        "g.title AS guideline, g.doi AS doi, g.year AS year "
        "ORDER BY g.year DESC"
    )
    return (cypher, params)
```

**Step 4: Run test to verify it passes**

```bash
uv run python -m pytest tests/graphrag/test_queries_v2.py -v
```

Expected: PASS

**Step 5: Run the clinical scenario evidence test**

```bash
source .env && uv run python -m pytest tests/graphrag/test_clinical_scenario.py::TestEvidenceRetrieval -v
```

Expected: PASS (now returns evidence even with incomplete chains)

**Step 6: Commit**

```bash
git add src/open_medicine/graphrag/graph/queries_v2.py tests/graphrag/test_queries_v2.py
git commit -m "fix(graphrag): use OPTIONAL MATCH for evidence in find_recommendations_for_entity"
```

---

### Task 3: Fix MRA Monitoring Gap (DrugClass Monitoring Propagation)

**Root cause:** The loader creates MONITORED_BY edges on individual Drug nodes (Spironolactone→K+) but not on the parent DrugClass node (MRA). When querying monitoring for Eplerenone, the engine checks Eplerenone→MONITORED_BY (none), then tries class inheritance via Eplerenone→MEMBER_OF→MRA→MONITORED_BY (also none). The monitoring edges only exist on Spironolactone.

**Fix approach:** During ingestion, propagate MONITORED_BY edges from member drugs to their parent DrugClass. If ≥2 members of a class share the same MONITORED_BY→Lab edge, create that edge on the DrugClass too. This way class inheritance works for monitoring.

**Files:**
- Modify: `src/open_medicine/graphrag/ingestion/loader_v2.py` (add monitoring propagation step)
- Create: `tests/graphrag/test_monitoring_propagation.py`
- Test: `tests/graphrag/test_clinical_scenario.py` (existing Eplerenone monitoring test)

**Step 1: Write a failing test**

```python
# tests/graphrag/test_monitoring_propagation.py
"""Tests for DrugClass monitoring edge propagation."""

def test_drug_class_inherits_monitoring_from_members():
    """If a member drug has MONITORED_BY edges, the parent DrugClass should too."""
    # Setup: create Drug(Spironolactone) -MONITORED_BY-> Lab(Potassium)
    #        create Drug(Spironolactone) -MEMBER_OF-> DrugClass(MRA)
    #        create Drug(Eplerenone) -MEMBER_OF-> DrugClass(MRA)
    # After propagation: DrugClass(MRA) -MONITORED_BY-> Lab(Potassium)
    ...
```

**Step 2: Run test to verify it fails**

```bash
uv run python -m pytest tests/graphrag/test_monitoring_propagation.py -v
```

Expected: FAIL

**Step 3: Add monitoring propagation to loader**

In `loader_v2.py`, after step 5 (MEMBER_OF edges), add step 6:

```python
# 6. Propagate monitoring from member drugs to DrugClass
for entity in seen_entities.values():
    if entity.entity_type == "drug_class":
        # Find all member drugs that have MONITORED_BY edges
        members = get_drug_class_members(entity.canonical_name)
        lab_counts: dict[str, int] = {}  # lab_id → count of members monitoring it
        lab_entities: dict[str, LinkedEntity] = {}

        for member_name in members:
            member = link_entity(member_name, "drug")
            if member is None or member.node_id not in seen_entities:
                continue
            # Check if this member has monitoring edges in our extraction
            for q in queries:
                cypher, params = q
                if "MONITORED_BY" in cypher and params.get("did") == member.node_id:
                    lab_id = params.get("lid", "")
                    if lab_id:
                        lab_counts[lab_id] = lab_counts.get(lab_id, 0) + 1

        # Propagate labs monitored by ≥1 member
        for lab_id, count in lab_counts.items():
            queries.append(
                LoaderQueries.create_monitored_by(
                    entity.node_id, lab_id,
                    MonitoredByProps(...)  # Copy from member
                )
            )
```

Note: The exact implementation needs to track which MONITORED_BY edges were created during extraction. An alternative simpler approach is a post-ingestion Cypher that propagates:

```cypher
MATCH (d:Drug)-[:MEMBER_OF]->(dc:DrugClass)
MATCH (d)-[r:MONITORED_BY]->(l:Lab)
WHERE NOT EXISTS { (dc)-[:MONITORED_BY]->(l) }
MERGE (dc)-[r2:MONITORED_BY]->(l)
SET r2.frequency = r.frequency,
    r2.threshold_alert = r.threshold_alert,
    r2.threshold_stop = r.threshold_stop,
    r2._source = 'propagated'
```

Add this as a post-load step in the loader, or as a standalone script similar to the ID normalization script.

**Step 4: Run test to verify it passes**

```bash
uv run python -m pytest tests/graphrag/test_monitoring_propagation.py -v
```

Expected: PASS

**Step 5: Run the clinical scenario monitoring test**

```bash
source .env && uv run python -m pytest tests/graphrag/test_clinical_scenario.py::TestMonitoringRequirements -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add src/open_medicine/graphrag/ingestion/loader_v2.py tests/graphrag/test_monitoring_propagation.py
git commit -m "fix(graphrag): propagate MONITORED_BY edges from member drugs to DrugClass"
```

---

### Task 4: Run Full Test Suite

**Step 1: Run all tests**

```bash
uv run python -m pytest -v
```

Expected: All 2939+ tests PASS

**Step 2: Run clinical scenario tests against live graph**

```bash
source .env && uv run python -m pytest tests/graphrag/test_clinical_scenario.py -v
```

Expected: All 21 tests PASS

**Step 3: Commit any remaining fixes**

If any tests fail, fix and commit.

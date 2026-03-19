# GraphRAG Scenario Grade B+ → A Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix 4 GraphRAG gaps identified in clinical scenario testing to bring the grade from B+ to A.

**Architecture:** Pure code fixes in the reasoning engine, enrichment parser, and loader. No schema changes, no re-ingestion needed for gaps 1-3. Gap 4 fixes the loader/enrichment so future ingestions populate missing fields.

**Tech Stack:** Python, Pydantic, Neo4j Cypher, regex

---

### Task 1: Fix `conditions_met` evaluation on vector fallback results

The `_vector_fallback()` method creates `SemanticMatch` objects but never calls `_evaluate_match_conditions()`. Since `conditions_met` defaults to `True`, all vector results incorrectly appear as passing — e.g., HFmrEF conditions (LVEF 41-49) show `conditions_met: true` for LVEF 28.

**Files:**
- Modify: `src/open_medicine/graphrag/reasoning/engine_v2.py:792-833`
- Test: `tests/graphrag/test_engine_v2.py`

**Step 1: Write the failing test**

Add to `tests/graphrag/test_engine_v2.py` in the `TestVectorFallback` class (near line 1473):

```python
@patch("open_medicine.graphrag.reasoning.engine_v2.embed_query")
@patch("open_medicine.graphrag.reasoning.engine_v2.link_entity", return_value=None)
def test_vector_fallback_evaluates_conditions(self, mock_link, mock_embed):
    """Vector fallback results must have conditions evaluated against patient_vars."""
    mock_embed.return_value = [0.1] * 1024
    engine, conn = _make_engine()
    # Vector search returns a match with LVEF >= 41 condition
    conn.execute_read.return_value = [
        {
            "entity_id": "atc:C09C",
            "entity_name": "ARB",
            "entity_type": "DrugClass",
            "strength": "weak_for",
            "evidence_quality": "moderate",
            "conditions": json.dumps([
                {"variable": "LVEF", "operator": ">=", "threshold": 41, "unit": "%"},
                {"variable": "LVEF", "operator": "<=", "threshold": 49, "unit": "%"},
            ]),
            "score": 0.85,
        }
    ]
    q = ClinicalQuery(
        intent="treatment_selection",
        concepts=["SomeCondition"],
        patient_vars={"lvef": 28},
        include_evidence=False,
    )
    result = engine.query(q)
    assert len(result.semantic_matches) >= 1
    match = result.semantic_matches[0]
    assert match.source_layer == "vector"
    # LVEF 28 does NOT meet >= 41, so conditions_met must be False
    assert match.conditions_met is False
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py::TestVectorFallback::test_vector_fallback_evaluates_conditions -v`
Expected: FAIL — `assert match.conditions_met is False` fails because `conditions_met` defaults to `True`.

**Step 3: Implement the fix**

In `src/open_medicine/graphrag/reasoning/engine_v2.py`, modify `_vector_fallback()` to evaluate conditions on each match. After the match is created (line 831), add condition evaluation:

```python
# In _vector_fallback(), after creating the match (line 831), before appending:
            matches.append(
                SemanticMatch(
                    entity_id=row.get("entity_id", ""),
                    entity_name=row.get("entity_name", ""),
                    entity_type=row.get("entity_type", ""),
                    edge_type=self._infer_edge_type(q.intent),
                    strength=row.get("strength", ""),
                    evidence_quality=row.get("evidence_quality") or "",
                    conditions_json=row.get("conditions"),
                    source_layer="vector",
                    similarity_score=score,
                )
            )
        # Evaluate conditions on vector results using the query's patient_vars
        for m in matches:
            self._evaluate_match_conditions(m, q.patient_vars)
        return matches
```

Note: `_vector_fallback` currently does NOT receive `q` — only embedding info. It needs the full query to access `patient_vars`. Change the signature to accept `ClinicalQuery` instead of just the query text. However, looking at the code, it already accepts `q: ClinicalQuery` at line 792. So we just add the loop before the return.

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py::TestVectorFallback::test_vector_fallback_evaluates_conditions -v`
Expected: PASS

**Step 5: Run existing vector tests to verify no regressions**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py::TestVectorFallback -v`
Expected: All pass. Note: `test_vector_fallback_when_graph_empty` uses `conditions: None`, so condition evaluation is a no-op (passes through).

**Step 6: Commit**

```bash
git add src/open_medicine/graphrag/reasoning/engine_v2.py tests/graphrag/test_engine_v2.py
git commit -m "fix(graphrag): evaluate conditions on vector fallback results

Vector results defaulted to conditions_met=True without evaluation,
causing false positives (e.g. HFmrEF conditions passing for LVEF 28)."
```

---

### Task 2: Add concept-to-variable inference for `missing_variables` reduction

When querying for `heart_failure_reduced_ef`, the engine reports `HF_type` as a missing variable even though the concept itself implies `HF_type=HFrEF`. This causes `conditions_met: null` on results that should be fully evaluable.

**Files:**
- Modify: `src/open_medicine/graphrag/reasoning/engine_v2.py:60-80` (alias map area) and `_evaluate_match_conditions` area
- Test: `tests/graphrag/test_engine_v2.py`

**Step 1: Write the failing test**

Add to `tests/graphrag/test_engine_v2.py` in the condition evaluation test class:

```python
def test_concept_inferred_vars_fill_missing(self):
    """Concepts like 'heart_failure_reduced_ef' should inject hf_type=HFrEF."""
    engine, conn = _make_engine()
    match = SemanticMatch(
        entity_id="atc:A10BK",
        entity_name="SGLT2 Inhibitor",
        entity_type="DrugClass",
        edge_type="INDICATED_FOR",
        strength="strong_for",
        evidence_quality="high",
        conditions_json=json.dumps([
            {"variable": "LVEF", "operator": "<=", "threshold": 40, "unit": "%"},
            {"variable": "HF_type", "operator": "==", "threshold": "HFrEF", "unit": None},
        ]),
    )
    # Patient vars have lvef but not HF_type — however concept implies it
    patient_vars = {"lvef": 28}
    inferred = engine._infer_vars_from_concepts(["heart_failure_reduced_ef"])
    merged = {**inferred, **patient_vars}
    engine._evaluate_match_conditions(match, merged)
    assert match.conditions_met is True
    assert match.missing_variables == []
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py -k test_concept_inferred_vars_fill_missing -v`
Expected: FAIL — `_infer_vars_from_concepts` does not exist yet.

**Step 3: Implement the fix**

In `src/open_medicine/graphrag/reasoning/engine_v2.py`, add the inference map and method near the `_VARIABLE_ALIASES` constant (after line 80):

```python
# Maps resolved concept/disease names to implied patient variables.
# When a query concept resolves to one of these, inject the variables
# into patient_vars so condition evaluation can proceed without
# reporting them as "missing".
_CONCEPT_IMPLIED_VARS: dict[str, dict[str, str | float | bool]] = {
    "heart_failure_reduced_ef": {"hf_type": "HFrEF"},
    "hfref": {"hf_type": "HFrEF"},
    "heart_failure_preserved_ef": {"hf_type": "HFpEF"},
    "hfpef": {"hf_type": "HFpEF"},
    "heart_failure_mildly_reduced_ef": {"hf_type": "HFmrEF"},
    "hfmref": {"hf_type": "HFmrEF"},
}
```

Add the method to the `ReasoningEngine` class:

```python
@staticmethod
def _infer_vars_from_concepts(concepts: list[str]) -> dict[str, str | float | bool]:
    """Infer patient variables from query concepts.

    E.g., querying for 'heart_failure_reduced_ef' implies hf_type=HFrEF.
    """
    inferred: dict[str, str | float | bool] = {}
    for concept in concepts:
        key = concept.lower().replace(" ", "_")
        implied = _CONCEPT_IMPLIED_VARS.get(key, {})
        inferred.update(implied)
    return inferred
```

Then, in each `_query_*` method that calls `_evaluate_match_conditions`, merge inferred vars into patient_vars. The cleanest place is in the `query()` dispatch method or at the top of each `_query_*`. Best approach: merge once in `query()` before dispatching, so all intents benefit.

Find the `query()` method and add the merge there, right before the dispatch call:

```python
# In query() method, before dispatching to intent handler:
inferred = self._infer_vars_from_concepts(q.concepts)
if inferred:
    # Merge inferred vars (patient-provided vars take precedence)
    merged = {**inferred, **q.patient_vars}
    q = q.model_copy(update={"patient_vars": merged})
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py -k test_concept_inferred_vars_fill_missing -v`
Expected: PASS

**Step 5: Run full engine test suite**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py -v`
Expected: All pass.

**Step 6: Commit**

```bash
git add src/open_medicine/graphrag/reasoning/engine_v2.py tests/graphrag/test_engine_v2.py
git commit -m "feat(graphrag): infer patient variables from query concepts

Querying for 'heart_failure_reduced_ef' now implies hf_type=HFrEF,
reducing false missing_variables reports on condition evaluation."
```

---

### Task 3: Add `titration_schedule` extraction and loader fallback

Two issues: (a) `loader_v2.py` line 595 doesn't fall back to regex-parsed `titration_schedule`, unlike all other dosing properties. (b) `enrichment.py` `parse_dosing_properties()` doesn't extract `titration_schedule` from text.

**Files:**
- Modify: `src/open_medicine/graphrag/enrichment.py:94-228` (add titration regex)
- Modify: `src/open_medicine/graphrag/ingestion/loader_v2.py:595` (add fallback)
- Test: `tests/graphrag/test_enrichment.py`
- Test: `tests/graphrag/test_loader_v2.py`

**Step 1: Write failing tests for enrichment**

Add to `tests/graphrag/test_enrichment.py` in the `TestParseDosing` class:

```python
def test_titration_schedule_every_2_weeks(self):
    text = "Start 3.125 mg twice daily; titrate every 2 weeks to 25 mg twice daily"
    result = parse_dosing_properties(text)
    assert result.get("titration_schedule") is not None
    assert "2 weeks" in result["titration_schedule"]

def test_titration_schedule_double_dose(self):
    text = "Initiate 12.5 mg daily; double the dose every 4 weeks as tolerated"
    result = parse_dosing_properties(text)
    assert result.get("titration_schedule") is not None

def test_titration_schedule_uptitrate(self):
    text = "uptitrate at 2-week intervals to target dose of 200 mg BID"
    result = parse_dosing_properties(text)
    assert result.get("titration_schedule") is not None
    assert "2-week" in result["titration_schedule"] or "2 week" in result["titration_schedule"]
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/graphrag/test_enrichment.py::TestParseDosing::test_titration_schedule_every_2_weeks tests/graphrag/test_enrichment.py::TestParseDosing::test_titration_schedule_double_dose tests/graphrag/test_enrichment.py::TestParseDosing::test_titration_schedule_uptitrate -v`
Expected: FAIL — `titration_schedule` key not in result.

**Step 3: Implement titration extraction in enrichment.py**

In `src/open_medicine/graphrag/enrichment.py`, add titration patterns after the route extraction block (after line 221, before the validation block at line 223):

```python
    # --- Titration schedule ---
    titration_patterns = [
        # "titrate every 2 weeks", "titrate every 2-4 weeks"
        r"(titrat\w*\s+every\s+\d+(?:-\d+)?\s*(?:weeks?|days?|months?))",
        # "uptitrate at 2-week intervals"
        r"(uptitrat\w*\s+(?:at\s+)?\d+(?:-\d+)?[\s-]*(?:week|day|month)\s*intervals?)",
        # "double the dose every 4 weeks"
        r"(double\s+(?:the\s+)?dose\s+every\s+\d+(?:-\d+)?\s*(?:weeks?|days?|months?))",
        # "increase dose every 2 weeks"
        r"(increase\s+(?:the\s+)?dose\s+every\s+\d+(?:-\d+)?\s*(?:weeks?|days?|months?))",
    ]
    for pat in titration_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            props["titration_schedule"] = m.group(1).strip()
            break
```

**Step 4: Run enrichment tests**

Run: `uv run python -m pytest tests/graphrag/test_enrichment.py::TestParseDosing -v`
Expected: All pass including new titration tests.

**Step 5: Write failing test for loader fallback**

Add to `tests/graphrag/test_loader_v2.py` near `test_dosed_for_regex_fallback` (line 578):

```python
def test_dosed_for_titration_fallback(self):
    """DOSED_FOR titration_schedule should fall back to regex like other dosing props."""
    conn = MagicMock()
    guideline = Guideline(
        id="test_2022", title="Test", doi="10.x/y", year=2022, organization="Org"
    )
    extractions = [
        ExtractionResult(
            rec_id="rec_dose_tit",
            rec_type="dosing",
            action="Start carvedilol",
            action_detail="Start at 3.125 mg twice daily; titrate every 2 weeks to target 25 mg twice daily",
            strength="strong_for",
            evidence_quality="high",
            concepts=[
                ConceptRef("Carvedilol", "drug", "subject"),
                ConceptRef("HFrEF", "disease", "target"),
            ],
            guideline_id="test_2022",
        ),
    ]
    data = LoadableGuideline(guideline=guideline, chunks=[], extractions=extractions)
    load_guideline(conn, data)

    all_queries = conn.execute_write_tx.call_args[0][0]
    df_queries = [
        (c, p) for c, p in all_queries
        if "DOSED_FOR" in c
    ]
    assert len(df_queries) >= 1
    _, params = df_queries[0]
    assert params.get("titration") is not None
    assert "2 weeks" in params["titration"]
```

**Step 6: Run test to verify it fails**

Run: `uv run python -m pytest tests/graphrag/test_loader_v2.py::TestLoadGuideline::test_dosed_for_titration_fallback -v`
Expected: FAIL — `titration` param is None because line 595 has no fallback.

**Step 7: Fix loader fallback**

In `src/open_medicine/graphrag/ingestion/loader_v2.py` line 595, change:

```python
# Before:
titration_schedule=sp.get("titration_schedule"),
# After:
titration_schedule=sp.get("titration_schedule") or parsed.get("titration_schedule"),
```

**Step 8: Run loader test**

Run: `uv run python -m pytest tests/graphrag/test_loader_v2.py::TestLoadGuideline::test_dosed_for_titration_fallback -v`
Expected: PASS

**Step 9: Run all loader and enrichment tests**

Run: `uv run python -m pytest tests/graphrag/test_loader_v2.py tests/graphrag/test_enrichment.py -v`
Expected: All pass.

**Step 10: Commit**

```bash
git add src/open_medicine/graphrag/enrichment.py src/open_medicine/graphrag/ingestion/loader_v2.py tests/graphrag/test_enrichment.py tests/graphrag/test_loader_v2.py
git commit -m "fix(graphrag): add titration_schedule extraction and loader fallback

Enrichment parser now extracts titration_schedule from dosing text.
Loader falls back to regex-parsed value like all other dosing properties."
```

---

### Task 4: Enrich treatment results with dosing summary from related edges

`find_treatment_options` returns empty `edge_properties: {}` because INDICATED_FOR edges carry only strength/evidence_quality/conditions. Add a lightweight follow-up traversal to populate basic dosing info from related DOSED_FOR edges.

**Files:**
- Modify: `src/open_medicine/graphrag/reasoning/engine_v2.py:182-263` (`_query_treatments`)
- Modify: `src/open_medicine/graphrag/graph/queries_v2.py` (add a new Cypher query)
- Test: `tests/graphrag/test_engine_v2.py`

**Step 1: Write the failing test**

Add to `tests/graphrag/test_engine_v2.py`:

```python
class TestTreatmentEdgePropertiesEnrichment:
    """Treatment results should include dosing summary from related DOSED_FOR edges."""

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_treatment_results_enriched_with_dosing(self, mock_link):
        linked = MagicMock()
        linked.node_id = "snomed:703272007"
        linked.node_label = "Disease"
        mock_link.return_value = linked

        engine, conn = _make_engine()
        # First call: find_treatments returns a drug with INDICATED_FOR
        # Second call: dosing enrichment returns DOSED_FOR properties
        conn.execute_read.side_effect = [
            # Layer 1: INDICATED_FOR results
            [
                {
                    "entity_id": "atc:A10BK",
                    "entity_name": "SGLT2 Inhibitor",
                    "entity_type": "DrugClass",
                    "strength": "strong_for",
                    "evidence_quality": "high",
                    "conditions": None,
                }
            ],
            # Dosing enrichment query
            [
                {
                    "entity_id": "atc:A10BK",
                    "starting_dose": "10 mg",
                    "frequency": "once daily",
                }
            ],
            # Evidence fetch (empty)
            [],
        ]
        q = ClinicalQuery(
            intent="treatment_selection",
            concepts=["heart_failure_reduced_ef"],
            include_evidence=False,
        )
        result = engine.query(q)
        sglt2 = next(
            (m for m in result.semantic_matches if m.entity_name == "SGLT2 Inhibitor"),
            None,
        )
        assert sglt2 is not None
        assert sglt2.edge_properties.get("starting_dose") == "10 mg"
        assert sglt2.edge_properties.get("frequency") == "once daily"
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py::TestTreatmentEdgePropertiesEnrichment::test_treatment_results_enriched_with_dosing -v`
Expected: FAIL — `edge_properties` is empty `{}`.

**Step 3: Add Cypher query for dosing enrichment**

In `src/open_medicine/graphrag/graph/queries_v2.py`, add a new static method to `ReasoningQueries`:

```python
@staticmethod
def find_dosing_summary_for_entities(entity_ids: list[str]) -> CypherStatement:
    """Fetch basic dosing properties for a list of drug/drug_class entities.

    Used to enrich treatment recommendations with dosing context.
    Returns one row per entity with the best available dosing info.
    """
    return (
        "UNWIND $ids AS eid "
        "MATCH (src {id: eid})-[r:DOSED_FOR]->(dis) "
        "RETURN src.id AS entity_id, "
        "r.starting_dose AS starting_dose, "
        "r.target_dose AS target_dose, "
        "r.max_dose AS max_dose, "
        "r.frequency AS frequency "
        "ORDER BY entity_id "
        "LIMIT 50",
        {"ids": entity_ids},
    )
```

**Step 4: Implement enrichment in `_query_treatments`**

In `src/open_medicine/graphrag/reasoning/engine_v2.py`, in `_query_treatments()`, after deduplication (line 254) and before evidence fetch (line 257), add:

```python
        # Enrich drug/drug_class matches with dosing summary
        drug_matches = [
            m for m in semantic_matches
            if m.entity_type in ("Drug", "DrugClass") and not m.edge_properties
        ]
        if drug_matches:
            drug_ids = [m.entity_id for m in drug_matches]
            cypher, params = ReasoningQueries.find_dosing_summary_for_entities(drug_ids)
            dosing_rows = self._conn.execute_read(cypher, params)
            dosing_by_id: dict[str, dict] = {}
            for row in dosing_rows:
                eid = row.get("entity_id", "")
                if eid not in dosing_by_id:  # Keep first (best) match per entity
                    dosing_by_id[eid] = {
                        k: row.get(k)
                        for k in ("starting_dose", "target_dose", "max_dose", "frequency")
                        if row.get(k)
                    }
            for m in drug_matches:
                if m.entity_id in dosing_by_id:
                    m.edge_properties = dosing_by_id[m.entity_id]
```

**Step 5: Run test to verify it passes**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py::TestTreatmentEdgePropertiesEnrichment -v`
Expected: PASS

**Step 6: Run full engine test suite**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py -v`
Expected: All pass. Existing tests use `conn.execute_read.return_value` (not `side_effect`), so they'll return the same value for the enrichment query (empty list is fine — no enrichment applied).

**Step 7: Commit**

```bash
git add src/open_medicine/graphrag/reasoning/engine_v2.py src/open_medicine/graphrag/graph/queries_v2.py tests/graphrag/test_engine_v2.py
git commit -m "feat(graphrag): enrich treatment results with dosing summary

Treatment recommendations now include starting_dose, frequency, etc.
from related DOSED_FOR edges, eliminating the need for a separate dosing query."
```

---

### Task 5: Integration verification — re-run clinical scenarios

After all 4 fixes are implemented and committed, verify by re-running the clinical scenarios.

**Step 1: Run all graphrag tests**

Run: `uv run python -m pytest tests/graphrag/ -v`
Expected: All pass.

**Step 2: Re-run clinical scenarios**

Use the `/run-scenarios` skill to re-run both scenarios against the MCP tools. Expected improvements:

| Gap | Before | After |
|-----|--------|-------|
| conditions_met on vector results | `true` for HFmrEF with LVEF 28 | `false` (correct) |
| edge_properties on treatments | `{}` empty | Populated with dosing summary |
| missing_variables for HFrEF queries | `["HF_type", "NYHA_class"]` | `[]` or reduced (HF_type inferred) |
| titration_schedule on dosing edges | `null` | Populated from regex extraction |

**Step 3: Commit any final adjustments**

If the scenario re-run reveals issues, fix and commit incrementally.

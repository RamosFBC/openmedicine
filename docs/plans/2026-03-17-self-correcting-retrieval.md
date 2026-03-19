# Self-Correcting Retrieval Loop — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a retrieve-evaluate-refine loop to engine_v2.py so the engine automatically re-queries with relaxed parameters when initial retrieval returns insufficient or low-confidence results.

**Architecture:** The existing 4-layer pipeline (semantic edges → multi-hop expansion → vector fallback → hints) stays intact. We add a **correction layer** that wraps the pipeline: after `_execute_query` returns, evaluate the result quality. If below threshold, apply a correction strategy (class escalation, concept decomposition, or intent relaxation) and re-query. Max 2 correction attempts to bound latency.

**Tech Stack:** Pure Python, Pydantic models, existing Neo4j graph connection. No new dependencies.

---

## Current State

The engine already has:
- **Fuzzy auto-retry** (line 140-153): if zero results, fuzzy-match concept names and retry once
- **Layer 3 vector fallback**: per-handler, falls through when graph traversal is empty
- **Layer 4 hints**: reformulation suggestions when everything is empty

What's **missing** (the self-correction gap):
1. When results exist but are **all conditions_met=False**, no re-query happens
2. No **class-level escalation**: if drug-level query returns nothing, doesn't check its drug class
3. No **concept decomposition**: "Sacubitril/Valsartan" doesn't split into components
4. No **intent relaxation**: if "dosing" returns nothing, doesn't check "treatment_selection" to confirm the drug is even indicated

---

### Task 1: Add correction strategies enum and result evaluator

**Files:**
- Modify: `src/open_medicine/graphrag/reasoning/types_v2.py`
- Modify: `src/open_medicine/graphrag/reasoning/engine_v2.py`
- Test: `tests/graphrag/test_engine_v2.py`

**Step 1: Write the failing test**

Add to `tests/graphrag/test_engine_v2.py`:

```python
class TestResultEvaluator:
    """Test the result quality evaluator that decides whether to self-correct."""

    def test_sufficient_high_confidence(self):
        """Full results with conditions_met=True → no correction needed."""
        from open_medicine.graphrag.reasoning.engine_v2 import ReasoningEngine

        result = GraphRAGResult(
            semantic_matches=[
                SemanticMatch(
                    entity_id="drug:carvedilol",
                    entity_name="Carvedilol",
                    entity_type="Drug",
                    edge_type="INDICATED_FOR",
                    strength="strong_for",
                    evidence_quality="high",
                    conditions_met=True,
                )
            ],
            confidence="high",
        )
        assert ReasoningEngine._needs_correction(result, min_results=1) is False

    def test_empty_results_needs_correction(self):
        """Zero results → needs correction."""
        result = GraphRAGResult(semantic_matches=[], confidence="low")
        assert ReasoningEngine._needs_correction(result, min_results=1) is True

    def test_all_conditions_failed_needs_correction(self):
        """All matches have conditions_met=False → needs correction."""
        result = GraphRAGResult(
            semantic_matches=[
                SemanticMatch(
                    entity_id="drug:x",
                    entity_name="X",
                    entity_type="Drug",
                    edge_type="INDICATED_FOR",
                    strength="strong_for",
                    evidence_quality="high",
                    conditions_met=False,
                )
            ],
            confidence="medium",
        )
        assert ReasoningEngine._needs_correction(result, min_results=1) is True

    def test_below_min_results_threshold(self):
        """Fewer results than threshold → needs correction."""
        result = GraphRAGResult(
            semantic_matches=[
                SemanticMatch(
                    entity_id="drug:x",
                    entity_name="X",
                    entity_type="Drug",
                    edge_type="INDICATED_FOR",
                    strength="strong_for",
                    evidence_quality="high",
                    conditions_met=True,
                )
            ],
            confidence="high",
        )
        # Wants at least 3, got 1
        assert ReasoningEngine._needs_correction(result, min_results=3) is True

    def test_vector_only_at_low_confidence(self):
        """Only vector results with low confidence → needs correction."""
        result = GraphRAGResult(
            semantic_matches=[
                SemanticMatch(
                    entity_id="drug:x",
                    entity_name="X",
                    entity_type="Drug",
                    edge_type="INDICATED_FOR",
                    strength="",
                    evidence_quality="",
                    source_layer="vector",
                    conditions_met=True,
                )
            ],
            confidence="medium",
            retrieval_layers_used=["vector"],
        )
        assert ReasoningEngine._needs_correction(result, min_results=1) is True
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py::TestResultEvaluator -v`
Expected: FAIL with `AttributeError: type object 'ReasoningEngine' has no attribute '_needs_correction'`

**Step 3: Write minimal implementation**

Add to `engine_v2.py` as a static method on `ReasoningEngine`:

```python
@staticmethod
def _needs_correction(result: GraphRAGResult, min_results: int = 1) -> bool:
    """Evaluate whether a query result needs self-correction.

    Returns True when:
    - Zero results
    - All matches have conditions_met=False (none applicable to patient)
    - Fewer passing matches than min_results
    - Only vector-sourced results (low structural confidence)
    """
    passing = [m for m in result.semantic_matches if m.conditions_met is not False]
    if not passing:
        return True
    if len(passing) < min_results:
        return True
    # Vector-only results are semantically approximate
    if all(m.source_layer == "vector" for m in passing):
        return True
    return False
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py::TestResultEvaluator -v`
Expected: PASS (all 5 tests)

**Step 5: Commit**

```bash
git add tests/graphrag/test_engine_v2.py src/open_medicine/graphrag/reasoning/engine_v2.py
git commit -m "feat(graphrag): add result quality evaluator for self-correction"
```

---

### Task 2: Add class-level escalation correction strategy

When a drug-level query returns insufficient results, re-query using the drug's parent class. Example: "Carvedilol" has no contraindication edges → check "Beta Blocker" class.

**Files:**
- Modify: `src/open_medicine/graphrag/reasoning/engine_v2.py`
- Test: `tests/graphrag/test_engine_v2.py`

**Step 1: Write the failing test**

```python
class TestClassEscalationCorrection:
    """Test that empty drug-level queries escalate to drug class."""

    @patch("open_medicine.graphrag.reasoning.engine_v2.embed_query")
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_drug_escalates_to_class(self, mock_link, mock_embed):
        """If drug-level contraindication returns nothing, try its class."""
        mock_embed.side_effect = Exception("no key")

        call_count = {"n": 0}
        def link_side_effect(name, etype):
            """First call: resolve drug. Second call: resolve class."""
            if etype == "drug" and name == "Carvedilol":
                return type("E", (), {"node_id": "drug:carvedilol", "entity_type": "Drug"})()
            if etype == "drug_class" and name == "Beta Blocker":
                return type("E", (), {"node_id": "atc:C07", "entity_type": "DrugClass"})()
            if etype == "disease":
                return type("E", (), {"node_id": "disease:hf", "entity_type": "Disease"})()
            return None

        mock_link.side_effect = link_side_effect

        conn = MagicMock()
        # First call: drug-level → empty
        # Second call: class lookup → returns parent
        # Third call: class-level → has results
        conn.execute_read.side_effect = [
            [],  # drug-level contraindication query
            [{"class_id": "atc:C07", "class_name": "Beta Blocker"}],  # parent class lookup
            [  # class-level contraindication query
                {
                    "entity_id": "disease:asthma",
                    "entity_name": "Asthma",
                    "entity_type": "Disease",
                    "strength": "strong_against",
                    "evidence_quality": "high",
                    "conditions": None,
                    "starting_dose": None,
                    "target_dose": None,
                    "max_dose": None,
                    "frequency": None,
                    "severity": "RELATIVE",
                    "mechanism": None,
                    "clinical_effect": None,
                    "threshold_alert": None,
                    "threshold_stop": None,
                    "reason": "Bronchospasm risk",
                }
            ],
        ]

        engine = ReasoningEngine(conn)
        q = ClinicalQuery(
            intent="contraindication",
            concepts=["Carvedilol"],
        )
        result = engine.query(q)
        assert len(result.semantic_matches) > 0
        assert any("Asthma" in m.entity_name for m in result.semantic_matches)
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py::TestClassEscalationCorrection -v`
Expected: FAIL — currently the engine doesn't escalate to class level

**Step 3: Write minimal implementation**

Add a `_try_class_escalation` method and integrate into `query()`:

```python
def _try_class_escalation(self, q: ClinicalQuery) -> ClinicalQuery | None:
    """If concepts are drugs, try re-querying with their parent drug classes."""
    escalated_concepts = []
    changed = False
    for concept in q.concepts:
        entity = link_entity(concept, "drug")
        if entity is not None:
            parents = self._get_parent_classes(entity.node_id)
            if parents:
                # Use the first (most specific) parent class
                class_id, class_name = parents[0]
                escalated_concepts.append(class_name)
                changed = True
                continue
        escalated_concepts.append(concept)

    if not changed:
        return None

    return ClinicalQuery(
        intent=q.intent,
        concepts=escalated_concepts,
        patient_vars=q.patient_vars,
        guideline_filter=q.guideline_filter,
        include_evidence=q.include_evidence,
        min_results_threshold=q.min_results_threshold,
    )
```

Modify `query()` to add correction after the existing fuzzy retry:

```python
def query(self, q: ClinicalQuery) -> GraphRAGResult:
    # ... existing infer_vars + execute_query ...

    # Existing: fuzzy auto-retry
    if not result.semantic_matches and not result.recommendation_matches:
        retried_concepts = self._fuzzy_resolve_concepts(q.concepts)
        if retried_concepts and retried_concepts != q.concepts:
            retry_q = q.model_copy(update={"concepts": retried_concepts})
            result = self._execute_query(retry_q)

    # NEW: self-correction — class escalation
    if self._needs_correction(result, q.min_results_threshold):
        escalated_q = self._try_class_escalation(q)
        if escalated_q is not None:
            correction_result = self._execute_query(escalated_q)
            # Merge: keep original results, add new ones (mark as expanded)
            for m in correction_result.semantic_matches:
                m.source_layer = "expanded"
            result.semantic_matches.extend(correction_result.semantic_matches)
            result.semantic_matches = self._deduplicate(result.semantic_matches)

    return result
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py::TestClassEscalationCorrection -v`
Expected: PASS

**Step 5: Run existing tests to verify no regressions**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py -v -x`
Expected: All existing tests pass

**Step 6: Commit**

```bash
git add src/open_medicine/graphrag/reasoning/engine_v2.py tests/graphrag/test_engine_v2.py
git commit -m "feat(graphrag): add class-level escalation self-correction"
```

---

### Task 3: Add concept decomposition correction strategy

Split combination concepts (e.g., "Sacubitril/Valsartan") into components and re-query each.

**Files:**
- Modify: `src/open_medicine/graphrag/reasoning/engine_v2.py`
- Test: `tests/graphrag/test_engine_v2.py`

**Step 1: Write the failing test**

```python
class TestConceptDecomposition:
    """Test splitting combination drug names into components."""

    def test_decompose_slash_separated(self):
        result = ReasoningEngine._decompose_concepts(["Sacubitril/Valsartan"])
        assert "Sacubitril" in result
        assert "Valsartan" in result
        assert "Sacubitril/Valsartan" in result  # keep original too

    def test_no_decomposition_simple_name(self):
        result = ReasoningEngine._decompose_concepts(["Carvedilol"])
        assert result == ["Carvedilol"]

    def test_preserves_non_drug_concepts(self):
        result = ReasoningEngine._decompose_concepts(["Heart Failure", "Sacubitril/Valsartan"])
        assert "Heart Failure" in result
        assert "Sacubitril" in result
        assert "Valsartan" in result
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py::TestConceptDecomposition -v`
Expected: FAIL with `AttributeError`

**Step 3: Write minimal implementation**

```python
@staticmethod
def _decompose_concepts(concepts: list[str]) -> list[str]:
    """Split combination drug names into components.

    "Sacubitril/Valsartan" → ["Sacubitril/Valsartan", "Sacubitril", "Valsartan"]
    Keeps the original concept for exact matching, adds components for broader search.
    """
    result = []
    changed = False
    for concept in concepts:
        result.append(concept)
        if "/" in concept:
            parts = [p.strip() for p in concept.split("/") if p.strip()]
            if len(parts) >= 2:
                result.extend(parts)
                changed = True
    return result if changed else concepts
```

Integrate into `query()` as a second correction strategy:

```python
    # NEW: self-correction — concept decomposition
    if self._needs_correction(result, q.min_results_threshold):
        decomposed = self._decompose_concepts(q.concepts)
        if decomposed != q.concepts:
            decomposed_q = q.model_copy(update={"concepts": decomposed})
            correction_result = self._execute_query(decomposed_q)
            for m in correction_result.semantic_matches:
                m.source_layer = "expanded"
            result.semantic_matches.extend(correction_result.semantic_matches)
            result.semantic_matches = self._deduplicate(result.semantic_matches)
```

**Step 4: Run tests**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py::TestConceptDecomposition -v`
Expected: PASS

**Step 5: Run existing tests**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py -v -x`
Expected: All pass

**Step 6: Commit**

```bash
git add src/open_medicine/graphrag/reasoning/engine_v2.py tests/graphrag/test_engine_v2.py
git commit -m "feat(graphrag): add concept decomposition self-correction"
```

---

### Task 4: Add retrieval metadata tracking

Track which correction strategies were attempted and whether they produced results. This feeds into the `GraphRAGResult` so consumers know how the answer was constructed.

**Files:**
- Modify: `src/open_medicine/graphrag/reasoning/types_v2.py`
- Modify: `src/open_medicine/graphrag/reasoning/engine_v2.py`
- Test: `tests/graphrag/test_engine_v2.py`

**Step 1: Write the failing test**

```python
class TestCorrectionMetadata:
    """Test that correction attempts are tracked in the result."""

    @patch("open_medicine.graphrag.reasoning.engine_v2.embed_query")
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_corrections_tracked(self, mock_link, mock_embed):
        """Result should list which corrections were attempted."""
        mock_embed.side_effect = Exception("no key")
        mock_link.return_value = None

        conn = MagicMock()
        conn.execute_read.return_value = []

        engine = ReasoningEngine(conn)
        q = ClinicalQuery(intent="contraindication", concepts=["UnknownDrug123"])
        result = engine.query(q)

        assert hasattr(result, "corrections_attempted")
        assert isinstance(result.corrections_attempted, list)
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py::TestCorrectionMetadata -v`
Expected: FAIL — `corrections_attempted` field doesn't exist

**Step 3: Write implementation**

Add to `types_v2.py` in `GraphRAGResult`:

```python
corrections_attempted: list[str] = Field(
    default_factory=list,
    description="Self-correction strategies attempted: fuzzy_retry, class_escalation, concept_decomposition",
)
```

Update `query()` to track corrections:

```python
def query(self, q: ClinicalQuery) -> GraphRAGResult:
    # ... existing code ...
    corrections: list[str] = []

    # Existing fuzzy retry
    if not result.semantic_matches and not result.recommendation_matches:
        retried_concepts = self._fuzzy_resolve_concepts(q.concepts)
        if retried_concepts and retried_concepts != q.concepts:
            corrections.append("fuzzy_retry")
            retry_q = q.model_copy(update={"concepts": retried_concepts})
            result = self._execute_query(retry_q)

    # Class escalation
    if self._needs_correction(result, q.min_results_threshold):
        escalated_q = self._try_class_escalation(q)
        if escalated_q is not None:
            corrections.append("class_escalation")
            # ... existing merge logic ...

    # Concept decomposition
    if self._needs_correction(result, q.min_results_threshold):
        decomposed = self._decompose_concepts(q.concepts)
        if decomposed != q.concepts:
            corrections.append("concept_decomposition")
            # ... existing merge logic ...

    result.corrections_attempted = corrections
    return result
```

**Step 4: Run tests**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py::TestCorrectionMetadata -v`
Expected: PASS

**Step 5: Run full engine test suite**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py -v -x`
Expected: All pass

**Step 6: Commit**

```bash
git add src/open_medicine/graphrag/reasoning/types_v2.py src/open_medicine/graphrag/reasoning/engine_v2.py tests/graphrag/test_engine_v2.py
git commit -m "feat(graphrag): track self-correction attempts in result metadata"
```

---

### Task 5: Integration test with clinical scenarios

Verify the self-correction loop works end-to-end with realistic clinical queries.

**Files:**
- Test: `tests/graphrag/test_engine_v2.py`

**Step 1: Write integration test**

```python
class TestSelfCorrectionIntegration:
    """End-to-end tests for the self-correction pipeline."""

    @patch("open_medicine.graphrag.reasoning.engine_v2.embed_query")
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_correction_does_not_run_when_results_sufficient(self, mock_link, mock_embed):
        """If Layer 1 returns good results, no correction is attempted."""
        mock_embed.side_effect = Exception("no key")
        entity = type("E", (), {"node_id": "drug:carvedilol", "entity_type": "Drug"})()
        mock_link.return_value = entity

        conn = MagicMock()
        conn.execute_read.return_value = [
            {
                "entity_id": "disease:hfref",
                "entity_name": "HFrEF",
                "entity_type": "Disease",
                "strength": "strong_for",
                "evidence_quality": "high",
                "conditions": None,
                "starting_dose": "3.125mg",
                "target_dose": "25mg",
                "max_dose": "25mg",
                "frequency": "BID",
                "severity": None,
                "mechanism": None,
                "clinical_effect": None,
                "threshold_alert": None,
                "threshold_stop": None,
                "reason": None,
            }
        ]

        engine = ReasoningEngine(conn)
        q = ClinicalQuery(intent="dosing", concepts=["Carvedilol"])
        result = engine.query(q)

        assert len(result.semantic_matches) >= 1
        assert result.corrections_attempted == []

    @patch("open_medicine.graphrag.reasoning.engine_v2.embed_query")
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_max_correction_attempts_bounded(self, mock_link, mock_embed):
        """Correction strategies are bounded — no infinite loops."""
        mock_embed.side_effect = Exception("no key")
        mock_link.return_value = None

        conn = MagicMock()
        conn.execute_read.return_value = []

        engine = ReasoningEngine(conn)
        q = ClinicalQuery(intent="contraindication", concepts=["TotallyFakeDrug"])
        result = engine.query(q)

        # Should attempt corrections but not loop forever
        assert len(result.corrections_attempted) <= 3
        # Should still have hints for the user
        assert result.confidence == "low"
```

**Step 2: Run tests**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py::TestSelfCorrectionIntegration -v`
Expected: PASS

**Step 3: Run full test suite**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py -v`
Expected: All pass (existing + new)

**Step 4: Commit**

```bash
git add tests/graphrag/test_engine_v2.py
git commit -m "test(graphrag): add self-correction integration tests"
```

---

## Summary

| Task | What | Tests |
|------|------|-------|
| 1 | Result quality evaluator (`_needs_correction`) | 5 unit tests |
| 2 | Class-level escalation strategy | 1 integration test |
| 3 | Concept decomposition strategy | 3 unit tests |
| 4 | Correction metadata tracking | 1 integration test |
| 5 | End-to-end integration validation | 2 integration tests |

**Total: 5 tasks, 12 new tests, ~80 lines of production code.**

The correction strategies are additive — they don't change existing behavior, only fire when initial retrieval is insufficient. Existing tests should pass without modification.

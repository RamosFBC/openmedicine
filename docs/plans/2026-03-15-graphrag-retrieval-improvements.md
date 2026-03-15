# GraphRAG Retrieval Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a 4-layer fallback chain to the ReasoningEngine v2 — multi-hop expansion, vector fallback, and hint generation — to improve retrieval resilience from ~60% to ~90% of 2025/2026 GraphRAG best practices.

**Architecture:** Layered fallback inside the existing intent-routed engine. Layer 1 (direct graph, current) → Layer 2 (DrugClass↔member + Disease↔stage expansion) → Layer 3 (vector search over EvidenceChunks → entity traversal) → Layer 4 (empty result with fuzzy hints). Each layer only activates when the previous returns insufficient results.

**Tech Stack:** Python 3.10+, Pydantic v2, Neo4j, Voyage AI embeddings, pytest

**Design doc:** `docs/plans/2026-03-15-graphrag-retrieval-improvements-design.md`

---

### Task 1: Add new fields to types_v2.py

**Files:**
- Modify: `src/open_medicine/graphrag/reasoning/types_v2.py`
- Test: `tests/graphrag/test_engine_v2.py`

**Step 1: Write failing tests for the new fields**

Add to the bottom of `tests/graphrag/test_engine_v2.py`:

```python
class TestNewTypeFields:
    def test_semantic_match_source_layer_default(self):
        m = SemanticMatch(
            entity_id="d1", entity_name="D", entity_type="Drug",
            edge_type="INDICATED_FOR", strength="strong_for", evidence_quality="high",
        )
        assert m.source_layer == "direct"

    def test_semantic_match_source_layer_custom(self):
        m = SemanticMatch(
            entity_id="d1", entity_name="D", entity_type="Drug",
            edge_type="INDICATED_FOR", strength="strong_for", evidence_quality="high",
            source_layer="expanded",
        )
        assert m.source_layer == "expanded"

    def test_graphrag_result_new_fields_default(self):
        r = GraphRAGResult()
        assert r.retrieval_layers_used == []
        assert r.hints == []

    def test_graphrag_result_hints_populated(self):
        r = GraphRAGResult(hints=["Try intent='dosing'"])
        assert len(r.hints) == 1

    def test_clinical_query_min_threshold_default(self):
        q = ClinicalQuery(intent="treatment_selection", concepts=["X"])
        assert q.min_results_threshold == 1

    def test_clinical_query_min_threshold_custom(self):
        q = ClinicalQuery(intent="treatment_selection", concepts=["X"], min_results_threshold=5)
        assert q.min_results_threshold == 5
```

Also add `GraphRAGResult` to the test file's imports from `types_v2`.

**Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py::TestNewTypeFields -v`
Expected: FAIL — `source_layer` field doesn't exist yet

**Step 3: Add the fields to types_v2.py**

In `SemanticMatch` (after `missing_variables` field, line 53), add:

```python
    source_layer: str = Field(
        default="direct",
        description="Retrieval layer: direct, expanded, or vector",
    )
```

In `ClinicalQuery` (after `include_evidence` field, line 33), add:

```python
    min_results_threshold: int = Field(
        default=1,
        description="Minimum results before triggering fallback layers",
    )
```

In `GraphRAGResult` (after `missing_variables` field, line 92), add:

```python
    retrieval_layers_used: list[str] = Field(
        default_factory=list,
        description="Layers that contributed results: direct, expanded, vector",
    )
    hints: list[str] = Field(
        default_factory=list,
        description="Reformulation suggestions when results are empty",
    )
```

**Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py -v`
Expected: ALL PASS (new tests + all existing tests)

**Step 5: Commit**

```bash
git add src/open_medicine/graphrag/reasoning/types_v2.py tests/graphrag/test_engine_v2.py
git commit -m "feat(graphrag): add source_layer, hints, retrieval_layers_used to types_v2"
```

---

### Task 2: Add fuzzy_match utility to terminology

**Files:**
- Modify: `src/open_medicine/graphrag/terminology/__init__.py`
- Test: `tests/graphrag/test_terminology_fuzzy.py` (create)

**Step 1: Write failing tests**

Create `tests/graphrag/test_terminology_fuzzy.py`:

```python
from open_medicine.graphrag.terminology import fuzzy_match


class TestFuzzyMatch:
    def test_exact_match(self):
        results = fuzzy_match("Carvedilol")
        assert any(r[0] == "Carvedilol" for r in results)

    def test_prefix_match(self):
        results = fuzzy_match("Carve")
        assert any("Carvedilol" in r[0] for r in results)

    def test_substring_match(self):
        results = fuzzy_match("valsartan")
        # Should find Sacubitril/Valsartan or Valsartan
        assert len(results) > 0

    def test_case_insensitive(self):
        results = fuzzy_match("hfref")
        assert any("HFrEF" in r[0] for r in results)

    def test_no_match(self):
        results = fuzzy_match("xyznonexistent123")
        assert results == []

    def test_returns_tuples_of_name_and_type(self):
        results = fuzzy_match("Carvedilol")
        assert len(results) > 0
        name, entity_type = results[0]
        assert isinstance(name, str)
        assert entity_type in ("drug", "drug_class", "disease", "lab", "procedure", "device", "symptom")

    def test_max_results(self):
        results = fuzzy_match("heart", max_results=3)
        assert len(results) <= 3
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/graphrag/test_terminology_fuzzy.py -v`
Expected: FAIL — `fuzzy_match` doesn't exist

**Step 3: Implement fuzzy_match**

Add to `src/open_medicine/graphrag/terminology/__init__.py`:

```python
_FILE_TO_TYPE: dict[str, str] = {
    "drugs": "drug",
    "drug_classes": "drug_class",
    "diseases": "disease",
    "labs": "lab",
    "procedures": "procedure",
    "devices": "device",
    "symptoms": "symptom",
}


def fuzzy_match(query: str, max_results: int = 5) -> list[tuple[str, str]]:
    """Find terminology entries matching a query by prefix or substring.

    Returns list of (canonical_name, entity_type) tuples, sorted by match quality:
    prefix matches first, then substring matches.
    """
    q = query.lower()
    prefix_matches: list[tuple[str, str]] = []
    substring_matches: list[tuple[str, str]] = []

    for file_name, entity_type in _FILE_TO_TYPE.items():
        data = load_terminology(file_name)
        for canonical, entry in data.items():
            names = [canonical] + entry.get("aliases", [])
            for name in names:
                nl = name.lower()
                if nl.startswith(q):
                    prefix_matches.append((canonical, entity_type))
                    break
                if q in nl:
                    substring_matches.append((canonical, entity_type))
                    break

    # Deduplicate preserving order
    seen: set[str] = set()
    results: list[tuple[str, str]] = []
    for item in prefix_matches + substring_matches:
        key = f"{item[0]}:{item[1]}"
        if key not in seen:
            seen.add(key)
            results.append(item)

    return results[:max_results]
```

**Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/graphrag/test_terminology_fuzzy.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/open_medicine/graphrag/terminology/__init__.py tests/graphrag/test_terminology_fuzzy.py
git commit -m "feat(graphrag): add fuzzy_match to terminology for hint generation"
```

---

### Task 3: Add vector+entity Cypher query to queries_v2.py

**Files:**
- Modify: `src/open_medicine/graphrag/graph/queries_v2.py`
- Test: `tests/graphrag/test_queries_v2.py` (create)

**Step 1: Write failing test**

Create `tests/graphrag/test_queries_v2.py`:

```python
from open_medicine.graphrag.graph.queries_v2 import ReasoningQueries


class TestVectorEntitySearch:
    def test_returns_cypher_and_params(self):
        embedding = [0.1] * 10
        cypher, params = ReasoningQueries.vector_entity_search(embedding, rec_type="treatment_selection")
        assert "db.index.vector.queryNodes" in cypher
        assert "RECOMMENDS" in cypher
        assert params["embedding"] == embedding
        assert params["rec_type"] == "treatment_selection"
        assert params["limit"] == 10

    def test_custom_limit(self):
        embedding = [0.1] * 10
        cypher, params = ReasoningQueries.vector_entity_search(embedding, rec_type="dosing", limit=5)
        assert params["limit"] == 5

    def test_no_rec_type_filter(self):
        embedding = [0.1] * 10
        cypher, params = ReasoningQueries.vector_entity_search(embedding)
        assert "rec.type" not in cypher
        assert "rec_type" not in params
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/graphrag/test_queries_v2.py -v`
Expected: FAIL — `vector_entity_search` doesn't exist

**Step 3: Implement the query**

Add to `ReasoningQueries` class in `src/open_medicine/graphrag/graph/queries_v2.py`, after the existing `vector_search` method:

```python
    @staticmethod
    def vector_entity_search(
        query_embedding: list[float],
        rec_type: str | None = None,
        limit: int = 10,
    ) -> CypherStatement:
        """Vector search → traverse to connected clinical entities.

        Finds EvidenceChunks by embedding similarity, then follows
        SOURCED_FROM and RECOMMENDS edges to return the entities
        (drugs, diseases, etc.) with their recommendation metadata.
        """
        cypher = (
            "CALL db.index.vector.queryNodes('evidence_embedding', $limit, $embedding) "
            "YIELD node, score "
            "MATCH (rec:Recommendation)-[:SOURCED_FROM]->(node) "
            "MATCH (rec)-[:RECOMMENDS]->(entity) "
        )
        params: dict = {"embedding": query_embedding, "limit": limit}

        if rec_type:
            cypher += "WHERE rec.type = $rec_type "
            params["rec_type"] = rec_type

        cypher += (
            "RETURN DISTINCT labels(entity)[0] AS entity_type, "
            "entity.id AS entity_id, entity.name AS entity_name, "
            "rec.strength AS strength, rec.evidence_quality AS evidence_quality, "
            "rec.conditions_json AS conditions, score "
            "ORDER BY score DESC"
        )
        return (cypher, params)
```

**Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/graphrag/test_queries_v2.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/open_medicine/graphrag/graph/queries_v2.py tests/graphrag/test_queries_v2.py
git commit -m "feat(graphrag): add vector_entity_search query for Layer 3 fallback"
```

---

### Task 4: Implement Layer 2 — multi-hop expansion in engine_v2.py

**Files:**
- Modify: `src/open_medicine/graphrag/reasoning/engine_v2.py`
- Test: `tests/graphrag/test_engine_v2.py`

**Step 1: Write failing tests**

Add to `tests/graphrag/test_engine_v2.py`:

```python
class TestLayer2Expansion:
    """Layer 2: DrugClass↔member and Disease↔stage expansion."""

    @patch("open_medicine.graphrag.reasoning.engine_v2.get_drug_class_members")
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_treatment_expands_disease_to_parent(self, mock_link, mock_members):
        """If HFrEF returns 0 results, expand to parent Heart Failure."""
        # Layer 1: HFrEF returns nothing
        disease = MagicMock()
        disease.node_id = "snomed:703272007"
        disease.node_label = "Disease"
        disease.entity_type = "disease"

        parent = MagicMock()
        parent.node_id = "snomed:84114007"
        parent.node_label = "Disease"
        parent.entity_type = "disease"

        mock_link.side_effect = [disease, parent]  # first call: HFrEF, second: Heart Failure
        mock_members.return_value = []

        engine, conn = _make_engine()
        # Layer 1 returns empty, Layer 2 (parent disease) returns result
        conn.execute_read.side_effect = [
            [],  # Layer 1: find_treatments for HFrEF
            [],  # Layer 2: find_stage_parents (Cypher query)
            [    # Layer 2: find_treatments for parent
                {
                    "entity_id": "drug_x", "entity_name": "DrugX",
                    "entity_type": "Drug", "strength": "strong_for",
                    "evidence_quality": "high", "conditions": None,
                }
            ],
        ]
        q = ClinicalQuery(
            intent="treatment_selection", concepts=["HFrEF"],
            include_evidence=False, min_results_threshold=1,
        )
        result = engine.query(q)
        assert len(result.semantic_matches) >= 1
        assert "expanded" in result.retrieval_layers_used

    @patch("open_medicine.graphrag.reasoning.engine_v2.get_drug_class_members")
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_monitoring_expands_class_to_members(self, mock_link, mock_members):
        """If MRA class has no MONITORED_BY, expand to member drugs."""
        drug_class = MagicMock()
        drug_class.node_id = "atc:C03DA"
        drug_class.node_label = "DrugClass"
        drug_class.entity_type = "drug_class"

        member_drug = MagicMock()
        member_drug.node_id = "rxnorm:35827"
        member_drug.node_label = "Drug"
        member_drug.entity_type = "drug"

        # link_entity: first call for "MRA" as drug → None, then reused for member
        mock_link.side_effect = [None, member_drug]
        mock_members.return_value = ["Spironolactone"]

        engine, conn = _make_engine()
        conn.execute_read.side_effect = [
            [],  # Layer 1: monitoring for MRA (not a drug)
            [    # Layer 2: monitoring for Spironolactone
                {"lab_id": "loinc:2823-3", "lab_name": "Potassium"}
            ],
        ]
        q = ClinicalQuery(
            intent="monitoring", concepts=["MRA"],
            include_evidence=False, min_results_threshold=1,
        )
        result = engine.query(q)
        assert len(result.semantic_matches) >= 1
        assert result.semantic_matches[0].source_layer == "expanded"

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_no_expansion_when_layer1_sufficient(self, mock_link):
        """Layer 2 should NOT run if Layer 1 meets threshold."""
        linked = MagicMock()
        linked.node_id = "disease_hfref"
        mock_link.return_value = linked

        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {
                "entity_id": "drug_1", "entity_name": "Drug1",
                "entity_type": "Drug", "strength": "strong_for",
                "evidence_quality": "high", "conditions": None,
            }
        ]
        q = ClinicalQuery(
            intent="treatment_selection", concepts=["HFrEF"],
            include_evidence=False, min_results_threshold=1,
        )
        result = engine.query(q)
        # Only 1 execute_read call (Layer 1), no expansion
        assert conn.execute_read.call_count == 1
        assert "expanded" not in result.retrieval_layers_used

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_deduplication_across_layers(self, mock_link):
        """Same entity from Layer 1 and Layer 2 — keep Layer 1 version."""
        linked = MagicMock()
        linked.node_id = "disease_hfref"
        linked.entity_type = "disease"
        mock_link.return_value = linked

        engine, conn = _make_engine()
        same_row = {
            "entity_id": "drug_1", "entity_name": "Drug1",
            "entity_type": "Drug", "strength": "strong_for",
            "evidence_quality": "high", "conditions": None,
        }
        conn.execute_read.return_value = [same_row]

        # Simulate: Layer 1 returns 1 result, Layer 2 returns same entity
        q = ClinicalQuery(
            intent="treatment_selection", concepts=["HFrEF"],
            include_evidence=False, min_results_threshold=1,
        )
        result = engine.query(q)
        # Should have exactly 1, not 2
        drug1_matches = [m for m in result.semantic_matches if m.entity_id == "drug_1"]
        assert len(drug1_matches) == 1
        assert drug1_matches[0].source_layer == "direct"
```

Also add this import at the top of the test file:

```python
from open_medicine.graphrag.ingestion.linker_v2 import get_drug_class_members
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py::TestLayer2Expansion -v`
Expected: FAIL — engine doesn't have expansion logic yet

**Step 3: Implement Layer 2 in engine_v2.py**

This is the biggest change. The approach:

1. Add `get_drug_class_members` import at the top of engine_v2.py:
   ```python
   from open_medicine.graphrag.ingestion.linker_v2 import link_entity, get_drug_class_members
   ```

2. Add a new Cypher query for disease parent traversal to `ReasoningQueries` in `queries_v2.py`:
   ```python
   @staticmethod
   def find_disease_parents(disease_id: str) -> CypherStatement:
       """Find parent diseases via STAGE_OF."""
       return (
           "MATCH (child:Disease {id: $did})-[:STAGE_OF]->(parent:Disease) "
           "RETURN parent.id AS parent_id, parent.name AS parent_name",
           {"did": disease_id},
       )

   @staticmethod
   def find_disease_children(disease_id: str) -> CypherStatement:
       """Find child diseases (stages/subtypes) via STAGE_OF."""
       return (
           "MATCH (child:Disease)-[:STAGE_OF]->(parent:Disease {id: $did}) "
           "RETURN child.id AS child_id, child.name AS child_name",
           {"did": disease_id},
       )
   ```

3. Refactor each intent handler in engine_v2.py to follow this pattern:
   - Run Layer 1 (current code)
   - Check `len(matches) < q.min_results_threshold`
   - If below threshold, run expansion and tag results with `source_layer="expanded"`
   - Deduplicate by `(entity_id, edge_type)`
   - Track which layers contributed in `retrieval_layers_used`

4. Add a `_deduplicate` helper:
   ```python
   @staticmethod
   def _deduplicate(matches: list[SemanticMatch]) -> list[SemanticMatch]:
       """Deduplicate by (entity_id, edge_type), keeping first occurrence."""
       seen: set[tuple[str, str]] = set()
       result: list[SemanticMatch] = []
       for m in matches:
           key = (m.entity_id, m.edge_type)
           if key not in seen:
               seen.add(key)
               result.append(m)
       return result
   ```

5. Add expansion methods:
   ```python
   def _expand_drug_class_members(
       self, class_name: str, query_fn, **kwargs
   ) -> list[SemanticMatch]:
       """Expand a drug class to its member drugs and run query_fn on each."""
       members = get_drug_class_members(class_name)
       matches: list[SemanticMatch] = []
       for member_name in members:
           entity = link_entity(member_name, "drug")
           if entity is None:
               continue
           # Call the appropriate query with the member's ID
           rows = query_fn(entity, **kwargs)
           for row in rows:
               m = self._row_to_match(row, **kwargs)
               if m:
                   m.source_layer = "expanded"
                   matches.append(m)
       return matches

   def _expand_disease_hierarchy(
       self, disease_id: str, query_fn, direction: str = "up", **kwargs
   ) -> list[SemanticMatch]:
       """Expand disease to parent/children and run query_fn on each."""
       if direction == "up":
           cypher, params = ReasoningQueries.find_disease_parents(disease_id)
       else:
           cypher, params = ReasoningQueries.find_disease_children(disease_id)
       rows = self._conn.execute_read(cypher, params)

       matches: list[SemanticMatch] = []
       for row in rows:
           related_id = row.get("parent_id") or row.get("child_id")
           if not related_id:
               continue
           expanded_rows = query_fn(related_id, **kwargs)
           for er in expanded_rows:
               m = self._row_to_match(er, **kwargs)
               if m:
                   m.source_layer = "expanded"
                   matches.append(m)
       return matches
   ```

6. Update `_build_result` to populate `retrieval_layers_used`:
   ```python
   layers = list({m.source_layer for m in semantic_matches})
   # ... existing code ...
   return GraphRAGResult(
       source="graph_traversal",
       semantic_matches=semantic_matches,
       evidence=evidence,
       confidence=confidence,
       missing_variables=list(set(all_missing)),
       retrieval_layers_used=layers,
   )
   ```

**Implementation note:** The exact refactoring of each intent handler is the bulk of the work. Each handler (`_query_treatments`, `_query_contraindications`, `_query_monitoring`, `_query_dosing`, `_query_interactions`) follows the same pattern: run current code → check threshold → expand → deduplicate. Factor the shared logic into a wrapper method rather than duplicating the check in every handler.

**Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py -v`
Expected: ALL PASS (new tests + all existing tests)

**Step 5: Commit**

```bash
git add src/open_medicine/graphrag/reasoning/engine_v2.py src/open_medicine/graphrag/graph/queries_v2.py tests/graphrag/test_engine_v2.py
git commit -m "feat(graphrag): add Layer 2 multi-hop expansion to ReasoningEngine"
```

---

### Task 5: Implement Layer 3 — vector fallback in engine_v2.py

**Files:**
- Modify: `src/open_medicine/graphrag/reasoning/engine_v2.py`
- Test: `tests/graphrag/test_engine_v2.py`

**Step 1: Write failing tests**

Add to `tests/graphrag/test_engine_v2.py`:

```python
class TestLayer3VectorFallback:
    """Layer 3: Vector search over EvidenceChunks when Layers 1+2 return nothing."""

    @patch("open_medicine.graphrag.reasoning.engine_v2.embed_query")
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_vector_fallback_when_graph_empty(self, mock_link, mock_embed):
        """When Layers 1+2 return 0, try vector search."""
        mock_link.return_value = None  # Entity not found → no Layer 1/2 results
        mock_embed.return_value = [0.1] * 1024

        engine, conn = _make_engine()
        # Vector search returns entities via chunk traversal
        conn.execute_read.return_value = [
            {
                "entity_id": "drug_1", "entity_name": "SomeDrug",
                "entity_type": "Drug", "strength": "strong_for",
                "evidence_quality": "high", "conditions": None,
                "score": 0.92,
            }
        ]
        q = ClinicalQuery(
            intent="treatment_selection", concepts=["SomeRareCondition"],
            include_evidence=False,
        )
        result = engine.query(q)
        assert len(result.semantic_matches) >= 1
        assert result.semantic_matches[0].source_layer == "vector"
        assert "vector" in result.retrieval_layers_used

    @patch("open_medicine.graphrag.reasoning.engine_v2.embed_query")
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_vector_fallback_skipped_when_layer1_has_results(self, mock_link, mock_embed):
        """Vector fallback should NOT run if Layer 1 has results."""
        linked = MagicMock()
        linked.node_id = "disease_hfref"
        mock_link.return_value = linked

        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {
                "entity_id": "drug_1", "entity_name": "Drug1",
                "entity_type": "Drug", "strength": "strong_for",
                "evidence_quality": "high", "conditions": None,
            }
        ]
        q = ClinicalQuery(
            intent="treatment_selection", concepts=["HFrEF"],
            include_evidence=False,
        )
        result = engine.query(q)
        mock_embed.assert_not_called()
        assert "vector" not in result.retrieval_layers_used

    @patch("open_medicine.graphrag.reasoning.engine_v2.embed_query", side_effect=Exception("No API key"))
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity", return_value=None)
    def test_vector_fallback_graceful_on_embed_error(self, mock_link, mock_embed):
        """If embedding fails (no API key), skip Layer 3 gracefully."""
        engine, conn = _make_engine()
        q = ClinicalQuery(
            intent="treatment_selection", concepts=["Unknown"],
            include_evidence=False,
        )
        result = engine.query(q)
        # Should not crash, just return empty
        assert result.confidence == "low"
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py::TestLayer3VectorFallback -v`
Expected: FAIL — no vector fallback logic

**Step 3: Implement Layer 3**

In `engine_v2.py`:

1. Add import at the top:
   ```python
   from open_medicine.graphrag.ingestion.embeddings import embed_query
   ```

2. Add the vector fallback method:
   ```python
   # Intent → rec_type mapping for vector search filtering
   _INTENT_TO_REC_TYPE = {
       "treatment_selection": "treatment_selection",
       "contraindication": "contraindication",
       "interaction": "interaction",
       "dosing": "dosing",
       "monitoring": "monitoring",
   }

   def _vector_fallback(self, q: ClinicalQuery) -> list[SemanticMatch]:
       """Layer 3: Vector search over EvidenceChunks → entity traversal."""
       try:
           query_text = f"{q.intent} {' '.join(q.concepts)}"
           embedding = embed_query(query_text)
       except Exception:
           logger.debug("Vector fallback skipped: embedding failed")
           return []

       rec_type = _INTENT_TO_REC_TYPE.get(q.intent)
       cypher, params = ReasoningQueries.vector_entity_search(
           embedding, rec_type=rec_type, limit=10
       )
       rows = self._conn.execute_read(cypher, params)

       matches: list[SemanticMatch] = []
       for row in rows:
           matches.append(
               SemanticMatch(
                   entity_id=row.get("entity_id", ""),
                   entity_name=row.get("entity_name", ""),
                   entity_type=row.get("entity_type", ""),
                   edge_type=self._infer_edge_type(q.intent),
                   strength=row.get("strength", ""),
                   evidence_quality=row.get("evidence_quality", ""),
                   conditions_json=row.get("conditions"),
                   source_layer="vector",
               )
           )
       return matches

   @staticmethod
   def _infer_edge_type(intent: str) -> str:
       """Map intent to the expected semantic edge type."""
       return {
           "treatment_selection": "INDICATED_FOR",
           "contraindication": "CONTRAINDICATED_IN",
           "interaction": "INTERACTS_WITH",
           "dosing": "DOSED_FOR",
           "monitoring": "MONITORED_BY",
       }.get(intent, "RECOMMENDS")
   ```

3. Wire it into the fallback chain — after Layer 2, if still 0 results:
   ```python
   if len(matches) == 0:
       vector_matches = self._vector_fallback(q)
       matches.extend(vector_matches)
   ```

4. Add `import logging` and `logger = logging.getLogger(__name__)` at module level.

**Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/open_medicine/graphrag/reasoning/engine_v2.py tests/graphrag/test_engine_v2.py
git commit -m "feat(graphrag): add Layer 3 vector fallback to ReasoningEngine"
```

---

### Task 6: Implement Layer 4 — hint generation in engine_v2.py

**Files:**
- Modify: `src/open_medicine/graphrag/reasoning/engine_v2.py`
- Test: `tests/graphrag/test_engine_v2.py`

**Step 1: Write failing tests**

Add to `tests/graphrag/test_engine_v2.py`:

```python
class TestLayer4Hints:
    """Layer 4: Actionable hints when all layers return nothing."""

    @patch("open_medicine.graphrag.reasoning.engine_v2.embed_query", side_effect=Exception("skip"))
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity", return_value=None)
    def test_unknown_concept_suggests_similar(self, mock_link, mock_embed):
        engine, conn = _make_engine()
        q = ClinicalQuery(
            intent="treatment_selection", concepts=["Carvedilo"],  # typo
            include_evidence=False,
        )
        result = engine.query(q)
        assert len(result.hints) > 0
        assert any("Carvedilol" in h for h in result.hints)

    @patch("open_medicine.graphrag.reasoning.engine_v2.embed_query", side_effect=Exception("skip"))
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity", return_value=None)
    def test_unsupported_intent_suggests_alternatives(self, mock_link, mock_embed):
        engine, conn = _make_engine()
        q = ClinicalQuery(
            intent="surgery_planning", concepts=["CABG"],
            include_evidence=False,
        )
        result = engine.query(q)
        assert any("treatment_selection" in h for h in result.hints)

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_no_hints_when_results_exist(self, mock_link):
        linked = MagicMock()
        linked.node_id = "disease_hfref"
        mock_link.return_value = linked

        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {
                "entity_id": "drug_1", "entity_name": "Drug1",
                "entity_type": "Drug", "strength": "strong_for",
                "evidence_quality": "high", "conditions": None,
            }
        ]
        q = ClinicalQuery(
            intent="treatment_selection", concepts=["HFrEF"],
            include_evidence=False,
        )
        result = engine.query(q)
        assert result.hints == []
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py::TestLayer4Hints -v`
Expected: FAIL — no hints logic

**Step 3: Implement hint generation**

Add to `engine_v2.py`:

```python
from open_medicine.graphrag.terminology import fuzzy_match

def _generate_hints(self, q: ClinicalQuery) -> list[str]:
    """Generate actionable reformulation hints."""
    hints: list[str] = []

    # Hint 1: unsupported intent
    if q.intent not in _INTENT_TO_QUERY:
        supported = ", ".join(sorted(_INTENT_TO_QUERY.keys()))
        hints.append(
            f"Intent '{q.intent}' is not directly routed. "
            f"Supported intents: {supported}"
        )

    # Hint 2: concept not found — suggest similar
    for concept in q.concepts:
        found = False
        for etype in ("drug", "drug_class", "disease", "lab", "procedure", "device", "symptom"):
            entity = link_entity(concept, etype)
            if entity and entity.canonical_name.lower() != concept.lower():
                # Found via alias or case mismatch — not truly missing
                found = True
                break
            if entity:
                found = True
                break
        if not found:
            similar = fuzzy_match(concept, max_results=3)
            if similar:
                suggestions = ", ".join(f"{name} ({etype})" for name, etype in similar)
                hints.append(f"Concept '{concept}' not in terminology. Similar: {suggestions}")
            else:
                hints.append(f"Concept '{concept}' not found in terminology.")

    return hints
```

Wire into `_build_result` — only when 0 semantic matches:
```python
hints: list[str] = []
if not semantic_matches:
    hints = self._generate_hints(q)

return GraphRAGResult(
    # ... existing fields ...
    hints=hints,
)
```

**Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/open_medicine/graphrag/reasoning/engine_v2.py tests/graphrag/test_engine_v2.py
git commit -m "feat(graphrag): add Layer 4 hint generation to ReasoningEngine"
```

---

### Task 7: Update sort order to respect source_layer

**Files:**
- Modify: `src/open_medicine/graphrag/reasoning/engine_v2.py`
- Test: `tests/graphrag/test_engine_v2.py`

**Step 1: Write failing test**

Add to `tests/graphrag/test_engine_v2.py`:

```python
class TestSourceLayerSorting:
    def _make_match(self, source_layer, strength="strong_for", conditions_met=True):
        return SemanticMatch(
            entity_id=f"id_{source_layer}", entity_name=f"Name_{source_layer}",
            entity_type="Drug", edge_type="INDICATED_FOR",
            strength=strength, evidence_quality="high",
            conditions_met=conditions_met, source_layer=source_layer,
        )

    def test_direct_ranks_before_expanded(self):
        engine, _ = _make_engine()
        matches = [
            self._make_match("expanded"),
            self._make_match("direct"),
        ]
        q = ClinicalQuery(intent="treatment_selection", concepts=["X"])
        result = engine._build_result(matches, [], q)
        assert result.semantic_matches[0].source_layer == "direct"
        assert result.semantic_matches[1].source_layer == "expanded"

    def test_expanded_ranks_before_vector(self):
        engine, _ = _make_engine()
        matches = [
            self._make_match("vector"),
            self._make_match("expanded"),
        ]
        q = ClinicalQuery(intent="treatment_selection", concepts=["X"])
        result = engine._build_result(matches, [], q)
        assert result.semantic_matches[0].source_layer == "expanded"
        assert result.semantic_matches[1].source_layer == "vector"

    def test_full_sort_order(self):
        engine, _ = _make_engine()
        matches = [
            self._make_match("vector", "weak_for", conditions_met=False),
            self._make_match("direct", "moderate_for", conditions_met=True),
            self._make_match("expanded", "strong_for", conditions_met=True),
            self._make_match("direct", "strong_for", conditions_met=True),
        ]
        q = ClinicalQuery(intent="treatment_selection", concepts=["X"])
        result = engine._build_result(matches, [], q)
        layers = [m.source_layer for m in result.semantic_matches]
        # direct+met first (sorted by strength), then expanded+met, then vector+unmet
        assert layers[0] == "direct"
        assert layers[-1] == "vector"
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py::TestSourceLayerSorting -v`
Expected: FAIL — sort doesn't consider source_layer

**Step 3: Update the sort key in _build_result**

In `engine_v2.py`, add a layer priority map:

```python
_LAYER_RANK = {"direct": 0, "expanded": 1, "vector": 2}
```

Update the sort in `_build_result`:

```python
semantic_matches.sort(
    key=lambda m: (
        _LAYER_RANK.get(m.source_layer, 99),
        not m.conditions_met,
        STRENGTH_RANK.get(m.strength, 99),
    )
)
```

**Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/open_medicine/graphrag/reasoning/engine_v2.py tests/graphrag/test_engine_v2.py
git commit -m "feat(graphrag): sort results by source_layer priority (direct > expanded > vector)"
```

---

### Task 8: Add `embed` CLI command to ingest_v2.py

**Files:**
- Modify: `src/open_medicine/graphrag/ingest_v2.py`
- Test: manual CLI test (embedding requires API key)

**Step 1: Implement the embed command**

In `ingest_v2.py`, add the `embed_chunks` function:

```python
def embed_chunks(conn: GraphConnection) -> int:
    """Generate embeddings for all EvidenceChunks that don't have them."""
    import os
    api_key = os.environ.get("VOYAGE_API_KEY", "")
    if not api_key:
        print("VOYAGE_API_KEY not set — skipping embedding generation")
        return 0

    from open_medicine.graphrag.ingestion.embeddings import embed_texts
    from open_medicine.graphrag.graph.queries_v2 import LoaderQueries

    # Fetch chunks without embeddings
    rows = conn.execute_read(
        "MATCH (ec:EvidenceChunk) WHERE ec.embedding IS NULL "
        "RETURN ec.id AS id, ec.text AS text"
    )
    if not rows:
        print("All chunks already have embeddings")
        return 0

    chunk_ids = [r["id"] for r in rows]
    texts = [r["text"] for r in rows]
    print(f"Embedding {len(texts)} chunks...")

    embeddings = embed_texts(texts, api_key=api_key)

    for chunk_id, embedding in zip(chunk_ids, embeddings):
        cypher, params = LoaderQueries.set_embedding(chunk_id, embedding)
        conn.execute_write(cypher, params)

    print(f"Embedded {len(embeddings)} chunks")
    return len(embeddings)
```

Add the CLI subcommand in `main()`:

```python
# Embed command
sub.add_parser("embed", help="Generate embeddings for EvidenceChunks (requires VOYAGE_API_KEY)")
```

Add the dispatch (inside the `with GraphConnection` block):

```python
elif args.command == "embed":
    embed_chunks(conn)
```

**Step 2: Run existing tests to verify no breakage**

Run: `uv run python -m pytest tests/graphrag/ -v`
Expected: ALL PASS

**Step 3: Commit**

```bash
git add src/open_medicine/graphrag/ingest_v2.py
git commit -m "feat(graphrag): add embed CLI command for EvidenceChunk vector generation"
```

---

### Task 9: Update ingestion pipeline command doc

**Files:**
- Modify: `.claude/commands/ingest-guideline.md`

**Step 1: Add Phase 4.6**

After the Phase 4.5 section (line ~244), add:

```markdown
### Phase 4.6: Generate Embeddings (optional)

If `VOYAGE_API_KEY` is set, generate vector embeddings for evidence chunks:
```bash
uv run python -m open_medicine.graphrag.ingest_v2 embed
```

This enables Layer 3 vector fallback in the ReasoningEngine.
If the API key is not set, this step is skipped — the engine degrades gracefully.
```

**Step 2: Commit**

```bash
git add .claude/commands/ingest-guideline.md
git commit -m "docs: add Phase 4.6 (embed) to ingestion pipeline"
```

---

### Task 10: Run full test suite and verify

**Step 1: Run all graphrag tests**

Run: `uv run python -m pytest tests/graphrag/ -v`
Expected: ALL PASS

**Step 2: Run full project test suite**

Run: `uv run python -m pytest -v`
Expected: ALL PASS (no regressions in calculator/guideline/differential tests)

**Step 3: Final commit if any fixups needed**

Only if tests revealed issues that need fixing.

# GraphRAG Production Quality & Enrichment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the 3 remaining quality gaps (terminology resolution, evidence relevance, edge property enrichment) and create .claude skills for graph creation and maintenance.

**Architecture:** Engine fixes are surgical changes to `engine_v2.py` handler methods. Evidence re-ranking uses existing Voyage AI embeddings stored on EvidenceChunk nodes. Skills are `.claude/commands/` markdown files that orchestrate existing agents and CLI commands.

**Tech Stack:** Python 3.10+, Neo4j, Voyage AI embeddings, Pydantic, pytest

---

## Stream 1: Terminology Resolution Fix

### Task 1.1: Add drug_class fallback to `_query_monitoring`

**Files:**
- Modify: `src/open_medicine/graphrag/reasoning/engine_v2.py:462-468`
- Test: `tests/graphrag/test_engine_v2.py`

**Step 1: Write the failing test**

Add to `tests/graphrag/test_engine_v2.py`:

```python
class TestQueryMonitoring:
    @patch("open_medicine.graphrag.reasoning.engine_v2.get_drug_class_members", return_value=[])
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_drug_class_direct_lookup_before_expansion(self, mock_link, mock_members):
        """When 'MRA' fails as drug, try drug_class directly before expanding."""
        mock_class_entity = MagicMock()
        mock_class_entity.node_id = "class_mra"
        mock_class_entity.node_label = "DrugClass"

        # First call: link_entity("MRA", "drug") -> None
        # Second call: link_entity("MRA", "drug_class") -> mock_class_entity
        mock_link.side_effect = [None, mock_class_entity]

        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {"lab_id": "lab_potassium", "lab_name": "Potassium"}
        ]
        q = ClinicalQuery(intent="monitoring", concepts=["MRA"])
        result = engine.query(q)

        # Should find monitoring via drug_class, NOT go to expansion
        assert len(result.semantic_matches) >= 1
        assert result.semantic_matches[0].entity_name == "Potassium"
        # link_entity should be called twice: ("MRA","drug"), ("MRA","drug_class")
        assert mock_link.call_count == 2
        # expansion should NOT be called since drug_class matched
        mock_members.assert_not_called()
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py::TestQueryMonitoring::test_drug_class_direct_lookup_before_expansion -v`
Expected: FAIL — `_query_monitoring` currently goes straight to `_expand_drug_class_to_monitoring` when drug lookup returns None.

**Step 3: Write minimal implementation**

In `engine_v2.py`, modify `_query_monitoring` (line 462-468). Replace:

```python
        for concept in q.concepts:
            entity = link_entity(concept, "drug")
            if entity is None:
                # Layer 2: concept might be a drug class — expand to members
                expanded = self._expand_drug_class_to_monitoring(concept)
                semantic_matches.extend(expanded)
                continue
```

With:

```python
        for concept in q.concepts:
            entity = link_entity(concept, "drug")
            if entity is None:
                # Try drug_class directly before expanding
                entity = link_entity(concept, "drug_class")
            if entity is None:
                # Layer 2: concept might be a drug class — expand to members
                expanded = self._expand_drug_class_to_monitoring(concept)
                semantic_matches.extend(expanded)
                continue
```

Also update the Cypher call at line 470 to pass `entity_label` since entity might be a DrugClass now:

```python
            cypher, params = ReasoningQueries.find_monitoring(
                entity.node_id, entity_label=entity.node_label
            )
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py::TestQueryMonitoring -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/open_medicine/graphrag/reasoning/engine_v2.py tests/graphrag/test_engine_v2.py
git commit -m "fix(graphrag): add drug_class direct lookup to monitoring handler

Before this change, _query_monitoring only tried link_entity(concept, 'drug').
If that returned None, it went straight to expanding drug class members.
Now it tries link_entity(concept, 'drug_class') first, which resolves
terms like 'MRA' directly without needing per-member expansion."
```

### Task 1.2: Add drug_class fallback to `_query_dosing`

**Files:**
- Modify: `src/open_medicine/graphrag/reasoning/engine_v2.py:402-404`
- Test: `tests/graphrag/test_engine_v2.py`

**Step 1: Write the failing test**

```python
class TestQueryDosing:
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_drug_class_fallback(self, mock_link):
        """When drug lookup fails, try drug_class before returning empty."""
        mock_class_entity = MagicMock()
        mock_class_entity.node_id = "class_arni"
        mock_class_entity.node_label = "DrugClass"

        # drug -> None, drug_class -> match
        mock_link.side_effect = [None, mock_class_entity]

        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {"disease_id": "disease_hfref", "disease": "HFrEF", "conditions": None}
        ]
        q = ClinicalQuery(intent="dosing", concepts=["ARNi"])
        result = engine.query(q)

        assert len(result.semantic_matches) >= 1
        assert mock_link.call_count == 2
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py::TestQueryDosing::test_drug_class_fallback -v`
Expected: FAIL — `_query_dosing` returns empty result when drug lookup fails.

**Step 3: Write minimal implementation**

In `engine_v2.py`, modify `_query_dosing` (line 402-404). Replace:

```python
        entity = link_entity(drug_name, "drug")
        if entity is None:
            return self._empty_result()
```

With:

```python
        entity = link_entity(drug_name, "drug")
        if entity is None:
            entity = link_entity(drug_name, "drug_class")
        if entity is None:
            return self._empty_result()
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py::TestQueryDosing -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py -v`
Expected: All tests pass.

**Step 6: Commit**

```bash
git add src/open_medicine/graphrag/reasoning/engine_v2.py tests/graphrag/test_engine_v2.py
git commit -m "fix(graphrag): add drug_class fallback to dosing handler

_query_dosing now tries link_entity(concept, 'drug_class') when
drug lookup returns None, matching the pattern in contraindications
and interactions handlers."
```

---

## Stream 2: Evidence Re-Ranking

### Task 2.1: Add cosine similarity re-ranking to `_fetch_evidence_for_matches`

**Files:**
- Modify: `src/open_medicine/graphrag/reasoning/engine_v2.py:792-821`
- Test: `tests/graphrag/test_engine_v2.py`

**Step 1: Write the failing test**

```python
class TestEvidenceReranking:
    @patch("open_medicine.graphrag.reasoning.engine_v2.embed_query")
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_evidence_ranked_by_relevance(self, mock_link, mock_embed):
        """Evidence should be re-ranked by cosine similarity to the query."""
        mock_embed.return_value = [1.0, 0.0, 0.0]  # query embedding

        engine, conn = _make_engine()

        # Simulate recommendations with evidence, some with embeddings
        conn.execute_read.return_value = [
            {
                "source_text": "Irrelevant iron text",
                "guideline": "AHA",
                "doi": "10.1161/test",
                "section": "Iron",
                "embedding": [0.0, 1.0, 0.0],  # orthogonal to query
            },
            {
                "source_text": "Relevant spironolactone monitoring",
                "guideline": "AHA",
                "doi": "10.1161/test",
                "section": "MRA",
                "embedding": [0.9, 0.1, 0.0],  # similar to query
            },
            {
                "source_text": "Somewhat relevant potassium text",
                "guideline": "AHA",
                "doi": "10.1161/test",
                "section": "Labs",
                "embedding": [0.5, 0.5, 0.0],  # moderately similar
            },
        ]

        matches = [
            SemanticMatch(
                entity_id="lab_potassium",
                entity_name="Potassium",
                entity_type="Lab",
                edge_type="MONITORED_BY",
            )
        ]
        q = ClinicalQuery(
            intent="monitoring",
            concepts=["Spironolactone"],
            include_evidence=True,
        )

        evidence = engine._fetch_evidence_for_matches(matches, q)

        # Should be re-ranked: most relevant first
        assert len(evidence) <= 5  # capped
        assert evidence[0].text == "Relevant spironolactone monitoring"
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py::TestEvidenceReranking::test_evidence_ranked_by_relevance -v`
Expected: FAIL — current implementation returns evidence in traversal order, no re-ranking.

**Step 3: Write minimal implementation**

Modify `_fetch_evidence_for_matches` in `engine_v2.py`. The Cypher query in `ReasoningQueries.find_recommendations_for_entity` needs to also return `embedding` from EvidenceChunk nodes. But since `_fetch_evidence_for_matches` traverses Recommendation→SOURCED_FROM→EvidenceChunk, we need to update the query to include embeddings.

First, add a helper for cosine similarity at the top of the file:

```python
import math

def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
```

Then modify `_fetch_evidence_for_matches`:

```python
    def _fetch_evidence_for_matches(
        self,
        matches: list[SemanticMatch],
        q: ClinicalQuery,
    ) -> list[EvidenceCitation]:
        """Fetch Layer 2 evidence for semantic matches, re-ranked by relevance."""
        evidence: list[EvidenceCitation] = []
        seen_chunks: set[str] = set()

        for match in matches:
            cypher, params = ReasoningQueries.find_recommendations_for_entity(
                match.entity_id, match.entity_type
            )
            rows = self._conn.execute_read(cypher, params)

            for row in rows:
                text = row.get("source_text", "")
                if text and text not in seen_chunks:
                    seen_chunks.add(text)
                    evidence.append(
                        EvidenceCitation(
                            chunk_id="",
                            text=text,
                            guideline_title=row.get("guideline") or "",
                            doi=row.get("doi") or "",
                            section=row.get("section") or "",
                        )
                    )

        # Re-rank by cosine similarity if we have embeddings
        if len(evidence) > 5:
            try:
                api_key = os.environ.get("VOYAGE_API_KEY", "")
                query_text = f"{q.intent} {' '.join(q.concepts)}"
                query_embedding = embed_query(query_text, api_key=api_key)

                # Re-fetch rows with embeddings for scoring
                scored: list[tuple[EvidenceCitation, float]] = []
                for ev in evidence:
                    # Find embedding for this evidence from the rows
                    emb = self._get_chunk_embedding(ev.text)
                    if emb:
                        score = _cosine_similarity(query_embedding, emb)
                        scored.append((ev, score))
                    else:
                        scored.append((ev, 0.0))

                scored.sort(key=lambda x: x[1], reverse=True)
                evidence = [e for e, _ in scored[:5]]
            except Exception:
                logger.debug("Evidence re-ranking failed, returning top 10 by traversal order")
                evidence = evidence[:10]

        return evidence
```

**Wait — this approach is too complex.** The embeddings live on EvidenceChunk nodes in Neo4j, not in the row results. A simpler approach: modify the Cypher query to also fetch the embedding, then score in Python.

Alternative simpler approach — update `_fetch_evidence_for_matches` to:
1. Collect all candidate evidence (existing logic)
2. If > 5 candidates, use a **single** Cypher query to fetch embeddings for those chunks
3. Compute cosine similarity with the query embedding
4. Return top 5

```python
    def _fetch_evidence_for_matches(
        self,
        matches: list[SemanticMatch],
        q: ClinicalQuery,
    ) -> list[EvidenceCitation]:
        """Fetch Layer 2 evidence for semantic matches, re-ranked by relevance."""
        candidates: list[tuple[EvidenceCitation, str]] = []  # (citation, text_for_matching)
        seen_chunks: set[str] = set()

        for match in matches:
            cypher, params = ReasoningQueries.find_recommendations_for_entity(
                match.entity_id, match.entity_type
            )
            rows = self._conn.execute_read(cypher, params)

            for row in rows:
                text = row.get("source_text", "")
                if text and text not in seen_chunks:
                    seen_chunks.add(text)
                    citation = EvidenceCitation(
                        chunk_id="",
                        text=text,
                        guideline_title=row.get("guideline") or "",
                        doi=row.get("doi") or "",
                        section=row.get("section") or "",
                    )
                    candidates.append((citation, text))

        if len(candidates) <= 5:
            return [c for c, _ in candidates]

        # Re-rank using vector similarity
        try:
            api_key = os.environ.get("VOYAGE_API_KEY", "")
            query_text = f"{q.intent} {' '.join(q.concepts)}"
            query_emb = embed_query(query_text, api_key=api_key)

            # Fetch embeddings for candidate texts from Neo4j
            texts = [t for _, t in candidates]
            emb_cypher = """
            MATCH (ec:EvidenceChunk)
            WHERE ec.text IN $texts AND ec.embedding IS NOT NULL
            RETURN ec.text AS text, ec.embedding AS embedding
            """
            emb_rows = self._conn.execute_read(emb_cypher, {"texts": texts})
            text_to_emb = {r["text"]: r["embedding"] for r in emb_rows}

            scored = []
            for citation, text in candidates:
                emb = text_to_emb.get(text)
                if emb:
                    score = _cosine_similarity(query_emb, emb)
                else:
                    score = 0.0
                scored.append((citation, score))

            scored.sort(key=lambda x: x[1], reverse=True)
            return [c for c, _ in scored[:5]]
        except Exception:
            logger.debug("Evidence re-ranking failed, returning first 10 by traversal order")
            return [c for c, _ in candidates[:10]]
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py::TestEvidenceReranking -v`
Expected: PASS

**Step 5: Write edge case test**

```python
    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_evidence_no_reranking_when_few(self, mock_link):
        """When <= 5 evidence citations, skip re-ranking."""
        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {"source_text": "Only one citation", "guideline": "AHA", "doi": "10.1161/test", "section": "X"},
        ]

        matches = [SemanticMatch(entity_id="x", entity_name="X", entity_type="Drug", edge_type="INDICATED_FOR")]
        q = ClinicalQuery(intent="treatment_selection", concepts=["X"], include_evidence=True)

        evidence = engine._fetch_evidence_for_matches(matches, q)
        assert len(evidence) == 1
        # embed_query should NOT be called (no re-ranking needed)
```

**Step 6: Run full test suite**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py -v`
Expected: All pass.

**Step 7: Commit**

```bash
git add src/open_medicine/graphrag/reasoning/engine_v2.py tests/graphrag/test_engine_v2.py
git commit -m "feat(graphrag): add evidence re-ranking by cosine similarity

When evidence candidates exceed 5, uses Voyage AI embeddings stored
on EvidenceChunk nodes to re-rank by cosine similarity to the query.
Returns top 5 most relevant citations instead of all matches.
Falls back to first 10 by traversal order if re-ranking fails."
```

---

## Stream 3: Create `/audit-graph` Skill

### Task 3.1: Create the audit-graph command

**Files:**
- Create: `.claude/commands/audit-graph.md`

**Step 1: Write the skill file**

Create `.claude/commands/audit-graph.md` with:
- Edge property coverage checks (% of DOSED_FOR with starting_dose, % of MONITORED_BY with frequency, etc.)
- Clinical scenario pass rate (run standard queries)
- Evidence relevance spot check (top-3 citations relevant?)
- Terminology resolution check (20 common terms resolve?)
- Score card with A/B/C/F grading

The skill should:
1. Accept an optional `guideline_id` argument (defaults to all)
2. Connect to Neo4j using the standard pattern
3. Run 4 audit sections in a Python script
4. Output a formatted score card

```markdown
# Audit GraphRAG Quality

Comprehensive quality scoring of the live knowledge graph.

## Usage

```
/audit-graph [guideline_id]
```

## Process

### Step 1: Edge Property Coverage

Run a Python script to check edge property population:

```bash
uv run python -c "
from dotenv import load_dotenv; load_dotenv()
from open_medicine.graphrag.config import get_settings
from open_medicine.graphrag.graph.connection import GraphConnection

settings = get_settings()
with GraphConnection(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password) as conn:
    # DOSED_FOR edge properties
    dosed = conn.execute_read('MATCH ()-[r:DOSED_FOR]->() RETURN count(r) AS total, count(r.starting_dose) AS has_start, count(r.max_dose) AS has_max, count(r.frequency) AS has_freq')
    # MONITORED_BY edge properties
    monitored = conn.execute_read('MATCH ()-[r:MONITORED_BY]->() RETURN count(r) AS total, count(r.frequency) AS has_freq, count(r.threshold_alert) AS has_alert')
    # INTERACTS_WITH edge properties
    interactions = conn.execute_read('MATCH ()-[r:INTERACTS_WITH]->() RETURN count(r) AS total, count(r.mechanism) AS has_mech, count(r.severity) AS has_sev')
    # CONTRAINDICATED_IN edge properties
    contras = conn.execute_read('MATCH ()-[r:CONTRAINDICATED_IN]->() RETURN count(r) AS total, count(r.severity) AS has_sev, count(r.reason) AS has_reason')

    for name, rows in [('DOSED_FOR', dosed), ('MONITORED_BY', monitored), ('INTERACTS_WITH', interactions), ('CONTRAINDICATED_IN', contras)]:
        r = rows[0] if rows else {}
        total = r.get('total', 0)
        print(f'{name}: {total} edges')
        for k, v in r.items():
            if k != 'total':
                pct = (v / total * 100) if total else 0
                print(f'  {k}: {v}/{total} ({pct:.0f}%)')
"
```

### Step 2: Clinical Scenario Pass Rate

Run generated test scenarios:
```bash
uv run python -m open_medicine.graphrag.ingest_v2 scenarios \
    --file data/cache/graphrag/aha_acc_hf_2022/test_scenarios.json
```

### Step 3: Structural Validation

```bash
uv run python -m open_medicine.graphrag.ingest_v2 validate
```

### Step 4: Terminology Resolution Check

Test 20 common clinical terms:
```bash
uv run python -c "
from open_medicine.graphrag.terminology.resolver import link_entity

terms = [
    ('MRA', 'drug_class'), ('ACEi', 'drug_class'), ('ARB', 'drug_class'),
    ('ARNi', 'drug_class'), ('SGLT2 Inhibitor', 'drug_class'),
    ('Beta Blocker', 'drug_class'), ('Loop Diuretic', 'drug_class'),
    ('Sacubitril/Valsartan', 'drug'), ('Carvedilol', 'drug'),
    ('Spironolactone', 'drug'), ('Dapagliflozin', 'drug'),
    ('Lisinopril', 'drug'), ('Metoprolol', 'drug'),
    ('Furosemide', 'drug'), ('Digoxin', 'drug'),
    ('HFrEF', 'disease'), ('Heart Failure', 'disease'),
    ('Potassium', 'lab'), ('Creatinine', 'lab'), ('BNP', 'lab'),
]
passed = 0
for name, etype in terms:
    result = link_entity(name, etype)
    status = 'OK' if result else 'FAIL'
    if result: passed += 1
    print(f'  [{status}] {name} ({etype})')
print(f'\nResolved: {passed}/{len(terms)}')
"
```

### Step 5: Score Card

Based on the results, assign grades:
- **Edge Properties**: A (>80% populated), B (60-80%), C (40-60%), F (<40%)
- **Scenarios**: A (100%), B (>85%), C (>70%), F (<70%)
- **Structure**: A (all pass), B (warnings only), C (1 critical), F (>1 critical)
- **Terminology**: A (100%), B (>90%), C (>75%), F (<75%)

**Overall**: Average of all sections. Report with actionable recommendations.
```

**Step 2: Verify the file is valid**

Run: `ls -la .claude/commands/audit-graph.md`
Expected: File exists.

**Step 3: Commit**

```bash
git add .claude/commands/audit-graph.md
git commit -m "feat(graphrag): add /audit-graph skill for quality scoring

Creates a comprehensive quality audit covering edge property coverage,
clinical scenario pass rate, structural validation, and terminology
resolution. Outputs a graded score card with actionable recommendations."
```

---

## Stream 4: Create `/enrich-graph` Skill

### Task 4.1: Create the enrichment script

**Files:**
- Create: `src/open_medicine/graphrag/enrichment.py`
- Test: `tests/graphrag/test_enrichment.py`

**Step 1: Write the failing test**

```python
"""Tests for GraphRAG edge property enrichment."""
import json
from open_medicine.graphrag.enrichment import parse_dosing_properties, parse_monitoring_properties


class TestParseDosing:
    def test_basic_dosing(self):
        text = "Bumetanide: initial daily dose 0.5-1.0 mg once or twice daily; maximum total daily dose 10 mg"
        result = parse_dosing_properties(text)
        assert result["starting_dose"] == "0.5-1.0 mg"
        assert "10 mg" in result["max_dose"]

    def test_empty_text(self):
        result = parse_dosing_properties("")
        assert result == {}


class TestParseMonitoring:
    def test_basic_monitoring(self):
        text = "Monitor potassium and renal function within 1-2 weeks of initiation"
        result = parse_monitoring_properties(text)
        assert "frequency" in result
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/graphrag/test_enrichment.py -v`
Expected: FAIL — module doesn't exist.

**Step 3: Write the enrichment module**

Create `src/open_medicine/graphrag/enrichment.py`:

```python
"""Extract structured edge properties from action_detail text.

Uses regex-based extraction for common patterns found in clinical guidelines.
Falls back to empty dict when patterns don't match — safe to call on any text.
"""

import re
from typing import Any


def parse_dosing_properties(text: str) -> dict[str, str]:
    """Extract dosing properties from action_detail text."""
    if not text:
        return {}

    props: dict[str, str] = {}

    # Starting/initial dose
    start_match = re.search(
        r"(?:initial|starting|begin(?:ning)?)\s+(?:daily\s+)?dose\s+(?:of\s+)?([\d.,\-/]+\s*(?:mg|mcg|g|units?|mL))",
        text, re.IGNORECASE,
    )
    if start_match:
        props["starting_dose"] = start_match.group(1).strip()

    # Target dose
    target_match = re.search(
        r"(?:target|goal|optimal)\s+(?:daily\s+)?dose\s+(?:of\s+)?([\d.,\-/]+\s*(?:mg|mcg|g|units?|mL))",
        text, re.IGNORECASE,
    )
    if target_match:
        props["target_dose"] = target_match.group(1).strip()

    # Maximum dose
    max_match = re.search(
        r"(?:max(?:imum)?|up\s+to)\s+(?:total\s+)?(?:daily\s+)?dose\s+(?:of\s+)?([\d.,\-/]+\s*(?:mg|mcg|g|units?|mL))",
        text, re.IGNORECASE,
    )
    if max_match:
        props["max_dose"] = max_match.group(1).strip()

    # Frequency
    freq_match = re.search(
        r"(once|twice|three times|four times|every\s+\d+\s*(?:hours?|hrs?|days?))\s+(?:daily|per\s+day|a\s+day)?",
        text, re.IGNORECASE,
    )
    if freq_match:
        props["frequency"] = freq_match.group(0).strip()

    # Route
    route_match = re.search(
        r"\b(oral(?:ly)?|intravenous(?:ly)?|IV|subcutaneous(?:ly)?|SC|SQ|intramuscular(?:ly)?|IM|topical(?:ly)?)\b",
        text, re.IGNORECASE,
    )
    if route_match:
        props["route"] = route_match.group(1).strip().lower()

    return props


def parse_monitoring_properties(text: str) -> dict[str, str]:
    """Extract monitoring properties from action_detail text."""
    if not text:
        return {}

    props: dict[str, str] = {}

    # Frequency
    freq_match = re.search(
        r"(?:within|every|at least every|monitor\s+(?:at\s+)?)\s*([\d\-]+\s*(?:weeks?|days?|months?|hours?))",
        text, re.IGNORECASE,
    )
    if freq_match:
        props["frequency"] = freq_match.group(0).strip()

    # Threshold alert (e.g., K+ > 5.0)
    alert_match = re.search(
        r"(K\+?|potassium|creatinine|eGFR|BNP|INR)\s*[>≥<≤]\s*[\d.]+\s*(?:mEq/L|mg/dL|mL/min|pg/mL)?",
        text, re.IGNORECASE,
    )
    if alert_match:
        props["threshold_alert"] = alert_match.group(0).strip()

    return props


def parse_interaction_properties(text: str) -> dict[str, str]:
    """Extract interaction properties from action_detail text."""
    if not text:
        return {}

    props: dict[str, str] = {}

    # Mechanism
    mech_match = re.search(
        r"(?:due to|because of|via|through|overlapping)\s+(.+?)(?:\.|;|$)",
        text, re.IGNORECASE,
    )
    if mech_match:
        props["mechanism"] = mech_match.group(1).strip()[:100]

    # Clinical effect
    effect_match = re.search(
        r"(?:risk of|may cause|increases?|leading to)\s+(.+?)(?:\.|;|$)",
        text, re.IGNORECASE,
    )
    if effect_match:
        props["clinical_effect"] = effect_match.group(1).strip()[:100]

    # Severity
    if any(w in text.lower() for w in ["avoid", "contraindicated", "never", "must not"]):
        props["severity"] = "MAJOR"
    elif any(w in text.lower() for w in ["caution", "careful", "monitor closely"]):
        props["severity"] = "MODERATE"
    else:
        props["severity"] = "MINOR"

    return props


def parse_contraindication_properties(text: str) -> dict[str, str]:
    """Extract contraindication properties from action_detail text."""
    if not text:
        return {}

    props: dict[str, str] = {}

    # Severity
    if any(w in text.lower() for w in ["avoid", "must not", "never", "absolutely", "contraindicated"]):
        props["severity"] = "ABSOLUTE"
    elif any(w in text.lower() for w in ["caution", "relative", "careful", "weigh", "consider"]):
        props["severity"] = "RELATIVE"

    # Reason
    reason_match = re.search(
        r"(?:because|due to|as it|since|worsen|risk of)\s+(.+?)(?:\.|;|$)",
        text, re.IGNORECASE,
    )
    if reason_match:
        props["reason"] = reason_match.group(1).strip()[:150]

    return props


# Map rec_type to parser
PARSERS: dict[str, Any] = {
    "dosing": parse_dosing_properties,
    "monitoring": parse_monitoring_properties,
    "interaction": parse_interaction_properties,
    "contraindication": parse_contraindication_properties,
}
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/graphrag/test_enrichment.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/open_medicine/graphrag/enrichment.py tests/graphrag/test_enrichment.py
git commit -m "feat(graphrag): add enrichment module for edge property extraction

Regex-based extraction of structured properties (dosing, monitoring,
interaction, contraindication) from action_detail prose text. Used by
the /enrich-graph skill to populate edge properties on existing graphs."
```

### Task 4.2: Create the enrich-graph command

**Files:**
- Create: `.claude/commands/enrich-graph.md`

**Step 1: Write the skill file**

The `/enrich-graph` skill should:
1. Read the consolidated JSONL for a guideline
2. Group extractions by rec_type
3. For each extraction, parse `action_detail` into structured properties using `enrichment.py`
4. Generate a JSONL patch file
5. Apply the patch to Neo4j (update edge properties)
6. Run `/audit-graph` to verify

```markdown
# Enrich Graph Edge Properties

Extract structured edge properties from existing JSONL and patch onto the live graph.

## Usage

```
/enrich-graph <guideline_id>
```

Example: `/enrich-graph aha_acc_hf_2022`

## Process

### Step 1: Generate enrichment patch

Parse action_detail text from consolidated JSONL into structured edge properties:

```bash
uv run python -c "
import json
from pathlib import Path
from collections import Counter
from open_medicine.graphrag.enrichment import PARSERS

guideline_id = '$ARGUMENTS'.strip() or 'aha_acc_hf_2022'
jsonl_path = Path(f'data/cache/graphrag/{guideline_id}/consolidated.jsonl')
patch_path = Path(f'data/patches/{guideline_id}_enrichment.jsonl')
patch_path.parent.mkdir(parents=True, exist_ok=True)

stats = Counter()
patches = []

for line in jsonl_path.read_text().splitlines():
    if not line.strip():
        continue
    rule = json.loads(line)
    rec_type = rule.get('rec_type', '')
    parser = PARSERS.get(rec_type)
    if not parser:
        continue

    detail = rule.get('action_detail', '')
    props = parser(detail)
    if props:
        patches.append({
            'rec_id': rule['rec_id'],
            'rec_type': rec_type,
            'properties': props,
            'source_text': detail[:200],
        })
        stats[rec_type] += 1

patch_path.write_text('\n'.join(json.dumps(p) for p in patches))
print(f'Generated {len(patches)} patches:')
for rt, count in stats.most_common():
    print(f'  {rt}: {count}')
print(f'Saved to {patch_path}')
"
```

### Step 2: Apply patch to Neo4j

Update edge properties in the graph:

```bash
uv run python -c "
import json
from pathlib import Path
from dotenv import load_dotenv; load_dotenv()
from open_medicine.graphrag.config import get_settings
from open_medicine.graphrag.graph.connection import GraphConnection

guideline_id = '$ARGUMENTS'.strip() or 'aha_acc_hf_2022'
patch_path = Path(f'data/patches/{guideline_id}_enrichment.jsonl')

settings = get_settings()
with GraphConnection(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password) as conn:
    applied = 0
    for line in patch_path.read_text().splitlines():
        if not line.strip():
            continue
        patch = json.loads(line)
        rec_id = patch['rec_id']
        props = patch['properties']
        rec_type = patch['rec_type']

        # Map rec_type to edge type
        edge_map = {
            'dosing': 'DOSED_FOR',
            'monitoring': 'MONITORED_BY',
            'interaction': 'INTERACTS_WITH',
            'contraindication': 'CONTRAINDICATED_IN',
        }
        edge_type = edge_map.get(rec_type, '')
        if not edge_type:
            continue

        # Update edge properties via the recommendation
        set_clauses = ', '.join(f'r.{k} = \$prop_{k}' for k in props)
        params = {f'prop_{k}': v for k, v in props.items()}
        params['rec_id'] = rec_id

        cypher = f'''
        MATCH (rec:Recommendation {{rec_id: \$rec_id}})-[:RECOMMENDS]->(entity)
        MATCH (entity)-[r:{edge_type}]->()
        SET {set_clauses}
        RETURN count(r) AS updated
        '''
        try:
            rows = conn.execute_read(cypher, params)
            if rows and rows[0].get('updated', 0) > 0:
                applied += 1
        except Exception as e:
            print(f'  Warning: {rec_id}: {e}')

    print(f'Applied {applied} edge property updates')
"
```

### Step 3: Verify

Run `/audit-graph` to check edge property coverage improved.
```

**Step 2: Commit**

```bash
git add .claude/commands/enrich-graph.md
git commit -m "feat(graphrag): add /enrich-graph skill for edge property enrichment

Extracts structured properties (doses, frequencies, thresholds, severities)
from action_detail text in consolidated JSONL and patches them onto
Neo4j edge properties. Pairs with /audit-graph for verification."
```

---

## Stream 5: Create `/maintain-graph` Skill

### Task 5.1: Create the maintain-graph command

**Files:**
- Create: `.claude/commands/maintain-graph.md`

**Step 1: Write the skill file**

```markdown
# Maintain Graph

Day-to-day graph operations for the clinical knowledge graph.

## Usage

```
/maintain-graph <operation> [args]
```

## Operations

### `add-term <name> <type> [aliases...]`

Add a new term to terminology files.

```bash
uv run python -c "
import json
from pathlib import Path

args = '$ARGUMENTS'.split()
op, name, term_type = args[0], args[1], args[2]
aliases = args[3:] if len(args) > 3 else []

type_to_file = {
    'drug': 'drugs.json',
    'drug_class': 'drug_classes.json',
    'disease': 'diseases.json',
    'lab': 'labs.json',
    'procedure': 'procedures.json',
    'device': 'devices.json',
    'symptom': 'symptoms.json',
}
fname = type_to_file.get(term_type)
if not fname:
    print(f'Unknown type: {term_type}')
    exit(1)

path = Path(f'src/open_medicine/graphrag/terminology/{fname}')
data = json.loads(path.read_text())
canonical = name.lower().replace(' ', '_')
if canonical in data:
    print(f'{name} already exists')
    exit(0)

data[canonical] = {'name': name, 'aliases': aliases}
path.write_text(json.dumps(data, indent=2))
print(f'Added {name} ({term_type}) with {len(aliases)} aliases')
"
```

### `check-health`

Quick health check of the graph.

```bash
uv run python -c "
from dotenv import load_dotenv; load_dotenv()
from open_medicine.graphrag.config import get_settings
from open_medicine.graphrag.graph.connection import GraphConnection

settings = get_settings()
with GraphConnection(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password) as conn:
    nodes = conn.execute_read('MATCH (n) RETURN labels(n)[0] AS label, count(n) AS cnt ORDER BY cnt DESC')
    edges = conn.execute_read('MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS cnt ORDER BY cnt DESC')
    orphans = conn.execute_read('MATCH (n) WHERE NOT EXISTS { (n)--() } AND NOT n:EvidenceChunk RETURN labels(n)[0] AS label, count(n) AS cnt')

    print('=== Node Counts ===')
    for r in nodes: print(f'  {r[\"label\"]}: {r[\"cnt\"]}')
    print('\n=== Edge Counts ===')
    for r in edges: print(f'  {r[\"type\"]}: {r[\"cnt\"]}')
    print('\n=== Orphans ===')
    total_orphans = sum(r['cnt'] for r in orphans)
    if total_orphans == 0:
        print('  None')
    else:
        for r in orphans: print(f'  {r[\"label\"]}: {r[\"cnt\"]}')
"
```

### `repair-evidence`

Re-link orphaned EvidenceChunk nodes to their recommendations.

### `normalize-ids`

Ensure all entity node IDs follow the `type:canonical_name` convention.

### `stats`

Print detailed graph statistics including edge property coverage.
```

**Step 2: Commit**

```bash
git add .claude/commands/maintain-graph.md
git commit -m "feat(graphrag): add /maintain-graph skill for day-to-day operations

Provides quick operations: add-term, check-health, repair-evidence,
normalize-ids, and stats for routine graph maintenance."
```

### Task 5.2: Update `/ingest-guideline` to include enrichment phase

**Files:**
- Modify: `.claude/commands/ingest-guideline.md`

**Step 1: Add Phase 4.7 (Enrichment) between load and validation**

After the existing Phase 4.6 (Generate Embeddings) and before Phase 5 (Validate), add:

```markdown
### Phase 4.7: Enrich Edge Properties

Run the enrichment module to populate edge properties from action_detail text:

```bash
/enrich-graph {guideline_id}
```

This extracts structured properties (doses, frequencies, thresholds, severities)
from the prose in action_detail fields and sets them on the corresponding Neo4j edges.
```

**Step 2: Commit**

```bash
git add .claude/commands/ingest-guideline.md
git commit -m "feat(graphrag): add enrichment phase to /ingest-guideline pipeline

Adds Phase 4.7 between embedding and validation to automatically
populate edge properties during guideline ingestion."
```

---

## Summary

After all tasks:
- **Stream 1** (Tasks 1.1-1.2): Terminology resolution — monitoring and dosing handlers try drug_class directly
- **Stream 2** (Task 2.1): Evidence re-ranking — top-5 by cosine similarity instead of all matches
- **Stream 3** (Task 3.1): `/audit-graph` skill — comprehensive quality scoring
- **Stream 4** (Tasks 4.1-4.2): `/enrich-graph` skill — extract and apply edge properties
- **Stream 5** (Tasks 5.1-5.2): `/maintain-graph` skill + ingestion pipeline update

**Verification**: Run `/audit-graph aha_acc_hf_2022` after all streams complete to get baseline score.

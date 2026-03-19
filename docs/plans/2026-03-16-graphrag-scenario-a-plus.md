# GraphRAG A+ Scenario Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the 6 gaps identified during clinical scenario testing (A- → A+) so both HF test scenarios achieve full PASS on all steps and safety assertions.

**Architecture:** Three code changes in the reasoning engine (`engine_v2.py`) plus three data-level fixes in extraction JSONL files. Each task is independently testable and committable. Tasks 1-3 are code changes (with TDD); Tasks 4-6 are data fixes; Task 7 is re-ingestion + verification.

**Tech Stack:** Python, Neo4j Cypher, JSONL extraction data, pytest with mocks

**Prerequisite plan:** This plan builds on the completed work in `docs/plans/2026-03-16-graphrag-scenario-grade-a.md`. That plan fixed vector fallback conditions, concept variable inference, titration extraction, and dosing enrichment. This plan addresses the remaining 6 gaps surfaced by `/run-scenarios`.

---

### Task 1: Severity Propagation — Always Merge Class-Level Interactions

**Problem:** `_query_interactions` (engine_v2.py:444) only checks parent class interactions when a drug has *no* direct interactions (`if not rows`). If Lisinopril (Drug) has MAJOR interactions but its class ACEi (DrugClass) has ABSOLUTE interaction with ARNi, the ABSOLUTE severity never surfaces. This caused the ACEi↔ARNi interaction to return MAJOR instead of ABSOLUTE in Scenario 2.

**Files:**
- Modify: `src/open_medicine/graphrag/reasoning/engine_v2.py:444-466` (class inheritance block)
- Modify: `src/open_medicine/graphrag/reasoning/engine_v2.py:925-934` (`_deduplicate` method)
- Test: `tests/graphrag/test_engine_v2.py`

**Step 1: Write the failing test**

Add to `tests/graphrag/test_engine_v2.py`:

```python
class TestInteractionSeverityPropagation:
    """Class-level ABSOLUTE severity must propagate even when drug has direct interactions."""

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_class_absolute_overrides_drug_major(self, mock_link):
        """If drug has MAJOR interaction and its class has ABSOLUTE, result must include ABSOLUTE."""
        engine, conn = _make_engine()

        mock_drug = MagicMock()
        mock_drug.node_id = "rxnorm:lisinopril"
        mock_drug.node_label = "Drug"
        mock_drug.snomed_code = None
        mock_drug.rxnorm_code = "rxnorm:lisinopril"
        mock_drug.atc_code = None
        mock_drug.loinc_code = None
        mock_drug.icd10_code = None
        mock_drug.cpt_code = None
        mock_drug.gmdn_code = None
        mock_link.return_value = mock_drug

        # Drug-level query returns MAJOR interaction with ARNi
        drug_rows = [
            {
                "entity_id": "atc:C09DX",
                "entity_name": "ARNi",
                "entity_type": "DrugClass",
                "severity": "MAJOR",
                "evidence_quality": "high",
                "mechanism": "angioedema risk",
                "clinical_effect": "potentially life-threatening",
            }
        ]
        # Class lookup returns ACEi class
        class_rows = [{"class_id": "atc:C09A", "class_name": "ACE Inhibitor"}]
        # Class-level query returns ABSOLUTE interaction with ARNi
        class_interaction_rows = [
            {
                "entity_id": "atc:C09DX",
                "entity_name": "ARNi",
                "entity_type": "DrugClass",
                "severity": "ABSOLUTE",
                "evidence_quality": "high",
                "mechanism": "concomitant use causes angioedema",
                "clinical_effect": "life-threatening angioedema",
            }
        ]
        conn.execute_read.side_effect = [drug_rows, class_rows, class_interaction_rows]

        q = ClinicalQuery(intent="interaction", concepts=["lisinopril"])
        result = engine.query(q)

        # After dedup, the ABSOLUTE severity must win
        arni_matches = [m for m in result.semantic_matches if m.entity_id == "atc:C09DX"]
        assert len(arni_matches) == 1, f"Expected 1 deduplicated match, got {len(arni_matches)}"
        assert arni_matches[0].edge_properties.get("severity") == "ABSOLUTE", (
            f"Expected ABSOLUTE from class propagation, got {arni_matches[0].edge_properties.get('severity')}"
        )

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_no_duplicate_when_same_severity(self, mock_link):
        """If drug and class both have MAJOR for same target, deduplicate to one."""
        engine, conn = _make_engine()

        mock_drug = MagicMock()
        mock_drug.node_id = "rxnorm:lisinopril"
        mock_drug.node_label = "Drug"
        mock_drug.snomed_code = None
        mock_drug.rxnorm_code = "rxnorm:lisinopril"
        mock_drug.atc_code = None
        mock_drug.loinc_code = None
        mock_drug.icd10_code = None
        mock_drug.cpt_code = None
        mock_drug.gmdn_code = None
        mock_link.return_value = mock_drug

        same_row = {
            "entity_id": "atc:C09DX",
            "entity_name": "ARNi",
            "entity_type": "DrugClass",
            "severity": "MAJOR",
            "evidence_quality": "high",
            "mechanism": "angioedema risk",
            "clinical_effect": "potentially life-threatening",
        }
        class_rows = [{"class_id": "atc:C09A", "class_name": "ACE Inhibitor"}]
        conn.execute_read.side_effect = [[same_row], class_rows, [same_row]]

        q = ClinicalQuery(intent="interaction", concepts=["lisinopril"])
        result = engine.query(q)

        arni_matches = [m for m in result.semantic_matches if m.entity_id == "atc:C09DX"]
        assert len(arni_matches) == 1, f"Expected 1 deduplicated match, got {len(arni_matches)}"
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py::TestInteractionSeverityPropagation -v`
Expected: FAIL — ABSOLUTE not found because class interactions are skipped when drug rows exist.

**Step 3: Implement the fix**

In `src/open_medicine/graphrag/reasoning/engine_v2.py`, replace lines 444-466 (the `if not rows` block) with:

```python
            # Class inheritance: ALWAYS check parent classes for a Drug entity
            # and merge results. This ensures ABSOLUTE severity from class-level
            # edges propagates even when the drug has direct interactions.
            if entity.node_label == "Drug":
                for class_id, _class_name in self._get_parent_classes(entity.node_id):
                    c_cypher, c_params = ReasoningQueries.find_interactions(
                        class_id, entity_label="DrugClass"
                    )
                    c_rows = self._conn.execute_read(c_cypher, c_params)
                    for row in c_rows:
                        semantic_matches.append(
                            SemanticMatch(
                                entity_id=row.get("entity_id", ""),
                                entity_name=row.get("entity_name", ""),
                                entity_type=row.get("entity_type", "Drug"),
                                edge_type="INTERACTS_WITH",
                                strength="",
                                evidence_quality=row.get("evidence_quality") or "",
                                source_layer="expanded",
                                edge_properties={
                                    k: row.get(k)
                                    for k in ("severity", "mechanism", "clinical_effect")
                                },
                            )
                        )
```

Then replace `_deduplicate` (line 925) to keep highest severity for interaction dedup:

```python
    _SEVERITY_RANK = {"ABSOLUTE": 3, "MAJOR": 2, "MINOR": 1}

    @staticmethod
    def _deduplicate(matches: list[SemanticMatch]) -> list[SemanticMatch]:
        """Deduplicate by (entity_id, edge_type), keeping highest severity for interactions."""
        seen: dict[tuple[str, str], int] = {}
        result: list[SemanticMatch] = []
        for m in matches:
            key = (m.entity_id, m.edge_type)
            sev = ReasoningEngine._SEVERITY_RANK.get(
                (m.edge_properties or {}).get("severity", ""), 0
            )
            if key not in seen:
                seen[key] = len(result)
                result.append(m)
            elif sev > ReasoningEngine._SEVERITY_RANK.get(
                (result[seen[key]].edge_properties or {}).get("severity", ""), 0
            ):
                result[seen[key]] = m
        return result
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py::TestInteractionSeverityPropagation -v`
Expected: PASS

**Step 5: Run full engine test suite for regressions**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add src/open_medicine/graphrag/reasoning/engine_v2.py tests/graphrag/test_engine_v2.py
git commit -m "fix(graphrag): always propagate class-level interaction severity to drug lookups

Previously, class-level interactions were only checked when a drug had
no direct interactions. This caused ABSOLUTE severity from class edges
(e.g., ACEi↔ARNi) to be missed when the drug also had MAJOR direct
interactions. Now always merges class-level results and deduplicates
by keeping the highest severity."
```

---

### Task 2: Device Therapy Condition Evaluation in Generic Handler

**Problem:** `device_therapy` intent falls through to `_query_generic` (engine_v2.py:701), which uses `RecommendationMatch` (no `conditions_met` field) and never calls `_evaluate_match_conditions`. CRT recommendations show `conditions_met=true` without checking for missing variables like QRS_duration.

**Files:**
- Modify: `src/open_medicine/graphrag/reasoning/engine_v2.py:701-751` (`_query_generic`)
- Modify: `src/open_medicine/graphrag/graph/queries_v2.py` (`find_recommendations_for_entity` — add `conditions_json` to RETURN)
- Test: `tests/graphrag/test_engine_v2.py`

**Step 1: Write the failing test**

```python
class TestGenericHandlerConditionEvaluation:
    """Generic query handler must evaluate conditions and flag missing variables."""

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_device_therapy_flags_missing_variables(self, mock_link):
        """Device therapy recs with conditions should flag missing patient vars."""
        engine, conn = _make_engine()

        mock_device = MagicMock()
        mock_device.node_id = "snomed:ICD"
        mock_device.node_label = "Device"
        mock_device.snomed_code = "snomed:ICD"
        mock_device.rxnorm_code = None
        mock_device.atc_code = None
        mock_device.loinc_code = None
        mock_device.icd10_code = None
        mock_device.cpt_code = None
        mock_device.gmdn_code = None
        mock_link.return_value = mock_device

        rows = [
            {
                "rec_id": "rec_001",
                "rec_type": "device_therapy",
                "action": "ICD implantation",
                "detail": "ICD for primary prevention in LVEF <=35%",
                "strength": "strong_for",
                "evidence_quality": "high",
                "source_text": "Guideline text...",
                "guideline": "AHA/ACC HF 2022",
                "doi": "10.1161/CIR.0000000000001063",
                "section": "7.4",
                "conditions_json": json.dumps([
                    {"variable": "LVEF", "operator": "<=", "threshold": 35},
                    {"variable": "QRS_duration", "operator": ">=", "threshold": 150},
                ]),
            }
        ]
        conn.execute_read.return_value = rows

        q = ClinicalQuery(
            intent="device_therapy",
            concepts=["ICD"],
            patient_vars={"lvef": 32},  # QRS_duration missing
        )
        result = engine.query(q)

        assert len(result.semantic_matches) > 0
        match = result.semantic_matches[0]
        assert match.conditions_met is None, "Should be None when variables are missing"
        assert "qrs_duration" in [v.lower() for v in match.missing_variables]

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_device_therapy_conditions_met_true(self, mock_link):
        """When all conditions pass, conditions_met should be True."""
        engine, conn = _make_engine()

        mock_device = MagicMock()
        mock_device.node_id = "snomed:ICD"
        mock_device.node_label = "Device"
        mock_device.snomed_code = "snomed:ICD"
        mock_device.rxnorm_code = None
        mock_device.atc_code = None
        mock_device.loinc_code = None
        mock_device.icd10_code = None
        mock_device.cpt_code = None
        mock_device.gmdn_code = None
        mock_link.return_value = mock_device

        rows = [
            {
                "rec_id": "rec_001",
                "rec_type": "device_therapy",
                "action": "ICD implantation",
                "detail": "ICD for primary prevention",
                "strength": "strong_for",
                "evidence_quality": "high",
                "source_text": "",
                "guideline": "",
                "doi": "",
                "section": "",
                "conditions_json": json.dumps([
                    {"variable": "LVEF", "operator": "<=", "threshold": 35},
                ]),
            }
        ]
        conn.execute_read.return_value = rows

        q = ClinicalQuery(
            intent="device_therapy",
            concepts=["ICD"],
            patient_vars={"lvef": 32},
        )
        result = engine.query(q)
        assert result.semantic_matches[0].conditions_met is True
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py::TestGenericHandlerConditionEvaluation -v`
Expected: FAIL — generic handler produces `RecommendationMatch` not `SemanticMatch`.

**Step 3a: Update Cypher query**

In `src/open_medicine/graphrag/graph/queries_v2.py`, find `find_recommendations_for_entity` and add `rec.conditions_json AS conditions_json` to the RETURN clause.

**Step 3b: Rewrite `_query_generic` to use SemanticMatch with condition evaluation**

Replace lines 701-751 in `engine_v2.py`:

```python
    def _query_generic(self, q: ClinicalQuery) -> GraphRAGResult:
        """Generic query — search recommendations by entity + type."""
        semantic_matches: list[SemanticMatch] = []
        all_evidence: list[EvidenceCitation] = []

        for concept in q.concepts:
            for entity_type in ("drug", "drug_class", "disease", "procedure", "device"):
                entity = link_entity(concept, entity_type)
                if entity is None:
                    continue

                cypher, params = ReasoningQueries.find_recommendations_for_entity(
                    entity.node_id, entity.node_label, rec_type=q.intent
                )
                rows = self._conn.execute_read(cypher, params)

                for row in rows:
                    match = SemanticMatch(
                        entity_id=row.get("rec_id", ""),
                        entity_name=row.get("action", ""),
                        entity_type=entity.node_label,
                        edge_type=q.intent or "generic",
                        strength=row.get("strength", ""),
                        evidence_quality=row.get("evidence_quality") or "",
                        conditions_json=row.get("conditions_json"),
                        edge_properties={
                            "rec_type": row.get("rec_type", ""),
                            "action_detail": row.get("detail", ""),
                        },
                    )
                    if q.patient_vars:
                        self._evaluate_match_conditions(match, q.patient_vars)
                    semantic_matches.append(match)

                    if row.get("source_text"):
                        all_evidence.append(
                            EvidenceCitation(
                                chunk_id="",
                                text=row["source_text"],
                                guideline_title=row.get("guideline") or "",
                                doi=row.get("doi") or "",
                                section=row.get("section") or "",
                            )
                        )

                if rows:
                    break

        confidence = "high" if semantic_matches else "low"
        hints = self._generate_hints(q) if not semantic_matches else []
        return GraphRAGResult(
            source="graph_traversal",
            semantic_matches=semantic_matches,
            evidence=all_evidence,
            confidence=confidence,
            hints=hints,
        )
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py::TestGenericHandlerConditionEvaluation -v`
Expected: PASS

**Step 5: Run full engine test suite**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add src/open_medicine/graphrag/reasoning/engine_v2.py src/open_medicine/graphrag/graph/queries_v2.py tests/graphrag/test_engine_v2.py
git commit -m "fix(graphrag): evaluate conditions in generic query handler

The generic handler (used for device_therapy, prevention, etc.) now
returns SemanticMatch with conditions_json and calls
_evaluate_match_conditions. CRT recommendations now correctly flag
missing QRS_duration instead of showing conditions_met=true."
```

---

### Task 3: Variable Normalization Regression Tests

**Problem:** Normalization code works correctly (confirmed in exploration), but no regression tests exist. Add tests to lock down behavior for `nyha_class`, `NYHA_class`, `NYHA Class`, eGFR variants, and potassium variants.

**Files:**
- Test: `tests/graphrag/test_engine_v2.py`

**Step 1: Write the tests**

```python
class TestVariableNormalization:
    """Verify _normalize_var_name handles all common patient variable forms."""

    def test_lowercase_underscore(self):
        assert ReasoningEngine._normalize_var_name("nyha_class") == "nyha_class"

    def test_mixed_case_underscore(self):
        assert ReasoningEngine._normalize_var_name("NYHA_class") == "nyha_class"

    def test_title_case_space(self):
        assert ReasoningEngine._normalize_var_name("NYHA Class") == "nyha_class"

    def test_all_caps(self):
        assert ReasoningEngine._normalize_var_name("NYHA_CLASS") == "nyha_class"

    def test_egfr_variants(self):
        assert ReasoningEngine._normalize_var_name("eGFR") == "egfr"
        assert ReasoningEngine._normalize_var_name("GFR") == "egfr"
        assert ReasoningEngine._normalize_var_name("estimated_gfr") == "egfr"

    def test_potassium_variants(self):
        assert ReasoningEngine._normalize_var_name("K+") == "potassium"
        assert ReasoningEngine._normalize_var_name("K") == "potassium"
        assert ReasoningEngine._normalize_var_name("potassium") == "potassium"

    def test_unknown_passes_through(self):
        assert ReasoningEngine._normalize_var_name("weight_kg") == "weight_kg"
```

**Step 2: Run tests**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py::TestVariableNormalization -v`
Expected: All PASS (normalization already works)

**Step 3: Commit**

```bash
git add tests/graphrag/test_engine_v2.py
git commit -m "test(graphrag): add variable normalization regression tests

Locks down _normalize_var_name for NYHA_class, eGFR, potassium
variants. Surfaced as potential issue during scenario testing but
code already handles them correctly."
```

---

### Task 4: SGLT2i eGFR Floor Condition — Extraction Data Fix

**Problem:** The SGLT2i treatment_selection extraction (`extractions/7_3_4.jsonl` line 1) has no eGFR condition. The eGFR < 20 contraindication exists (line 4) but the treatment eligibility edge doesn't encode the floor, preventing explicit eGFR evaluation.

**Files:**
- Modify: `data/cache/graphrag/aha_acc_hf_2022/extractions/7_3_4.jsonl` (line 1)

**Step 1: Add eGFR condition to SGLT2i treatment_selection**

Edit line 1 of `data/cache/graphrag/aha_acc_hf_2022/extractions/7_3_4.jsonl`. In the `conditions` array of the `logic_node`, add a fourth condition:

```json
{"variable": "eGFR", "operator": ">=", "threshold": 20, "unit": "mL/min/1.73m2"}
```

The full conditions array becomes:
```json
[
  {"variable": "LVEF", "operator": "<=", "threshold": 40, "unit": "%"},
  {"variable": "HF_type", "operator": "==", "threshold": "HFrEF", "unit": null},
  {"variable": "NYHA_class", "operator": ">=", "threshold": 2, "unit": null},
  {"variable": "eGFR", "operator": ">=", "threshold": 20, "unit": "mL/min/1.73m2"}
]
```

Source: EMPEROR-Reduced excluded eGFR < 20; DAPA-HF excluded eGFR < 30. Conservative floor of 20 per AHA/ACC 2022 (already captured in extraction line 4: `ln_aha_acc_hf_2022_7_3_4_004`).

**Step 2: Validate JSONL**

Run: `uv run python -c "import json; [json.loads(l) for l in open('data/cache/graphrag/aha_acc_hf_2022/extractions/7_3_4.jsonl') if l.strip()]; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add data/cache/graphrag/aha_acc_hf_2022/extractions/7_3_4.jsonl
git commit -m "fix(graphrag): add eGFR >= 20 condition to SGLT2i treatment_selection

Per EMPEROR-Reduced/DAPA-HF, SGLT2i for HFrEF requires eGFR >= 20.
Was captured as contraindication (eGFR < 20) but missing from
treatment eligibility conditions."
```

---

### Task 5: Spironolactone Monitoring — Two-Tier K+ Thresholds

**Problem:** Monitoring extraction has `threshold_discontinuation: ">=5.5 mEq/L"` but no explicit `threshold_alert`. The schema supports both `threshold_alert` and `threshold_stop`. Per AHA/ACC 2022: alert/reduce dose at K+ >= 5.0, discontinue at K+ >= 5.5.

**Files:**
- Modify: `data/cache/graphrag/aha_acc_hf_2022/enrichment_extractions/7_3_3_monitoring.jsonl` (lines 3 and 4)

**Step 1: Update spironolactone K+ monitoring (line 3)**

In rec_id `rec_aha_acc_hf_2022_7_3_3_003`, update the MONITORED_BY relationship properties to:

```json
{
  "schedule": "1 week, 4 weeks, then every 6 months",
  "threshold_initiation": "<5.0 mEq/L",
  "threshold_alert": ">=5.0 mEq/L (do not initiate; reduce dose if K+ rises above 5.0 on therapy)",
  "threshold_stop": ">=5.5 mEq/L (discontinue if K+ cannot be maintained <5.5 mEq/L)",
  "threshold_discontinuation": ">=5.5 mEq/L"
}
```

**Step 2: Update eplerenone K+ monitoring (line 4)**

Same change for rec_id `rec_aha_acc_hf_2022_7_3_3_004`.

**Step 3: Validate JSONL**

Run: `uv run python -c "import json; [json.loads(l) for l in open('data/cache/graphrag/aha_acc_hf_2022/enrichment_extractions/7_3_3_monitoring.jsonl') if l.strip()]; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add data/cache/graphrag/aha_acc_hf_2022/enrichment_extractions/7_3_3_monitoring.jsonl
git commit -m "fix(graphrag): add two-tier K+ thresholds for MRA monitoring

Adds threshold_alert (>=5.0, reduce dose) and threshold_stop (>=5.5,
discontinue) to spironolactone/eplerenone monitoring edges. Previously
only had threshold_discontinuation at 5.5."
```

---

### Task 6: Evidence Section Field — Verify and Fix Chunker

**Problem:** Evidence chunks return `section: null`. The code path supports section propagation (chunker → loader → query), so the gap is likely in the chunker not populating `Chunk.section` from markdown headings.

**Files:**
- Investigate: `src/open_medicine/graphrag/ingestion/chunker.py`
- Test: `tests/graphrag/test_chunker.py`

**Step 1: Read the chunker and check if section is populated**

Inspect `chunker.py` to see how `Chunk.section` is set. If it's always `""` or `None`, identify where to extract the section heading from the markdown `## ` prefix.

**Step 2: Write a regression test**

```python
def test_chunk_preserves_section_heading():
    """Chunks from sectioned markdown must carry the section name."""
    from open_medicine.graphrag.ingestion.chunker import chunk_guideline_section

    text = "## 7.3.3 Mineralocorticoid Receptor Antagonists\n\nMRA is recommended for HFrEF..."
    chunks = chunk_guideline_section(text, section_id="7_3_3", guideline_id="aha_acc_hf_2022")
    assert len(chunks) > 0
    assert chunks[0].section, "Chunk section should not be empty"
```

**Step 3: Fix chunker if needed**

If `Chunk.section` is not being populated, extract the first heading from the text block:

```python
# In the chunking function, after creating each chunk:
import re
heading_match = re.match(r"^#+\s+(.+)", text)
if heading_match:
    chunk.section = heading_match.group(1).strip()
```

**Step 4: Run test**

Run: `uv run python -m pytest tests/graphrag/test_chunker.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/open_medicine/graphrag/ingestion/chunker.py tests/graphrag/test_chunker.py
git commit -m "fix(graphrag): populate section field in evidence chunks from markdown headings

EvidenceChunk nodes now carry the source section name for better
navigability in evidence citation responses."
```

---

### Task 7: Re-ingest, Re-run Scenarios, Verify A+

**Prerequisites:** Tasks 1-6 complete. Tasks 4-5 modified extraction data, so re-ingestion is needed.

**Step 1: Back up graph**

Invoke `/openmedicine-graph-safety` skill to create a backup before re-ingesting.

**Step 2: Re-ingest modified sections**

Re-ingest sections 7_3_3 and 7_3_4 of aha_acc_hf_2022 using the loader. This applies the updated SGLT2i eGFR condition and the two-tier K+ thresholds.

**Step 3: Run all graphrag unit tests**

Run: `uv run python -m pytest tests/graphrag/ -v`
Expected: All PASS

**Step 4: Re-run clinical scenarios**

Use `/run-scenarios` to execute both test scenarios. Expected improvements:

| Gap | Before | After |
|-----|--------|-------|
| ACEi↔ARNi severity | MAJOR (drug-level) | ABSOLUTE (class propagated) |
| CRT missing variables | Not flagged | QRS_duration flagged |
| SGLT2i eGFR evaluation | Not evaluated | conditions_met=true at eGFR 35 |
| K+ thresholds | Single tier (5.5 stop) | Two tiers (5.0 alert, 5.5 stop) |
| Evidence section | null | Populated heading |
| Variable normalization | Already correct | Regression tests locked in |

**Step 5: Verify A+ grade**

All safety-critical assertions PASS. All dimension scores >= A. Overall verdict: A+.

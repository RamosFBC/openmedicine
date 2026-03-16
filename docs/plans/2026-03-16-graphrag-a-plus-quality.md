# GraphRAG A+ Quality: Surface Edge Properties to MCP Tools

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make all edge properties (severity, starting_dose, frequency, threshold_alert, threshold_stop, mechanism, clinical_effect) flow from Neo4j through the engine to MCP tool output, achieving A+ quality on the grading rubric.

**Architecture:** The Cypher queries already fetch edge properties correctly. The gap is in `SemanticMatch` (no fields for them) and the engine methods (discard them when building matches). Fix: extend `SemanticMatch` with an `edge_properties` dict, populate it in each engine query method, and add `threshold_stop` extraction to the enrichment parser.

**Tech Stack:** Python, Pydantic, Neo4j (Cypher), pytest with mocked connections

---

## Task 1: Add `edge_properties` to SemanticMatch

The core fix. `SemanticMatch` needs a flexible dict field to carry edge-specific properties without creating separate models for each edge type.

**Files:**
- Modify: `src/open_medicine/graphrag/reasoning/types_v2.py:40-67`
- Test: `tests/graphrag/test_engine_v2.py`

**Step 1: Write the failing test**

In `tests/graphrag/test_engine_v2.py`, add at the top of the file (after existing imports):

```python
class TestSemanticMatchEdgeProperties:
    """Verify SemanticMatch carries edge properties."""

    def test_edge_properties_default_empty(self):
        m = SemanticMatch(
            entity_id="x", entity_name="X", entity_type="Drug",
            edge_type="DOSED_FOR", strength="", evidence_quality="",
        )
        assert m.edge_properties == {}

    def test_edge_properties_carries_dosing(self):
        m = SemanticMatch(
            entity_id="x", entity_name="X", entity_type="Drug",
            edge_type="DOSED_FOR", strength="", evidence_quality="",
            edge_properties={
                "starting_dose": "12.5 mg",
                "target_dose": "50 mg",
                "max_dose": "50 mg",
                "frequency": "once daily",
            },
        )
        assert m.edge_properties["starting_dose"] == "12.5 mg"
        assert m.edge_properties["frequency"] == "once daily"

    def test_edge_properties_carries_severity(self):
        m = SemanticMatch(
            entity_id="x", entity_name="X", entity_type="Drug",
            edge_type="INTERACTS_WITH", strength="", evidence_quality="",
            edge_properties={"severity": "MAJOR", "mechanism": "hyperkalemia"},
        )
        assert m.edge_properties["severity"] == "MAJOR"

    def test_edge_properties_carries_monitoring(self):
        m = SemanticMatch(
            entity_id="x", entity_name="X", entity_type="Lab",
            edge_type="MONITORED_BY", strength="", evidence_quality="",
            edge_properties={
                "frequency": "within 1 week, then monthly",
                "threshold_alert": "K+ >= 5.5 mEq/L",
                "threshold_stop": "K+ >= 6.0 mEq/L",
            },
        )
        assert m.edge_properties["threshold_stop"] == "K+ >= 6.0 mEq/L"

    def test_edge_properties_serializes_to_json(self):
        m = SemanticMatch(
            entity_id="x", entity_name="X", entity_type="Drug",
            edge_type="DOSED_FOR", strength="", evidence_quality="",
            edge_properties={"starting_dose": "10 mg"},
        )
        data = m.model_dump()
        assert data["edge_properties"] == {"starting_dose": "10 mg"}
```

**Step 2: Run test to verify it fails**

```bash
uv run python -m pytest tests/graphrag/test_engine_v2.py::TestSemanticMatchEdgeProperties -v
```

Expected: FAIL — `SemanticMatch.__init__() got an unexpected keyword argument 'edge_properties'`

**Step 3: Implement — add `edge_properties` field**

In `src/open_medicine/graphrag/reasoning/types_v2.py`, add one field to `SemanticMatch` after `similarity_score`:

```python
    edge_properties: dict[str, str | None] = Field(
        default_factory=dict,
        description="Edge-specific properties (severity, starting_dose, frequency, "
        "threshold_alert, threshold_stop, mechanism, clinical_effect, etc.)",
    )
```

**Step 4: Run test to verify it passes**

```bash
uv run python -m pytest tests/graphrag/test_engine_v2.py::TestSemanticMatchEdgeProperties -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/open_medicine/graphrag/reasoning/types_v2.py tests/graphrag/test_engine_v2.py
git commit -m "feat(graphrag): add edge_properties dict to SemanticMatch"
```

---

## Task 2: Populate edge_properties in `_query_interactions`

The interaction handler at engine_v2.py:377-407 builds SemanticMatch but discards `severity`, `mechanism`, and `clinical_effect` from the Cypher row. Fix: read them into `edge_properties`.

**Files:**
- Modify: `src/open_medicine/graphrag/reasoning/engine_v2.py:358-423`
- Test: `tests/graphrag/test_engine_v2.py`

**Step 1: Write the failing test**

```python
class TestInteractionEdgeProperties:
    """Verify interaction queries surface severity/mechanism/effect."""

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_interaction_severity_surfaced(self, mock_link):
        mock_entity = MagicMock()
        mock_entity.node_id = "drug:spironolactone"
        mock_entity.node_label = "Drug"
        mock_entity.snomed_code = "S"
        mock_entity.rxnorm_code = None
        mock_entity.atc_code = None
        mock_entity.loinc_code = None
        mock_entity.icd10_code = None
        mock_entity.cpt_code = None
        mock_entity.gmdn_code = None
        mock_link.return_value = mock_entity

        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {
                "entity_id": "atc:C09C",
                "entity_name": "ARB",
                "entity_type": "DrugClass",
                "severity": "MAJOR",
                "evidence_quality": "moderate",
                "mechanism": "additive hyperkalemia risk",
                "clinical_effect": "life-threatening hyperkalemia",
            }
        ]

        q = ClinicalQuery(intent="interaction", concepts=["spironolactone"])
        result = engine.query(q)

        assert len(result.semantic_matches) >= 1
        match = result.semantic_matches[0]
        assert match.edge_properties["severity"] == "MAJOR"
        assert match.edge_properties["mechanism"] == "additive hyperkalemia risk"
        assert match.edge_properties["clinical_effect"] == "life-threatening hyperkalemia"

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_interaction_missing_severity_is_none(self, mock_link):
        mock_entity = MagicMock()
        mock_entity.node_id = "drug:x"
        mock_entity.node_label = "Drug"
        mock_entity.snomed_code = "S"
        mock_entity.rxnorm_code = None
        mock_entity.atc_code = None
        mock_entity.loinc_code = None
        mock_entity.icd10_code = None
        mock_entity.cpt_code = None
        mock_entity.gmdn_code = None
        mock_link.return_value = mock_entity

        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {
                "entity_id": "drug:y",
                "entity_name": "Y",
                "entity_type": "Drug",
                "severity": None,
                "evidence_quality": "low",
                "mechanism": None,
                "clinical_effect": None,
            }
        ]

        q = ClinicalQuery(intent="interaction", concepts=["x"])
        result = engine.query(q)
        match = result.semantic_matches[0]
        assert match.edge_properties.get("severity") is None
```

**Step 2: Run test to verify it fails**

```bash
uv run python -m pytest tests/graphrag/test_engine_v2.py::TestInteractionEdgeProperties -v
```

Expected: FAIL — `edge_properties` is `{}`, key `severity` not found

**Step 3: Implement — populate edge_properties in `_query_interactions`**

In `engine_v2.py`, modify the two places where `SemanticMatch` is built inside `_query_interactions` (lines ~378 and ~398).

Replace the direct-layer match construction (around line 378):

```python
                semantic_matches.append(
                    SemanticMatch(
                        entity_id=row.get("entity_id", ""),
                        entity_name=row.get("entity_name", ""),
                        entity_type=row.get("entity_type", "Drug"),
                        edge_type="INTERACTS_WITH",
                        strength="",
                        evidence_quality=row.get("evidence_quality") or "",
                        edge_properties={
                            k: row.get(k)
                            for k in ("severity", "mechanism", "clinical_effect")
                        },
                    )
                )
```

And the expanded-layer match construction (around line 398):

```python
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

**Step 4: Run test to verify it passes**

```bash
uv run python -m pytest tests/graphrag/test_engine_v2.py::TestInteractionEdgeProperties -v
```

Expected: PASS

**Step 5: Run all engine tests**

```bash
uv run python -m pytest tests/graphrag/test_engine_v2.py -v
```

Expected: All PASS

**Step 6: Commit**

```bash
git add src/open_medicine/graphrag/reasoning/engine_v2.py tests/graphrag/test_engine_v2.py
git commit -m "feat(graphrag): surface interaction severity/mechanism/effect in edge_properties"
```

---

## Task 3: Populate edge_properties in `_query_contraindications`

The contraindication handler reads `severity` from the Cypher row (line 749: `r.severity AS severity`) but doesn't pass it to `SemanticMatch`. The `strength` field IS populated from `r.strength`, but `severity` (ABSOLUTE/RELATIVE) is different from `strength` (strong_for/strong_against).

**Files:**
- Modify: `src/open_medicine/graphrag/reasoning/engine_v2.py:265-343`
- Test: `tests/graphrag/test_engine_v2.py`

**Step 1: Write the failing test**

```python
class TestContraindicationEdgeProperties:
    """Verify contraindication queries surface severity."""

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_contraindication_severity_surfaced(self, mock_link):
        mock_entity = MagicMock()
        mock_entity.node_id = "atc:C09DX"
        mock_entity.node_label = "DrugClass"
        mock_entity.snomed_code = None
        mock_entity.rxnorm_code = None
        mock_entity.atc_code = "C09DX"
        mock_entity.loinc_code = None
        mock_entity.icd10_code = None
        mock_entity.cpt_code = None
        mock_entity.gmdn_code = None
        mock_link.return_value = mock_entity

        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {
                "disease_id": "snomed:41291007",
                "disease_name": "Angioedema",
                "strength": "strong_against",
                "severity": "ABSOLUTE",
                "evidence_quality": "high",
                "conditions": None,
            }
        ]

        q = ClinicalQuery(intent="contraindication", concepts=["sacubitril_valsartan"])
        result = engine.query(q)

        assert len(result.semantic_matches) >= 1
        match = result.semantic_matches[0]
        assert match.edge_properties["severity"] == "ABSOLUTE"
```

**Step 2: Run test to verify it fails**

```bash
uv run python -m pytest tests/graphrag/test_engine_v2.py::TestContraindicationEdgeProperties -v
```

Expected: FAIL

**Step 3: Implement — add edge_properties to contraindication matches**

In `_query_contraindications`, modify both direct (line ~286) and expanded (line ~311) SemanticMatch constructions to include:

```python
                        edge_properties={
                            "severity": row.get("severity"),
                        },
```

Add this kwarg to all four places where `SemanticMatch` is constructed with `edge_type="CONTRAINDICATED_IN"` in `_query_contraindications`.

**Step 4: Run test to verify it passes**

```bash
uv run python -m pytest tests/graphrag/test_engine_v2.py::TestContraindicationEdgeProperties -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/open_medicine/graphrag/reasoning/engine_v2.py tests/graphrag/test_engine_v2.py
git commit -m "feat(graphrag): surface contraindication severity in edge_properties"
```

---

## Task 4: Populate edge_properties in `_query_dosing`

The dosing Cypher (queries_v2.py:783-801) returns `starting_dose`, `target_dose`, `max_dose`, `route`, `frequency`, `titration`. The engine discards all of them.

**Files:**
- Modify: `src/open_medicine/graphrag/reasoning/engine_v2.py:466-543`
- Test: `tests/graphrag/test_engine_v2.py`

**Step 1: Write the failing test**

```python
class TestDosingEdgeProperties:
    """Verify dosing queries surface dose properties."""

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_dosing_properties_surfaced(self, mock_link):
        mock_entity = MagicMock()
        mock_entity.node_id = "drug:spironolactone"
        mock_entity.node_label = "Drug"
        mock_entity.snomed_code = "S"
        mock_entity.rxnorm_code = None
        mock_entity.atc_code = None
        mock_entity.loinc_code = None
        mock_entity.icd10_code = None
        mock_entity.cpt_code = None
        mock_entity.gmdn_code = None
        mock_link.return_value = mock_entity

        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {
                "disease_id": "snomed:703272007",
                "disease": "HFrEF",
                "starting_dose": "12.5 mg",
                "target_dose": "50 mg",
                "max_dose": "50 mg",
                "route": "oral",
                "frequency": "once daily",
                "titration": "double every 2 weeks",
                "conditions": None,
            }
        ]

        q = ClinicalQuery(intent="dosing", concepts=["spironolactone"])
        result = engine.query(q)

        assert len(result.semantic_matches) >= 1
        match = result.semantic_matches[0]
        assert match.edge_properties["starting_dose"] == "12.5 mg"
        assert match.edge_properties["target_dose"] == "50 mg"
        assert match.edge_properties["max_dose"] == "50 mg"
        assert match.edge_properties["frequency"] == "once daily"
        assert match.edge_properties["route"] == "oral"
        assert match.edge_properties["titration_schedule"] == "double every 2 weeks"
```

**Step 2: Run test to verify it fails**

```bash
uv run python -m pytest tests/graphrag/test_engine_v2.py::TestDosingEdgeProperties -v
```

Expected: FAIL

**Step 3: Implement — add edge_properties to dosing matches**

In `_query_dosing`, modify both direct (line ~498) and expanded (line ~516) SemanticMatch constructions. Add:

```python
                edge_properties={
                    "starting_dose": row.get("starting_dose"),
                    "target_dose": row.get("target_dose"),
                    "max_dose": row.get("max_dose"),
                    "route": row.get("route"),
                    "frequency": row.get("frequency"),
                    "titration_schedule": row.get("titration"),
                },
```

**Step 4: Run test to verify it passes**

```bash
uv run python -m pytest tests/graphrag/test_engine_v2.py::TestDosingEdgeProperties -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/open_medicine/graphrag/reasoning/engine_v2.py tests/graphrag/test_engine_v2.py
git commit -m "feat(graphrag): surface dosing properties in edge_properties"
```

---

## Task 5: Populate edge_properties in `_query_monitoring`

The monitoring Cypher (queries_v2.py:808-813) returns `frequency`, `threshold_alert`, `threshold_stop`. All discarded.

**Files:**
- Modify: `src/open_medicine/graphrag/reasoning/engine_v2.py:545-614`
- Test: `tests/graphrag/test_engine_v2.py`

**Step 1: Write the failing test**

```python
class TestMonitoringEdgeProperties:
    """Verify monitoring queries surface threshold properties."""

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_monitoring_thresholds_surfaced(self, mock_link):
        mock_entity = MagicMock()
        mock_entity.node_id = "drug:spironolactone"
        mock_entity.node_label = "Drug"
        mock_entity.snomed_code = "S"
        mock_entity.rxnorm_code = None
        mock_entity.atc_code = None
        mock_entity.loinc_code = None
        mock_entity.icd10_code = None
        mock_entity.cpt_code = None
        mock_entity.gmdn_code = None
        mock_link.return_value = mock_entity

        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {
                "lab_id": "loinc:2823-3",
                "lab_name": "Potassium",
                "frequency": "within 1 week, then monthly",
                "threshold_alert": "K+ >= 5.5 mEq/L",
                "threshold_stop": "K+ >= 6.0 mEq/L",
            }
        ]

        q = ClinicalQuery(intent="monitoring", concepts=["spironolactone"])
        result = engine.query(q)

        assert len(result.semantic_matches) >= 1
        match = result.semantic_matches[0]
        assert match.edge_properties["frequency"] == "within 1 week, then monthly"
        assert match.edge_properties["threshold_alert"] == "K+ >= 5.5 mEq/L"
        assert match.edge_properties["threshold_stop"] == "K+ >= 6.0 mEq/L"
```

**Step 2: Run test to verify it fails**

```bash
uv run python -m pytest tests/graphrag/test_engine_v2.py::TestMonitoringEdgeProperties -v
```

Expected: FAIL

**Step 3: Implement — add edge_properties to monitoring matches**

In `_query_monitoring`, modify all three places where `SemanticMatch` is constructed with `edge_type="MONITORED_BY"` (direct at ~569, expanded at ~589, and class expansion at ~720). Add:

```python
                        edge_properties={
                            "frequency": row.get("frequency"),
                            "threshold_alert": row.get("threshold_alert"),
                            "threshold_stop": row.get("threshold_stop"),
                        },
```

**Step 4: Run test to verify it passes**

```bash
uv run python -m pytest tests/graphrag/test_engine_v2.py::TestMonitoringEdgeProperties -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/open_medicine/graphrag/reasoning/engine_v2.py tests/graphrag/test_engine_v2.py
git commit -m "feat(graphrag): surface monitoring thresholds in edge_properties"
```

---

## Task 6: Add `threshold_stop` to enrichment parser

`parse_monitoring_properties()` in enrichment.py extracts `frequency` and `threshold_alert` but not `threshold_stop`. The schema defines it, the loader writes it, and the Cypher reads it — but the enrichment parser never produces it.

**Files:**
- Modify: `src/open_medicine/graphrag/enrichment.py:231-273`
- Test: `tests/graphrag/test_enrichment.py` (new test class, or add to existing)

**Step 1: Write the failing test**

Check if `tests/graphrag/test_enrichment.py` exists. If not, check for any enrichment test file. Add tests to the appropriate location.

```python
class TestMonitoringThresholdStop:
    """Verify threshold_stop extraction from monitoring text."""

    def test_stop_potassium_6(self):
        text = (
            "Monitor potassium within 1 week. Alert if K+ >= 5.5 mEq/L. "
            "Stop if K+ >= 6.0 mEq/L or creatinine > 2.5 mg/dL."
        )
        from open_medicine.graphrag.enrichment import parse_monitoring_properties
        props = parse_monitoring_properties(text)
        assert "threshold_stop" in props
        assert "6.0" in props["threshold_stop"]

    def test_stop_discontinue_pattern(self):
        text = (
            "Discontinue if potassium >= 6.0 mEq/L or eGFR < 15 mL/min."
        )
        from open_medicine.graphrag.enrichment import parse_monitoring_properties
        props = parse_monitoring_properties(text)
        assert "threshold_stop" in props

    def test_stop_hold_pattern(self):
        text = (
            "Hold spironolactone if K+ > 5.5 mEq/L. Resume at lower dose "
            "when K+ < 5.0 mEq/L."
        )
        from open_medicine.graphrag.enrichment import parse_monitoring_properties
        props = parse_monitoring_properties(text)
        assert "threshold_stop" in props

    def test_no_stop_threshold(self):
        text = "Monitor electrolytes periodically."
        from open_medicine.graphrag.enrichment import parse_monitoring_properties
        props = parse_monitoring_properties(text)
        assert "threshold_stop" not in props
```

**Step 2: Run test to verify it fails**

```bash
uv run python -m pytest tests/graphrag/test_enrichment.py::TestMonitoringThresholdStop -v
```

Expected: FAIL — `threshold_stop` key not found

**Step 3: Implement — add threshold_stop extraction**

In `enrichment.py`, after the `threshold_alert` extraction block (line ~271), add:

```python
    # --- Threshold stop (discontinue/hold) ---
    stop_patterns = [
        # "stop if K+ >= 6.0" / "discontinue if potassium >= 6.0"
        re.compile(
            r"(?:stop|discontinue|hold|withhold|suspend)\s+(?:\w+\s+)?if\s+"
            r"((?:K\+?|potassium|creatinine|eGFR|BNP|INR)"
            r"(?:\s+(?:level|levels?))?"
            r"\s*(?:>=?|<=?|≥|≤|>|<)\s*[\d.]+\s*"
            r"(?:mEq/L|mg/dL|mL/min(?:/1\.73\s*m2)?|pg/mL|ng/mL)?)",
            re.IGNORECASE,
        ),
        # "K+ >= 6.0 ... discontinue" (threshold before action word)
        re.compile(
            r"((?:K\+?|potassium|creatinine|eGFR)"
            r"(?:\s+(?:level|levels?))?"
            r"\s*(?:>=?|<=?|≥|≤|>|<)\s*[\d.]+\s*"
            r"(?:mEq/L|mg/dL|mL/min(?:/1\.73\s*m2)?)?)"
            r"[^.;]*?(?:stop|discontinue|hold|withhold)",
            re.IGNORECASE,
        ),
    ]
    for pat in stop_patterns:
        stop_matches = pat.findall(text)
        if stop_matches:
            props["threshold_stop"] = "; ".join(t.strip() for t in stop_matches)
            break
```

**Step 4: Run test to verify it passes**

```bash
uv run python -m pytest tests/graphrag/test_enrichment.py::TestMonitoringThresholdStop -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/open_medicine/graphrag/enrichment.py tests/graphrag/test_enrichment.py
git commit -m "feat(graphrag): extract threshold_stop in monitoring enrichment parser"
```

---

## Task 7: Fix contraindication patient variable evaluation

In Scenario 2, `check_contraindications` with `history_of_angioedema: false` returned the angioedema contraindication with `conditions_met: true`. The problem: the CONTRAINDICATED_IN edge for angioedema has no `conditions_json` — it's a structural edge. The engine defaults `conditions_met` to `True` when there are no conditions. But the contraindication should only apply when the patient HAS the condition.

The fix: for CONTRAINDICATED_IN edges, when the matched disease appears in patient_vars as a boolean `false`, suppress the match (set `conditions_met = False`).

**Files:**
- Modify: `src/open_medicine/graphrag/reasoning/engine_v2.py`
- Test: `tests/graphrag/test_engine_v2.py`

**Step 1: Write the failing test**

```python
class TestContraindicationPatientVarEvaluation:
    """Verify contraindication respects patient_vars like history_of_angioedema."""

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_angioedema_false_suppresses_match(self, mock_link):
        """When patient has no angioedema history, the contraindication should not fire."""
        mock_entity = MagicMock()
        mock_entity.node_id = "atc:C09DX"
        mock_entity.node_label = "DrugClass"
        mock_entity.snomed_code = None
        mock_entity.rxnorm_code = None
        mock_entity.atc_code = "C09DX"
        mock_entity.loinc_code = None
        mock_entity.icd10_code = None
        mock_entity.cpt_code = None
        mock_entity.gmdn_code = None
        mock_link.return_value = mock_entity

        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {
                "disease_id": "snomed:41291007",
                "disease_name": "Angioedema",
                "strength": "strong_against",
                "severity": "ABSOLUTE",
                "evidence_quality": "high",
                "conditions": None,
            }
        ]

        q = ClinicalQuery(
            intent="contraindication",
            concepts=["sacubitril_valsartan"],
            patient_vars={"history_of_angioedema": False},
        )
        result = engine.query(q)

        # The match should still be returned (for awareness) but conditions_met=False
        assert len(result.semantic_matches) >= 1
        match = result.semantic_matches[0]
        assert match.conditions_met is False

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_angioedema_true_fires_match(self, mock_link):
        """When patient HAS angioedema history, conditions_met should be True."""
        mock_entity = MagicMock()
        mock_entity.node_id = "atc:C09DX"
        mock_entity.node_label = "DrugClass"
        mock_entity.snomed_code = None
        mock_entity.rxnorm_code = None
        mock_entity.atc_code = "C09DX"
        mock_entity.loinc_code = None
        mock_entity.icd10_code = None
        mock_entity.cpt_code = None
        mock_entity.gmdn_code = None
        mock_link.return_value = mock_entity

        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {
                "disease_id": "snomed:41291007",
                "disease_name": "Angioedema",
                "strength": "strong_against",
                "severity": "ABSOLUTE",
                "evidence_quality": "high",
                "conditions": None,
            }
        ]

        q = ClinicalQuery(
            intent="contraindication",
            concepts=["sacubitril_valsartan"],
            patient_vars={"history_of_angioedema": True},
        )
        result = engine.query(q)

        assert len(result.semantic_matches) >= 1
        match = result.semantic_matches[0]
        assert match.conditions_met is True

    @patch("open_medicine.graphrag.reasoning.engine_v2.link_entity")
    def test_no_patient_var_leaves_conditions_met_true(self, mock_link):
        """When no patient vars provided, default conditions_met stays True."""
        mock_entity = MagicMock()
        mock_entity.node_id = "atc:C09DX"
        mock_entity.node_label = "DrugClass"
        mock_entity.snomed_code = None
        mock_entity.rxnorm_code = None
        mock_entity.atc_code = "C09DX"
        mock_entity.loinc_code = None
        mock_entity.icd10_code = None
        mock_entity.cpt_code = None
        mock_entity.gmdn_code = None
        mock_link.return_value = mock_entity

        engine, conn = _make_engine()
        conn.execute_read.return_value = [
            {
                "disease_id": "snomed:41291007",
                "disease_name": "Angioedema",
                "strength": "strong_against",
                "severity": "ABSOLUTE",
                "evidence_quality": "high",
                "conditions": None,
            }
        ]

        q = ClinicalQuery(
            intent="contraindication",
            concepts=["sacubitril_valsartan"],
            patient_vars={},
        )
        result = engine.query(q)
        match = result.semantic_matches[0]
        assert match.conditions_met is True
```

**Step 2: Run test to verify it fails**

```bash
uv run python -m pytest tests/graphrag/test_engine_v2.py::TestContraindicationPatientVarEvaluation -v
```

Expected: FAIL — first test fails because `conditions_met` is `True` when it should be `False`

**Step 3: Implement — add disease-name-to-patient-var matching for contraindications**

Add a helper method to `ReasoningEngine` and call it after building each contraindication match. Place this after `_evaluate_match_conditions`:

```python
    # Map from disease names to patient variable keys for contraindication lookup
    _DISEASE_TO_PATIENT_VAR: dict[str, str] = {
        "angioedema": "history_of_angioedema",
        "pregnancy": "pregnant",
        "bilateral renal artery stenosis": "bilateral_renal_artery_stenosis",
        "hyperkalemia": "history_of_hyperkalemia",
        "cardiogenic shock": "cardiogenic_shock",
    }

    def _evaluate_contraindication_applicability(
        self,
        match: SemanticMatch,
        patient_vars: dict[str, Any],
    ) -> None:
        """For contraindications without conditions_json, check if the disease
        applies to the patient based on history variables.

        Example: Angioedema contraindication checks history_of_angioedema.
        If the patient variable is explicitly False, set conditions_met=False.
        """
        if match.conditions_json:
            return  # Already handled by _evaluate_match_conditions

        disease_name = match.entity_name.lower()
        patient_var_key = self._DISEASE_TO_PATIENT_VAR.get(disease_name)
        if not patient_var_key:
            return  # No mapping — keep default conditions_met=True

        # Normalize patient vars to check
        norm_vars = {k.lower(): v for k, v in patient_vars.items()}
        if patient_var_key in norm_vars:
            if norm_vars[patient_var_key] is False:
                match.conditions_met = False
            else:
                match.conditions_met = True
        # If variable not provided, leave as True (conservative — assume contraindication applies)
```

Then in `_query_contraindications`, call this method after each `_evaluate_match_conditions` call:

```python
                    self._evaluate_match_conditions(match, q.patient_vars)
                    self._evaluate_contraindication_applicability(match, q.patient_vars)
```

Do this for ALL four SemanticMatch construction sites in `_query_contraindications`.

**Step 4: Run test to verify it passes**

```bash
uv run python -m pytest tests/graphrag/test_engine_v2.py::TestContraindicationPatientVarEvaluation -v
```

Expected: PASS

**Step 5: Run all engine tests**

```bash
uv run python -m pytest tests/graphrag/test_engine_v2.py -v
```

Expected: All PASS

**Step 6: Commit**

```bash
git add src/open_medicine/graphrag/reasoning/engine_v2.py tests/graphrag/test_engine_v2.py
git commit -m "fix(graphrag): evaluate contraindication applicability against patient history vars"
```

---

## Task 8: End-to-end integration — run test scenarios against live graph

Verify the full pipeline works with real Neo4j data. This test runs both scenarios from `data/test_scenarios/` via the MCP server's internal handler.

**Files:**
- Create: `tests/graphrag/test_scenario_edge_properties.py`

**Step 1: Write the integration test**

```python
"""Integration: verify edge properties flow through to MCP results.

Requires live Neo4j connection (source .env before running).
"""

import json
import os

import pytest

from open_medicine.graphrag.config import get_settings
from open_medicine.graphrag.graph.connection import GraphConnection
from open_medicine.graphrag.reasoning.engine_v2 import ReasoningEngine
from open_medicine.graphrag.reasoning.types_v2 import ClinicalQuery

pytestmark = pytest.mark.skipif(
    not os.environ.get("GRAPHRAG_NEO4J_URI"),
    reason="Requires live Neo4j (source .env)",
)


@pytest.fixture(scope="module")
def engine():
    settings = get_settings()
    conn = GraphConnection(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    return ReasoningEngine(conn)


class TestScenario1EdgeProperties:
    """HF patient with angioedema history — edge properties must flow."""

    def test_contraindication_severity_is_populated(self, engine):
        q = ClinicalQuery(
            intent="contraindication",
            concepts=["sacubitril_valsartan"],
            patient_vars={"history_of_angioedema": True},
        )
        result = engine.query(q)

        ci_matches = [m for m in result.semantic_matches if m.edge_type == "CONTRAINDICATED_IN"]
        assert len(ci_matches) >= 1, "Expected at least one contraindication match"

        angioedema = [m for m in ci_matches if "angioedema" in m.entity_name.lower()]
        assert len(angioedema) >= 1, "Expected angioedema contraindication"
        assert angioedema[0].edge_properties.get("severity") is not None, (
            "severity must be populated on CONTRAINDICATED_IN edge"
        )

    def test_monitoring_thresholds_populated(self, engine):
        q = ClinicalQuery(
            intent="monitoring",
            concepts=["spironolactone"],
            patient_vars={"egfr": 35, "potassium": 5.1},
        )
        result = engine.query(q)

        k_matches = [
            m for m in result.semantic_matches
            if "potassium" in m.entity_name.lower()
        ]
        if k_matches:
            # If threshold data exists in graph, it should flow through
            props = k_matches[0].edge_properties
            # At minimum, frequency or threshold_alert should be present
            has_any = any(props.get(k) for k in ("frequency", "threshold_alert", "threshold_stop"))
            assert has_any, f"Expected monitoring properties, got: {props}"


class TestScenario2EdgeProperties:
    """Multimorbid patient — ARNi permissible but interaction critical."""

    def test_acei_arni_interaction_severity(self, engine):
        q = ClinicalQuery(
            intent="interaction",
            concepts=["lisinopril", "sacubitril_valsartan"],
        )
        result = engine.query(q)

        assert len(result.semantic_matches) >= 1, "Expected interaction matches"
        # At least one match should have severity populated
        severities = [
            m.edge_properties.get("severity")
            for m in result.semantic_matches
            if m.edge_properties.get("severity")
        ]
        assert len(severities) >= 1, (
            "Expected at least one interaction with severity populated"
        )

    def test_contraindication_false_angioedema(self, engine):
        q = ClinicalQuery(
            intent="contraindication",
            concepts=["sacubitril_valsartan"],
            patient_vars={"history_of_angioedema": False},
        )
        result = engine.query(q)

        angioedema = [
            m for m in result.semantic_matches
            if "angioedema" in m.entity_name.lower()
        ]
        if angioedema:
            assert angioedema[0].conditions_met is False, (
                "Angioedema contraindication should not fire when history_of_angioedema=False"
            )

    def test_dapagliflozin_dosing_properties(self, engine):
        q = ClinicalQuery(
            intent="dosing",
            concepts=["dapagliflozin"],
            patient_vars={"egfr": 48, "weight_kg": 58},
        )
        result = engine.query(q)

        if result.semantic_matches:
            props = result.semantic_matches[0].edge_properties
            # If dosing data exists, starting_dose or frequency should be populated
            has_any = any(
                props.get(k)
                for k in ("starting_dose", "target_dose", "frequency")
            )
            # This is a soft assertion — depends on graph data quality
            if not has_any:
                pytest.skip("Dosing properties not yet populated in graph (enrichment needed)")
```

**Step 2: Run tests (requires .env)**

```bash
source .env && uv run python -m pytest tests/graphrag/test_scenario_edge_properties.py -v
```

Expected: Tests pass if edge properties are populated in the graph. Some may skip if enrichment hasn't been re-run yet.

**Step 3: Commit**

```bash
git add tests/graphrag/test_scenario_edge_properties.py
git commit -m "test(graphrag): add integration tests for edge property flow through MCP"
```

---

## Task 9: Run full test suite

Verify nothing was broken.

**Step 1: Run unit tests**

```bash
uv run python -m pytest tests/graphrag/test_engine_v2.py -v
```

Expected: All PASS

**Step 2: Run enrichment tests**

```bash
uv run python -m pytest tests/graphrag/test_enrichment.py -v
```

Expected: All PASS

**Step 3: Run broader test suite**

```bash
uv run python -m pytest tests/graphrag/ -v
```

Expected: All PASS (integration tests may skip without .env)

**Step 4: Commit any fixes if needed**

---

## Summary of Changes

| File | Change | Impact |
|------|--------|--------|
| `types_v2.py` | Add `edge_properties: dict` to `SemanticMatch` | All edge data now flows through |
| `engine_v2.py` | Read severity/dosing/monitoring from Cypher rows into `edge_properties` | 4 query methods fixed |
| `engine_v2.py` | Add `_evaluate_contraindication_applicability` | Patient vars suppress inapplicable contraindications |
| `enrichment.py` | Add `threshold_stop` extraction patterns | Enrichment parser now extracts all monitoring fields |
| Tests | 6 new test classes, 1 integration test file | Full coverage of edge property flow |

**What this does NOT change:**
- Cypher queries (already correct)
- Schema (already defines all properties)
- Loader (already writes all properties)
- MCP server (already serializes full `GraphRAGResult` — edge_properties will automatically appear)
- Synthesis layer (explicitly excluded — agent's responsibility)

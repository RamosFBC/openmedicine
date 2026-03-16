# GraphRAG Safety Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix 7 critical-to-high severity safety gaps in the GraphRAG reasoning engine, loader, and schema that could lead to incorrect clinical decisions.

**Architecture:** Each fix is self-contained and testable in isolation. We modify types, schema, engine, loader, and enrichment — all within `src/open_medicine/graphrag/`. Every fix follows fail-safe defaults: when data is missing, the system must signal uncertainty, never silently pass.

**Tech Stack:** Python 3.10+, Pydantic, Neo4j Cypher, pytest. Run tests with `uv run python -m pytest`.

---

## Background: Safety Gaps Identified

| ID | Severity | Summary |
|----|----------|---------|
| C1 | CRITICAL | Missing safety variables treated as conditions_met=True |
| C2 | CRITICAL | Contraindication queries never return evidence_quality |
| C3 | CRITICAL | Interaction severity defaults to MODERATE (understates risk) |
| C4 | CRITICAL | Contraindication severity defaults to ABSOLUTE (cry-wolf) |
| C5 | HIGH | No dose-range plausibility validation in enrichment |
| C7 | CRITICAL | No distinction between "no contraindications" vs "no data" |
| H4 | HIGH | Vector fallback has no cosine similarity threshold |

---

### Task 1: Fix Missing-Variable Safety in Condition Evaluation (C1)

**Context:** When `conditions_json` has conditions like `{variable: "pregnancy", operator: "==", threshold: "false"}` and the patient_vars dict does NOT include "pregnancy", the system currently sets `conditions_met=True` because no condition explicitly failed. For safety-critical queries (contraindications, interactions), missing data should mean UNCERTAIN, not SAFE.

**Files:**
- Modify: `src/open_medicine/graphrag/reasoning/types_v2.py:40-61`
- Modify: `src/open_medicine/graphrag/reasoning/engine_v2.py:767-800`
- Modify: `src/open_medicine/graphrag/reasoning/engine_v2.py:879-924`
- Test: `tests/graphrag/test_engine_v2.py`

**Step 1: Write the failing tests**

Add to `tests/graphrag/test_engine_v2.py`:

```python
def test_missing_safety_variable_sets_conditions_met_none():
    """C1: Missing variables must NOT default to conditions_met=True."""
    engine = ReasoningEngine(mock_conn)

    match = SemanticMatch(
        entity_id="rxnorm:1364430",
        entity_name="Apixaban",
        entity_type="Drug",
        edge_type="CONTRAINDICATED_IN",
        strength="strong_against",
        evidence_quality="high",
        conditions_json='[{"variable": "pregnancy", "operator": "==", "threshold": "true"}]',
    )

    # Patient vars do NOT include pregnancy status
    engine._evaluate_match_conditions(match, {"lvef": 35})

    # conditions_met should be None (uncertain), NOT True
    assert match.conditions_met is None
    assert "pregnancy" in match.missing_variables


def test_all_conditions_met_returns_true():
    """Conditions fully evaluated and passing should return True."""
    engine = ReasoningEngine(mock_conn)

    match = SemanticMatch(
        entity_id="rxnorm:1364430",
        entity_name="Apixaban",
        entity_type="Drug",
        edge_type="INDICATED_FOR",
        strength="strong_for",
        evidence_quality="high",
        conditions_json='[{"variable": "lvef", "operator": "<=", "threshold": "40"}]',
    )

    engine._evaluate_match_conditions(match, {"lvef": 35})

    assert match.conditions_met is True
    assert match.missing_variables == []


def test_condition_explicitly_failed_returns_false():
    """Conditions fully evaluated and failing should return False."""
    engine = ReasoningEngine(mock_conn)

    match = SemanticMatch(
        entity_id="rxnorm:1364430",
        entity_name="Apixaban",
        entity_type="Drug",
        edge_type="INDICATED_FOR",
        strength="strong_for",
        evidence_quality="high",
        conditions_json='[{"variable": "lvef", "operator": "<=", "threshold": "40"}]',
    )

    engine._evaluate_match_conditions(match, {"lvef": 55})

    assert match.conditions_met is False
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py::test_missing_safety_variable_sets_conditions_met_none -v`
Expected: FAIL — `assert True is None`

**Step 3: Change `conditions_met` type from `bool` to `bool | None`**

In `src/open_medicine/graphrag/reasoning/types_v2.py`, change line 52-54:

```python
    conditions_met: bool | None = Field(
        default=True, description="Whether patient meets criteria. None = uncertain (missing variables)"
    )
```

Also update `RecommendationMatch` at line 73:

```python
    conditions_met: bool | None = Field(
        default=True,
        description="Whether patient meets criteria. None = uncertain (missing variables)",
    )
```

**Step 4: Fix `_evaluate_match_conditions` in engine_v2.py**

Replace lines 767-800:

```python
    def _evaluate_match_conditions(
        self, match: SemanticMatch, patient_vars: dict[str, Any]
    ) -> None:
        """Evaluate eligibility conditions against patient variables.

        Three-state result:
        - True: all conditions evaluated and passed
        - False: at least one condition explicitly failed
        - None: no condition failed, but one or more variables missing (uncertain)
        """
        if not match.conditions_json:
            return

        try:
            conditions = json.loads(match.conditions_json)
        except (json.JSONDecodeError, TypeError):
            return

        if not isinstance(conditions, list):
            return

        # Normalize patient variable keys to canonical forms via alias map
        norm_vars: dict[str, Any] = {}
        for k, v in patient_vars.items():
            canonical = self._normalize_var_name(k)
            norm_vars[canonical] = v

        missing: list[str] = []
        any_failed = False

        for cond in conditions:
            result = self._evaluate_condition(cond, norm_vars)
            if result is None:
                missing.append(cond.get("variable", ""))
            elif not result:
                any_failed = True

        match.missing_variables = missing

        if any_failed:
            match.conditions_met = False
        elif missing:
            match.conditions_met = None  # Uncertain — missing variables
        else:
            match.conditions_met = True
```

**Step 5: Update `_build_result` sorting to handle None**

In engine_v2.py, replace the sort key at lines 887-893:

```python
        # Sort by: layer priority, conditions_met (True first, None middle, False last), then strength
        def _sort_key(m: SemanticMatch) -> tuple:
            cm = m.conditions_met
            # True=0 (best), None=1 (uncertain), False=2 (failed)
            cm_rank = 0 if cm is True else (1 if cm is None else 2)
            return (
                _LAYER_RANK.get(m.source_layer, 99),
                cm_rank,
                STRENGTH_RANK.get(m.strength, 99),
            )

        semantic_matches.sort(key=_sort_key)
```

Update confidence logic at lines 899-909:

```python
        # Determine confidence
        full_matches = [m for m in semantic_matches if m.conditions_met is True]
        uncertain_matches = [m for m in semantic_matches if m.conditions_met is None]
        all_missing: list[str] = []
        for m in semantic_matches:
            all_missing.extend(m.missing_variables)

        if full_matches:
            confidence = "high"
        elif uncertain_matches:
            confidence = "medium"
        elif semantic_matches:
            confidence = "medium"
        else:
            confidence = "low"
```

**Step 6: Run all tests**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py -v`
Expected: ALL PASS

**Step 7: Commit**

```bash
git add src/open_medicine/graphrag/reasoning/types_v2.py src/open_medicine/graphrag/reasoning/engine_v2.py tests/graphrag/test_engine_v2.py
git commit -m "fix(graphrag): treat missing safety variables as uncertain, not passing (C1)"
```

---

### Task 2: Add `evidence_quality` to Contraindication and Interaction Queries (C2)

**Context:** `find_contraindications()` in queries_v2.py returns `r.strength, r.severity` but NOT `r.evidence_quality`. The engine then sets `evidence_quality=""` for all contraindication and interaction matches. This means consumers cannot distinguish a high-evidence contraindication from an expert-opinion one.

**Files:**
- Modify: `src/open_medicine/graphrag/graph/queries_v2.py:713-741`
- Modify: `src/open_medicine/graphrag/reasoning/engine_v2.py:226-298` (contraindications)
- Modify: `src/open_medicine/graphrag/reasoning/engine_v2.py:313-372` (interactions)
- Modify: `src/open_medicine/graphrag/graph/schema_v2.py:371-380` (add evidence_quality to ContraindicatedInProps)
- Modify: `src/open_medicine/graphrag/graph/schema_v2.py:383-391` (add evidence_quality to InteractsWithProps)
- Test: `tests/graphrag/test_engine_v2.py`
- Test: `tests/graphrag/test_queries_v2.py`

**Step 1: Write failing test**

Add to `tests/graphrag/test_engine_v2.py`:

```python
def test_contraindication_returns_evidence_quality():
    """C2: Contraindication matches must include evidence_quality from edge."""
    # Mock connection returns a row with evidence_quality
    mock = MockConnection([{
        "disease_id": "snomed:6296007",
        "disease_name": "Heart Failure",
        "strength": "strong_against",
        "severity": "absolute",
        "evidence_quality": "high",
        "conditions": None,
    }])
    engine = ReasoningEngine(mock)

    q = ClinicalQuery(
        intent="contraindication",
        concepts=["Apixaban"],
    )
    result = engine.query(q)

    assert result.semantic_matches
    assert result.semantic_matches[0].evidence_quality == "high"


def test_interaction_returns_evidence_quality():
    """C2: Interaction matches must include evidence_quality from edge."""
    mock = MockConnection([{
        "entity_id": "rxnorm:11289",
        "entity_name": "Warfarin",
        "entity_type": "Drug",
        "severity": "major",
        "evidence_quality": "moderate",
        "mechanism": "CYP2C9 inhibition",
        "clinical_effect": "increased bleeding risk",
    }])
    engine = ReasoningEngine(mock)

    q = ClinicalQuery(
        intent="interaction",
        concepts=["Aspirin"],
    )
    result = engine.query(q)

    assert result.semantic_matches
    assert result.semantic_matches[0].evidence_quality == "moderate"
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py::test_contraindication_returns_evidence_quality -v`
Expected: FAIL — evidence_quality is ""

**Step 3: Add `evidence_quality` to edge property models**

In `schema_v2.py`, add to `ContraindicatedInProps` (line ~375):

```python
class ContraindicatedInProps(BaseModel):
    """Properties on CONTRAINDICATED_IN edges."""
    strength: RecommendationStrength = Field(description="Recommendation strength")
    severity: ContraindicationSeverity = Field(description="Absolute or relative contraindication")
    evidence_quality: EvidenceQuality | None = Field(default=None, description="Evidence quality")
    conditions_json: str | None = Field(default=None, description="JSON-encoded eligibility criteria")
```

In `schema_v2.py`, add to `InteractsWithProps` (line ~387):

```python
class InteractsWithProps(BaseModel):
    """Properties on INTERACTS_WITH edges (Drug → Drug)."""
    severity: InteractionSeverity = Field(description="Interaction severity")
    evidence_quality: EvidenceQuality | None = Field(default=None, description="Evidence quality")
    mechanism: str | None = Field(default=None, description="Interaction mechanism")
    clinical_effect: str | None = Field(default=None, description="Clinical effect description")
```

**Step 4: Update Cypher queries to return `evidence_quality`**

In `queries_v2.py`, update `find_contraindications()` (line ~722) RETURN clause to include:
```
r.evidence_quality AS evidence_quality
```

In `queries_v2.py`, update `find_interactions()` (line ~737) RETURN clause to include:
```
r.evidence_quality AS evidence_quality
```

**Step 5: Update engine to read `evidence_quality` from rows**

In `engine_v2.py`, `_query_contraindications` method, change line 250:
```python
evidence_quality=row.get("evidence_quality", ""),
```

In `engine_v2.py`, `_query_interactions` method, change line 337 (and the expanded block ~line 354):
```python
evidence_quality=row.get("evidence_quality", ""),
```

**Step 6: Update loader to write evidence_quality on edges**

In `loader_v2.py`, `_create_semantic_edge` method, update the CONTRAINDICATED_IN block (line ~553):
```python
    elif edge_type == "CONTRAINDICATED_IN":
        props = ContraindicatedInProps(
            strength=RecommendationStrength(extraction.strength),
            severity=ContraindicationSeverity.ABSOLUTE,
            evidence_quality=EvidenceQuality(extraction.evidence_quality),
        )
```

Update `_create_interacts_with` (line ~596):
```python
    props = InteractsWithProps(
        severity=InteractionSeverity.MODERATE,
        evidence_quality=EvidenceQuality(extraction.evidence_quality),
    )
```

**Step 7: Run all tests**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py tests/graphrag/test_queries_v2.py tests/graphrag/test_schema_v2.py -v`
Expected: ALL PASS

**Step 8: Commit**

```bash
git add src/open_medicine/graphrag/graph/schema_v2.py src/open_medicine/graphrag/graph/queries_v2.py src/open_medicine/graphrag/reasoning/engine_v2.py src/open_medicine/graphrag/ingestion/loader_v2.py tests/graphrag/test_engine_v2.py tests/graphrag/test_queries_v2.py
git commit -m "fix(graphrag): propagate evidence_quality on contraindication and interaction edges (C2)"
```

---

### Task 3: Add UNKNOWN Severity Levels for Interactions and Contraindications (C3, C4)

**Context:** Interaction severity defaults to MODERATE (understates risk when unknown). Contraindication severity defaults to ABSOLUTE (overstates risk, causes alert fatigue). Both need an UNKNOWN level. The enrichment module should populate actual severity; the default should be UNKNOWN.

**Files:**
- Modify: `src/open_medicine/graphrag/graph/schema_v2.py:79-92`
- Modify: `src/open_medicine/graphrag/ingestion/loader_v2.py:555,596`
- Modify: `src/open_medicine/graphrag/enrichment.py`
- Test: `tests/graphrag/test_schema_v2.py`
- Test: `tests/graphrag/test_loader_v2.py`

**Step 1: Write failing tests**

Add to `tests/graphrag/test_schema_v2.py`:

```python
def test_interaction_severity_has_unknown():
    """C3: InteractionSeverity must have UNKNOWN value."""
    assert hasattr(InteractionSeverity, "UNKNOWN")
    assert InteractionSeverity.UNKNOWN == "unknown"


def test_contraindication_severity_has_unknown():
    """C4: ContraindicationSeverity must have UNKNOWN value."""
    assert hasattr(ContraindicationSeverity, "UNKNOWN")
    assert ContraindicationSeverity.UNKNOWN == "unknown"
```

Add to `tests/graphrag/test_loader_v2.py`:

```python
def test_interaction_defaults_to_unknown_severity():
    """C3: INTERACTS_WITH edges must default to UNKNOWN, not MODERATE."""
    # Create an interaction edge and verify default severity
    # (test the _create_interacts_with function)
    queries = []
    drug_a = LinkedEntity(
        canonical_name="Warfarin", entity_type="drug",
        node_label="Drug", node_id="rxnorm:11289",
    )
    drug_b = LinkedEntity(
        canonical_name="Aspirin", entity_type="drug",
        node_label="Drug", node_id="rxnorm:1191",
    )
    extraction = ExtractionResult(
        rec_id="test_001", rec_type="interaction",
        action="Avoid combination",
        action_detail="Risk of bleeding",
        strength="strong_against", evidence_quality="high",
        concepts=[], relationships=[], conditions=[],
    )
    _create_interacts_with(queries, drug_a, drug_b, extraction)

    # The query params should contain severity="unknown" (not "moderate")
    assert any("unknown" in str(q[1].values()) for q in queries)
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/graphrag/test_schema_v2.py::test_interaction_severity_has_unknown -v`
Expected: FAIL — `AttributeError: UNKNOWN`

**Step 3: Add UNKNOWN to severity enums**

In `schema_v2.py`, update `InteractionSeverity` (line 79):

```python
class InteractionSeverity(StrEnum):
    MAJOR = "major"
    MODERATE = "moderate"
    MINOR = "minor"
    UNKNOWN = "unknown"
```

Update `ContraindicationSeverity` (line 87):

```python
class ContraindicationSeverity(StrEnum):
    ABSOLUTE = "absolute"
    RELATIVE = "relative"
    UNKNOWN = "unknown"
```

**Step 4: Change defaults in loader**

In `loader_v2.py`, line 555, change:
```python
severity=ContraindicationSeverity.UNKNOWN,  # Enrichment will refine
```

In `loader_v2.py`, line 596, change:
```python
props = InteractsWithProps(severity=InteractionSeverity.UNKNOWN)
```

**Step 5: Update enrichment to populate severity, loader to use enriched values**

The enrichment module already parses severity — we need to ensure the loader applies enriched values. In `loader_v2.py`, `_create_semantic_edge`, after creating the edge, apply enrichment:

```python
    elif edge_type == "CONTRAINDICATED_IN":
        # Parse severity from action_detail via enrichment
        enriched = parse_contraindication_properties(extraction.action_detail)
        severity_str = enriched.get("severity")
        if severity_str:
            severity = ContraindicationSeverity(severity_str.lower())
        else:
            severity = ContraindicationSeverity.UNKNOWN
        props = ContraindicatedInProps(
            strength=RecommendationStrength(extraction.strength),
            severity=severity,
            evidence_quality=EvidenceQuality(extraction.evidence_quality),
        )
```

Similarly for interactions:
```python
def _create_interacts_with(...):
    enriched = parse_interaction_properties(extraction.action_detail)
    severity_str = enriched.get("severity")
    if severity_str:
        severity = InteractionSeverity(severity_str.lower())
    else:
        severity = InteractionSeverity.UNKNOWN
    props = InteractsWithProps(severity=severity)
```

**Step 6: Run all tests**

Run: `uv run python -m pytest tests/graphrag/test_schema_v2.py tests/graphrag/test_loader_v2.py tests/graphrag/test_enrichment.py -v`
Expected: ALL PASS

**Step 7: Commit**

```bash
git add src/open_medicine/graphrag/graph/schema_v2.py src/open_medicine/graphrag/ingestion/loader_v2.py tests/graphrag/test_schema_v2.py tests/graphrag/test_loader_v2.py
git commit -m "fix(graphrag): add UNKNOWN severity level, stop defaulting to MODERATE/ABSOLUTE (C3/C4)"
```

---

### Task 4: Add Dose Plausibility Validation to Enrichment (C5)

**Context:** The enrichment regex extracts dose strings but never validates that starting ≤ target ≤ max, or that values are within pharmacological plausibility. A regex misparse could silently produce dangerously wrong doses.

**Files:**
- Modify: `src/open_medicine/graphrag/enrichment.py`
- Test: `tests/graphrag/test_enrichment.py`

**Step 1: Write failing tests**

Add to `tests/graphrag/test_enrichment.py`:

```python
from open_medicine.graphrag.enrichment import validate_dose_consistency


def test_valid_dose_ordering():
    """C5: start <= target <= max should pass."""
    props = {"starting_dose": "5 mg", "target_dose": "50 mg", "max_dose": "200 mg"}
    issues = validate_dose_consistency(props)
    assert issues == []


def test_starting_exceeds_max_flagged():
    """C5: starting > max must be flagged."""
    props = {"starting_dose": "200 mg", "max_dose": "50 mg"}
    issues = validate_dose_consistency(props)
    assert len(issues) >= 1
    assert any("starting_dose" in i and "max_dose" in i for i in issues)


def test_target_exceeds_max_flagged():
    """C5: target > max must be flagged."""
    props = {"target_dose": "300 mg", "max_dose": "200 mg"}
    issues = validate_dose_consistency(props)
    assert len(issues) >= 1


def test_non_numeric_doses_skip_validation():
    """C5: Non-numeric doses (ranges, ratios) should not crash."""
    props = {"starting_dose": "24/26 mg", "target_dose": "97/103 mg"}
    issues = validate_dose_consistency(props)
    assert isinstance(issues, list)  # No crash


def test_parse_dosing_flags_inconsistency():
    """C5: parse_dosing_properties should include _validation_issues when doses are inconsistent."""
    text = "Start at 200 mg daily, maximum dose 50 mg"
    props = parse_dosing_properties(text)
    assert "_validation_issues" in props
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/graphrag/test_enrichment.py::test_valid_dose_ordering -v`
Expected: FAIL — `ImportError: cannot import name 'validate_dose_consistency'`

**Step 3: Implement dose validation**

Add to `src/open_medicine/graphrag/enrichment.py`:

```python
def _extract_numeric_mg(dose_str: str) -> float | None:
    """Extract the primary numeric value in mg from a dose string.

    Handles: "5 mg", "5-10 mg" (takes first), "24/26 mg" (takes first).
    Returns None if not parseable.
    """
    if not dose_str:
        return None
    # Extract first number
    m = re.search(r"([\d.]+)", dose_str)
    if not m:
        return None
    try:
        value = float(m.group(1))
    except ValueError:
        return None
    # Normalize to mg if units present
    lower = dose_str.lower()
    if "mcg" in lower:
        value /= 1000
    elif "g" in lower and "mg" not in lower and "mcg" not in lower:
        value *= 1000
    return value


def validate_dose_consistency(props: dict[str, str]) -> list[str]:
    """Validate that extracted dose values are internally consistent.

    Returns list of human-readable issues. Empty list = valid.
    """
    issues: list[str] = []

    start = _extract_numeric_mg(props.get("starting_dose", ""))
    target = _extract_numeric_mg(props.get("target_dose", ""))
    max_d = _extract_numeric_mg(props.get("max_dose", ""))

    if start is not None and max_d is not None and start > max_d:
        issues.append(
            f"starting_dose ({props['starting_dose']}) > max_dose ({props['max_dose']})"
        )

    if target is not None and max_d is not None and target > max_d:
        issues.append(
            f"target_dose ({props['target_dose']}) > max_dose ({props['max_dose']})"
        )

    if start is not None and target is not None and start > target:
        # This can be legitimate (titration from high to low), so warn only
        issues.append(
            f"starting_dose ({props['starting_dose']}) > target_dose ({props['target_dose']}) "
            f"— verify this is intentional (down-titration)"
        )

    return issues
```

**Step 4: Integrate validation into `parse_dosing_properties`**

At the end of `parse_dosing_properties()` (before `return props`), add:

```python
    # Validate dose consistency
    validation_issues = validate_dose_consistency(props)
    if validation_issues:
        props["_validation_issues"] = "; ".join(validation_issues)

    return props
```

**Step 5: Run tests**

Run: `uv run python -m pytest tests/graphrag/test_enrichment.py -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add src/open_medicine/graphrag/enrichment.py tests/graphrag/test_enrichment.py
git commit -m "fix(graphrag): add dose plausibility validation to enrichment (C5)"
```

---

### Task 5: Distinguish "No Data" from "No Contraindications" (C7)

**Context:** When the engine returns zero results for a contraindication query, the consumer cannot distinguish "checked and found no contraindications" from "we have no data about this drug." Both return `confidence="low"` with empty matches. For safety-critical queries, "no data" must be explicitly flagged.

**Files:**
- Modify: `src/open_medicine/graphrag/reasoning/types_v2.py:87-108`
- Modify: `src/open_medicine/graphrag/reasoning/engine_v2.py:879-924`
- Modify: `src/open_medicine/graphrag/reasoning/engine_v2.py:226-298`
- Test: `tests/graphrag/test_engine_v2.py`

**Step 1: Write failing tests**

Add to `tests/graphrag/test_engine_v2.py`:

```python
def test_no_data_flagged_for_unknown_drug_contraindication():
    """C7: Querying contraindications for an unknown drug must flag data_coverage='none'."""
    mock = MockConnection([])  # No results
    engine = ReasoningEngine(mock)

    q = ClinicalQuery(
        intent="contraindication",
        concepts=["CompletelyUnknownDrug12345"],
    )
    result = engine.query(q)

    assert result.data_coverage == "none"
    assert result.confidence == "low"


def test_known_drug_no_contraindications_flagged_as_partial():
    """C7: Known drug with no contraindications should flag data_coverage='partial' or 'full'."""
    mock = MockConnection([])  # No contraindication results, but drug exists
    engine = ReasoningEngine(mock)

    q = ClinicalQuery(
        intent="contraindication",
        concepts=["Apixaban"],  # Known drug in terminology
    )
    result = engine.query(q)

    # Drug exists in terminology, so we checked — just found nothing
    assert result.data_coverage in ("partial", "full")
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py::test_no_data_flagged_for_unknown_drug_contraindication -v`
Expected: FAIL — `AttributeError: data_coverage`

**Step 3: Add `data_coverage` field to GraphRAGResult**

In `types_v2.py`, add to `GraphRAGResult` (after line 108):

```python
    data_coverage: Literal["full", "partial", "none"] = Field(
        default="full",
        description=(
            "Whether queried entities exist in the graph. "
            "'none' = entity not found (cannot confirm safety). "
            "'partial' = some entities found. "
            "'full' = all queried entities found."
        ),
    )
```

**Step 4: Track entity resolution in engine query methods**

In `engine_v2.py`, update `_query_contraindications` to track which concepts resolved:

After the `for concept in q.concepts:` loop, before the vector fallback, add:

```python
        # Track data coverage — did we find the queried entities in our terminology?
        resolved_count = 0
        for concept in q.concepts:
            for entity_type in ("drug", "drug_class"):
                entity = link_entity(concept, entity_type)
                if entity and self._is_known_entity(entity):
                    resolved_count += 1
                    break
```

Pass `resolved_count` and `len(q.concepts)` into `_build_result`.

**Step 5: Update `_build_result` to compute `data_coverage`**

Add a `resolved_concepts` parameter to `_build_result`:

```python
    def _build_result(
        self,
        semantic_matches: list[SemanticMatch],
        evidence: list[EvidenceCitation],
        q: ClinicalQuery,
        resolved_concepts: int | None = None,
    ) -> GraphRAGResult:
```

Add data_coverage computation before the return:

```python
        # Determine data coverage
        total_concepts = len(q.concepts)
        if resolved_concepts is not None:
            if resolved_concepts == 0:
                data_coverage: Literal["full", "partial", "none"] = "none"
            elif resolved_concepts < total_concepts:
                data_coverage = "partial"
            else:
                data_coverage = "full"
        else:
            # Default: if we have results, we have data
            data_coverage = "full" if semantic_matches else "partial"

        return GraphRAGResult(
            source="graph_traversal",
            semantic_matches=semantic_matches,
            evidence=evidence,
            confidence=confidence,
            missing_variables=list(set(all_missing)),
            retrieval_layers_used=layers,
            hints=hints,
            data_coverage=data_coverage,
        )
```

**Step 6: Update all query methods to pass resolved_concepts**

Update `_query_contraindications`, `_query_interactions`, `_query_treatments`, `_query_dosing`, `_query_monitoring` to track and pass `resolved_concepts` to `_build_result`.

**Step 7: Run tests**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py -v`
Expected: ALL PASS

**Step 8: Commit**

```bash
git add src/open_medicine/graphrag/reasoning/types_v2.py src/open_medicine/graphrag/reasoning/engine_v2.py tests/graphrag/test_engine_v2.py
git commit -m "fix(graphrag): distinguish 'no data' from 'no contraindications found' (C7)"
```

---

### Task 6: Add Cosine Similarity Threshold to Vector Fallback (H4)

**Context:** The vector fallback returns all results from Neo4j's vector search with no minimum similarity threshold. A query about "acetaminophen" could return chunks about "aspirin" if nothing better exists. Results should have a minimum score and the score should be visible to consumers.

**Files:**
- Modify: `src/open_medicine/graphrag/reasoning/engine_v2.py:674-704`
- Modify: `src/open_medicine/graphrag/reasoning/types_v2.py:40-61`
- Test: `tests/graphrag/test_engine_v2.py`

**Step 1: Write failing tests**

Add to `tests/graphrag/test_engine_v2.py`:

```python
def test_vector_fallback_filters_low_similarity():
    """H4: Vector results below similarity threshold must be filtered out."""
    mock = MockConnection([
        {"entity_id": "rxnorm:1", "entity_name": "GoodMatch", "entity_type": "Drug",
         "strength": "strong_for", "evidence_quality": "high", "conditions": None, "score": 0.9},
        {"entity_id": "rxnorm:2", "entity_name": "WeakMatch", "entity_type": "Drug",
         "strength": "weak_for", "evidence_quality": "low", "conditions": None, "score": 0.3},
    ])
    engine = ReasoningEngine(mock)

    q = ClinicalQuery(intent="treatment_selection", concepts=["TestDrug"])
    matches = engine._vector_fallback(q)

    # Only the high-similarity match should pass (threshold default: 0.7)
    names = [m.entity_name for m in matches]
    assert "GoodMatch" in names
    assert "WeakMatch" not in names


def test_semantic_match_has_similarity_score():
    """H4: SemanticMatch should carry similarity_score for vector results."""
    match = SemanticMatch(
        entity_id="rxnorm:1", entity_name="Drug",
        entity_type="Drug", edge_type="INDICATED_FOR",
        strength="strong_for", evidence_quality="high",
        source_layer="vector", similarity_score=0.85,
    )
    assert match.similarity_score == 0.85
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py::test_semantic_match_has_similarity_score -v`
Expected: FAIL — `unexpected keyword argument 'similarity_score'`

**Step 3: Add `similarity_score` to SemanticMatch**

In `types_v2.py`, add after line 61:

```python
    similarity_score: float | None = Field(
        default=None,
        description="Cosine similarity score (0-1) for vector-sourced matches",
    )
```

**Step 4: Add threshold constant and filtering to vector fallback**

In `engine_v2.py`, add constant near the top (after `_LAYER_RANK`):

```python
# Minimum cosine similarity for vector fallback results
VECTOR_SIMILARITY_THRESHOLD = 0.7
```

Update `_vector_fallback` method:

```python
    def _vector_fallback(self, q: ClinicalQuery) -> list[SemanticMatch]:
        """Layer 3: Vector search over EvidenceChunks → entity traversal."""
        api_key = os.environ.get("VOYAGE_API_KEY", "")
        try:
            query_text = f"{q.intent} {' '.join(q.concepts)}"
            embedding = embed_query(query_text, api_key=api_key)
        except Exception:
            logger.debug("Vector fallback skipped: embedding failed")
            return []

        rec_type = self._INTENT_TO_REC_TYPE.get(q.intent)
        cypher, params = ReasoningQueries.vector_entity_search(
            embedding, rec_type=rec_type, limit=10
        )
        rows = self._conn.execute_read(cypher, params)

        matches: list[SemanticMatch] = []
        for row in rows:
            score = row.get("score", 0.0)
            if score < VECTOR_SIMILARITY_THRESHOLD:
                continue  # Filter low-confidence vector matches
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
                    similarity_score=score,
                )
            )
        return matches
```

**Step 5: Run tests**

Run: `uv run python -m pytest tests/graphrag/test_engine_v2.py -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add src/open_medicine/graphrag/reasoning/types_v2.py src/open_medicine/graphrag/reasoning/engine_v2.py tests/graphrag/test_engine_v2.py
git commit -m "fix(graphrag): add cosine similarity threshold to vector fallback (H4)"
```

---

### Task 7: Run Full Test Suite and Verify No Regressions

**Files:**
- No new files

**Step 1: Run the complete test suite**

Run: `uv run python -m pytest tests/ -v --tb=short`
Expected: ALL PASS (no regressions)

**Step 2: Run GraphRAG tests specifically**

Run: `uv run python -m pytest tests/graphrag/ -v`
Expected: ALL PASS

**Step 3: If any failures, fix them before proceeding**

Common things to check:
- Existing tests that compare `conditions_met` to `True` (bool) may need updating for `True | None` type
- Existing tests that hardcode `evidence_quality=""` for contraindications need updating
- Schema tests that enumerate `InteractionSeverity` / `ContraindicationSeverity` values need to include `UNKNOWN`

**Step 4: Commit any test fixes**

```bash
git add -u
git commit -m "test(graphrag): update existing tests for safety hardening changes"
```

---

## Summary of Changes

| Task | Fix ID | Files Changed | Impact |
|------|--------|---------------|--------|
| 1 | C1 | types_v2.py, engine_v2.py | Missing vars → uncertain, not passing |
| 2 | C2 | schema_v2.py, queries_v2.py, engine_v2.py, loader_v2.py | evidence_quality on all edge types |
| 3 | C3/C4 | schema_v2.py, loader_v2.py | UNKNOWN severity level, enrichment-driven defaults |
| 4 | C5 | enrichment.py | Dose plausibility validation |
| 5 | C7 | types_v2.py, engine_v2.py | data_coverage field distinguishes no-data vs no-results |
| 6 | H4 | types_v2.py, engine_v2.py | Vector similarity threshold + score on matches |
| 7 | — | tests/ | Full regression check |

## NOT in scope (future work)

- H1: Version pinning / temporal validity on edges
- H2: Enrichment validation against pharmacological databases
- H3: Drug class inheritance exclusion mechanism
- H5: Terminology expansion beyond cardiology
- H6: Bidirectional interaction queries
- M1-M5: Audit logging, dead schema cleanup, multi-guideline testing, graph constraints, embedding API resilience

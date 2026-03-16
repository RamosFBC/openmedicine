# Ingest Guideline into GraphRAG

Orchestrate the full pipeline to ingest a clinical guideline PDF/markdown into the Neo4j knowledge graph using Claude Code agents instead of API calls.

## Usage

```
/ingest-guideline <guideline_file> <guideline_id> <doi>
```

Example:
```
/ingest-guideline data/guidelines/aha_acc_hf_2022.md aha_acc_hf_2022 10.1161/CIR.0000000000001063
```

## Pipeline

### Phase 0: Prepare

1. Parse arguments: `$ARGUMENTS` contains `<file> <id> <doi>`
2. Verify the markdown file exists
3. Clear previous extraction cache for this guideline: `data/cache/graphrag/{guideline_id}/`
4. Ensure Neo4j indexes exist by running:
   ```bash
   uv run python -c "
   from dotenv import load_dotenv; load_dotenv()
   from open_medicine.graphrag.config import get_settings
   from open_medicine.graphrag.graph.connection import GraphConnection
   from open_medicine.graphrag.ingest_v2 import ensure_indexes
   settings = get_settings()
   with GraphConnection(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password) as conn:
       ensure_indexes(conn)
   print('Indexes ready')
   "
   ```

### Phase 1: Section Discovery

Read the guideline markdown and identify all clinical sections worth extracting. Skip:
- Table of contents, preamble, methodology, abbreviations, appendices, references
- Writing committee members, acknowledgments

Focus on sections that contain clinical recommendations:
- Numbered sections (2.x through 14.x) that have "Recommendation" or "Synopsis" subsections
- Drug therapy sections (dosing tables, COR/LOE tables)
- Management sections
- Comorbidity sections

For each section, record:
- `section_id`: e.g. "7_3_1"
- `section_title`: e.g. "Renin-Angiotensin System Inhibition With ACEi or ARB or ARNi"
- `start_line`: line number in the markdown
- `end_line`: line number (start of next same-level section)

Write the section map to `data/cache/graphrag/{guideline_id}/sections.json`.

### Phase 2: Typed Parallel Section Extraction

Create output directory: `data/cache/graphrag/{guideline_id}/extractions/`

For each section, launch **7 typed extractor agents** — one per `rec_type_focus`:
- `dosing` — doses, titration, frequency, route
- `monitoring` — lab monitoring, thresholds, frequency
- `contraindication` — true contraindications only (not safety warnings)
- `interaction` — drug-drug interactions
- `treatment_selection` — recommended therapies, first-line agents
- `diagnostic_criteria` — staging definitions, classification thresholds, biomarker cutoffs
- `safety_warning` — conditional restrictions, withdrawal warnings, agent-selection constraints

Each agent receives the full instructions from `.claude/agents/graphrag-typed-extractor.md`
embedded in its prompt, plus these parameters:
- `guideline_file`: path to the markdown
- `section_start_line` and `section_end_line`
- `section_id` and `section_title`
- `guideline_id`
- `rec_type_focus`: one of the 5 types above
- `output_file`: `data/cache/graphrag/{guideline_id}/extractions/{section_id}_{rec_type_focus}.jsonl`
- `terminology_dir`: `src/open_medicine/graphrag/terminology/`

**IMPORTANT**: The agent type must be `general-purpose` (not a custom agent type).
Read the typed extractor agent doc and embed its full instructions in the agent prompt.

**Batch size**: 5 agents at a time (to stay within parallel limits).
For each section, launch 2 batches: first 5 types, then remaining 2.
**Wait for each batch to complete before launching the next.**

Recommended batching per section:
- Batch A (5): dosing, monitoring, contraindication, interaction, treatment_selection
- Batch B (2): diagnostic_criteria, safety_warning

After all batches complete, verify each output file exists.
Empty files are expected (not every section has every rec_type).
Report: "Extracted {N} rules from {M} sections across 7 rec_types."

### Phase 2.3: Typed Extraction Validation Gate

Run the type-specific validation gate on the raw typed extractions:

```bash
uv run python -c "
from pathlib import Path
from open_medicine.graphrag.extraction_validator import validate_directory

extraction_dir = Path('data/cache/graphrag/{guideline_id}/extractions/')
terminology_dir = Path('src/open_medicine/graphrag/terminology/')

result = validate_directory(extraction_dir, terminology_dir=terminology_dir)
print(result.summary())

if result.rejected > 0:
    print(f'\nWARNING: {result.rejected} rules rejected — review issues above')
    # List files with rejections for targeted re-extraction
    from collections import Counter
    files_with_errors = Counter()
    for issue in result.issues:
        if issue.severity == 'error':
            files_with_errors[issue.rec_id.rsplit('_', 1)[0]] += 1
    print('Files to re-extract:')
    for f, count in files_with_errors.most_common():
        print(f'  {f}: {count} errors')
"
```

**Type-specific checks (handled by the validator):**
- **Dosing**: rejects rules with no dose values (starting_dose, target_dose, or max_dose)
- **Monitoring**: rejects rules with no frequency
- **Contraindication**: rejects rules with no severity; warns on likely safety_warnings
- **Interaction**: rejects rules with no severity
- **All types**: rejects rules with empty `relationships` or empty `concepts`

**Quality criteria to proceed:**
- Pass rate > 80% (accepted / total)
- Zero pregnancy contraindications targeting managed disease instead of Pregnancy
- If pass rate < 80%, re-run the failing typed extractors with explicit correction instructions

### Phase 2.5: Legacy Quality Gate (Concept Validation)

Before proceeding to normalization, run a **strict quality gate** on the raw extractions:

```python
import json
from pathlib import Path
from collections import Counter

terminology_dir = Path("src/open_medicine/graphrag/terminology/")

# Load all valid concept names from terminology
valid_names = set()
for fname in ["drugs.json", "drug_classes.json", "diseases.json", "labs.json",
              "procedures.json", "devices.json", "symptoms.json"]:
    data = json.loads((terminology_dir / fname).read_text())
    for canonical, entry in data.items():
        valid_names.add(canonical.lower())
        for alias in entry.get("aliases", []):
            valid_names.add(alias.lower())

type_counts = Counter()
not_in_terminology = []
contraindication_warnings = []

for f in sorted(Path("data/cache/graphrag/{guideline_id}/extractions/").glob("*.jsonl")):
    for line in f.read_text().splitlines():
        if not line.strip(): continue
        rule = json.loads(line)
        rec_type = rule.get("rec_type", "")

        for c in rule.get("concepts", []):
            name = c.get("name", "")
            ctype = c.get("type", "unknown")
            type_counts[ctype] += 1
            if name.lower() not in valid_names:
                not_in_terminology.append(f"{name} ({ctype}) in {f.stem}")

        # Check for misclassified contraindications
        if rec_type == "contraindication":
            action = rule.get("action", "").lower()
            if any(w in action for w in ["withdraw", "abrupt", "exclude", "caution", "other than"]):
                contraindication_warnings.append(f"{rule.get('rec_id', '')}: {rule.get('action', '')}")

print(f"Concept types: {dict(type_counts)}")
print(f"\nConcepts NOT in terminology ({len(not_in_terminology)}):")
for item in not_in_terminology[:20]:
    print(f"  - {item}")
if len(not_in_terminology) > 20:
    print(f"  ... and {len(not_in_terminology) - 20} more")

print(f"\nMisclassified contraindications ({len(contraindication_warnings)}):")
for item in contraindication_warnings:
    print(f"  - {item}")
```

**Additional checks — run these BEFORE proceeding:**

```python
# Check for pregnancy contraindications targeting managed disease instead of Pregnancy
pregnancy_issues = []
indicated_drugs = set()  # drugs that appear in treatment_selection recs

for f in sorted(Path(f"data/cache/graphrag/{guideline_id}/extractions/").glob("*.jsonl")):
    for line in f.read_text().splitlines():
        if not line.strip(): continue
        rule = json.loads(line)
        if rule.get("rec_type") == "treatment_selection":
            for c in rule.get("concepts", []):
                if c.get("role") == "subject":
                    indicated_drugs.add(c["name"])

for f in sorted(Path(f"data/cache/graphrag/{guideline_id}/extractions/").glob("*.jsonl")):
    for line in f.read_text().splitlines():
        if not line.strip(): continue
        rule = json.loads(line)
        if rule.get("rec_type") != "contraindication": continue
        action = rule.get("action", "").lower()

        # Check pregnancy contraindications targeting wrong disease
        if "pregnan" in action:
            targets = [c for c in rule.get("concepts", []) if c.get("role") == "target"]
            if targets and not any(t["name"] == "Pregnancy" for t in targets):
                pregnancy_issues.append(f"{rule.get('rec_id')}: targets {[t['name'] for t in targets]} instead of Pregnancy")

        # Check if contraindicated drug is also indicated (conditional contraindication)
        subjects = [c["name"] for c in rule.get("concepts", []) if c.get("role") == "subject"]
        for s in subjects:
            if s in indicated_drugs:
                contraindication_warnings.append(
                    f"{rule.get('rec_id')}: {s} is also in treatment_selection — likely safety_warning"
                )

print(f"\nPregnancy contraindication target issues ({len(pregnancy_issues)}):")
for item in pregnancy_issues:
    print(f"  - {item}")

print(f"\nContraindicated drugs that are also indicated ({len(contraindication_warnings)}):")
for item in contraindication_warnings[:20]:
    print(f"  - {item}")
```

**Quality criteria to proceed:**
- Concepts NOT in terminology should be < 10% of total concepts
- Zero misclassified contraindications (safety warnings tagged as contraindication)
- No single concept type > 50%
- Zero pregnancy contraindications targeting managed disease instead of Pregnancy
- Contraindicated-but-also-indicated drugs should be reviewed — most should be safety_warning

If quality gate fails, identify the problematic sections and re-run those extractors
with explicit correction instructions.

### Phase 3: Concept Normalization

Launch a single `general-purpose` agent with the full instructions from
`.claude/agents/graphrag-concept-normalizer.md` embedded in its prompt, plus:
- `extraction_dir`: `data/cache/graphrag/{guideline_id}/extractions/`
- `output_file`: `data/cache/graphrag/{guideline_id}/consolidated.jsonl`
- `guideline_id`
- `terminology_dir`: `src/open_medicine/graphrag/terminology/`

**IMPORTANT**: The agent type must be `general-purpose` (not a custom agent type).

The normalizer will:
1. Drop ALL concepts not in terminology files
2. Fix concept types to match terminology
3. Reclassify safety warnings that were mistagged as contraindications
4. Deduplicate and merge aliases
5. Detect drug-drug interactions and conflicting recommendations

### Phase 4: Load into Neo4j

Use `ingest_v2.py load` to load the consolidated JSONL:

```bash
uv run python -m open_medicine.graphrag.ingest_v2 load \
    --jsonl data/cache/graphrag/{guideline_id}/consolidated.jsonl \
    --file {guideline_file} \
    --id {guideline_id} \
    --doi {doi} \
    --title "{title}" \
    --year {year} \
    --org "{organization}"
```

Or use `migrate` to clear and reload:
```bash
uv run python -m open_medicine.graphrag.ingest_v2 migrate \
    --jsonl data/cache/graphrag/{guideline_id}/consolidated.jsonl \
    --file {guideline_file} \
    --id {guideline_id} \
    --doi {doi} \
    --title "{title}" \
    --year {year} \
    --org "{organization}"
```

### Phase 4.5: Generate Test Scenarios

Generate clinical test scenarios from the consolidated JSONL:
```bash
uv run python -m open_medicine.graphrag.ingest_v2 generate-scenarios \
    --jsonl data/cache/graphrag/{guideline_id}/consolidated.jsonl \
    --output data/cache/graphrag/{guideline_id}/test_scenarios.json
```

This derives scenarios automatically from the extractions:
- **treatment_selection** recs → expect drug INDICATED_FOR disease
- **contraindication** recs → expect drug CONTRAINDICATED_IN disease
- **monitoring** recs → expect drug MONITORED_BY lab (specific drugs only, not drug classes)
- **dosing** recs → expect drug DOSED_FOR disease
- **negative tests** → first-line drugs should NOT be contraindicated for their indicated diseases

Only concepts that exist in terminology files are included (matching what the loader creates).

### Phase 4.6: Generate Embeddings (optional)

If `VOYAGE_API_KEY` is set, generate vector embeddings for evidence chunks:
```bash
uv run python -m open_medicine.graphrag.ingest_v2 embed
```

This enables Layer 3 vector fallback in the ReasoningEngine.
If the API key is not set, this step is skipped — the engine degrades gracefully.

### Phase 4.7: Enrich Edge Properties (REQUIRED)

Run the enrichment module to populate structured properties on graph edges:

```
/enrich-graph {guideline_id}
```

This extracts structured properties (doses, frequencies, thresholds, severities)
from the prose in action_detail fields and patches them onto the corresponding
Neo4j edge properties.

**This phase is MANDATORY.** Without enrichment, DOSED_FOR edges have empty
starting_dose/target_dose/frequency, CONTRAINDICATED_IN edges lack severity
classifications, and the graph cannot support clinical decision-making.

### Phase 4.8: Post-Enrichment Quality Gate (REQUIRED)

After enrichment, run this validation to ensure A+ edge property coverage:

```bash
uv run python -c "
from dotenv import load_dotenv; load_dotenv()
from open_medicine.graphrag.config import get_settings
from open_medicine.graphrag.graph.connection import GraphConnection

settings = get_settings()
with GraphConnection(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password) as conn:
    failures = []

    # DOSED_FOR: starting_dose >= 90%, frequency >= 80%
    rows = conn.execute_read('''
        MATCH ()-[r:DOSED_FOR]->()
        RETURN count(r) AS total,
            sum(CASE WHEN r.starting_dose IS NOT NULL THEN 1 ELSE 0 END) AS has_start,
            sum(CASE WHEN r.target_dose IS NOT NULL THEN 1 ELSE 0 END) AS has_target,
            sum(CASE WHEN r.frequency IS NOT NULL THEN 1 ELSE 0 END) AS has_freq
    ''')
    r = rows[0]
    total = r['total']
    if total > 0:
        start_pct = r['has_start'] / total * 100
        target_pct = r['has_target'] / total * 100
        freq_pct = r['has_freq'] / total * 100
        print(f'DOSED_FOR: starting_dose={start_pct:.0f}%, target_dose={target_pct:.0f}%, frequency={freq_pct:.0f}%')
        if start_pct < 90: failures.append(f'DOSED_FOR.starting_dose={start_pct:.0f}% (need >=90%)')
        if freq_pct < 80: failures.append(f'DOSED_FOR.frequency={freq_pct:.0f}% (need >=80%)')

    # CONTRAINDICATED_IN: severity = 100%
    rows = conn.execute_read('''
        MATCH ()-[r:CONTRAINDICATED_IN]->()
        RETURN count(r) AS total,
            sum(CASE WHEN r.severity IS NOT NULL THEN 1 ELSE 0 END) AS has_sev
    ''')
    r = rows[0]
    if r['total'] > 0:
        sev_pct = r['has_sev'] / r['total'] * 100
        print(f'CONTRAINDICATED_IN: severity={sev_pct:.0f}%')
        if sev_pct < 100: failures.append(f'CONTRAINDICATED_IN.severity={sev_pct:.0f}% (need 100%)')

    # INTERACTS_WITH: severity = 100%
    rows = conn.execute_read('''
        MATCH ()-[r:INTERACTS_WITH]->()
        RETURN count(r) AS total,
            sum(CASE WHEN r.severity IS NOT NULL THEN 1 ELSE 0 END) AS has_sev
    ''')
    r = rows[0]
    if r['total'] > 0:
        sev_pct = r['has_sev'] / r['total'] * 100
        print(f'INTERACTS_WITH: severity={sev_pct:.0f}%')
        if sev_pct < 100: failures.append(f'INTERACTS_WITH.severity={sev_pct:.0f}% (need 100%)')

    # MONITORED_BY: threshold_alert >= 30%
    rows = conn.execute_read('''
        MATCH ()-[r:MONITORED_BY]->()
        RETURN count(r) AS total,
            sum(CASE WHEN r.threshold_alert IS NOT NULL THEN 1 ELSE 0 END) AS has_alert
    ''')
    r = rows[0]
    if r['total'] > 0:
        alert_pct = r['has_alert'] / r['total'] * 100
        print(f'MONITORED_BY: threshold_alert={alert_pct:.0f}%')
        if alert_pct < 30: failures.append(f'MONITORED_BY.threshold_alert={alert_pct:.0f}% (need >=30%)')

    # Clinical value spot-checks
    # 1. Angioedema contraindications must be ABSOLUTE for ACEi/ARNi
    rows = conn.execute_read('''
        MATCH (d)-[r:CONTRAINDICATED_IN]->(c)
        WHERE c.name = 'Angioedema' AND r.severity IS NOT NULL
            AND (d.name IN ['ACE Inhibitor', 'Sacubitril/Valsartan'] OR d.name = 'ARNi')
        RETURN d.name, r.severity
    ''')
    for row in rows:
        if row['r.severity'].upper() != 'ABSOLUTE':
            failures.append(f'{row[\"d.name\"]} -> Angioedema severity={row[\"r.severity\"]} (must be ABSOLUTE)')

    # 2. ACEi <-> ARNi interaction must be MAJOR
    rows = conn.execute_read('''
        MATCH (d1)-[r:INTERACTS_WITH]->(d2)
        WHERE (d1.name = 'ACE Inhibitor' AND d2.name = 'ARNi')
           OR (d1.name = 'Sacubitril/Valsartan' AND d2.name = 'ACE Inhibitor')
        RETURN d1.name, d2.name, r.severity
    ''')
    for row in rows:
        if row['r.severity'] != 'MAJOR':
            failures.append(f'{row[\"d1.name\"]} <-> {row[\"d2.name\"]} severity={row[\"r.severity\"]} (must be MAJOR)')

    # 3. Cross-contamination check: drug-specific dosing shouldn't match combination product
    rows = conn.execute_read('''
        MATCH (d:Drug)-[r:DOSED_FOR]->()
        WHERE d.name = 'Valsartan' AND r.starting_dose CONTAINS '49'
        RETURN d.name, r.starting_dose
    ''')
    for row in rows:
        failures.append(f'Valsartan has Sacubitril/Valsartan dose ({row[\"r.starting_dose\"]})')

    if failures:
        print(f'\nFAILED — {len(failures)} issues:')
        for f in failures:
            print(f'  ✗ {f}')
        print('\nFix these issues before proceeding to Phase 5.')
        raise SystemExit(1)
    else:
        print('\nPASSED — all edge property quality gates met')
"
```

**Quality criteria to proceed:**
- DOSED_FOR.starting_dose ≥ 90%
- DOSED_FOR.frequency ≥ 80%
- CONTRAINDICATED_IN.severity = 100%
- INTERACTS_WITH.severity = 100%
- MONITORED_BY.threshold_alert ≥ 30%
- Angioedema contraindications for ACEi/ARNi = ABSOLUTE
- ACEi ↔ ARNi interaction = MAJOR
- No cross-contamination of combination product doses

If quality gate fails, fix issues (re-run enrichment, patch specific edges)
and re-run this gate before proceeding.

### Phase 5: Validate

#### Step 1: Structural validation

Run the built-in structural checks:
```bash
uv run python -m open_medicine.graphrag.ingest_v2 validate
```

#### Step 2: Scenario validation

Run the generated test scenarios against the loaded graph:
```bash
uv run python -m open_medicine.graphrag.ingest_v2 scenarios \
    --file data/cache/graphrag/{guideline_id}/test_scenarios.json
```

This fires each scenario through the `ReasoningEngine` and validates:
- Minimum result counts
- Expected entities present in results
- Correct edge types (INDICATED_FOR, CONTRAINDICATED_IN, etc.)
- Absent entities that should NOT appear (false positive detection)

**The command exits with code 1 if any scenario fails.**

**Quality criteria to pass:**
- All scenarios pass (0 failures)
- If scenarios fail, review the specific issues and either:
  1. Fix the consolidated JSONL and re-load (Phase 4)
  2. Update the test scenario if the expectation was wrong

#### Step 3: Deep validation (optional)

For a comprehensive audit with scoring, launch the validator agent:

Launch a `general-purpose` agent with the full instructions from
`.claude/agents/graphrag-validator.md` embedded in its prompt, plus:
- `guideline_id`
- `terminology_dir`: `src/open_medicine/graphrag/terminology/`
- `test_scenarios_file`: `data/cache/graphrag/{guideline_id}/test_scenarios.json`

**IMPORTANT**: The agent type must be `general-purpose` (not a custom agent type).
Read the validator agent doc and embed its full instructions in the agent prompt.

The validator runs Tier 1 (structural Cypher checks) + Tier 2 (clinical scenario tests)
and produces a scored report. **Grade B+ (≥75/100) = pass.**

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

### Phase 2: Parallel Section Extraction

Create output directory: `data/cache/graphrag/{guideline_id}/extractions/`

Launch `general-purpose` agents in parallel batches. Each agent receives the full
instructions from `.claude/agents/graphrag-section-extractor.md` embedded in its prompt,
plus these parameters:
- `guideline_file`: path to the markdown
- `section_start_line` and `section_end_line`
- `section_id` and `section_title`
- `guideline_id`
- `output_file`: `data/cache/graphrag/{guideline_id}/extractions/{section_id}.jsonl`
- `terminology_dir`: `src/open_medicine/graphrag/terminology/`

**IMPORTANT**: The agent type must be `general-purpose` (not a custom agent type).
Read the extractor agent doc and embed its full instructions in the agent prompt.

**Batch size**: 5 agents at a time (to stay within parallel limits).
**Wait for each batch to complete before launching the next.**

After all batches complete, verify each output file exists and has content.
Report: "Extracted {N} rules from {M} sections."

### Phase 2.5: Extraction Quality Gate

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

### Phase 4.7: Enrich Edge Properties

Run the enrichment module to populate structured properties on graph edges:

```
/enrich-graph {guideline_id}
```

This extracts structured properties (doses, frequencies, thresholds, severities)
from the prose in action_detail fields and patches them onto the corresponding
Neo4j edge properties. Skip if enrichment is not needed.

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

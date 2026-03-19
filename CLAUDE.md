# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Open Medicine is a Python library and MCP Server providing deterministic, DOI-traceable clinical calculators and guideline retrieval for AI agents. Every output includes scientific citations (DOIs) and FHIR-compatible codes to prevent hallucinations in medical contexts.

## Commands

```bash
uv sync --extra test                    # Install all dependencies
uv sync --extra test --extra embeddings # Install with embedding support (httpx)
uv run python -m pytest -v              # Run fast tests (skips Hypothesis fuzz + integration)
uv run python -m pytest -v --runslow   # Run ALL tests including slow (CI mode)
uv run python -m pytest tests/test_chadsvasc.py -v                          # Single test file
uv run python -m pytest tests/test_chadsvasc.py::test_chadsvasc_max_score -v  # Single test
uv run python -m pytest -k "chadsvasc" -v                                   # Pattern match
uv run open-medicine-mcp                # Run MCP server locally
uv build                                # Build package
OPENAI_API_KEY=... uv run python -m open_medicine.embeddings.generate  # Regenerate embeddings
```

> **Important:** Always use `uv run python -m pytest` (not `uv run pytest`) — pytest is not directly on PATH.

## Maintenance Commands

```bash
/health-check                              # Unified project health report (skill)
/check-dois                                # Verify all DOIs still resolve
/check-dois fix                            # Suggest replacements for dead DOIs
/check-embeddings                          # Embedding freshness and coverage
/check-embeddings regenerate               # Regenerate embeddings
/check-dependencies                        # Package staleness and CVE scan
/check-dependencies update                 # Update uv.lock
/check-tests                               # Test timing and untested content
/check-tests full                          # Flaky test detection (double run)
/check-terminology                         # Orphaned terms and duplicates
/benchmark                                 # Query performance vs baseline
/benchmark save                            # Save new performance baseline
```

## Architecture

**Three layers:**

1. **Foundation** (`src/open_medicine/foundation/base.py`) — Core data models: `Evidence` (DOI, level, description), `ClinicalResult` (value, interpretation, evidence, FHIR codes, `to_fhir()` export).

2. **Clinical Content** (`src/open_medicine/mcp/`) — Three content types, all returning `ClinicalResult` with DOI-backed `Evidence`:
   - **Calculators** — Pure functions in `calculators/<name>.py`, registered in `registry.py`
   - **Guidelines** — Curated guidelines as markdown in `guidelines/content/<id>/<section>.md`, indexed in `guidelines/registry.json`
   - **Differentials** — JSON data files in `mcp/differentials/data/<presentation>.json`, auto-loaded by `differentials/engine.py`

3. **MCP Server** (`src/open_medicine/mcp/server.py`) — Exposes 7 meta-tools over stdio:
   - `search_clinical_calculators`, `execute_clinical_calculator` — Calculator discovery and execution via `registry.py`
   - `search_guidelines`, `retrieve_guideline` — Guideline search and section retrieval
   - `search_differential_diagnosis`, `get_differential_diagnosis` — Differential search and ranked retrieval
   - `search_medical_knowledge` — Unified semantic search across all content (embedding-based with keyword fallback)

**Auto-loading pattern**: Differentials use file-based auto-discovery — any `.json` file added to `data/` directories is loaded at import time. No separate registry step needed (unlike calculators).

## Adding a Calculator

### Manual (single calculator)

1. Create `src/open_medicine/mcp/calculators/<name>.py` — Pydantic params model + pure function returning `ClinicalResult` with `Evidence` (DOI required)
2. Add unit tests to `tests/test_<name>.py` — boundary/edge cases, verify DOI
3. Add Hypothesis bounds test to `tests/comparative_validation/test_bounds.py`
4. Register in `src/open_medicine/mcp/registry.py`

### Via `/add-calculator` skill (batch workflow)

Uses a **supervisor + subagent** pattern:

**Subagents** (`calculator-builder` type) do all the work:
1. Activate the `openmedicine-calculator` skill
2. Research the source paper (web search, literature review)
3. Implement the calculator in `calculators/<name>.py`
4. Register in `registry.py`
5. Write tests in `tests/test_<name>.py` (unit + fuzz + comparative)
6. Run `uv run python -m pytest tests/test_<name>.py -v` to verify their work

**Supervisor** (main agent) only:
1. Runs the full test suite `uv run python -m pytest -v` to confirm no conflicts
2. Reports a combined summary

> **Do NOT write calculator code or tests at the supervisor level** — that is the subagent's responsibility.

## Adding a Guideline

### Manual (single guideline)

1. Add entry to `src/open_medicine/guidelines/registry.json`
2. Create markdown in `guidelines/content/<guideline_id>/<section>.md`
3. Add tests to `tests/test_guidelines.py`

### Via `/add-guideline` skill (batch workflow)

Uses a **supervisor + subagent** pattern:

**Subagents** (`guideline-builder` type) do all the work:
1. Activate the `openmedicine-guidelines` skill
2. Research the guideline (web search, literature review)
3. Write all content markdown files in `guidelines/content/<id>/`
4. Write search + retrieve tests in `tests/test_guidelines.py`
5. Run `uv run python -m pytest tests/test_guidelines.py -v` to verify their work

**Supervisor** (main agent) only:
1. Updates `registry.json` with new entries from completed subagents
2. Runs the full test suite `uv run python -m pytest tests/test_guidelines.py -v` to confirm no conflicts

> **Do NOT write content files or tests at the supervisor level** — that is the subagent's responsibility.

## Adding a Differential Diagnosis

### Data schema

Each file in `src/open_medicine/mcp/differentials/data/<presentation>.json` must follow this structure:

```json
{
  "differential_id": "chest_pain",
  "title": "Chest Pain Differential Diagnosis",
  "description": "Brief description of the clinical presentation.",
  "keywords": ["chest pain", "angina", "ACS"],
  "source_doi": "10.1016/j.jacc.2021.07.053",
  "evidence_level": "Clinical Practice Guideline",
  "source_description": "Full citation: Author, Title, Journal Year;Vol:Pages.",
  "diagnoses": [
    {
      "name": "Acute Coronary Syndrome (ACS)",
      "likelihood": "must_not_miss | less_common | common",
      "key_features": ["feature1", "feature2"],
      "red_flags": ["flag1", "flag2"],
      "recommended_tests": ["test1", "calculate_heart_score"],
      "related_guidelines": ["guideline_id"],
      "age_modifier": "risk_increases_over_45 | null",
      "sex_modifier": "atypical_presentation_more_common_in_female | null"
    }
  ],
  "also_consider": [
    {
      "name": "Rare Diagnosis Name",
      "rationale": "One-sentence clinically actionable rationale for considering this diagnosis"
    }
  ],
  "clinical_reasoning_prompt": "This is an evidence-based reference set, not an exhaustive differential. Consider atypical presentations and diagnoses not listed here based on the specific patient context."
}
```

### Manual (single differential)

1. **Research first** — verify DOI is real, diagnoses and likelihoods match the cited source
2. Create `src/open_medicine/mcp/differentials/data/<presentation>.json` following the schema above
3. Add tests to `tests/test_differentials.py` — search match, required fields, DOI present
4. No registration step needed — engine auto-loads all `.json` files from `data/`

### Key rules

- `source_doi` must be verified (web search the DOI, confirm it resolves to the claimed paper)
- `likelihood` must be one of: `must_not_miss`, `less_common`, `common`
- `recommended_tests` can reference calculator IDs (e.g., `calculate_heart_score`) — these create cross-links
- `related_guidelines` should reference guideline IDs that exist in the guidelines registry
- `also_consider` is a required array with 5-15 lightweight entries (name + rationale only) covering rare/atypical diagnoses
- `clinical_reasoning_prompt` is a required non-empty string that frames the output as a reference set and encourages broader reasoning
- Use existing `chest_pain.json` as a reference template

## GraphRAG

**Graph database:** Neo4j Aura (remote). Connection via environment variables:

```bash
# In .env (already configured):
GRAPHRAG_NEO4J_URI=neo4j+s://...databases.neo4j.io
GRAPHRAG_NEO4J_USER=...
GRAPHRAG_NEO4J_PASSWORD=...
```

**SSL workaround (macOS):** Neo4j Aura uses a certificate chain that macOS Python can't verify. Replace `neo4j+s://` with `neo4j+ssc://` (skips certificate verification) when connecting from local dev:

```python
uri = os.environ.get("GRAPHRAG_NEO4J_URI", "")
if "neo4j+s://" in uri:
    uri = uri.replace("neo4j+s://", "neo4j+ssc://")
```

**Running integration tests against live graph:**

```bash
source .env && uv run python -m pytest tests/graphrag/test_clinical_scenario.py -v
```

**Key architecture:**
- `engine_v2.py` — Dual-layer reasoning engine (Layer 1: semantic edges, Layer 2: recommendation traversal)
- `linker_v2.py` — Resolves entity names to canonical IDs via terminology JSON files
- `queries_v2.py` — Cypher query builders for both ingestion and reasoning
- `loader_v2.py` — Ingestion pipeline (extractions → typed nodes + semantic edges)
- `enrichment.py` — Regex-based extraction of structured edge properties (dosing, monitoring, interactions, contraindications) from action_detail text
- Entity IDs must match between terminology database and graph nodes (e.g. `atc:M01A` not `drug_class:nsaid`)

### Data Completeness Standard (A+)

Every graph must meet **A+ quality** before being considered production-ready. Enrichment (`/enrich-graph`) is a REQUIRED step after ingestion, not optional.

**Edge property coverage thresholds (A+ minimum):**

| Edge Type | Property | A+ Threshold |
|-----------|----------|-------------|
| DOSED_FOR | starting_dose | ≥ 90% |
| DOSED_FOR | frequency | ≥ 80% |
| DOSED_FOR | max_dose | ≥ 50% |
| CONTRAINDICATED_IN | severity | 100% |
| INTERACTS_WITH | severity | 100% |
| MONITORED_BY | threshold_alert | ≥ 30% |

**Clinical value correctness (mandatory spot-checks):**
- Angioedema contraindications for ACEi/ARNi must be severity=ABSOLUTE
- ACEi↔ARNi interaction must be severity=MAJOR
- No cross-contamination: combination product doses (e.g. Sacubitril/Valsartan 49mg) must NOT appear on monotherapy drug nodes (e.g. plain Valsartan should show 20-40mg)
- Severity must never be MINOR for known dangerous interactions

**Grading scale** (used by `/audit-graph`):

| Grade | Edge Properties | Scenarios | Terminology |
|-------|----------------|-----------|-------------|
| A+ | ≥ 95% populated | 100% pass | 100% resolve |
| A | 90–95% | 100% pass | 100% resolve |
| B | 80–90% | > 85% pass | > 90% |
| C | 60–80% | > 70% pass | > 80% |
| F | < 60% | < 70% pass | < 80% |

**Pipeline workflow for A+ quality:**
1. `/ingest-guideline` — Extract and load nodes + edges (Phase 1–4.6)
2. `/enrich-graph` — Apply structured properties to edges (REQUIRED Phase 4.7)
3. Post-enrichment quality gate — Verify thresholds are met (Phase 4.8)
4. `/hunt-graph-gaps` — Content completeness validation (REQUIRED)
5. `/fix-graph-gaps` — Fix any gaps found (if needed)
6. `/audit-graph` — Full quality audit with score card
7. `/run-scenarios` — Clinical decision-making validation

Or use `/build-graph` to run the entire pipeline automatically.

### Clinical Completeness Standard (Autonomous Care)

A graph is only fit for autonomous clinical care when an AI agent can answer **every clinical question** the source guideline addresses — without hallucinating, without gaps, without missing safety-critical data. Edge property coverage (A+ standard above) is necessary but NOT sufficient.

**The completeness standard asks:** For every actionable recommendation in the source guideline, does the graph contain the data an agent needs to act on it?

**Seven dimensions of completeness:**

| Dimension | What It Means | How to Verify |
|-----------|--------------|---------------|
| **Treatment coverage** | Every drug/device recommended for a condition has an INDICATED_FOR edge | Count source recommendations vs INDICATED_FOR edges |
| **Safety coverage** | Every contraindication has a CONTRAINDICATED_IN edge with severity; every dangerous interaction has INTERACTS_WITH with severity | Zero contraindications without severity; zero known-dangerous interactions missing |
| **Dosing coverage** | Every drug with a specified dose has a DOSED_FOR edge with starting_dose, target_dose, or max_dose | Compare dosing tables in source against DOSED_FOR edges |
| **Monitoring coverage** | Every monitoring requirement has a MONITORED_BY edge with frequency and thresholds | Compare monitoring sections against MONITORED_BY edges |
| **Condition coverage** | Patient eligibility criteria (LVEF, eGFR, NYHA, etc.) are captured as edge conditions | Spot-check that condition-dependent recommendations include conditions_json |
| **Diagnostic coverage** | Classification criteria and staging thresholds are captured | Compare diagnostic sections against DIAGNOSED_BY edges |
| **Evidence traceability** | Every recommendation links to an EvidenceChunk with source text | Zero recommendations without SOURCED_FROM edges |

**Completeness thresholds (A+ minimum):**

| Dimension | A+ | A | B | F |
|-----------|-----|---|---|---|
| Treatment coverage | ≥ 95% of source recommendations captured | 90-95% | 80-90% | < 80% |
| Safety coverage | 100% of contraindications + interactions captured | 100% | ≥ 90% | < 90% |
| Dosing coverage | ≥ 90% of source dosing data captured | 85-90% | 75-85% | < 75% |
| Monitoring coverage | ≥ 85% of monitoring requirements captured | 80-85% | 70-80% | < 70% |
| Condition coverage | ≥ 80% of conditional recommendations have conditions | 70-80% | 60-70% | < 60% |
| Diagnostic coverage | ≥ 80% of diagnostic criteria captured | 70-80% | 60-70% | < 60% |
| Evidence traceability | 100% of recommendations have source text | 100% | ≥ 95% | < 95% |

**Safety is non-negotiable:** If ANY contraindication or dangerous interaction is missing from the graph, the graph CANNOT be graded above B regardless of other scores. Missing safety data can cause patient harm.

**How to measure:** Run `/hunt-graph-gaps` which compares the source guideline against JSONL extractions and the live graph. The gap report classifies each clinical fact as COMPLETE, EXTRACTION_GAP, LOADING_GAP, ENRICHMENT_GAP, PROPERTY_GAP, or TERMINOLOGY_GAP. Content coverage = COMPLETE / (COMPLETE + all gaps).

**Relationship to edge property coverage:** The A+ edge property standard (above) checks that *existing* edges have populated fields. The completeness standard checks that *all required edges exist in the first place*. Both must pass for A+ overall.

### Graph Safety

Before running `/ingest-guideline` or `/enrich-graph`, the `openmedicine-graph-safety` skill MUST be invoked to create a backup. Backups are stored in `data/backups/graphrag/`.

## Clinical Validation Standard

All clinical content (calculators, guidelines, differentials, graph data) must pass these checks before committing:

1. **Source Traceability** — Every clinical fact is traceable to a peer-reviewed source via DOI or guideline citation. No "common knowledge" additions.
2. **DOI Verification** — Web search the DOI on doi.org or the journal website. Confirm the title, authors, year, and journal match the claimed paper. Verify it is the final published version (not a preprint or journal-in-press). If the DOI does not resolve, do not proceed.
3. **Exact Matching** — Numbers must match the source exactly: doses, thresholds, scoring weights, percentages, cutoffs. When in doubt, the source paper wins.
4. **No Hallucination** — Never rely on pre-training knowledge for clinical data. Use only the cited source. If you cannot verify a fact from the source, omit it.
5. **Accuracy Spot-Check** — Manually verify 5–10% of claims against the source document (minimum 3 claims per content item). Check at least one dose, one threshold, and one eligibility criterion.

> **This standard is referenced by all skills and commands.** When a skill says "apply the Clinical Validation Standard", follow all 5 checks above.

## Severity Definitions

Used by all review, audit, and fix workflows:

- **CRITICAL** — Blocks publication, may cause patient harm
  - Wrong DOI or DOI does not resolve
  - Incorrect clinical data (wrong dose, wrong threshold, contradicts source)
  - Missing mandatory tests or failing tests
  - FHIR code represents input parameter, not output concept
  - Contraindication/interaction severity empty (safety-critical)
  - A+ edge property coverage below threshold

- **WARNING** — Should fix before next release
  - Missing guideline cross-reference
  - Low test coverage (< 6 tests per calculator, < 3 per guideline)
  - Low topic keyword count (< 10 per guideline)
  - Missing comparative validation sources
  - Edge property partially populated

- **SUGGESTION** — Nice to have
  - Code style improvements
  - Additional edge case tests
  - Documentation enhancements

> **Action priority:** Fix all CRITICAL before any WARNING. Fix all WARNING before SUGGESTION. CRITICAL issues block release.

## Git Conventions

- Do not add `Co-Authored-By` trailers to commits

## Code Conventions

- Type hints on all functions
- Pydantic `Field(...)` with `description` for all model fields
- All tools return `ClinicalResult` with valid `Evidence` (DOI, level)
- Include LOINC/FHIR codes when available
- **DOI verification required** — apply the Clinical Validation Standard (above) for every `source_doi` before committing
- **Clinical data must match cited sources** — drug dosing, diagnostic criteria, and scoring thresholds must be verified against the referenced guideline/paper per the Clinical Validation Standard
- Use existing content as reference templates: `chadsvasc.py` (calculator), `chest_pain.json` (differential)
- Python >=3.10, CI tests against 3.10–3.13

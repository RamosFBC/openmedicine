# GraphRAG 100% Cohesive System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close all gaps identified in the GraphRAG system audit — enforce mandatory backups, unify gap analysis, wire scenario testing commands, consolidate quality thresholds, and deprecate superseded agents.

**Architecture:** Five independent tasks that can be parallelized. Each modifies `.claude/` markdown files (commands, skills, agents) and CLAUDE.md. No Python code changes — this is purely documentation/orchestration layer.

**Tech Stack:** Claude Code skills/commands/agents (markdown), CLAUDE.md

---

### Task 1: Mandatory Backup Enforcement

Add backup as a mandatory Phase 0 step in `/ingest-guideline` and `/enrich-graph`. Currently, only `/fix-graph-gaps` enforces backup. The `openmedicine-graph-safety` skill says "NEVER run these without backup" but the commands don't enforce it.

**Files:**
- Modify: `.claude/commands/ingest-guideline.md` (insert new Phase 0 step before existing Phase 0)
- Modify: `.claude/commands/enrich-graph.md` (insert backup step before Phase 1)

**Step 1: Add mandatory backup to `/ingest-guideline`**

In `.claude/commands/ingest-guideline.md`, replace lines 18-35 (the current Phase 0) with a new version that starts with backup:

Replace:
```
### Phase 0: Prepare

1. Parse arguments: `$ARGUMENTS` contains `<file> <id> <doi>`
2. Verify the markdown file exists
3. Clear previous extraction cache for this guideline: `data/cache/graphrag/{guideline_id}/`
4. Ensure Neo4j indexes exist by running:
```

With:
```
### Phase 0: Prepare

1. Parse arguments: `$ARGUMENTS` contains `<file> <id> <doi>`
2. Verify the markdown file exists
3. **Mandatory backup** — invoke the `openmedicine-graph-safety` skill to snapshot the current graph state before any mutations. This is NOT optional. If backup fails, STOP.
4. Clear previous extraction cache for this guideline: `data/cache/graphrag/{guideline_id}/`
5. Ensure Neo4j indexes exist by running:
```

**Step 2: Add mandatory backup to `/enrich-graph`**

In `.claude/commands/enrich-graph.md`, insert a new section between "Parse the guideline_id" (line 17) and "### Phase 1" (line 19):

Insert after line 17:
```
### Phase 0: Mandatory Backup

Before any graph mutations, invoke the `openmedicine-graph-safety` skill to create a backup. This is REQUIRED — if backup fails, STOP.

```

**Step 3: Verify both commands reference backup**

Read both modified files to confirm backup language is present and consistent with `/fix-graph-gaps` pre-flight.

---

### Task 2: Unified Gap Analysis

Make `/enrich-graph` accept a gap report from `/hunt-graph-gaps` instead of doing its own separate analysis. Add a `--from-gap-report` flow so the hunt→enrich pipeline is connected.

**Files:**
- Modify: `.claude/commands/enrich-graph.md` (add gap report acceptance)
- Modify: `.claude/commands/hunt-graph-gaps.md` (update remediation suggestions)
- Modify: `.claude/commands/fix-graph-gaps.md` (cross-reference enrichment)

**Step 1: Update `/enrich-graph` to accept gap report**

In `.claude/commands/enrich-graph.md`, replace the Phase 1 header and first paragraph (lines 19-21) with:

Replace:
```
### Phase 1: Full Guideline Audit (Graph vs Source)

Read the **complete guideline markdown** and compare its clinical content against what is currently in the graph. This is the critical step that drives the entire enrichment.
```

With:
```
### Phase 1: Gap Analysis (Graph vs Source)

**If a gap report exists** (from a prior `/hunt-graph-gaps` run), read it from `data/cache/graphrag/{guideline_id}/gap_report.json` and skip to Phase 2. The gap report already contains the full inventory of missing edges, empty properties, and missing nodes.

**If no gap report exists**, perform the full audit below. This is the critical step that drives the entire enrichment.
```

**Step 2: Update `/hunt-graph-gaps` to save report to file**

In `.claude/commands/hunt-graph-gaps.md`, add instruction to save the report. Replace lines 41-49 with:

Replace:
```
After the agent completes, present the gap report to the user with:
- Summary coverage percentage
- Count of gaps by type and severity
- Top priority remediation actions

If the user wants to fix gaps, suggest:
- `/ingest-guideline` for extraction gaps (with specific sections)
- `/enrich-graph` for enrichment/property gaps
- Manual terminology updates for terminology gaps
```

With:
```
After the agent completes:

1. **Save the gap report** to `data/cache/graphrag/{guideline_id}/gap_report.json` for use by downstream commands (`/enrich-graph`, `/fix-graph-gaps`).

2. Present the gap report to the user with:
   - Summary coverage percentage
   - Count of gaps by type and severity
   - Top priority remediation actions

3. Suggest next steps based on gap types:
   - `EXTRACTION_GAP` or `LOADING_GAP` (CRITICAL) → `/fix-graph-gaps` (handles full dependency chain)
   - `ENRICHMENT_GAP` or `PROPERTY_GAP` (WARNING) → `/enrich-graph` (reads saved gap report automatically)
   - `TERMINOLOGY_GAP` (WARNING) → `/fix-graph-gaps` (handles terminology additions first)
   - Mixed gaps → `/fix-graph-gaps` (handles all gap types in dependency order)
```

**Step 3: Update `/fix-graph-gaps` to read saved gap report**

In `.claude/commands/fix-graph-gaps.md`, replace lines 17-19:

Replace:
```
### Pre-Flight

1. **Locate the gap report** — check if `/hunt-graph-gaps` was run in this session or if a report file exists. If no gap report is available, run `/hunt-graph-gaps` first.
```

With:
```
### Pre-Flight

1. **Locate the gap report** — check for `data/cache/graphrag/{guideline_id}/gap_report.json`. If it exists, use it. If not, check if `/hunt-graph-gaps` was run in this session. If no gap report is available anywhere, run `/hunt-graph-gaps {guideline_id}` first and wait for it to complete.
```

---

### Task 3: Wire Scenario Testing Commands

Create `/create-scenarios` and `/run-scenarios` commands that expose the `clinical-scenario-runner` agent to users. Currently scenarios are auto-generated during ingest but there's no standalone way to create or run them.

**Files:**
- Create: `.claude/commands/create-scenarios.md`
- Create: `.claude/commands/run-scenarios.md`

**Step 1: Create `/create-scenarios` command**

Write `.claude/commands/create-scenarios.md`:

```markdown
# Create Clinical Test Scenarios

Create new clinical test scenarios for GraphRAG evaluation. Scenarios test that the MCP tools return correct clinical decisions for complex patient cases.

## Usage

```
/create-scenarios [guideline_id] [focus]
```

- `guideline_id` defaults to `aha_acc_hf_2022`
- `focus` is optional: `safety`, `dosing`, `monitoring`, `interactions`, or `comprehensive`

## Process

Parse `$ARGUMENTS` (default guideline_id `aha_acc_hf_2022`, default focus `comprehensive`).

### Step 1: Inventory existing scenarios

```bash
ls data/test_scenarios/*.md 2>/dev/null || echo "No scenarios exist yet"
```

Also check auto-generated scenarios:
```bash
cat data/cache/graphrag/{guideline_id}/test_scenarios.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d)} auto-generated scenarios')" 2>/dev/null || echo "No auto-generated scenarios"
```

### Step 2: Query graph for available data

Before writing scenarios, check what data exists in the graph to ensure scenarios are testable:

```bash
uv run python << 'PYEOF'
from dotenv import load_dotenv; load_dotenv()
from open_medicine.graphrag.config import get_settings
from open_medicine.graphrag.graph.connection import GraphConnection

settings = get_settings()
uri = settings.neo4j_uri.replace('neo4j+s://', 'neo4j+ssc://')
with GraphConnection(uri, settings.neo4j_user, settings.neo4j_password) as conn:
    for edge_type in ['INDICATED_FOR', 'CONTRAINDICATED_IN', 'INTERACTS_WITH', 'DOSED_FOR', 'MONITORED_BY']:
        rows = conn.execute_read(f'''
            MATCH (a)-[r:{edge_type}]->(b)
            RETURN a.name AS src, b.name AS tgt,
                   r.severity AS severity, r.starting_dose AS dose
            ORDER BY a.name LIMIT 10
        ''', {})
        print(f'\n{edge_type} ({len(rows)} shown):')
        for r in rows:
            extra = f" sev={r['severity']}" if r.get('severity') else ""
            extra += f" dose={r['dose']}" if r.get('dose') else ""
            print(f'  {r["src"]} -> {r["tgt"]}{extra}')
PYEOF
```

### Step 3: Write scenario file

Create a new scenario in `data/test_scenarios/` following the format of existing scenarios (e.g., `hf_critical_decisions.md`). Each scenario must have:

1. **Patient Profile** — age, sex, weight, diagnoses, comorbidities, medications, labs, allergies
2. **Clinical Question** — what clinical decision needs to be made
3. **Decision Chain** — numbered steps, each with:
   - Tool name (maps to MCP tool)
   - Arguments
   - Expected result (what should be returned, with specific values)
4. **Expected Outcome Summary** — pass/fail criteria for each safety-critical assertion

**Focus area guidance:**
- `safety`: Emphasize contraindication checks with patient-specific variables (angioedema history, pregnancy, renal impairment)
- `dosing`: Emphasize dose verification with renal/hepatic adjustments
- `monitoring`: Emphasize lab monitoring thresholds and frequency
- `interactions`: Emphasize multi-drug regimens with known interactions
- `comprehensive`: Cover all of the above in one scenario

### Step 4: Verify scenario is testable

For each tool call in the scenario, verify the expected entities exist in the graph:

```bash
uv run python -c "
from dotenv import load_dotenv; load_dotenv()
from open_medicine.graphrag.config import get_settings
from open_medicine.graphrag.graph.connection import GraphConnection

settings = get_settings()
uri = settings.neo4j_uri.replace('neo4j+s://', 'neo4j+ssc://')
with GraphConnection(uri, settings.neo4j_user, settings.neo4j_password) as conn:
    # Check each entity referenced in the scenario
    for name in ['ENTITY_1', 'ENTITY_2']:  # Replace with actual entity names
        rows = conn.execute_read('MATCH (n) WHERE toLower(n.name) CONTAINS toLower(\$name) RETURN labels(n)[0] AS label, n.name AS name', {'name': name})
        status = 'FOUND' if rows else 'MISSING'
        print(f'  [{status}] {name}')
"
```

Report: "Created scenario at `data/test_scenarios/{name}.md` with {N} decision steps. Run `/run-scenarios {name}` to execute."
```

**Step 2: Create `/run-scenarios` command**

Write `.claude/commands/run-scenarios.md`:

```markdown
# Run Clinical Test Scenarios

Execute clinical test scenarios against the GraphRAG MCP tools. Spawns `clinical-scenario-runner` agents to evaluate graph quality through realistic clinical decision-making.

## Usage

```
/run-scenarios [scenario_name | all] [guideline_id]
```

- `scenario_name`: filename without extension (e.g., `hf_critical_decisions`), or `all` to run everything
- `guideline_id` defaults to `aha_acc_hf_2022`

Examples:
```
/run-scenarios hf_critical_decisions
/run-scenarios all
```

## Process

Parse `$ARGUMENTS`.

### Step 1: Identify scenarios to run

```bash
ls data/test_scenarios/*.md
```

If `scenario_name` is `all` or empty, run all `.md` files in `data/test_scenarios/`.
If a specific name is given, run only `data/test_scenarios/{scenario_name}.md`.

### Step 2: Spawn scenario runner agents

For each scenario file, spawn a `clinical-scenario-runner` agent:

```
scenario_file: {absolute_path_to_scenario_file}
```

**Batch size**: Up to 3 agents in parallel (scenario runners make many MCP calls).
Wait for each batch before launching the next.

### Step 3: Collect and aggregate results

After all agents complete, aggregate their reports:

```
================================================================
Clinical Scenario Test Results
================================================================

Scenario: hf_critical_decisions
  Overall Grade: B
  Safety blocks: A | Interactions: B | Dosing: A | Monitoring: C
  Data gaps: 2 (threshold_alert empty on MRA monitoring)

Scenario: hf_multimorbid_escalation
  Overall Grade: A
  Safety blocks: A | Interactions: A | Dosing: A | Monitoring: A
  Data gaps: 0

----------------------------------------------------------------
Aggregate: 2 scenarios, 1 A, 1 B
  Safety pass rate: 100%
  Weakest dimension: Monitoring (1 gap)
================================================================
```

### Step 4: Recommend actions

If any scenario grades below B:
- Grade C with safety failures → "CRITICAL: Run `/fix-graph-gaps` to fix safety-critical edge properties"
- Grade C/D with data gaps → "WARNING: Run `/enrich-graph` to populate missing edge properties"
- Grade F → "CRITICAL: Graph data is insufficient. Run `/hunt-graph-gaps` to identify all missing content"

If all scenarios grade A/B:
- "Graph quality meets clinical decision-making standards."
```

---

### Task 4: Single Source of Truth for Quality Thresholds

Consolidate all quality gate thresholds into one reference section in CLAUDE.md and have all commands reference it instead of defining their own copies. Currently thresholds are defined in CLAUDE.md, `/ingest-guideline` Phase 4.8, `/enrich-graph` Phase 4.2, and `/audit-graph` Section 5.

**Files:**
- Modify: `.claude/commands/ingest-guideline.md` (Phase 4.8 — reference CLAUDE.md instead of inline thresholds)
- Modify: `.claude/commands/enrich-graph.md` (Phase 4.2 — reference CLAUDE.md instead of inline thresholds)
- Modify: `.claude/commands/fix-graph-gaps.md` (Quality Gate — reference CLAUDE.md)
- Modify: `.claude/commands/audit-graph.md` (Section 5 — reference CLAUDE.md)

**Step 1: Update `/ingest-guideline` Phase 4.8 to reference CLAUDE.md**

In `.claude/commands/ingest-guideline.md`, replace lines 339-340:

Replace:
```
### Phase 4.8: Post-Enrichment Quality Gate (REQUIRED)

After enrichment, run this validation to ensure A+ edge property coverage:
```

With:
```
### Phase 4.8: Post-Enrichment Quality Gate (REQUIRED)

After enrichment, run this validation to ensure A+ edge property coverage.
Thresholds are defined in the "Data Completeness Standard (A+)" section of CLAUDE.md.
Validation script:
```

**Step 2: Update `/enrich-graph` Phase 4.2 to reference CLAUDE.md**

In `.claude/commands/enrich-graph.md`, replace lines 253-255:

Replace:
```
#### Step 4.2: Post-enrichment quality gate

Run the quality gate from `/ingest-guideline` Phase 4.8:
```

With:
```
#### Step 4.2: Post-enrichment quality gate

Run the A+ quality gate. Thresholds are defined in the "Data Completeness Standard (A+)" section of CLAUDE.md. Same validation as `/ingest-guideline` Phase 4.8:
```

**Step 3: Update `/fix-graph-gaps` Quality Gate to reference CLAUDE.md**

In `.claude/commands/fix-graph-gaps.md`, replace lines 34-40:

Replace:
```
### Quality Gate

After all fixes, verify A+ thresholds:
- DOSED_FOR.starting_dose >= 90%
- DOSED_FOR.frequency >= 80%
- CONTRAINDICATED_IN.severity = 100%
- INTERACTS_WITH.severity = 100%
- MONITORED_BY.threshold_alert >= 30%
```

With:
```
### Quality Gate

After all fixes, verify A+ thresholds as defined in the "Data Completeness Standard (A+)" section of CLAUDE.md. Run the same validation script as `/ingest-guideline` Phase 4.8.
```

**Step 4: Update `/audit-graph` Section 5 to reference CLAUDE.md**

In `.claude/commands/audit-graph.md`, replace lines 113-119:

Replace:
```
| Section | A+ | A | B | C | F |
|---------|----|----|---|---|---|
| Edge Properties | ≥95% fields populated | 90-95% | 80-90% | 60-80% | <60% |
| Structure | All checks pass | All checks pass | Warnings only | 1 critical fail | >1 critical |
| Scenarios | 100% pass | 100% pass | >85% pass | >70% pass | <70% |
| Terminology | 100% resolve | 100% resolve | >90% | >80% | <80% |
```

With:
```
Grading thresholds are defined in the "Data Completeness Standard (A+)" section of CLAUDE.md. Apply those thresholds:

| Section | A+ | A | B | C | F |
|---------|----|----|---|---|---|
| Edge Properties | ≥95% fields populated | 90-95% | 80-90% | 60-80% | <60% |
| Structure | All checks pass | All checks pass | Warnings only | 1 critical fail | >1 critical |
| Scenarios | 100% pass | 100% pass | >85% pass | >70% pass | <70% |
| Terminology | 100% resolve | 100% resolve | >90% | >80% | <80% |
```

---

### Task 5: Deprecate `graphrag-section-extractor` Agent

Mark the generic section extractor as deprecated since all commands now use the typed extractor exclusively. This prevents confusion about which agent to use.

**Files:**
- Modify: `.claude/agents/graphrag-section-extractor.md` (add deprecation notice)

**Step 1: Add deprecation notice**

In `.claude/agents/graphrag-section-extractor.md`, replace lines 1-11:

Replace:
```
---
name: graphrag-section-extractor
description: >
  Reads a specific section of a clinical guideline markdown file and extracts
  granular clinical rules (dosing, contraindications, interactions, monitoring,
  treatment selection, diagnostic criteria) as structured JSONL. Understands
  clinical context deeply — produces specific actionable rules, not summaries.
  Spawn one instance per guideline section for parallel extraction.
tools: Read, Write, Edit, Glob, Grep, Bash, WebSearch
---

# GraphRAG Section Extractor Agent (v2 Schema)
```

With:
```
---
name: graphrag-section-extractor
description: >
  DEPRECATED — Use graphrag-typed-extractor instead. This generic extractor has been
  superseded by the typed extractor which produces richer output by focusing on one
  rec_type per agent instance. Kept for reference only.
tools: Read, Write, Edit, Glob, Grep, Bash, WebSearch
---

# GraphRAG Section Extractor Agent (v2 Schema) — DEPRECATED

> **DEPRECATED**: This agent is superseded by `graphrag-typed-extractor`. All commands
> (`/ingest-guideline`, `/enrich-graph`, `/fix-graph-gaps`) use the typed extractor.
> This file is kept for reference. Do NOT spawn this agent for new extractions.
```

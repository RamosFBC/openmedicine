# Maintenance Skills & Commands Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add 2 maintenance skills and 6 maintenance commands to give the OpenMedicine project full operational health coverage.

**Architecture:** Commands are markdown files in `.claude/commands/` with inline Python scripts (deterministic checks). Skills are `SKILL.md` files in `.claude/skills/` for workflows requiring judgment. The `/health-check` skill orchestrates all `/check-*` commands.

**Tech Stack:** Python inline scripts, Neo4j Cypher, `uv run`, `httpx` for DOI resolution, existing `GraphConnection` and embedding infrastructure.

**Design doc:** `docs/plans/2026-03-16-maintenance-skills-design.md`

---

## Phase 1: Commands (independent — can run in parallel)

All commands follow the same pattern as existing commands (e.g., `/validate`, `/audit-graph`):
- YAML frontmatter with `description`, `argument-hint`, `allowed-tools`
- Inline Python scripts using `!` backtick blocks for auto-run sections
- `$ARGUMENTS` for user input parsing
- Results printed to stdout

### Task 1: `/check-dois` Command

**Files:**
- Create: `.claude/commands/check-dois.md`

**Step 1: Write the command file**

Create `.claude/commands/check-dois.md` with:

```markdown
---
description: Verify all source DOIs in the project still resolve. Detects link rot across calculators, guidelines, differentials, and graph evidence.
argument-hint: "[fix]"
allowed-tools: Bash(uv run python *), WebSearch
---

# Check DOI Health

Verify every `source_doi` in the project resolves to a live paper.

## Collect DOIs

!`uv run python -c "
import json, os, sys, importlib, re; sys.path.insert(0, 'src')
from open_medicine.mcp.registry import CALCULATOR_REGISTRY
gp = os.path.join(os.path.dirname(importlib.import_module('open_medicine').__file__), 'guidelines')
cp = str(importlib.import_module('open_medicine.mcp.calculators').__path__[0])
dp = str(importlib.import_module('open_medicine.mcp.differentials').__path__[0]) + '/data'

dois = {}  # doi -> list of sources

# Guidelines
reg = json.load(open(gp + '/registry.json'))
for g in reg:
    doi = g.get('doi', '')
    if doi:
        dois.setdefault(doi, []).append(f'guideline:{g[\"id\"]}')

# Calculators - scan source files for DOI patterns
doi_pattern = re.compile(r'10\.\d{4,}/[^\s\"]+')
for name in CALCULATOR_REGISTRY:
    short = name.replace('calculate_', '')
    calc_file = cp + f'/{short}.py'
    if os.path.exists(calc_file):
        content = open(calc_file).read()
        for m in doi_pattern.finditer(content):
            d = m.group().rstrip('.,;)')
            dois.setdefault(d, []).append(f'calculator:{name}')

# Differentials
if os.path.isdir(dp):
    for f in os.listdir(dp):
        if f.endswith('.json'):
            data = json.load(open(dp + '/' + f))
            doi = data.get('source_doi', '')
            if doi:
                dois.setdefault(doi, []).append(f'differential:{data.get(\"differential_id\", f)}')

print(f'Found {len(dois)} unique DOIs across {sum(len(v) for v in dois.values())} references')
for doi, sources in sorted(dois.items()):
    print(f'  {doi}')
    for s in sources:
        print(f'    <- {s}')
"`

## Input

`$ARGUMENTS`

### No arguments — Resolve Check

For each DOI collected above, verify it resolves:

```python
import httpx, json, time
from pathlib import Path

cache_path = Path('data/cache/doi_check.json')
cache_path.parent.mkdir(parents=True, exist_ok=True)
cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}

# Skip DOIs checked within last 24 hours
# For each uncached DOI:
#   HEAD request to https://doi.org/{doi}
#   Rate limit: 1 request per second (time.sleep(1))
#   Record: status_code, final_url, timestamp

# Report format:
# | DOI | Status | Used By |
# |-----|--------|---------|
# | 10.1016/... | ✅ OK | guideline:aha_acc_hf_2022 |
# | 10.1234/... | ❌ DEAD (404) | calculator:calculate_chadsvasc |
```

Run the resolution check using `httpx` (available via `uv sync --extra embeddings`). Print the table. Save results to cache.

**Severity classification:**
- Dead DOI on active content = **CRITICAL** (per Severity Definitions in CLAUDE.md)
- DOI with redirect chain >3 hops = **WARNING**
- All resolved = **PASS**

### `fix` argument — Suggest Replacements

For each dead DOI:
1. Extract the paper title from the source file that references it
2. Use WebSearch to find the correct/updated DOI
3. Print suggested replacement with the file path to edit

Do NOT auto-apply fixes. Report only.
```

**Step 2: Test the command**

Run `/check-dois` in a Claude Code session and verify:
- DOI collection finds DOIs from all 3 sources
- Resolution check produces a readable table
- Cache file is created at `data/cache/doi_check.json`

**Step 3: Commit**

```bash
git add .claude/commands/check-dois.md
git commit -m "feat: add /check-dois command for DOI link-rot detection"
```

---

### Task 2: `/check-embeddings` Command

**Files:**
- Create: `.claude/commands/check-embeddings.md`

**Step 1: Write the command file**

Create `.claude/commands/check-embeddings.md` with:

```markdown
---
description: Check embedding freshness, dimensionality, and coverage. Detects stale or missing embeddings for clinical content.
argument-hint: "[regenerate | cost]"
allowed-tools: Bash(uv run python *)
---

# Check Embedding Health

Track embedding freshness and coverage for semantic search.

## Current Status

!`uv run python -c "
import json, os, sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, 'src')
emb_path = Path('src/open_medicine/embeddings/data/embeddings.json')

if not emb_path.exists():
    print('❌ No embeddings file found at', emb_path)
    print('Run: OPENAI_API_KEY=... uv run python -m open_medicine.embeddings.generate')
    sys.exit(0)

# File metadata
mtime = datetime.fromtimestamp(emb_path.stat().st_mtime)
age_days = (datetime.now() - mtime).days
data = json.loads(emb_path.read_text())

# Count embedded items
emb_count = len(data) if isinstance(data, list) else len(data.get('embeddings', data.get('items', [])))

# Count current content that should be embedded
from open_medicine.mcp.registry import CALCULATOR_REGISTRY
calc_count = len(CALCULATOR_REGISTRY)

gp = os.path.join(os.path.dirname(__import__('open_medicine').__file__), 'guidelines')
guide_reg = json.load(open(gp + '/registry.json'))
section_count = sum(len(g.get('sections', [])) for g in guide_reg)

dp = os.path.join(os.path.dirname(__import__('open_medicine').__file__), 'mcp', 'differentials', 'data')
diff_count = len([f for f in os.listdir(dp) if f.endswith('.json')]) if os.path.isdir(dp) else 0

expected = calc_count + section_count + diff_count

status = '✅ FRESH' if age_days < 30 else ('⚠️ STALE' if age_days < 90 else '❌ VERY STALE')

print(f'Embeddings: {status} ({age_days} days old)')
print(f'Last generated: {mtime.strftime(\"%Y-%m-%d %H:%M\")}')
print(f'Embedded items: {emb_count}')
print(f'Expected items: {expected} (calcs={calc_count}, sections={section_count}, diffs={diff_count})')
print(f'Missing: {max(0, expected - emb_count)}')

# Check dimensionality
if isinstance(data, list) and data:
    sample = data[0]
    if isinstance(sample, dict) and 'embedding' in sample:
        dim = len(sample['embedding'])
        print(f'Dimensionality: {dim}')
    elif isinstance(sample, list):
        dim = len(sample)
        print(f'Dimensionality: {dim}')

# Staleness thresholds
if age_days >= 90:
    print(f'\n⚠️ WARNING: Embeddings are {age_days} days old. Regenerate recommended.')
if expected - emb_count > 0:
    print(f'⚠️ WARNING: {expected - emb_count} content items have no embedding.')
"`

## Input

`$ARGUMENTS`

### No arguments — Report Only

Display the status above. No changes made.

### `regenerate` — Regenerate Embeddings

Confirm with the user, then run:
```bash
uv run python -m open_medicine.embeddings.generate
```

Requires `OPENAI_API_KEY` environment variable. Remind the user if not set.

### `cost` — Estimate Cost

Calculate approximate cost based on:
- Number of items to embed
- Average text length per item (~500 tokens)
- OpenAI text-embedding-3-small pricing ($0.02 / 1M tokens)

Print estimate before committing to regeneration.
```

**Step 2: Test the command**

Run `/check-embeddings` and verify:
- Status line shows age and freshness grade
- Item counts are accurate
- Missing count is correct

**Step 3: Commit**

```bash
git add .claude/commands/check-embeddings.md
git commit -m "feat: add /check-embeddings command for embedding freshness tracking"
```

---

### Task 3: `/check-dependencies` Command

**Files:**
- Create: `.claude/commands/check-dependencies.md`

**Step 1: Write the command file**

Create `.claude/commands/check-dependencies.md` with:

```markdown
---
description: Check for outdated dependencies, security vulnerabilities, and Python version compatibility gaps.
argument-hint: "[update | audit]"
allowed-tools: Bash(uv *), Bash(pip-audit *)
---

# Check Dependency Health

Detect outdated packages, CVEs, and Python version gaps.

## Lock File Freshness

!`uv run python -c "
from pathlib import Path
from datetime import datetime

lock = Path('uv.lock')
if lock.exists():
    mtime = datetime.fromtimestamp(lock.stat().st_mtime)
    age = (datetime.now() - mtime).days
    status = '✅ FRESH' if age < 14 else ('⚠️ AGING' if age < 30 else '❌ STALE')
    print(f'uv.lock: {status} ({age} days old, last updated {mtime.strftime(\"%Y-%m-%d\")})')
else:
    print('❌ No uv.lock found')
"`

## Python Version Support

!`uv run python -c "
import tomllib, sys, platform
with open('pyproject.toml', 'rb') as f:
    data = tomllib.load(f)
requires = data.get('project', {}).get('requires-python', 'not set')
print(f'requires-python: {requires}')
print(f'Current interpreter: Python {platform.python_version()}')
# Check CI matrix
import re
ci_path = '.github/workflows/test.yml'
try:
    ci = open(ci_path).read()
    versions = re.findall(r'\"(3\.\d+)\"', ci)
    print(f'CI matrix: {\", \".join(versions) if versions else \"not found\"}')
except FileNotFoundError:
    print('CI config: not found')
"`

## Input

`$ARGUMENTS`

### No arguments — Report Only

1. Show lock file freshness (above)
2. Show Python version info (above)
3. Run `uv pip list --outdated` equivalent to find outdated packages
4. Report in table format:

```
| Package | Pinned | Latest | Update Type |
|---------|--------|--------|-------------|
| pydantic | 2.9.1 | 2.10.0 | minor |
| neo4j | 5.24.0 | 5.26.0 | minor |
```

### `update` — Update Lock File

```bash
uv lock --upgrade
```

Then run tests to verify nothing broke:
```bash
uv run python -m pytest tests/test_chadsvasc.py tests/test_guidelines.py -v --timeout=30
```

### `audit` — Security Scan Only

```bash
uv run pip-audit 2>/dev/null || echo "pip-audit not installed. Run: uv pip install pip-audit"
```

Report any CVEs found with severity level.
```

**Step 2: Test the command**

Run `/check-dependencies` and verify lock file age and Python version are reported.

**Step 3: Commit**

```bash
git add .claude/commands/check-dependencies.md
git commit -m "feat: add /check-dependencies command for dependency health monitoring"
```

---

### Task 4: `/check-tests` Command

**Files:**
- Create: `.claude/commands/check-tests.md`

**Step 1: Write the command file**

Create `.claude/commands/check-tests.md` with:

```markdown
---
description: Detect flaky tests, slow tests, and untested content. Analyzes test health beyond simple pass/fail.
argument-hint: "[full | slow]"
allowed-tools: Bash(uv run python *)
---

# Check Test Health

Analyze test suite for flakiness, slowness, and coverage gaps.

## Quick Summary

!`uv run python -m pytest --co -q 2>&1 | tail -3`

## Untested Content

!`uv run python -c "
import os, sys, importlib; sys.path.insert(0, 'src')
from open_medicine.mcp.registry import CALCULATOR_REGISTRY

untested = []
for name in CALCULATOR_REGISTRY:
    short = name.replace('calculate_', '')
    test_file = f'tests/test_{short}.py'
    if not os.path.exists(test_file):
        untested.append(name)

if untested:
    print(f'⚠️ Calculators without test files ({len(untested)}):')
    for u in untested:
        print(f'  - {u} (expected: tests/test_{u.replace(\"calculate_\", \"\")}.py)')
else:
    print('✅ All calculators have test files')

# Check guidelines
gp = os.path.join(os.path.dirname(importlib.import_module('open_medicine').__file__), 'guidelines')
import json
reg = json.load(open(gp + '/registry.json'))
test_content = open('tests/test_guidelines.py').read() if os.path.exists('tests/test_guidelines.py') else ''
untested_guides = [g['id'] for g in reg if g['id'] not in test_content]
if untested_guides:
    print(f'⚠️ Guidelines not referenced in test_guidelines.py ({len(untested_guides)}):')
    for u in untested_guides:
        print(f'  - {u}')
else:
    print('✅ All guidelines referenced in tests')

# Check differentials
dp = os.path.join(os.path.dirname(importlib.import_module('open_medicine').__file__), 'mcp', 'differentials', 'data')
test_diff = open('tests/test_differentials.py').read() if os.path.exists('tests/test_differentials.py') else ''
if os.path.isdir(dp):
    diff_ids = [f.replace('.json', '') for f in os.listdir(dp) if f.endswith('.json')]
    untested_diffs = [d for d in diff_ids if d not in test_diff]
    if untested_diffs:
        print(f'⚠️ Differentials not referenced in tests ({len(untested_diffs)}):')
        for u in untested_diffs:
            print(f'  - {u}')
    else:
        print('✅ All differentials referenced in tests')
"`

## Input

`$ARGUMENTS`

### No arguments — Timed Single Run

Run targeted test files with timing:

```bash
uv run python -m pytest tests/ -v --tb=short --durations=10 2>&1
```

Report:
- Total pass/fail count
- Top 10 slowest tests (from `--durations=10`)
- Any tests >5s = **WARNING**, >15s = **CRITICAL**

### `full` — Flaky Detection (Double Run)

Run the test suite twice and compare results:

```bash
# Run 1
uv run python -m pytest tests/ -v --tb=line 2>&1 > /tmp/test_run_1.txt
# Run 2
uv run python -m pytest tests/ -v --tb=line 2>&1 > /tmp/test_run_2.txt
```

Diff the results. Tests that pass in one run but fail in another = **flaky**.

Report flaky tests with both run results.

**Important:** Use `uv run python -m pytest` (never `uv run pytest`). Run targeted files when possible (per project conventions).

### `slow` — Slow Tests Only

```bash
uv run python -m pytest tests/ --durations=0 -q 2>&1
```

Report only tests >5s, sorted by duration.
```

**Step 2: Test the command**

Run `/check-tests` and verify untested content detection works.

**Step 3: Commit**

```bash
git add .claude/commands/check-tests.md
git commit -m "feat: add /check-tests command for test health analysis"
```

---

### Task 5: `/check-terminology` Command

**Files:**
- Create: `.claude/commands/check-terminology.md`

**Step 1: Write the command file**

Create `.claude/commands/check-terminology.md` with:

```markdown
---
description: Detect orphaned terminology entries, duplicates, and drift between terminology files and the live graph.
argument-hint: "[fix-orphans | fix-dupes]"
allowed-tools: Bash(uv run python *)
---

# Check Terminology Health

Cross-reference terminology files against the live Neo4j graph to find orphans, unresolved entities, and duplicates.

## Terminology Files

!`uv run python -c "
import json, os
from pathlib import Path

term_dir = Path('src/open_medicine/graphrag/terminology')
if not term_dir.exists():
    print('❌ Terminology directory not found:', term_dir)
else:
    for f in sorted(term_dir.glob('*.json')):
        data = json.loads(f.read_text())
        if isinstance(data, list):
            print(f'{f.name}: {len(data)} entries')
        elif isinstance(data, dict):
            print(f'{f.name}: {len(data)} entries')
"`

## Input

`$ARGUMENTS`

### No arguments — Full Scan

Run a cross-reference check between terminology files and the live graph:

```python
# 1. Load all terminology entries from JSON files
# 2. Query graph for all nodes by label (Drug, DrugClass, Disease, Lab, Procedure, Device)
# 3. Compare:
#    - Terms in JSON but no graph node = orphaned term
#    - Graph nodes with no JSON entry = unresolved entity
# 4. Duplicate detection:
#    - Same canonical name, different IDs
#    - Same ID, different canonical names
#    - Alias overlap (two entries sharing an alias)
```

Connect to Neo4j using:
```python
from dotenv import load_dotenv; load_dotenv()
from open_medicine.graphrag.config import get_settings
from open_medicine.graphrag.graph.connection import GraphConnection

settings = get_settings()
conn = GraphConnection(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
```

Report format:
```
## Terminology Health: ⚠️ 3 orphaned, 2 unresolved

| File | Entries | In Graph | Orphaned |
|------|---------|----------|----------|
| drugs.json | 84 | 71 | 13 |
| diseases.json | 23 | 21 | 2 |

Unresolved graph nodes (no terminology match):
  - Drug: "Entresto" (suggest alias: sacubitril_valsartan)

Duplicates:
  - drugs.json: "valsartan" and "Valsartan" (case mismatch)
```

### `fix-orphans` — Remove Orphaned Entries

For each orphaned term (in JSON but not in graph), confirm with user before removing. Write the updated JSON file back.

### `fix-dupes` — Merge Duplicates

For each duplicate pair, show both entries and ask which to keep. Merge aliases from the removed entry into the kept one.
```

**Step 2: Test the command**

Run `/check-terminology` and verify terminology file listing works. Graph cross-reference requires live Neo4j connection.

**Step 3: Commit**

```bash
git add .claude/commands/check-terminology.md
git commit -m "feat: add /check-terminology command for terminology health monitoring"
```

---

### Task 6: `/benchmark` Command

**Files:**
- Create: `.claude/commands/benchmark.md`

**Step 1: Write the command file**

Create `.claude/commands/benchmark.md` with:

```markdown
---
description: Benchmark GraphRAG query performance against stored baselines. Detects latency regressions across all intent types.
argument-hint: "[save | history]"
allowed-tools: Bash(uv run python *)
---

# Benchmark Query Performance

Run a fixed suite of representative clinical queries and compare against baselines.

## Query Suite

The benchmark runs 10 queries covering all intent types:

```python
BENCHMARK_QUERIES = [
    ("treatment/HFrEF", "treatment_selection", ["heart_failure_reduced_ef"], {}),
    ("contraindication/ACEi+angioedema", "contraindication", ["ACE Inhibitor"], {"history_of_angioedema": True}),
    ("contraindication/ARNi+angioedema", "contraindication", ["Sacubitril/Valsartan"], {"history_of_angioedema": True}),
    ("interaction/ACEi+ARNi", "interaction", ["ACE Inhibitor", "Sacubitril/Valsartan"], {}),
    ("interaction/MRA+ARB", "interaction", ["MRA", "ARB"], {}),
    ("dosing/carvedilol", "dosing", ["Carvedilol"], {}),
    ("dosing/spironolactone", "dosing", ["Spironolactone"], {}),
    ("monitoring/spironolactone", "monitoring", ["Spironolactone"], {}),
    ("monitoring/ACEi", "monitoring", ["ACE Inhibitor"], {}),
    ("treatment/AF", "treatment_selection", ["atrial_fibrillation"], {}),
]
```

## Input

`$ARGUMENTS`

### No arguments — Run and Compare

```python
import time, json, os
from pathlib import Path
from dotenv import load_dotenv; load_dotenv()
from open_medicine.graphrag.config import get_settings
from open_medicine.graphrag.graph.connection import GraphConnection
from open_medicine.graphrag.reasoning.engine_v2 import ReasoningEngine
from open_medicine.graphrag.reasoning.types_v2 import ClinicalQuery

settings = get_settings()
conn = GraphConnection(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
engine = ReasoningEngine(conn)

results = []
for name, intent, concepts, pvars in BENCHMARK_QUERIES:
    start = time.perf_counter()
    r = engine.query(ClinicalQuery(intent=intent, concepts=concepts, patient_vars=pvars, include_evidence=False))
    elapsed_ms = (time.perf_counter() - start) * 1000
    results.append({
        "name": name,
        "latency_ms": round(elapsed_ms, 1),
        "matches": len(r.semantic_matches),
        "confidence": r.confidence,
    })

conn.close()

# Compare against baseline
baseline_path = Path("data/benchmarks/baseline.json")
if baseline_path.exists():
    baseline = {r["name"]: r for r in json.loads(baseline_path.read_text())}
    # Flag >2x = WARNING, >5x = CRITICAL
else:
    print("No baseline found. Run /benchmark save to create one.")
```

Report format:
```
## Performance: ✅ All within bounds

| Query | Baseline | Current | Delta | Status |
|-------|----------|---------|-------|--------|
| treatment/HFrEF | 340ms | 380ms | +12% | ✅ |
| contraindication/ACEi | 120ms | 890ms | +641% | ❌ CRITICAL |

Avg latency: 215ms (baseline: 198ms, +8%)
```

### `save` — Save New Baseline

Run the query suite and save results as the new baseline:

```python
Path("data/benchmarks").mkdir(parents=True, exist_ok=True)
Path("data/benchmarks/baseline.json").write_text(json.dumps(results, indent=2))
# Also save timestamped copy
Path(f"data/benchmarks/{date}.json").write_text(json.dumps(results, indent=2))
```

### `history` — Show Trend

Load all `data/benchmarks/*.json` files (excluding baseline.json), show average latency trend across last 5 runs.
```

**Step 2: Test the command**

Run `/benchmark save` to create initial baseline, then `/benchmark` to compare.

**Step 3: Commit**

```bash
git add .claude/commands/benchmark.md
git commit -m "feat: add /benchmark command for query performance tracking"
```

---

## Phase 2: Skills

### Task 7: `openmedicine-graph-safety` Skill

**Files:**
- Create: `.claude/skills/openmedicine-graph-safety/SKILL.md`

**Step 1: Write the skill file**

Create `.claude/skills/openmedicine-graph-safety/SKILL.md`:

```markdown
---
name: openmedicine-graph-safety
description: Use when about to run graph mutations (ingestion, enrichment, manual Cypher), when a pipeline fails mid-execution, or when needing to restore graph state. Triggers on "backup", "restore", "rollback", "undo graph", "before ingestion", "pipeline failed".
---

# Graph Safety — Backup, Validate, Rollback

Protect graph data integrity during mutations. NEVER run `/ingest-guideline` or `/enrich-graph` without this skill.

> **Core principle:** Every graph mutation must be reversible. Backup before, validate after, rollback if wrong.

## When to Use

- Before ANY `/ingest-guideline` or `/enrich-graph` run
- Before manual Cypher mutations against Neo4j
- After a failed ingestion/enrichment (recovery mode)
- When user says "restore", "backup", "rollback", "undo graph changes"

## Pre-Mutation Backup

Before running any graph mutation:

### 1. Snapshot Current State

```python
from dotenv import load_dotenv; load_dotenv()
from open_medicine.graphrag.config import get_settings
from open_medicine.graphrag.graph.connection import GraphConnection
import json
from pathlib import Path
from datetime import datetime

settings = get_settings()
conn = GraphConnection(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

# Count nodes and edges per type
node_counts = {}
for label in ['Drug', 'DrugClass', 'Disease', 'Lab', 'Procedure', 'Device', 'Guideline', 'EvidenceChunk']:
    rows = conn.execute_read(f'MATCH (n:{label}) RETURN count(n) AS c')
    node_counts[label] = rows[0]['c'] if rows else 0

edge_counts = {}
for rel in ['INDICATED_FOR', 'CONTRAINDICATED_IN', 'INTERACTS_WITH', 'DOSED_FOR', 'MONITORED_BY']:
    rows = conn.execute_read(f'MATCH ()-[r:{rel}]->() RETURN count(r) AS c')
    edge_counts[rel] = rows[0]['c'] if rows else 0

snapshot = {
    'timestamp': datetime.now().isoformat(),
    'nodes': node_counts,
    'edges': edge_counts,
}
print(json.dumps(snapshot, indent=2))
```

### 2. Export Affected Subgraph

For the guideline being modified, export all its nodes and edges:

```python
# Export all edges associated with a guideline's evidence chunks
rows = conn.execute_read('''
    MATCH (g:Guideline {id: $gid})<-[:FROM_GUIDELINE]-(ec:EvidenceChunk)
    OPTIONAL MATCH (a)-[r]->(b)
    WHERE any(prop IN keys(r) WHERE r[prop] = ec.id)
       OR (a:EvidenceChunk AND a.id = ec.id)
    RETURN labels(a) AS src_labels, a AS src_props,
           type(r) AS rel_type, properties(r) AS rel_props,
           labels(b) AS tgt_labels, b AS tgt_props
''', {'gid': guideline_id})
```

Save to `data/backups/graphrag/{guideline_id}/{timestamp}.jsonl`.

### 3. Record in Manifest

Append to `data/backups/graphrag/manifest.json`:

```json
{
    "timestamp": "2026-03-16T14:30:00",
    "guideline_id": "aha_acc_hf_2022",
    "operation": "enrich-graph",
    "snapshot_before": {"nodes": {...}, "edges": {...}},
    "backup_file": "data/backups/graphrag/aha_acc_hf_2022/2026-03-16T14:30:00.jsonl"
}
```

## Post-Mutation Validation

After the mutation completes:

### 4. Compare Node/Edge Counts

Re-run the snapshot query. Compare against pre-mutation snapshot:
- Unexpected node deletions (count decreased for a type not being modified) = **CRITICAL**
- Edge count decreased by >20% for any type = **WARNING** (may be intentional, confirm with user)
- New counts as expected = **PASS**

### 5. Clinical Spot-Checks

Run the mandatory safety assertions (from CLAUDE.md):

```python
# Angioedema contraindications must be ABSOLUTE
rows = conn.execute_read('''
    MATCH (d)-[r:CONTRAINDICATED_IN]->(c)
    WHERE c.name = 'Angioedema' AND r.severity IS NOT NULL
    RETURN d.name, r.severity
''')
for row in rows:
    assert row['r.severity'].upper() == 'ABSOLUTE', \
        f"CRITICAL: {row['d.name']} -> Angioedema severity={row['r.severity']} (must be ABSOLUTE)"

# ACEi↔ARNi interaction must be MAJOR
rows = conn.execute_read('''
    MATCH (d1)-[r:INTERACTS_WITH]->(d2)
    WHERE d1.name = 'ACE Inhibitor' AND d2.name IN ['ARNi', 'Sacubitril/Valsartan']
    RETURN d1.name, d2.name, r.severity
''')
for row in rows:
    assert row['r.severity'] == 'MAJOR', \
        f"CRITICAL: {row['d1.name']} <-> {row['d2.name']} severity={row['r.severity']} (must be MAJOR)"
```

### 6. Offer Rollback if Validation Fails

If any CRITICAL issue is found:
1. Print the specific failures
2. Ask: "Validation failed. Rollback to pre-mutation state?"
3. If yes → proceed to Recovery section below

## Recovery

### 7. List Available Backups

```python
manifest = json.loads(Path('data/backups/graphrag/manifest.json').read_text())
for entry in sorted(manifest, key=lambda x: x['timestamp'], reverse=True):
    print(f"{entry['timestamp']}  {entry['operation']:20s}  {entry['guideline_id']}")
```

### 8. Restore from Backup

Load the JSONL backup and re-create nodes/edges via Cypher:

```python
# Read backup JSONL
# For each line: CREATE or MERGE node, CREATE relationship with all properties
# This overwrites the current state for the affected subgraph
```

**IMPORTANT:** Restoration is destructive for the affected subgraph. Always confirm with user.

## Red Flags — STOP

- Running `/ingest-guideline` without backup → STOP, backup first
- Running `/enrich-graph` without backup → STOP, backup first
- Post-mutation spot-check failed → STOP, offer rollback
- Edge count dropped >50% → STOP, likely data corruption

## Backup Storage

```
data/backups/graphrag/
├── manifest.json                          ← Index of all backups
├── aha_acc_hf_2022/
│   ├── 2026-03-16T14:30:00.jsonl         ← Full subgraph export
│   └── 2026-03-16T15:45:00.jsonl
└── kdigo_ckd_2024/
    └── ...
```

Backups older than 90 days can be pruned. Keep at least 3 per guideline.
```

**Step 2: Test the skill**

Test by running a mock scenario:
1. Run `/check-terminology` to confirm graph connection works
2. Invoke the skill manually before an `/enrich-graph` run
3. Verify backup file is created and manifest is updated
4. Verify post-mutation spot-checks run and pass

**Step 3: Commit**

```bash
git add .claude/skills/openmedicine-graph-safety/SKILL.md
git commit -m "feat: add openmedicine-graph-safety skill for backup/validate/rollback"
```

---

### Task 8: `openmedicine-health-check` Skill

**Files:**
- Create: `.claude/skills/openmedicine-health-check/SKILL.md`

**Depends on:** Tasks 1-6 (all `/check-*` commands must exist)

**Step 1: Write the skill file**

Create `.claude/skills/openmedicine-health-check/SKILL.md`:

```markdown
---
name: openmedicine-health-check
description: Use when starting a maintenance session, checking overall project health, before a release, or after returning from a break. Triggers on "health check", "project health", "what needs attention", "morning rounds", "maintenance check".
---

# Project Health Check

Orchestrate all maintenance checks into a unified report with severity triage.

> **Core principle:** Run all checks, triage by severity, present one actionable report.

## When to Use

- Start of a maintenance session
- Before a release (complements `/release` pre-checks)
- After returning from a break (catch up on what drifted)
- User says "health check", "project health", "what needs attention"

## Process

### 1. Run All Checks

Run these commands and collect their output. Where possible, run them in parallel (they are independent):

| Command | What It Checks |
|---------|---------------|
| `/check-dois` | DOI link rot across all content |
| `/check-embeddings` | Embedding freshness and coverage |
| `/check-dependencies` | Package staleness, CVEs, Python compat |
| `/check-tests` | Flaky tests, slow tests, untested content |
| `/check-terminology` | Orphaned terms, duplicates, graph drift |
| `/benchmark` | Query latency regressions |

Also check:
- Last graph backup age (from `data/backups/graphrag/manifest.json`)
- Last `/audit-graph` grade (if stored)

### 2. Triage by Severity

Classify all findings using Severity Definitions from CLAUDE.md:

**CRITICAL** (any → project health = RED):
- Dead DOIs on active content
- Graph backup >30 days old or missing
- Test failures in CI
- Missing ABSOLUTE contraindication severity
- Security CVE in dependencies

**WARNING** (>2 without CRITICAL → YELLOW):
- Stale embeddings (>90 days)
- Outdated dependencies (>30 days)
- Terminology drift (unresolved graph entities)
- Slow queries (>2x baseline)
- Flaky tests detected
- Untested content exists

**SUGGESTION** (informational):
- Minor terminology duplicates
- Embedding count slightly off
- Lock file aging (14-30 days)

### 3. Produce Unified Report

```
================================================================
  OpenMedicine Health Report — 2026-03-16
================================================================

  Overall: 🟢 GREEN / 🟡 YELLOW / 🔴 RED

| Check | Status | Key Finding |
|-------|--------|-------------|
| DOIs | ✅ PASS | 47/47 alive |
| Embeddings | ⚠️ WARN | 94 days old, 3 missing |
| Dependencies | ✅ PASS | Lock file 5 days old, 0 CVEs |
| Tests | ⚠️ WARN | 1 flaky (test_embedding_search) |
| Terminology | ✅ PASS | 0 orphans, 0 dupes |
| Benchmark | ✅ PASS | Avg 215ms (baseline 198ms, +8%) |
| Graph Backup | ✅ PASS | Last backup: 2 days ago |

----------------------------------------------------------------
  Action Items (by priority)
----------------------------------------------------------------

1. [WARNING] Regenerate embeddings — 94 days stale
   → Run: /check-embeddings regenerate

2. [WARNING] Fix flaky test: test_embedding_search
   → Run: /check-tests full

----------------------------------------------------------------
  Suggested Next Command: /check-embeddings regenerate
================================================================
```

### 4. Save Report

Save to `data/health-reports/{date}.md` for historical tracking.

## Health Grading

- **GREEN** = 0 CRITICAL, ≤2 WARNING
- **YELLOW** = 0 CRITICAL, >2 WARNING
- **RED** = any CRITICAL

## Integration with Other Workflows

- `/release` should run health check as a pre-release gate (RED = block release)
- `/status` can reference latest health report for the dashboard
- Graph mutations should check backup age (>30 days = WARNING from this skill)
```

**Step 2: Test the skill**

Test by invoking "health check" and verifying:
- All 6 `/check-*` commands are invoked
- Results are triaged correctly
- Report format matches the template
- Health grade is computed correctly

**Step 3: Commit**

```bash
git add .claude/skills/openmedicine-health-check/SKILL.md
git commit -m "feat: add openmedicine-health-check skill for unified project health reporting"
```

---

## Phase 3: Integration

### Task 9: Update CLAUDE.md with New Commands

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Add new commands to the Commands section**

After the existing commands block, add:

```markdown
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
```

**Step 2: Add backup workflow to GraphRAG section**

After the existing GraphRAG section, add:

```markdown
### Graph Safety

Before running `/ingest-guideline` or `/enrich-graph`, the `openmedicine-graph-safety` skill MUST be invoked to create a backup. Backups are stored in `data/backups/graphrag/`.
```

**Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add maintenance commands and graph safety workflow to CLAUDE.md"
```

---

### Task 10: Create Data Directories

**Files:**
- Create directories: `data/backups/graphrag/`, `data/benchmarks/`, `data/health-reports/`

**Step 1: Create directories with .gitkeep files**

```bash
mkdir -p data/backups/graphrag data/benchmarks data/health-reports
touch data/backups/graphrag/.gitkeep data/benchmarks/.gitkeep data/health-reports/.gitkeep
```

**Step 2: Add to .gitignore**

Add cache files that shouldn't be committed:

```
data/cache/doi_check.json
data/health-reports/*.md
data/benchmarks/*.json
data/backups/graphrag/**/*.jsonl
```

Keep the directories (via .gitkeep) but ignore generated content.

**Step 3: Commit**

```bash
git add data/backups/graphrag/.gitkeep data/benchmarks/.gitkeep data/health-reports/.gitkeep .gitignore
git commit -m "chore: add data directories for maintenance workflows"
```

---

## Execution Notes

**Parallelism:** Tasks 1-6 are fully independent and can be executed in parallel (different files, no shared state). Tasks 7-8 are independent of each other but Task 8 should be done after Tasks 1-6 so the referenced commands exist. Tasks 9-10 should be last.

**Testing:** Commands are tested by running them. Skills require the writing-skills TDD process (baseline → write → verify). For this plan, the "test" for each command is running it and confirming output is useful.

**Dependencies:**
```
Tasks 1-6 (parallel) → Task 8 (health-check references commands)
Task 7 (independent)
Tasks 9-10 (after all others)
```

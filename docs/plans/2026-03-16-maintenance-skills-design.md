# Maintenance Skills & Commands Design

**Date:** 2026-03-16
**Status:** Approved

## Problem

OpenMedicine has mature content creation workflows (calculators, guidelines, differentials) but lacks operational maintenance automation. Graph data has no backup/restore, DOIs can rot silently, embeddings go stale without alerting, dependencies drift, and there's no unified health dashboard.

## Approach: Hybrid (Commands + Skills)

**Skills** (2) — for workflows requiring judgment (when to backup, how to triage).
**Commands** (6) — for deterministic checks (run script, report results).

The `/health-check` skill ties all commands together into a unified report.

---

## Skills

### 1. `openmedicine-graph-safety`

**Triggers:** Before ingestion/enrichment, after failed pipeline, "restore", "backup", "rollback", "undo graph changes".

**Workflow:**

Pre-mutation:
1. Snapshot current graph state (node/edge counts per type)
2. Export affected subgraph to local JSONL backup
3. Record timestamp + description in backup manifest

Post-mutation validation:
4. Compare node/edge counts (detect unexpected deletions)
5. Run clinical spot-checks (angioedema=ABSOLUTE, ACEi↔ARNi=MAJOR)
6. If validation fails → offer rollback from backup

Recovery:
7. List available backups with timestamps
8. Restore selected backup (re-import JSONL, overwrite affected edges)

**Storage:** `data/backups/graphrag/{guideline_id}/{timestamp}.jsonl` + `manifest.json`

**Safety rules:**
- NEVER run ingestion/enrichment without a backup first
- Backups include Cypher export (nodes + edges + all properties)
- Manifest tracks: timestamp, guideline_id, operation type, node/edge counts before, agent who ran it

---

### 2. `openmedicine-health-check`

**Triggers:** Start of maintenance session, "health check", "project health", "what needs attention", before release, after returning from a break.

**Workflow:**

1. Run all `/check-*` commands in parallel:
   - `/check-dois`, `/check-embeddings`, `/check-dependencies`
   - `/check-tests`, `/check-terminology`, `/benchmark`

2. Triage by Severity Definitions (from CLAUDE.md):
   - **CRITICAL:** Dead DOIs on active content, graph backup >30 days old, test failures, missing ABSOLUTE contraindications
   - **WARNING:** Stale embeddings (>90 days), outdated dependencies, terminology drift, slow queries (>2x baseline)
   - **SUGGESTION:** Flaky tests, low-priority coverage gaps, minor terminology duplicates

3. Produce unified report:

```
## Project Health: GREEN / YELLOW / RED

| Check | Status | Findings |
|-------|--------|----------|
| DOIs | ✅ PASS | 0 dead, 47 verified |
| Tests | ⚠️ WARN | 2 flaky, 1 slow (>5s) |

## Action Items (by priority)
1. [CRITICAL] Fix dead DOI on acc_aha_af_2023...
2. [WARNING] Regenerate embeddings (last: 94 days ago)...

## Suggested Next Command
/check-dois fix
```

4. Save report to `data/health-reports/{date}.md`

**Grading:**
- **GREEN** = 0 CRITICAL, ≤2 WARNING
- **YELLOW** = 0 CRITICAL, >2 WARNING
- **RED** = any CRITICAL

---

## Commands

### 3. `/check-dois`

**Purpose:** Verify every `source_doi` in the project still resolves.

**Sources:** Calculator files, guidelines registry, differential data files, graph edges.

**Execution:**
1. Collect + deduplicate all DOIs
2. HEAD request to `https://doi.org/{doi}` (rate limit: 1 req/sec)
3. Report alive/dead/timeout with "Used By" column
4. Cache results 24h in `data/cache/doi_check.json`

**Arguments:**
- No args → scan and report
- `fix` → web search dead DOIs, suggest replacements

**Severity:** Dead DOI on active content = CRITICAL.

---

### 4. `/check-embeddings`

**Purpose:** Track embedding freshness, validate dimensionality, trigger regeneration.

**Execution:**
1. Check last generation timestamp (file mtime or metadata)
2. Compare embedded chunk count vs current EvidenceChunk count
3. Verify dimensionality matches expected model output
4. Calculate staleness (age in days, content drift)

**Arguments:**
- No args → report status
- `regenerate` → run embedding generation with confirmation
- `cost` → estimate API cost based on chunk count

---

### 5. `/check-dependencies`

**Purpose:** Detect outdated packages, CVEs, and Python version gaps.

**Execution:**
1. Lock file freshness (age of uv.lock)
2. Security scan (`uv pip audit` or pip-audit)
3. Python version check (pyproject.toml vs CI matrix vs latest release)

**Arguments:**
- No args → report only
- `update` → `uv lock --upgrade` with confirmation
- `audit` → security-only scan (fast)

---

### 6. `/check-tests`

**Purpose:** Detect flaky tests, slow tests, and untested content.

**Execution:**
1. Run test suite with timing per test
2. Optionally run 2x to detect flaky tests (results differ between runs)
3. Flag slow tests (>5s WARNING, >15s CRITICAL)
4. Identify untested calculators/guidelines/differentials

**Arguments:**
- No args → single run with timing (fast)
- `full` → double run with flaky detection
- `slow` → only report tests >5s

**Rules:** Use `uv run python -m pytest`, run targeted files not full suite.

---

### 7. `/check-terminology`

**Purpose:** Detect orphaned terms, duplicates, and graph↔terminology drift.

**Execution:**
1. Load all `.json` files from `src/open_medicine/graphrag/terminology/`
2. Cross-reference against graph nodes (both directions)
3. Detect duplicates (case mismatches, overlapping aliases, same-ID conflicts)

**Arguments:**
- No args → report only
- `fix-orphans` → remove entries with no graph presence (with confirmation)
- `fix-dupes` → merge duplicates (interactive)

---

### 8. `/benchmark`

**Purpose:** Track query performance against baselines to detect regressions.

**Execution:**
1. Run 10 representative queries across all intent types
2. Measure round-trip time, Cypher execution time, result count, edge property fill rate
3. Compare against stored baseline

**Thresholds:** >2x baseline = WARNING, >5x baseline = CRITICAL.

**Arguments:**
- No args → run and compare
- `save` → save current run as new baseline
- `history` → show trend across last 5 baselines

**Storage:** `data/benchmarks/{date}.json`

---

## Integration

### How these connect to existing workflows

```
/health-check (skill)
  ├── /check-dois (command)
  ├── /check-embeddings (command)
  ├── /check-dependencies (command)
  ├── /check-tests (command)
  ├── /check-terminology (command)
  └── /benchmark (command)

/ingest-guideline → triggers openmedicine-graph-safety (backup before, validate after)
/enrich-graph → triggers openmedicine-graph-safety (backup before, validate after)
/release → runs /health-check as pre-release gate
```

### Data directories created

```
data/
├── backups/graphrag/{guideline_id}/{timestamp}.jsonl  ← graph-safety
├── benchmarks/{date}.json                              ← benchmark
├── cache/doi_check.json                                ← check-dois
└── health-reports/{date}.md                            ← health-check
```

### CLAUDE.md additions needed

- Document `/check-*` commands in the Commands section
- Add backup/restore workflow to GraphRAG section
- Reference health grading (GREEN/YELLOW/RED) in release checklist

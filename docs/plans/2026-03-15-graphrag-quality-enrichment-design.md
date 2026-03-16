# GraphRAG Production Quality & Enrichment System Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement the implementation plan that follows this design.

**Date**: 2026-03-15
**Status**: Approved

## Problem

The GraphRAG system returns data for 12/12 clinical queries but with shallow quality:
1. **Empty edge properties** — DOSED_FOR, MONITORED_BY, INTERACTS_WITH edges exist but carry no clinical detail (doses, thresholds, mechanisms)
2. **Missing structured edges** — No CONTRAINDICATED_IN or INTERACTS_WITH edges for specific drugs; contraindications only exist as recommendation text
3. **Irrelevant evidence** — Evidence fetching returns 200+ generic citations instead of query-specific text
4. **Terminology gaps** — Entity resolution tries only one type (drug OR drug_class), failing for concepts like "MRA"

## Root Cause

All 537 extractions in consolidated JSONL have `relationships: []` (empty array). Dosing details, interaction mechanisms, contraindication severity, and monitoring thresholds exist as prose in `action_detail` but were never extracted as structured properties. The extractor agent prompt doesn't ask for them, and the loader has the fields defined but receives empty data.

## Approach: Hybrid (Fix Pipeline + Enrich Current Graph)

Fix the extraction pipeline for future guidelines while surgically enriching the current AHA/ACC HF 2022 graph. This ensures production quality now and for every future guideline.

---

## Fix 1: Edge Property Enrichment (Current Graph)

### Strategy
Create an enrichment agent that reads existing consolidated JSONL, uses LLM to parse `action_detail` text into structured properties, and outputs a JSONL patch file.

### Extraction targets by rec_type

**Dosing (94 records):**
- Input: `"Bumetanide: initial daily dose 0.5-1.0 mg once or twice daily; maximum total daily dose 10 mg"`
- Output: `{starting_dose: "0.5-1.0 mg", frequency: "once or twice daily", max_dose: "10 mg", route: "oral"}`
- Target edge: DOSED_FOR

**Monitoring (60 records):**
- Input: `"Monitor potassium and renal function within 1-2 weeks of initiation and periodically thereafter"`
- Output: `{frequency: "1-2 weeks after initiation, then periodically", threshold_alert: "K+ > 5.0 mEq/L", threshold_stop: "K+ > 5.5 mEq/L"}`
- Target edge: MONITORED_BY

**Interaction (9 records):**
- Input: `"Allow 36-hour washout between ACEi and ARNi to avoid angioedema risk"`
- Output: `{mechanism: "overlapping RAAS blockade", clinical_effect: "angioedema risk", severity: "MAJOR"}`
- Target edge: INTERACTS_WITH

**Contraindication (64 records):**
- Input: `"NSAIDs worsen HF symptoms and should be avoided whenever possible"`
- Output: `{severity: "ABSOLUTE", reason: "worsens HF symptoms"}`
- Target edge: CONTRAINDICATED_IN (severity classification)

### Batch strategy
Group by rec_type, send 10-15 extractions per LLM call with structured output schema. ~20 LLM calls total. Output to `data/patches/aha_acc_hf_2022_enrichment.jsonl`.

---

## Fix 2: Evidence Relevance (Engine)

### Problem
`_fetch_evidence_for_matches` traverses Recommendation→SOURCED_FROM→EvidenceChunk for every matched entity. A query about "Spironolactone dosing" returns 191 citations including iron deficiency text.

### Solution: Vector re-ranking
```python
def _fetch_evidence_for_matches(self, matches, q):
    candidates = [...]  # existing SOURCED_FROM traversal
    query_embedding = embed_query(f"{q.intent} {' '.join(q.concepts)}")
    scored = [(c, cosine_sim(query_embedding, c.embedding)) for c in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [c for c, score in scored[:5]]
```

Reuses existing Voyage AI embeddings stored on EvidenceChunk nodes. No new API calls — just fetch embeddings alongside text and compute cosine similarity locally.

Fallback: If embeddings unavailable, return all candidates capped at 10.

---

## Fix 3: Terminology Resolution (Engine)

### Problem
`_query_monitoring` calls `link_entity(concept, "drug")` → None for "MRA" → falls to expansion. Should try drug_class directly first.

### Solution
Each intent handler tries both entity types before falling to expansion/vector:
```python
entity = link_entity(concept, "drug")
if entity is None:
    entity = link_entity(concept, "drug_class")
if entity is None:
    # expansion / vector fallback
```

Apply to: `_query_monitoring`, `_query_interactions`, `_query_contraindications`, `_query_dosing`.

---

## Fix 4: Extractor Agent Update (Future Guidelines)

Update `graphrag-section-extractor.md` to extract structured `relationships[]` with typed properties:
- Dosing: starting_dose, target_dose, max_dose, route, frequency
- Monitoring: frequency, threshold_alert, threshold_stop
- Interaction: mechanism, clinical_effect, severity
- Contraindication: severity (ABSOLUTE/RELATIVE), reason

This ensures every future guideline gets rich edge properties from extraction, not just prose.

---

## Fix 5: .claude Skill System

### `/enrich-graph`
Extract structured edge properties from existing JSONL and patch onto graph.
1. Read consolidated JSONL
2. Spawn parallel subagents per rec_type to extract structured properties
3. Merge patches, apply via `ingest_v2.py apply-patch`
4. Run `/audit-graph` to verify

### `/audit-graph`
Comprehensive quality scoring of the live graph.
1. Edge property coverage (% of DOSED_FOR with starting_dose, etc.)
2. Clinical scenario pass rate (12 standard queries)
3. Evidence relevance (top-3 citations actually relevant?)
4. Terminology resolution (20 common terms resolve?)
5. Output: Score card with grade A/B/C/F

### `/maintain-graph`
Day-to-day graph operations: add terminology, propagate edges, normalize IDs, repair evidence.

### Update `/ingest-guideline`
Add Phase 4.5 (Enrichment) between load and validation.

---

## Implementation Strategy

| Stream | Work | Dependencies |
|--------|------|-------------|
| Stream 1 | Terminology resolution fix in engine | None |
| Stream 2 | Evidence re-ranking in engine | None |
| Stream 3 | Create `/audit-graph` skill | None |
| Stream 4 | Create `/enrich-graph` skill | Stream 3 |
| Stream 5 | Create `/maintain-graph` skill | None |
| Stream 6 | Run enrichment on AHA/ACC HF graph | Stream 4 |
| Stream 7 | Update extractor agent for future guidelines | None |

Streams 1, 2, 3, 5, 7 are independent — run in parallel.
Stream 4 depends on 3 (audit used for verification).
Stream 6 depends on 4 (enrichment skill must exist).

## Success Criteria

After all fixes:
- 12/12 clinical queries return data (maintained)
- DOSED_FOR edges: >80% have starting_dose or max_dose populated
- MONITORED_BY edges: >60% have frequency populated
- Evidence: top-3 citations are query-relevant (manual spot check)
- "MRA monitoring" resolves via direct drug_class lookup (no vector fallback needed)
- `/audit-graph` scores B+ or higher

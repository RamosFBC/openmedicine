# Enrich Graph Edge Properties

Comprehensive graph enrichment: audit existing graph against the source guideline markdown, identify gaps (missing edges, empty properties), then dispatch parallel section-level agents to extract the missing data and patch it onto the live graph. All enrichment must meet the A+ quality standard and Clinical Validation Standard defined in CLAUDE.md. Use Severity Definitions (CRITICAL/WARNING/SUGGESTION) when reporting issues.

## Usage

```
/enrich-graph [guideline_id]
```

Example: `/enrich-graph aha_acc_hf_2022`

Default guideline_id: `aha_acc_hf_2022`

## Process

Parse the guideline_id from `$ARGUMENTS` (default to `aha_acc_hf_2022` if empty).

### Phase 1: Full Guideline Audit (Graph vs Source)

Read the **complete guideline markdown** and compare its clinical content against what is currently in the graph. This is the critical step that drives the entire enrichment.

#### Step 1.1: Read the guideline markdown

```bash
# Find the guideline file
ls data/guidelines/{guideline_id}*.md
```

Read the entire markdown file using the Read tool. Identify every clinically actionable statement:
- Drug dosing (starting dose, target dose, max dose, frequency, route, titration)
- Monitoring requirements (labs, frequency, thresholds)
- Contraindications (drug → disease, with severity)
- Drug-drug interactions (with severity, mechanism)
- Treatment selections (drug/device → disease, with strength/evidence)
- Diagnostic criteria (disease → labs/procedures)

#### Step 1.2: Query the graph for current state

Run this audit query to get a complete picture of what's in the graph:

```bash
uv run python << 'PYEOF'
import logging, os, json
from dotenv import load_dotenv; load_dotenv()
logging.getLogger('neo4j').setLevel(logging.ERROR)
from open_medicine.graphrag.config import get_settings
from open_medicine.graphrag.graph.connection import GraphConnection

settings = get_settings()
uri = settings.neo4j_uri.replace('neo4j+s://', 'neo4j+ssc://')
conn = GraphConnection(uri, settings.neo4j_user, settings.neo4j_password)

print('=== NODES ===')
for label in ['Drug', 'DrugClass', 'Disease', 'Lab', 'Procedure', 'Device']:
    rows = conn.execute_read(f'MATCH (n:{label}) RETURN n.id AS id, n.name AS name ORDER BY n.name', {})
    print(f'\n{label} ({len(rows)}):')
    for r in rows:
        print(f'  {r["id"]:40s} {r["name"]}')

print('\n=== EDGE PROPERTY COVERAGE ===')
for edge_type in ['INDICATED_FOR', 'CONTRAINDICATED_IN', 'INTERACTS_WITH', 'DOSED_FOR', 'MONITORED_BY']:
    rows = conn.execute_read(f'''
        MATCH (a)-[r:{edge_type}]->(b)
        RETURN a.name AS src, b.name AS tgt, properties(r) AS props
        ORDER BY a.name, b.name
    ''', {})
    print(f'\n{edge_type} ({len(rows)} edges):')
    for r in rows:
        props = {k: v for k, v in r['props'].items() if v is not None and k != 'conditions_json'}
        empty_keys = [k for k, v in r['props'].items() if v is None or v == '']
        status = '✅' if not empty_keys else f'⚠️  empty: {", ".join(empty_keys)}'
        print(f'  {r["src"]:30s} -> {r["tgt"]:30s} {status}')
        if props:
            for k, v in sorted(props.items()):
                if k == 'conditions_json': continue
                val = str(v)[:80]
                print(f'    {k}: {val}')

conn.close()
PYEOF
```

#### Step 1.3: Generate the gap report

Compare the guideline content against the graph. For each section of the guideline, identify:

1. **Missing nodes**: Drugs, diseases, labs mentioned in the guideline but absent from the graph
2. **Missing edges**: Relationships described in the guideline but not present as graph edges (e.g., Warfarin MONITORED_BY INR, Digoxin INTERACTS_WITH Amiodarone)
3. **Empty edge properties**: Edges that exist but have NULL/empty properties (e.g., DOSED_FOR with no starting_dose, CONTRAINDICATED_IN with no severity)
4. **Missing evidence_quality/strength**: Edges where these key properties are empty

Write the gap report to `data/cache/graphrag/{guideline_id}/enrichment_gaps.json`:

```json
{
  "missing_edges": [
    {
      "section_id": "7_3_1",
      "section_title": "ACEi/ARB/ARNi",
      "edge_type": "INTERACTS_WITH",
      "source": "Digoxin",
      "target": "Amiodarone",
      "expected_properties": {"severity": "MAJOR", "mechanism": "increased digoxin levels"},
      "source_text": "quote from guideline"
    }
  ],
  "empty_properties": [
    {
      "edge_type": "CONTRAINDICATED_IN",
      "source": "ACE Inhibitor",
      "target": "Angioedema",
      "missing_properties": ["evidence_quality", "severity"],
      "section_id": "7_3_1"
    }
  ],
  "missing_nodes": [
    {"name": "Warfarin", "type": "drug", "reason": "Referenced in section 10.2 for AF management"}
  ]
}
```

### Phase 2: Regex-Based Enrichment (Existing JSONL)

Before dispatching agents, first try to fill empty properties using the regex parsers on existing extracted text. This is fast and free.

```bash
uv run python -c "
import json
from pathlib import Path
from collections import Counter
from open_medicine.graphrag.enrichment import PARSERS

guideline_id = '$ARGUMENTS'.strip() or 'aha_acc_hf_2022'
jsonl_path = Path(f'data/cache/graphrag/{guideline_id}/consolidated.jsonl')
patch_path = Path(f'data/patches/{guideline_id}_enrichment.jsonl')
patch_path.parent.mkdir(parents=True, exist_ok=True)

stats = Counter()
patches = []

for line in jsonl_path.read_text().splitlines():
    if not line.strip():
        continue
    rule = json.loads(line)
    rec_type = rule.get('rec_type', '')
    parser = PARSERS.get(rec_type)
    if not parser:
        continue

    detail = rule.get('action_detail', '')
    props = parser(detail)
    if props:
        patches.append({
            'rec_id': rule['rec_id'],
            'rec_type': rec_type,
            'properties': props,
            'source_text': detail[:200],
        })
        stats[rec_type] += 1

patch_path.write_text('\n'.join(json.dumps(p) for p in patches))
print(f'Generated {len(patches)} patches:')
for rt, count in stats.most_common():
    print(f'  {rt}: {count}')
print(f'Saved to {patch_path}')
"
```

Apply the regex patches to Neo4j (same as before — see Step 3 of old enrichment).

### Phase 3: Section-Level Agent Extraction for Gaps

For gaps that the regex parsers cannot fill (missing edges, missing nodes, complex properties), dispatch **parallel extraction agents** per guideline section — the same multi-agent pattern used in `/ingest-guideline` Phase 2.

#### Step 3.1: Identify sections with gaps

From the gap report (Phase 1.3), group gaps by `section_id`. For each section that has gaps, determine which `rec_type_focus` values are needed:

- Missing INTERACTS_WITH edges → need `interaction` extractor
- Missing MONITORED_BY edges → need `monitoring` extractor
- Missing DOSED_FOR edges or empty dosing properties → need `dosing` extractor
- Missing CONTRAINDICATED_IN edges or empty severity → need `contraindication` extractor
- Missing INDICATED_FOR edges → need `treatment_selection` extractor

#### Step 3.2: Dispatch targeted extraction agents

For each (section, rec_type) pair that has gaps, launch a `general-purpose` agent with:

1. Read the full instructions from `.claude/agents/graphrag-typed-extractor.md` and embed them in the agent prompt
2. Provide these parameters:
   - `guideline_file`: path to the guideline markdown
   - `section_start_line` and `section_end_line` from the section map
   - `section_id` and `section_title`
   - `guideline_id`
   - `rec_type_focus`: the specific type needed for this gap
   - `output_file`: `data/cache/graphrag/{guideline_id}/enrichment_extractions/{section_id}_{rec_type_focus}.jsonl`
   - `terminology_dir`: `src/open_medicine/graphrag/terminology/`
3. **Add gap-specific instructions** to the agent prompt:
   - List the specific gaps from the gap report for this section
   - Tell the agent: "The graph is MISSING these edges/properties. Focus your extraction on finding the clinical evidence for them."
   - Include the exact source text quotes from the gap report

**IMPORTANT**: The agent type must be `general-purpose` (not a custom agent type).

**Batch size**: 5 agents at a time (to stay within parallel limits).
Wait for each batch to complete before launching the next.

If the section map doesn't exist, regenerate it:
```bash
cat data/cache/graphrag/{guideline_id}/sections.json
```
If missing, read the guideline and create it (same as `/ingest-guideline` Phase 1).

#### Step 3.3: Normalize new extractions

Launch a single `general-purpose` agent with the full instructions from
`.claude/agents/graphrag-concept-normalizer.md` embedded in its prompt, plus:
- `extraction_dir`: `data/cache/graphrag/{guideline_id}/enrichment_extractions/`
- `output_file`: `data/cache/graphrag/{guideline_id}/enrichment_consolidated.jsonl`
- `guideline_id`
- `terminology_dir`: `src/open_medicine/graphrag/terminology/`

**IMPORTANT**: The agent type must be `general-purpose` (not a custom agent type).

#### Step 3.4: Load new extractions into Neo4j

```bash
uv run python -m open_medicine.graphrag.ingest_v2 load \
    --jsonl data/cache/graphrag/{guideline_id}/enrichment_consolidated.jsonl \
    --file {guideline_file} \
    --id {guideline_id} \
    --doi {doi} \
    --title "{title}" \
    --year {year} \
    --org "{organization}"
```

**Note**: Use `load` (not `migrate`) to ADD new edges without clearing existing ones.

#### Step 3.5: Apply regex enrichment on NEW extractions

Re-run the regex enrichment (Phase 2) on the new `enrichment_consolidated.jsonl` to populate structured properties on the newly created edges.

### Phase 4: Verify

#### Step 4.1: Re-run the graph audit

Repeat Phase 1.2 (graph query) and compare against the gap report. Check:
- How many previously missing edges now exist?
- How many previously empty properties are now populated?

#### Step 4.2: Post-enrichment quality gate

Run the quality gate from `/ingest-guideline` Phase 4.8:

```bash
uv run python -c "
from dotenv import load_dotenv; load_dotenv()
from open_medicine.graphrag.config import get_settings
from open_medicine.graphrag.graph.connection import GraphConnection

settings = get_settings()
uri = settings.neo4j_uri.replace('neo4j+s://', 'neo4j+ssc://')

with GraphConnection(uri, settings.neo4j_user, settings.neo4j_password) as conn:
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

    # CONTRAINDICATED_IN: severity = 100%, evidence_quality >= 80%
    rows = conn.execute_read('''
        MATCH ()-[r:CONTRAINDICATED_IN]->()
        RETURN count(r) AS total,
            sum(CASE WHEN r.severity IS NOT NULL THEN 1 ELSE 0 END) AS has_sev,
            sum(CASE WHEN r.evidence_quality IS NOT NULL AND r.evidence_quality <> '' THEN 1 ELSE 0 END) AS has_eq
    ''')
    r = rows[0]
    if r['total'] > 0:
        sev_pct = r['has_sev'] / r['total'] * 100
        eq_pct = r['has_eq'] / r['total'] * 100
        print(f'CONTRAINDICATED_IN: severity={sev_pct:.0f}%, evidence_quality={eq_pct:.0f}%')
        if sev_pct < 100: failures.append(f'CONTRAINDICATED_IN.severity={sev_pct:.0f}% (need 100%)')
        if eq_pct < 80: failures.append(f'CONTRAINDICATED_IN.evidence_quality={eq_pct:.0f}% (need >=80%)')

    # INTERACTS_WITH: severity = 100%, evidence_quality >= 80%
    rows = conn.execute_read('''
        MATCH ()-[r:INTERACTS_WITH]->()
        RETURN count(r) AS total,
            sum(CASE WHEN r.severity IS NOT NULL THEN 1 ELSE 0 END) AS has_sev,
            sum(CASE WHEN r.evidence_quality IS NOT NULL AND r.evidence_quality <> '' THEN 1 ELSE 0 END) AS has_eq
    ''')
    r = rows[0]
    if r['total'] > 0:
        sev_pct = r['has_sev'] / r['total'] * 100
        eq_pct = r['has_eq'] / r['total'] * 100
        print(f'INTERACTS_WITH: severity={sev_pct:.0f}%, evidence_quality={eq_pct:.0f}%')
        if sev_pct < 100: failures.append(f'INTERACTS_WITH.severity={sev_pct:.0f}% (need 100%)')
        if eq_pct < 80: failures.append(f'INTERACTS_WITH.evidence_quality={eq_pct:.0f}% (need >=80%)')

    # MONITORED_BY: frequency >= 50%, threshold_alert >= 30%
    rows = conn.execute_read('''
        MATCH ()-[r:MONITORED_BY]->()
        RETURN count(r) AS total,
            sum(CASE WHEN r.frequency IS NOT NULL THEN 1 ELSE 0 END) AS has_freq,
            sum(CASE WHEN r.threshold_alert IS NOT NULL THEN 1 ELSE 0 END) AS has_alert
    ''')
    r = rows[0]
    if r['total'] > 0:
        freq_pct = r['has_freq'] / r['total'] * 100
        alert_pct = r['has_alert'] / r['total'] * 100
        print(f'MONITORED_BY: frequency={freq_pct:.0f}%, threshold_alert={alert_pct:.0f}%')
        if freq_pct < 50: failures.append(f'MONITORED_BY.frequency={freq_pct:.0f}% (need >=50%)')
        if alert_pct < 30: failures.append(f'MONITORED_BY.threshold_alert={alert_pct:.0f}% (need >=30%)')

    # INDICATED_FOR: strength >= 90%, evidence_quality >= 80%
    rows = conn.execute_read('''
        MATCH ()-[r:INDICATED_FOR]->()
        RETURN count(r) AS total,
            sum(CASE WHEN r.strength IS NOT NULL AND r.strength <> '' THEN 1 ELSE 0 END) AS has_str,
            sum(CASE WHEN r.evidence_quality IS NOT NULL AND r.evidence_quality <> '' THEN 1 ELSE 0 END) AS has_eq
    ''')
    r = rows[0]
    if r['total'] > 0:
        str_pct = r['has_str'] / r['total'] * 100
        eq_pct = r['has_eq'] / r['total'] * 100
        print(f'INDICATED_FOR: strength={str_pct:.0f}%, evidence_quality={eq_pct:.0f}%')
        if str_pct < 90: failures.append(f'INDICATED_FOR.strength={str_pct:.0f}% (need >=90%)')
        if eq_pct < 80: failures.append(f'INDICATED_FOR.evidence_quality={eq_pct:.0f}% (need >=80%)')

    # Clinical spot-checks
    rows = conn.execute_read('''
        MATCH (d)-[r:CONTRAINDICATED_IN]->(c)
        WHERE c.name = 'Angioedema' AND r.severity IS NOT NULL
            AND (d.name IN ['ACE Inhibitor', 'Sacubitril/Valsartan'] OR d.name = 'ARNi')
        RETURN d.name, r.severity
    ''')
    for row in rows:
        if row['r.severity'].upper() != 'ABSOLUTE':
            failures.append(f'{row[\"d.name\"]} -> Angioedema severity={row[\"r.severity\"]} (must be ABSOLUTE)')

    rows = conn.execute_read('''
        MATCH (d1)-[r:INTERACTS_WITH]->(d2)
        WHERE (d1.name = 'ACE Inhibitor' AND d2.name = 'ARNi')
           OR (d1.name = 'Sacubitril/Valsartan' AND d2.name = 'ACE Inhibitor')
        RETURN d1.name, d2.name, r.severity
    ''')
    for row in rows:
        if row['r.severity'] != 'MAJOR':
            failures.append(f'{row[\"d1.name\"]} <-> {row[\"d2.name\"]} severity={row[\"r.severity\"]} (must be MAJOR)')

    if failures:
        print(f'\nFAILED — {len(failures)} issues:')
        for f in failures:
            print(f'  ✗ {f}')
        raise SystemExit(1)
    else:
        print('\nPASSED — all quality gates met')
"
```

#### Step 4.3: Run simulation

Run the clinical scenario simulation to confirm previously failing queries now work:

```bash
# Test specific scenarios that were failing before enrichment
export $(grep -v '^#' .env | grep -v VOYAGE | xargs) && uv run python << 'PYEOF'
import logging, os
logging.getLogger('neo4j').setLevel(logging.ERROR)
os.environ.pop('VOYAGE_API_KEY', None)
from open_medicine.graphrag.graph.connection import GraphConnection
from open_medicine.graphrag.reasoning.engine_v2 import ReasoningEngine
from open_medicine.graphrag.reasoning.types_v2 import ClinicalQuery

uri = os.environ['GRAPHRAG_NEO4J_URI'].replace('neo4j+s://','neo4j+ssc://')
conn = GraphConnection(uri, os.environ['GRAPHRAG_NEO4J_USER'], os.environ['GRAPHRAG_NEO4J_PASSWORD'])
engine = ReasoningEngine(conn)

tests = [
    ("Warfarin monitoring", "monitoring", ["Warfarin"], {}),
    ("Warfarin interactions", "interaction", ["Warfarin"], {}),
    ("Digoxin interactions", "interaction", ["Digoxin"], {}),
    ("Metformin CI", "contraindication", ["Metformin"], {"eGFR": 20}),
    ("ACEi CI (with severity)", "contraindication", ["ACE Inhibitor"], {}),
    ("Spironolactone CI (with severity)", "contraindication", ["Spironolactone"], {}),
]

for name, intent, concepts, pvars in tests:
    r = engine.query(ClinicalQuery(intent=intent, concepts=concepts, patient_vars=pvars, include_evidence=False))
    ns = len(r.semantic_matches)
    icon = '✅' if ns > 0 else '❌'
    props_filled = sum(1 for m in r.semantic_matches if m.evidence_quality and m.evidence_quality != '')
    print(f'{icon} {name}: sem={ns} conf={r.confidence} cov={r.data_coverage} eq_filled={props_filled}/{ns}')
    for m in r.semantic_matches[:3]:
        print(f'    {m.entity_name} str={m.strength} eq={m.evidence_quality} sev={getattr(m, "severity", "N/A")}')

conn.close()
PYEOF
```

### Phase 5: Report

Print a summary:
- Edges added (before vs after count per edge type)
- Properties filled (before vs after percentage per edge type)
- Remaining gaps (if any)
- Quality gate result (PASS/FAIL)

If gaps remain after this enrichment cycle, list them and suggest either:
1. Adding missing entities to terminology files (drugs.json, etc.)
2. Re-running enrichment with more targeted agent instructions
3. Manual graph patches for edge cases

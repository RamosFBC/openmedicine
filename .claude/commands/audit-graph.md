# Audit GraphRAG Quality

Comprehensive quality scoring of the live knowledge graph. Checks edge property coverage, clinical scenario pass rate, structural integrity, and terminology resolution.

## Usage

```
/audit-graph [guideline_id]
```

Default guideline_id: `aha_acc_hf_2022`

## Process

Parse the guideline_id from `$ARGUMENTS` (default to `aha_acc_hf_2022` if empty).

### Section 1: Edge Property Coverage

Run this Python script to check how many edges have structured properties populated:

```bash
uv run python -c "
from dotenv import load_dotenv; load_dotenv()
from open_medicine.graphrag.config import get_settings
from open_medicine.graphrag.graph.connection import GraphConnection

settings = get_settings()
with GraphConnection(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password) as conn:
    checks = {
        'DOSED_FOR': {
            'query': 'MATCH ()-[r:DOSED_FOR]->() RETURN count(r) AS total, sum(CASE WHEN r.starting_dose IS NOT NULL THEN 1 ELSE 0 END) AS has_start, sum(CASE WHEN r.max_dose IS NOT NULL THEN 1 ELSE 0 END) AS has_max, sum(CASE WHEN r.frequency IS NOT NULL THEN 1 ELSE 0 END) AS has_freq',
            'fields': ['has_start', 'has_max', 'has_freq'],
        },
        'MONITORED_BY': {
            'query': 'MATCH ()-[r:MONITORED_BY]->() RETURN count(r) AS total, sum(CASE WHEN r.frequency IS NOT NULL THEN 1 ELSE 0 END) AS has_freq, sum(CASE WHEN r.threshold_alert IS NOT NULL THEN 1 ELSE 0 END) AS has_alert',
            'fields': ['has_freq', 'has_alert'],
        },
        'INTERACTS_WITH': {
            'query': 'MATCH ()-[r:INTERACTS_WITH]->() RETURN count(r) AS total, sum(CASE WHEN r.mechanism IS NOT NULL THEN 1 ELSE 0 END) AS has_mech, sum(CASE WHEN r.severity IS NOT NULL THEN 1 ELSE 0 END) AS has_sev',
            'fields': ['has_mech', 'has_sev'],
        },
        'CONTRAINDICATED_IN': {
            'query': 'MATCH ()-[r:CONTRAINDICATED_IN]->() RETURN count(r) AS total, sum(CASE WHEN r.severity IS NOT NULL THEN 1 ELSE 0 END) AS has_sev, sum(CASE WHEN r.reason IS NOT NULL THEN 1 ELSE 0 END) AS has_reason',
            'fields': ['has_sev', 'has_reason'],
        },
    }

    print('=== Edge Property Coverage ===')
    total_edges = 0
    total_populated = 0
    for edge_type, check in checks.items():
        rows = conn.execute_read(check['query'])
        r = rows[0] if rows else {}
        total = r.get('total', 0)
        total_edges += total
        print(f'\n{edge_type}: {total} edges')
        for field in check['fields']:
            count = r.get(field, 0)
            total_populated += count
            pct = (count / total * 100) if total else 0
            print(f'  {field}: {count}/{total} ({pct:.0f}%)')
"
```

### Section 2: Structural Validation

```bash
uv run python -m open_medicine.graphrag.ingest_v2 validate
```

### Section 3: Clinical Scenario Pass Rate

```bash
uv run python -m open_medicine.graphrag.ingest_v2 scenarios \
    --file data/cache/graphrag/aha_acc_hf_2022/test_scenarios.json 2>&1 || true
```

Report the pass/fail count.

### Section 4: Terminology Resolution

Test 20 common clinical terms for resolution:

```bash
uv run python -c "
from open_medicine.graphrag.terminology.resolver import link_entity

terms = [
    ('MRA', 'drug_class'), ('ACEi', 'drug_class'), ('ARB', 'drug_class'),
    ('ARNi', 'drug_class'), ('SGLT2 Inhibitor', 'drug_class'),
    ('Beta Blocker', 'drug_class'), ('Loop Diuretic', 'drug_class'),
    ('Sacubitril/Valsartan', 'drug'), ('Carvedilol', 'drug'),
    ('Spironolactone', 'drug'), ('Dapagliflozin', 'drug'),
    ('Lisinopril', 'drug'), ('Metoprolol', 'drug'),
    ('Furosemide', 'drug'), ('Digoxin', 'drug'),
    ('HFrEF', 'disease'), ('Heart Failure', 'disease'),
    ('Potassium', 'lab'), ('Creatinine', 'lab'), ('BNP', 'lab'),
]
passed = 0
for name, etype in terms:
    result = link_entity(name, etype)
    status = 'OK' if result else 'FAIL'
    if result: passed += 1
    print(f'  [{status}] {name} ({etype})')
print(f'\nResolved: {passed}/{len(terms)}')
"
```

### Section 5: Score Card

Based on the results above, assign grades for each section:

| Section | A | B | C | F |
|---------|---|---|---|---|
| Edge Properties | >80% fields populated | 60-80% | 40-60% | <40% |
| Structure | All checks pass | Warnings only | 1 critical fail | >1 critical |
| Scenarios | 100% pass | >85% pass | >70% pass | <70% |
| Terminology | 100% resolve | >90% | >75% | <75% |

**Overall grade**: Average of section grades (A=4, B=3, C=2, F=0).

Print the score card in this format:

```
============================================================
GraphRAG Audit Score Card
============================================================
Edge Properties:  [grade] - [detail]
Structure:        [grade] - [detail]
Scenarios:        [grade] - [detail]
Terminology:      [grade] - [detail]
------------------------------------------------------------
Overall:          [grade]
============================================================

Recommendations:
- [actionable items based on failures]
```

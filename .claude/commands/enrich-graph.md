# Enrich Graph Edge Properties

Extract structured edge properties from existing JSONL and patch onto the live graph.

## Usage

```
/enrich-graph [guideline_id]
```

Example: `/enrich-graph aha_acc_hf_2022`

Default guideline_id: `aha_acc_hf_2022`

## Process

Parse the guideline_id from `$ARGUMENTS` (default to `aha_acc_hf_2022` if empty).

### Step 1: Generate enrichment patch

Parse action_detail text from consolidated JSONL into structured edge properties:

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

### Step 2: Review patch

Before applying, review a sample of the generated patches:

```bash
uv run python -c "
import json
from pathlib import Path

guideline_id = '$ARGUMENTS'.strip() or 'aha_acc_hf_2022'
patch_path = Path(f'data/patches/{guideline_id}_enrichment.jsonl')

patches = [json.loads(line) for line in patch_path.read_text().splitlines() if line.strip()]
for rec_type in ['dosing', 'monitoring', 'interaction', 'contraindication']:
    typed = [p for p in patches if p['rec_type'] == rec_type]
    if typed:
        print(f'\n=== {rec_type} (sample 1/{len(typed)}) ===')
        sample = typed[0]
        print(f'  rec_id: {sample[\"rec_id\"]}')
        print(f'  source: {sample[\"source_text\"][:100]}...')
        print(f'  properties: {json.dumps(sample[\"properties\"], indent=4)}')
"
```

### Step 3: Apply patch to Neo4j

Update edge properties in the graph:

```bash
uv run python -c "
import json
from pathlib import Path
from dotenv import load_dotenv; load_dotenv()
from open_medicine.graphrag.config import get_settings
from open_medicine.graphrag.graph.connection import GraphConnection

guideline_id = '$ARGUMENTS'.strip() or 'aha_acc_hf_2022'
patch_path = Path(f'data/patches/{guideline_id}_enrichment.jsonl')

edge_map = {
    'dosing': 'DOSED_FOR',
    'monitoring': 'MONITORED_BY',
    'interaction': 'INTERACTS_WITH',
    'contraindication': 'CONTRAINDICATED_IN',
}

settings = get_settings()
with GraphConnection(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password) as conn:
    applied = 0
    skipped = 0
    for line in patch_path.read_text().splitlines():
        if not line.strip():
            continue
        patch = json.loads(line)
        rec_id = patch['rec_id']
        props = patch['properties']
        edge_type = edge_map.get(patch['rec_type'], '')
        if not edge_type:
            skipped += 1
            continue

        set_clauses = ', '.join(f'r.{k} = \$prop_{k}' for k in props)
        params = {f'prop_{k}': v for k, v in props.items()}
        params['rec_id'] = rec_id

        cypher = f'''
        MATCH (rec:Recommendation {{rec_id: \$rec_id}})-[:RECOMMENDS]->(entity)
        MATCH (entity)-[r:{edge_type}]->()
        SET {set_clauses}
        RETURN count(r) AS updated
        '''
        try:
            rows = conn.execute_read(cypher, params)
            if rows and rows[0].get('updated', 0) > 0:
                applied += 1
        except Exception as e:
            print(f'  Warning: {rec_id}: {e}')
            skipped += 1

    print(f'Applied: {applied} edge property updates')
    print(f'Skipped: {skipped}')
"
```

### Step 4: Verify

Run `/audit-graph` to check edge property coverage improved:

```
/audit-graph
```

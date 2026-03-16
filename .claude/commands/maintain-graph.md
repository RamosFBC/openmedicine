# Maintain Graph

Day-to-day operations for the clinical knowledge graph.

## Usage

```
/maintain-graph <operation> [args]
```

## Operations

Parse the operation from `$ARGUMENTS`.

### `check-health`

Quick health check of the graph:

```bash
uv run python -c "
from dotenv import load_dotenv; load_dotenv()
from open_medicine.graphrag.config import get_settings
from open_medicine.graphrag.graph.connection import GraphConnection

settings = get_settings()
with GraphConnection(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password) as conn:
    nodes = conn.execute_read('MATCH (n) RETURN labels(n)[0] AS label, count(n) AS cnt ORDER BY cnt DESC')
    edges = conn.execute_read('MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS cnt ORDER BY cnt DESC')
    orphans = conn.execute_read('MATCH (n) WHERE NOT EXISTS { (n)--() } AND NOT n:EvidenceChunk RETURN labels(n)[0] AS label, count(n) AS cnt')

    print('=== Node Counts ===')
    for r in nodes: print(f'  {r[\"label\"]}: {r[\"cnt\"]}')
    print('\n=== Edge Counts ===')
    for r in edges: print(f'  {r[\"type\"]}: {r[\"cnt\"]}')
    total_orphans = sum(r['cnt'] for r in orphans)
    print(f'\n=== Orphans: {total_orphans} ===')
    if total_orphans:
        for r in orphans: print(f'  {r[\"label\"]}: {r[\"cnt\"]}')
"
```

### `add-term <name> <type> [aliases...]`

Add a new term to the terminology files.

**Validation required before adding:** (1) Verify the term exists in the appropriate terminology system (SNOMED, LOINC, ATC, RxNorm). (2) Check for duplicates — search existing terminology JSON for the term or its aliases. (3) Provide the source reference for the new term. Never add terms without verified codes.


```bash
uv run python -c "
import json, sys
from pathlib import Path

args = '$ARGUMENTS'.split()[1:]  # skip 'add-term'
if len(args) < 2:
    print('Usage: /maintain-graph add-term <name> <type> [alias1 alias2 ...]')
    sys.exit(1)

name, term_type = args[0], args[1]
aliases = args[2:] if len(args) > 2 else []

type_to_file = {
    'drug': 'drugs.json', 'drug_class': 'drug_classes.json',
    'disease': 'diseases.json', 'lab': 'labs.json',
    'procedure': 'procedures.json', 'device': 'devices.json',
    'symptom': 'symptoms.json',
}
fname = type_to_file.get(term_type)
if not fname:
    print(f'Unknown type: {term_type}. Valid: {list(type_to_file.keys())}')
    sys.exit(1)

path = Path(f'src/open_medicine/graphrag/terminology/{fname}')
data = json.loads(path.read_text())
canonical = name.lower().replace(' ', '_')
if canonical in data:
    print(f'{name} already exists in {fname}')
    sys.exit(0)

data[canonical] = {'name': name, 'aliases': aliases}
path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
print(f'Added {name} ({term_type}) with aliases: {aliases}')
"
```

### `stats`

Detailed graph statistics including edge property coverage:

```bash
uv run python -c "
from dotenv import load_dotenv; load_dotenv()
from open_medicine.graphrag.config import get_settings
from open_medicine.graphrag.graph.connection import GraphConnection

settings = get_settings()
with GraphConnection(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password) as conn:
    # Node counts
    nodes = conn.execute_read('MATCH (n) RETURN labels(n)[0] AS label, count(n) AS cnt ORDER BY cnt DESC')
    # Edge counts
    edges = conn.execute_read('MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS cnt ORDER BY cnt DESC')
    # Guideline info
    guidelines = conn.execute_read('MATCH (g:Guideline) RETURN g.title AS title, g.doi AS doi, g.year AS year')
    # Evidence chunks with embeddings
    emb_stats = conn.execute_read('MATCH (ec:EvidenceChunk) RETURN count(ec) AS total, sum(CASE WHEN ec.embedding IS NOT NULL THEN 1 ELSE 0 END) AS embedded')

    print('=== Guidelines Loaded ===')
    for g in guidelines:
        print(f'  {g[\"title\"]} ({g.get(\"year\", \"?\")})')
        print(f'    DOI: {g.get(\"doi\", \"N/A\")}')

    print('\n=== Node Counts ===')
    total_nodes = sum(r['cnt'] for r in nodes)
    for r in nodes: print(f'  {r[\"label\"]}: {r[\"cnt\"]}')
    print(f'  Total: {total_nodes}')

    print('\n=== Edge Counts ===')
    total_edges = sum(r['cnt'] for r in edges)
    for r in edges: print(f'  {r[\"type\"]}: {r[\"cnt\"]}')
    print(f'  Total: {total_edges}')

    e = emb_stats[0] if emb_stats else {}
    print(f'\n=== Embeddings ===')
    print(f'  EvidenceChunks: {e.get(\"total\", 0)}')
    print(f'  With embeddings: {e.get(\"embedded\", 0)}')
"
```

### `repair-evidence`

Re-link orphaned EvidenceChunk nodes to their source recommendations:

```bash
uv run python -c "
from dotenv import load_dotenv; load_dotenv()
from open_medicine.graphrag.config import get_settings
from open_medicine.graphrag.graph.connection import GraphConnection

settings = get_settings()
with GraphConnection(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password) as conn:
    orphans = conn.execute_read('''
        MATCH (ec:EvidenceChunk)
        WHERE NOT EXISTS { (:Recommendation)-[:SOURCED_FROM]->(ec) }
        RETURN ec.chunk_id AS id, ec.text AS text LIMIT 20
    ''')
    print(f'Found {len(orphans)} orphaned EvidenceChunks')
    for o in orphans:
        print(f'  {o[\"id\"]}: {o[\"text\"][:80]}...')

    if orphans:
        print('\nTo fix: re-run /ingest-guideline to reload the graph')
"
```

## Quality Assurance

After any maintenance operation, verify A+ quality standards from CLAUDE.md are maintained. Run `/audit-graph` if structural changes were made.

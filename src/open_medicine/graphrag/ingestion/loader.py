from __future__ import annotations
import json
from dataclasses import dataclass
from open_medicine.graphrag.graph.schema import Guideline
from open_medicine.graphrag.ingestion.chunker import Chunk
from open_medicine.graphrag.ingestion.extractor import ExtractionResult
from open_medicine.graphrag.ingestion.linker import link_entity
from open_medicine.graphrag.graph.connection import GraphConnection


@dataclass
class LoadableGuideline:
    guideline: Guideline
    chunks: list[Chunk]
    extractions: list[ExtractionResult]


def load_guideline(conn: GraphConnection, data: LoadableGuideline) -> None:
    """Load a complete guideline into Neo4j as a single transaction."""
    queries: list[tuple[str, dict]] = []

    # 1. Delete existing data for this guideline (idempotent)
    queries.append((
        "MATCH (n) WHERE n.guideline_id = $gid DETACH DELETE n",
        {"gid": data.guideline.id},
    ))
    queries.append((
        "MATCH (g:Guideline {id: $gid}) DETACH DELETE g",
        {"gid": data.guideline.id},
    ))

    # 2. Create Guideline node
    queries.append((
        "CREATE (g:Guideline {id: $id, title: $title, doi: $doi, year: $year, organization: $org, total_pages: $pages})",
        {
            "id": data.guideline.id, "title": data.guideline.title,
            "doi": data.guideline.doi, "year": data.guideline.year,
            "org": data.guideline.organization, "pages": data.guideline.total_pages,
        },
    ))

    # 3. Create EvidenceChunk nodes
    for chunk in data.chunks:
        queries.append((
            "CREATE (ec:EvidenceChunk {id: $id, text: $text, guideline_id: $gid, section: $section})",
            {"id": chunk.id, "text": chunk.text, "gid": chunk.guideline_id, "section": chunk.section},
        ))
        # BELONGS_TO edge
        queries.append((
            "MATCH (ec:EvidenceChunk {id: $cid}), (g:Guideline {id: $gid}) CREATE (ec)-[:BELONGS_TO]->(g)",
            {"cid": chunk.id, "gid": data.guideline.id},
        ))
        # CHILD_OF edge
        if chunk.parent_chunk_id:
            queries.append((
                "MATCH (child:EvidenceChunk {id: $cid}), (parent:EvidenceChunk {id: $pid}) CREATE (child)-[:CHILD_OF]->(parent)",
                {"cid": chunk.id, "pid": chunk.parent_chunk_id},
            ))

    # 4. Create LogicNode + Concept nodes
    for extraction in data.extractions:
        ln = extraction.logic_node
        conditions_json = json.dumps([c.model_dump() for c in ln.conditions])
        queries.append((
            "CREATE (ln:LogicNode {id: $id, type: $type, conditions: $conds, action: $action, "
            "action_detail: $detail, strength: $strength, guideline_id: $gid, page: $page})",
            {
                "id": ln.id, "type": ln.type.value, "conds": conditions_json,
                "action": ln.action, "detail": ln.action_detail,
                "strength": ln.strength, "gid": ln.guideline_id, "page": ln.page,
            },
        ))
        # DEFINED_BY edge
        queries.append((
            "MATCH (ln:LogicNode {id: $lid}), (g:Guideline {id: $gid}) CREATE (ln)-[:DEFINED_BY]->(g)",
            {"lid": ln.id, "gid": data.guideline.id},
        ))

        # Concept nodes + PARTICIPATES_IN edges
        for concept_ref in extraction.concepts:
            linked = link_entity(concept_ref.name, concept_ref.type)
            c_id = concept_ref.name.lower().replace(" ", "_")
            c_name = linked.canonical_name if linked else concept_ref.name
            snomed = linked.snomed_code if linked else None
            loinc = linked.loinc_code if linked else None

            queries.append((
                "MERGE (c:Concept {id: $id}) "
                "ON CREATE SET c.name = $name, c.type = $type, c.snomed_code = $snomed, c.loinc_code = $loinc",
                {"id": c_id, "name": c_name, "type": concept_ref.type, "snomed": snomed, "loinc": loinc},
            ))
            queries.append((
                "MATCH (c:Concept {id: $cid}), (ln:LogicNode {id: $lid}) "
                "CREATE (c)-[:PARTICIPATES_IN {role: $role}]->(ln)",
                {"cid": c_id, "lid": ln.id, "role": "intervention"},
            ))

    conn.execute_write_tx(queries)

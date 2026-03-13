from __future__ import annotations
import json
from dataclasses import dataclass
from itertools import combinations
from open_medicine.graphrag.graph.schema import Guideline
from open_medicine.graphrag.graph.queries import LoaderQueries
from open_medicine.graphrag.ingestion.chunker import Chunk
from open_medicine.graphrag.ingestion.extractor import ExtractionResult
from open_medicine.graphrag.ingestion.linker import link_entity, link_variable
from open_medicine.graphrag.graph.connection import GraphConnection

CONTRADICTORY_ACTIONS = {
    frozenset({"initiate", "contraindicated"}),
    frozenset({"initiate", "avoid"}),
    frozenset({"dose_adjust", "contraindicated"}),
    frozenset({"prefer", "avoid"}),
    frozenset({"monitor", "contraindicated"}),
}

STRENGTH_RANK = {"Strong/A": 0, "Moderate/B": 1, "Weak/C": 2, "Expert_Opinion": 3}


@dataclass
class LoadableGuideline:
    guideline: Guideline
    chunks: list[Chunk]
    extractions: list[ExtractionResult]


def detect_conflicts(
    extractions: list[ExtractionResult],
) -> list[tuple[str, str, str]]:
    """Detect conflicting LogicNode pairs. Returns (winner_id, loser_id, resolution)."""
    conflicts: list[tuple[str, str, str]] = []

    # Group by (shared concept, type)
    by_key: dict[tuple[str, str], list[ExtractionResult]] = {}
    for ext in extractions:
        for concept in ext.concepts:
            key = (concept.name.lower(), ext.logic_node.type.value)
            by_key.setdefault(key, []).append(ext)

    for group in by_key.values():
        if len(group) < 2:
            continue
        for a, b in combinations(group, 2):
            action_pair = frozenset({a.logic_node.action, b.logic_node.action})
            if action_pair not in CONTRADICTORY_ACTIONS:
                continue

            # Determine winner
            a_year = int(a.logic_node.guideline_id.split("_")[-1]) if a.logic_node.guideline_id.split("_")[-1].isdigit() else 0
            b_year = int(b.logic_node.guideline_id.split("_")[-1]) if b.logic_node.guideline_id.split("_")[-1].isdigit() else 0

            if a_year != b_year:
                resolution = "newer"
                winner, loser = (a, b) if a_year > b_year else (b, a)
            else:
                resolution = "stronger"
                a_rank = STRENGTH_RANK.get(a.logic_node.strength, 99)
                b_rank = STRENGTH_RANK.get(b.logic_node.strength, 99)
                winner, loser = (a, b) if a_rank <= b_rank else (b, a)

            conflicts.append((winner.logic_node.id, loser.logic_node.id, resolution))

    return conflicts


def load_guideline(conn: GraphConnection, data: LoadableGuideline) -> None:
    """Load a complete guideline into Neo4j as a single transaction."""
    queries: list[tuple[str, dict]] = []

    # 1. Delete existing data (idempotent)
    queries.extend(LoaderQueries.delete_guideline(data.guideline.id))

    # 2. Create Guideline node
    queries.append(LoaderQueries.create_guideline(data.guideline))

    # 3. Create EvidenceChunk nodes + edges
    for chunk in data.chunks:
        queries.append(LoaderQueries.create_evidence_chunk(
            chunk.id, chunk.text, chunk.guideline_id, chunk.section,
        ))
        queries.append(LoaderQueries.create_belongs_to(chunk.id, data.guideline.id))
        if chunk.parent_chunk_id:
            queries.append(LoaderQueries.create_child_of(chunk.id, chunk.parent_chunk_id))

    # 4. Create LogicNode + Concept + PatientVariable nodes + all edges
    seen_variables: set[str] = set()
    for extraction in data.extractions:
        ln = extraction.logic_node
        conditions_json = json.dumps([c.model_dump() for c in ln.conditions])
        queries.append(LoaderQueries.create_logic_node(
            ln.id, ln.type.value, conditions_json,
            ln.action, ln.action_detail, ln.strength,
            ln.guideline_id, ln.page,
        ))
        queries.append(LoaderQueries.create_defined_by(ln.id, data.guideline.id))

        # SOURCED_FROM edge
        if extraction.source_chunk_id:
            queries.append(LoaderQueries.create_sourced_from(ln.id, extraction.source_chunk_id))

        # Concept nodes + PARTICIPATES_IN edges
        drug_concepts: list[str] = []
        for concept_ref in extraction.concepts:
            linked = link_entity(concept_ref.name, concept_ref.type)
            c_id = concept_ref.name.lower().replace(" ", "_")
            c_name = linked.canonical_name if linked else concept_ref.name
            snomed = linked.snomed_code if linked else None
            loinc = linked.loinc_code if linked else None

            queries.append(LoaderQueries.create_concept(c_id, c_name, concept_ref.type, snomed, loinc))
            queries.append(LoaderQueries.create_participates_in(c_id, ln.id, "intervention"))

            if concept_ref.type == "drug":
                drug_concepts.append(c_id)

        # INTERACTS_WITH edges for interaction-type LogicNodes
        if ln.type.value == "interaction" and len(drug_concepts) >= 2:
            for i in range(len(drug_concepts)):
                for j in range(i + 1, len(drug_concepts)):
                    queries.append(LoaderQueries.create_interacts_with(drug_concepts[i], drug_concepts[j]))

        # PatientVariable nodes + EVALUATES edges
        for cond in ln.conditions:
            var_name = cond.variable
            if var_name not in seen_variables:
                seen_variables.add(var_name)
                linked_var = link_variable(var_name)
                if linked_var:
                    queries.append(LoaderQueries.create_patient_variable(
                        var_name, linked_var.canonical_name,
                        linked_var.unit, linked_var.loinc_code, linked_var.var_type,
                    ))
                else:
                    queries.append(LoaderQueries.create_patient_variable(
                        var_name, var_name, "", None, "continuous",
                    ))
            queries.append(LoaderQueries.create_evaluates(ln.id, var_name))

    # 5. Conflict detection
    conflicts = detect_conflicts(data.extractions)
    for winner_id, loser_id, resolution in conflicts:
        queries.append(LoaderQueries.create_conflicts_with(winner_id, loser_id, resolution))

    conn.execute_write_tx(queries)

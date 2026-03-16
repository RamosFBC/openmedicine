"""Guideline loader v2 — Typed nodes, semantic edges, dual-layer graph.

Supersedes loader.py. Creates label-per-type nodes and semantic relationship
types, building both Layer 1 (direct clinical edges) and Layer 2 (evidence
provenance edges).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from itertools import combinations
from typing import TYPE_CHECKING

from open_medicine.graphrag.graph.queries_v2 import CypherStatement, LoaderQueries

if TYPE_CHECKING:
    from open_medicine.graphrag.graph.connection import GraphConnection
from open_medicine.graphrag.enrichment import (
    parse_contraindication_properties,
    parse_interaction_properties,
)
from open_medicine.graphrag.graph.schema_v2 import (
    ContraindicatedInProps,
    ContraindicationSeverity,
    DosedForProps,
    EvidenceQuality,
    Guideline,
    IndicatedForProps,
    InteractsWithProps,
    InteractionSeverity,
    MonitoredByProps,
    Recommendation,
    RecommendationStrength,
    RecommendationType,
)
from open_medicine.graphrag.ingestion.chunker import Chunk
from open_medicine.graphrag.ingestion.extractor_v2 import (
    ConceptRef,
    ExtractedRelationship,
    ExtractionResult,
)
from open_medicine.graphrag.ingestion.linker_v2 import (
    LinkedEntity,
    get_drug_class_members,
    link_entity,
    link_variable,
)

logger = logging.getLogger(__name__)

# Actions that contradict each other (for conflict detection)
CONTRADICTORY_ACTIONS = {
    frozenset({"initiate", "contraindicated"}),
    frozenset({"initiate", "avoid"}),
    frozenset({"dose_adjust", "contraindicated"}),
    frozenset({"prefer", "avoid"}),
    frozenset({"monitor", "contraindicated"}),
    frozenset({"prescribe", "contraindicated"}),
    frozenset({"prescribe", "avoid"}),
    frozenset({"recommend", "avoid"}),
}

# Strength ranking for conflict resolution (lower = stronger)
STRENGTH_RANK = {
    "strong_for": 0,
    "moderate_for": 1,
    "weak_for": 2,
    "strong_against": 0,
    "no_benefit": 1,
}

# Maps (rec_type, source_entity_type, target_entity_type) → semantic edge type
_EDGE_DERIVATION: dict[tuple[str, str, str], str] = {
    # Treatment selection → INDICATED_FOR
    ("treatment_selection", "drug", "disease"): "INDICATED_FOR",
    ("treatment_selection", "drug_class", "disease"): "INDICATED_FOR",
    ("treatment_selection", "procedure", "disease"): "INDICATED_FOR",
    ("treatment_selection", "device", "disease"): "INDICATED_FOR",
    # Device therapy → INDICATED_FOR
    ("device_therapy", "device", "disease"): "INDICATED_FOR",
    # Contraindication → CONTRAINDICATED_IN
    ("contraindication", "drug", "disease"): "CONTRAINDICATED_IN",
    ("contraindication", "drug_class", "disease"): "CONTRAINDICATED_IN",
    ("contraindication", "procedure", "disease"): "CONTRAINDICATED_IN",
    # Dosing → DOSED_FOR
    ("dosing", "drug", "disease"): "DOSED_FOR",
    # Monitoring → MONITORED_BY
    ("monitoring", "drug", "lab"): "MONITORED_BY",
    ("monitoring", "drug_class", "lab"): "MONITORED_BY",
    # Interaction → INTERACTS_WITH
    ("interaction", "drug", "drug"): "INTERACTS_WITH",
    ("interaction", "drug", "drug_class"): "INTERACTS_WITH",
    ("interaction", "drug_class", "drug"): "INTERACTS_WITH",
    ("interaction", "drug_class", "drug_class"): "INTERACTS_WITH",
    # Diagnostic → DIAGNOSED_BY
    ("diagnostic_criteria", "disease", "procedure"): "DIAGNOSED_BY",
    ("diagnostic_criteria", "disease", "lab"): "DIAGNOSED_BY",
}


@dataclass
class LoadableGuideline:
    """All data needed to load a guideline into the graph."""

    guideline: Guideline
    chunks: list[Chunk]
    extractions: list[ExtractionResult]


def detect_conflicts(
    extractions: list[ExtractionResult],
) -> list[tuple[str, str, str]]:
    """Detect conflicting recommendation pairs.

    Returns list of (winner_id, loser_id, resolution).
    """
    conflicts: list[tuple[str, str, str]] = []

    # Group by (shared concept name, rec_type)
    by_key: dict[tuple[str, str], list[ExtractionResult]] = {}
    for ext in extractions:
        for concept in ext.concepts:
            key = (concept.name.lower(), ext.rec_type)
            by_key.setdefault(key, []).append(ext)

    for group in by_key.values():
        if len(group) < 2:
            continue
        for a, b in combinations(group, 2):
            action_pair = frozenset(
                {a.action.lower().split()[0], b.action.lower().split()[0]}
            )
            if action_pair not in CONTRADICTORY_ACTIONS:
                continue

            # Determine winner: newer guideline wins, then stronger recommendation
            a_year = _extract_year(a.guideline_id)
            b_year = _extract_year(b.guideline_id)

            if a_year != b_year:
                resolution = "newer"
                winner, loser = (a, b) if a_year > b_year else (b, a)
            else:
                resolution = "stronger"
                a_rank = STRENGTH_RANK.get(a.strength, 99)
                b_rank = STRENGTH_RANK.get(b.strength, 99)
                winner, loser = (a, b) if a_rank <= b_rank else (b, a)

            conflicts.append((winner.rec_id, loser.rec_id, resolution))

    return conflicts


def _extract_year(guideline_id: str) -> int:
    """Try to extract a year from a guideline ID string."""
    parts = guideline_id.split("_")
    for part in reversed(parts):
        if part.isdigit() and len(part) == 4:
            return int(part)
    return 0


def load_guideline(conn: GraphConnection, data: LoadableGuideline) -> None:
    """Load a complete guideline into Neo4j as a single transaction.

    Creates:
    - Typed clinical nodes (Drug, Disease, Lab, etc.)
    - Recommendation nodes with evidence links (Layer 2)
    - Semantic edges between clinical nodes (Layer 1)
    - Drug class membership (MEMBER_OF) edges
    - PatientVariable → Lab (MEASURES) edges
    - Conflict edges between contradictory recommendations
    """
    queries: list[CypherStatement] = []

    # 1. Delete existing data (idempotent)
    queries.extend(LoaderQueries.delete_guideline(data.guideline.id))

    # 2. Create Guideline node
    queries.append(LoaderQueries.create_guideline(data.guideline))

    # 3. Create EvidenceChunk nodes
    for chunk in data.chunks:
        queries.append(
            LoaderQueries.create_evidence_chunk(
                chunk.id, chunk.text, section=chunk.section
            )
        )

    # 4. Process each extraction → create typed nodes + edges
    seen_entities: dict[str, LinkedEntity] = {}  # node_id → LinkedEntity
    seen_variables: set[str] = set()
    seen_member_of: set[tuple[str, str]] = set()  # (drug_id, class_id)
    seen_measures: set[tuple[str, str]] = set()  # (var_id, lab_id)

    for extraction in data.extractions:
        # 4a. Create Recommendation node
        rec = Recommendation(
            id=extraction.rec_id,
            type=RecommendationType(extraction.rec_type),
            action=extraction.action,
            action_detail=extraction.action_detail,
            strength=RecommendationStrength(extraction.strength),
            evidence_quality=EvidenceQuality(extraction.evidence_quality),
            conditions_json=json.dumps(extraction.conditions)
            if extraction.conditions
            else None,
            guideline_id=data.guideline.id,
            page=extraction.page,
        )
        queries.append(LoaderQueries.create_recommendation(rec))

        # Layer 2: DEFINED_BY → Guideline
        queries.append(
            LoaderQueries.create_defined_by(extraction.rec_id, data.guideline.id)
        )

        # Layer 2: SOURCED_FROM → EvidenceChunk
        if extraction.source_chunk_id:
            queries.append(
                LoaderQueries.create_sourced_from(
                    extraction.rec_id, extraction.source_chunk_id
                )
            )

        # 4b. Create typed entity nodes + Layer 2 RECOMMENDS edges
        entity_map: dict[str, LinkedEntity] = {}  # role → linked entity
        for concept_ref in extraction.concepts:
            linked = _ensure_entity_node(queries, concept_ref, seen_entities)
            entity_map[f"{concept_ref.role}:{concept_ref.name}"] = linked

            # Layer 2: RECOMMENDS edge
            queries.append(
                LoaderQueries.create_recommends(
                    extraction.rec_id,
                    linked.node_id,
                    linked.node_label,
                    role=concept_ref.role,
                )
            )

            # Layer 2: FOR_CONDITION edge (disease targets)
            if linked.entity_type == "disease":
                queries.append(
                    LoaderQueries.create_for_condition(
                        extraction.rec_id, linked.node_id
                    )
                )

        # 4c. Create semantic edges (Layer 1) from explicit relationships
        for rel in extraction.relationships:
            _create_semantic_edge_from_relationship(
                queries, rel, seen_entities, extraction
            )

        # 4d. Derive semantic edges from rec_type + entity types
        _derive_semantic_edges(queries, extraction, entity_map)

        # 4e. PatientVariable nodes + EVALUATES edges
        for cond in extraction.conditions:
            var_name = cond.get("variable", "")
            if not var_name:
                continue
            if var_name not in seen_variables:
                seen_variables.add(var_name)
                linked_var = link_variable(var_name)
                if linked_var:
                    queries.append(
                        LoaderQueries.create_patient_variable(
                            linked_var.var_id,
                            linked_var.canonical_name,
                            loinc_code=linked_var.loinc_code,
                            unit=linked_var.unit,
                            var_type=linked_var.var_type,
                        )
                    )
                    # MEASURES edge: PatientVariable → Lab
                    if linked_var.linked_lab:
                        lab_entry = link_entity(linked_var.linked_lab, "lab")
                        if lab_entry:
                            _ensure_entity_node(
                                queries,
                                ConceptRef(
                                    linked_var.linked_lab, "lab", "monitor"
                                ),
                                seen_entities,
                            )
                            pair = (linked_var.var_id, lab_entry.node_id)
                            if pair not in seen_measures:
                                seen_measures.add(pair)
                                queries.append(
                                    LoaderQueries.create_measures(
                                        linked_var.var_id, lab_entry.node_id
                                    )
                                )
                else:
                    queries.append(
                        LoaderQueries.create_patient_variable(
                            f"pv:{var_name.lower()}",
                            var_name,
                            var_type="continuous",
                        )
                    )

            # EVALUATES edge
            linked_var = link_variable(var_name)
            var_id = linked_var.var_id if linked_var else f"pv:{var_name.lower()}"
            queries.append(
                LoaderQueries.create_evaluates(extraction.rec_id, var_id)
            )

    # 5. Drug class membership (MEMBER_OF) edges
    for entity in seen_entities.values():
        if entity.entity_type == "drug_class":
            members = get_drug_class_members(entity.canonical_name)
            for member_name in members:
                member = link_entity(member_name, "drug")
                if member and member.node_id in seen_entities:
                    pair = (member.node_id, entity.node_id)
                    if pair not in seen_member_of:
                        seen_member_of.add(pair)
                        queries.append(
                            LoaderQueries.create_member_of(
                                member.node_id, entity.node_id
                            )
                        )

    # 6. Propagate MONITORED_BY edges from member drugs to parent DrugClass
    queries.extend(propagate_monitoring_to_classes(queries, seen_entities))

    # 7. Conflict detection
    conflicts = detect_conflicts(data.extractions)
    for winner_id, loser_id, resolution in conflicts:
        queries.append(
            LoaderQueries.create_conflicts_with(winner_id, loser_id, resolution)
        )

    logger.info("Executing %d Cypher statements in batches...", len(queries))
    conn.execute_write_tx(queries)
    logger.info("All statements executed.")


def _ensure_entity_node(
    queries: list[CypherStatement],
    concept_ref: ConceptRef,
    seen: dict[str, LinkedEntity],
) -> LinkedEntity:
    """Create a typed entity node if not already seen. Returns the LinkedEntity."""
    linked = link_entity(concept_ref.name, concept_ref.type)
    if linked is None:
        # Should not happen — link_entity returns minimal entry for unknown entities
        linked = LinkedEntity(
            canonical_name=concept_ref.name,
            entity_type=concept_ref.type,
            node_label=concept_ref.type.title(),
            node_id=f"{concept_ref.type}:{concept_ref.name.lower().replace(' ', '_')}",
        )

    if linked.node_id not in seen:
        seen[linked.node_id] = linked
        queries.append(_create_node_query(linked))

    return linked


def _create_node_query(entity: LinkedEntity) -> CypherStatement:
    """Create the appropriate typed node query for an entity."""
    t = entity.entity_type
    if t == "drug":
        return LoaderQueries.create_drug(
            entity.node_id,
            entity.canonical_name,
            rxnorm_code=entity.rxnorm_code,
            snomed_code=entity.snomed_code,
            atc_code=entity.atc_code,
            aliases=entity.aliases,
        )
    if t == "drug_class":
        return LoaderQueries.create_drug_class(
            entity.node_id,
            entity.canonical_name,
            atc_code=entity.atc_code,
            aliases=entity.aliases,
        )
    if t == "disease":
        return LoaderQueries.create_disease(
            entity.node_id,
            entity.canonical_name,
            snomed_code=entity.snomed_code,
            icd10_code=entity.icd10_code,
            aliases=entity.aliases,
        )
    if t == "symptom":
        return LoaderQueries.create_symptom(
            entity.node_id,
            entity.canonical_name,
            snomed_code=entity.snomed_code,
            aliases=entity.aliases,
        )
    if t == "lab":
        return LoaderQueries.create_lab(
            entity.node_id,
            entity.canonical_name,
            loinc_code=entity.loinc_code,
            snomed_code=entity.snomed_code,
            unit=entity.unit,
            reference_range=entity.reference_range,
        )
    if t == "procedure":
        return LoaderQueries.create_procedure(
            entity.node_id,
            entity.canonical_name,
            snomed_code=entity.snomed_code,
            cpt_code=entity.cpt_code,
            aliases=entity.aliases,
        )
    if t == "device":
        return LoaderQueries.create_device(
            entity.node_id,
            entity.canonical_name,
            snomed_code=entity.snomed_code,
            gmdn_code=entity.gmdn_code,
            aliases=entity.aliases,
        )
    # Fallback — shouldn't reach here
    return LoaderQueries.create_drug(entity.node_id, entity.canonical_name)


def _derive_semantic_edges(
    queries: list[CypherStatement],
    extraction: ExtractionResult,
    entity_map: dict[str, LinkedEntity],
) -> None:
    """Derive Layer 1 semantic edges from rec_type + entity type combinations.

    Safety warnings only get Layer 2 (RECOMMENDS) edges — no Layer 1
    semantic edges, to avoid false CONTRAINDICATED_IN signals for drugs
    that are actually indicated.
    """
    # safety_warning: no Layer 1 edges — only Layer 2 RECOMMENDS (already created)
    if extraction.rec_type == "safety_warning":
        return

    # Separate entities by role
    subjects = [
        e for key, e in entity_map.items() if key.startswith("subject:")
    ]
    targets = [
        e for key, e in entity_map.items() if key.startswith("target:")
    ]
    # Labs with role "monitor" — always create MONITORED_BY edges for monitoring recs,
    # even when disease targets also exist (disease targets get INDICATED_FOR separately)
    monitors = [
        e for key, e in entity_map.items() if key.startswith("monitor:")
    ]
    if monitors and extraction.rec_type == "monitoring":
        # Create MONITORED_BY edges directly: each drug subject → each monitor lab
        drug_subjects = [
            e for key, e in entity_map.items()
            if key.startswith("subject:") and e.entity_type in ("drug", "drug_class")
        ]
        for drug in drug_subjects:
            for lab in monitors:
                _create_semantic_edge(
                    queries, "MONITORED_BY", drug, lab, extraction
                )
        # Still add monitors to targets so they can match other derivation rules
        targets.extend(monitors)

    # If no explicit roles, try to infer from entity types and rec_type
    if not targets:
        # For treatment_selection: drugs/procedures are subjects, diseases are targets
        if extraction.rec_type in (
            "treatment_selection",
            "dosing",
            "contraindication",
            "device_therapy",
        ):
            new_subjects = []
            for e in subjects:
                if e.entity_type in ("drug", "drug_class", "procedure", "device"):
                    new_subjects.append(e)
                elif e.entity_type == "disease":
                    targets.append(e)
            if new_subjects:
                subjects = new_subjects
        elif extraction.rec_type == "monitoring":
            new_subjects = []
            for e in subjects:
                if e.entity_type in ("drug", "drug_class"):
                    new_subjects.append(e)
                elif e.entity_type == "lab":
                    targets.append(e)
            if new_subjects:
                subjects = new_subjects
        elif extraction.rec_type == "diagnostic_criteria":
            new_subjects = []
            for e in subjects:
                if e.entity_type == "disease":
                    new_subjects.append(e)
                elif e.entity_type in ("lab", "procedure"):
                    targets.append(e)
            if new_subjects:
                subjects = new_subjects
        elif extraction.rec_type == "interaction":
            # Separate drugs/drug_classes into two groups by entity type
            # to pair drugs with interacting drug_classes (and vice versa)
            drugs = [e for e in subjects if e.entity_type == "drug"]
            drug_classes = [e for e in subjects if e.entity_type == "drug_class"]
            # If we have both drugs and drug_classes, pair across groups
            if drugs and drug_classes:
                for d in drugs:
                    for dc in drug_classes:
                        _create_interacts_with(queries, d, dc, extraction)
                return
            # If only drugs (2+), fall back to all-pairs
            all_interactors = drugs + drug_classes
            if len(all_interactors) >= 2:
                for i, d1 in enumerate(all_interactors):
                    for d2 in all_interactors[i + 1 :]:
                        _create_interacts_with(queries, d1, d2, extraction)
                return

    # Create semantic edges for each subject → target pair
    for src in subjects:
        for tgt in targets:
            edge_key = (extraction.rec_type, src.entity_type, tgt.entity_type)
            edge_type = _EDGE_DERIVATION.get(edge_key)
            if edge_type:
                _create_semantic_edge(queries, edge_type, src, tgt, extraction)


def _create_semantic_edge(
    queries: list[CypherStatement],
    edge_type: str,
    source: LinkedEntity,
    target: LinkedEntity,
    extraction: ExtractionResult,
) -> None:
    """Create a typed semantic edge (Layer 1)."""
    if edge_type == "INDICATED_FOR":
        props = IndicatedForProps(
            strength=RecommendationStrength(extraction.strength),
            evidence_quality=EvidenceQuality(extraction.evidence_quality),
            conditions_json=json.dumps(extraction.conditions)
            if extraction.conditions
            else None,
        )
        queries.append(
            LoaderQueries.create_indicated_for(
                source.node_id, source.node_label, target.node_id, props
            )
        )
    elif edge_type == "CONTRAINDICATED_IN":
        # Use enrichment to derive severity from action_detail text
        ci_props = parse_contraindication_properties(extraction.action_detail)
        severity_str = ci_props.get("severity", "").lower()
        if severity_str in ("absolute", "relative"):
            severity = ContraindicationSeverity(severity_str)
        else:
            severity = ContraindicationSeverity.UNKNOWN
        props = ContraindicatedInProps(
            strength=RecommendationStrength(extraction.strength),
            severity=severity,
            evidence_quality=EvidenceQuality(extraction.evidence_quality),
        )
        queries.append(
            LoaderQueries.create_contraindicated_in(
                source.node_id, source.node_label, target.node_id, props
            )
        )
    elif edge_type == "DOSED_FOR":
        # Extract dosing properties from relationship properties if available
        dosed_props = DosedForProps(
            conditions_json=json.dumps(extraction.conditions)
            if extraction.conditions
            else None,
        )
        queries.append(
            LoaderQueries.create_dosed_for(
                source.node_id, target.node_id, dosed_props
            )
        )
    elif edge_type == "MONITORED_BY":
        mon_props = MonitoredByProps()
        queries.append(
            LoaderQueries.create_monitored_by(
                source.node_id, target.node_id, mon_props
            )
        )
    elif edge_type == "DIAGNOSED_BY":
        queries.append(
            LoaderQueries.create_diagnosed_by(
                source.node_id, target.node_id, target.node_label
            )
        )


def _create_interacts_with(
    queries: list[CypherStatement],
    drug_a: LinkedEntity,
    drug_b: LinkedEntity,
    extraction: ExtractionResult,
) -> None:
    """Create INTERACTS_WITH edge between two drugs/drug classes."""
    # Use enrichment to derive severity from action_detail text
    ix_props = parse_interaction_properties(extraction.action_detail)
    severity_str = ix_props.get("severity", "").lower()
    if severity_str in ("major", "moderate", "minor"):
        severity = InteractionSeverity(severity_str)
    else:
        severity = InteractionSeverity.UNKNOWN
    props = InteractsWithProps(
        severity=severity,
        evidence_quality=EvidenceQuality(extraction.evidence_quality),
    )
    queries.append(
        LoaderQueries.create_interacts_with(
            drug_a.node_id,
            drug_b.node_id,
            props,
            source_label=drug_a.node_label,
            target_label=drug_b.node_label,
        )
    )


def propagate_monitoring_to_classes(
    queries: list[CypherStatement],
    seen_entities: dict[str, LinkedEntity],
) -> list[CypherStatement]:
    """Propagate MONITORED_BY edges from member drugs to their parent DrugClass.

    Scans the already-built query list for MONITORED_BY edges on drugs,
    then creates matching edges on the parent DrugClass if that class
    is in the seen_entities set.
    """
    # Collect MONITORED_BY edges per drug: drug_id → list of (lab_id, props_dict)
    drug_monitoring: dict[str, list[tuple[str, dict]]] = {}
    for cypher_str, params in queries:
        if "MONITORED_BY" in cypher_str and "did" in params and "lid" in params:
            drug_id = params["did"]
            lab_id = params["lid"]
            props = {
                k: params.get(k)
                for k in ("freq", "alert", "stop", "conds")
                if params.get(k) is not None
            }
            drug_monitoring.setdefault(drug_id, []).append((lab_id, props))

    if not drug_monitoring:
        return []

    # For each drug class, check if its members have monitoring edges
    propagated: list[CypherStatement] = []
    seen_class_labs: set[tuple[str, str]] = set()

    for entity in seen_entities.values():
        if entity.entity_type != "drug_class":
            continue

        members = get_drug_class_members(entity.canonical_name)
        for member_name in members:
            member = link_entity(member_name, "drug")
            if member is None or member.node_id not in drug_monitoring:
                continue

            for lab_id, props in drug_monitoring[member.node_id]:
                key = (entity.node_id, lab_id)
                if key in seen_class_labs:
                    continue
                seen_class_labs.add(key)

                # Create MONITORED_BY on the DrugClass
                propagated.append((
                    "MATCH (dc:DrugClass {id: $did}), (l:Lab {id: $lid}) "
                    "MERGE (dc)-[r:MONITORED_BY]->(l) "
                    "ON CREATE SET r.frequency = $freq, r.threshold_alert = $alert, "
                    "r.threshold_stop = $stop, r.conditions_json = $conds, "
                    "r._source = 'propagated'",
                    {
                        "did": entity.node_id,
                        "lid": lab_id,
                        **{k: props.get(k) for k in ("freq", "alert", "stop", "conds")},
                    },
                ))

    return propagated


def _create_semantic_edge_from_relationship(
    queries: list[CypherStatement],
    rel: ExtractedRelationship,
    seen: dict[str, LinkedEntity],
    extraction: ExtractionResult,
) -> None:
    """Create a semantic edge from an explicitly extracted relationship."""
    # Ensure both entities exist
    src_ref = ConceptRef(rel.source_name, rel.source_type, "subject")
    tgt_ref = ConceptRef(rel.target_name, rel.target_type, "target")
    src = _ensure_entity_node(queries, src_ref, seen)
    tgt = _ensure_entity_node(queries, tgt_ref, seen)

    if rel.rel_type == "MEMBER_OF" and src.entity_type == "drug":
        queries.append(LoaderQueries.create_member_of(src.node_id, tgt.node_id))
    elif rel.rel_type in _EDGE_DERIVATION.values():
        _create_semantic_edge(queries, rel.rel_type, src, tgt, extraction)

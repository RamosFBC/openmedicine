"""GraphRAG Query Builders v2 — Typed nodes, semantic edges, dual-layer queries.

Supersedes queries.py (generic Concept + PARTICIPATES_IN).
All Cypher uses label-per-type nodes and semantic relationship types.
"""

from __future__ import annotations

from open_medicine.graphrag.graph.schema_v2 import (
    ContraindicatedInProps,
    DosedForProps,
    Guideline,
    IndicatedForProps,
    InteractsWithProps,
    MonitoredByProps,
    Recommendation,
)

# Type alias for a Cypher statement + parameter dict
CypherStatement = tuple[str, dict]


# ---------------------------------------------------------------------------
# Loader Queries (ingestion)
# ---------------------------------------------------------------------------


class LoaderQueries:
    """Cypher builders for ingestion with typed nodes and semantic edges."""

    # -- Guideline lifecycle ---------------------------------------------------

    @staticmethod
    def delete_guideline(guideline_id: str) -> list[CypherStatement]:
        """Delete a guideline and all nodes scoped to it.

        Preserves edges with _source='patch' — these are manual corrections
        that should survive re-ingestion.
        """
        return [
            # Delete non-patch edges from Recommendations first
            (
                "MATCH (rec:Recommendation {guideline_id: $gid})-[r]-() "
                "WHERE coalesce(r._source, '') <> 'patch' "
                "DELETE r",
                {"gid": guideline_id},
            ),
            # Delete Recommendation nodes (now disconnected from non-patch edges)
            (
                "MATCH (rec:Recommendation {guideline_id: $gid}) "
                "WHERE NOT exists { (rec)-[r]-() WHERE r._source = 'patch' } "
                "DELETE rec",
                {"gid": guideline_id},
            ),
            # Delete orphaned EvidenceChunks
            (
                "MATCH (ec:EvidenceChunk) "
                "WHERE NOT exists { (rec:Recommendation)-[:SOURCED_FROM]->(ec) } "
                "DETACH DELETE ec",
                {},
            ),
            # Delete the Guideline node itself
            (
                "MATCH (g:Guideline {id: $gid}) DETACH DELETE g",
                {"gid": guideline_id},
            ),
        ]

    # -- Node creators ---------------------------------------------------------

    @staticmethod
    def create_guideline(guideline: Guideline) -> CypherStatement:
        return (
            "MERGE (g:Guideline {id: $id}) "
            "ON CREATE SET g.title = $title, g.doi = $doi, g.year = $year, "
            "g.organization = $org, g.version = $version",
            {
                "id": guideline.id,
                "title": guideline.title,
                "doi": guideline.doi,
                "year": guideline.year,
                "org": guideline.organization,
                "version": guideline.version,
            },
        )

    @staticmethod
    def create_drug(
        node_id: str,
        name: str,
        rxnorm_code: str | None = None,
        snomed_code: str | None = None,
        atc_code: str | None = None,
        aliases: list[str] | None = None,
    ) -> CypherStatement:
        return (
            "MERGE (d:Drug {id: $id}) "
            "ON CREATE SET d.name = $name, d.rxnorm_code = $rxnorm, "
            "d.snomed_code = $snomed, d.atc_code = $atc, d.aliases = $aliases",
            {
                "id": node_id,
                "name": name,
                "rxnorm": rxnorm_code,
                "snomed": snomed_code,
                "atc": atc_code,
                "aliases": aliases or [],
            },
        )

    @staticmethod
    def create_drug_class(
        node_id: str,
        name: str,
        atc_code: str | None = None,
        fda_epc: str | None = None,
        aliases: list[str] | None = None,
    ) -> CypherStatement:
        return (
            "MERGE (dc:DrugClass {id: $id}) "
            "ON CREATE SET dc.name = $name, dc.atc_code = $atc, "
            "dc.fda_epc = $fda_epc, dc.aliases = $aliases",
            {
                "id": node_id,
                "name": name,
                "atc": atc_code,
                "fda_epc": fda_epc,
                "aliases": aliases or [],
            },
        )

    @staticmethod
    def create_disease(
        node_id: str,
        name: str,
        snomed_code: str | None = None,
        icd10_code: str | None = None,
        aliases: list[str] | None = None,
    ) -> CypherStatement:
        return (
            "MERGE (dis:Disease {id: $id}) "
            "ON CREATE SET dis.name = $name, dis.snomed_code = $snomed, "
            "dis.icd10_code = $icd10, dis.aliases = $aliases",
            {
                "id": node_id,
                "name": name,
                "snomed": snomed_code,
                "icd10": icd10_code,
                "aliases": aliases or [],
            },
        )

    @staticmethod
    def create_symptom(
        node_id: str,
        name: str,
        snomed_code: str | None = None,
        aliases: list[str] | None = None,
    ) -> CypherStatement:
        return (
            "MERGE (s:Symptom {id: $id}) "
            "ON CREATE SET s.name = $name, s.snomed_code = $snomed, s.aliases = $aliases",
            {
                "id": node_id,
                "name": name,
                "snomed": snomed_code,
                "aliases": aliases or [],
            },
        )

    @staticmethod
    def create_lab(
        node_id: str,
        name: str,
        loinc_code: str | None = None,
        snomed_code: str | None = None,
        unit: str | None = None,
        reference_range: str | None = None,
    ) -> CypherStatement:
        return (
            "MERGE (l:Lab {id: $id}) "
            "ON CREATE SET l.name = $name, l.loinc_code = $loinc, "
            "l.snomed_code = $snomed, l.unit = $unit, l.reference_range = $ref_range",
            {
                "id": node_id,
                "name": name,
                "loinc": loinc_code,
                "snomed": snomed_code,
                "unit": unit,
                "ref_range": reference_range,
            },
        )

    @staticmethod
    def create_procedure(
        node_id: str,
        name: str,
        snomed_code: str | None = None,
        cpt_code: str | None = None,
        aliases: list[str] | None = None,
    ) -> CypherStatement:
        return (
            "MERGE (p:Procedure {id: $id}) "
            "ON CREATE SET p.name = $name, p.snomed_code = $snomed, "
            "p.cpt_code = $cpt, p.aliases = $aliases",
            {
                "id": node_id,
                "name": name,
                "snomed": snomed_code,
                "cpt": cpt_code,
                "aliases": aliases or [],
            },
        )

    @staticmethod
    def create_device(
        node_id: str,
        name: str,
        snomed_code: str | None = None,
        gmdn_code: str | None = None,
        aliases: list[str] | None = None,
    ) -> CypherStatement:
        return (
            "MERGE (dev:Device {id: $id}) "
            "ON CREATE SET dev.name = $name, dev.snomed_code = $snomed, "
            "dev.gmdn_code = $gmdn, dev.aliases = $aliases",
            {
                "id": node_id,
                "name": name,
                "snomed": snomed_code,
                "gmdn": gmdn_code,
                "aliases": aliases or [],
            },
        )

    @staticmethod
    def create_recommendation(rec: Recommendation) -> CypherStatement:
        return (
            "MERGE (rec:Recommendation {id: $id}) "
            "ON CREATE SET rec.type = $type, rec.action = $action, "
            "rec.action_detail = $detail, rec.strength = $strength, "
            "rec.evidence_quality = $eq, rec.conditions_json = $conds, "
            "rec.guideline_id = $gid, rec.section = $section, rec.page = $page",
            {
                "id": rec.id,
                "type": rec.type.value,
                "action": rec.action,
                "detail": rec.action_detail,
                "strength": rec.strength.value,
                "eq": rec.evidence_quality.value,
                "conds": rec.conditions_json,
                "gid": rec.guideline_id,
                "section": rec.section,
                "page": rec.page,
            },
        )

    @staticmethod
    def create_evidence_chunk(
        chunk_id: str,
        text: str,
        section: str | None = None,
        page_start: int | None = None,
        page_end: int | None = None,
    ) -> CypherStatement:
        return (
            "MERGE (ec:EvidenceChunk {id: $id}) "
            "ON CREATE SET ec.text = $text, ec.section = $section, "
            "ec.page_start = $page_start, ec.page_end = $page_end",
            {
                "id": chunk_id,
                "text": text,
                "section": section,
                "page_start": page_start,
                "page_end": page_end,
            },
        )

    @staticmethod
    def create_publication(
        doi: str,
        title: str | None = None,
        year: int | None = None,
        study_type: str | None = None,
    ) -> CypherStatement:
        return (
            "MERGE (pub:Publication {doi: $doi}) "
            "ON CREATE SET pub.title = $title, pub.year = $year, "
            "pub.study_type = $study_type",
            {"doi": doi, "title": title, "year": year, "study_type": study_type},
        )

    @staticmethod
    def create_patient_variable(
        var_id: str,
        name: str,
        loinc_code: str | None = None,
        unit: str | None = None,
        var_type: str = "continuous",
    ) -> CypherStatement:
        return (
            "MERGE (pv:PatientVariable {id: $id}) "
            "ON CREATE SET pv.name = $name, pv.loinc_code = $loinc, "
            "pv.unit = $unit, pv.var_type = $type",
            {
                "id": var_id,
                "name": name,
                "loinc": loinc_code,
                "unit": unit,
                "type": var_type,
            },
        )

    @staticmethod
    def create_population(
        pop_id: str,
        description: str,
        criteria_json: str | None = None,
    ) -> CypherStatement:
        return (
            "MERGE (pop:Population {id: $id}) "
            "ON CREATE SET pop.description = $desc, pop.criteria_json = $criteria",
            {"id": pop_id, "desc": description, "criteria": criteria_json},
        )

    @staticmethod
    def create_temporal_constraint(
        tc_id: str,
        tc_type: str,
        value: float | str | None = None,
        unit: str | None = None,
        reference_event: str | None = None,
        relation: str | None = None,
    ) -> CypherStatement:
        return (
            "MERGE (tc:TemporalConstraint {id: $id}) "
            "ON CREATE SET tc.type = $type, tc.value = $value, tc.unit = $unit, "
            "tc.reference_event = $ref_event, tc.relation = $relation",
            {
                "id": tc_id,
                "type": tc_type,
                "value": value,
                "unit": unit,
                "ref_event": reference_event,
                "relation": relation,
            },
        )

    @staticmethod
    def create_organization(
        org_id: str,
        name: str,
        abbreviation: str | None = None,
        country: str | None = None,
    ) -> CypherStatement:
        return (
            "MERGE (org:Organization {id: $id}) "
            "ON CREATE SET org.name = $name, org.abbreviation = $abbr, "
            "org.country = $country",
            {"id": org_id, "name": name, "abbr": abbreviation, "country": country},
        )

    # -- Semantic edge creators (Layer 1) --------------------------------------

    @staticmethod
    def create_indicated_for(
        source_id: str,
        source_label: str,
        target_id: str,
        props: IndicatedForProps,
    ) -> CypherStatement:
        """Create INDICATED_FOR edge: Drug/DrugClass/Procedure/Device → Disease."""
        return (
            f"MATCH (src:{source_label} {{id: $src_id}}), (tgt:Disease {{id: $tgt_id}}) "
            "MERGE (src)-[r:INDICATED_FOR]->(tgt) "
            "ON CREATE SET r.strength = $strength, r.evidence_quality = $eq, "
            "r.conditions_json = $conds",
            {
                "src_id": source_id,
                "tgt_id": target_id,
                "strength": props.strength.value,
                "eq": props.evidence_quality.value,
                "conds": props.conditions_json,
            },
        )

    @staticmethod
    def create_contraindicated_in(
        source_id: str,
        source_label: str,
        target_id: str,
        props: ContraindicatedInProps,
    ) -> CypherStatement:
        """Create CONTRAINDICATED_IN edge: Drug/DrugClass/Procedure/Device → Disease."""
        return (
            f"MATCH (src:{source_label} {{id: $src_id}}), (tgt:Disease {{id: $tgt_id}}) "
            "MERGE (src)-[r:CONTRAINDICATED_IN]->(tgt) "
            "ON CREATE SET r.strength = $strength, r.severity = $severity, "
            "r.evidence_quality = $eq, r.conditions_json = $conds",
            {
                "src_id": source_id,
                "tgt_id": target_id,
                "strength": props.strength.value,
                "severity": props.severity.value,
                "eq": props.evidence_quality.value if props.evidence_quality else None,
                "conds": props.conditions_json,
            },
        )

    @staticmethod
    def create_interacts_with(
        drug_a_id: str,
        drug_b_id: str,
        props: InteractsWithProps,
        source_label: str = "Drug",
        target_label: str = "Drug",
    ) -> CypherStatement:
        """Create INTERACTS_WITH edge: Drug/DrugClass → Drug/DrugClass."""
        return (
            f"MATCH (a:{source_label} {{id: $aid}}), (b:{target_label} {{id: $bid}}) "
            "MERGE (a)-[r:INTERACTS_WITH]->(b) "
            "ON CREATE SET r.severity = $severity, r.evidence_quality = $eq, "
            "r.mechanism = $mechanism, r.clinical_effect = $effect",
            {
                "aid": drug_a_id,
                "bid": drug_b_id,
                "severity": props.severity.value,
                "eq": props.evidence_quality.value if props.evidence_quality else None,
                "mechanism": props.mechanism,
                "effect": props.clinical_effect,
            },
        )

    @staticmethod
    def create_dosed_for(
        drug_id: str,
        disease_id: str,
        props: DosedForProps,
    ) -> CypherStatement:
        """Create DOSED_FOR edge: Drug → Disease."""
        return (
            "MATCH (d:Drug {id: $did}), (dis:Disease {id: $dis_id}) "
            "MERGE (d)-[r:DOSED_FOR]->(dis) "
            "ON CREATE SET r.starting_dose = $start, r.target_dose = $target, "
            "r.max_dose = $max, r.route = $route, r.frequency = $freq, "
            "r.titration_schedule = $titration, r.conditions_json = $conds",
            {
                "did": drug_id,
                "dis_id": disease_id,
                "start": props.starting_dose,
                "target": props.target_dose,
                "max": props.max_dose,
                "route": props.route,
                "freq": props.frequency,
                "titration": props.titration_schedule,
                "conds": props.conditions_json,
            },
        )

    @staticmethod
    def create_monitored_by(
        drug_id: str,
        lab_id: str,
        props: MonitoredByProps,
    ) -> CypherStatement:
        """Create MONITORED_BY edge: Drug → Lab."""
        return (
            "MATCH (d:Drug {id: $did}), (l:Lab {id: $lid}) "
            "MERGE (d)-[r:MONITORED_BY]->(l) "
            "ON CREATE SET r.frequency = $freq, r.threshold_alert = $alert, "
            "r.threshold_stop = $stop, r.conditions_json = $conds",
            {
                "did": drug_id,
                "lid": lab_id,
                "freq": props.frequency,
                "alert": props.threshold_alert,
                "stop": props.threshold_stop,
                "conds": props.conditions_json,
            },
        )

    @staticmethod
    def create_member_of(drug_id: str, drug_class_id: str) -> CypherStatement:
        """Create MEMBER_OF edge: Drug → DrugClass."""
        return (
            "MATCH (d:Drug {id: $did}), (dc:DrugClass {id: $dcid}) "
            "MERGE (d)-[:MEMBER_OF]->(dc)",
            {"did": drug_id, "dcid": drug_class_id},
        )

    @staticmethod
    def create_presents_with(
        disease_id: str,
        symptom_id: str,
        frequency: str = "common",
    ) -> CypherStatement:
        """Create PRESENTS_WITH edge: Disease → Symptom."""
        return (
            "MATCH (dis:Disease {id: $dis_id}), (s:Symptom {id: $sid}) "
            "MERGE (dis)-[r:PRESENTS_WITH]->(s) "
            "ON CREATE SET r.frequency = $freq",
            {"dis_id": disease_id, "sid": symptom_id, "freq": frequency},
        )

    @staticmethod
    def create_diagnosed_by(
        disease_id: str,
        target_id: str,
        target_label: str,
    ) -> CypherStatement:
        """Create DIAGNOSED_BY edge: Disease → Procedure/Lab."""
        return (
            f"MATCH (dis:Disease {{id: $dis_id}}), (tgt:{target_label} {{id: $tgt_id}}) "
            "MERGE (dis)-[:DIAGNOSED_BY]->(tgt)",
            {"dis_id": disease_id, "tgt_id": target_id},
        )

    @staticmethod
    def create_stage_of(
        child_disease_id: str,
        parent_disease_id: str,
        stage_system: str | None = None,
        stage_value: str | None = None,
    ) -> CypherStatement:
        """Create STAGE_OF edge: Disease → Disease."""
        return (
            "MATCH (child:Disease {id: $child_id}), (parent:Disease {id: $parent_id}) "
            "MERGE (child)-[r:STAGE_OF]->(parent) "
            "ON CREATE SET r.stage_system = $system, r.stage_value = $value",
            {
                "child_id": child_disease_id,
                "parent_id": parent_disease_id,
                "system": stage_system,
                "value": stage_value,
            },
        )

    # -- Evidence edge creators (Layer 2) --------------------------------------

    @staticmethod
    def create_recommends(
        rec_id: str,
        target_id: str,
        target_label: str,
        role: str | None = None,
    ) -> CypherStatement:
        """Create RECOMMENDS edge: Recommendation → clinical entity."""
        return (
            f"MATCH (rec:Recommendation {{id: $rec_id}}), (tgt:{target_label} {{id: $tgt_id}}) "
            "MERGE (rec)-[r:RECOMMENDS]->(tgt) "
            "ON CREATE SET r.role = $role",
            {"rec_id": rec_id, "tgt_id": target_id, "role": role},
        )

    @staticmethod
    def create_for_condition(rec_id: str, disease_id: str) -> CypherStatement:
        """Create FOR_CONDITION edge: Recommendation → Disease."""
        return (
            "MATCH (rec:Recommendation {id: $rec_id}), (dis:Disease {id: $dis_id}) "
            "MERGE (rec)-[:FOR_CONDITION]->(dis)",
            {"rec_id": rec_id, "dis_id": disease_id},
        )

    @staticmethod
    def create_sourced_from(rec_id: str, chunk_id: str) -> CypherStatement:
        """Create SOURCED_FROM edge: Recommendation → EvidenceChunk."""
        return (
            "MATCH (rec:Recommendation {id: $rec_id}), (ec:EvidenceChunk {id: $cid}) "
            "MERGE (rec)-[:SOURCED_FROM]->(ec)",
            {"rec_id": rec_id, "cid": chunk_id},
        )

    @staticmethod
    def create_defined_by(rec_id: str, guideline_id: str) -> CypherStatement:
        """Create DEFINED_BY edge: Recommendation → Guideline."""
        return (
            "MATCH (rec:Recommendation {id: $rec_id}), (g:Guideline {id: $gid}) "
            "MERGE (rec)-[:DEFINED_BY]->(g)",
            {"rec_id": rec_id, "gid": guideline_id},
        )

    @staticmethod
    def create_evaluates(rec_id: str, variable_id: str) -> CypherStatement:
        """Create EVALUATES edge: Recommendation → PatientVariable."""
        return (
            "MATCH (rec:Recommendation {id: $rec_id}), (pv:PatientVariable {id: $vid}) "
            "MERGE (rec)-[:EVALUATES]->(pv)",
            {"rec_id": rec_id, "vid": variable_id},
        )

    @staticmethod
    def create_applies_to(rec_id: str, population_id: str) -> CypherStatement:
        """Create APPLIES_TO edge: Recommendation → Population."""
        return (
            "MATCH (rec:Recommendation {id: $rec_id}), (pop:Population {id: $pop_id}) "
            "MERGE (rec)-[:APPLIES_TO]->(pop)",
            {"rec_id": rec_id, "pop_id": population_id},
        )

    @staticmethod
    def create_timed_by(rec_id: str, tc_id: str) -> CypherStatement:
        """Create TIMED_BY edge: Recommendation → TemporalConstraint."""
        return (
            "MATCH (rec:Recommendation {id: $rec_id}), (tc:TemporalConstraint {id: $tc_id}) "
            "MERGE (rec)-[:TIMED_BY]->(tc)",
            {"rec_id": rec_id, "tc_id": tc_id},
        )

    @staticmethod
    def create_published_by(guideline_id: str, org_id: str) -> CypherStatement:
        """Create PUBLISHED_BY edge: Guideline → Organization."""
        return (
            "MATCH (g:Guideline {id: $gid}), (org:Organization {id: $oid}) "
            "MERGE (g)-[:PUBLISHED_BY]->(org)",
            {"gid": guideline_id, "oid": org_id},
        )

    @staticmethod
    def create_cited_in(pub_doi: str, rec_id: str) -> CypherStatement:
        """Create CITED_IN edge: Publication → Recommendation."""
        return (
            "MATCH (pub:Publication {doi: $doi}), (rec:Recommendation {id: $rec_id}) "
            "MERGE (pub)-[:CITED_IN]->(rec)",
            {"doi": pub_doi, "rec_id": rec_id},
        )

    @staticmethod
    def create_measures(variable_id: str, lab_id: str) -> CypherStatement:
        """Create MEASURES edge: PatientVariable → Lab."""
        return (
            "MATCH (pv:PatientVariable {id: $vid}), (l:Lab {id: $lid}) "
            "MERGE (pv)-[:MEASURES]->(l)",
            {"vid": variable_id, "lid": lab_id},
        )

    # -- Cross-guideline edges -------------------------------------------------

    @staticmethod
    def create_conflicts_with(
        rec_a_id: str,
        rec_b_id: str,
        resolution: str | None = None,
        resolution_detail: str | None = None,
    ) -> CypherStatement:
        """Create CONFLICTS_WITH edge: Recommendation → Recommendation."""
        return (
            "MATCH (a:Recommendation {id: $aid}), (b:Recommendation {id: $bid}) "
            "MERGE (a)-[r:CONFLICTS_WITH]->(b) "
            "ON CREATE SET r.resolution = $resolution, "
            "r.resolution_detail = $detail",
            {
                "aid": rec_a_id,
                "bid": rec_b_id,
                "resolution": resolution,
                "detail": resolution_detail,
            },
        )

    @staticmethod
    def create_supersedes(
        newer_rec_id: str, older_rec_id: str, reason: str | None = None
    ) -> CypherStatement:
        """Create SUPERSEDES edge: Recommendation → Recommendation."""
        return (
            "MATCH (newer:Recommendation {id: $nid}), (older:Recommendation {id: $oid}) "
            "MERGE (newer)-[r:SUPERSEDES]->(older) "
            "ON CREATE SET r.reason = $reason",
            {"nid": newer_rec_id, "oid": older_rec_id, "reason": reason},
        )

    # -- Embedding -------------------------------------------------------------

    @staticmethod
    def set_embedding(chunk_id: str, embedding: list[float]) -> CypherStatement:
        return (
            "MATCH (ec:EvidenceChunk {id: $id}) SET ec.embedding = $embedding",
            {"id": chunk_id, "embedding": embedding},
        )


# ---------------------------------------------------------------------------
# Reasoning Queries (query-time)
# ---------------------------------------------------------------------------


class ReasoningQueries:
    """Cypher builders for dual-layer clinical queries."""

    # -- Layer 1: Semantic Knowledge Graph (one-hop clinical queries) ----------

    @staticmethod
    def find_treatments(
        disease_id: str,
        guideline_filter: str | None = None,
    ) -> CypherStatement:
        """What treats disease X? One-hop via INDICATED_FOR."""
        cypher = (
            "MATCH (src)-[r:INDICATED_FOR]->(dis:Disease {id: $dis_id}) "
            "WHERE src:Drug OR src:DrugClass OR src:Procedure OR src:Device "
        )
        params: dict = {"dis_id": disease_id}
        if guideline_filter:
            cypher += (
                "MATCH (rec:Recommendation)-[:RECOMMENDS]->(src) "
                "WHERE rec.guideline_id = $gfilter "
            )
            params["gfilter"] = guideline_filter
        cypher += (
            "RETURN labels(src)[0] AS entity_type, src.id AS entity_id, "
            "src.name AS entity_name, r.strength AS strength, "
            "r.evidence_quality AS evidence_quality, "
            "r.conditions_json AS conditions"
        )
        return (cypher, params)

    @staticmethod
    def find_indications_for_drug(
        entity_id: str,
        entity_label: str = "Drug",
        guideline_filter: str | None = None,
    ) -> CypherStatement:
        """What diseases is drug/drug_class X indicated for? Reverse of find_treatments."""
        cypher = (
            f"MATCH (src:{entity_label} {{id: $eid}})-[r:INDICATED_FOR]->(dis:Disease) "
        )
        params: dict = {"eid": entity_id}
        if guideline_filter:
            cypher += (
                "MATCH (rec:Recommendation)-[:RECOMMENDS]->(src) "
                "WHERE rec.guideline_id = $gfilter "
            )
            params["gfilter"] = guideline_filter
        cypher += (
            "RETURN 'Disease' AS entity_type, dis.id AS entity_id, "
            "dis.name AS entity_name, r.strength AS strength, "
            "r.evidence_quality AS evidence_quality, "
            "r.conditions_json AS conditions"
        )
        return (cypher, params)

    @staticmethod
    def find_contraindications(
        entity_id: str,
        entity_label: str,
    ) -> CypherStatement:
        """What is entity X contraindicated in?"""
        return (
            f"MATCH (src:{entity_label} {{id: $eid}})-[r:CONTRAINDICATED_IN]->(dis:Disease) "
            "RETURN dis.id AS disease_id, dis.name AS disease_name, "
            "r.strength AS strength, r.severity AS severity, "
            "r.evidence_quality AS evidence_quality, "
            "r.conditions_json AS conditions",
            {"eid": entity_id},
        )

    @staticmethod
    def find_interactions(
        entity_id: str, entity_label: str = "Drug"
    ) -> CypherStatement:
        """What interacts with drug/drug class X?"""
        return (
            f"MATCH (d:{entity_label} {{id: $did}})-[r:INTERACTS_WITH]-(other) "
            "WHERE other:Drug OR other:DrugClass "
            "RETURN other.id AS entity_id, other.name AS entity_name, "
            "labels(other)[0] AS entity_type, "
            "r.severity AS severity, r.evidence_quality AS evidence_quality, "
            "r.mechanism AS mechanism, "
            "r.clinical_effect AS clinical_effect",
            {"did": entity_id},
        )

    @staticmethod
    def find_diagnostic_criteria(disease_id: str) -> CypherStatement:
        """What diagnostic criteria (labs/procedures) are used for disease X?"""
        return (
            "MATCH (dis:Disease {id: $did})-[:DIAGNOSED_BY]->(tgt) "
            "WHERE tgt:Lab OR tgt:Procedure "
            "RETURN labels(tgt)[0] AS entity_type, tgt.id AS entity_id, "
            "tgt.name AS entity_name",
            {"did": disease_id},
        )

    @staticmethod
    def find_dosing(drug_id: str, disease_id: str | None = None) -> CypherStatement:
        """Get dosing info for drug X (optionally for disease Y)."""
        if disease_id:
            return (
                "MATCH (d:Drug {id: $did})-[r:DOSED_FOR]->(dis:Disease {id: $dis_id}) "
                "RETURN dis.name AS disease, r.starting_dose AS starting_dose, "
                "r.target_dose AS target_dose, r.max_dose AS max_dose, "
                "r.route AS route, r.frequency AS frequency, "
                "r.titration_schedule AS titration, r.conditions_json AS conditions",
                {"did": drug_id, "dis_id": disease_id},
            )
        return (
            "MATCH (d:Drug {id: $did})-[r:DOSED_FOR]->(dis:Disease) "
            "RETURN dis.id AS disease_id, dis.name AS disease, "
            "r.starting_dose AS starting_dose, r.target_dose AS target_dose, "
            "r.max_dose AS max_dose, r.route AS route, r.frequency AS frequency, "
            "r.titration_schedule AS titration, r.conditions_json AS conditions",
            {"did": drug_id},
        )

    @staticmethod
    def find_monitoring(
        entity_id: str, entity_label: str = "Drug"
    ) -> CypherStatement:
        """What labs should be monitored for entity X?"""
        return (
            f"MATCH (d:{entity_label} {{id: $eid}})-[r:MONITORED_BY]->(l:Lab) "
            "RETURN l.id AS lab_id, l.name AS lab_name, "
            "r.frequency AS frequency, r.threshold_alert AS threshold_alert, "
            "r.threshold_stop AS threshold_stop",
            {"eid": entity_id},
        )

    @staticmethod
    def find_drug_class_members(drug_class_id: str) -> CypherStatement:
        """Get all drugs in a drug class."""
        return (
            "MATCH (d:Drug)-[:MEMBER_OF]->(dc:DrugClass {id: $dcid}) "
            "RETURN d.id AS drug_id, d.name AS drug_name",
            {"dcid": drug_class_id},
        )

    @staticmethod
    def find_drug_class(drug_id: str) -> CypherStatement:
        """What class does drug X belong to?"""
        return (
            "MATCH (d:Drug {id: $did})-[:MEMBER_OF]->(dc:DrugClass) "
            "RETURN dc.id AS class_id, dc.name AS class_name",
            {"did": drug_id},
        )

    # -- Layer 2: Evidence/Recommendation Layer (provenance trail) -------------

    @staticmethod
    def get_recommendation_detail(rec_id: str) -> CypherStatement:
        """Full provenance for a recommendation."""
        return (
            "MATCH (rec:Recommendation {id: $rec_id}) "
            "OPTIONAL MATCH (rec)-[:SOURCED_FROM]->(ec:EvidenceChunk) "
            "OPTIONAL MATCH (rec)-[:DEFINED_BY]->(g:Guideline) "
            "OPTIONAL MATCH (rec)-[:EVALUATES]->(pv:PatientVariable) "
            "OPTIONAL MATCH (rec)-[:TIMED_BY]->(tc:TemporalConstraint) "
            "OPTIONAL MATCH (rec)-[:APPLIES_TO]->(pop:Population) "
            "RETURN rec, collect(DISTINCT ec) AS evidence, "
            "g, collect(DISTINCT pv) AS variables, "
            "collect(DISTINCT tc) AS temporal, "
            "collect(DISTINCT pop) AS populations",
            {"rec_id": rec_id},
        )

    @staticmethod
    def find_recommendations_for_entity(
        entity_id: str,
        entity_label: str,
        rec_type: str | None = None,
    ) -> CypherStatement:
        """All recommendations that reference a specific entity."""
        cypher = (
            f"MATCH (rec:Recommendation)-[:RECOMMENDS]->(tgt:{entity_label} {{id: $eid}}) "
            "OPTIONAL MATCH (rec)-[:SOURCED_FROM]->(ec:EvidenceChunk) "
            "OPTIONAL MATCH (rec)-[:DEFINED_BY]->(g:Guideline) "
        )
        params: dict = {"eid": entity_id}
        if rec_type:
            cypher += "WHERE rec.type = $rtype "
            params["rtype"] = rec_type
        cypher += (
            "RETURN rec.id AS rec_id, rec.type AS rec_type, "
            "rec.action AS action, rec.action_detail AS detail, "
            "rec.strength AS strength, rec.evidence_quality AS evidence_quality, "
            "rec.conditions_json AS conditions_json, "
            "ec.id AS chunk_id, ec.text AS source_text, ec.section AS section, "
            "g.title AS guideline, g.doi AS doi, g.year AS year "
            "ORDER BY g.year DESC"
        )
        return (cypher, params)

    @staticmethod
    def get_full_recommendation_chain(
        entity_id: str,
        entity_label: str,
        disease_id: str,
    ) -> CypherStatement:
        """Full evidence chain: entity + disease → recommendations → evidence."""
        return (
            f"MATCH (rec:Recommendation)-[:RECOMMENDS]->(tgt:{entity_label} {{id: $eid}}) "
            "MATCH (rec)-[:FOR_CONDITION]->(dis:Disease {id: $dis_id}) "
            "MATCH (rec)-[:SOURCED_FROM]->(ec:EvidenceChunk) "
            "MATCH (rec)-[:DEFINED_BY]->(g:Guideline) "
            "OPTIONAL MATCH (rec)-[:EVALUATES]->(pv:PatientVariable) "
            "OPTIONAL MATCH (rec)-[:TIMED_BY]->(tc:TemporalConstraint) "
            "RETURN rec.id AS rec_id, rec.type AS rec_type, "
            "rec.action AS action, rec.strength AS strength, "
            "rec.evidence_quality AS evidence_quality, "
            "rec.conditions_json AS conditions, "
            "ec.text AS source_text, g.doi AS doi, "
            "collect(DISTINCT pv.name) AS variables, "
            "collect(DISTINCT {type: tc.type, value: tc.value, unit: tc.unit}) AS temporal "
            "ORDER BY g.year DESC",
            {"eid": entity_id, "dis_id": disease_id},
        )

    # -- Vector search ---------------------------------------------------------

    @staticmethod
    def vector_search(
        query_embedding: list[float], limit: int = 10
    ) -> CypherStatement:
        """Semantic search on EvidenceChunk embeddings."""
        return (
            "CALL db.index.vector.queryNodes('evidence_embedding', $limit, $embedding) "
            "YIELD node, score "
            "OPTIONAL MATCH (rec:Recommendation)-[:SOURCED_FROM]->(node) "
            "OPTIONAL MATCH (rec)-[:DEFINED_BY]->(g:Guideline) "
            "RETURN node.id AS ec_id, node.text AS ec_text, "
            "node.section AS ec_section, score, "
            "g.title AS g_title, g.doi AS g_doi, "
            "collect(DISTINCT {id: rec.id, type: rec.type, action: rec.action}) AS recommendations "
            "ORDER BY score DESC",
            {"embedding": query_embedding, "limit": limit},
        )

    # -- Dosing enrichment -----------------------------------------------------

    @staticmethod
    def find_dosing_summary_for_entities(
        entity_ids: list[str],
    ) -> CypherStatement:
        """Fetch basic dosing properties for a list of drug/drug_class entities.

        Used to enrich treatment recommendations with dosing context.
        Returns one row per entity with the best available dosing info.
        """
        return (
            "UNWIND $ids AS eid "
            "MATCH (src {id: eid})-[r:DOSED_FOR]->(dis) "
            "RETURN src.id AS entity_id, "
            "r.starting_dose AS starting_dose, "
            "r.target_dose AS target_dose, "
            "r.max_dose AS max_dose, "
            "r.frequency AS frequency "
            "ORDER BY entity_id "
            "LIMIT 50",
            {"ids": entity_ids},
        )

    # -- Disease hierarchy traversal -------------------------------------------

    @staticmethod
    def find_disease_parents(disease_id: str) -> CypherStatement:
        """Find parent diseases via STAGE_OF."""
        return (
            "MATCH (child:Disease {id: $did})-[:STAGE_OF]->(parent:Disease) "
            "RETURN parent.id AS parent_id, parent.name AS parent_name",
            {"did": disease_id},
        )

    @staticmethod
    def find_disease_children(disease_id: str) -> CypherStatement:
        """Find child diseases (stages/subtypes) via STAGE_OF."""
        return (
            "MATCH (child:Disease)-[:STAGE_OF]->(parent:Disease {id: $did}) "
            "RETURN child.id AS child_id, child.name AS child_name",
            {"did": disease_id},
        )

    # -- Vector → entity traversal ---------------------------------------------

    @staticmethod
    def vector_entity_search(
        query_embedding: list[float],
        rec_type: str | None = None,
        limit: int = 10,
    ) -> CypherStatement:
        """Vector search → traverse to connected clinical entities.

        Finds EvidenceChunks by embedding similarity, then follows
        SOURCED_FROM and RECOMMENDS edges to return the entities
        (drugs, diseases, etc.) with their recommendation metadata.
        """
        cypher = (
            "CALL db.index.vector.queryNodes('evidence_embedding', $limit, $embedding) "
            "YIELD node, score "
            "MATCH (rec:Recommendation)-[:SOURCED_FROM]->(node) "
            "MATCH (rec)-[:RECOMMENDS]->(entity) "
        )
        params: dict = {"embedding": query_embedding, "limit": limit}

        if rec_type:
            cypher += "WHERE rec.type = $rec_type "
            params["rec_type"] = rec_type

        cypher += (
            "RETURN DISTINCT labels(entity)[0] AS entity_type, "
            "entity.id AS entity_id, entity.name AS entity_name, "
            "rec.strength AS strength, rec.evidence_quality AS evidence_quality, "
            "rec.conditions_json AS conditions, score "
            "ORDER BY score DESC"
        )
        return (cypher, params)

    # -- Conflict detection ----------------------------------------------------

    @staticmethod
    def find_conflicts(rec_ids: list[str]) -> CypherStatement:
        """Find CONFLICTS_WITH edges among given recommendations."""
        return (
            "MATCH (a:Recommendation)-[r:CONFLICTS_WITH]->(b:Recommendation) "
            "WHERE a.id IN $ids AND b.id IN $ids "
            "RETURN a.id AS winner_id, b.id AS loser_id, "
            "r.resolution AS resolution, r.resolution_detail AS detail",
            {"ids": rec_ids},
        )

    # -- Evidence retrieval ----------------------------------------------------

    @staticmethod
    def get_evidence_chunk(chunk_id: str) -> CypherStatement:
        """Retrieve exact source text for a chunk."""
        return (
            "MATCH (ec:EvidenceChunk {id: $id}) "
            "OPTIONAL MATCH (rec:Recommendation)-[:SOURCED_FROM]->(ec) "
            "OPTIONAL MATCH (rec)-[:DEFINED_BY]->(g:Guideline) "
            "RETURN ec.text AS text, ec.section AS section, "
            "g.title AS guideline, g.doi AS doi",
            {"id": chunk_id},
        )

    # -- Listings --------------------------------------------------------------

    @staticmethod
    def list_guidelines() -> CypherStatement:
        return (
            "MATCH (g:Guideline) "
            "RETURN g.id AS id, g.title AS title, g.doi AS doi, g.year AS year",
            {},
        )

    @staticmethod
    def list_drugs() -> CypherStatement:
        return (
            "MATCH (d:Drug) RETURN d.id AS id, d.name AS name, "
            "d.rxnorm_code AS rxnorm ORDER BY d.name",
            {},
        )

    @staticmethod
    def list_diseases() -> CypherStatement:
        return (
            "MATCH (dis:Disease) RETURN dis.id AS id, dis.name AS name, "
            "dis.snomed_code AS snomed ORDER BY dis.name",
            {},
        )

    @staticmethod
    def list_drug_classes() -> CypherStatement:
        return (
            "MATCH (dc:DrugClass) "
            "OPTIONAL MATCH (d:Drug)-[:MEMBER_OF]->(dc) "
            "RETURN dc.id AS id, dc.name AS name, dc.atc_code AS atc, "
            "collect(d.name) AS members ORDER BY dc.name",
            {},
        )


# ---------------------------------------------------------------------------
# Patch Queries (incremental updates)
# ---------------------------------------------------------------------------


class PatchQueries:
    """Cypher builders for incremental graph updates (patch operations)."""

    # Valid node labels for patch operations
    VALID_LABELS = frozenset({
        "Drug", "DrugClass", "Disease", "Symptom", "Lab",
        "Procedure", "Device", "Guideline", "Recommendation",
        "EvidenceChunk", "PatientVariable", "Publication",
        "Population", "TemporalConstraint", "Organization",
    })

    # Valid semantic edge types
    VALID_EDGE_TYPES = frozenset({
        "INDICATED_FOR", "CONTRAINDICATED_IN", "DOSED_FOR",
        "MONITORED_BY", "INTERACTS_WITH", "DIAGNOSED_BY",
        "MEMBER_OF", "STAGE_OF", "PRESENTS_WITH",
        "RECOMMENDS", "FOR_CONDITION", "SOURCED_FROM",
        "DEFINED_BY", "EVALUATES", "APPLIES_TO", "TIMED_BY",
        "PUBLISHED_BY", "CITED_IN", "MEASURES",
        "CONFLICTS_WITH", "SUPERSEDES",
    })

    @staticmethod
    def check_node_exists(node_id: str) -> CypherStatement:
        """Check if a node with the given ID exists."""
        return (
            "MATCH (n {id: $id}) RETURN n.id AS id, labels(n)[0] AS label",
            {"id": node_id},
        )

    @staticmethod
    def add_edge(
        source_id: str,
        source_label: str,
        target_id: str,
        target_label: str,
        edge_type: str,
        props: dict,
    ) -> CypherStatement:
        """Create or merge an edge between two existing nodes.

        Adds _source='patch' and _patch_date for tracking.
        """
        return (
            f"MATCH (a:{source_label} {{id: $sid}}), (b:{target_label} {{id: $tid}}) "
            f"MERGE (a)-[r:{edge_type}]->(b) "
            "SET r += $props, r._source = 'patch'",
            {"sid": source_id, "tid": target_id, "props": props},
        )

    @staticmethod
    def add_node(
        label: str,
        node_id: str,
        name: str,
        props: dict,
    ) -> CypherStatement:
        """Create a new node with the given label, ID, name, and properties."""
        return (
            f"MERGE (n:{label} {{id: $id}}) "
            "ON CREATE SET n.name = $name, n += $props, n._source = 'patch'",
            {"id": node_id, "name": name, "props": props},
        )

    @staticmethod
    def patch_node(
        node_id: str,
        label: str,
        props: dict,
    ) -> CypherStatement:
        """Update properties on an existing node (non-destructive merge)."""
        return (
            f"MATCH (n:{label} {{id: $id}}) SET n += $props",
            {"id": node_id, "props": props},
        )

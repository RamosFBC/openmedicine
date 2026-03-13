from __future__ import annotations

from open_medicine.graphrag.graph.schema import Guideline


class LoaderQueries:
    """Cypher builders for ingestion."""

    @staticmethod
    def delete_guideline(guideline_id: str) -> list[tuple[str, dict]]:
        return [
            ("MATCH (n) WHERE n.guideline_id = $gid DETACH DELETE n", {"gid": guideline_id}),
            ("MATCH (g:Guideline {id: $gid}) DETACH DELETE g", {"gid": guideline_id}),
        ]

    @staticmethod
    def create_guideline(guideline: Guideline) -> tuple[str, dict]:
        return (
            "CREATE (g:Guideline {id: $id, title: $title, doi: $doi, year: $year, "
            "organization: $org, total_pages: $pages})",
            {
                "id": guideline.id, "title": guideline.title,
                "doi": guideline.doi, "year": guideline.year,
                "org": guideline.organization, "pages": guideline.total_pages,
            },
        )

    @staticmethod
    def create_evidence_chunk(chunk_id: str, text: str, guideline_id: str, section: str) -> tuple[str, dict]:
        return (
            "CREATE (ec:EvidenceChunk {id: $id, text: $text, guideline_id: $gid, section: $section})",
            {"id": chunk_id, "text": text, "gid": guideline_id, "section": section},
        )

    @staticmethod
    def create_logic_node(
        node_id: str, node_type: str, conditions_json: str,
        action: str, action_detail: str, strength: str,
        guideline_id: str, page: int,
    ) -> tuple[str, dict]:
        return (
            "CREATE (ln:LogicNode {id: $id, type: $type, conditions: $conds, action: $action, "
            "action_detail: $detail, strength: $strength, guideline_id: $gid, page: $page})",
            {
                "id": node_id, "type": node_type, "conds": conditions_json,
                "action": action, "detail": action_detail,
                "strength": strength, "gid": guideline_id, "page": page,
            },
        )

    @staticmethod
    def create_concept(
        concept_id: str, name: str, concept_type: str,
        snomed_code: str | None, loinc_code: str | None,
    ) -> tuple[str, dict]:
        return (
            "MERGE (c:Concept {id: $id}) "
            "ON CREATE SET c.name = $name, c.type = $type, c.snomed_code = $snomed, c.loinc_code = $loinc",
            {"id": concept_id, "name": name, "type": concept_type, "snomed": snomed_code, "loinc": loinc_code},
        )

    @staticmethod
    def create_patient_variable(
        var_id: str, name: str, unit: str,
        loinc_code: str | None, var_type: str,
    ) -> tuple[str, dict]:
        return (
            "MERGE (pv:PatientVariable {id: $id}) "
            "ON CREATE SET pv.name = $name, pv.unit = $unit, pv.loinc_code = $loinc, pv.type = $type",
            {"id": var_id, "name": name, "unit": unit, "loinc": loinc_code, "type": var_type},
        )

    @staticmethod
    def create_belongs_to(chunk_id: str, guideline_id: str) -> tuple[str, dict]:
        return (
            "MATCH (ec:EvidenceChunk {id: $cid}), (g:Guideline {id: $gid}) "
            "CREATE (ec)-[:BELONGS_TO]->(g)",
            {"cid": chunk_id, "gid": guideline_id},
        )

    @staticmethod
    def create_child_of(child_id: str, parent_id: str) -> tuple[str, dict]:
        return (
            "MATCH (child:EvidenceChunk {id: $cid}), (parent:EvidenceChunk {id: $pid}) "
            "CREATE (child)-[:CHILD_OF]->(parent)",
            {"cid": child_id, "pid": parent_id},
        )

    @staticmethod
    def create_defined_by(logic_node_id: str, guideline_id: str) -> tuple[str, dict]:
        return (
            "MATCH (ln:LogicNode {id: $lid}), (g:Guideline {id: $gid}) "
            "CREATE (ln)-[:DEFINED_BY]->(g)",
            {"lid": logic_node_id, "gid": guideline_id},
        )

    @staticmethod
    def create_sourced_from(logic_node_id: str, chunk_id: str) -> tuple[str, dict]:
        return (
            "MATCH (ln:LogicNode {id: $lid}), (ec:EvidenceChunk {id: $cid}) "
            "CREATE (ln)-[:SOURCED_FROM]->(ec)",
            {"lid": logic_node_id, "cid": chunk_id},
        )

    @staticmethod
    def create_evaluates(logic_node_id: str, variable_id: str) -> tuple[str, dict]:
        return (
            "MATCH (ln:LogicNode {id: $lid}), (pv:PatientVariable {id: $vid}) "
            "CREATE (ln)-[:EVALUATES]->(pv)",
            {"lid": logic_node_id, "vid": variable_id},
        )

    @staticmethod
    def create_participates_in(concept_id: str, logic_node_id: str, role: str) -> tuple[str, dict]:
        return (
            "MATCH (c:Concept {id: $cid}), (ln:LogicNode {id: $lid}) "
            "CREATE (c)-[:PARTICIPATES_IN {role: $role}]->(ln)",
            {"cid": concept_id, "lid": logic_node_id, "role": role},
        )

    @staticmethod
    def create_conflicts_with(ln_a_id: str, ln_b_id: str, resolution: str) -> tuple[str, dict]:
        return (
            "MATCH (a:LogicNode {id: $aid}), (b:LogicNode {id: $bid}) "
            "CREATE (a)-[:CONFLICTS_WITH {resolution: $resolution}]->(b)",
            {"aid": ln_a_id, "bid": ln_b_id, "resolution": resolution},
        )

    @staticmethod
    def create_interacts_with(concept_a_id: str, concept_b_id: str) -> tuple[str, dict]:
        return (
            "MATCH (a:Concept {id: $aid}), (b:Concept {id: $bid}) "
            "MERGE (a)-[:INTERACTS_WITH]->(b)",
            {"aid": concept_a_id, "bid": concept_b_id},
        )

    @staticmethod
    def set_embedding(chunk_id: str, embedding: list[float]) -> tuple[str, dict]:
        return (
            "MATCH (ec:EvidenceChunk {id: $id}) SET ec.embedding = $embedding",
            {"id": chunk_id, "embedding": embedding},
        )


class ReasoningQueries:
    """Cypher builders for query-time traversal."""

    @staticmethod
    def find_logic_nodes(
        intent: str, concept_ids: list[str],
        guideline_filter: str | None = None,
    ) -> tuple[str, dict]:
        cypher = (
            "MATCH (c:Concept)-[:PARTICIPATES_IN]->(ln:LogicNode {type: $intent})"
            "-[:SOURCED_FROM]->(ec:EvidenceChunk)-[:BELONGS_TO]->(g:Guideline) "
            "WHERE c.id IN $concepts "
        )
        params: dict = {"intent": intent, "concepts": concept_ids}
        if guideline_filter:
            cypher += "AND ln.guideline_id = $gfilter "
            params["gfilter"] = guideline_filter
        cypher += (
            "RETURN DISTINCT ln.id AS ln_id, ln.type AS ln_type, ln.action AS ln_action, "
            "ln.action_detail AS ln_detail, ln.strength AS ln_strength, "
            "ln.conditions AS ln_conditions, ln.page AS ln_page, "
            "ec.id AS ec_id, ec.text AS ec_text, ec.section AS ec_section, "
            "g.title AS g_title, g.doi AS g_doi, g.year AS g_year "
            "ORDER BY g.year DESC"
        )
        return (cypher, params)

    @staticmethod
    def vector_search(query_embedding: list[float], limit: int = 10) -> tuple[str, dict]:
        return (
            "CALL db.index.vector.queryNodes('evidence_embedding', $limit, $embedding) "
            "YIELD node, score "
            "MATCH (node)-[:BELONGS_TO]->(g:Guideline) "
            "RETURN node.id AS ec_id, node.text AS ec_text, node.section AS ec_section, "
            "score, g.title AS g_title, g.doi AS g_doi "
            "ORDER BY score DESC",
            {"embedding": query_embedding, "limit": limit},
        )

    @staticmethod
    def graph_enhanced_context(chunk_id: str) -> tuple[str, dict]:
        return (
            "MATCH (ec:EvidenceChunk {id: $id}) "
            "OPTIONAL MATCH (ec)-[:CHILD_OF]->(parent:EvidenceChunk) "
            "OPTIONAL MATCH (ln:LogicNode)-[:SOURCED_FROM]->(ec) "
            "RETURN ec.text AS text, parent.text AS parent_text, "
            "collect(DISTINCT {id: ln.id, type: ln.type, action: ln.action, detail: ln.action_detail}) AS related_nodes",
            {"id": chunk_id},
        )

    @staticmethod
    def get_evidence_chunk(chunk_id: str) -> tuple[str, dict]:
        return (
            "MATCH (ec:EvidenceChunk {id: $id})-[:BELONGS_TO]->(g:Guideline) "
            "RETURN ec.text AS text, ec.section AS section, g.title AS guideline, g.doi AS doi",
            {"id": chunk_id},
        )

    @staticmethod
    def list_guidelines() -> tuple[str, dict]:
        return (
            "MATCH (g:Guideline) RETURN g.id AS id, g.title AS title, g.doi AS doi, g.year AS year",
            {},
        )

    @staticmethod
    def find_conflicts(logic_node_ids: list[str]) -> tuple[str, dict]:
        return (
            "MATCH (a:LogicNode)-[r:CONFLICTS_WITH]->(b:LogicNode) "
            "WHERE a.id IN $ids AND b.id IN $ids "
            "RETURN a.id AS winner_id, b.id AS loser_id, r.resolution AS resolution",
            {"ids": logic_node_ids},
        )

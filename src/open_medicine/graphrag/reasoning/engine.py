from __future__ import annotations
import json
import operator
from typing import Any
from open_medicine.graphrag.graph.connection import GraphConnection
from open_medicine.graphrag.reasoning.types import (
    ClinicalQuery, GraphRAGResult, LogicNodeMatch, EvidenceCitation,
)

STRENGTH_RANK = {"Strong/A": 0, "Moderate/B": 1, "Weak/C": 2, "Expert_Opinion": 3}
OPS = {
    "<": operator.lt, "<=": operator.le,
    ">": operator.gt, ">=": operator.ge,
    "==": operator.eq, "!=": operator.ne,
}


class ReasoningEngine:
    def __init__(self, conn: GraphConnection) -> None:
        self._conn = conn

    def _evaluate_condition(self, cond: dict, patient_vars: dict[str, Any]) -> bool | None:
        var = cond["variable"]
        if var not in patient_vars:
            return None  # unknown
        op_fn = OPS.get(cond["operator"])
        if not op_fn:
            return None
        try:
            return op_fn(float(patient_vars[var]), float(cond["threshold"]))
        except (ValueError, TypeError):
            return op_fn(str(patient_vars[var]), str(cond["threshold"]))

    def query(self, q: ClinicalQuery) -> GraphRAGResult:
        concept_ids = [c.lower().replace(" ", "_") for c in q.concepts]

        cypher = (
            "MATCH (c:Concept)-[:PARTICIPATES_IN]->(ln:LogicNode {type: $intent})"
            "-[:SOURCED_FROM]->(ec:EvidenceChunk)-[:BELONGS_TO]->(g:Guideline) "
            "WHERE c.id IN $concepts "
        )
        if q.guideline_filter:
            cypher += "AND ln.guideline_id = $gfilter "

        cypher += (
            "RETURN ln.id AS ln_id, ln.type AS ln_type, ln.action AS ln_action, "
            "ln.action_detail AS ln_detail, ln.strength AS ln_strength, "
            "ln.conditions AS ln_conditions, ln.page AS ln_page, "
            "ec.id AS ec_id, ec.text AS ec_text, ec.section AS ec_section, "
            "g.title AS g_title, g.doi AS g_doi, g.year AS g_year "
            "ORDER BY g.year DESC"
        )

        params: dict[str, Any] = {"intent": q.intent, "concepts": concept_ids}
        if q.guideline_filter:
            params["gfilter"] = q.guideline_filter

        rows = self._conn.execute_read(cypher, params)

        matches: list[LogicNodeMatch] = []
        evidence: list[EvidenceCitation] = []
        all_missing: list[str] = []

        for row in rows:
            conditions = json.loads(row["ln_conditions"]) if isinstance(row["ln_conditions"], str) else row["ln_conditions"]
            missing_vars: list[str] = []
            all_met = True

            for cond in conditions:
                result = self._evaluate_condition(cond, q.patient_vars)
                if result is None:
                    missing_vars.append(cond["variable"])
                    all_met = False
                elif not result:
                    all_met = False

            conditions_met = all_met and len(missing_vars) == 0

            matches.append(LogicNodeMatch(
                logic_node_id=row["ln_id"],
                type=row["ln_type"],
                action=row["ln_action"],
                action_detail=row["ln_detail"],
                strength=row["ln_strength"],
                conditions_met=conditions_met,
                missing_variables=missing_vars,
            ))
            all_missing.extend(missing_vars)

            evidence.append(EvidenceCitation(
                chunk_id=row["ec_id"],
                text=row["ec_text"],
                guideline_title=row["g_title"],
                doi=row["g_doi"],
                section=row["ec_section"],
                page=row["ln_page"],
            ))

        # Sort: full matches first, then by strength, then by year (already ordered)
        matches.sort(key=lambda m: (
            not m.conditions_met,
            STRENGTH_RANK.get(m.strength, 99),
        ))

        # Determine confidence
        full_matches = [m for m in matches if m.conditions_met]
        if full_matches:
            confidence = "high"
        elif matches:
            confidence = "medium"
        else:
            confidence = "low"

        return GraphRAGResult(
            source="graph_traversal",
            matches=matches,
            synthesis=None,
            evidence=evidence,
            confidence=confidence,
            missing_variables=list(set(all_missing)),
        )

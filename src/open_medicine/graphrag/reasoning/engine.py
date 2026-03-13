from __future__ import annotations
import json
import operator
from typing import Any
from open_medicine.graphrag.graph.connection import GraphConnection
from open_medicine.graphrag.graph.queries import ReasoningQueries
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
            return None
        op_fn = OPS.get(cond["operator"])
        if not op_fn:
            return None
        try:
            return op_fn(float(patient_vars[var]), float(cond["threshold"]))
        except (ValueError, TypeError):
            return op_fn(str(patient_vars[var]), str(cond["threshold"]))

    def query(self, q: ClinicalQuery) -> GraphRAGResult:
        concept_ids = [c.lower().replace(" ", "_") for c in q.concepts]

        cypher, params = ReasoningQueries.find_logic_nodes(
            q.intent, concept_ids, q.guideline_filter,
        )
        rows = self._conn.execute_read(cypher, params)

        # Deduplicate by ln_id, collect evidence
        seen: dict[str, dict] = {}
        evidence_map: dict[str, list[EvidenceCitation]] = {}

        for row in rows:
            ln_id = row["ln_id"]
            citation = EvidenceCitation(
                chunk_id=row["ec_id"], text=row["ec_text"],
                guideline_title=row["g_title"], doi=row["g_doi"],
                section=row["ec_section"], page=row["ln_page"],
            )
            if ln_id not in seen:
                seen[ln_id] = row
                evidence_map[ln_id] = []
            evidence_map[ln_id].append(citation)

        # Build matches
        matches: list[LogicNodeMatch] = []
        all_evidence: list[EvidenceCitation] = []
        all_missing: list[str] = []

        for ln_id, row in seen.items():
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
                logic_node_id=ln_id,
                type=row["ln_type"],
                action=row["ln_action"],
                action_detail=row["ln_detail"],
                strength=row["ln_strength"],
                conditions_met=conditions_met,
                missing_variables=missing_vars,
            ))
            all_evidence.extend(evidence_map[ln_id])
            all_missing.extend(missing_vars)

        # Check for CONFLICTS_WITH among matched nodes
        if len(matches) >= 2:
            matched_ids = [m.logic_node_id for m in matches]
            conflict_cypher, conflict_params = ReasoningQueries.find_conflicts(matched_ids)
            conflict_rows = self._conn.execute_read(conflict_cypher, conflict_params)
            loser_ids = {r["loser_id"] for r in conflict_rows}
            for m in matches:
                if m.logic_node_id in loser_ids:
                    m.conditions_met = False
                    m.action_detail += " [superseded by newer/stronger guideline]"

        # Sort: full matches first, then by strength
        matches.sort(key=lambda m: (
            not m.conditions_met,
            STRENGTH_RANK.get(m.strength, 99),
        ))

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
            evidence=all_evidence,
            confidence=confidence,
            missing_variables=list(set(all_missing)),
        )

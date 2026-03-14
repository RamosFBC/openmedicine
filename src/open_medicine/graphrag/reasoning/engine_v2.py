"""GraphRAG Reasoning Engine v2 — Semantic edge traversal with dual-layer queries.

Supersedes engine.py. Uses typed semantic edges for one-hop clinical queries
(Layer 1) and falls back to recommendation traversal (Layer 2) for full
evidence chains.
"""

from __future__ import annotations

import json
import operator
from typing import TYPE_CHECKING, Any

from open_medicine.graphrag.graph.queries_v2 import ReasoningQueries
from open_medicine.graphrag.ingestion.linker_v2 import link_entity
from open_medicine.graphrag.reasoning.types_v2 import (
    ClinicalQuery,
    EvidenceCitation,
    GraphRAGResult,
    RecommendationMatch,
    SemanticMatch,
)

if TYPE_CHECKING:
    from open_medicine.graphrag.graph.connection import GraphConnection


# Strength ranking (lower = stronger)
STRENGTH_RANK = {
    "strong_for": 0,
    "moderate_for": 1,
    "weak_for": 2,
    "strong_against": 0,
    "no_benefit": 1,
}

# Comparison operators
OPS = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": operator.eq,
    "!=": operator.ne,
}

# Maps query intents to Layer 1 query methods
_INTENT_TO_QUERY = {
    "treatment_selection": "_query_treatments",
    "contraindication": "_query_contraindications",
    "interaction": "_query_interactions",
    "dosing": "_query_dosing",
    "monitoring": "_query_monitoring",
}


class ReasoningEngine:
    """Graph-based clinical reasoning using semantic edges."""

    def __init__(self, conn: GraphConnection) -> None:
        self._conn = conn

    def query(self, q: ClinicalQuery) -> GraphRAGResult:
        """Execute a clinical query using the dual-layer graph.

        1. Try Layer 1 semantic edge traversal (one-hop)
        2. If include_evidence, enrich with Layer 2 recommendation data
        3. Evaluate patient conditions
        4. Detect conflicts
        5. Return ranked results
        """
        # Route to intent-specific query
        method_name = _INTENT_TO_QUERY.get(q.intent)
        if method_name:
            handler = getattr(self, method_name)
            result = handler(q)
        else:
            # Fall back to generic recommendation search
            result = self._query_generic(q)

        return result

    # ----- Intent-specific queries (Layer 1) -----

    def _query_treatments(self, q: ClinicalQuery) -> GraphRAGResult:
        """Find treatments for a disease via INDICATED_FOR edges."""
        semantic_matches: list[SemanticMatch] = []
        all_evidence: list[EvidenceCitation] = []

        for concept in q.concepts:
            entity = link_entity(concept, "disease")
            if entity is None:
                continue

            cypher, params = ReasoningQueries.find_treatments(
                entity.node_id, q.guideline_filter
            )
            rows = self._conn.execute_read(cypher, params)

            for row in rows:
                match = SemanticMatch(
                    entity_id=row.get("entity_id", ""),
                    entity_name=row.get("entity_name", ""),
                    entity_type=row.get("entity_type", ""),
                    edge_type="INDICATED_FOR",
                    strength=row.get("strength", ""),
                    evidence_quality=row.get("evidence_quality", ""),
                    conditions_json=row.get("conditions"),
                )
                self._evaluate_match_conditions(match, q.patient_vars)
                semantic_matches.append(match)

        # Enrich with evidence if requested
        if q.include_evidence and semantic_matches:
            all_evidence = self._fetch_evidence_for_matches(semantic_matches, q)

        return self._build_result(semantic_matches, all_evidence, q)

    def _query_contraindications(self, q: ClinicalQuery) -> GraphRAGResult:
        """Find contraindications via CONTRAINDICATED_IN edges."""
        semantic_matches: list[SemanticMatch] = []

        for concept in q.concepts:
            # Try drug first, then drug_class
            for entity_type in ("drug", "drug_class"):
                entity = link_entity(concept, entity_type)
                if entity is None:
                    continue

                cypher, params = ReasoningQueries.find_contraindications(
                    entity.node_id, entity.node_label
                )
                rows = self._conn.execute_read(cypher, params)

                for row in rows:
                    match = SemanticMatch(
                        entity_id=row.get("disease_id", ""),
                        entity_name=row.get("disease_name", ""),
                        entity_type="Disease",
                        edge_type="CONTRAINDICATED_IN",
                        strength=row.get("strength", ""),
                        evidence_quality="",
                        conditions_json=row.get("conditions"),
                    )
                    self._evaluate_match_conditions(match, q.patient_vars)
                    semantic_matches.append(match)

                if rows:
                    break  # Found results, don't try other entity types

        all_evidence = (
            self._fetch_evidence_for_matches(semantic_matches, q)
            if q.include_evidence and semantic_matches
            else []
        )
        return self._build_result(semantic_matches, all_evidence, q)

    def _query_interactions(self, q: ClinicalQuery) -> GraphRAGResult:
        """Find drug interactions via INTERACTS_WITH edges."""
        semantic_matches: list[SemanticMatch] = []

        for concept in q.concepts:
            entity = link_entity(concept, "drug")
            if entity is None:
                continue

            cypher, params = ReasoningQueries.find_interactions(entity.node_id)
            rows = self._conn.execute_read(cypher, params)

            for row in rows:
                semantic_matches.append(
                    SemanticMatch(
                        entity_id=row.get("drug_id", ""),
                        entity_name=row.get("drug_name", ""),
                        entity_type="Drug",
                        edge_type="INTERACTS_WITH",
                        strength="",
                        evidence_quality="",
                    )
                )

        return self._build_result(semantic_matches, [], q)

    def _query_dosing(self, q: ClinicalQuery) -> GraphRAGResult:
        """Find dosing info via DOSED_FOR edges."""
        semantic_matches: list[SemanticMatch] = []

        # First concept is the drug, second (if present) is the disease
        drug_name = q.concepts[0] if q.concepts else None
        disease_name = q.concepts[1] if len(q.concepts) > 1 else None

        if not drug_name:
            return self._empty_result()

        entity = link_entity(drug_name, "drug")
        if entity is None:
            return self._empty_result()

        disease_id = None
        if disease_name:
            disease_entity = link_entity(disease_name, "disease")
            if disease_entity:
                disease_id = disease_entity.node_id

        cypher, params = ReasoningQueries.find_dosing(entity.node_id, disease_id)
        rows = self._conn.execute_read(cypher, params)

        for row in rows:
            match = SemanticMatch(
                entity_id=row.get("disease_id", entity.node_id),
                entity_name=row.get("disease", drug_name),
                entity_type="Disease",
                edge_type="DOSED_FOR",
                strength="",
                evidence_quality="",
                conditions_json=row.get("conditions"),
            )
            self._evaluate_match_conditions(match, q.patient_vars)
            semantic_matches.append(match)

        all_evidence = (
            self._fetch_evidence_for_matches(semantic_matches, q)
            if q.include_evidence and semantic_matches
            else []
        )
        return self._build_result(semantic_matches, all_evidence, q)

    def _query_monitoring(self, q: ClinicalQuery) -> GraphRAGResult:
        """Find monitoring requirements via MONITORED_BY edges."""
        semantic_matches: list[SemanticMatch] = []

        for concept in q.concepts:
            entity = link_entity(concept, "drug")
            if entity is None:
                continue

            cypher, params = ReasoningQueries.find_monitoring(entity.node_id)
            rows = self._conn.execute_read(cypher, params)

            for row in rows:
                semantic_matches.append(
                    SemanticMatch(
                        entity_id=row.get("lab_id", ""),
                        entity_name=row.get("lab_name", ""),
                        entity_type="Lab",
                        edge_type="MONITORED_BY",
                        strength="",
                        evidence_quality="",
                    )
                )

        return self._build_result(semantic_matches, [], q)

    def _query_generic(self, q: ClinicalQuery) -> GraphRAGResult:
        """Generic query — search recommendations by entity + type."""
        rec_matches: list[RecommendationMatch] = []
        all_evidence: list[EvidenceCitation] = []

        for concept in q.concepts:
            # Try each entity type until we find matches
            for entity_type in ("drug", "drug_class", "disease", "procedure", "device"):
                entity = link_entity(concept, entity_type)
                if entity is None:
                    continue

                cypher, params = ReasoningQueries.find_recommendations_for_entity(
                    entity.node_id, entity.node_label, rec_type=q.intent
                )
                rows = self._conn.execute_read(cypher, params)

                for row in rows:
                    rec_matches.append(
                        RecommendationMatch(
                            rec_id=row.get("rec_id", ""),
                            rec_type=row.get("rec_type", ""),
                            action=row.get("action", ""),
                            action_detail=row.get("detail", ""),
                            strength=row.get("strength", ""),
                            evidence_quality=row.get("evidence_quality", ""),
                        )
                    )
                    if row.get("source_text"):
                        all_evidence.append(
                            EvidenceCitation(
                                chunk_id="",
                                text=row["source_text"],
                                guideline_title=row.get("guideline", ""),
                                doi=row.get("doi", ""),
                                section=row.get("section", ""),
                            )
                        )

                if rows:
                    break

        confidence = "high" if rec_matches else "low"
        return GraphRAGResult(
            source="graph_traversal",
            recommendation_matches=rec_matches,
            evidence=all_evidence,
            confidence=confidence,
        )

    # ----- Helpers -----

    def _evaluate_match_conditions(
        self, match: SemanticMatch, patient_vars: dict[str, Any]
    ) -> None:
        """Evaluate eligibility conditions against patient variables."""
        if not match.conditions_json:
            return

        try:
            conditions = json.loads(match.conditions_json)
        except (json.JSONDecodeError, TypeError):
            return

        if not isinstance(conditions, list):
            return

        missing: list[str] = []
        all_met = True

        for cond in conditions:
            result = self._evaluate_condition(cond, patient_vars)
            if result is None:
                missing.append(cond.get("variable", ""))
                all_met = False
            elif not result:
                all_met = False

        match.conditions_met = all_met and len(missing) == 0
        match.missing_variables = missing

    @staticmethod
    def _evaluate_condition(
        cond: dict, patient_vars: dict[str, Any]
    ) -> bool | None:
        """Evaluate a single condition. Returns None if variable missing."""
        var = cond.get("variable", "")
        if var not in patient_vars:
            return None
        op_fn = OPS.get(cond.get("operator", ""))
        if not op_fn:
            return None
        try:
            return op_fn(float(patient_vars[var]), float(cond["threshold"]))
        except (ValueError, TypeError):
            return op_fn(str(patient_vars[var]), str(cond["threshold"]))

    def _fetch_evidence_for_matches(
        self,
        matches: list[SemanticMatch],
        q: ClinicalQuery,
    ) -> list[EvidenceCitation]:
        """Fetch Layer 2 evidence for semantic matches."""
        evidence: list[EvidenceCitation] = []
        seen_chunks: set[str] = set()

        for match in matches:
            cypher, params = ReasoningQueries.find_recommendations_for_entity(
                match.entity_id, match.entity_type
            )
            rows = self._conn.execute_read(cypher, params)

            for row in rows:
                text = row.get("source_text", "")
                if text and text not in seen_chunks:
                    seen_chunks.add(text)
                    evidence.append(
                        EvidenceCitation(
                            chunk_id="",
                            text=text,
                            guideline_title=row.get("guideline", ""),
                            doi=row.get("doi", ""),
                            section=row.get("section", ""),
                        )
                    )

        return evidence

    def _build_result(
        self,
        semantic_matches: list[SemanticMatch],
        evidence: list[EvidenceCitation],
        q: ClinicalQuery,
    ) -> GraphRAGResult:
        """Build final result with ranking and conflict detection."""
        # Sort by conditions_met (met first), then strength
        semantic_matches.sort(
            key=lambda m: (
                not m.conditions_met,
                STRENGTH_RANK.get(m.strength, 99),
            )
        )

        # Detect conflicts among recommendation matches
        # (done at Layer 2 level if we have recommendation data)

        # Determine confidence
        full_matches = [m for m in semantic_matches if m.conditions_met]
        all_missing = []
        for m in semantic_matches:
            all_missing.extend(m.missing_variables)

        if full_matches:
            confidence = "high"
        elif semantic_matches:
            confidence = "medium"
        else:
            confidence = "low"

        return GraphRAGResult(
            source="graph_traversal",
            semantic_matches=semantic_matches,
            evidence=evidence,
            confidence=confidence,
            missing_variables=list(set(all_missing)),
        )

    @staticmethod
    def _empty_result() -> GraphRAGResult:
        return GraphRAGResult(source="graph_traversal", confidence="low")

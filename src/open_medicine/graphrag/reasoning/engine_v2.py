"""GraphRAG Reasoning Engine v2 — Semantic edge traversal with dual-layer queries.

Supersedes engine.py. Uses typed semantic edges for one-hop clinical queries
(Layer 1) and falls back to recommendation traversal (Layer 2) for full
evidence chains.

Retrieval layers:
  Layer 1 (direct)   — One-hop semantic edge traversal
  Layer 2 (expanded) — Multi-hop: DrugClass→members, Disease→parent/children
"""

from __future__ import annotations

import json
import logging
import operator
import os
from typing import TYPE_CHECKING, Any

from open_medicine.graphrag.graph.queries_v2 import ReasoningQueries
from open_medicine.graphrag.ingestion.embeddings import embed_query
from open_medicine.graphrag.ingestion.linker_v2 import get_drug_class_members, link_entity
from open_medicine.graphrag.terminology import fuzzy_match
from open_medicine.graphrag.reasoning.types_v2 import (
    ClinicalQuery,
    EvidenceCitation,
    GraphRAGResult,
    RecommendationMatch,
    SemanticMatch,
)

if TYPE_CHECKING:
    from open_medicine.graphrag.graph.connection import GraphConnection

logger = logging.getLogger(__name__)

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

# Layer priority for sort ordering (lower = higher priority)
_LAYER_RANK = {"direct": 0, "expanded": 1, "vector": 2}

# Maps query intents to Layer 1 query methods
_INTENT_TO_QUERY = {
    "treatment_selection": "_query_treatments",
    "contraindication": "_query_contraindications",
    "interaction": "_query_interactions",
    "dosing": "_query_dosing",
    "monitoring": "_query_monitoring",
    "diagnostic_criteria": "_query_diagnostic_criteria",
}


class ReasoningEngine:
    """Graph-based clinical reasoning using semantic edges."""

    def __init__(self, conn: GraphConnection) -> None:
        self._conn = conn

    def query(self, q: ClinicalQuery) -> GraphRAGResult:
        """Execute a clinical query using the dual-layer graph.

        1. Try Layer 1 semantic edge traversal (one-hop)
        2. If below threshold, try Layer 2 expansion (multi-hop)
        3. If include_evidence, enrich with recommendation data
        4. Evaluate patient conditions
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

    # ----- Intent-specific queries (Layer 1 + Layer 2 expansion) -----

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

            # Layer 2 expansion: if insufficient results, try parent diseases
            if len(semantic_matches) < q.min_results_threshold:
                expanded = self._expand_disease_hierarchy(
                    entity.node_id, "treatment_selection", q,
                )
                semantic_matches.extend(expanded)

        # Layer 3: vector fallback if still empty
        if len(semantic_matches) == 0:
            vector_matches = self._vector_fallback(q)
            semantic_matches.extend(vector_matches)

        semantic_matches = self._deduplicate(semantic_matches)

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

    @staticmethod
    def _is_known_entity(entity: Any) -> bool:
        """Check if entity was resolved from terminology (not synthetic)."""
        if entity is None:
            return False
        # Synthetic entities have generic IDs like "drug:ace_inhibitors"
        # Real entities have coded IDs like "rxnorm:123", "atc:C09A", "snomed:456"
        return any([
            entity.snomed_code, entity.rxnorm_code, entity.atc_code,
            entity.loinc_code, entity.icd10_code, entity.cpt_code,
            entity.gmdn_code,
        ])

    def _query_interactions(self, q: ClinicalQuery) -> GraphRAGResult:
        """Find drug interactions via INTERACTS_WITH edges."""
        semantic_matches: list[SemanticMatch] = []

        for concept in q.concepts:
            entity = link_entity(concept, "drug")
            if not self._is_known_entity(entity):
                entity = link_entity(concept, "drug_class")
            if entity is None:
                continue

            cypher, params = ReasoningQueries.find_interactions(
                entity.node_id, entity_label=entity.node_label
            )
            rows = self._conn.execute_read(cypher, params)

            for row in rows:
                semantic_matches.append(
                    SemanticMatch(
                        entity_id=row.get("entity_id", ""),
                        entity_name=row.get("entity_name", ""),
                        entity_type=row.get("entity_type", "Drug"),
                        edge_type="INTERACTS_WITH",
                        strength="",
                        evidence_quality="",
                    )
                )

        return self._build_result(semantic_matches, [], q)

    def _query_diagnostic_criteria(self, q: ClinicalQuery) -> GraphRAGResult:
        """Find diagnostic criteria via DIAGNOSED_BY edges."""
        semantic_matches: list[SemanticMatch] = []

        for concept in q.concepts:
            entity = link_entity(concept, "disease")
            if entity is None:
                continue

            cypher, params = ReasoningQueries.find_diagnostic_criteria(entity.node_id)
            rows = self._conn.execute_read(cypher, params)

            for row in rows:
                semantic_matches.append(
                    SemanticMatch(
                        entity_id=row.get("entity_id", ""),
                        entity_name=row.get("entity_name", ""),
                        entity_type=row.get("entity_type", ""),
                        edge_type="DIAGNOSED_BY",
                        strength="",
                        evidence_quality="",
                    )
                )

        if not semantic_matches:
            return self._query_generic(q)

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
                # Layer 2: concept might be a drug class — expand to members
                expanded = self._expand_drug_class_to_monitoring(concept)
                semantic_matches.extend(expanded)
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

        semantic_matches = self._deduplicate(semantic_matches)
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
        hints = self._generate_hints(q) if not rec_matches else []
        return GraphRAGResult(
            source="graph_traversal",
            recommendation_matches=rec_matches,
            evidence=all_evidence,
            confidence=confidence,
            hints=hints,
        )

    # ----- Layer 2: Multi-hop expansion -----

    def _expand_disease_hierarchy(
        self, disease_id: str, intent: str, q: ClinicalQuery,
    ) -> list[SemanticMatch]:
        """Expand disease to parent diseases and query treatments for each."""
        cypher, params = ReasoningQueries.find_disease_parents(disease_id)
        rows = self._conn.execute_read(cypher, params)

        matches: list[SemanticMatch] = []
        for row in rows:
            parent_id = row.get("parent_id")
            if not parent_id:
                continue

            if intent == "treatment_selection":
                t_cypher, t_params = ReasoningQueries.find_treatments(
                    parent_id, q.guideline_filter
                )
                t_rows = self._conn.execute_read(t_cypher, t_params)
                for t_row in t_rows:
                    match = SemanticMatch(
                        entity_id=t_row.get("entity_id", ""),
                        entity_name=t_row.get("entity_name", ""),
                        entity_type=t_row.get("entity_type", ""),
                        edge_type="INDICATED_FOR",
                        strength=t_row.get("strength", ""),
                        evidence_quality=t_row.get("evidence_quality", ""),
                        conditions_json=t_row.get("conditions"),
                        source_layer="expanded",
                    )
                    self._evaluate_match_conditions(match, q.patient_vars)
                    matches.append(match)

        return matches

    def _expand_drug_class_to_monitoring(
        self, class_name: str,
    ) -> list[SemanticMatch]:
        """Expand a drug class to member drugs and find monitoring for each."""
        members = get_drug_class_members(class_name)
        matches: list[SemanticMatch] = []

        for member_name in members:
            entity = link_entity(member_name, "drug")
            if entity is None:
                continue

            cypher, params = ReasoningQueries.find_monitoring(entity.node_id)
            rows = self._conn.execute_read(cypher, params)

            for row in rows:
                matches.append(
                    SemanticMatch(
                        entity_id=row.get("lab_id", ""),
                        entity_name=row.get("lab_name", ""),
                        entity_type="Lab",
                        edge_type="MONITORED_BY",
                        strength="",
                        evidence_quality="",
                        source_layer="expanded",
                    )
                )

        return matches

    # ----- Layer 3: Vector fallback -----

    # Intent → rec_type mapping for vector search filtering
    _INTENT_TO_REC_TYPE = {
        "treatment_selection": "treatment_selection",
        "contraindication": "contraindication",
        "interaction": "interaction",
        "dosing": "dosing",
        "monitoring": "monitoring",
    }

    def _vector_fallback(self, q: ClinicalQuery) -> list[SemanticMatch]:
        """Layer 3: Vector search over EvidenceChunks → entity traversal."""
        api_key = os.environ.get("VOYAGE_API_KEY", "")
        try:
            query_text = f"{q.intent} {' '.join(q.concepts)}"
            embedding = embed_query(query_text, api_key=api_key)
        except Exception:
            logger.debug("Vector fallback skipped: embedding failed")
            return []

        rec_type = self._INTENT_TO_REC_TYPE.get(q.intent)
        cypher, params = ReasoningQueries.vector_entity_search(
            embedding, rec_type=rec_type, limit=10
        )
        rows = self._conn.execute_read(cypher, params)

        matches: list[SemanticMatch] = []
        for row in rows:
            matches.append(
                SemanticMatch(
                    entity_id=row.get("entity_id", ""),
                    entity_name=row.get("entity_name", ""),
                    entity_type=row.get("entity_type", ""),
                    edge_type=self._infer_edge_type(q.intent),
                    strength=row.get("strength", ""),
                    evidence_quality=row.get("evidence_quality", ""),
                    conditions_json=row.get("conditions"),
                    source_layer="vector",
                )
            )
        return matches

    @staticmethod
    def _infer_edge_type(intent: str) -> str:
        """Map intent to the expected semantic edge type."""
        return {
            "treatment_selection": "INDICATED_FOR",
            "contraindication": "CONTRAINDICATED_IN",
            "interaction": "INTERACTS_WITH",
            "dosing": "DOSED_FOR",
            "monitoring": "MONITORED_BY",
        }.get(intent, "RECOMMENDS")

    # ----- Layer 4: Hint generation -----

    def _generate_hints(self, q: ClinicalQuery) -> list[str]:
        """Generate actionable reformulation hints when results are empty."""
        hints: list[str] = []

        # Hint 1: unsupported intent
        if q.intent not in _INTENT_TO_QUERY:
            supported = ", ".join(sorted(_INTENT_TO_QUERY.keys()))
            hints.append(
                f"Intent '{q.intent}' is not directly routed. "
                f"Supported intents: {supported}"
            )

        # Hint 2: concept not found — suggest similar
        for concept in q.concepts:
            similar = fuzzy_match(concept, max_results=3)
            if similar:
                suggestions = ", ".join(
                    f"{name} ({etype})" for name, etype in similar
                )
                hints.append(
                    f"Concept '{concept}' not found in graph. "
                    f"Similar: {suggestions}"
                )
            else:
                hints.append(f"Concept '{concept}' not found in terminology.")

        return hints

    # ----- Helpers -----

    @staticmethod
    def _deduplicate(matches: list[SemanticMatch]) -> list[SemanticMatch]:
        """Deduplicate by (entity_id, edge_type), keeping first occurrence."""
        seen: set[tuple[str, str]] = set()
        result: list[SemanticMatch] = []
        for m in matches:
            key = (m.entity_id, m.edge_type)
            if key not in seen:
                seen.add(key)
                result.append(m)
        return result

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

        # Normalize patient variable keys to lowercase for case-insensitive matching
        norm_vars = {k.lower(): v for k, v in patient_vars.items()}

        missing: list[str] = []
        any_failed = False

        for cond in conditions:
            result = self._evaluate_condition(cond, norm_vars)
            if result is None:
                missing.append(cond.get("variable", ""))
            elif not result:
                any_failed = True

        match.conditions_met = not any_failed
        match.missing_variables = missing

    @staticmethod
    def _evaluate_condition(
        cond: dict, patient_vars: dict[str, Any]
    ) -> bool | None:
        """Evaluate a single condition. Returns None if variable missing."""
        var = cond.get("variable", "")
        var_lower = var.lower()
        if var_lower not in patient_vars:
            return None
        op_fn = OPS.get(cond.get("operator", ""))
        if not op_fn:
            return None
        try:
            return op_fn(float(patient_vars[var_lower]), float(cond["threshold"]))
        except (ValueError, TypeError):
            return op_fn(str(patient_vars[var_lower]), str(cond["threshold"]))

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
        # Sort by: layer priority, conditions_met (met first), then strength
        semantic_matches.sort(
            key=lambda m: (
                _LAYER_RANK.get(m.source_layer, 99),
                not m.conditions_met,
                STRENGTH_RANK.get(m.strength, 99),
            )
        )

        # Track which layers contributed
        layers = sorted({m.source_layer for m in semantic_matches})

        # Determine confidence
        full_matches = [m for m in semantic_matches if m.conditions_met]
        all_missing: list[str] = []
        for m in semantic_matches:
            all_missing.extend(m.missing_variables)

        if full_matches:
            confidence = "high"
        elif semantic_matches:
            confidence = "medium"
        else:
            confidence = "low"

        # Layer 4: hints when results are empty
        hints: list[str] = []
        if not semantic_matches:
            hints = self._generate_hints(q)

        return GraphRAGResult(
            source="graph_traversal",
            semantic_matches=semantic_matches,
            evidence=evidence,
            confidence=confidence,
            missing_variables=list(set(all_missing)),
            retrieval_layers_used=layers,
            hints=hints,
        )

    @staticmethod
    def _empty_result() -> GraphRAGResult:
        return GraphRAGResult(source="graph_traversal", confidence="low")

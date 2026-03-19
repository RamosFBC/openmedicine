"""GraphRAG Reasoning Types v2 — Typed results with GRADE-aligned evidence.

Supersedes types.py. Uses separate strength/evidence_quality fields
and supports dual-layer query results.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ClinicalQuery(BaseModel):
    """Query input for the reasoning engine."""

    intent: str = Field(
        description="Query type: treatment_selection, dosing, contraindication, "
        "interaction, monitoring, diagnostic_criteria, prevention, referral, "
        "device_therapy, lifestyle, discharge, follow_up"
    )
    concepts: list[str] = Field(
        description="Clinical concept names to query (drug names, conditions, etc.)"
    )
    patient_vars: dict[str, float | str | bool] = Field(
        default_factory=dict, description="Patient variables and their values"
    )
    guideline_filter: str | None = Field(
        default=None, description="Optional: scope to a specific guideline"
    )
    include_evidence: bool = Field(
        default=True, description="Include Layer 2 evidence chain in response"
    )
    min_results_threshold: int = Field(
        default=1,
        description="Minimum results before triggering fallback layers",
    )


class SemanticMatch(BaseModel):
    """A single match from Layer 1 semantic edge traversal."""

    entity_id: str = Field(description="ID of the matched clinical entity")
    entity_name: str = Field(description="Name of the matched entity")
    entity_type: str = Field(description="Neo4j label (Drug, Disease, etc.)")
    edge_type: str = Field(description="Semantic edge type (INDICATED_FOR, etc.)")
    strength: str = Field(description="Recommendation strength")
    evidence_quality: str = Field(description="Evidence quality level")
    conditions_json: str | None = Field(
        default=None, description="Eligibility criteria"
    )
    conditions_met: bool | None = Field(
        default=True,
        description="Whether patient meets criteria. True=all passed, "
        "False=at least one failed, None=uncertain (missing variables)",
    )
    missing_variables: list[str] = Field(
        default_factory=list, description="Variables needed but not provided"
    )
    source_layer: str = Field(
        default="direct",
        description="Retrieval layer: direct, expanded, or vector",
    )
    similarity_score: float | None = Field(
        default=None,
        description="Cosine similarity score (0-1) for vector-sourced matches",
    )
    edge_properties: dict[str, str | None] = Field(
        default_factory=dict,
        description="Edge-specific properties (severity, starting_dose, frequency, "
        "threshold_alert, threshold_stop, mechanism, clinical_effect, etc.)",
    )


class RecommendationMatch(BaseModel):
    """A match from Layer 2 recommendation traversal (full provenance)."""

    rec_id: str = Field(description="Recommendation node ID")
    rec_type: str = Field(description="Recommendation type")
    action: str = Field(description="Recommended action")
    action_detail: str = Field(description="Human-readable explanation")
    strength: str = Field(description="Recommendation strength")
    evidence_quality: str = Field(description="Evidence quality level")
    conditions_met: bool | None = Field(
        default=True,
        description="Whether patient meets criteria. True=all passed, "
        "False=at least one failed, None=uncertain (missing variables)",
    )
    missing_variables: list[str] = Field(default_factory=list)


class EvidenceCitation(BaseModel):
    """Source text with full provenance trail."""

    chunk_id: str
    text: str
    guideline_title: str = ""
    doi: str = ""
    section: str = ""


class GraphRAGResult(BaseModel):
    """Combined result from dual-layer queries."""

    source: Literal["graph_traversal", "llm_synthesis"] = "graph_traversal"
    semantic_matches: list[SemanticMatch] = Field(
        default_factory=list, description="Layer 1 one-hop results"
    )
    recommendation_matches: list[RecommendationMatch] = Field(
        default_factory=list, description="Layer 2 provenance results"
    )
    synthesis: str | None = None
    evidence: list[EvidenceCitation] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "low"
    missing_variables: list[str] = Field(default_factory=list)
    retrieval_layers_used: list[str] = Field(
        default_factory=list,
        description="Layers that contributed results: direct, expanded, vector",
    )
    hints: list[str] = Field(
        default_factory=list,
        description="Reformulation suggestions when results are empty",
    )
    corrections_attempted: list[str] = Field(
        default_factory=list,
        description="Self-correction strategies attempted: fuzzy_retry, class_escalation, concept_decomposition",
    )
    data_coverage: Literal["full", "partial", "none"] = Field(
        default="full",
        description=(
            "Whether queried entities exist in the graph. "
            "'none' = entity not found (cannot confirm safety). "
            "'partial' = some entities found. "
            "'full' = all queried entities found."
        ),
    )

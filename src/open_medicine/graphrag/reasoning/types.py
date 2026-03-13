from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field


class ClinicalQuery(BaseModel):
    intent: str = Field(description="Query type: dosing, contraindication, interaction, monitoring, treatment_selection, diagnostic_criteria")
    concepts: list[str] = Field(description="Clinical concepts to query (drug names, conditions, etc.)")
    patient_vars: dict[str, float | str | bool] = Field(default_factory=dict, description="Patient variables")
    guideline_filter: str | None = Field(default=None, description="Optional: scope to a specific guideline")
    include_source_text: bool = Field(default=True, description="Include raw source text in response")


class LogicNodeMatch(BaseModel):
    logic_node_id: str
    type: str
    action: str
    action_detail: str
    strength: str
    conditions_met: bool
    missing_variables: list[str] = Field(default_factory=list)


class EvidenceCitation(BaseModel):
    chunk_id: str
    text: str
    guideline_title: str
    doi: str
    section: str
    page: int


class GraphRAGResult(BaseModel):
    source: Literal["graph_traversal", "llm_synthesis"]
    matches: list[LogicNodeMatch]
    synthesis: str | None = None
    evidence: list[EvidenceCitation]
    confidence: Literal["high", "medium", "low"]
    missing_variables: list[str] = Field(default_factory=list)

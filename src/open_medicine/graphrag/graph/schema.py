from __future__ import annotations
from enum import StrEnum
from pydantic import BaseModel, Field, field_validator


class ConceptType(StrEnum):
    DRUG = "drug"
    DISEASE = "disease"
    LAB = "lab"
    PROCEDURE = "procedure"
    SYMPTOM = "symptom"


class LogicNodeType(StrEnum):
    DOSING = "dosing"
    CONTRAINDICATION = "contraindication"
    INTERACTION = "interaction"
    MONITORING = "monitoring"
    TREATMENT_SELECTION = "treatment_selection"
    DIAGNOSTIC_CRITERIA = "diagnostic_criteria"


class VariableType(StrEnum):
    CONTINUOUS = "continuous"
    CATEGORICAL = "categorical"
    BOOLEAN = "boolean"


VALID_OPERATORS = {"<", "<=", ">", ">=", "==", "!="}


class Condition(BaseModel):
    variable: str = Field(description="Patient variable name, e.g. eGFR")
    operator: str = Field(description="Comparison operator")
    threshold: float | str = Field(description="Threshold value")
    unit: str | None = Field(default=None, description="Unit of measurement")

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v: str) -> str:
        if v not in VALID_OPERATORS:
            raise ValueError(f"Invalid operator '{v}'. Must be one of {VALID_OPERATORS}")
        return v


class Concept(BaseModel):
    id: str = Field(description="Canonical identifier")
    name: str = Field(description="Human-readable name")
    type: ConceptType = Field(description="Entity type")
    snomed_code: str | None = Field(default=None, description="SNOMED-CT code")
    loinc_code: str | None = Field(default=None, description="LOINC code")
    fhir_code: str | None = Field(default=None, description="FHIR code")
    aliases: list[str] = Field(default_factory=list, description="Alternative names")


class LogicNode(BaseModel):
    id: str = Field(description="Unique identifier")
    type: LogicNodeType = Field(description="Rule type")
    conditions: list[Condition] = Field(description="Conditions that trigger this rule")
    action: str = Field(description="Action to take")
    action_detail: str = Field(description="Human-readable explanation")
    strength: str = Field(description="Evidence strength (e.g. Strong/A)")
    guideline_id: str = Field(description="Source guideline ID")
    page: int = Field(description="Source page number")


class EvidenceChunk(BaseModel):
    id: str = Field(description="Deterministic hash ID")
    text: str = Field(description="Raw source text")
    guideline_id: str = Field(description="Source guideline ID")
    section: str = Field(description="Section name")
    page_start: int = Field(description="Start page")
    page_end: int = Field(description="End page")
    parent_chunk_id: str | None = Field(default=None, description="Parent chunk ID")
    embedding: list[float] | None = Field(default=None, description="Vector embedding")


class Guideline(BaseModel):
    id: str = Field(description="Unique guideline identifier")
    title: str = Field(description="Full guideline title")
    doi: str = Field(description="DOI of the guideline")
    year: int = Field(description="Publication year")
    organization: str = Field(description="Issuing organization")
    total_pages: int = Field(description="Total pages in source PDF")


class PatientVariable(BaseModel):
    id: str = Field(description="Variable identifier (e.g. eGFR)")
    name: str = Field(description="Human-readable name")
    unit: str = Field(description="Unit of measurement")
    loinc_code: str | None = Field(default=None, description="LOINC code")
    type: VariableType = Field(description="Variable type")

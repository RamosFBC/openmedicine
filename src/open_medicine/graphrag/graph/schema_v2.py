"""GraphRAG Schema v2 — Production-grade clinical knowledge graph models.

Type-native node labels, semantic relationship types, and dual-layer
architecture following patterns from Hetionet, PrimeKG, and CKG.

Supersedes schema.py (single Concept label + generic PARTICIPATES_IN).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class RecommendationType(StrEnum):
    """Clinical recommendation categories (replaces LogicNodeType)."""

    TREATMENT_SELECTION = "treatment_selection"
    DOSING = "dosing"
    CONTRAINDICATION = "contraindication"
    INTERACTION = "interaction"
    MONITORING = "monitoring"
    DIAGNOSTIC_CRITERIA = "diagnostic_criteria"
    PREVENTION = "prevention"
    REFERRAL = "referral"
    DEVICE_THERAPY = "device_therapy"
    LIFESTYLE = "lifestyle"
    DISCHARGE = "discharge"
    FOLLOW_UP = "follow_up"


class EvidenceQuality(StrEnum):
    """GRADE-aligned evidence quality levels."""

    HIGH = "high"  # LOE A — RCTs, meta-analyses
    MODERATE = "moderate"  # LOE B-R — Randomized, moderate quality
    LOW = "low"  # LOE B-NR — Non-randomized
    VERY_LOW = "very_low"  # LOE C-LD — Limited data
    EXPERT = "expert"  # LOE C-EO — Expert opinion


class RecommendationStrength(StrEnum):
    """ACC/AHA class-based recommendation strength."""

    STRONG_FOR = "strong_for"  # Class I — Benefit >>> Risk
    MODERATE_FOR = "moderate_for"  # Class IIa — Benefit >> Risk
    WEAK_FOR = "weak_for"  # Class IIb — Benefit >= Risk
    STRONG_AGAINST = "strong_against"  # Class III (Harm)
    NO_BENEFIT = "no_benefit"  # Class III (No Benefit)


class TemporalType(StrEnum):
    """Types of temporal constraints in clinical guidelines."""

    DURATION = "duration"  # "for 12 weeks"
    FREQUENCY = "frequency"  # "every 2 weeks", "BID"
    RELATIVE = "relative"  # "within 36 hours of"
    SEQUENCE = "sequence"  # "start X before Y"
    WASHOUT = "washout"  # "36 hours between ACEi and ARNi"
    REASSESSMENT = "reassessment"  # "reassess at 3 months"


class VariableType(StrEnum):
    """Patient variable data types."""

    CONTINUOUS = "continuous"
    CATEGORICAL = "categorical"
    BOOLEAN = "boolean"


class InteractionSeverity(StrEnum):
    """Drug-drug interaction severity levels."""

    MAJOR = "major"
    MODERATE = "moderate"
    MINOR = "minor"


class ContraindicationSeverity(StrEnum):
    """Contraindication severity levels."""

    ABSOLUTE = "absolute"
    RELATIVE = "relative"


class Likelihood(StrEnum):
    """Frequency/likelihood qualifiers for clinical associations."""

    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"


# ---------------------------------------------------------------------------
# Shared field constants
# ---------------------------------------------------------------------------

VALID_OPERATORS = {"<", "<=", ">", ">=", "==", "!="}


# ---------------------------------------------------------------------------
# Clinical Core Nodes (Layer 1 entities)
# ---------------------------------------------------------------------------


class Drug(BaseModel):
    """Specific medication — primary ID: RxNorm CUI."""

    id: str = Field(description="Primary ID, format: rxnorm:{CUI}")
    name: str = Field(description="Canonical drug name")
    rxnorm_code: str | None = Field(default=None, description="RxNorm CUI")
    snomed_code: str | None = Field(default=None, description="SNOMED-CT code")
    atc_code: str | None = Field(default=None, description="ATC code")
    drugbank_id: str | None = Field(default=None, description="DrugBank ID")
    aliases: list[str] = Field(default_factory=list, description="Alternative names")


class DrugClass(BaseModel):
    """Pharmacologic class (ATC L2-L4) — primary ID: ATC code."""

    id: str = Field(description="Primary ID, format: atc:{code}")
    name: str = Field(description="Canonical class name")
    atc_code: str | None = Field(default=None, description="ATC code")
    fda_epc: str | None = Field(
        default=None, description="FDA Established Pharmacologic Class"
    )
    aliases: list[str] = Field(default_factory=list, description="Alternative names")


class Disease(BaseModel):
    """Condition, syndrome, or clinical state — primary ID: SNOMED-CT."""

    id: str = Field(description="Primary ID, format: snomed:{code}")
    name: str = Field(description="Canonical disease name")
    snomed_code: str | None = Field(default=None, description="SNOMED-CT code")
    icd10_code: str | None = Field(default=None, description="ICD-10 code")
    mondo_id: str | None = Field(default=None, description="MONDO ID")
    aliases: list[str] = Field(default_factory=list, description="Alternative names")


class Symptom(BaseModel):
    """Patient-reported symptom or clinical sign — primary ID: SNOMED-CT."""

    id: str = Field(description="Primary ID, format: snomed:{code}")
    name: str = Field(description="Canonical symptom name")
    snomed_code: str | None = Field(default=None, description="SNOMED-CT code")
    aliases: list[str] = Field(default_factory=list, description="Alternative names")


class Lab(BaseModel):
    """Lab test, biomarker, measurement, or vital — primary ID: LOINC."""

    id: str = Field(description="Primary ID, format: loinc:{code}")
    name: str = Field(description="Canonical lab/test name")
    loinc_code: str | None = Field(default=None, description="LOINC code")
    snomed_code: str | None = Field(default=None, description="SNOMED-CT code")
    unit: str | None = Field(default=None, description="Standard unit of measurement")
    reference_range: str | None = Field(
        default=None, description="Normal reference range"
    )


class Procedure(BaseModel):
    """Diagnostic or therapeutic procedure — primary ID: SNOMED-CT."""

    id: str = Field(description="Primary ID, format: snomed:{code}")
    name: str = Field(description="Canonical procedure name")
    snomed_code: str | None = Field(default=None, description="SNOMED-CT code")
    cpt_code: str | None = Field(default=None, description="CPT code")
    aliases: list[str] = Field(default_factory=list, description="Alternative names")


class Device(BaseModel):
    """Medical device (ICD, CRT, LVAD, CPAP) — primary ID: SNOMED-CT."""

    id: str = Field(description="Primary ID, format: snomed:{code}")
    name: str = Field(description="Canonical device name")
    snomed_code: str | None = Field(default=None, description="SNOMED-CT code")
    gmdn_code: str | None = Field(default=None, description="GMDN code")
    aliases: list[str] = Field(default_factory=list, description="Alternative names")


# ---------------------------------------------------------------------------
# Evidence & Recommendation Nodes (Layer 2)
# ---------------------------------------------------------------------------


class Guideline(BaseModel):
    """Source clinical guideline document."""

    id: str = Field(description="Unique guideline identifier")
    title: str = Field(description="Full guideline title")
    doi: str = Field(description="DOI of the guideline")
    year: int = Field(description="Publication year")
    organization: str = Field(description="Issuing organization")
    version: str | None = Field(default=None, description="Guideline version")


class Recommendation(BaseModel):
    """Single clinical recommendation (replaces LogicNode).

    Each Recommendation connects to clinical entities via semantic edges
    (Layer 2) and is backed by EvidenceChunks for provenance.
    """

    id: str = Field(description="Deterministic ID")
    type: RecommendationType = Field(description="Recommendation category")
    action: str = Field(description="Recommended action")
    action_detail: str = Field(description="Human-readable explanation")
    strength: RecommendationStrength = Field(description="Recommendation strength")
    evidence_quality: EvidenceQuality = Field(description="Evidence quality level")
    conditions_json: str | None = Field(
        default=None,
        description="JSON-encoded eligibility criteria (structured backup)",
    )
    guideline_id: str = Field(description="Source guideline ID")
    section: str | None = Field(default=None, description="Guideline section")
    page: int | None = Field(default=None, description="Source page number")


class EvidenceChunk(BaseModel):
    """Source text passage — shared across multiple Recommendations."""

    id: str = Field(description="Content-hash ID")
    text: str = Field(description="Raw source text")
    section: str | None = Field(default=None, description="Section name")
    page_start: int | None = Field(default=None, description="Start page")
    page_end: int | None = Field(default=None, description="End page")
    embedding: list[float] | None = Field(default=None, description="Vector embedding")


class Publication(BaseModel):
    """Cited study or trial supporting a recommendation."""

    doi: str = Field(description="Publication DOI (primary ID)")
    title: str | None = Field(default=None, description="Publication title")
    authors: str | None = Field(default=None, description="Author list")
    journal: str | None = Field(default=None, description="Journal name")
    year: int | None = Field(default=None, description="Publication year")
    study_type: str | None = Field(
        default=None, description="Study type (RCT, meta-analysis, etc.)"
    )


# ---------------------------------------------------------------------------
# Patient Context Nodes
# ---------------------------------------------------------------------------


class PopulationCriterion(BaseModel):
    """Single criterion in a population definition."""

    variable: str = Field(description="Patient variable name (e.g. LVEF)")
    operator: str = Field(description="Comparison operator")
    threshold: float | str = Field(description="Threshold value")
    unit: str | None = Field(default=None, description="Unit of measurement")

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v: str) -> str:
        if v not in VALID_OPERATORS:
            msg = f"Invalid operator '{v}'. Must be one of {VALID_OPERATORS}"
            raise ValueError(msg)
        return v


class Population(BaseModel):
    """Defined patient cohort for a recommendation (FHIR EvidenceVariable)."""

    id: str = Field(description="Deterministic ID")
    description: str = Field(
        description="Human-readable cohort description",
    )
    inclusion: list[PopulationCriterion] = Field(
        default_factory=list, description="Inclusion criteria (ALL must be true)"
    )
    exclusion: list[PopulationCriterion] = Field(
        default_factory=list, description="Exclusion criteria (NONE must be true)"
    )


class PatientVariable(BaseModel):
    """Evaluable patient parameter — linked to Lab entities via MEASURES."""

    id: str = Field(description="Variable identifier")
    name: str = Field(description="Human-readable name")
    loinc_code: str | None = Field(default=None, description="LOINC code")
    unit: str | None = Field(default=None, description="Unit of measurement")
    var_type: VariableType = Field(description="Variable data type")


# ---------------------------------------------------------------------------
# Temporal Nodes
# ---------------------------------------------------------------------------


class TemporalConstraint(BaseModel):
    """Timing requirement for a clinical action."""

    id: str = Field(description="Deterministic ID")
    type: TemporalType = Field(description="Temporal constraint category")
    value: float | str | None = Field(
        default=None, description="Numeric or descriptive value"
    )
    unit: str | None = Field(
        default=None, description="Time unit (hours, days, weeks, months)"
    )
    reference_event: str | None = Field(
        default=None, description="Event this is relative to"
    )
    relation: str | None = Field(
        default=None, description="Temporal relation (within/before/after/during)"
    )


# ---------------------------------------------------------------------------
# Administrative Nodes
# ---------------------------------------------------------------------------


class Organization(BaseModel):
    """Guideline publisher (AHA, ACC, ESC, etc.)."""

    id: str = Field(description="Organization identifier")
    name: str = Field(description="Full organization name")
    abbreviation: str | None = Field(default=None, description="Common abbreviation")
    country: str | None = Field(default=None, description="Country of origin")


class CareSetting(BaseModel):
    """Where care is delivered."""

    id: str = Field(description="Care setting identifier")
    name: str = Field(
        description="Setting name (inpatient/outpatient/ICU/ED/ambulatory)"
    )


class CareTeamRole(BaseModel):
    """Specialist type for referral recommendations."""

    id: str = Field(description="Role identifier")
    name: str = Field(
        description="Role name (cardiologist/electrophysiologist/surgeon)"
    )


# ---------------------------------------------------------------------------
# Semantic Edge Property Models (Layer 1)
# ---------------------------------------------------------------------------


class IndicatedForProps(BaseModel):
    """Properties on INDICATED_FOR edges (Drug/DrugClass/Procedure/Device → Disease)."""

    strength: RecommendationStrength = Field(description="Recommendation strength")
    evidence_quality: EvidenceQuality = Field(description="Evidence quality")
    conditions_json: str | None = Field(
        default=None, description="JSON-encoded eligibility criteria"
    )


class ContraindicatedInProps(BaseModel):
    """Properties on CONTRAINDICATED_IN edges."""

    strength: RecommendationStrength = Field(description="Recommendation strength")
    severity: ContraindicationSeverity = Field(
        description="Absolute or relative contraindication"
    )
    conditions_json: str | None = Field(
        default=None, description="JSON-encoded eligibility criteria"
    )


class InteractsWithProps(BaseModel):
    """Properties on INTERACTS_WITH edges (Drug → Drug)."""

    severity: InteractionSeverity = Field(description="Interaction severity")
    mechanism: str | None = Field(default=None, description="Interaction mechanism")
    clinical_effect: str | None = Field(
        default=None, description="Clinical effect description"
    )


class DosedForProps(BaseModel):
    """Properties on DOSED_FOR edges (Drug → Disease)."""

    starting_dose: str | None = Field(default=None, description="Starting dose")
    target_dose: str | None = Field(default=None, description="Target dose")
    max_dose: str | None = Field(default=None, description="Maximum dose")
    route: str | None = Field(default=None, description="Route of administration")
    frequency: str | None = Field(default=None, description="Dosing frequency")
    titration_schedule: str | None = Field(
        default=None, description="Titration schedule"
    )
    conditions_json: str | None = Field(
        default=None, description="JSON-encoded eligibility criteria"
    )


class MonitoredByProps(BaseModel):
    """Properties on MONITORED_BY edges (Drug → Lab)."""

    frequency: str | None = Field(default=None, description="Monitoring frequency")
    threshold_alert: str | None = Field(
        default=None, description="Alert threshold value"
    )
    threshold_stop: str | None = Field(
        default=None, description="Stop threshold value"
    )
    conditions_json: str | None = Field(
        default=None, description="JSON-encoded conditions"
    )


class CausesSideEffectProps(BaseModel):
    """Properties on CAUSES_SIDE_EFFECT edges (Drug → Symptom/Disease)."""

    frequency: Likelihood = Field(description="How common the side effect is")
    severity: str | None = Field(default=None, description="Severity description")


class PresentsWithProps(BaseModel):
    """Properties on PRESENTS_WITH edges (Disease → Symptom)."""

    frequency: Likelihood = Field(description="How common the presentation is")
    specificity: str | None = Field(
        default=None, description="How specific to this disease"
    )


class DiagnosedByProps(BaseModel):
    """Properties on DIAGNOSED_BY edges (Disease → Procedure/Lab)."""

    sensitivity: str | None = Field(default=None, description="Test sensitivity")
    specificity: str | None = Field(default=None, description="Test specificity")
    when_to_order: str | None = Field(
        default=None, description="When to order this test"
    )
    conditions_json: str | None = Field(
        default=None, description="JSON-encoded conditions"
    )


class RiskFactorForProps(BaseModel):
    """Properties on RISK_FACTOR_FOR edges."""

    relative_risk: str | None = Field(default=None, description="Relative risk value")
    strength: RecommendationStrength | None = Field(
        default=None, description="Strength of association"
    )


class StageOfProps(BaseModel):
    """Properties on STAGE_OF edges (Disease → Disease)."""

    stage_system: str | None = Field(
        default=None, description="Staging system (e.g. ACC/AHA, NYHA)"
    )
    stage_value: str | None = Field(
        default=None, description="Stage value (e.g. Stage C, Class III)"
    )


class RecommendsProps(BaseModel):
    """Properties on RECOMMENDS edges (Recommendation → entity)."""

    role: str | None = Field(
        default=None,
        description="Role of recommended entity (primary/alternative/adjunct)",
    )


class ConflictsWithProps(BaseModel):
    """Properties on CONFLICTS_WITH edges (Recommendation → Recommendation)."""

    resolution: str | None = Field(
        default=None,
        description="Resolution strategy (newer/stronger/specialist)",
    )
    resolution_detail: str | None = Field(
        default=None, description="Detailed resolution explanation"
    )


class SupersedesProps(BaseModel):
    """Properties on SUPERSEDES edges (Recommendation → Recommendation)."""

    reason: str | None = Field(default=None, description="Reason for supersession")


class DefinesProps(BaseModel):
    """Properties on DEFINES edges (Population → Disease/Lab/PatientVariable)."""

    operator: str | None = Field(default=None, description="Comparison operator")
    threshold: float | str | None = Field(default=None, description="Threshold value")
    unit: str | None = Field(default=None, description="Unit of measurement")


# ---------------------------------------------------------------------------
# Node label → Model mapping (for loader dispatch)
# ---------------------------------------------------------------------------

NODE_LABEL_MAP: dict[str, type[BaseModel]] = {
    "Drug": Drug,
    "DrugClass": DrugClass,
    "Disease": Disease,
    "Symptom": Symptom,
    "Lab": Lab,
    "Procedure": Procedure,
    "Device": Device,
    "Guideline": Guideline,
    "Recommendation": Recommendation,
    "EvidenceChunk": EvidenceChunk,
    "Publication": Publication,
    "Population": Population,
    "PatientVariable": PatientVariable,
    "TemporalConstraint": TemporalConstraint,
    "Organization": Organization,
    "CareSetting": CareSetting,
    "CareTeamRole": CareTeamRole,
}

# Clinical entity labels (Layer 1 nodes that get semantic edges)
CLINICAL_LABELS = frozenset(
    {"Drug", "DrugClass", "Disease", "Symptom", "Lab", "Procedure", "Device"}
)

# All valid semantic edge types (Layer 1)
SEMANTIC_EDGE_TYPES = frozenset(
    {
        "INDICATED_FOR",
        "CONTRAINDICATED_IN",
        "INTERACTS_WITH",
        "DOSED_FOR",
        "MONITORED_BY",
        "CAUSES_SIDE_EFFECT",
        "MEMBER_OF",
        "PRESENTS_WITH",
        "DIAGNOSED_BY",
        "RISK_FACTOR_FOR",
        "STAGE_OF",
        "COMPLICATES",
        "REQUIRES_MONITORING",
    }
)

# Evidence/provenance edge types (Layer 2)
EVIDENCE_EDGE_TYPES = frozenset(
    {
        "RECOMMENDS",
        "FOR_CONDITION",
        "SOURCED_FROM",
        "DEFINED_BY",
        "CITED_IN",
        "PUBLISHED_BY",
        "EVALUATES",
        "APPLIES_TO",
        "TIMED_BY",
        "DELIVERED_IN",
        "REFERRED_TO",
    }
)

# Cross-guideline edge types
CROSS_GUIDELINE_EDGE_TYPES = frozenset(
    {"CONFLICTS_WITH", "SUPERSEDES", "CORROBORATES"}
)

# Patient context edge types
PATIENT_CONTEXT_EDGE_TYPES = frozenset({"MEASURES", "DEFINES"})

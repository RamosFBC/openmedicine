"""Guideline extraction v2 — Typed relationships and GRADE-aligned evidence.

Supersedes extractor.py. Outputs typed concept references with entity types
matching the new schema labels, and separate strength/evidence_quality fields.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field

from open_medicine.graphrag.graph.schema_v2 import (
    EvidenceQuality,
    PopulationCriterion,
    RecommendationStrength,
    RecommendationType,
)

logger = logging.getLogger(__name__)

# Valid entity types in the new schema
VALID_ENTITY_TYPES = frozenset(
    {"drug", "drug_class", "disease", "symptom", "lab", "procedure", "device"}
)

# Valid recommendation types (for prompt validation)
VALID_REC_TYPES = frozenset(v.value for v in RecommendationType)


@dataclass
class ConceptRef:
    """Reference to a clinical entity extracted from text."""

    name: str
    type: str  # drug, drug_class, disease, symptom, lab, procedure, device
    role: str = "subject"  # subject, target, monitor — role in the recommendation


@dataclass
class ExtractedRelationship:
    """Typed relationship between entities derived from extraction."""

    rel_type: str  # INDICATED_FOR, CONTRAINDICATED_IN, DOSED_FOR, etc.
    source_name: str
    source_type: str  # entity type of source
    target_name: str
    target_type: str  # entity type of target
    properties: dict = field(default_factory=dict)  # Edge properties


@dataclass
class ExtractionResult:
    """Single extracted recommendation with typed concepts and relationships."""

    rec_id: str
    rec_type: str  # RecommendationType value
    action: str
    action_detail: str
    strength: str  # RecommendationStrength value
    evidence_quality: str  # EvidenceQuality value
    conditions: list[dict] = field(default_factory=list)  # PopulationCriterion-like dicts
    concepts: list[ConceptRef] = field(default_factory=list)
    relationships: list[ExtractedRelationship] = field(default_factory=list)
    structured_properties: dict = field(default_factory=dict)  # Type-specific props (doses, severities, etc.)
    source_chunk_id: str = ""
    guideline_id: str = ""
    page: int = 0


EXTRACTION_PROMPT = """You are a clinical guideline extraction agent.

Given this text from a medical guideline, Section: {parent_context}:

---
{chunk_text}
---

Extract all clinical recommendations as a JSON array. Each recommendation must have:

- "id": unique string (format "rec_<guideline>_<number>")
- "type": one of: "treatment_selection", "dosing", "contraindication", "interaction", "monitoring", "diagnostic_criteria", "prevention", "referral", "device_therapy", "lifestyle", "discharge", "follow_up"
- "action": concise action string (e.g., "Prescribe ARNi", "Avoid in pregnancy")
- "action_detail": human-readable explanation of the recommendation
- "strength": one of: "strong_for", "moderate_for", "weak_for", "strong_against", "no_benefit"
- "evidence_quality": one of: "high", "moderate", "low", "very_low", "expert"
- "conditions": array of {{"variable": str, "operator": "<|<=|>|>=|==|!=", "threshold": number|string, "unit": str|null}}
- "guideline_id": "{guideline_id}"
- "page": {page}
- "concepts": array of {{"name": entity name, "type": "drug"|"drug_class"|"disease"|"symptom"|"lab"|"procedure"|"device", "role": "subject"|"target"|"monitor"}}
- "relationships": array of {{"rel_type": str, "source_name": str, "source_type": str, "target_name": str, "target_type": str, "properties": {{}}}}

Relationship types and their valid source → target:
- "INDICATED_FOR": Drug/DrugClass/Procedure/Device → Disease
- "CONTRAINDICATED_IN": Drug/DrugClass → Disease (properties: "severity": "absolute"|"relative")
- "DOSED_FOR": Drug → Disease (properties: "starting_dose", "target_dose", "max_dose", "route", "frequency")
- "MONITORED_BY": Drug → Lab (properties: "frequency", "threshold_alert", "threshold_stop")
- "INTERACTS_WITH": Drug → Drug (properties: "severity": "major"|"moderate"|"minor", "mechanism")
- "MEMBER_OF": Drug → DrugClass (only when text explicitly states class membership)

Map evidence strength from guideline notation:
- Class I / "is recommended" / "should" → "strong_for"
- Class IIa / "can be useful" / "is reasonable" → "moderate_for"
- Class IIb / "may be considered" → "weak_for"
- Class III Harm / "should not" / "is potentially harmful" → "strong_against"
- Class III No Benefit / "is not recommended" / "no benefit" → "no_benefit"
- LOE A / RCTs / meta-analyses → "high"
- LOE B-R / randomized → "moderate"
- LOE B-NR / non-randomized → "low"
- LOE C-LD / limited data → "very_low"
- LOE C-EO / expert opinion → "expert"

If no clinical recommendations are present, return an empty array [].
Return ONLY the JSON array, no other text."""


def _call_llm(prompt: str) -> str:
    """Call the LLM API. Separated for easy mocking."""
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def _call_llm_with_retry(
    prompt: str,
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> str:
    """Call LLM with exponential backoff on transient errors."""
    import anthropic as _anthropic

    for attempt in range(max_retries):
        try:
            return _call_llm(prompt)
        except (_anthropic.RateLimitError, _anthropic.APIConnectionError):
            if attempt == max_retries - 1:
                raise
            time.sleep(base_delay * (2**attempt))
    # Unreachable, but satisfies type checker
    raise RuntimeError("Retry loop exited unexpectedly")


def _strip_code_fences(text: str) -> str:
    """Strip markdown code fences from LLM output."""
    text = text.strip()
    if text.startswith("```"):
        # Remove opening fence (with optional language tag)
        first_newline = text.index("\n")
        text = text[first_newline + 1 :]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def _normalize_entity_type(raw_type: str) -> str:
    """Normalize entity type, mapping old types to new ones."""
    mapping = {
        "drug": "drug",
        "drug_class": "drug_class",
        "drugclass": "drug_class",
        "disease": "disease",
        "condition": "disease",
        "symptom": "symptom",
        "sign": "symptom",
        "lab": "lab",
        "biomarker": "lab",
        "vital": "lab",
        "procedure": "procedure",
        "test": "procedure",
        "device": "device",
    }
    return mapping.get(raw_type.lower(), raw_type.lower())


def _validate_strength(raw: str) -> str:
    """Validate and normalize recommendation strength."""
    valid = {v.value for v in RecommendationStrength}
    if raw in valid:
        return raw
    # Legacy format mapping
    legacy = {
        "strong/a": "strong_for",
        "strong": "strong_for",
        "moderate/b": "moderate_for",
        "moderate": "moderate_for",
        "weak/c": "weak_for",
        "weak": "weak_for",
        "expert_opinion": "weak_for",
    }
    return legacy.get(raw.lower(), "moderate_for")


def _validate_evidence_quality(raw: str) -> str:
    """Validate and normalize evidence quality."""
    valid = {v.value for v in EvidenceQuality}
    if raw in valid:
        return raw
    legacy = {
        "a": "high",
        "b-r": "moderate",
        "b-nr": "low",
        "c-ld": "very_low",
        "c-eo": "expert",
        "loe a": "high",
        "loe b": "moderate",
        "loe c": "very_low",
    }
    return legacy.get(raw.lower(), "moderate")


def extract_recommendations(
    chunk_text: str,
    parent_context: str,
    guideline_id: str,
    page: int,
) -> list[ExtractionResult]:
    """Extract typed recommendations from a text chunk using LLM."""
    prompt = EXTRACTION_PROMPT.format(
        chunk_text=chunk_text,
        parent_context=parent_context,
        guideline_id=guideline_id,
        page=page,
    )

    try:
        raw = _call_llm_with_retry(prompt)
    except Exception:
        logger.exception("LLM call failed for chunk in %s", guideline_id)
        return []

    raw = _strip_code_fences(raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("LLM returned invalid JSON for chunk in %s", guideline_id)
        return []

    if not isinstance(data, list):
        return []

    results: list[ExtractionResult] = []
    for item in data:
        try:
            result = _parse_extraction_item(item, guideline_id, page)
            if result is not None:
                results.append(result)
        except Exception:
            logger.warning("Skipping invalid extraction: %s", item)
            continue

    return results


def _parse_extraction_item(
    item: dict, guideline_id: str, page: int
) -> ExtractionResult | None:
    """Parse a single extraction item into an ExtractionResult."""
    rec_type = item.get("type", "")
    if rec_type not in VALID_REC_TYPES:
        logger.warning("Unknown recommendation type: %s", rec_type)
        return None

    # Parse concepts
    concepts = []
    for c in item.get("concepts", []):
        entity_type = _normalize_entity_type(c.get("type", ""))
        if entity_type not in VALID_ENTITY_TYPES:
            logger.warning("Unknown entity type: %s", c.get("type"))
            continue
        concepts.append(
            ConceptRef(
                name=c["name"],
                type=entity_type,
                role=c.get("role", "subject"),
            )
        )

    # Parse relationships
    relationships = []
    for r in item.get("relationships", []):
        relationships.append(
            ExtractedRelationship(
                rel_type=r.get("rel_type", ""),
                source_name=r.get("source_name", ""),
                source_type=_normalize_entity_type(r.get("source_type", "")),
                target_name=r.get("target_name", ""),
                target_type=_normalize_entity_type(r.get("target_type", "")),
                properties=r.get("properties", {}),
            )
        )

    # Parse conditions
    conditions = []
    for c in item.get("conditions", []):
        if "variable" in c and "operator" in c and "threshold" in c:
            conditions.append(c)

    return ExtractionResult(
        rec_id=item.get("id", f"rec_{guideline_id}_{id(item)}"),
        rec_type=rec_type,
        action=item.get("action", ""),
        action_detail=item.get("action_detail", ""),
        strength=_validate_strength(item.get("strength", "moderate_for")),
        evidence_quality=_validate_evidence_quality(
            item.get("evidence_quality", "moderate")
        ),
        conditions=conditions,
        concepts=concepts,
        relationships=relationships,
        guideline_id=guideline_id,
        page=page,
    )

from __future__ import annotations
import json
import logging
import time
from dataclasses import dataclass, field
import anthropic as _anthropic
from open_medicine.graphrag.graph.schema import LogicNode, Condition

logger = logging.getLogger(__name__)


@dataclass
class ConceptRef:
    name: str
    type: str


@dataclass
class ExtractionResult:
    logic_node: LogicNode
    concepts: list[ConceptRef]
    source_chunk_id: str = ""


EXTRACTION_PROMPT = """You are a clinical guideline extraction agent.

Given this text from a medical guideline, Section: {parent_context}:

---
{chunk_text}
---

Extract all clinical rules as a JSON array. Each rule must have:
- "id": unique string (use format "ln_<guideline>_<number>")
- "type": one of "dosing", "contraindication", "interaction", "monitoring", "treatment_selection", "diagnostic_criteria"
- "conditions": array of {{"variable": str, "operator": "<|<=|>|>=|==|!=", "threshold": number|string, "unit": str|null}}
- "action": type-specific action string
- "action_detail": human-readable explanation
- "strength": evidence strength (e.g. "Strong/A", "Moderate/B", "Weak/C", "Expert_Opinion")
- "guideline_id": "{guideline_id}"
- "page": {page}
- "concepts": array of {{"name": entity name, "type": "drug"|"disease"|"lab"|"procedure"|"symptom"}}

If no clinical rules are present, return an empty array [].
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
    for attempt in range(max_retries):
        try:
            return _call_llm(prompt)
        except (_anthropic.RateLimitError, _anthropic.APIConnectionError):
            if attempt == max_retries - 1:
                raise
            time.sleep(base_delay * (2 ** attempt))


def extract_logic_nodes(
    chunk_text: str,
    parent_context: str,
    guideline_id: str,
    page: int,
) -> list[ExtractionResult]:
    """Extract LogicNodes from a text chunk using LLM."""
    prompt = EXTRACTION_PROMPT.format(
        chunk_text=chunk_text,
        parent_context=parent_context,
        guideline_id=guideline_id,
        page=page,
    )

    try:
        raw = _call_llm_with_retry(prompt)
    except Exception:
        logger.exception("LLM call failed")
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("LLM returned invalid JSON")
        return []

    if not isinstance(data, list):
        return []

    results: list[ExtractionResult] = []
    for item in data:
        try:
            concepts = [ConceptRef(c["name"], c["type"]) for c in item.pop("concepts", [])]
            conditions = [Condition(**c) for c in item.get("conditions", [])]
            item["conditions"] = conditions
            logic_node = LogicNode(**item)
            results.append(ExtractionResult(logic_node=logic_node, concepts=concepts))
        except Exception:
            logger.warning("Skipping invalid extraction: %s", item)
            continue

    return results

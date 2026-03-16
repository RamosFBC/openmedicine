"""Extract structured edge properties from action_detail text.

Uses regex-based extraction for common patterns found in clinical guidelines.
Falls back to empty dict when patterns don't match — safe to call on any text.
"""

import re
from typing import Any


def parse_dosing_properties(text: str) -> dict[str, str]:
    """Extract dosing properties from action_detail text."""
    if not text:
        return {}

    props: dict[str, str] = {}

    # Starting/initial dose
    start_match = re.search(
        r"(?:initial|starting|begin(?:ning)?)\s+(?:daily\s+)?dose\s+(?:of\s+)?"
        r"([\d.,\-/]+\s*(?:mg|mcg|g|units?|mL))",
        text,
        re.IGNORECASE,
    )
    if start_match:
        props["starting_dose"] = start_match.group(1).strip()

    # Target dose
    target_match = re.search(
        r"(?:target|goal|optimal)\s+(?:daily\s+)?dose\s+(?:of\s+)?"
        r"([\d.,\-/]+\s*(?:mg|mcg|g|units?|mL))",
        text,
        re.IGNORECASE,
    )
    if target_match:
        props["target_dose"] = target_match.group(1).strip()

    # Maximum dose
    max_match = re.search(
        r"(?:max(?:imum)?|up\s+to)\s+(?:total\s+)?(?:daily\s+)?dose\s+(?:of\s+)?"
        r"([\d.,\-/]+\s*(?:mg|mcg|g|units?|mL))",
        text,
        re.IGNORECASE,
    )
    if max_match:
        props["max_dose"] = max_match.group(1).strip()

    # Frequency
    freq_match = re.search(
        r"((?:once|twice|three times|four times)"
        r"(?:\s+(?:or\s+)?(?:once|twice|three times|four times))*"
        r"\s+(?:daily|per\s+day|a\s+day)"
        r"|every\s+\d+\s*(?:hours?|hrs?|days?))",
        text,
        re.IGNORECASE,
    )
    if freq_match:
        props["frequency"] = freq_match.group(0).strip()

    # Route
    route_match = re.search(
        r"\b(oral(?:ly)?|intravenous(?:ly)?|IV|subcutaneous(?:ly)?|SC|SQ"
        r"|intramuscular(?:ly)?|IM|topical(?:ly)?)\b",
        text,
        re.IGNORECASE,
    )
    if route_match:
        props["route"] = route_match.group(1).strip().lower()

    return props


def parse_monitoring_properties(text: str) -> dict[str, str]:
    """Extract monitoring properties from action_detail text."""
    if not text:
        return {}

    props: dict[str, str] = {}

    # Frequency
    freq_match = re.search(
        r"(?:within|every|at least every|monitor\s+(?:at\s+)?)"
        r"\s*([\d\-]+\s*(?:weeks?|days?|months?|hours?))",
        text,
        re.IGNORECASE,
    )
    if freq_match:
        props["frequency"] = freq_match.group(0).strip()

    # Threshold alert (e.g., K+ > 5.0)
    alert_match = re.search(
        r"(K\+?|potassium|creatinine|eGFR|BNP|INR)"
        r"\s*[>≥<≤]\s*[\d.]+\s*(?:mEq/L|mg/dL|mL/min|pg/mL)?",
        text,
        re.IGNORECASE,
    )
    if alert_match:
        props["threshold_alert"] = alert_match.group(0).strip()

    return props


def parse_interaction_properties(text: str) -> dict[str, str]:
    """Extract interaction properties from action_detail text."""
    if not text:
        return {}

    props: dict[str, str] = {}

    # Mechanism
    mech_match = re.search(
        r"(?:due to|because of|via|through|overlapping)\s+(.+?)(?:\.|;|$)",
        text,
        re.IGNORECASE,
    )
    if mech_match:
        props["mechanism"] = mech_match.group(1).strip()[:100]

    # Clinical effect
    effect_match = re.search(
        r"(?:risk of|may cause|increases?|leading to)\s+(.+?)(?:\.|;|$)",
        text,
        re.IGNORECASE,
    )
    if effect_match:
        props["clinical_effect"] = effect_match.group(1).strip()[:100]

    # Severity
    if any(
        w in text.lower()
        for w in ["avoid", "contraindicated", "never", "must not"]
    ):
        props["severity"] = "MAJOR"
    elif any(
        w in text.lower()
        for w in ["caution", "careful", "monitor closely"]
    ):
        props["severity"] = "MODERATE"
    else:
        props["severity"] = "MINOR"

    return props


def parse_contraindication_properties(text: str) -> dict[str, str]:
    """Extract contraindication properties from action_detail text."""
    if not text:
        return {}

    props: dict[str, str] = {}

    # Severity
    if any(
        w in text.lower()
        for w in ["avoid", "must not", "never", "absolutely", "contraindicated"]
    ):
        props["severity"] = "ABSOLUTE"
    elif any(
        w in text.lower()
        for w in ["caution", "relative", "careful", "weigh", "consider"]
    ):
        props["severity"] = "RELATIVE"

    # Reason
    reason_match = re.search(
        r"(?:because|due to|as it|since|worsen|risk of)\s+(.+?)(?:\.|;|$)",
        text,
        re.IGNORECASE,
    )
    if reason_match:
        props["reason"] = reason_match.group(1).strip()[:150]

    return props


# Map rec_type to parser
PARSERS: dict[str, Any] = {
    "dosing": parse_dosing_properties,
    "monitoring": parse_monitoring_properties,
    "interaction": parse_interaction_properties,
    "contraindication": parse_contraindication_properties,
}

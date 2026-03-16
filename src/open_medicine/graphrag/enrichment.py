"""Extract structured edge properties from action_detail text.

Uses regex-based extraction for common patterns found in clinical guidelines.
Falls back to empty dict when patterns don't match — safe to call on any text.
"""

import re
from typing import Any

# Shared dose unit pattern — order matters: longer units first
# Supports ranges with "-", "/", or "to": "0.125-0.25 mg", "0.125 to 0.25 mg"
_DOSE_UNIT = r"[\d.,\-/]+(?:\s+to\s+[\d.,\-/]+)?\s*(?:mcg/kg/min|mcg/min|mg|mcg|g|units?|mL)"


def parse_dosing_properties(text: str) -> dict[str, str]:
    """Extract dosing properties from action_detail text."""
    if not text:
        return {}

    props: dict[str, str] = {}

    # --- Starting dose ---
    # Priority 1: "start X mg", "initial dose X mg", "initial daily dose X mg"
    start_patterns = [
        # "start 6.25 mg", "start 5-10 mg once daily"
        rf"(?:start(?:ing)?|begin)\s+(?:at\s+)?({_DOSE_UNIT})",
        # "initial dose 6.25 mg", "initial daily dose 0.5-1.0 mg"
        rf"initial\s+(?:and\s+target\s+)?(?:daily\s+)?dose\s+(?:of\s+)?({_DOSE_UNIT})",
        # "starting dose of ... is X mg" / "starting dose is X mg"
        rf"(?:starting|beginning)\s+(?:daily\s+)?dose\s+(?:of\s+\w+\s+(?:and\s+\w+\s+)?)?(?:is\s+)?({_DOSE_UNIT})",
        # "initiated and maintained at 0.125 mg" (digoxin)
        rf"initiated\s+(?:and\s+maintained\s+)?at\s+({_DOSE_UNIT})",
        # "may initiate at 24/26 mg" (sacubitril-valsartan)
        rf"(?:may\s+)?initiate\s+at\s+({_DOSE_UNIT})",
        # Infusion: "infusion 2.5-20 mcg/kg/min", "infusion: 0.5-30 mcg/min"
        rf"infusion[:\s]+({_DOSE_UNIT})",
        # "inotropic dose: 5-10 mcg/kg/min" (Dopamine)
        rf"(?:inotropic|vasopressor|maintenance)\s+dose[:\s]+({_DOSE_UNIT})",
        # "FDA-approved dose is 80 mg" (Tafamidis)
        rf"(?:FDA[- ]approved|recommended)\s+dose\s+(?:is\s+|of\s+)?({_DOSE_UNIT})",
        # Bare dose with drug name: "enoxaparin 40 mg", "heparin 5000 units"
        rf"\b[A-Z][a-z]+(?:aparin|aban|olol|pril|artan|amide|idone|arin|oxin)\s+({_DOSE_UNIT})",
    ]
    for pat in start_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            props["starting_dose"] = m.group(1).strip()
            break

    # Special: "X mg once daily (starting dose equals target dose)" — SGLT2i
    equals_match = re.search(
        rf"({_DOSE_UNIT})\s+(?:once|twice)\s+daily\s*\(starting\s+dose\s+equals\s+target",
        text,
        re.IGNORECASE,
    )
    if equals_match and "starting_dose" not in props:
        props["starting_dose"] = equals_match.group(1).strip()

    # --- Target dose ---
    target_patterns = [
        # "target dose of 50 mg", "target dose 10 mg"
        rf"target\s+(?:daily\s+)?dose\s+(?:of\s+)?({_DOSE_UNIT})",
        # "target dose is 200 mg" (sacubitril-valsartan)
        rf"target\s+(?:daily\s+)?dose\s+is\s+({_DOSE_UNIT})",
        # "titrate to target of 40 mg" (without "dose")
        rf"titrate\s+to\s+(?:target\s+(?:of\s+)?)?({_DOSE_UNIT})",
        # "goal dose of 25 mg"
        rf"(?:goal|optimal)\s+(?:daily\s+)?dose\s+(?:of\s+)?({_DOSE_UNIT})",
        # "target X mg ISDN" or "target of X mg"
        rf"target\s+(?:of\s+)?({_DOSE_UNIT})",
    ]
    for pat in target_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            props["target_dose"] = m.group(1).strip()
            break

    # Special: "starting dose equals target dose" — copy starting_dose
    if "target_dose" not in props and "starting dose equals target" in text.lower():
        if "starting_dose" in props:
            props["target_dose"] = props["starting_dose"]

    # "initial and target dose X mg" — both starting and target
    init_target = re.search(
        rf"initial\s+and\s+target\s+dose\s+(?:of\s+)?({_DOSE_UNIT})",
        text,
        re.IGNORECASE,
    )
    if init_target:
        dose = init_target.group(1).strip()
        if "starting_dose" not in props:
            props["starting_dose"] = dose
        if "target_dose" not in props:
            props["target_dose"] = dose

    # --- Maximum dose ---
    max_patterns = [
        # "maximum total daily dose 10 mg", "maximum daily dose 600 mg"
        rf"max(?:imum)?\s+(?:total\s+)?(?:daily\s+)?dose\s+(?:of\s+)?({_DOSE_UNIT})",
        # "up to 200 mg"
        rf"up\s+to\s+({_DOSE_UNIT})",
    ]
    for pat in max_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            props["max_dose"] = m.group(1).strip()
            break

    # --- Frequency ---
    freq_patterns = [
        # "once daily", "twice daily", "3 times daily", "once or twice daily"
        r"((?:once|twice|\d+\s+times)"
        r"(?:\s+(?:or\s+)?(?:once|twice|\d+\s+times))*"
        r"\s+(?:daily|per\s+day|a\s+day))",
        # "every 8 hours", "every 8 or 12 hours"
        r"(every\s+[\d]+(?:\s+or\s+\d+)?\s*(?:hours?|hrs?|days?))",
        # "every other day"
        r"(every\s+other\s+day)",
        # "BID", "TID", "QD", "QID"
        r"\b(BID|TID|QD|QID)\b",
        # "3 times daily", "3-4 times daily"
        r"(\d+(?:-\d+)?\s+times\s+daily)",
    ]
    for pat in freq_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            props["frequency"] = m.group(1).strip()
            break

    # --- Route ---
    route_match = re.search(
        r"\b(oral(?:ly)?|intravenous(?:ly)?|IV|subcutaneous(?:ly)?|SC|SQ"
        r"|intramuscular(?:ly)?|IM|topical(?:ly)?|infusion)\b",
        text,
        re.IGNORECASE,
    )
    if route_match:
        route = route_match.group(1).strip().lower()
        # Normalize infusion → IV
        if route == "infusion":
            route = "iv"
        props["route"] = route

    return props


def parse_monitoring_properties(text: str) -> dict[str, str]:
    """Extract monitoring properties from action_detail text."""
    if not text:
        return {}

    props: dict[str, str] = {}

    # --- Frequency ---
    freq_patterns = [
        # "approximately 1 week, then 4 weeks, then every 6 months"
        r"(approximately\s+[\d\-]+\s*(?:weeks?|days?|months?),?\s+"
        r"then\s+[\d\-]+\s*(?:weeks?|days?|months?)(?:,?\s+"
        r"then\s+(?:every\s+)?[\d\-]+\s*(?:weeks?|days?|months?))?)",
        # "1 week, then 4 weeks" (schedule pattern)
        r"([\d\-]+\s*(?:week|month)s?,?\s+then\s+[\d\-]+\s*(?:weeks?|months?))",
        # "within 1-2 weeks", "within 7 days"
        r"(within\s+[\d\-]+\s*(?:weeks?|days?|months?|hours?))",
        # "every 6 months", "at least every 3 months"
        r"((?:at\s+least\s+)?every\s+[\d\-]+\s*(?:weeks?|days?|months?|hours?))",
        # "monitor at X weeks"
        r"(monitor\s+(?:at\s+)?[\d\-]+\s*(?:weeks?|days?|months?))",
    ]
    for pat in freq_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            props["frequency"] = m.group(1).strip()
            break

    # --- Threshold alerts (extract ALL thresholds found) ---
    threshold_pattern = re.compile(
        r"((?:K\+?|potassium|creatinine|eGFR|BNP|NT-proBNP|INR"
        r"|serum\s+digoxin(?:\s+concentration)?|troponin)"
        r"(?:\s+(?:level|levels?|concentration))?"
        r"\s*(?:>=?|<=?|≥|≤|>|<)\s*[\d.]+\s*"
        r"(?:mEq/L|mg/dL|mL/min(?:/1\.73\s*m2)?|pg/mL|ng/mL|ng/dL)?)",
        re.IGNORECASE,
    )
    thresholds = threshold_pattern.findall(text)
    if thresholds:
        # Store all thresholds semicolon-separated
        props["threshold_alert"] = "; ".join(t.strip() for t in thresholds)

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
    lower = text.lower()

    # --- Severity ---
    # Angioedema is ALWAYS absolute — special case first
    if "angioedema" in lower:
        props["severity"] = "ABSOLUTE"
    elif any(
        phrase in lower
        for phrase in [
            "avoid",
            "must not",
            "never",
            "absolutely",
            "contraindicated",
            "contraindication",
            "should not be used",
            "should not be administered",
            "are not recommended",
            "is not recommended",
            "not recommended",
            "causes harm",
            "potentially harmful",
            "may be harmful",
            "not indicated",
            "increase the risk of mortality",
            "increased mortality",
            "worsen",
            "exacerbates",
            "has generally failed",
            "no longer qualify",
        ]
    ):
        props["severity"] = "ABSOLUTE"
    elif any(
        phrase in lower
        for phrase in [
            "caution",
            "relative",
            "careful",
            "weigh",
            "consider",
            "not adequate",
            "is ineffective",
            "lacks evidence",
            "toxicity",
        ]
    ):
        props["severity"] = "RELATIVE"

    # --- Reason ---
    reason_patterns = [
        r"(?:because|due to|as it|since|risk of)\s+(.+?)(?:\.|;|$)",
        r"(?:worsen|worsening)\s+(.+?)(?:\.|;|$)",
        r"(?:associated with|causes?|leading to)\s+(.+?)(?:\.|;|$)",
        r"(?:increase[sd]?\s+(?:the\s+)?risk\s+(?:of\s+)?)\s*(.+?)(?:\.|;|$)",
    ]
    for pat in reason_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            props["reason"] = m.group(1).strip()[:150]
            break

    return props


# Map rec_type to parser
PARSERS: dict[str, Any] = {
    "dosing": parse_dosing_properties,
    "monitoring": parse_monitoring_properties,
    "interaction": parse_interaction_properties,
    "contraindication": parse_contraindication_properties,
}

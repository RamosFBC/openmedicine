"""Shared search utilities for tokenized keyword matching with clinical synonyms."""
import re
from typing import Any


# Bidirectional clinical synonym groups.
# Each group is a set of terms that should be treated as equivalent during search.
# When a user searches for any term in a group, all terms in that group are expanded.
_SYNONYM_GROUPS: list[set[str]] = [
    # Renal / Kidney
    {"kidney", "renal", "nephro", "nephrology"},
    # Heart / Cardiac
    {"heart", "cardiac", "cardio", "cardiovascular"},
    # Myocardial infarction
    {"mi", "myocardial infarction", "heart attack", "stemi", "nstemi", "acs", "acute coronary syndrome"},
    # Stroke / Cerebrovascular
    {"stroke", "cerebrovascular", "cva", "ischemic stroke", "tia", "transient ischemic attack"},
    # Liver / Hepatic
    {"liver", "hepatic", "hepatology", "hepato"},
    # Lung / Pulmonary
    {"lung", "pulmonary", "respiratory", "pneumo"},
    # Blood clot / VTE
    {"dvt", "deep vein thrombosis", "pe", "pulmonary embolism", "vte", "venous thromboembolism", "clot", "thrombosis", "embolism"},
    # Bleeding / Hemorrhage
    {"bleeding", "hemorrhage", "haemorrhage", "bleed"},
    # Anticoagulation
    {"anticoagulation", "anticoagulant", "blood thinner", "anticoag"},
    # Atrial fibrillation
    {"afib", "atrial fibrillation", "af", "a-fib"},
    # Infection / Sepsis
    {"sepsis", "infection", "septic", "infectious"},
    # GFR / Creatinine clearance
    {"gfr", "egfr", "glomerular filtration", "creatinine clearance", "crcl"},
    # Blood sugar / Glucose / Diabetes
    {"glucose", "blood sugar", "diabetes", "diabetic", "dm", "hyperglycemia"},
    # Blood pressure / Hypertension
    {"blood pressure", "hypertension", "bp", "htn"},
    # Anxiety
    {"anxiety", "anxious", "gad", "generalized anxiety"},
    # Depression
    {"depression", "depressive", "depressed", "phq"},
    # Pain
    {"pain", "painful", "ache", "nociceptive"},
    # Fracture / Bone
    {"fracture", "bone", "osteoporosis", "osteoporotic", "skeletal"},
    # Burn
    {"burn", "burns", "thermal injury", "tbsa"},
    # Trauma
    {"trauma", "traumatic", "injury"},
    # Pediatric / Child
    {"pediatric", "paediatric", "child", "children", "neonatal", "newborn", "infant"},
    # ICU / Critical care
    {"icu", "critical care", "intensive care"},
    # Alcohol / Ethanol
    {"alcohol", "ethanol", "drinking", "alcoholism"},
    # Opioid
    {"opioid", "opiate", "narcotic"},
    # Cancer / Oncology
    {"cancer", "oncology", "oncologic", "malignancy", "tumor", "tumour", "neoplasm"},
    # Sodium
    {"sodium", "na", "hyponatremia", "hypernatremia"},
    # Calcium
    {"calcium", "ca", "hypocalcemia", "hypercalcemia"},
    # Pancreatitis
    {"pancreatitis", "pancreatic", "pancreas"},
    # Pneumonia
    {"pneumonia", "cap", "community acquired pneumonia"},
    # GI / Gastrointestinal
    {"gi", "gastrointestinal", "gastro", "upper gi", "lower gi"},
    # Delirium / Confusion
    {"delirium", "confusion", "confused", "altered mental status", "ams"},
    # Sedation / Agitation
    {"sedation", "agitation", "agitated", "sedated"},
    # Arthritis / Joint
    {"arthritis", "joint", "rheumatoid", "rheumatology"},
    # Prostate / Urinary
    {"prostate", "bph", "urinary", "urology", "lower urinary tract"},
    # Drug reaction / ADR
    {"drug reaction", "adr", "adverse drug reaction", "adverse event", "pharmacovigilance"},
    # Withdrawal
    {"withdrawal", "detox", "detoxification"},
    # Endocarditis
    {"endocarditis", "ie", "infective endocarditis"},
    # Cervical spine / C-spine
    {"cervical spine", "c-spine", "cspine", "neck injury"},
    # Sleep apnea
    {"sleep apnea", "osa", "obstructive sleep apnea", "sleep"},
    # Necrotizing fasciitis / Soft tissue
    {"necrotizing fasciitis", "nec fasc", "soft tissue infection", "nsti"},
    # Acetaminophen / Paracetamol
    {"acetaminophen", "paracetamol", "tylenol", "apap"},
    # Warfarin / Coumadin
    {"warfarin", "coumadin", "inr"},
    # Heparin / HIT
    {"heparin", "hit", "heparin induced thrombocytopenia"},
    # DIC
    {"dic", "disseminated intravascular coagulation"},
    # Subarachnoid hemorrhage
    {"sah", "subarachnoid hemorrhage", "subarachnoid"},
    # Body mass / Obesity
    {"bmi", "body mass", "obesity", "obese", "overweight"},
    # Body surface area
    {"bsa", "body surface area"},
    # Insulin
    {"insulin", "basal insulin"},
    # COPD
    {"copd", "chronic obstructive", "emphysema", "chronic bronchitis"},
    # Frailty / Geriatrics
    {"frailty", "frail", "geriatric", "geriatrics", "elderly"},
    # Mortality risk / Comorbidity
    {"comorbidity", "comorbid", "charlson", "mortality risk"},
    # Perioperative / Surgery
    {"perioperative", "preoperative", "surgical", "surgery", "noncardiac surgery"},
    # QT interval
    {"qt", "qtc", "qt interval", "long qt", "torsades"},
    # Acid-base
    {"acidosis", "acid-base", "metabolic acidosis", "anion gap"},
    # Osmolality
    {"osmolality", "osmolar", "osmolar gap", "toxic alcohol"},
    # Pharyngitis / Sore throat
    {"pharyngitis", "sore throat", "strep throat", "streptococcal", "tonsillitis"},
    # Ankle / Foot injury
    {"ankle", "ankle injury", "midfoot", "foot injury"},
    # Obstetrics / Labor
    {"obstetric", "obstetrics", "labor", "labour", "cervical", "induction", "bishop"},
    # Fluid / IV
    {"fluid", "iv fluid", "resuscitation", "maintenance fluid", "hydration"},
    # Consciousness / Coma
    {"consciousness", "coma", "gcs", "glasgow coma", "unresponsive", "unconscious"},
    # Early warning / Deterioration
    {"early warning", "deterioration", "clinical deterioration", "news", "mews", "pews"},
    # Febrile neutropenia
    {"febrile neutropenia", "neutropenic fever", "neutropenia"},
    # Dosing / Dose adjustment
    {"dosing", "dose", "dose adjustment", "renal dosing", "drug dosing"},
]


def _build_synonym_index() -> dict[str, set[str]]:
    """Build a lookup: token → set of all synonym tokens in its group."""
    index: dict[str, set[str]] = {}
    for group in _SYNONYM_GROUPS:
        for term in group:
            # Index both full terms and individual words within multi-word terms
            index[term] = group
            for word in term.split():
                if word not in index:
                    index[word] = group
    return index


_SYNONYM_INDEX = _build_synonym_index()


def _expand_query_tokens(query: str) -> set[str]:
    """
    Tokenize and expand a query using clinical synonyms.

    Given "kidney function", returns {"kidney", "function", "renal", "nephro", "nephrology", ...}
    """
    query_lower = query.lower()
    raw_tokens = set(query_lower.split())
    expanded = set(raw_tokens)

    # Try matching multi-word phrases from the query using word boundaries
    for term, group in _SYNONYM_INDEX.items():
        if " " in term and _word_boundary_match(term, query_lower):
            for synonym in group:
                expanded.update(synonym.split())

    # Expand each individual raw token (exact match only, no substring)
    for token in raw_tokens:
        if token in _SYNONYM_INDEX:
            for synonym in _SYNONYM_INDEX[token]:
                expanded.update(synonym.split())

    return expanded


def _word_boundary_match(token: str, text_lower: str) -> bool:
    """Check if token appears as a whole word in text (not as a substring inside another word)."""
    return bool(re.search(r'(?<![a-z])' + re.escape(token) + r'(?![a-z])', text_lower))


def score_match(query: str, searchable_text: str) -> float:
    """
    Score how well a query matches a searchable text using token overlap.

    Returns a score between 0.0 and 1.0 where:
    - 0.0 = no tokens match
    - 1.0 = all query tokens (expanded) match

    The scoring weights:
    - Direct token matches count as 1.0
    - Synonym-expanded matches count as 0.7 (to prefer direct hits)

    Uses word-boundary matching to avoid false positives where short tokens
    (e.g., "af", "na") match as substrings inside longer words.
    """
    query_lower = query.lower()
    raw_tokens = set(query_lower.split())
    expanded_tokens = _expand_query_tokens(query)
    text_lower = searchable_text.lower()

    if not raw_tokens:
        return 0.0

    score = 0.0

    for token in expanded_tokens:
        is_direct = token in raw_tokens
        weight = 1.0 if is_direct else 0.7

        # Use word-boundary matching to prevent false substring matches
        if _word_boundary_match(token, text_lower):
            score += weight

    # Bonus for exact phrase match (the whole query appears as a word-boundary phrase)
    if _word_boundary_match(query_lower, text_lower):
        score += 2.0

    # Normalize by raw token count
    denominator = max(len(raw_tokens), 1)
    return min(score / denominator, 1.0) if denominator > 0 else 0.0


def tokenized_search(
    query: str,
    items: list[dict[str, Any]],
    text_key: str = "searchable_text",
    min_score: float = 0.3,
    max_results: int = 10,
) -> list[dict[str, Any]]:
    """
    Search items using tokenized matching with synonym expansion.

    Args:
        query: User search query.
        items: List of dicts, each with a text field to search against.
        text_key: Key in each item dict containing the searchable text.
        min_score: Minimum score threshold to include in results.
        max_results: Maximum number of results to return.

    Returns:
        Items that match, sorted by relevance score (highest first),
        capped at max_results. Each item gets a '_score' key added.
    """
    if not query.strip():
        return []

    scored = []
    for item in items:
        text = item.get(text_key, "")
        s = score_match(query, text)
        if s >= min_score:
            result = {k: v for k, v in item.items() if k != text_key}
            result["_score"] = round(s, 3)
            scored.append(result)

    scored.sort(key=lambda x: x["_score"], reverse=True)
    return scored[:max_results]

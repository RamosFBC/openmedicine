"""Local terminology database for clinical concept normalization.

JSON mapping files provide validated code-to-name mappings for:
- Drugs (RxNorm, SNOMED, ATC)
- Drug classes (ATC, FDA EPC)
- Diseases (SNOMED, ICD-10, MONDO)
- Labs (LOINC, SNOMED)
- Procedures (SNOMED, CPT)
- Devices (SNOMED, GMDN)
- Symptoms (SNOMED)
- Patient variables (LOINC)
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_DATA_DIR = Path(__file__).parent


@lru_cache(maxsize=16)
def load_terminology(filename: str) -> dict:
    """Load a terminology JSON file by name (e.g. 'drugs')."""
    path = _DATA_DIR / f"{filename}.json"
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def lookup(filename: str, name: str) -> dict | None:
    """Look up a concept by name (case-insensitive) in a terminology file.

    Checks canonical names first, then aliases.
    """
    data = load_terminology(filename)
    key = name.lower()

    # Direct canonical name match
    for canonical, entry in data.items():
        if canonical.lower() == key:
            return entry

    # Alias match
    for _canonical, entry in data.items():
        aliases = entry.get("aliases", [])
        if any(a.lower() == key for a in aliases):
            return entry

    return None


_FILE_TO_TYPE: dict[str, str] = {
    "drugs": "drug",
    "drug_classes": "drug_class",
    "diseases": "disease",
    "labs": "lab",
    "procedures": "procedure",
    "devices": "device",
    "symptoms": "symptom",
}


def fuzzy_match(query: str, max_results: int = 5) -> list[tuple[str, str]]:
    """Find terminology entries matching a query by prefix or substring.

    Returns list of (canonical_name, entity_type) tuples, sorted by match quality:
    prefix matches first, then substring matches.
    """
    q = query.lower()
    prefix_matches: list[tuple[str, str]] = []
    substring_matches: list[tuple[str, str]] = []

    for file_name, entity_type in _FILE_TO_TYPE.items():
        data = load_terminology(file_name)
        for canonical, entry in data.items():
            names = [canonical] + entry.get("aliases", [])
            for name in names:
                nl = name.lower()
                if nl.startswith(q):
                    prefix_matches.append((canonical, entity_type))
                    break
                if q in nl:
                    substring_matches.append((canonical, entity_type))
                    break

    # Deduplicate preserving order
    seen: set[str] = set()
    results: list[tuple[str, str]] = []
    for item in prefix_matches + substring_matches:
        key = f"{item[0]}:{item[1]}"
        if key not in seen:
            seen.add(key)
            results.append(item)

    return results[:max_results]

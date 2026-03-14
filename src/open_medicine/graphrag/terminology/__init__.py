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

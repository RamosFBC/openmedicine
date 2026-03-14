"""Entity linker v2 — Terminology-driven concept resolution.

Resolves extracted entity names to canonical forms with standard codes,
using the JSON terminology database instead of hardcoded dicts.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from open_medicine.graphrag.terminology import lookup

# Maps extractor entity_type strings to terminology file names
_TYPE_TO_FILE: dict[str, str] = {
    "drug": "drugs",
    "drug_class": "drug_classes",
    "disease": "diseases",
    "symptom": "symptoms",
    "lab": "labs",
    "procedure": "procedures",
    "device": "devices",
}

# Maps entity_type to Neo4j label
_TYPE_TO_LABEL: dict[str, str] = {
    "drug": "Drug",
    "drug_class": "DrugClass",
    "disease": "Disease",
    "symptom": "Symptom",
    "lab": "Lab",
    "procedure": "Procedure",
    "device": "Device",
}


@dataclass
class LinkedEntity:
    """Resolved clinical entity with standard codes."""

    canonical_name: str
    entity_type: str  # drug, drug_class, disease, symptom, lab, procedure, device
    node_label: str  # Neo4j label: Drug, DrugClass, Disease, etc.
    node_id: str  # Typed ID: rxnorm:123, snomed:456, loinc:789, etc.
    snomed_code: str | None = None
    loinc_code: str | None = None
    rxnorm_code: str | None = None
    atc_code: str | None = None
    icd10_code: str | None = None
    cpt_code: str | None = None
    gmdn_code: str | None = None
    unit: str | None = None
    reference_range: str | None = None
    aliases: list[str] = field(default_factory=list)


@dataclass
class LinkedVariable:
    """Resolved patient variable with LOINC code and linked lab."""

    canonical_name: str
    var_id: str  # pv:{name}
    loinc_code: str | None
    unit: str
    var_type: str  # continuous, categorical, boolean
    linked_lab: str | None  # Name of linked Lab entity (for MEASURES edge)


def _slugify(name: str) -> str:
    """Create a URL-safe slug from a name."""
    return name.lower().replace(" ", "_").replace("/", "_").replace("-", "_")


def link_entity(name: str, entity_type: str) -> LinkedEntity | None:
    """Resolve a clinical entity name to its canonical form with codes.

    Looks up the entity in the appropriate terminology JSON file.
    Returns None if entity_type is not recognized.
    For unknown entities within a valid type, returns a minimal LinkedEntity
    with a generated ID.
    """
    file_name = _TYPE_TO_FILE.get(entity_type)
    if file_name is None:
        return None

    label = _TYPE_TO_LABEL[entity_type]
    entry = lookup(file_name, name)

    if entry is not None:
        return LinkedEntity(
            canonical_name=_find_canonical_name(file_name, name, entry),
            entity_type=entity_type,
            node_label=label,
            node_id=entry.get("id", f"{entity_type}:{_slugify(name)}"),
            snomed_code=entry.get("snomed_code"),
            loinc_code=entry.get("loinc_code"),
            rxnorm_code=entry.get("rxnorm_code"),
            atc_code=entry.get("atc_code"),
            icd10_code=entry.get("icd10_code"),
            cpt_code=entry.get("cpt_code"),
            gmdn_code=entry.get("gmdn_code"),
            unit=entry.get("unit"),
            reference_range=entry.get("reference_range"),
            aliases=entry.get("aliases", []),
        )

    # Unknown entity — create minimal entry with generated ID
    return LinkedEntity(
        canonical_name=name.strip().title(),
        entity_type=entity_type,
        node_label=label,
        node_id=f"{entity_type}:{_slugify(name)}",
    )


def _find_canonical_name(file_name: str, query: str, entry: dict) -> str:
    """Find the canonical name key that maps to this entry."""
    from open_medicine.graphrag.terminology import load_terminology

    data = load_terminology(file_name)
    key_lower = query.lower()

    # Check canonical names first
    for canonical, e in data.items():
        if e is entry and canonical.lower() != key_lower:
            return canonical
        if e is entry:
            return canonical

    # Fallback: use the query as-is
    return query.strip().title()


def link_variable(name: str) -> LinkedVariable | None:
    """Resolve a patient variable name to its canonical form with LOINC code."""
    entry = lookup("variables", name)
    if entry is None:
        return None

    return LinkedVariable(
        canonical_name=_find_canonical_name("variables", name, entry),
        var_id=entry.get("id", f"pv:{_slugify(name)}"),
        loinc_code=entry.get("loinc_code"),
        unit=entry.get("unit", ""),
        var_type=entry.get("var_type", "continuous"),
        linked_lab=entry.get("linked_lab"),
    )


def get_drug_class_members(class_name: str) -> list[str]:
    """Get member drug names for a drug class (for MEMBER_OF edges)."""
    entry = lookup("drug_classes", class_name)
    if entry is None:
        return []
    return entry.get("member_drugs", [])

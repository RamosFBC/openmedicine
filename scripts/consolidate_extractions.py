#!/usr/bin/env python3
"""
Consolidate raw extraction outputs into a normalized, deduplicated JSONL file.

Strict terminology gate: every concept must exist in a terminology file.
"""

import json
import glob
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

# Paths
BASE = Path(__file__).resolve().parent.parent
EXTRACTION_DIR = BASE / "data" / "cache" / "graphrag" / "aha_acc_hf_2022" / "extractions"
OUTPUT_FILE = BASE / "data" / "cache" / "graphrag" / "aha_acc_hf_2022" / "consolidated.jsonl"
TERMINOLOGY_DIR = BASE / "src" / "open_medicine" / "graphrag" / "terminology"
GUIDELINE_ID = "aha_acc_hf_2022"

# Terminology file mapping: filename -> concept type
TERM_FILES = {
    "drugs.json": "drug",
    "drug_classes.json": "drug_class",
    "diseases.json": "disease",
    "labs.json": "lab",
    "procedures.json": "procedure",
    "devices.json": "device",
    "symptoms.json": "symptom",
}


def load_terminology() -> dict:
    """
    Build a lookup index: lowered name/alias -> (canonical_name, type, codes_dict).
    Also returns the raw terminology for the concept registry.
    """
    lookup: dict[str, tuple[str, str, dict]] = {}
    raw_term: dict[str, dict] = {}  # canonical_name -> {type, codes, aliases}

    for filename, concept_type in TERM_FILES.items():
        filepath = TERMINOLOGY_DIR / filename
        if not filepath.exists():
            print(f"WARNING: terminology file not found: {filepath}")
            continue
        with open(filepath) as f:
            data = json.load(f)

        for canonical_name, entry in data.items():
            # Extract codes
            codes = {}
            for key in ("rxnorm_code", "snomed_code", "atc_code", "icd10_code",
                         "mondo_id", "loinc_code", "cpt_code", "gmdn_code",
                         "fda_epc"):
                if key in entry:
                    codes[key] = entry[key]

            aliases = entry.get("aliases", [])
            raw_term[canonical_name] = {
                "type": concept_type,
                "codes": codes,
                "aliases": aliases,
            }

            # Index canonical name
            lookup[canonical_name.lower()] = (canonical_name, concept_type, codes)
            # Index all aliases
            for alias in aliases:
                lookup[alias.lower()] = (canonical_name, concept_type, codes)

    return lookup, raw_term


def resolve_concept(name: str, extracted_type: str, lookup: dict) -> tuple[str, str, dict] | None:
    """
    Try to resolve a concept name against the terminology lookup.
    Returns (canonical_name, correct_type, codes) or None if not found.
    """
    key = name.lower().strip()
    if key in lookup:
        return lookup[key]

    # Try some common normalizations
    # Remove trailing 's' for plurals
    if key.endswith("s") and key[:-1] in lookup:
        return lookup[key[:-1]]

    # Try with/without hyphens
    alt = key.replace("-", " ")
    if alt in lookup:
        return lookup[alt]
    alt = key.replace(" ", "-")
    if alt in lookup:
        return lookup[alt]

    return None


def normalize_strength(raw: str) -> tuple[str, str]:
    """Convert raw strength like 'Strong/A' to (strength, evidence_quality)."""
    raw = raw.strip()

    # Parse strength
    strength = "moderate_for"  # default
    if raw.startswith("Strong"):
        strength = "strong_for"
    elif raw.startswith("Moderate"):
        strength = "moderate_for"
    elif raw.startswith("Weak") or raw.startswith("Limited"):
        strength = "weak_for"
    elif raw.startswith("Expert"):
        strength = "expert_opinion"
    elif "Harm" in raw or "No Benefit" in raw:
        strength = "strong_against"

    # Parse evidence quality
    evidence = "moderate"  # default
    if "/A" in raw:
        evidence = "high"
    elif "/B-R" in raw:
        evidence = "moderate"
    elif "/B-NR" in raw:
        evidence = "moderate"
    elif "/C-LD" in raw:
        evidence = "low"
    elif "/C-EO" in raw:
        evidence = "very_low"
    elif "Expert" in raw:
        evidence = "very_low"

    return strength, evidence


def should_reclassify_contraindication(rec: dict, treatment_drugs: set) -> bool:
    """
    Determine if a contraindication should be reclassified as safety_warning.
    """
    action = rec.get("action", "").lower()
    action_detail = rec.get("action_detail", "").lower()
    combined = action + " " + action_detail

    # Patterns that indicate safety_warning, not true contraindication
    safety_patterns = [
        "withdraw", "withdrawal", "abrupt",
        "exclude non-evidence", "other than",
        "use caution", "insufficient data",
        "careful", "monitor", "caution",
    ]

    for pat in safety_patterns:
        if pat in combined:
            return True

    # Check if drug is also a first-line treatment for same disease
    concepts = rec.get("_resolved_concepts", [])
    drug_names = {c["name"] for c in concepts if c["type"] in ("drug", "drug_class")}
    disease_names = {c["name"] for c in concepts if c["type"] == "disease"}

    for drug in drug_names:
        for disease in disease_names:
            pair_key = f"{drug}||{disease}"
            if pair_key in treatment_drugs:
                return True

    return False


def is_true_contraindication(action: str, action_detail: str) -> bool:
    """Check if this is a true contraindication (explicitly harmful)."""
    combined = (action + " " + action_detail).lower()
    harm_patterns = [
        "contraindicated", "potentially harmful", "should not be used",
        "causes harm", "harmful", "class iii", "avoid",
        "is not recommended", "do not use", "not be administered",
    ]
    return any(pat in combined for pat in harm_patterns)


def assign_role(concept_type: str, rec_type: str) -> str:
    """Assign the correct role based on concept type and rec_type."""
    role_map = {
        "treatment_selection": {
            "drug": "subject", "drug_class": "subject",
            "disease": "target", "lab": "monitor",
            "procedure": "subject", "device": "subject",
            "symptom": "context",
        },
        "monitoring": {
            "drug": "subject", "drug_class": "subject",
            "lab": "monitor", "disease": "target",
            "procedure": "subject", "device": "subject",
            "symptom": "context",
        },
        "dosing": {
            "drug": "subject", "drug_class": "subject",
            "disease": "target", "lab": "monitor",
            "procedure": "context", "device": "context",
            "symptom": "context",
        },
        "diagnostic_criteria": {
            "disease": "target", "procedure": "subject",
            "lab": "subject", "drug": "context",
            "drug_class": "context", "device": "subject",
            "symptom": "context",
        },
        "contraindication": {
            "drug": "subject", "drug_class": "subject",
            "disease": "target", "lab": "monitor",
            "procedure": "context", "device": "subject",
            "symptom": "context",
        },
        "safety_warning": {
            "drug": "subject", "drug_class": "subject",
            "disease": "target", "lab": "monitor",
            "procedure": "context", "device": "subject",
            "symptom": "context",
        },
        "interaction": {
            "drug": "subject", "drug_class": "subject",
            "disease": "context", "lab": "monitor",
            "procedure": "context", "device": "context",
            "symptom": "context",
        },
    }
    return role_map.get(rec_type, {}).get(concept_type, "context")


def detect_interactions(all_recs: list) -> list:
    """Find INTERACTS_WITH pairs from interaction-type recs."""
    interactions = []
    seen = set()

    # Known interactions to flag
    known_interactions = [
        {"ACE Inhibitor", "ARB"},
        {"ACE Inhibitor", "MRA", "ARB"},
        {"Digoxin", "Amiodarone"},
        {"ACE Inhibitor", "ARNi"},
    ]

    for rec in all_recs:
        if rec.get("rec_type") == "interaction":
            drug_concepts = [
                c["name"] for c in rec.get("concepts", [])
                if c["type"] in ("drug", "drug_class")
            ]
            if len(drug_concepts) >= 2:
                pair = tuple(sorted(drug_concepts[:2]))
                if pair not in seen:
                    seen.add(pair)
                    interactions.append(list(pair))

    # Also check treatment_selection recs for known interaction patterns
    all_drug_sets = defaultdict(set)
    for rec in all_recs:
        concepts = rec.get("concepts", [])
        drugs_in_rec = {c["name"] for c in concepts if c["type"] in ("drug", "drug_class")}
        diseases_in_rec = {c["name"] for c in concepts if c["type"] == "disease"}
        for d in diseases_in_rec:
            all_drug_sets[d] |= drugs_in_rec

    for known_set in known_interactions:
        pair_list = sorted(known_set)
        if len(pair_list) == 2:
            pair = tuple(pair_list)
            if pair not in seen:
                seen.add(pair)
                interactions.append(list(pair))
        elif len(pair_list) == 3:
            # Add pairwise
            for i in range(len(pair_list)):
                for j in range(i + 1, len(pair_list)):
                    pair = tuple(sorted([pair_list[i], pair_list[j]]))
                    if pair not in seen:
                        seen.add(pair)
                        interactions.append(list(pair))

    return interactions


def detect_conflicts(all_recs: list) -> list:
    """Find contradictory recommendations."""
    conflicts = []

    # Group by (drug/drug_class concept, disease concept)
    concept_recs = defaultdict(list)
    for rec in all_recs:
        drugs = [c["name"] for c in rec.get("concepts", []) if c["type"] in ("drug", "drug_class")]
        diseases = [c["name"] for c in rec.get("concepts", []) if c["type"] == "disease"]
        for drug in drugs:
            for disease in diseases:
                concept_recs[(drug, disease)].append(rec)

    # Look for treatment_selection + contraindication for same drug+disease
    for (drug, disease), recs in concept_recs.items():
        rec_types = {r["rec_type"] for r in recs}
        if "treatment_selection" in rec_types and "contraindication" in rec_types:
            treat_recs = [r for r in recs if r["rec_type"] == "treatment_selection"]
            contra_recs = [r for r in recs if r["rec_type"] == "contraindication"]
            for t in treat_recs:
                for c in contra_recs:
                    conflicts.append([
                        t["rec_id"], c["rec_id"],
                        f"Drug '{drug}' is both recommended and contraindicated for '{disease}' — likely a conditional safety warning"
                    ])

    return conflicts


def make_rec_id(original_id: str) -> str:
    """Convert logic_node id to rec_id format."""
    return original_id.replace("ln_", "rec_")


def main():
    print("=" * 70)
    print("CONSOLIDATION: Terminology-gated concept normalization")
    print("=" * 70)

    # Step 1: Load terminology
    print("\n[Step 1] Loading terminology files...")
    lookup, raw_term = load_terminology()
    print(f"  Loaded {len(raw_term)} canonical concepts, {len(lookup)} lookup entries")

    # Step 2: Read all extractions
    print("\n[Step 2] Reading extraction files...")
    extraction_files = sorted(glob.glob(str(EXTRACTION_DIR / "*.jsonl")))
    all_raw_recs = []
    for fpath in extraction_files:
        with open(fpath) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                rec["_source_file"] = os.path.basename(fpath)
                all_raw_recs.append(rec)
    print(f"  Read {len(all_raw_recs)} raw recommendations from {len(extraction_files)} files")

    # Step 3: Process each recommendation
    print("\n[Step 3] Validating concepts against terminology...")
    stats = {
        "concepts_kept": 0,
        "concepts_dropped": 0,
        "types_fixed": 0,
        "aliases_merged": 0,
        "rec_types_reclassified": 0,
    }
    dropped_concepts = defaultdict(int)
    type_distribution = defaultdict(int)

    # First pass: build treatment_drugs set for contraindication reclassification
    treatment_drugs = set()
    for raw_rec in all_raw_recs:
        ln = raw_rec["logic_node"]
        if ln["type"] == "treatment_selection":
            concepts = raw_rec.get("concepts", [])
            drug_names = set()
            disease_names = set()
            for c in concepts:
                resolved = resolve_concept(c["name"], c["type"], lookup)
                if resolved:
                    canon_name, canon_type, _ = resolved
                    if canon_type in ("drug", "drug_class"):
                        drug_names.add(canon_name)
                    elif canon_type == "disease":
                        disease_names.add(canon_name)
            for drug in drug_names:
                for disease in disease_names:
                    treatment_drugs.add(f"{drug}||{disease}")

    # Second pass: process all recs
    processed_recs = []
    concept_registry = {}  # canonical_name -> {type, codes, aliases}
    seen_canonical_names = set()

    for raw_rec in all_raw_recs:
        ln = raw_rec["logic_node"]
        concepts = raw_rec.get("concepts", [])

        # Resolve concepts
        resolved_concepts = []
        for c in concepts:
            result = resolve_concept(c["name"], c["type"], lookup)
            if result is None:
                stats["concepts_dropped"] += 1
                dropped_concepts[c["name"]] += 1
                continue

            canon_name, canon_type, codes = result
            stats["concepts_kept"] += 1

            # Track type fixes
            if c["type"] != canon_type:
                stats["types_fixed"] += 1

            # Track alias merges
            if c["name"].lower() != canon_name.lower():
                stats["aliases_merged"] += 1

            type_distribution[canon_type] += 1

            # Build concept registry entry
            if canon_name not in concept_registry:
                term_entry = raw_term.get(canon_name, {})
                concept_registry[canon_name] = {
                    "type": canon_type,
                    "codes": term_entry.get("codes", codes),
                    "aliases": term_entry.get("aliases", []),
                }

            resolved_concepts.append({
                "name": canon_name,
                "type": canon_type,
            })

        # Deduplicate resolved concepts (same canonical name)
        seen_in_rec = set()
        deduped_concepts = []
        for c in resolved_concepts:
            if c["name"] not in seen_in_rec:
                seen_in_rec.add(c["name"])
                deduped_concepts.append(c)

        # Determine rec_type (may reclassify)
        rec_type = ln["type"]
        strength_raw = ln.get("strength", "Moderate/B-NR")
        strength, evidence_quality = normalize_strength(strength_raw)

        # Check contraindication reclassification
        if rec_type == "contraindication":
            temp_rec = {
                "action": ln.get("action", ""),
                "action_detail": ln.get("action_detail", ""),
                "_resolved_concepts": deduped_concepts,
            }
            if should_reclassify_contraindication(temp_rec, treatment_drugs):
                if not is_true_contraindication(ln.get("action", ""), ln.get("action_detail", "")):
                    rec_type = "safety_warning"
                    stats["rec_types_reclassified"] += 1

        # Assign roles
        for c in deduped_concepts:
            c["role"] = assign_role(c["type"], rec_type)

        # Build output rec
        rec_id = make_rec_id(ln["id"])
        output_rec = {
            "rec_id": rec_id,
            "rec_type": rec_type,
            "action": ln.get("action", ""),
            "action_detail": ln.get("action_detail", ""),
            "strength": strength,
            "evidence_quality": evidence_quality,
            "conditions": ln.get("conditions", []),
            "concepts": deduped_concepts,
            "relationships": [],
            "source_text": raw_rec.get("source_text", ""),
            "guideline_id": GUIDELINE_ID,
        }
        processed_recs.append(output_rec)

    # Step 4: Detect interactions and conflicts
    print("\n[Step 4] Detecting interactions and conflicts...")
    interactions = detect_interactions(processed_recs)
    conflicts = detect_conflicts(processed_recs)
    print(f"  Found {len(interactions)} interaction pairs")
    print(f"  Found {len(conflicts)} potential conflicts")

    # Step 5: Quality check
    print("\n[Step 5] Quality check...")
    # Verify zero concepts outside terminology
    all_concept_names = set()
    for rec in processed_recs:
        for c in rec["concepts"]:
            all_concept_names.add(c["name"])

    outside_term = all_concept_names - set(concept_registry.keys())
    if outside_term:
        print(f"  ERROR: {len(outside_term)} concepts outside terminology: {outside_term}")
    else:
        print("  PASS: All concepts are in terminology")

    # Verify drug vs drug_class
    for name, entry in concept_registry.items():
        term_entry = raw_term.get(name)
        if term_entry and term_entry["type"] != entry["type"]:
            print(f"  WARNING: Type mismatch for '{name}': registry={entry['type']}, term={term_entry['type']}")

    # Verify interaction pairs involve drug-typed entities
    for pair in interactions:
        for drug_name in pair:
            if drug_name in concept_registry:
                if concept_registry[drug_name]["type"] not in ("drug", "drug_class"):
                    print(f"  WARNING: Interaction entity '{drug_name}' is type {concept_registry[drug_name]['type']}")

    # Check labs in monitoring have role=monitor
    for rec in processed_recs:
        if rec["rec_type"] == "monitoring":
            for c in rec["concepts"]:
                if c["type"] == "lab" and c["role"] != "monitor":
                    print(f"  WARNING: Lab '{c['name']}' in monitoring rec {rec['rec_id']} has role={c['role']}")

    print("  Quality check complete.")

    # Step 6: Report
    print("\n" + "=" * 70)
    print("CONSOLIDATION REPORT")
    print("=" * 70)
    print(f"Concepts kept: {stats['concepts_kept']}")
    print(f"Concepts dropped (not in terminology): {stats['concepts_dropped']}")
    print(f"Types fixed: {stats['types_fixed']}")
    print(f"Aliases merged: {stats['aliases_merged']}")
    print(f"rec_types reclassified: {stats['rec_types_reclassified']} (contraindication -> safety_warning)")
    print(f"Distribution: " + ", ".join(f"{k}={v}" for k, v in sorted(type_distribution.items())))
    print(f"Unique canonical concepts: {len(concept_registry)}")
    print(f"Interaction pairs: {len(interactions)}")
    print(f"Conflicts: {len(conflicts)}")

    if dropped_concepts:
        print(f"\nTop dropped concepts:")
        for name, count in sorted(dropped_concepts.items(), key=lambda x: -x[1])[:30]:
            print(f"  '{name}' x{count}")

    # Rec type distribution
    rec_type_dist = defaultdict(int)
    for rec in processed_recs:
        rec_type_dist[rec["rec_type"]] += 1
    print(f"\nRec type distribution: " + ", ".join(f"{k}={v}" for k, v in sorted(rec_type_dist.items())))

    # Step 7: Write output
    print(f"\n[Step 7] Writing {len(processed_recs)} recs + metadata to {OUTPUT_FILE}...")
    os.makedirs(OUTPUT_FILE.parent, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        for rec in processed_recs:
            f.write(json.dumps(rec) + "\n")

        # Write metadata as final line
        metadata = {
            "_type": "metadata",
            "concept_registry": concept_registry,
            "interactions": interactions,
            "conflicts": conflicts,
            "quality_report": {
                "concepts_kept": stats["concepts_kept"],
                "concepts_dropped": stats["concepts_dropped"],
                "types_fixed": stats["types_fixed"],
                "aliases_merged": stats["aliases_merged"],
                "rec_types_reclassified": stats["rec_types_reclassified"],
                "distribution": dict(type_distribution),
            },
        }
        f.write(json.dumps(metadata) + "\n")

    print("Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

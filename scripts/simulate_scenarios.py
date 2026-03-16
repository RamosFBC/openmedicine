"""Simulate clinical agent scenarios against live Neo4j graph.

Run: source .env && uv run python scripts/simulate_scenarios.py
"""
from __future__ import annotations
import logging, os, sys

logging.getLogger("neo4j").setLevel(logging.ERROR)
os.environ.pop("VOYAGE_API_KEY", None)

from open_medicine.graphrag.graph.connection import GraphConnection
from open_medicine.graphrag.reasoning.engine_v2 import ReasoningEngine
from open_medicine.graphrag.reasoning.types_v2 import ClinicalQuery

def p(s=""): print(s, flush=True)

def main():
    uri = os.environ.get("GRAPHRAG_NEO4J_URI", "").replace("neo4j+s://", "neo4j+ssc://")
    pw = os.environ.get("GRAPHRAG_NEO4J_PASSWORD", "")
    if not pw: p("ERROR: Set GRAPHRAG_NEO4J_PASSWORD"); sys.exit(1)
    conn = GraphConnection(uri, os.environ.get("GRAPHRAG_NEO4J_USER", "neo4j"), pw)
    engine = ReasoningEngine(conn)

    S = [
        ("HFrEF treatments", "treatment_selection", ["HFrEF"], {"LVEF": 25, "eGFR": 55, "potassium": 4.2, "SBP": 105}, True),
        ("HFrEF tx (LVEF 55)", "treatment_selection", ["HFrEF"], {"LVEF": 55}, True),
        ("ACEi contraindications", "contraindication", ["ACE Inhibitor"], {"pregnancy": True}, True),
        ("Sacubitril/Valsartan dosing", "dosing", ["Sacubitril/Valsartan"], {"eGFR": 55}, True),
        ("Warfarin monitoring", "monitoring", ["Warfarin"], {}, True),
        ("HF diagnostic criteria", "diagnostic_criteria", ["Heart Failure"], {}, True),
        ("Digoxin interactions", "interaction", ["Digoxin"], {}, False),
        ("Warfarin interactions", "interaction", ["Warfarin"], {}, True),
        ("ACEi interactions", "interaction", ["ACE Inhibitor"], {}, True),
        ("Metformin CI (eGFR 20)", "contraindication", ["Metformin"], {"eGFR": 20}, True),
        ("Spironolactone CI", "contraindication", ["Spironolactone"], {"potassium": 5.8}, True),
        ("SGLT2i treatments", "treatment_selection", ["SGLT2 Inhibitor"], {"LVEF": 30}, True),
        ("Empagliflozin dosing", "dosing", ["Empagliflozin"], {"eGFR": 45}, True),
        ("Beta Blocker HFrEF", "treatment_selection", ["Beta Blocker"], {"LVEF": 30}, True),
        ("Carvedilol dosing", "dosing", ["Carvedilol"], {}, True),
        ("Unknown drug", "interaction", ["Xylophonazine"], {}, False),
        ("Empty concepts", "treatment_selection", [], {}, False),
        ("HF prevention", "prevention", ["Heart Failure"], {}, False),
    ]

    p(f"\n{'='*78}")
    p(f"  CLINICAL SIMULATION — {len(S)} queries (vector fallback OFF)")
    p(f"{'='*78}\n")

    issues = []
    for i, (name, intent, concepts, pvars, expect) in enumerate(S, 1):
        p(f"  [{i:02d}] running: {name}...")
        try:
            r = engine.query(ClinicalQuery(
                intent=intent, concepts=concepts, patient_vars=pvars,
                include_evidence=False,
            ))
        except Exception as e:
            p(f"       ❌ EXCEPTION: {type(e).__name__}: {e}\n")
            issues.append((name, f"EXCEPTION: {e}"))
            continue

        ns, nr = len(r.semantic_matches), len(r.recommendation_matches)
        has = ns > 0 or nr > 0
        if has and expect: icon = "✅"
        elif not has and not expect: icon = "⚪"
        elif has and not expect: icon = "🟢"
        else:
            icon = "⚠️ "
            issues.append((name, f"No results (cov={r.data_coverage})"))

        flags = []
        if r.confidence == "high" and r.retrieval_layers_used == ["vector"]:
            flags.append("HIGH_CONF_VECTOR_ONLY")
            issues.append((name, "High conf from vector-only"))

        unmet = sum(1 for m in r.semantic_matches if m.conditions_met is False)
        unc = sum(1 for m in r.semantic_matches if m.conditions_met is None)

        p(f"       {icon} sem={ns} rec={nr} conf={r.confidence} cov={r.data_coverage} layers={r.retrieval_layers_used}")
        if unmet: p(f"       ⛔ {unmet} conditions_met=False")
        if unc: p(f"       ❓ {unc} conditions_met=None")
        if r.missing_variables: p(f"       📋 missing={r.missing_variables}")
        if r.hints: p(f"       💡 hints={r.hints}")
        if flags: p(f"       🚩 {', '.join(flags)}")
        for j, m in enumerate(r.semantic_matches[:3]):
            cm = "✅" if m.conditions_met is True else ("❓" if m.conditions_met is None else "⛔")
            p(f"         [{j+1}] {m.entity_name} ({m.edge_type}) str={m.strength} eq={m.evidence_quality} {cm}")
        for j, rc in enumerate(r.recommendation_matches[:2]):
            p(f"         rec[{j+1}] {rc.action} str={rc.strength}")
        p()

    p(f"{'='*78}")
    if issues:
        p(f"  ⚠️  {len(issues)} issue(s):")
        for n, d in issues: p(f"    - {n}: {d}")
    else:
        p(f"  ✅ All {len(S)} scenarios clean.")
    p(f"{'='*78}\n")
    conn.close()

if __name__ == "__main__":
    main()

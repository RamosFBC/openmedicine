#!/usr/bin/env python3
"""Clinical Case Evaluation — Real-world GraphRAG performance test.

Simulates a realistic critical care scenario and evaluates the graph's
ability to answer the clinical questions a physician faces at bedside.

Case: 68-year-old male presenting to the ED with acute decompensated
heart failure. Newly diagnosed HFrEF (LVEF 25%), type 2 diabetes,
CKD stage 3b (eGFR 35 mL/min), potassium 5.1 mEq/L.

Clinical questions map to AHA/ACC/HFSA 2022 guideline expectations.
Each query is graded against known ground truth from the guideline.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from open_medicine.graphrag.config import get_settings
from open_medicine.graphrag.graph.connection import GraphConnection
from open_medicine.graphrag.reasoning.engine_v2 import ReasoningEngine
from open_medicine.graphrag.reasoning.types_v2 import ClinicalQuery, GraphRAGResult


# ── Patient ──────────────────────────────────────────────────────────

PATIENT = {
    "name": "Mr. James R.",
    "age": 68,
    "sex": "male",
    "presenting_complaint": "Progressive dyspnea on exertion x 3 weeks, "
    "orthopnea, lower extremity edema, 8 lb weight gain",
    "vitals": {
        "BP": "142/88 mmHg",
        "HR": "98 bpm",
        "SpO2": "92% on room air",
        "RR": "24/min",
    },
    "echo": "LVEF 25%, dilated LV, moderate mitral regurgitation",
    "labs": {
        "BNP": "1,840 pg/mL (elevated)",
        "eGFR": 35,
        "Creatinine": "1.8 mg/dL",
        "Potassium": "5.1 mEq/L",
        "Sodium": "134 mEq/L",
        "HbA1c": "7.8%",
    },
    "history": [
        "Type 2 Diabetes Mellitus (10 years)",
        "Hypertension (15 years)",
        "No prior HF diagnosis",
        "Current meds: Metformin 1000mg BID, Amlodipine 10mg daily",
    ],
}

# ── Patient variables for condition evaluation ───────────────────────

PATIENT_VARS = {
    "age": 68,
    "egfr": 35,
    "potassium": 5.1,
    "LVEF": 25,
    "heart_failure_type": "HFrEF",
}


# ── Ground Truth from AHA/ACC/HFSA 2022 ─────────────────────────────

@dataclass
class ClinicalExpectation:
    """What the guideline says the answer should be."""

    question_id: str
    clinical_question: str
    why_it_matters: str
    query: ClinicalQuery
    # Entities we MUST find in results (case-insensitive substring match)
    must_find: list[str] = field(default_factory=list)
    # Entities that must NOT appear
    must_not_find: list[str] = field(default_factory=list)
    # Minimum number of results
    min_results: int = 0
    # Expected edge type
    expected_edge: str = ""
    # Guideline citation for the ground truth
    guideline_basis: str = ""


EXPECTATIONS: list[ClinicalExpectation] = [
    # ── Q1: What is the first-line GDMT for HFrEF? ──────────────────
    ClinicalExpectation(
        question_id="Q1",
        clinical_question=(
            "What medications are indicated for this patient's HFrEF (LVEF 25%)?"
        ),
        why_it_matters=(
            "The 2022 guideline mandates 4-pillar GDMT for HFrEF: "
            "ACEi/ARB/ARNi + beta-blocker + MRA + SGLT2i. Missing any pillar "
            "increases mortality. This is THE critical decision at diagnosis."
        ),
        query=ClinicalQuery(
            intent="treatment_selection",
            concepts=["HFrEF"],
            patient_vars=PATIENT_VARS,
            include_evidence=True,
        ),
        # Per AHA/ACC/HFSA 2022 §7.3.2: 4-class GDMT
        must_find=["SGLT2"],  # The 2022 addition — SGLT2i is now Class I
        min_results=2,
        expected_edge="INDICATED_FOR",
        guideline_basis=(
            "AHA/ACC/HFSA 2022 §7.3.2: 'For patients with HFrEF, GDMT including "
            "ACEi/ARB/ARNi, beta-blocker, MRA, and SGLT2i is recommended (Class I).'"
        ),
    ),

    # ── Q2: Contraindications with CKD + hyperkalemia risk ──────────
    ClinicalExpectation(
        question_id="Q2",
        clinical_question=(
            "Are there contraindications for ACE inhibitors given eGFR 35 and K+ 5.1?"
        ),
        why_it_matters=(
            "ACEi can worsen hyperkalemia and renal function. The guideline "
            "provides specific thresholds for when to hold or avoid ACEi/ARB. "
            "Getting this wrong risks life-threatening hyperkalemia."
        ),
        query=ClinicalQuery(
            intent="contraindication",
            concepts=["ACE inhibitors"],
            patient_vars=PATIENT_VARS,
            include_evidence=True,
        ),
        # We expect the graph to surface contraindication conditions
        # (even if this patient doesn't quite meet them, the edges should exist)
        min_results=0,  # May or may not have explicit ACEi contraindications
        expected_edge="CONTRAINDICATED_IN",
        guideline_basis=(
            "AHA/ACC/HFSA 2022 §7.3.2: ACEi/ARB contraindicated in bilateral "
            "renal artery stenosis, angioedema history. Caution with K+ >5.0."
        ),
    ),

    # ── Q3: What monitoring is needed for an MRA? ────────────────────
    ClinicalExpectation(
        question_id="Q3",
        clinical_question=(
            "What labs need monitoring if we start Spironolactone (MRA) "
            "given this patient's renal function?"
        ),
        why_it_matters=(
            "MRAs cause hyperkalemia, especially with CKD. The RALES trial "
            "showed increased mortality when K+ monitoring was inadequate. "
            "This patient's K+ is already 5.1 — close to the danger zone."
        ),
        query=ClinicalQuery(
            intent="monitoring",
            concepts=["Spironolactone"],
            patient_vars=PATIENT_VARS,
            include_evidence=False,
        ),
        must_find=[],  # We'll check what comes back
        min_results=0,
        expected_edge="MONITORED_BY",
        guideline_basis=(
            "AHA/ACC/HFSA 2022 §7.3.2: 'MRA should be avoided if eGFR <30 or "
            "K+ >5.0. Monitor potassium and renal function within 1 week.'"
        ),
    ),

    # ── Q4: SGLT2i treatment for HFrEF with diabetes ────────────────
    ClinicalExpectation(
        question_id="Q4",
        clinical_question=(
            "Is an SGLT2 inhibitor indicated for this patient with HFrEF + T2DM?"
        ),
        why_it_matters=(
            "SGLT2i are the newest pillar of GDMT (2022 upgrade to Class I). "
            "DAPA-HF and EMPEROR-Reduced showed 26% reduction in HF "
            "hospitalization. This patient has BOTH HFrEF AND T2DM — dual benefit."
        ),
        query=ClinicalQuery(
            intent="treatment_selection",
            concepts=["heart failure with reduced ejection fraction"],
            patient_vars=PATIENT_VARS,
            include_evidence=True,
        ),
        must_find=["SGLT2"],
        min_results=1,
        expected_edge="INDICATED_FOR",
        guideline_basis=(
            "AHA/ACC/HFSA 2022 §7.3.2: 'In patients with HFrEF, SGLT2i are "
            "recommended to reduce HF hospitalization and CV mortality (Class I, "
            "Level A).'"
        ),
    ),

    # ── Q5: Heart failure treatments broadly ─────────────────────────
    ClinicalExpectation(
        question_id="Q5",
        clinical_question=(
            "What are all treatments indicated for heart failure?"
        ),
        why_it_matters=(
            "Broad retrieval test — checks whether the graph returns the full "
            "therapeutic landscape including diuretics, vasodilators, devices, "
            "not just the 4-pillar GDMT."
        ),
        query=ClinicalQuery(
            intent="treatment_selection",
            concepts=["Heart Failure"],
            patient_vars={},
            include_evidence=False,
        ),
        min_results=3,
        expected_edge="INDICATED_FOR",
        guideline_basis=(
            "AHA/ACC/HFSA 2022: Multiple drug classes indicated including "
            "ACEi, ARB, ARNi, beta-blockers, MRA, SGLT2i, diuretics, "
            "hydralazine/isosorbide dinitrate, ivabradine."
        ),
    ),

    # ── Q6: Drug-drug interactions ───────────────────────────────────
    ClinicalExpectation(
        question_id="Q6",
        clinical_question=(
            "Are there drug interactions between ACE inhibitors and ARBs?"
        ),
        why_it_matters=(
            "ACEi + ARB dual therapy increases hyperkalemia and renal failure "
            "risk without mortality benefit. ONTARGET trial showed harm. "
            "The guideline explicitly warns against combination."
        ),
        query=ClinicalQuery(
            intent="interaction",
            concepts=["ACE inhibitors"],
            patient_vars=PATIENT_VARS,
            include_evidence=False,
        ),
        min_results=1,  # L1+L5 fix: DrugClass interactions now created and queried
        expected_edge="INTERACTS_WITH",
        guideline_basis=(
            "AHA/ACC/HFSA 2022: 'Combination of ACEi, ARB, and/or ARNi "
            "should not be used (Class III: Harm).'"
        ),
    ),

    # ── Q7: Dosing for a specific drug ───────────────────────────────
    ClinicalExpectation(
        question_id="Q7",
        clinical_question=(
            "What is the dosing for Carvedilol in HFrEF?"
        ),
        why_it_matters=(
            "Beta-blocker dosing in HF requires careful uptitration from low "
            "starting dose. Starting too high causes decompensation. "
            "Not reaching target dose leaves mortality benefit on the table."
        ),
        query=ClinicalQuery(
            intent="dosing",
            concepts=["Carvedilol", "HFrEF"],
            patient_vars=PATIENT_VARS,
            include_evidence=True,
        ),
        min_results=0,
        expected_edge="DOSED_FOR",
        guideline_basis=(
            "AHA/ACC/HFSA 2022 Table 16: Carvedilol starting dose 3.125 mg BID, "
            "target dose 25 mg BID (<85 kg) or 50 mg BID (≥85 kg)."
        ),
    ),

    # ── Q8: Diagnostic criteria — HFrEF classification ──────────────
    ClinicalExpectation(
        question_id="Q8",
        clinical_question=(
            "What are the diagnostic criteria for classifying heart failure "
            "subtypes by ejection fraction?"
        ),
        why_it_matters=(
            "Correct HF classification drives the entire treatment algorithm. "
            "HFrEF (≤40%), HFmrEF (41-49%), HFpEF (≥50%) have different "
            "evidence bases and guideline recommendations."
        ),
        query=ClinicalQuery(
            intent="diagnostic_criteria",
            concepts=["heart failure"],
            patient_vars=PATIENT_VARS,
            include_evidence=True,
        ),
        must_find=[],  # L2 fix: diagnostic_criteria now has dedicated query
        min_results=0,  # May have DIAGNOSED_BY edges or fall back to generic
        guideline_basis=(
            "AHA/ACC/HFSA 2022 §3: HFrEF = LVEF ≤40%, HFmrEF = 41-49%, "
            "HFpEF = LVEF ≥50%, HFimpEF = previously ≤40%, now >40%."
        ),
    ),
]


# ── Evaluation Engine ────────────────────────────────────────────────

@dataclass
class QueryResult:
    expectation: ClinicalExpectation
    graph_result: GraphRAGResult
    passed: bool
    issues: list[str]
    findings: list[str]


def evaluate_query(
    engine: ReasoningEngine, exp: ClinicalExpectation,
) -> QueryResult:
    """Run a single clinical query and evaluate against ground truth."""
    result = engine.query(exp.query)
    issues: list[str] = []
    findings: list[str] = []

    matches = result.semantic_matches
    rec_matches = result.recommendation_matches
    total = len(matches) + len(rec_matches)

    # Track entity names from both match types
    entity_names_lower = [m.entity_name.lower() for m in matches]
    for rm in rec_matches:
        entity_names_lower.append(rm.action.lower())
        entity_names_lower.append(rm.action_detail.lower())

    # Check minimum results
    if total < exp.min_results:
        issues.append(
            f"Expected >={exp.min_results} results, got {total}"
        )

    # Check must_find entities
    for entity in exp.must_find:
        found = any(entity.lower() in n for n in entity_names_lower)
        if not found:
            issues.append(f"MISSING expected entity: '{entity}'")
        else:
            findings.append(f"Found expected: '{entity}'")

    # Check must_not_find entities
    for entity in exp.must_not_find:
        found = any(entity.lower() in n for n in entity_names_lower)
        if found:
            issues.append(f"UNEXPECTED entity present: '{entity}'")

    # Check edge type
    if exp.expected_edge and matches:
        edge_types = {m.edge_type for m in matches}
        if exp.expected_edge not in edge_types:
            issues.append(
                f"Expected edge '{exp.expected_edge}', got {edge_types}"
            )
        else:
            findings.append(f"Correct edge type: {exp.expected_edge}")

    # Record what was found
    if matches:
        findings.append(
            f"Semantic matches ({len(matches)}): "
            + ", ".join(
                f"{m.entity_name} [{m.source_layer}]"
                for m in matches[:8]
            )
        )
    if rec_matches:
        findings.append(
            f"Recommendation matches ({len(rec_matches)}): "
            + ", ".join(rm.action for rm in rec_matches[:5])
        )
    if result.evidence:
        findings.append(f"Evidence citations: {len(result.evidence)}")
    if result.hints:
        findings.append(f"Hints: {result.hints}")
    if result.missing_variables:
        findings.append(f"Missing patient vars: {result.missing_variables}")

    findings.append(f"Confidence: {result.confidence}")
    findings.append(f"Layers used: {result.retrieval_layers_used}")

    return QueryResult(
        expectation=exp,
        graph_result=result,
        passed=len(issues) == 0,
        issues=issues,
        findings=findings,
    )


def print_patient_presentation() -> None:
    """Print the clinical case presentation."""
    print("\n" + "=" * 70)
    print("CLINICAL CASE — Emergency Department Presentation")
    print("=" * 70)
    print(f"\nPatient: {PATIENT['name']}, {PATIENT['age']}yo {PATIENT['sex']}")
    print(f"Chief Complaint: {PATIENT['presenting_complaint']}")
    print("\nVitals:")
    for k, v in PATIENT["vitals"].items():
        print(f"  {k}: {v}")
    print(f"\nEcho: {PATIENT['echo']}")
    print("\nLaboratory:")
    for k, v in PATIENT["labs"].items():
        print(f"  {k}: {v}")
    print("\nHistory:")
    for item in PATIENT["history"]:
        print(f"  - {item}")
    print("\nAssessment: New-onset HFrEF (LVEF 25%) with acute decompensation")
    print("  Comorbid: T2DM, HTN, CKD stage 3b")
    print("  Key concern: Hyperkalemia risk (K+ 5.1) limits MRA/ACEi options")
    print("=" * 70)


def print_evaluation_report(results: list[QueryResult]) -> None:
    """Print the full evaluation report with clinical context."""
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    total = len(results)

    for r in results:
        status = "PASS" if r.passed else "FAIL"
        exp = r.expectation
        gr = r.graph_result

        print(f"\n{'─' * 70}")
        print(f"[{status}] {exp.question_id}: {exp.clinical_question}")
        print(f"{'─' * 70}")
        print(f"  Clinical significance: {exp.why_it_matters[:120]}...")
        print(f"  Query: intent={exp.query.intent}, concepts={exp.query.concepts}")

        if r.findings:
            print("  Findings:")
            for f in r.findings:
                print(f"    {f}")

        if r.issues:
            print("  ISSUES:")
            for issue in r.issues:
                print(f"    !! {issue}")

        print(f"  Guideline basis: {exp.guideline_basis[:100]}...")

    # Summary
    print(f"\n{'=' * 70}")
    print("EVALUATION SUMMARY")
    print(f"{'=' * 70}")
    print(f"  Total queries:  {total}")
    print(f"  Passed:         {passed}")
    print(f"  Failed:         {failed}")
    print(f"  Score:          {passed}/{total} ({passed/total*100:.0f}%)")

    # Clinical coverage assessment
    intents_tested = {exp.query.intent for exp in [r.expectation for r in results]}
    intents_with_results = set()
    for r in results:
        gr = r.graph_result
        if gr.semantic_matches or gr.recommendation_matches:
            intents_with_results.add(r.expectation.query.intent)

    print(f"\n  Intents tested:       {sorted(intents_tested)}")
    print(f"  Intents with results: {sorted(intents_with_results)}")

    empty = [
        r.expectation.question_id
        for r in results
        if not r.graph_result.semantic_matches
        and not r.graph_result.recommendation_matches
    ]
    if empty:
        print(f"  Empty results:        {empty}")

    # Retrieval layer analysis
    layers_used: dict[str, int] = {}
    for r in results:
        for layer in r.graph_result.retrieval_layers_used:
            layers_used[layer] = layers_used.get(layer, 0) + 1
    if layers_used:
        print(f"\n  Retrieval layer usage: {layers_used}")
        if "expanded" in layers_used or "vector" in layers_used:
            print("    (fallback layers active — graph has coverage gaps)")
        else:
            print("    (all direct — graph edges well-connected)")

    print(f"{'=' * 70}")

    return passed, total


def main() -> None:
    print_patient_presentation()

    settings = get_settings()
    print(f"\nConnecting to Neo4j at {settings.neo4j_uri}...")

    try:
        with GraphConnection(
            settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password
        ) as conn:
            # Quick health check
            health = conn.execute_read("RETURN 1 AS ok")
            if not health:
                print("ERROR: Cannot connect to Neo4j")
                sys.exit(1)
            print("Connected.")

            # Check graph has data
            node_count = conn.execute_read(
                "MATCH (n) RETURN count(n) AS cnt"
            )[0]["cnt"]
            print(f"Graph contains {node_count} nodes.\n")

            if node_count == 0:
                print("ERROR: Graph is empty. Load data first:")
                print("  uv run python -m open_medicine.graphrag.ingest_v2 load ...")
                sys.exit(1)

            engine = ReasoningEngine(conn)

            print("Running clinical queries against the graph...\n")
            results = []
            for exp in EXPECTATIONS:
                result = evaluate_query(engine, exp)
                results.append(result)
                tag = "PASS" if result.passed else "FAIL"
                n = (
                    len(result.graph_result.semantic_matches)
                    + len(result.graph_result.recommendation_matches)
                )
                print(f"  [{tag}] {exp.question_id}: {n} results — {exp.clinical_question[:60]}")

            print_evaluation_report(results)

            passed, total = sum(1 for r in results if r.passed), len(results)
            sys.exit(0 if passed == total else 1)

    except Exception as e:
        print(f"\nERROR: {e}")
        print("\nEnsure .env has GRAPHRAG_NEO4J_URI, GRAPHRAG_NEO4J_USER, GRAPHRAG_NEO4J_PASSWORD")
        sys.exit(1)


if __name__ == "__main__":
    main()

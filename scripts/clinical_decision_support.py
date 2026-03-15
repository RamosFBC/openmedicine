#!/usr/bin/env python3
"""Clinical Decision Support — Real-world GraphRAG consultation.

Simulates a physician managing a complex heart failure patient through
sequential clinical decisions. Each decision point queries the graph
and synthesizes actionable, safety-critical recommendations.

This is NOT a pass/fail test. It's a demonstration of the graph as a
real-time clinical decision support tool for a hypothetical patient.

Case: Maria Santos, 74-year-old woman presenting with new-onset HFrEF
complicated by atrial fibrillation, CKD stage 3b, and a recent fall.
She is already on multiple medications. The physician must navigate
drug interactions, contraindications, dose adjustments, and monitoring
to build a safe treatment plan.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()

from open_medicine.graphrag.config import get_settings
from open_medicine.graphrag.graph.connection import GraphConnection
from open_medicine.graphrag.reasoning.engine_v2 import ReasoningEngine
from open_medicine.graphrag.reasoning.types_v2 import ClinicalQuery, GraphRAGResult


# ═══════════════════════════════════════════════════════════════════════
# THE PATIENT
# ═══════════════════════════════════════════════════════════════════════

PATIENT = {
    "name": "Maria Santos",
    "age": 74,
    "sex": "female",
    "weight_kg": 62,
    "height_cm": 158,
    "presenting_complaint": (
        "Progressive exertional dyspnea over 6 weeks, now at rest. "
        "Orthopnea (3-pillow), PND x 2 nights. Bilateral ankle swelling. "
        "Weight gain 5 kg in 3 weeks. Episode of near-syncope yesterday."
    ),
    "vitals": {
        "BP": "108/68 mmHg",
        "HR": "112 bpm (irregularly irregular)",
        "SpO2": "90% on room air",
        "RR": "28/min",
        "Temp": "36.8°C",
        "JVP": "Elevated to ear lobe",
    },
    "echo": (
        "LVEF 20%, severely dilated LV (LVEDd 68mm), "
        "moderate-to-severe functional mitral regurgitation, "
        "moderate tricuspid regurgitation, "
        "RVSP 55 mmHg (pulmonary hypertension), "
        "RV mildly dilated with preserved function"
    ),
    "ecg": "Atrial fibrillation with rapid ventricular response, rate 112, "
           "left axis deviation, poor R-wave progression V1-V4, "
           "no acute ST changes",
    "labs": {
        "NT-proBNP": "8,420 pg/mL (severely elevated)",
        "Troponin I": "0.08 ng/mL (mildly elevated — demand ischemia)",
        "eGFR": 32,
        "Creatinine": "1.6 mg/dL",
        "BUN": "38 mg/dL",
        "Potassium": "5.3 mEq/L",
        "Sodium": "131 mEq/L",
        "Magnesium": "1.8 mg/dL",
        "Hemoglobin": "10.2 g/dL (mild anemia)",
        "HbA1c": "6.1% (prediabetic)",
        "TSH": "4.8 mIU/L (high-normal)",
        "Albumin": "3.0 g/dL (low)",
        "INR": "1.0",
        "Liver enzymes": "AST 42, ALT 38 (mildly elevated — hepatic congestion)",
    },
    "current_medications": [
        "Lisinopril 10 mg daily (for HTN, started 2 years ago)",
        "Amlodipine 5 mg daily (for HTN)",
        "Metformin 500 mg BID (for prediabetes, started 6 months ago)",
        "Aspirin 81 mg daily",
        "Omeprazole 20 mg daily",
        "Vitamin D 1000 IU daily",
    ],
    "medical_history": [
        "Hypertension (20 years)",
        "Prediabetes (1 year)",
        "Osteoarthritis bilateral knees (takes OTC NSAIDs intermittently)",
        "Atrial fibrillation (newly diagnosed on this admission)",
        "Fall 1 week ago (mechanical, no head injury)",
        "No prior heart failure diagnosis",
        "No known drug allergies",
    ],
    "social_history": (
        "Lives alone, independent ADLs until 6 weeks ago. "
        "Retired teacher. Non-smoker. No alcohol. "
        "Two adult children who live nearby."
    ),
    "assessment": (
        "New-onset HFrEF (LVEF 20%), NYHA class IV, acute decompensation.\n"
        "  New atrial fibrillation with rapid ventricular response.\n"
        "  CKD stage 3b (eGFR 32) — likely cardiorenal.\n"
        "  Hyperkalemia (K+ 5.3) — limits RAAS blockade options.\n"
        "  Hyponatremia (Na+ 131) — marker of severity.\n"
        "  Mild hepatic congestion.\n"
        "  Fall risk (elderly, recent fall, polypharmacy)."
    ),
}

PATIENT_VARS = {
    "age": 74,
    "sex": "female",
    "LVEF": 20,
    "egfr": 32,
    "potassium": 5.3,
    "sodium": 131,
    "heart_failure_type": "HFrEF",
    "nyha_class": 4,
    "heart_rate": 112,
    "systolic_bp": 108,
}


# ═══════════════════════════════════════════════════════════════════════
# CLINICAL DECISION POINTS
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class DecisionPoint:
    """A clinical decision the physician must make."""
    step: int
    title: str
    clinical_context: str
    queries: list[ClinicalQuery]
    safety_check: str  # What the physician MUST verify before acting
    expected_clinical_answer: str  # What the guideline says


DECISION_POINTS: list[DecisionPoint] = [
    # ── Step 1: Establish GDMT Foundation ──────────────────────────────
    DecisionPoint(
        step=1,
        title="Initiate Guideline-Directed Medical Therapy (GDMT)",
        clinical_context=(
            "Maria has newly diagnosed HFrEF with LVEF 20%. The 2022 AHA/ACC "
            "guideline mandates 4-pillar GDMT: ACEi/ARB/ARNi + beta-blocker + "
            "MRA + SGLT2i. But her hemodynamics are tenuous (BP 108/68), K+ is "
            "5.3, and eGFR is 32. Can we safely start all four pillars?"
        ),
        queries=[
            ClinicalQuery(
                intent="treatment_selection",
                concepts=["HFrEF"],
                patient_vars=PATIENT_VARS,
                include_evidence=True,
            ),
        ],
        safety_check=(
            "Before prescribing: verify BP tolerates RAAS blockade (SBP >90), "
            "verify K+ allows MRA/ACEi (K+ <5.5 per guideline, but 5.3 is very "
            "close), verify eGFR allows MRA (eGFR >30 per guideline, 32 is borderline)."
        ),
        expected_clinical_answer=(
            "Start all 4 pillars per guideline, BUT with caution:\n"
            "  - Continue Lisinopril (already on ACEi) — do NOT uptitrate yet\n"
            "  - Start low-dose beta-blocker (after hemodynamic stabilization)\n"
            "  - MRA: BORDERLINE — eGFR 32 (>30 ok) but K+ 5.3 (>5.0 is caution zone)\n"
            "  - SGLT2i: Can start — renal benefit shown even with low eGFR\n"
            "  - STOP Amlodipine — negative inotrope, harmful in HFrEF"
        ),
    ),

    # ── Step 2: Contraindication Check — What Must We STOP? ───────────
    DecisionPoint(
        step=2,
        title="Identify Contraindicated Medications",
        clinical_context=(
            "Maria is on Amlodipine (dihydropyridine CCB) and intermittent NSAIDs. "
            "Both are potentially harmful in HFrEF. She also just got diagnosed with "
            "AF — does this change anything?"
        ),
        queries=[
            ClinicalQuery(
                intent="contraindication",
                concepts=["Calcium Channel Blockers"],
                patient_vars=PATIENT_VARS,
                include_evidence=True,
            ),
            ClinicalQuery(
                intent="contraindication",
                concepts=["NSAIDs"],
                patient_vars=PATIENT_VARS,
                include_evidence=True,
            ),
        ],
        safety_check=(
            "Amlodipine: Non-dihydropyridine CCBs (verapamil, diltiazem) are Class III "
            "(harm) in HFrEF. Amlodipine is safer but still not recommended as first-line.\n"
            "NSAIDs: Class III (harm) — worsen fluid retention, renal function, and "
            "counteract diuretics/ACEi."
        ),
        expected_clinical_answer=(
            "STOP: NSAIDs immediately (Class III: Harm in HF).\n"
            "STOP: Amlodipine — replace with evidence-based antihypertensives already "
            "in GDMT (ACEi + BB provide BP control).\n"
            "ADD: Anticoagulation for new AF with CHA₂DS₂-VASc ≥3."
        ),
    ),

    # ── Step 3: Drug Interactions — ACEi + MRA + K+ 5.3 ──────────────
    DecisionPoint(
        step=3,
        title="Assess Critical Drug Interactions",
        clinical_context=(
            "Maria is on Lisinopril (ACEi). We want to add Spironolactone (MRA). "
            "Both raise potassium. Her K+ is already 5.3. This is the #1 safety "
            "question in her case. Additionally, she should NOT receive combined "
            "ACEi + ARB (which the graph should warn about)."
        ),
        queries=[
            ClinicalQuery(
                intent="interaction",
                concepts=["ACE inhibitors"],
                patient_vars=PATIENT_VARS,
                include_evidence=True,
            ),
            ClinicalQuery(
                intent="interaction",
                concepts=["Spironolactone"],
                patient_vars=PATIENT_VARS,
                include_evidence=False,
            ),
        ],
        safety_check=(
            "Triple RAAS blockade (ACEi + ARB + MRA) is NEVER appropriate.\n"
            "Dual blockade (ACEi + MRA) is standard GDMT BUT requires K+ <5.0 "
            "and eGFR >30 at initiation. Maria's K+ 5.3 EXCEEDS this threshold.\n"
            "Clinical decision: treat hyperkalemia FIRST, then add MRA."
        ),
        expected_clinical_answer=(
            "ACEi + ARB: AVOID combination (Class III: Harm).\n"
            "ACEi + MRA: Standard GDMT, but DEFER in Maria until K+ <5.0.\n"
            "Action plan: hold MRA, treat hyperkalemia (loop diuretics, kayexalate), "
            "recheck K+ in 48h. Start MRA only when K+ <5.0."
        ),
    ),

    # ── Step 4: Beta-Blocker Dosing ───────────────────────────────────
    DecisionPoint(
        step=4,
        title="Select and Dose Beta-Blocker",
        clinical_context=(
            "Maria needs a beta-blocker for HFrEF AND for AF rate control. "
            "Her HR is 112 in AF. She has low BP (108/68). Starting a beta-blocker "
            "during acute decompensation risks further hemodynamic compromise. "
            "Which agent? What starting dose? When to start?"
        ),
        queries=[
            ClinicalQuery(
                intent="dosing",
                concepts=["Carvedilol", "HFrEF"],
                patient_vars=PATIENT_VARS,
                include_evidence=True,
            ),
            ClinicalQuery(
                intent="dosing",
                concepts=["Metoprolol Succinate", "HFrEF"],
                patient_vars=PATIENT_VARS,
                include_evidence=True,
            ),
        ],
        safety_check=(
            "CRITICAL: Do NOT start or uptitrate beta-blocker during acute "
            "decompensation (Class III). Wait until euvolemic AND off IV diuretics.\n"
            "Starting dose must be the LOWEST available — 3.125 mg BID for carvedilol, "
            "12.5-25 mg daily for metoprolol succinate."
        ),
        expected_clinical_answer=(
            "Wait until hemodynamically stable and euvolemic (typically 24-72h).\n"
            "Then start Carvedilol 3.125 mg BID OR Metoprolol Succinate 12.5-25 mg daily.\n"
            "Carvedilol preferred: also provides alpha-blockade (additional BP benefit), "
            "and COMET trial showed superiority over metoprolol tartrate.\n"
            "Target: Carvedilol 25 mg BID (<85 kg) — uptitrate every 2 weeks."
        ),
    ),

    # ── Step 5: Monitoring Plan ───────────────────────────────────────
    DecisionPoint(
        step=5,
        title="Establish Monitoring Protocol",
        clinical_context=(
            "Maria is going to be on ACEi + beta-blocker + eventually MRA + SGLT2i. "
            "With eGFR 32 and K+ 5.3, she needs aggressive lab monitoring. "
            "What labs, how often, and what thresholds trigger action?"
        ),
        queries=[
            ClinicalQuery(
                intent="monitoring",
                concepts=["Spironolactone"],
                patient_vars=PATIENT_VARS,
                include_evidence=True,
            ),
            ClinicalQuery(
                intent="monitoring",
                concepts=["Lisinopril"],
                patient_vars=PATIENT_VARS,
                include_evidence=True,
            ),
        ],
        safety_check=(
            "RALES trial: MRA mortality benefit REVERSED when K+ monitoring was "
            "inadequate — real-world hyperkalemia deaths increased after publication.\n"
            "With eGFR 32: check BMP within 1 week of ANY RAAS agent change.\n"
            "Stop MRA if K+ >5.5. Stop ACEi if K+ >5.5 or creatinine rises >30%."
        ),
        expected_clinical_answer=(
            "Baseline: BMP, Cr, K+, Mg²⁺, renal panel NOW.\n"
            "After ACEi continuation: recheck K+, Cr in 1 week.\n"
            "After MRA initiation: recheck K+, Cr at 3 days, 1 week, 1 month.\n"
            "After SGLT2i: recheck eGFR at 1 month (expected initial dip is OK).\n"
            "Ongoing: BMP every 3-6 months, more frequently if eGFR declining.\n"
            "STOP thresholds: K+ >5.5, Cr rise >30% from baseline, eGFR <20."
        ),
    ),

    # ── Step 6: Diagnostic Criteria Verification ──────────────────────
    DecisionPoint(
        step=6,
        title="Confirm HF Classification and Staging",
        clinical_context=(
            "We classified Maria as HFrEF. Let's verify against the 2022 criteria. "
            "Does she meet diagnostic criteria? What stage is she in? "
            "This determines her entire treatment algorithm."
        ),
        queries=[
            ClinicalQuery(
                intent="diagnostic_criteria",
                concepts=["Heart Failure"],
                patient_vars=PATIENT_VARS,
                include_evidence=True,
            ),
        ],
        safety_check=(
            "Misclassification changes everything: HFpEF has NO proven mortality-"
            "reducing GDMT. HFrEF has Class I evidence for 4-pillar therapy.\n"
            "LVEF 20% = definitely HFrEF (≤40%). Stage C (structural disease + symptoms)."
        ),
        expected_clinical_answer=(
            "Confirmed HFrEF: LVEF 20% (≤40% threshold).\n"
            "Stage C: Structural heart disease with current symptoms.\n"
            "NYHA Class IV: Symptoms at rest.\n"
            "This confirms eligibility for all Class I GDMT recommendations."
        ),
    ),

    # ── Step 7: ARNi Transition Planning ──────────────────────────────
    DecisionPoint(
        step=7,
        title="Plan ACEi-to-ARNi Transition",
        clinical_context=(
            "The 2022 guideline recommends ARNi (sacubitril/valsartan) over ACEi. "
            "Maria is on Lisinopril. Transitioning requires a mandatory 36-hour "
            "washout period to prevent angioedema. With her tenuous hemodynamics, "
            "timing matters."
        ),
        queries=[
            ClinicalQuery(
                intent="treatment_selection",
                concepts=["Sacubitril/Valsartan", "HFrEF"],
                patient_vars=PATIENT_VARS,
                include_evidence=True,
            ),
            ClinicalQuery(
                intent="interaction",
                concepts=["ARNi"],
                patient_vars=PATIENT_VARS,
                include_evidence=True,
            ),
        ],
        safety_check=(
            "MANDATORY 36-hour washout between ACEi and ARNi (angioedema risk).\n"
            "Start at lowest dose (sacubitril 24mg/valsartan 26mg BID).\n"
            "Requires SBP ≥100 mmHg. Maria's SBP is 108 — borderline.\n"
            "PARADIGM-HF: ARNi reduced CV death 20% vs enalapril."
        ),
        expected_clinical_answer=(
            "Plan for ARNi transition AFTER stabilization:\n"
            "1. Continue Lisinopril during acute phase\n"
            "2. When euvolemic + SBP stable ≥100: stop Lisinopril\n"
            "3. 36-hour washout (no RAAS blockade)\n"
            "4. Start Sacubitril/Valsartan 24/26 mg BID\n"
            "5. Uptitrate to 97/103 mg BID over 2-4 weeks if tolerated"
        ),
    ),
]


# ═══════════════════════════════════════════════════════════════════════
# CLINICAL DECISION SUPPORT ENGINE
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class DecisionResult:
    """Result of a clinical decision point evaluation."""
    decision: DecisionPoint
    query_results: list[GraphRAGResult]
    graph_provided_info: bool  # Did the graph return useful data?
    safety_flags: list[str]  # Safety concerns surfaced
    clinical_summary: str  # Synthesized recommendation


def print_patient() -> None:
    """Print the full patient presentation."""
    p = PATIENT
    print("\n" + "=" * 78)
    print("  CLINICAL CASE — Cardiology Consultation Request")
    print("=" * 78)

    print(f"\n  Patient:  {p['name']}, {p['age']}-year-old {p['sex']}")
    print(f"  Weight:   {p['weight_kg']} kg | Height: {p['height_cm']} cm")
    print(f"  Chief Complaint: {p['presenting_complaint']}")

    print("\n  ┌─ Vitals ───────────────────────────────────────────────────────┐")
    for k, v in p["vitals"].items():
        print(f"  │  {k:8s}: {v:50s}│")
    print("  └──────────────────────────────────────────────────────────────────┘")

    print(f"\n  ECG:  {p['ecg']}")
    print(f"  Echo: {p['echo']}")

    print("\n  ┌─ Laboratory ──────────────────────────────────────────────────┐")
    for k, v in p["labs"].items():
        flag = ""
        if isinstance(v, str) and ("elevated" in v.lower() or "low" in v.lower()):
            flag = " ⚠"
        elif k == "Potassium" and isinstance(v, (int, float)) and v > 5.0:
            flag = " ⚠"
        print(f"  │  {k:16s}: {str(v):42s}{flag:2s}│")
    print("  └──────────────────────────────────────────────────────────────────┘")

    print("\n  Current Medications:")
    for med in p["current_medications"]:
        print(f"    - {med}")

    print("\n  Medical History:")
    for item in p["medical_history"]:
        print(f"    - {item}")

    print(f"\n  Social: {p['social_history']}")

    print(f"\n  ┌─ Assessment ──────────────────────────────────────────────────┐")
    for line in p["assessment"].split("\n"):
        print(f"  │  {line:64s}│")
    print("  └──────────────────────────────────────────────────────────────────┘")
    print()


def run_decision_point(
    engine: ReasoningEngine, dp: DecisionPoint,
) -> DecisionResult:
    """Execute all queries for a decision point and synthesize results."""
    query_results: list[GraphRAGResult] = []
    safety_flags: list[str] = []
    all_matches: list[str] = []

    for q in dp.queries:
        result = engine.query(q)
        query_results.append(result)

        # Collect findings
        for m in result.semantic_matches:
            desc = f"[{m.edge_type}] {m.entity_name}"
            if m.strength:
                desc += f" (strength={m.strength})"
            if not m.conditions_met:
                desc += " ** CONDITIONS NOT MET **"
                safety_flags.append(
                    f"Patient may not meet conditions for: {m.entity_name}"
                )
            if m.missing_variables:
                desc += f" (missing: {', '.join(m.missing_variables)})"
            all_matches.append(desc)

        for rm in result.recommendation_matches:
            desc = f"[REC:{rm.rec_type}] {rm.action}"
            if rm.action_detail:
                desc += f" — {rm.action_detail[:80]}"
            all_matches.append(desc)

        # Safety: check for missing variables
        if result.missing_variables:
            safety_flags.append(
                f"Graph needs patient data not provided: {result.missing_variables}"
            )

    has_info = any(
        r.semantic_matches or r.recommendation_matches for r in query_results
    )

    # Build clinical summary
    if all_matches:
        summary = "\n    ".join(all_matches)
    else:
        hints = []
        for r in query_results:
            hints.extend(r.hints)
        if hints:
            summary = "No direct matches. Hints: " + "; ".join(hints)
        else:
            summary = "No results returned from graph."

    return DecisionResult(
        decision=dp,
        query_results=query_results,
        graph_provided_info=has_info,
        safety_flags=safety_flags,
        clinical_summary=summary,
    )


def print_decision_result(dr: DecisionResult) -> None:
    """Print a single decision point result with clinical context."""
    dp = dr.decision
    status = "DATA AVAILABLE" if dr.graph_provided_info else "NO GRAPH DATA"

    print(f"\n{'━' * 78}")
    print(f"  STEP {dp.step}: {dp.title}")
    print(f"  Status: [{status}]")
    print(f"{'━' * 78}")

    # Clinical context
    print(f"\n  Clinical Context:")
    for line in _wrap(dp.clinical_context, 72):
        print(f"    {line}")

    # What the graph returned
    print(f"\n  Graph Results:")
    for i, qr in enumerate(dr.query_results):
        q = dp.queries[i]
        n = len(qr.semantic_matches) + len(qr.recommendation_matches)
        print(f"    Query {i+1}: intent={q.intent}, concepts={q.concepts}")
        print(f"      Matches: {n} | Confidence: {qr.confidence} | "
              f"Layers: {qr.retrieval_layers_used}")

        if qr.semantic_matches:
            for m in qr.semantic_matches:
                cond = ""
                if not m.conditions_met:
                    cond = " [CONDITIONS NOT MET]"
                elif m.missing_variables:
                    cond = f" [missing: {', '.join(m.missing_variables)}]"
                strength_info = ""
                if m.strength:
                    strength_info = f", strength={m.strength}"
                    if m.evidence_quality:
                        strength_info += f", evidence={m.evidence_quality}"
                print(
                    f"      - {m.entity_name} ({m.entity_type}) "
                    f"via {m.edge_type}{strength_info}{cond}"
                )

        if qr.recommendation_matches:
            for rm in qr.recommendation_matches:
                print(f"      - [REC] {rm.action}")
                if rm.action_detail:
                    print(f"              {rm.action_detail[:100]}")

        if qr.evidence:
            print(f"      Evidence citations: {len(qr.evidence)}")
            for ev in qr.evidence[:3]:
                txt = ev.text[:100].replace("\n", " ")
                print(f"        - [{ev.section}] {txt}...")
                if ev.doi:
                    print(f"          DOI: {ev.doi}")

        if qr.hints:
            print(f"      Hints: {qr.hints}")

    # Safety flags
    if dr.safety_flags:
        print(f"\n  Safety Flags:")
        for flag in dr.safety_flags:
            print(f"    !! {flag}")

    # Safety check (what the physician must verify)
    print(f"\n  Safety Verification Required:")
    for line in _wrap(dp.safety_check, 72):
        print(f"    {line}")

    # Expected clinical answer
    print(f"\n  Expected Clinical Answer (per AHA/ACC 2022):")
    for line in dp.expected_clinical_answer.split("\n"):
        print(f"    {line}")


def _wrap(text: str, width: int) -> list[str]:
    """Simple word wrap."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 > width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}" if current else word
    if current:
        lines.append(current)
    return lines


def print_treatment_plan(results: list[DecisionResult]) -> None:
    """Print the final synthesized treatment plan."""
    print(f"\n{'=' * 78}")
    print("  SYNTHESIZED TREATMENT PLAN — Maria Santos, 74F, HFrEF (LVEF 20%)")
    print(f"{'=' * 78}")

    # Count how many decision points had graph data
    with_data = sum(1 for r in results if r.graph_provided_info)
    total = len(results)

    print(f"\n  Graph Coverage: {with_data}/{total} decision points had graph data")

    # Summarize all safety flags
    all_flags = []
    for r in results:
        all_flags.extend(r.safety_flags)
    if all_flags:
        print(f"\n  Total Safety Flags Raised: {len(all_flags)}")
        for i, flag in enumerate(all_flags, 1):
            print(f"    {i}. {flag}")

    # Synthesize: what the physician should do based on graph + clinical judgment
    print(f"""
  ┌─ ACUTE PHASE (Hours 0-24) ─────────────────────────────────────────┐
  │  1. IV Furosemide — aggressive diuresis for volume overload        │
  │  2. CONTINUE Lisinopril 10 mg — already on ACEi (GDMT pillar 1)   │
  │  3. STOP Amlodipine — not recommended in HFrEF                    │
  │  4. STOP NSAIDs — Class III: Harm in HF                           │
  │  5. HOLD on MRA — K+ 5.3 is above 5.0 threshold                  │
  │  6. HOLD on beta-blocker — acute decompensation, wait for euvolemia│
  │  7. Start anticoagulation for new AF (CHA2DS2-VASc >= 3)          │
  │  8. Monitor: BMP, K+, Cr, I/O, daily weights q6-12h              │
  └────────────────────────────────────────────────────────────────────┘

  ┌─ STABILIZATION PHASE (Days 1-3) ───────────────────────────────────┐
  │  9. Once euvolemic + off IV diuretics:                             │
  │     - Start Carvedilol 3.125 mg BID (lowest dose)                  │
  │     - Recheck K+ — if <5.0, start Spironolactone 12.5-25 mg daily │
  │ 10. Start SGLT2i (Dapagliflozin 10 mg or Empagliflozin 10 mg)     │
  │ 11. Recheck BMP at 72h after each new medication                   │
  └────────────────────────────────────────────────────────────────────┘

  ┌─ TRANSITION PHASE (Days 3-7+) ─────────────────────────────────────┐
  │ 12. Plan ACEi → ARNi transition when SBP stable ≥100:             │
  │     - Stop Lisinopril, wait 36 hours                               │
  │     - Start Sacubitril/Valsartan 24/26 mg BID                      │
  │ 13. Uptitrate beta-blocker every 2 weeks to target dose            │
  │ 14. Consider ICD evaluation at 3-month mark if LVEF still ≤35%    │
  └────────────────────────────────────────────────────────────────────┘

  ┌─ MONITORING SCHEDULE ──────────────────────────────────────────────┐
  │  K+, Cr, eGFR: 3 days, 1 week, 2 weeks, then monthly              │
  │  Echo: repeat at 3 months to reassess LVEF                        │
  │  BNP: at discharge, 1 month, 3 months                             │
  │  STOP thresholds: K+ >5.5, Cr rise >30%, SBP <90, HR <50         │
  └────────────────────────────────────────────────────────────────────┘
""")

    print(f"{'=' * 78}")
    print(f"  Coverage: {with_data}/{total} decisions informed by graph data")
    all_layers = {}
    for r in results:
        for qr in r.query_results:
            for layer in qr.retrieval_layers_used:
                all_layers[layer] = all_layers.get(layer, 0) + 1
    if all_layers:
        print(f"  Retrieval layers: {all_layers}")
    print(f"  Safety flags surfaced: {len(all_flags)}")
    print(f"{'=' * 78}")


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main() -> None:
    print_patient()

    settings = get_settings()
    print(f"Connecting to Neo4j at {settings.neo4j_uri}...")

    try:
        with GraphConnection(
            settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password
        ) as conn:
            health = conn.execute_read("RETURN 1 AS ok")
            if not health:
                print("ERROR: Cannot connect to Neo4j")
                sys.exit(1)

            node_count = conn.execute_read(
                "MATCH (n) RETURN count(n) AS cnt"
            )[0]["cnt"]
            edge_count = conn.execute_read(
                "MATCH ()-[r]->() RETURN count(r) AS cnt"
            )[0]["cnt"]
            print(f"Connected. Graph: {node_count} nodes, {edge_count} edges.\n")

            if node_count == 0:
                print("ERROR: Graph is empty. Load data first.")
                sys.exit(1)

            engine = ReasoningEngine(conn)

            print("Running clinical decision support queries...\n")
            results: list[DecisionResult] = []
            for dp in DECISION_POINTS:
                print(f"  Step {dp.step}: {dp.title}...", end=" ", flush=True)
                result = run_decision_point(engine, dp)
                n_matches = sum(
                    len(r.semantic_matches) + len(r.recommendation_matches)
                    for r in result.query_results
                )
                status = f"{n_matches} matches" if n_matches else "no matches"
                print(f"[{status}]")
                results.append(result)

            # Print detailed results
            for dr in results:
                print_decision_result(dr)

            # Print synthesized treatment plan
            print_treatment_plan(results)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        print("\nEnsure .env has GRAPHRAG_NEO4J_URI, GRAPHRAG_NEO4J_USER, GRAPHRAG_NEO4J_PASSWORD")
        sys.exit(1)


if __name__ == "__main__":
    main()

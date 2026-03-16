# Critical Decision Scenario: Multimorbid HF Patient — SGLT2i Initiation with Polypharmacy Risks

## Patient Profile

- **Age:** 74
- **Sex:** Female
- **Weight:** 58 kg
- **Primary Diagnosis:** HFrEF (LVEF 32%)
- **Comorbidities:** Type 2 Diabetes, Chronic Kidney Disease (Stage 3a), Gout, Hypertension, History of GI bleed (6 months ago)
- **Allergies:** None documented

### Current Medications

| Drug | Dose | Frequency |
|------|------|-----------|
| Lisinopril | 20 mg | Daily |
| Metoprolol succinate | 100 mg | Daily |
| Spironolactone | 25 mg | Daily |
| Metformin | 1000 mg | BID |
| Allopurinol | 300 mg | Daily |
| Aspirin | 81 mg | Daily |
| Omeprazole | 20 mg | Daily |

### Current Labs

| Lab | Value | Reference |
|-----|-------|-----------|
| eGFR | 48 mL/min/1.73m² | >60 |
| Potassium | 4.9 mEq/L | 3.5–5.0 |
| BNP | 620 pg/mL | <100 |
| Creatinine | 1.3 mg/dL | 0.6–1.1 |
| HbA1c | 8.2% | <7.0 |
| Hemoglobin | 10.8 g/dL | 12.0–16.0 |
| Sodium | 134 mEq/L | 136–145 |

---

## Clinical Question

This patient is on 3 of 4 GDMT pillars (ACEi + beta blocker + MRA) but is missing an SGLT2 inhibitor. Her HbA1c is suboptimal and she has mild anemia and borderline hyponatremia. The attending wants to add dapagliflozin and consider upgrading lisinopril to sacubitril/valsartan. Walk through each decision using the MCP tools.

---

## Decision Chain (8 steps — one per MCP tool)

### Step 1: List Available Guidelines

**Tool:** `list_available_guidelines`

Confirm the AHA/ACC HF 2022 guideline is loaded. This guideline governs all GDMT decisions in this scenario.

---

### Step 2: Find Treatment Options for HFrEF

**Tool:** `find_treatment_options`
```
condition: "heart_failure_reduced_ef"
patient_vars: { "lvef": 32, "egfr": 48, "nyha_class": 2 }
```

**Expected:** All 4 GDMT pillars returned. Patient is on 3 of 4 — SGLT2i is the gap. ARNi upgrade from ACEi should also appear as a recommendation.

**Critical Decision:** Two changes are proposed — adding SGLT2i and upgrading to ARNi. Both need safety evaluation before proceeding.

---

### Step 3: Check Contraindications for Sacubitril/Valsartan

**Tool:** `check_contraindications`
```
intervention: "sacubitril_valsartan"
patient_vars: { "history_of_angioedema": false, "potassium": 4.9, "egfr": 48 }
```

**Expected:** No absolute contraindication. However, the patient is on lisinopril — a mandatory 36-hour washout period is required before starting ARNi. The potassium at 4.9 is a caution flag (not a block).

**Why this matters:** Unlike the first scenario (where angioedema blocks ARNi entirely), here the ARNi is permissible but requires careful sequencing. The agent must communicate the washout requirement.

---

### Step 4: Check Drug Interaction — ACEi and ARNi Overlap

**Tool:** `check_drug_interaction`
```
drug_a: "lisinopril"
drug_b: "sacubitril_valsartan"
```

**Expected:** ABSOLUTE interaction — ACEi and ARNi must NEVER be co-administered. Risk of life-threatening angioedema. Requires 36-hour washout after stopping ACEi before starting ARNi.

**Critical Decision:** This is a sequencing safety gate. The agent must ensure lisinopril is stopped and a washout period elapses before sacubitril/valsartan can be initiated.

---

### Step 5: Check Dosing for Dapagliflozin

**Tool:** `check_drug_dosing`
```
drug: "dapagliflozin"
patient_vars: { "egfr": 48, "weight_kg": 58 }
```

**Expected:** Standard dose 10 mg daily. eGFR ≥ 20 is sufficient for initiation in HF indication (no renal dose adjustment needed for HF, unlike diabetes-only indication where eGFR ≥ 25 was previously required).

**Why this matters:** Many clinicians hesitate to start SGLT2i with eGFR < 60. The tool should confirm eligibility per current guidelines.

---

### Step 6: Check Monitoring Requirements for Spironolactone

**Tool:** `check_monitoring_requirements`
```
intervention: "spironolactone"
patient_vars: { "egfr": 48, "potassium": 4.9 }
```

**Expected:** Potassium and creatinine monitoring. With K+ at 4.9 (near upper limit) and CKD, monitoring frequency should be increased. Alert threshold K+ ≥ 5.5, consider dose reduction. Stop threshold K+ ≥ 6.0.

**Critical Decision:** Adding dapagliflozin may actually help here — SGLT2i can modestly reduce potassium, potentially making the MRA safer. But this benefit doesn't eliminate the need for monitoring.

---

### Step 7: Query Clinical Graph — Device Therapy Eligibility

**Tool:** `query_clinical_graph`
```
intent: "device_therapy"
concepts: ["ICD", "CRT", "heart_failure_reduced_ef"]
patient_vars: { "lvef": 32, "nyha_class": 2 }
guideline_filter: "aha_acc_hf_2022"
```

**Expected:** With LVEF 32% (≤35%), the patient meets criteria for ICD evaluation for primary prevention of sudden cardiac death. CRT may be indicated if QRS duration is prolonged (not provided — the agent should note this data gap).

**Why this matters:** GDMT optimization is step 1, but device therapy evaluation runs in parallel. An AI agent should flag this even when the primary question is about medications.

---

### Step 8: Fetch Evidence for ARNi Recommendation

**Tool:** `fetch_evidence_chunk`
```
chunk_id: <from Step 2 or Step 3 evidence field>
```

**Expected:** Returns the AHA/ACC 2022 guideline text supporting ARNi use in HFrEF, including the Class I recommendation and PARADIGM-HF trial reference.

---

## Expected Outcome Summary

| Decision | Result | Safety Implication |
|----------|--------|--------------------|
| Add SGLT2i (dapagliflozin)? | **RECOMMENDED** — eligible by eGFR, standard dose | Safest addition; may also improve glycemic control and reduce K+ |
| Upgrade to ARNi? | **PERMISSIBLE** — no contraindication, but requires ACEi washout | Must stop lisinopril ≥ 36 hours before starting; ABSOLUTE interaction if co-administered |
| Continue spironolactone? | **YES with increased monitoring** — K+ 4.9 is borderline | Weekly K+/Cr checks; dose reduce if K+ ≥ 5.5 |
| Device therapy? | **EVALUATE** — LVEF ≤ 35% meets ICD criteria | Needs QRS duration to assess CRT candidacy |
| Aspirin with GI bleed history? | **FLAG** — not part of HF GDMT query but relevant | Consider risk-benefit given recent GI bleed |

## Why This Scenario Is Valuable

1. **Permissible-but-sequenced intervention:** ARNi is allowed here (unlike Scenario 1 with angioedema), but requires careful drug transition — tests the agent's ability to handle sequencing, not just yes/no blocks
2. **ABSOLUTE interaction without contraindication:** ACEi + ARNi is a fatal interaction even though neither drug alone is contraindicated — tests interaction checking independent of contraindication checking
3. **Borderline lab values:** K+ at 4.9 isn't a hard stop, but requires the agent to flag risk and adjust monitoring — tests nuanced decision-making
4. **Multi-domain reasoning:** HF GDMT + diabetes management + device therapy + GI safety — tests whether the agent considers adjacent clinical domains
5. **Complementary to Scenario 1:** Together, the two scenarios cover both "hard block" (angioedema → no ARNi) and "proceed with caution" (no angioedema → ARNi with washout) decision patterns

# Critical Decision Scenario: Heart Failure Patient on ACE Inhibitor with Worsening Symptoms

## Patient Profile

- **Age:** 68
- **Sex:** Male
- **Weight:** 82 kg
- **Primary Diagnosis:** HFrEF (LVEF 28%)
- **Comorbidities:** Type 2 Diabetes, Chronic Kidney Disease (Stage 3b), Atrial Fibrillation, Hypertension
- **History:** Prior angioedema episode on enalapril (switched to losartan 2 years ago)

### Current Medications

| Drug | Dose | Frequency |
|------|------|-----------|
| Losartan | 50 mg | BID |
| Carvedilol | 12.5 mg | BID |
| Furosemide | 40 mg | Daily |
| Metformin | 500 mg | BID |
| Warfarin | 5 mg | Daily |

### Current Labs

| Lab | Value | Reference |
|-----|-------|-----------|
| eGFR | 35 mL/min/1.73m² | >60 |
| Potassium | 5.1 mEq/L | 3.5–5.0 |
| BNP | 890 pg/mL | <100 |
| Creatinine | 1.9 mg/dL | 0.7–1.3 |
| HbA1c | 7.8% | <7.0 |
| INR | 2.4 | 2.0–3.0 |

---

## Clinical Question

The patient presents with worsening dyspnea on exertion (NYHA Class III, previously Class II). The attending wants to optimize guideline-directed medical therapy (GDMT). Walk through the following critical decisions using the MCP tools.

---

## Decision Chain (8 steps — one per MCP tool)

### Step 1: List Available Guidelines

**Tool:** `list_available_guidelines`

Confirm which heart failure guidelines are loaded. The AHA/ACC HF 2022 guideline should be available to scope all subsequent queries.

---

### Step 2: Find Treatment Options for HFrEF

**Tool:** `find_treatment_options`
```
condition: "heart_failure_reduced_ef"
patient_vars: { "lvef": 28, "egfr": 35, "nyha_class": 3 }
```

**Expected:** ARNi, beta blocker, MRA, SGLT2i as GDMT pillars. Identify which therapies the patient is missing (ARNi upgrade, MRA, SGLT2i).

**Critical Decision:** The patient is on losartan (ARB), not ARNi. Guidelines recommend upgrading to sacubitril/valsartan. But this patient has a history of angioedema on enalapril...

---

### Step 3: Check Contraindications for Sacubitril/Valsartan

**Tool:** `check_contraindications`
```
intervention: "sacubitril_valsartan"
patient_vars: { "history_of_angioedema": true, "potassium": 5.1, "egfr": 35 }
```

**Expected:** ABSOLUTE contraindication due to angioedema history with ACE inhibitor. This is the critical safety gate — ARNi must NOT be started.

**Why this matters:** An AI agent that ignores this contraindication could recommend a drug that causes life-threatening angioedema. The graph must return severity=ABSOLUTE.

---

### Step 4: Check Drug Interaction — Adding Spironolactone to Current Regimen

**Tool:** `check_drug_interaction`
```
drug_a: "spironolactone"
drug_b: "losartan"
patient_vars: { "potassium": 5.1, "egfr": 35 }
```

**Expected:** MAJOR interaction risk (hyperkalemia), especially with potassium already at 5.1 and eGFR 35. The combination requires close monitoring, not necessarily avoidance — but the agent must flag the risk.

---

### Step 5: Check Dosing for Spironolactone Given Renal Function

**Tool:** `check_drug_dosing`
```
drug: "spironolactone"
patient_vars: { "egfr": 35, "potassium": 5.1, "weight_kg": 82 }
```

**Expected:** Low starting dose (12.5–25 mg daily) given CKD Stage 3b and borderline potassium. Max dose may be restricted.

**Critical Decision:** With K+ already at 5.1 and eGFR 35, starting an MRA carries real hyperkalemia risk. The dosing response should reflect the need for cautious initiation.

---

### Step 6: Check Monitoring Requirements for Spironolactone

**Tool:** `check_monitoring_requirements`
```
intervention: "spironolactone"
patient_vars: { "egfr": 35, "potassium": 5.1 }
```

**Expected:** Potassium and creatinine monitoring within 1 week of initiation, then at 1 month, then every 3 months. Alert threshold for K+ ≥ 5.5, stop threshold for K+ ≥ 6.0.

---

### Step 7: Query SGLT2i Eligibility via Clinical Graph

**Tool:** `query_clinical_graph`
```
intent: "treatment_selection"
concepts: ["SGLT2 Inhibitor", "heart_failure_reduced_ef"]
patient_vars: { "egfr": 35, "lvef": 28 }
guideline_filter: "aha_acc_hf_2022"
```

**Expected:** SGLT2i (dapagliflozin or empagliflozin) is recommended for HFrEF regardless of diabetes status. eGFR ≥ 20 is the typical cutoff — this patient at eGFR 35 qualifies.

**Critical Decision:** Adding dapagliflozin would give the patient 3 of the 4 GDMT pillars (beta blocker + MRA + SGLT2i) despite the ARNi contraindication.

---

### Step 8: Fetch Evidence for a Recommendation

**Tool:** `fetch_evidence_chunk`
```
chunk_id: <from any previous step's evidence field>
```

**Expected:** Returns the exact guideline text backing the recommendation — verifiable, DOI-traceable.

---

## Expected Outcome Summary

| Decision | Result | Safety Implication |
|----------|--------|--------------------|
| Upgrade to ARNi? | **BLOCKED** — absolute contraindication (angioedema history) | Prevents life-threatening reaction |
| Add MRA (spironolactone)? | **PROCEED WITH CAUTION** — hyperkalemia risk, low dose, close monitoring | Requires K+ < 5.0 ideally; weekly labs |
| Add SGLT2i (dapagliflozin)? | **RECOMMENDED** — eligible by eGFR and LVEF | Safest GDMT addition for this patient |
| Switch warfarin to DOAC? | **Consider separately** — not part of HF GDMT but relevant for AFib management | eGFR 35 affects DOAC dosing |

## Why This Scenario Is Valuable

1. **Contraindication catch:** The angioedema → ARNi block is a must-not-miss safety check
2. **Drug interaction awareness:** MRA + ARB + CKD = hyperkalemia risk cascade
3. **Dosing adjustment:** Renal impairment changes starting doses and monitoring frequency
4. **Multi-tool chaining:** No single tool answers the full question — the agent must compose results
5. **Evidence traceability:** Every recommendation should trace back to AHA/ACC HF 2022 guideline text

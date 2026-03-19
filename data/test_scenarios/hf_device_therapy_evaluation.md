# Critical Decision Scenario: Device Therapy Evaluation — CRT vs ICD with Ivabradine Eligibility

## Patient Profile

- **Age:** 56
- **Sex:** Female
- **Weight:** 72 kg
- **Primary Diagnosis:** Nonischemic dilated cardiomyopathy, HFrEF (LVEF 28%)
- **Comorbidities:** Hypertension, Obesity (BMI 31)
- **History:** Diagnosed with HFrEF 8 months ago. On max-tolerated GDMT for 6 months. No angioedema. No prior MI.
- **ECG:** Sinus rhythm, LBBB, QRS duration 162 ms
- **Resting heart rate:** 78 bpm (on carvedilol 25 mg BID)

### Current Medications

| Drug | Dose | Frequency |
|------|------|-----------|
| Sacubitril/Valsartan | 97 mg | BID |
| Carvedilol | 25 mg | BID |
| Spironolactone | 50 mg | Daily |
| Dapagliflozin | 10 mg | Daily |
| Amlodipine | 5 mg | Daily |

### Current Labs

| Lab | Value | Reference |
|-----|-------|-----------|
| eGFR | 78 mL/min/1.73m2 | >60 |
| Potassium | 4.4 mEq/L | 3.5-5.0 |
| BNP | 450 pg/mL | <100 |
| Creatinine | 0.9 mg/dL | 0.6-1.1 |
| Sodium | 138 mEq/L | 136-145 |
| TSH | 2.1 mIU/L | 0.4-4.0 |

---

## Clinical Question

This patient is on all 4 GDMT pillars at target doses, yet remains symptomatic (NYHA Class III). Her ECG shows sinus rhythm with LBBB and QRS 162 ms. The attending wants to evaluate device therapy eligibility (CRT, ICD, or CRT-D) and consider ivabradine for heart rate reduction. The "trick" here is that the patient meets **both** CRT and ICD criteria — the answer is a combined CRT-D device, and the agent must synthesize multiple recommendation paths to arrive at this conclusion.

---

## Decision Chain (8 steps)

### Step 1: List Available Guidelines

**Tool:** `list_available_guidelines`

Confirm AHA/ACC HF 2022 is loaded. Device therapy recommendations (Section 7.4) are critical for this scenario.

---

### Step 2: Query CRT Eligibility

**Tool:** `query_clinical_graph`
```
intent: "device_therapy"
concepts: ["CRT", "cardiac_resynchronization_therapy"]
patient_vars: { "LVEF": 28, "QRS_duration": 162, "QRS_morphology": "LBBB", "heart_rhythm": "sinus", "NYHA_class": 3 }
guideline_filter: "aha_acc_hf_2022"
```

**Expected:** Strong recommendation (Class I) for CRT — all 5 conditions met: LVEF <= 35%, sinus rhythm, LBBB, QRS >= 150 ms, NYHA >= 2. The graph should return `conditions_met: true` for rec_003 (Implant CRT). Additional CRT variants (non-LBBB, shorter QRS) should show `conditions_met: false`.

**Critical Decision:** This is the strongest CRT indication (LBBB + QRS >= 150 ms). The agent must recognize this as Class I, not merely "can be useful" (Class IIa).

---

### Step 3: Query ICD Eligibility

**Tool:** `query_clinical_graph`
```
intent: "device_therapy"
concepts: ["ICD", "heart_failure"]
patient_vars: { "LVEF": 28, "NYHA_class": 3, "HF_type": "HFrEF" }
guideline_filter: "aha_acc_hf_2022"
```

**Expected:** Strong recommendation for ICD (LVEF <= 35%, NYHA II-III, HFrEF). The nonischemic etiology is relevant — the patient must have been on GDMT for adequate time (she has been for 6+ months, which satisfies the guideline requirement).

**Why this matters:** The patient independently qualifies for BOTH CRT and ICD. The agent should synthesize these into a CRT-D (combination) device recommendation, which provides both resynchronization and defibrillation.

---

### Step 4: Find Treatment Options to Confirm GDMT Optimization

**Tool:** `find_treatment_options`
```
condition: "heart_failure_reduced_ef"
patient_vars: { "LVEF": 28, "NYHA_class": 3, "eGFR": 78, "potassium": 4.4, "HF_type": "HFrEF" }
```

**Expected:** All 4 GDMT pillars should appear with `conditions_met: true`. Ivabradine should also appear as a moderate recommendation (LVEF <= 35%, NYHA II-III, heart rate >= 70 — her HR is 78). This confirms the patient has additional pharmacologic options before considering advanced therapies.

---

### Step 5: Check Dosing for Ivabradine

**Tool:** `check_drug_dosing`
```
drug: "ivabradine"
patient_vars: { "LVEF": 28, "heart_rate": 78, "NYHA_class": 3 }
```

**Expected:** Starting dose 5 mg BID, target 7.5 mg BID. Titrate based on heart rate response — increase after 2 weeks if HR remains >= 70.

**Critical Decision:** Ivabradine requires heart rate >= 70 bpm on maximally tolerated beta blocker. This patient's HR is 78 on carvedilol 25 mg BID (at target for her weight of 72 kg, since <=85 kg target is 25 mg BID). She qualifies.

---

### Step 6: Check Carvedilol Dosing to Confirm Target Dose

**Tool:** `check_drug_dosing`
```
drug: "carvedilol"
patient_vars: { "LVEF": 28, "weight_kg": 72 }
```

**Expected:** Starting dose 3.125 mg BID, target 25-50 mg BID. Max dose: 50 mg BID for >85 kg, 25 mg BID for <=85 kg. At 72 kg, her current 25 mg BID IS the target dose — confirming she's maximized on beta blocker.

**Why this matters:** Ivabradine is only appropriate when the beta blocker is at max tolerated dose. The weight-based max dose for carvedilol (<=85 kg → 25 mg BID) must be checked to validate ivabradine eligibility.

---

### Step 7: Check Contraindications for Sacubitril/Valsartan (Confirm No Issues)

**Tool:** `check_contraindications`
```
intervention: "sacubitril_valsartan"
patient_vars: { "history_of_angioedema": false, "potassium": 4.4, "eGFR": 78 }
```

**Expected:** Angioedema contraindication shows `conditions_met: false` (no angioedema history). No active contraindications — confirms current ARNi therapy is appropriate.

---

### Step 8: Fetch Evidence for CRT Recommendation

**Tool:** `fetch_evidence_chunk`
```
chunk_id: <from Step 2 evidence field>
```

**Expected:** Returns the guideline text: "For patients who have LVEF <=35%, sinus rhythm, LBBB with QRS duration >=150 ms, and NYHA class II, III, or ambulatory IV symptoms on GDMT, CRT is indicated..."

---

## Expected Outcome Summary

| Decision | Result | Safety Implication |
|----------|--------|--------------------|
| CRT? | **STRONGLY RECOMMENDED** — Class I (LBBB + QRS >= 150 + sinus + LVEF <= 35% + NYHA III) | Reduces mortality, hospitalizations, improves QOL |
| ICD? | **RECOMMENDED** — LVEF <= 35%, NYHA III, nonischemic DCM on GDMT >= 6 months | Primary prevention of sudden cardiac death |
| Combined CRT-D? | **YES** — qualifies for both independently, combined device is standard | Single procedure for both resynchronization and defibrillation |
| Add ivabradine? | **RECOMMENDED** — HR 78 on max beta blocker (25 mg BID at <=85 kg target) | Additional HR reduction may improve outcomes |
| Beta blocker change? | **NO** — already at weight-based target (25 mg BID for <=85 kg) | Do not uptitrate further |
| GDMT adequate? | **YES** — all 4 pillars at target doses | Device therapy is the next escalation step |

## Why This Scenario Is Valuable

1. **Device therapy synthesis:** Patient qualifies for both CRT and ICD independently — agent must synthesize into CRT-D recommendation (not just list them separately)
2. **Multi-condition evaluation:** CRT eligibility depends on 5 simultaneous conditions (LVEF, QRS, morphology, rhythm, NYHA) — tests the graph's condition evaluation engine thoroughly
3. **Weight-based dosing verification:** Carvedilol max dose depends on body weight — the agent must check this to validate ivabradine eligibility
4. **Pharmacologic before device is confirmed:** All 4 GDMT pillars are maximized before device discussion — tests that the agent verifies this prerequisite
5. **Complementary to existing scenarios:** Scenarios 1-2 focus on medication safety; this scenario tests the device therapy recommendation pathway and condition evaluation

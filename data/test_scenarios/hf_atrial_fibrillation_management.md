# Critical Decision Scenario: HFrEF with Atrial Fibrillation — Rhythm Control, Anticoagulation, and CRT in AF

## Patient Profile

- **Age:** 67
- **Sex:** Male
- **Weight:** 81 kg
- **Primary Diagnosis:** HFrEF (LVEF 30%)
- **Comorbidities:** Persistent Atrial Fibrillation (rate poorly controlled), Hypertension, Prior TIA (2 years ago), Type 2 Diabetes
- **History:** Failed rate control with metoprolol (HR remains 110-120 at rest). No angioedema. MI 3 years ago.
- **ECG:** Atrial fibrillation, ventricular rate 115 bpm, QRS 148 ms, non-LBBB (RBBB pattern)

### Current Medications

| Drug | Dose | Frequency |
|------|------|-----------|
| Sacubitril/Valsartan | 97 mg | BID |
| Metoprolol succinate | 200 mg | Daily |
| Spironolactone | 25 mg | Daily |
| Empagliflozin | 10 mg | Daily |
| Apixaban | 5 mg | BID |
| Furosemide | 40 mg | Daily |

### Current Labs

| Lab | Value | Reference |
|-----|-------|-----------|
| eGFR | 52 mL/min/1.73m2 | >60 |
| Potassium | 4.6 mEq/L | 3.5-5.0 |
| BNP | 980 pg/mL | <100 |
| Creatinine | 1.4 mg/dL | 0.7-1.3 |
| INR | 1.0 | 0.8-1.2 |
| TSH | 1.8 mIU/L | 0.4-4.0 |

---

## Clinical Question

This patient has HFrEF on full GDMT but with poorly controlled atrial fibrillation despite max-dose metoprolol. The rapid ventricular rate (115 bpm) is likely contributing to his HF symptoms. The attending wants to address: (1) Rhythm control options safe in HFrEF, (2) Anticoagulation adequacy, (3) Whether this patient qualifies for CRT despite being in AF, and (4) Whether AV nodal ablation is appropriate. The "trick" is that standard antiarrhythmics (class IC, dronedarone) are HARMFUL in HFrEF — only amiodarone and dofetilide are safe.

---

## Decision Chain (8 steps)

### Step 1: List Available Guidelines

**Tool:** `list_available_guidelines`

Confirm AHA/ACC HF 2022 is loaded.

---

### Step 2: Query AF Management in Heart Failure

**Tool:** `query_clinical_graph`
```
intent: "treatment_selection"
concepts: ["atrial_fibrillation", "amiodarone", "dofetilide", "heart_failure"]
patient_vars: { "HF_type": "HFrEF", "heart_rhythm": "atrial fibrillation", "AF_type": "persistent" }
```

**Expected:**
- Amiodarone — moderate_for (neutral mortality in HFrEF)
- Dofetilide — indicated (neutral mortality in HFrEF)
- Catheter ablation — moderate_for
- AV nodal ablation — moderate_for (when rate control fails)
- CRT in AF — moderate_for (requires near 100% ventricular pacing)
- DOAC preferred over warfarin
- Class IC antiarrhythmics and dronedarone — HARMFUL in HFrEF (not returned as options)

**Critical Decision:** The evidence text should confirm "Amiodarone and dofetilide are the only antiarrhythmic agents with neutral effects on mortality in HFrEF" and "class IC antiarrhythmic medications and dronedarone may increase the risk of mortality."

---

### Step 3: Calculate CHA2DS2-VASc Score

**Tool:** `execute_clinical_calculator`
```
calculator_id: "calculate_chadsvasc"
parameters: {
  "congestive_heart_failure": true,
  "hypertension": true,
  "age": 67,
  "diabetes": true,
  "stroke_tia_thromboembolism": true,
  "vascular_disease": true,
  "female_sex": false
}
```

**Expected:** Score = 7 (CHF=1, HTN=1, Age 65-74=1, DM=1, Stroke/TIA=2, Vasc=1, Male=0). Very high stroke risk — anticoagulation is absolutely mandatory.

**Why this matters:** With prior TIA, the stroke risk is extremely high. The calculator integration confirms anticoagulation adequacy and tests that the system prioritizes stroke prevention.

---

### Step 4: Check Drug Interaction — Amiodarone + Apixaban

**Tool:** `check_drug_interaction`
```
drug_a: "amiodarone"
drug_b: "apixaban"
```

**Expected:** If the graph has this interaction, it should flag that amiodarone inhibits P-glycoprotein and may increase apixaban levels. If not in the graph, this tests a known gap.

---

### Step 5: Query CRT Eligibility in Atrial Fibrillation

**Tool:** `query_clinical_graph`
```
intent: "device_therapy"
concepts: ["CRT", "cardiac_resynchronization_therapy"]
patient_vars: { "LVEF": 30, "heart_rhythm": "atrial fibrillation", "QRS_duration": 148, "NYHA_class": 3 }
guideline_filter: "aha_acc_hf_2022"
```

**Expected:** CRT in AF (rec_007): moderate_for — requires LVEF <=35%, AF, and either AV nodal ablation or rate control to allow near 100% ventricular pacing. The standard CRT criteria (LBBB + QRS >=150 + sinus) will show conditions_met: false because the patient is in AF, not sinus. But the AF-specific CRT recommendation should match.

**Critical Decision:** CRT in AF has different criteria than in sinus rhythm. The QRS of 148 ms with non-LBBB pattern is borderline — and the AF-specific recommendation doesn't require specific QRS criteria, just that CRT criteria are otherwise met or ventricular pacing is needed.

---

### Step 6: Query AV Nodal Ablation Eligibility

**Tool:** `query_clinical_graph`
```
intent: "treatment_selection"
concepts: ["AV_nodal_ablation", "atrial_fibrillation", "heart_failure"]
patient_vars: { "LVEF": 30, "heart_rhythm": "atrial fibrillation", "AF_type": "persistent", "rhythm_control_failed_or_undesired": true, "ventricular_rate": "rapid despite medical therapy" }
```

**Expected:** AV nodal ablation is moderate_for when: AF present, LVEF <=50%, rhythm control failed or undesired, rapid ventricular rate despite medical therapy. This patient meets all criteria.

---

### Step 7: Check Monitoring for Spironolactone (Ongoing)

**Tool:** `check_monitoring_requirements`
```
intervention: "spironolactone"
patient_vars: { "eGFR": 52, "potassium": 4.6 }
```

**Expected:** Standard monitoring — K+, creatinine, eGFR. With K+ at 4.6 (approaching 5.0 alert), frequency should be maintained at every 3 months minimum.

---

### Step 8: Fetch Evidence for Antiarrhythmic Safety

**Tool:** `fetch_evidence_chunk`
```
chunk_id: <from Step 2 evidence about amiodarone/dofetilide>
```

**Expected:** "Amiodarone and dofetilide are the only antiarrhythmic agents with neutral effects on mortality in clinical trials of patients with HFrEF."

---

## Expected Outcome Summary

| Decision | Result | Safety Implication |
|----------|--------|--------------------|
| Rhythm control agent? | **Amiodarone or dofetilide ONLY** — all others harmful in HFrEF | Class IC and dronedarone increase mortality in HFrEF |
| Anticoagulation adequate? | **YES** — CHA2DS2-VASc 7, very high risk | Must continue; DOAC preferred over warfarin |
| Catheter ablation? | **CONSIDER** — moderate recommendation for HF + AF | May restore sinus rhythm and improve LV function |
| AV nodal ablation + CRT? | **CONSIDER** — failed rate control, AF + LVEF <=35% | Requires commitment to permanent pacing; CRT provides resynchronization |
| Standard CRT criteria met? | **NO** — AF (not sinus), non-LBBB, QRS <150 ms | Does NOT meet standard CRT criteria; AF-specific pathway applies instead |
| Ivabradine? | **CONTRAINDICATED** — requires sinus rhythm | Ivabradine is ineffective and potentially harmful in AF |

## Why This Scenario Is Valuable

1. **Antiarrhythmic safety in HFrEF:** Only amiodarone and dofetilide are safe — tests that the system correctly excludes class IC and dronedarone
2. **CRT in AF vs. sinus rhythm:** Different eligibility criteria — tests that the graph has AF-specific CRT recommendations
3. **AV nodal ablation pathway:** Rate control failure triggers this procedural option — tests multi-step decision (failed rate control → ablation + CRT)
4. **High CHA2DS2-VASc with calculator:** Score of 7 with prior TIA — tests calculator integration for anticoagulation decisions
5. **Ivabradine negative test:** Ivabradine requires sinus rhythm — agent must NOT recommend it in AF despite meeting other criteria (LVEF <=35%, HR >=70)
6. **Complements Scenario 4:** Scenario 4 tests CRT in sinus rhythm with LBBB; this tests CRT in AF with non-LBBB

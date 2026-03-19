# Critical Decision Scenario: Post-Hospitalization GDMT Escalation — Vericiguat, Digoxin, Iron, and Diuretic Optimization

## Patient Profile

- **Age:** 63
- **Sex:** Male
- **Weight:** 78 kg
- **Primary Diagnosis:** HFrEF (LVEF 32%), recently hospitalized for acute decompensation
- **Comorbidities:** CKD Stage 3a, Iron Deficiency (ferritin 45, TSAT 15%), Hyponatremia
- **History:** Discharged 2 weeks ago after 7-day hospitalization for volume overload. On all 4 GDMT pillars at target doses. Persistent NYHA III symptoms despite optimization. No angioedema.
- **HF Stage:** C (recently hospitalized)

### Current Medications

| Drug | Dose | Frequency |
|------|------|-----------|
| Sacubitril/Valsartan | 97 mg | BID |
| Carvedilol | 25 mg | BID |
| Spironolactone | 50 mg | Daily |
| Dapagliflozin | 10 mg | Daily |
| Furosemide | 80 mg | BID |
| Potassium chloride | 20 mEq | BID |

### Current Labs

| Lab | Value | Reference |
|-----|-------|-----------|
| eGFR | 48 mL/min/1.73m2 | >60 |
| Potassium | 4.3 mEq/L | 3.5-5.0 |
| BNP | 1100 pg/mL | <100 |
| Creatinine | 1.5 mg/dL | 0.7-1.3 |
| Sodium | 131 mEq/L | 136-145 |
| Hemoglobin | 11.2 g/dL | 13.5-17.5 |
| Ferritin | 45 ng/mL | 30-400 |
| TSAT | 15% | 20-50% |

---

## Clinical Question

This patient is on ALL 4 GDMT pillars at target doses but remains symptomatic post-hospitalization. What additional therapies can be added beyond the core 4 pillars? The guideline provides several "add-on" options for refractory HFrEF: vericiguat (post-hospitalization), digoxin (persistent symptoms), ferric carboxymaltose (iron deficiency), and diuretic optimization (hyponatremia → vasopressin antagonist consideration). The "trick" is that the 4-pillar paradigm is necessary but not always sufficient — the agent must know about second-line options.

---

## Decision Chain (8 steps)

### Step 1: List Available Guidelines

**Tool:** `list_available_guidelines`

Confirm AHA/ACC HF 2022 is loaded.

---

### Step 2: Find Treatment Options Including Second-Line

**Tool:** `find_treatment_options`
```
condition: "heart_failure_reduced_ef"
patient_vars: { "LVEF": 32, "NYHA_class": 3, "HF_type": "HFrEF", "HF_stage": "C", "eGFR": 48, "potassium": 4.3, "heart_rate": 68, "iron_deficiency": true }
```

**Expected:** Beyond the 4 pillars (already on all), second-line options should appear:
- Vericiguat — weak_for (LVEF <45%, NYHA II-IV, Stage C)
- Digoxin — weak_for (HFrEF, Stage C)
- Ferric Carboxymaltose — moderate_for (iron deficiency + HFrEF)
- Ivabradine — moderate_for ONLY if HR >=70 (patient's HR is 68, so conditions_met: false)

**Critical Decision:** The agent must identify that standard GDMT is maximized and correctly navigate to second-line options. Ivabradine should NOT be recommended with HR 68 (below the >=70 threshold).

---

### Step 3: Check Dosing for Vericiguat

**Tool:** `check_drug_dosing`
```
drug: "vericiguat"
patient_vars: { "LVEF": 32, "NYHA_class": 3, "HF_stage": "C" }
```

**Expected:** Starting dose 2.5 mg daily, target 10 mg daily. Titrate: double every 2 weeks. Vericiguat is specifically indicated after a worsening HF event (recent hospitalization).

---

### Step 4: Check Dosing for Digoxin

**Tool:** `check_drug_dosing`
```
drug: "digoxin"
patient_vars: { "LVEF": 32, "eGFR": 48, "HF_type": "HFrEF" }
```

**Expected:** Starting dose 0.125-0.25 mg daily, max 0.25 mg/day. Individualize to serum level 0.5-<0.9 ng/mL. With eGFR 48, start at the lower end (0.125 mg) to avoid accumulation.

**Why this matters:** Digoxin has a narrow therapeutic index and renal clearance. The agent must adjust dosing for CKD and emphasize serum level monitoring.

---

### Step 5: Check Drug Interaction — Vericiguat + Spironolactone

**Tool:** `check_drug_interaction`
```
drug_a: "vericiguat"
drug_b: "spironolactone"
```

**Expected:** Limited data in graph. If present, no significant interaction. Tests how the system handles newer drug combinations.

---

### Step 6: Check Monitoring for Spironolactone (Ongoing)

**Tool:** `check_monitoring_requirements`
```
intervention: "spironolactone"
patient_vars: { "eGFR": 48, "potassium": 4.3 }
```

**Expected:** Standard K+, creatinine, eGFR monitoring. Patient is on spironolactone + KCl supplementation — agent should note that potassium supplementation with MRA requires careful monitoring.

---

### Step 7: Query Iron Deficiency Treatment

**Tool:** `query_clinical_graph`
```
intent: "treatment_selection"
concepts: ["iron_deficiency", "ferric_carboxymaltose", "heart_failure"]
patient_vars: { "HF_type": "HFrEF", "iron_deficiency": true }
```

**Expected:** Ferric carboxymaltose — moderate_for (HFrEF + iron deficiency, with or without anemia). IV iron replacement improves functional status and QOL.

---

### Step 8: Calculate GRACE Score (Risk Stratification)

**Tool:** `execute_clinical_calculator`
```
calculator_id: "calculate_charlson"
parameters: {
  "congestive_heart_failure": true,
  "moderate_severe_renal_disease": false,
  "age": 63
}
```

**Expected:** Moderate CCI reflecting CHF (1) + age adjustment (1 for age 63). Lower comorbidity burden supports aggressive therapy.

---

## Expected Outcome Summary

| Decision | Result | Safety Implication |
|----------|--------|--------------------|
| Add vericiguat? | **RECOMMENDED (weak)** — LVEF <45%, NYHA III, post-hospitalization | Shown to reduce HF hospitalization in VICTORIA trial |
| Add digoxin? | **CONSIDER (weak)** — persistent symptoms on full GDMT | Narrow therapeutic index; start low with eGFR 48, target level 0.5-<0.9 |
| IV iron (ferric carboxymaltose)? | **RECOMMENDED (moderate)** — ferritin 45, TSAT 15% | Improves functional status and QOL even without anemia |
| Add ivabradine? | **NOT ELIGIBLE** — HR 68 (below 70 bpm threshold) | Ivabradine requires HR >=70 on max beta blocker |
| Vasopressin antagonist? | **CONSIDER** — Na 131 (hyponatremia) | May help correct hyponatremia; limited long-term data |
| Diuretic adjustment? | **MONITOR** — on high-dose furosemide | Consider adding metolazone if diuretic resistance develops |

## Why This Scenario Is Valuable

1. **Beyond-4-pillar therapy:** Tests that the system knows about vericiguat, digoxin, ferric carboxymaltose, and vasopressin antagonists — not just the core 4 pillars
2. **Post-hospitalization context:** Vericiguat is specifically for post-worsening HF — tests that HF_stage and recent hospitalization affect recommendations
3. **Ivabradine negative test (HR threshold):** HR 68 is below the >=70 cutoff — tests precise threshold evaluation when the margin is narrow
4. **Iron deficiency management:** IV iron in HF is evidence-based but often missed — tests non-drug (infusion) therapy recommendations
5. **Narrow therapeutic index drug:** Digoxin dosing with renal adjustment + serum level targeting — tests safety-critical dosing
6. **Complements existing scenarios:** Scenarios 1-5 focus on the 4 GDMT pillars; this scenario tests what comes after GDMT is maximized

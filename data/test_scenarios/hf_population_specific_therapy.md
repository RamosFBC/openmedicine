# Critical Decision Scenario: African American HFrEF Patient — Race-Specific GDMT and Anticoagulation

## Patient Profile

- **Age:** 62
- **Sex:** Male
- **Weight:** 95 kg
- **Primary Diagnosis:** HFrEF (LVEF 25%)
- **Comorbidities:** Atrial Fibrillation (persistent), Hypertension, Type 2 Diabetes, Peripheral Artery Disease
- **History:** No angioedema history, no prior stroke/TIA
- **Race:** African American

### Current Medications

| Drug | Dose | Frequency |
|------|------|-----------|
| Sacubitril/Valsartan | 49 mg | BID |
| Carvedilol | 12.5 mg | BID |
| Dapagliflozin | 10 mg | Daily |
| Furosemide | 40 mg | BID |
| Metformin | 1000 mg | BID |
| Apixaban | 5 mg | BID |

### Current Labs

| Lab | Value | Reference |
|-----|-------|-----------|
| eGFR | 55 mL/min/1.73m2 | >60 |
| Potassium | 4.2 mEq/L | 3.5-5.0 |
| BNP | 1200 pg/mL | <100 |
| Creatinine | 1.4 mg/dL | 0.7-1.3 |
| HbA1c | 7.4% | <7.0 |
| INR | 1.1 | 0.8-1.2 |
| Hemoglobin | 12.8 g/dL | 13.5-17.5 |

---

## Clinical Question

This African American patient has HFrEF with LVEF 25% and NYHA Class III symptoms despite being on 3 of 4 GDMT pillars (ARNi + beta blocker + SGLT2i). He is missing an MRA. Additionally, as an African American with NYHA III HFrEF, he may qualify for hydralazine/isosorbide dinitrate (H-ISDN) as add-on therapy per AHA/ACC guidelines. He also has persistent atrial fibrillation — the attending wants to verify anticoagulation adequacy using the CHA2DS2-VASc calculator. Walk through each decision.

---

## Decision Chain (8 steps)

### Step 1: List Available Guidelines

**Tool:** `list_available_guidelines`

Confirm AHA/ACC HF 2022 is loaded. This guideline contains the Class I recommendation for H-ISDN in African American patients with NYHA III-IV HFrEF.

---

### Step 2: Find Treatment Options with Race-Specific Recommendations

**Tool:** `find_treatment_options`
```
condition: "heart_failure_reduced_ef"
patient_vars: { "LVEF": 25, "NYHA_class": 3, "eGFR": 55, "potassium": 4.2, "race": "African American", "HF_type": "HFrEF" }
```

**Expected:** All 4 GDMT pillars plus Hydralazine and Isosorbide Dinitrate with `conditions_met: true` (race = African American, NYHA >= 3, LVEF <= 40%). Also: ICD recommendation (LVEF <= 35%, NYHA 2-3).

**Critical Decision:** The `race` variable should unlock H-ISDN as a strong recommendation. Without race data, this therapy would show as having missing variables. This tests population-specific treatment selection.

---

### Step 3: Check Dosing for Hydralazine

**Tool:** `check_drug_dosing`
```
drug: "hydralazine"
patient_vars: { "LVEF": 25, "NYHA_class": 3, "race": "African American" }
```

**Expected:** Starting dose 25-50 mg TID-QID, target 75 mg TID (fixed-dose combo) or 300 mg/day divided. The graph should return the full titration schedule.

**Why this matters:** H-ISDN dosing is complex (3-4 times daily, two drugs to titrate). An agent must communicate this clearly to avoid adherence issues.

---

### Step 4: Check Dosing for Spironolactone (the Missing MRA)

**Tool:** `check_drug_dosing`
```
drug: "spironolactone"
patient_vars: { "eGFR": 55, "potassium": 4.2, "weight_kg": 95 }
```

**Expected:** Starting dose 12.5-25 mg daily, target 50 mg daily. With eGFR 55 and K+ 4.2, this patient is well within safe initiation range — much more favorable than Scenario 1 (eGFR 35, K+ 5.1).

**Critical Decision:** This patient can safely start an MRA. The favorable labs mean standard dosing applies, unlike the cautious approach needed in renally impaired patients.

---

### Step 5: Check Drug Interaction — MRA + ARNi

**Tool:** `check_drug_interaction`
```
drug_a: "spironolactone"
drug_b: "sacubitril_valsartan"
patient_vars: { "potassium": 4.2, "eGFR": 55 }
```

**Expected:** MAJOR interaction (hyperkalemia risk from dual RAAS blockade). Severity = MAJOR, not ABSOLUTE — the combination is permissible with monitoring. The graph should return mechanism (dual RAAS blockade → potassium retention).

**Why this matters:** Unlike ACEi + ARNi (ABSOLUTE), MRA + ARNi is a monitored combination, not a hard block. The agent must distinguish these severity levels.

---

### Step 6: Check Monitoring for Spironolactone

**Tool:** `check_monitoring_requirements`
```
intervention: "spironolactone"
patient_vars: { "eGFR": 55, "potassium": 4.2 }
```

**Expected:** K+, creatinine, eGFR monitoring. Frequency: 1 week, 4 weeks, then every 3 months. Alert threshold: K+ >= 5.0. Stop threshold: K+ >= 5.5.

---

### Step 7: Calculate CHA2DS2-VASc for Anticoagulation Decision

**Tool:** `execute_clinical_calculator`
```
calculator_id: "calculate_chadsvasc"
parameters: {
  "congestive_heart_failure": true,
  "hypertension": true,
  "age": 62,
  "diabetes": true,
  "stroke_tia_thromboembolism": false,
  "vascular_disease": true,
  "female_sex": false
}
```

**Expected:** Score = 5 (CHF +1, HTN +1, Age 65-74 = 0 (age 62 is < 65), DM +1, Vascular +1, Male +0... actually age 62 is < 65 so age = 0). Let me recalculate: CHF=1, HTN=1, Age(62)=0, DM=1, Stroke=0, Vasc=1, Male=0. Score = 4.

A CHA2DS2-VASc of 4 strongly supports continued anticoagulation. The calculator should provide risk stratification and recommend anticoagulation.

**Critical Decision:** This step bridges the calculator engine and the graph engine — the agent uses a calculator to inform a treatment decision, demonstrating multi-tool reasoning.

---

### Step 8: Query Clinical Graph for Device Therapy

**Tool:** `query_clinical_graph`
```
intent: "device_therapy"
concepts: ["ICD", "heart_failure"]
patient_vars: { "LVEF": 25, "NYHA_class": 3, "HF_type": "HFrEF" }
guideline_filter: "aha_acc_hf_2022"
```

**Expected:** ICD is recommended (LVEF <= 35%, NYHA II-III, HFrEF). The graph should also note that CRT evaluation requires QRS duration — data not available in this scenario, which the agent should flag as a gap.

---

## Expected Outcome Summary

| Decision | Result | Safety Implication |
|----------|--------|--------------------|
| Add MRA (spironolactone)? | **RECOMMENDED** — favorable labs (K+ 4.2, eGFR 55), standard dosing | Complete all 4 GDMT pillars |
| Add H-ISDN? | **RECOMMENDED** — African American, NYHA III, LVEF <= 40% (Class I) | Population-specific mortality benefit (A-HeFT trial) |
| MRA + ARNi interaction? | **PROCEED WITH CAUTION** — MAJOR severity, not ABSOLUTE | Monitor K+ closely, but combination is standard practice |
| Continue anticoagulation? | **YES** — CHA2DS2-VASc 4, high stroke risk | Apixaban appropriate with eGFR 55 |
| ICD evaluation? | **EVALUATE** — meets LVEF/NYHA criteria | Primary prevention of sudden cardiac death |
| Beta blocker uptitration? | **CONSIDER** — carvedilol 12.5 mg is below target (25-50 mg for >85 kg) | Weight-based target: 50 mg BID for this 95 kg patient |

## Why This Scenario Is Valuable

1. **Population-specific therapy test:** H-ISDN recommendation requires `race == "African American"` — verifies the graph evaluates demographic conditions correctly
2. **Calculator + graph integration:** CHA2DS2-VASc calculation informs the anticoagulation decision, testing cross-engine reasoning
3. **Favorable vs. unfavorable labs contrast:** Unlike Scenarios 1-2 (borderline K+, low eGFR), this patient has favorable labs — tests that the system recommends standard dosing when appropriate, not just caution
4. **Complex dosing regimen:** H-ISDN requires TID-QID dosing of two drugs — tests the system's ability to communicate complex titration schedules
5. **Complementary to existing scenarios:** Covers population-specific and calculator integration patterns not tested by Scenarios 1-2

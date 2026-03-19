# Critical Decision Scenario: eGFR Boundary Testing with Ivabradine Add-On and Beta Blocker Uptitration

## Patient Profile

- **Age:** 71
- **Sex:** Male
- **Weight:** 68 kg
- **Primary Diagnosis:** Ischemic cardiomyopathy, HFrEF (LVEF 30%)
- **Comorbidities:** CKD Stage 4 (progressing), Type 2 Diabetes with nephropathy, Hypertension, Prior MI (14 months ago)
- **History:** No angioedema. Prior MI was anterior STEMI with PCI to LAD 14 months ago.
- **Resting heart rate:** 82 bpm

### Current Medications

| Drug | Dose | Frequency |
|------|------|-----------|
| Losartan | 50 mg | Daily |
| Metoprolol succinate | 50 mg | Daily |
| Furosemide | 80 mg | BID |
| Insulin glargine | 20 units | Nightly |
| Aspirin | 81 mg | Daily |
| Atorvastatin | 40 mg | Daily |

### Current Labs

| Lab | Value | Reference |
|-----|-------|-----------|
| eGFR | 22 mL/min/1.73m2 | >60 |
| Potassium | 5.2 mEq/L | 3.5-5.0 |
| BNP | 1800 pg/mL | <100 |
| Creatinine | 2.8 mg/dL | 0.7-1.3 |
| HbA1c | 8.1% | <7.0 |
| Hemoglobin | 10.2 g/dL | 13.5-17.5 |
| Sodium | 132 mEq/L | 136-145 |
| Digoxin level | not on digoxin | — |

---

## Clinical Question

This high-risk patient has HFrEF with severely reduced kidney function (eGFR 22) and elevated potassium (5.2). He is on only 2 of 4 GDMT pillars (ARB + beta blocker), both at sub-target doses. The attending wants to optimize GDMT but every escalation is constrained by renal function: Can he start an SGLT2i (eGFR threshold is 20)? Can he tolerate an MRA with K+ already above 5.0? Should he be upgraded to ARNi? And with a resting HR of 82 on sub-target beta blocker, is ivabradine appropriate, or should the beta blocker be uptitrated first?

The "trick" is that the eGFR of 22 is just barely above the SGLT2i threshold of >= 20, the K+ of 5.2 exceeds the MRA safe initiation threshold of < 5.0, and ivabradine is premature because the beta blocker is well below target dose.

---

## Decision Chain (8 steps)

### Step 1: List Available Guidelines

**Tool:** `list_available_guidelines`

Confirm AHA/ACC HF 2022 is loaded.

---

### Step 2: Find Treatment Options with Boundary Labs

**Tool:** `find_treatment_options`
```
condition: "heart_failure_reduced_ef"
patient_vars: { "LVEF": 30, "NYHA_class": 3, "eGFR": 22, "potassium": 5.2, "HF_type": "HFrEF" }
```

**Expected:** SGLT2i should show `conditions_met: true` (eGFR >= 20 threshold is met at eGFR 22). MRA/Spironolactone should show `conditions_met: false` because `potassium < 5.0` condition fails (K+ is 5.2). ARNi should show conditions met for LVEF/NYHA. Beta blocker and ACEi/ARB should be met.

**Critical Decision:** The eGFR 22 is right at the boundary. At eGFR 19, SGLT2i would NOT be eligible. The agent must evaluate this precisely, not round or approximate.

---

### Step 3: Check Dosing for Dapagliflozin at Low eGFR

**Tool:** `check_drug_dosing`
```
drug: "dapagliflozin"
patient_vars: { "eGFR": 22, "weight_kg": 68 }
```

**Expected:** Standard dose 10 mg daily. No renal dose adjustment for HF indication — eGFR >= 20 is sufficient. The graph should confirm eligibility.

**Why this matters:** Many clinicians hesitate at eGFR < 25. The 2022 guideline explicitly supports initiation down to eGFR >= 20 for the HF indication. This tests that the system correctly applies the updated threshold.

---

### Step 4: Check Contraindications for Spironolactone at Elevated K+

**Tool:** `check_contraindications`
```
intervention: "spironolactone"
patient_vars: { "potassium": 5.2, "eGFR": 22 }
```

**Expected:** The MRA eligibility conditions require K+ < 5.0 and eGFR > 30. This patient fails BOTH: K+ is 5.2 (above 5.0 threshold) and eGFR is 22 (below 30 threshold). MRA initiation is NOT safe.

**Critical Decision:** This is a hard block based on lab values, not drug allergy. The agent must recognize that both the potassium and renal thresholds are violated and defer MRA initiation until labs improve.

---

### Step 5: Check Dosing for Metoprolol Succinate — Uptitration Opportunity

**Tool:** `check_drug_dosing`
```
drug: "metoprolol_succinate"
patient_vars: { "LVEF": 30, "weight_kg": 68 }
```

**Expected:** Starting dose 12.5-25 mg daily, target 200 mg daily. Patient is on 50 mg daily — well below target. There is significant room for uptitration.

**Why this matters:** Ivabradine requires maximally tolerated beta blocker first (heart rate >= 70 on max dose). At 50 mg metoprolol (target 200 mg), the beta blocker should be uptitrated BEFORE considering ivabradine. This is a sequencing test.

---

### Step 6: Check Monitoring Requirements for the Current Regimen

**Tool:** `check_monitoring_requirements`
```
intervention: "losartan"
patient_vars: { "eGFR": 22, "potassium": 5.2 }
```

**Expected:** K+, creatinine, and eGFR monitoring. With eGFR 22 and K+ 5.2, the alert thresholds are already exceeded (K+ >= 5.0 is alert level). The system should flag that current ARB therapy needs close monitoring given the deteriorating renal function.

---

### Step 7: Check Drug Interaction — Considering ARNi Upgrade

**Tool:** `check_drug_interaction`
```
drug_a: "losartan"
drug_b: "sacubitril_valsartan"
```

**Expected:** While losartan (ARB) and ARNi don't have the ABSOLUTE interaction that ACEi + ARNi has, the system should return information about the need to discontinue the ARB before starting ARNi. The interaction is relevant for sequencing.

**Critical Decision:** Unlike ACEi → ARNi (which requires 36-hour washout), ARB → ARNi can be done more directly. However, in this patient with eGFR 22 and K+ 5.2, upgrading RAAS blockade is risky. The agent should weigh benefit vs. risk.

---

### Step 8: Calculate Charlson Comorbidity Index

**Tool:** `execute_clinical_calculator`
```
calculator_id: "calculate_charlson"
parameters: {
  "myocardial_infarction": true,
  "congestive_heart_failure": true,
  "peripheral_vascular_disease": false,
  "cerebrovascular_disease": false,
  "dementia": false,
  "chronic_pulmonary_disease": false,
  "connective_tissue_disease": false,
  "peptic_ulcer_disease": false,
  "mild_liver_disease": false,
  "uncomplicated_diabetes": false,
  "hemiplegia": false,
  "moderate_severe_renal_disease": true,
  "diabetes_with_end_organ_damage": true,
  "solid_tumor": false,
  "leukemia": false,
  "lymphoma": false,
  "moderate_severe_liver_disease": false,
  "metastatic_solid_tumor": false,
  "aids": false,
  "age": 71
}
```

**Expected:** High CCI score reflecting MI (1) + CHF (1) + moderate-severe renal disease (2) + diabetes with end-organ damage (2) + age adjustment (2 for age 71). Total = 8, indicating significant 10-year mortality risk.

**Why this matters:** The Charlson score contextualizes the aggressiveness of GDMT optimization — a CCI of 8 suggests competing mortality risks, which may influence how aggressively to titrate medications with narrow therapeutic windows.

---

## Expected Outcome Summary

| Decision | Result | Safety Implication |
|----------|--------|--------------------|
| Add SGLT2i (dapagliflozin)? | **RECOMMENDED** — eGFR 22 >= 20 threshold, barely eligible | Renoprotective benefit especially valuable in CKD4; monitor eGFR |
| Add MRA (spironolactone)? | **BLOCKED** — K+ 5.2 (> 5.0) AND eGFR 22 (< 30) | Both safety thresholds violated; defer until K+ and eGFR improve |
| Upgrade to ARNi? | **DEFER** — feasible in principle but high risk with eGFR 22 and K+ 5.2 | Enhanced RAAS blockade risks worsening hyperkalemia and renal function |
| Add ivabradine? | **PREMATURE** — beta blocker at 25% of target dose (50/200 mg) | Must uptitrate metoprolol first; ivabradine only after max beta blocker |
| Uptitrate metoprolol? | **YES** — 50 mg daily vs. target 200 mg daily | Slow titration (double every 2 weeks) with HR and BP monitoring |
| ICD evaluation? | **EVALUATE** — LVEF 30%, > 40 days post-MI, NYHA III | Meets criteria if reasonable expectation of > 1 year meaningful survival |
| Overall risk? | **HIGH** — Charlson CCI ~8, eGFR declining, K+ elevated | Competing mortality risks affect treatment aggressiveness |

## Why This Scenario Is Valuable

1. **Boundary value testing:** eGFR 22 is just 2 units above the SGLT2i cutoff (>= 20) — tests precise threshold evaluation, not approximate reasoning
2. **Double safety block:** MRA is blocked by BOTH K+ (> 5.0) and eGFR (< 30) — tests that the system checks multiple conditions, not just the first one that fails
3. **Sequencing discipline:** Ivabradine before max beta blocker is a common clinical error — the system must enforce "maximize beta blocker first" before adding ivabradine
4. **Risk stratification integration:** Charlson CCI provides mortality context that shapes how aggressively to optimize GDMT — tests calculator-informed clinical reasoning
5. **Complementary to existing scenarios:** Scenarios 1-2 test drug safety blocks; Scenario 3 tests population-specific therapy; this scenario tests threshold precision, sequencing discipline, and risk contextualization

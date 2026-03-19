# Critical Decision Scenario: Advanced Heart Failure (Stage D) — LVAD, Transplant, Inotropes, and Palliative Care

## Patient Profile

- **Age:** 54
- **Sex:** Male
- **Weight:** 75 kg
- **Primary Diagnosis:** Nonischemic dilated cardiomyopathy, HFrEF (LVEF 15%)
- **Comorbidities:** NYHA Class IV (ambulatory with inotropic support), CKD Stage 3a, recurrent ICD shocks
- **History:** On max-tolerated GDMT for 2+ years. CRT-D implanted 18 months ago. Three HF hospitalizations in past 6 months despite optimal medical therapy. Currently on dobutamine infusion.
- **Functional status:** Unable to perform activities of daily living without assistance

### Current Medications

| Drug | Dose | Frequency |
|------|------|-----------|
| Sacubitril/Valsartan | 49 mg | BID |
| Carvedilol | 3.125 mg | BID |
| Spironolactone | 25 mg | Daily |
| Empagliflozin | 10 mg | Daily |
| Furosemide | 80 mg | BID |
| Metolazone | 2.5 mg | Daily |
| Dobutamine | 5 mcg/kg/min | Continuous IV |
| Digoxin | 0.125 mg | Daily |

### Current Labs

| Lab | Value | Reference |
|-----|-------|-----------|
| eGFR | 38 mL/min/1.73m2 | >60 |
| Potassium | 4.5 mEq/L | 3.5-5.0 |
| BNP | 2800 pg/mL | <100 |
| Creatinine | 1.8 mg/dL | 0.7-1.3 |
| Sodium | 128 mEq/L | 136-145 |
| Hemoglobin | 11.0 g/dL | 13.5-17.5 |
| Albumin | 3.0 g/dL | 3.5-5.0 |
| Digoxin level | 0.8 ng/mL | 0.5-<0.9 |

---

## Clinical Question

This patient has advanced Stage D heart failure — inotrope-dependent, NYHA IV, LVEF 15%, recurrent hospitalizations despite maximal medical and device therapy. The guideline decision tree now branches beyond GDMT into: (1) Is the patient a transplant candidate? (2) Is LVAD (durable MCS) appropriate? (3) What is the role of palliative care? (4) Should diuretic therapy be intensified? The "trick" is that GDMT is already maximized — the decisions now are about advanced therapies and goals of care, not more drugs.

---

## Decision Chain (8 steps)

### Step 1: List Available Guidelines

**Tool:** `list_available_guidelines`

Confirm AHA/ACC HF 2022 is loaded. Stage D / advanced HF recommendations are critical.

---

### Step 2: Find Treatment Options for Stage D

**Tool:** `find_treatment_options`
```
condition: "heart_failure_reduced_ef"
patient_vars: { "LVEF": 15, "NYHA_class": 4, "HF_type": "HFrEF", "HF_stage": "D", "inotrope_dependent": true, "MCS_or_transplant_eligible": true, "eGFR": 38, "potassium": 4.5 }
```

**Expected:** Advanced therapy recommendations appear:
- LVAD — strong_for (NYHA IV, inotrope dependent)
- Cardiac Transplantation — moderate_for (Stage D, MCS/transplant eligible)
- Mechanical Circulatory Support — moderate_for (Stage D)
- Inotrope — moderate_for (Stage D, as bridge)
- Durable MCS — moderate_for (NYHA IV)
- Standard GDMT drugs should still appear but at already-met doses

**Critical Decision:** The system must transition from "optimize GDMT" to "evaluate advanced therapies." An agent that keeps recommending drug uptitration misses that this patient needs LVAD/transplant evaluation.

---

### Step 3: Query Advanced Therapy Decision Tree

**Tool:** `query_clinical_graph`
```
intent: "treatment_selection"
concepts: ["advanced_heart_failure", "LVAD", "transplant", "inotrope"]
patient_vars: { "HF_stage": "D", "MCS_or_transplant_eligible": true, "NYHA_class": 4, "inotrope_dependent": true, "LVEF": 15 }
```

**Expected:**
- LVAD (strong_for) — NYHA IV, inotrope-dependent
- Cardiac Transplantation (moderate_for) — Stage D, eligible
- Mechanical Circulatory Support (moderate_for) — Stage D
- Inotrope (moderate_for) — as bridge to definitive therapy
- Palliative Care (weak_for) — if NOT MCS/transplant eligible

**Why this matters:** The palliative care option should NOT appear prominently because the patient IS eligible for MCS/transplant. If eligibility were false, palliative care would be the primary recommendation.

---

### Step 4: Check Dosing for Digoxin (Narrow Therapeutic Index)

**Tool:** `check_drug_dosing`
```
drug: "digoxin"
patient_vars: { "LVEF": 15, "HF_type": "HFrEF", "eGFR": 38 }
```

**Expected:** Starting dose 0.125-0.25 mg daily, max 0.25 mg/day, individualized to serum level 0.5-<0.9 ng/mL. Patient's current level of 0.8 ng/mL is within the narrow therapeutic window.

**Critical Decision:** Digoxin has a very narrow therapeutic index. Serum levels must stay between 0.5 and <0.9 ng/mL. With declining renal function (eGFR 38), accumulation risk increases. The agent must flag this ongoing risk.

---

### Step 5: Check Dosing for Metolazone (Diuretic Resistance)

**Tool:** `check_drug_dosing`
```
drug: "metolazone"
patient_vars: { "eGFR": 38 }
```

**Expected:** Starting dose 2.5 mg daily, max 20 mg. Metolazone is used for sequential nephron blockade when loop diuretics alone are insufficient (diuretic resistance).

---

### Step 6: Check Monitoring for Current Regimen

**Tool:** `check_monitoring_requirements`
```
intervention: "spironolactone"
patient_vars: { "eGFR": 38, "potassium": 4.5 }
```

**Expected:** K+, creatinine, eGFR monitoring. With eGFR 38 (approaching the 30 threshold), increased monitoring frequency is warranted. The system should flag that eGFR is nearing the stop threshold (<=30).

---

### Step 7: Calculate Charlson Comorbidity Index

**Tool:** `execute_clinical_calculator`
```
calculator_id: "calculate_charlson"
parameters: {
  "congestive_heart_failure": true,
  "moderate_severe_renal_disease": false,
  "age": 54
}
```

**Expected:** Lower CCI than Scenario 5's elderly patient (no MI, no diabetes, younger age). This supports that the patient has good non-cardiac health and is a reasonable MCS/transplant candidate.

---

### Step 8: Query Device Therapy (Confirm CRT-D Already In Place)

**Tool:** `query_clinical_graph`
```
intent: "device_therapy"
concepts: ["ICD", "CRT", "heart_failure"]
patient_vars: { "LVEF": 15, "NYHA_class": 4, "HF_type": "HFrEF" }
guideline_filter: "aha_acc_hf_2022"
```

**Expected:** ICD/CRT recommendations will show as met, confirming that device therapy has already been appropriately implemented. The next step is LVAD/transplant, not more device optimization.

---

## Expected Outcome Summary

| Decision | Result | Safety Implication |
|----------|--------|--------------------|
| More GDMT optimization? | **NO** — already on all 4 pillars, max tolerated doses | Further uptitration unlikely to help; advanced therapy needed |
| LVAD evaluation? | **STRONGLY RECOMMENDED** — NYHA IV, inotrope dependent, eligible | Bridge to transplant or destination therapy |
| Transplant evaluation? | **RECOMMENDED** — Stage D, eligible, age 54, low non-cardiac comorbidity | Definitive therapy for end-stage HF |
| Continue inotropes? | **YES as bridge** — bridge to MCS/transplant | Not a long-term solution; increases arrhythmia risk |
| Palliative care? | **PARALLEL track** — not instead of advanced therapy | Goals of care discussion alongside advanced therapy evaluation |
| Digoxin level? | **MONITOR CLOSELY** — 0.8 ng/mL in therapeutic range but eGFR declining | Accumulation risk with worsening renal function |
| Hyponatremia (Na 128)? | **FLAG** — consider vasopressin antagonist | Hyponatremia is a poor prognostic marker in HF |

## Why This Scenario Is Valuable

1. **Beyond-GDMT decision making:** Tests that the system recognizes when drug optimization is exhausted and advanced therapies are needed
2. **Stage D pathway:** LVAD/transplant/inotrope/palliative care — a completely different decision tree than Stage C GDMT
3. **MCS eligibility branching:** Palliative care recommendation changes based on MCS/transplant eligibility — tests conditional branching
4. **Digoxin therapeutic monitoring:** Narrow therapeutic index drug with renal accumulation risk — tests monitoring-focused reasoning
5. **Diuretic resistance management:** Metolazone for sequential nephron blockade — tests advanced diuretic strategy
6. **Complements all other scenarios:** All previous scenarios focus on adding/optimizing drugs; this is about transitioning to surgical/device advanced therapy

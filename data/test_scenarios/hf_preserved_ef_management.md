# Critical Decision Scenario: HFpEF Management — Different Evidence Landscape and Hypertension-Driven Therapy

## Patient Profile

- **Age:** 72
- **Sex:** Female
- **Weight:** 88 kg
- **Primary Diagnosis:** HFpEF (LVEF 58%)
- **Comorbidities:** Hypertension (poorly controlled), Type 2 Diabetes, Obesity (BMI 34), Obstructive Sleep Apnea
- **History:** Two HF hospitalizations in the past year. No coronary artery disease. No angioedema.

### Current Medications

| Drug | Dose | Frequency |
|------|------|-----------|
| Amlodipine | 10 mg | Daily |
| Lisinopril | 10 mg | Daily |
| Metformin | 1000 mg | BID |
| Furosemide | 20 mg | Daily |

### Current Labs

| Lab | Value | Reference |
|-----|-------|-----------|
| eGFR | 62 mL/min/1.73m2 | >60 |
| Potassium | 4.1 mEq/L | 3.5-5.0 |
| BNP | 320 pg/mL | <100 |
| Creatinine | 0.9 mg/dL | 0.6-1.1 |
| HbA1c | 7.9% | <7.0 |
| BP | 158/92 mmHg | <130/80 |

---

## Clinical Question

This patient has HFpEF with uncontrolled hypertension and recurrent hospitalizations. Unlike HFrEF, HFpEF has a fundamentally different evidence base — recommendations are weaker (Class IIa/IIb vs. Class I), the drug classes overlap but the indications differ, and blood pressure management is the cornerstone. The attending wants to optimize therapy. The "trick" is that an agent must NOT apply HFrEF GDMT rules to an HFpEF patient — different HF type means different recommendations with different strength levels.

---

## Decision Chain (8 steps)

### Step 1: List Available Guidelines

**Tool:** `list_available_guidelines`

Confirm AHA/ACC HF 2022 is loaded. HFpEF recommendations are in a separate section from HFrEF.

---

### Step 2: Find Treatment Options for HFpEF

**Tool:** `find_treatment_options`
```
condition: "heart_failure_preserved_ef"
patient_vars: { "LVEF": 58, "HF_type": "HFpEF", "comorbidity_hypertension": true, "NYHA_class": 2 }
```

**Expected:** Different recommendation landscape than HFrEF:
- ARB, ACEi, Sacubitril/Valsartan, MRA → strong_for BUT with low evidence quality (hypertension management)
- SGLT2i (Empagliflozin) → moderate_for with moderate evidence (EMPEROR-Preserved)
- Spironolactone → weak_for (TOPCAT data)
- ARNi, Candesartan → weak_for
- NO beta blocker recommendation for HFpEF (unlike HFrEF where it's Class I)

**Critical Decision:** The agent must recognize that HFpEF recommendations are driven by hypertension management and comorbidity control, NOT the 4-pillar GDMT paradigm of HFrEF. Applying HFrEF rules here would be incorrect.

---

### Step 3: Check Dosing for Empagliflozin (SGLT2i for HFpEF)

**Tool:** `check_drug_dosing`
```
drug: "empagliflozin"
patient_vars: { "eGFR": 62, "weight_kg": 88 }
```

**Expected:** 10 mg daily, same as HFrEF dosing. No renal adjustment needed at eGFR 62.

**Why this matters:** EMPEROR-Preserved showed empagliflozin benefit in HFpEF. The system should recommend it with moderate evidence quality, not the high evidence quality it has for HFrEF.

---

### Step 4: Check Dosing for Candesartan (HFpEF-Specific ARB)

**Tool:** `check_drug_dosing`
```
drug: "candesartan"
patient_vars: { "LVEF": 58, "HF_type": "HFpEF" }
```

**Expected:** Starting dose 4-8 mg daily, target 32 mg daily. Candesartan has specific HFpEF data (CHARM-Preserved trial) unlike other ARBs.

---

### Step 5: Check Dosing for Spironolactone in HFpEF

**Tool:** `check_drug_dosing`
```
drug: "spironolactone"
patient_vars: { "eGFR": 62, "potassium": 4.1, "LVEF": 58 }
```

**Expected:** Same dosing as HFrEF (12.5-25 mg start, 50 mg target) but the recommendation strength is weak_for in HFpEF (TOPCAT data was mixed). The favorable labs make initiation safe.

---

### Step 6: Check Monitoring for Spironolactone

**Tool:** `check_monitoring_requirements`
```
intervention: "spironolactone"
patient_vars: { "eGFR": 62, "potassium": 4.1 }
```

**Expected:** Same monitoring as HFrEF — K+, creatinine at 1 week, 4 weeks, then every 3 months. Alert K+ >= 5.0, stop K+ >= 5.5.

---

### Step 7: Check Contraindications for Sacubitril/Valsartan (Considering Upgrade)

**Tool:** `check_contraindications`
```
intervention: "sacubitril_valsartan"
patient_vars: { "history_of_angioedema": false, "potassium": 4.1, "eGFR": 62 }
```

**Expected:** No contraindication (angioedema conditions_met: false). The patient is on lisinopril (ACEi) — if switching, 36-hour washout required.

---

### Step 8: Query Diagnostic Criteria

**Tool:** `query_clinical_graph`
```
intent: "diagnostic_criteria"
concepts: ["HFpEF", "BNP", "echocardiography"]
patient_vars: { "LVEF": 58, "HF_type": "HFpEF" }
```

**Expected:** Diagnostic workup recommendations — BNP/NT-proBNP, echocardiography. HFpEF diagnosis requires LVEF >= 50% with evidence of elevated LV filling pressures.

---

## Expected Outcome Summary

| Decision | Result | Safety Implication |
|----------|--------|--------------------|
| Apply HFrEF 4-pillar GDMT? | **NO** — wrong HF type | HFpEF has different evidence base; applying HFrEF rules is clinically incorrect |
| Add SGLT2i (empagliflozin)? | **RECOMMENDED (moderate)** — EMPEROR-Preserved data | Best evidence for HFpEF-specific benefit |
| Add MRA (spironolactone)? | **CONSIDER (weak)** — TOPCAT data mixed | Favorable labs make it safe; evidence is weaker than HFrEF |
| Optimize BP with ARNi? | **CONSIDER** — requires ACEi washout | Strong for HTN management, weak for HFpEF-specific benefit |
| Add beta blocker? | **NOT INDICATED** — no HFpEF recommendation | Beta blockers lack evidence in HFpEF; would be incorrect |
| Manage OSA? | **YES** — CPAP indicated for HF + OSA | May improve HF symptoms and outcomes |

## Why This Scenario Is Valuable

1. **HF type differentiation:** Tests that the system correctly applies HFpEF (not HFrEF) recommendations — different strengths, different evidence quality
2. **Recommendation strength awareness:** Same drugs appear in both HFpEF and HFrEF but with different recommendation strengths — agent must communicate this
3. **Negative test:** Beta blockers should NOT be recommended for HFpEF — tests that the system doesn't over-recommend
4. **Hypertension as primary target:** HFpEF management is BP-driven, not 4-pillar-GDMT-driven — tests clinical framing
5. **Complements HFrEF scenarios:** All previous scenarios are HFrEF; this is the first HFpEF scenario

# Critical Decision Scenario: Cardiac Amyloidosis (ATTR-CM) — Etiology-Specific Therapy and GDMT Intolerance

## Patient Profile

- **Age:** 78
- **Sex:** Male
- **Weight:** 82 kg
- **Primary Diagnosis:** Transthyretin cardiac amyloidosis (ATTR-CM, wild-type), HFpEF transitioning to HFrEF (LVEF 38%)
- **Comorbidities:** Atrial Fibrillation (persistent), Carpal Tunnel Syndrome (bilateral), Lumbar Spinal Stenosis
- **History:** Diagnosed via bone scintigraphy (Grade 3 uptake) and TTR gene sequencing (wild-type confirmed). No monoclonal light chains.
- **Key finding:** Hypotension on low-dose ACEi (systolic BP 88 mmHg) — discontinued

### Current Medications

| Drug | Dose | Frequency |
|------|------|-----------|
| Furosemide | 40 mg | Daily |
| Apixaban | 5 mg | BID |
| None other (intolerant to RAAS inhibitors and beta blockers) | — | — |

### Current Labs

| Lab | Value | Reference |
|-----|-------|-----------|
| eGFR | 45 mL/min/1.73m2 | >60 |
| Potassium | 4.3 mEq/L | 3.5-5.0 |
| BNP | 1500 pg/mL | <100 |
| Creatinine | 1.5 mg/dL | 0.7-1.3 |
| Troponin | 0.08 ng/mL | <0.04 |
| NT-proBNP | 4200 pg/mL | <300 |

---

## Clinical Question

This patient has confirmed wild-type transthyretin cardiac amyloidosis (ATTR-CM) with NYHA Class II symptoms. ATTR-CM is a specific HF etiology where standard GDMT is often poorly tolerated — vasodilators worsen hypotension (patients rely on preload), and beta blockers reduce compensatory heart rate response. Tafamidis is the only etiology-specific disease-modifying therapy. The attending wants to start tafamidis and determine what other therapies are appropriate. The "trick" is that standard HFrEF GDMT may be harmful in ATTR-CM — the agent must recognize this special etiology.

---

## Decision Chain (8 steps)

### Step 1: List Available Guidelines

**Tool:** `list_available_guidelines`

Confirm AHA/ACC HF 2022 is loaded. Cardiac amyloidosis section covers tafamidis and the unique treatment considerations.

---

### Step 2: Check Dosing for Tafamidis

**Tool:** `check_drug_dosing`
```
drug: "tafamidis"
patient_vars: { "diagnosis": "ATTR-CM", "NYHA_class": 2 }
```

**Expected:** Starting dose 80 mg (tafamidis meglumine) or 61 mg (tafamidis) once daily. No dose titration. Conditions_met: true for ATTR-CM diagnosis.

**Critical Decision:** Tafamidis is the only disease-modifying therapy for ATTR-CM. The evidence should cite the ATTR-ACT trial showing reduced mortality and cardiovascular hospitalizations.

---

### Step 3: Find Treatment Options (Demonstrate GDMT Mismatch)

**Tool:** `find_treatment_options`
```
condition: "heart_failure_reduced_ef"
patient_vars: { "LVEF": 38, "NYHA_class": 2, "HF_type": "HFrEF", "eGFR": 45, "potassium": 4.3 }
```

**Expected:** Standard HFrEF recommendations returned (ARNi, beta blocker, MRA, SGLT2i). But the evidence text should include: "For patients with ATTR-CM and EF <=40%, GDMT may be poorly tolerated. The vasodilating effects of ARNi, ACEi, and ARB may exacerbate hypotension. Beta blockers may worsen HF symptoms as patients rely on heart rate response."

**Why this matters:** The standard GDMT appears indicated by LVEF/NYHA criteria, but the ATTR-CM etiology makes most of it harmful. An intelligent agent must cross-reference the etiology warning against the standard recommendations.

---

### Step 4: Query Diagnostic Criteria for Cardiac Amyloidosis

**Tool:** `query_clinical_graph`
```
intent: "diagnostic_criteria"
concepts: ["cardiac_amyloidosis", "ATTR-CM", "bone_scintigraphy"]
patient_vars: { "HF_type": "HFpEF" }
```

**Expected:** Diagnostic pathway for ATTR-CM:
- Cardiac MRI (recommended)
- Bone scintigraphy (recommended for ATTR-CM confirmation)
- TTR gene sequencing (recommended to differentiate wild-type from hereditary)
- Rule out AL amyloidosis (serum/urine light chains)

---

### Step 5: Check Contraindications for Sacubitril/Valsartan in ATTR-CM

**Tool:** `check_contraindications`
```
intervention: "sacubitril_valsartan"
patient_vars: { "history_of_angioedema": false, "diagnosis": "ATTR-CM" }
```

**Expected:** No formal ABSOLUTE contraindication based on ATTR-CM alone. However, the treatment_selection evidence flags that "vasodilating effects of ARNi may exacerbate hypotension." This is a clinical judgment call, not a hard graph-level block.

**Critical Decision:** The distinction between formal contraindication (ABSOLUTE — must never use) and clinical caution (poorly tolerated — use with extreme care) is nuanced. The graph correctly represents this as evidence/warning, not contraindication.

---

### Step 6: Calculate CHA2DS2-VASc for Anticoagulation

**Tool:** `execute_clinical_calculator`
```
calculator_id: "calculate_chadsvasc"
parameters: {
  "congestive_heart_failure": true,
  "hypertension": false,
  "age": 78,
  "diabetes": false,
  "stroke_tia_thromboembolism": false,
  "vascular_disease": false,
  "female_sex": false
}
```

**Expected:** Score = 3 (CHF=1, Age >=75=2). Supports continued anticoagulation.

---

### Step 7: Check Drug Interaction — Tafamidis + Apixaban

**Tool:** `check_drug_interaction`
```
drug_a: "tafamidis"
drug_b: "apixaban"
```

**Expected:** Limited or no data in the graph for this specific interaction. This tests a known gap and whether the system appropriately indicates uncertainty rather than assuming no interaction.

---

### Step 8: Fetch Evidence for Tafamidis Recommendation

**Tool:** `fetch_evidence_chunk`
```
chunk_id: <from Step 2 evidence about tafamidis>
```

**Expected:** "In select patients with wild-type or variant transthyretin cardiac amyloidosis and NYHA class I to III HF symptoms, transthyretin tetramer stabilizer therapy (tafamidis) is indicated to reduce cardiovascular morbidity and mortality."

---

## Expected Outcome Summary

| Decision | Result | Safety Implication |
|----------|--------|--------------------|
| Start tafamidis? | **STRONGLY RECOMMENDED** — only disease-modifying therapy for ATTR-CM | Reduces mortality per ATTR-ACT trial |
| Apply standard HFrEF GDMT? | **CAUTION** — GDMT poorly tolerated in ATTR-CM | Vasodilators worsen hypotension; beta blockers reduce compensatory HR |
| Start RAAS inhibitor? | **AVOID** — patient already hypotensive on low-dose ACEi | History of SBP 88 on ACEi; ATTR-CM exacerbates preload dependence |
| Continue anticoagulation? | **YES** — CHA2DS2-VASc 3 with persistent AF | Stroke prevention; ATTR-CM also has thrombotic risk |
| Gene testing done? | **CONFIRMED** — wild-type (not hereditary) | Affects prognosis and family screening recommendations |
| Diuretics? | **CONTINUE** — only symptomatic relief available beyond tafamidis | Loop diuretics for volume management |

## Why This Scenario Is Valuable

1. **Etiology-specific therapy:** Tafamidis is unique to ATTR-CM — tests that the system has rare disease-specific recommendations
2. **GDMT intolerance pattern:** Standard HFrEF GDMT is harmful/intolerable — tests that the system recognizes etiology-dependent exceptions
3. **Diagnostic pathway:** Bone scintigraphy → gene sequencing → light chain rule-out — tests diagnostic criteria recommendations
4. **Nuanced contraindication vs. caution:** ATTR-CM doesn't create a formal ABSOLUTE contraindication to RAAS inhibitors but makes them clinically dangerous — tests the system's ability to communicate nuance
5. **Unique entity in graph:** Tafamidis appears only for ATTR-CM — tests that the condition matching works for rare etiologies
6. **Complements all other scenarios:** Every other scenario assumes GDMT is beneficial; this scenario tests when GDMT itself is the problem

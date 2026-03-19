# Critical Decision Scenario: Peripartum Cardiomyopathy — Pregnancy Contraindications and Safe Alternatives

## Patient Profile

- **Age:** 32
- **Sex:** Female
- **Weight:** 70 kg
- **Primary Diagnosis:** Peripartum cardiomyopathy, HFrEF (LVEF 28%)
- **Comorbidities:** None prior to pregnancy
- **History:** Diagnosed 2 weeks postpartum. Currently breastfeeding. Planning future pregnancies.
- **Pregnancy status:** Postpartum, breastfeeding

### Current Medications

| Drug | Dose | Frequency |
|------|------|-----------|
| Furosemide | 40 mg | Daily |
| None other | — | — |

### Current Labs

| Lab | Value | Reference |
|-----|-------|-----------|
| eGFR | 95 mL/min/1.73m2 | >60 |
| Potassium | 4.0 mEq/L | 3.5-5.0 |
| BNP | 680 pg/mL | <100 |
| Creatinine | 0.7 mg/dL | 0.6-1.1 |
| Hemoglobin | 11.5 g/dL | 12.0-16.0 |
| TSH | 3.2 mIU/L | 0.4-4.0 |
| Prolactin | elevated | — |

---

## Clinical Question

This young woman has newly diagnosed peripartum cardiomyopathy with severe LV dysfunction (LVEF 28%). Standard HFrEF GDMT (ACEi/ARB/ARNi, MRA, SGLT2i, ivabradine) is ALL contraindicated in pregnancy and during breastfeeding for most agents. The attending must identify which drugs are safe postpartum/breastfeeding and which require future pregnancy planning. Additionally, bromocriptine may be considered for peripartum cardiomyopathy with LVEF <35%. The "trick" is that nearly the entire HFrEF armamentarium is blocked by pregnancy/lactation — the agent must find the narrow set of safe alternatives.

---

## Decision Chain (8 steps)

### Step 1: List Available Guidelines

**Tool:** `list_available_guidelines`

Confirm AHA/ACC HF 2022 is loaded. Section on pregnancy and peripartum cardiomyopathy is critical.

---

### Step 2: Find Treatment Options for HFrEF (Standard)

**Tool:** `find_treatment_options`
```
condition: "heart_failure_reduced_ef"
patient_vars: { "LVEF": 28, "NYHA_class": 3, "HF_type": "HFrEF", "eGFR": 95, "potassium": 4.0 }
```

**Expected:** Full HFrEF GDMT recommendations — ARNi, beta blocker, MRA, SGLT2i all with conditions_met: true. This shows what WOULD be recommended if the patient weren't breastfeeding/planning pregnancy.

**Critical Decision:** The treatment options look great on paper — but the pregnancy/lactation context invalidates most of them. The agent must cross-reference with contraindications.

---

### Step 3: Check Contraindications for Sacubitril/Valsartan (Pregnancy)

**Tool:** `check_contraindications`
```
intervention: "sacubitril_valsartan"
patient_vars: { "history_of_angioedema": false, "pregnancy": true }
```

**Expected:** Contraindication due to pregnancy/planning pregnancy. ACEi, ARB, ARNi, MRA, SGLT2i, ivabradine, and vericiguat all cause fetal harm. The graph evidence should cite: "ACEi, ARB, ARNi, MRA, SGLT2i, ivabradine, and vericiguat should not be administered because of significant risks of fetal harm."

---

### Step 4: Query Safe Drugs in Pregnancy/Postpartum

**Tool:** `query_clinical_graph`
```
intent: "treatment_selection"
concepts: ["heart_failure", "pregnancy", "peripartum_cardiomyopathy"]
patient_vars: { "sex": "female", "pregnancy": true, "postpartum": true, "breastfeeding": true, "LVEF": 28, "HF_type": "HFrEF" }
```

**Expected:** Safe alternatives in pregnancy/postpartum:
- **Metoprolol succinate** — safe in pregnancy (expert opinion)
- **Hydralazine** — safe in pregnancy (expert opinion)
- **Nitrates** — safe in pregnancy (expert opinion)
- **Furosemide** — safe in pregnancy (expert opinion)
- **Postpartum breastfeeding-safe ACEi:** Enalapril, Captopril (expert opinion)
- **Bromocriptine** — for peripartum cardiomyopathy with LVEF <35% (expert opinion)

---

### Step 5: Check Dosing for Enalapril (Breastfeeding-Safe ACEi)

**Tool:** `check_drug_dosing`
```
drug: "enalapril"
patient_vars: { "LVEF": 28, "eGFR": 95 }
```

**Expected:** Starting dose 2.5 mg BID, target 10-20 mg BID, max 40 mg/day. Enalapril has minimal breast milk excretion and is considered safe during lactation.

---

### Step 6: Check Dosing for Metoprolol Succinate (Pregnancy-Safe Beta Blocker)

**Tool:** `check_drug_dosing`
```
drug: "metoprolol_succinate"
patient_vars: { "LVEF": 28, "weight_kg": 70 }
```

**Expected:** Starting dose 12.5-25 mg daily, target 200 mg daily. Metoprolol is the preferred beta blocker in pregnancy/lactation.

---

### Step 7: Check Drug Interaction — Enalapril + Hydralazine

**Tool:** `check_drug_interaction`
```
drug_a: "enalapril"
drug_b: "hydralazine"
```

**Expected:** No significant interaction. Both can be used together. In the postpartum setting, enalapril provides RAAS inhibition while hydralazine provides additional vasodilation.

---

### Step 8: Fetch Evidence for Pregnancy Contraindication

**Tool:** `fetch_evidence_chunk`
```
chunk_id: <from Step 3 evidence about pregnancy>
```

**Expected:** Guideline text: "In women with HF or cardiomyopathy who are pregnant or currently planning for pregnancy, ACEi, ARB, ARNi, MRA, SGLT2i, ivabradine, and vericiguat should not be administered because of significant risks of fetal harm."

---

## Expected Outcome Summary

| Decision | Result | Safety Implication |
|----------|--------|--------------------|
| Standard HFrEF GDMT? | **MOSTLY BLOCKED** — pregnancy/lactation contraindication | ACEi, ARB, ARNi, MRA, SGLT2i, ivabradine ALL contraindicated |
| Start ACEi (enalapril)? | **YES — postpartum/breastfeeding safe** | Minimal breast milk excretion; provides RAAS inhibition |
| Start beta blocker? | **YES — metoprolol safe** | Preferred beta blocker in pregnancy/lactation |
| Start hydralazine + nitrate? | **YES — pregnancy safe** | Alternative vasodilator when RAAS inhibitors are contraindicated |
| Consider bromocriptine? | **CONSIDER** — LVEF <35%, peripartum cardiomyopathy | Inhibits prolactin; may improve LV recovery (expert opinion) |
| Future pregnancy plan? | **CRITICAL COUNSELING** — must stop all teratogenic drugs before conception | Must plan medication transitions before future pregnancies |

## Why This Scenario Is Valuable

1. **Mass contraindication test:** Nearly the entire HFrEF pharmacopeia is contraindicated — tests the system's ability to navigate when standard therapy is blocked
2. **Safe alternative identification:** The agent must find the narrow window of pregnancy/lactation-safe drugs — not just block everything
3. **Sex-specific conditions:** Pregnancy/postpartum/breastfeeding variables are unique to female patients — tests demographic condition handling
4. **Peripartum-specific therapy:** Bromocriptine is unique to peripartum cardiomyopathy — tests rare etiology-specific recommendations
5. **Unique patient population:** Young, otherwise healthy patient — contrasts with the elderly multimorbid patients in all other scenarios

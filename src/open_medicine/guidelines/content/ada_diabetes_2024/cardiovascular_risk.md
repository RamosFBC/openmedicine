# Cardiovascular Disease and Risk Management in Diabetes — ADA 2024

## ASCVD Risk Assessment

The ACC/AHA Pooled Cohort Equations (ASCVD Risk Estimator Plus) is a useful tool to estimate 10-year risk of a first ASCVD event in patients with diabetes. Risk calculators do not fully account for duration of diabetes or the presence of diabetes complications such as albuminuria.

> **OpenMedicine Calculator:** `calculate_ascvd` — available via MCP for automated 10-year ASCVD risk estimation.

---

## Cardiorenal Risk Reduction with Glucose-Lowering Agents

### Decision Algorithm

```
Patient with type 2 diabetes
  → Does the patient have established ASCVD or high ASCVD risk?
      → YES → Include GLP-1 RA and/or SGLT2i with demonstrated CV benefit,
              independent of A1C (Rec 9.18, Grade A)
  → Does the patient have heart failure (HFrEF or HFpEF)?
      → YES → Include SGLT2 inhibitor (Rec 9.19, Grade A)
  → Does the patient have CKD (eGFR 20–60 mL/min/1.73 m² and/or albuminuria)?
      → YES → Include SGLT2 inhibitor (Rec 9.20, Grade A)
      → eGFR < 30? → Prefer GLP-1 RA for glycemic management (Rec 9.21, Grade B)
  → Combined therapy with both SGLT2i and GLP-1 RA may be considered for additive benefits
  → These agents are recommended INDEPENDENT of A1C and INDEPENDENT of metformin use
```

### SGLT2 Inhibitors with Demonstrated Cardiovascular Benefit

| Drug | CV Outcome Trial | Key Findings |
|---|---|---|
| Empagliflozin | EMPA-REG OUTCOME | Reduced composite MACE, CV death, HF hospitalization |
| Canagliflozin | CANVAS Program | Reduced composite MACE |
| Dapagliflozin | DECLARE-TIMI 58 | Reduced HF hospitalization; CV death/MI in ASCVD subgroup |

### GLP-1 Receptor Agonists with Demonstrated Cardiovascular Benefit

| Drug | CV Outcome Trial | Key Findings |
|---|---|---|
| Liraglutide | LEADER | Reduced composite MACE, CV death, all-cause mortality |
| Semaglutide (subcutaneous) | SUSTAIN-6 | Reduced composite MACE, stroke |
| Dulaglutide | REWIND | Reduced composite MACE, stroke |

### Agents WITHOUT Demonstrated CV Benefit

- **Ertugliflozin** (VERTIS-CV): No significant MACE reduction.
- **Exenatide ER** (EXSCEL): No significant MACE reduction.
- **DPP-4 inhibitors** (sitagliptin, saxagliptin, alogliptin, linagliptin): CV safety demonstrated but no MACE reduction. Saxagliptin associated with increased HF hospitalization (SAVOR-TIMI 53).

---

## Blood Pressure Management

### Target (Recommendation 10.4, Grade A)

The on-treatment target blood pressure goal is **< 130/80 mmHg**, if it can be safely attained.

### Pharmacologic Initiation

- **Recommendation 10.7 (Grade A):** Initiate pharmacologic therapy for confirmed blood pressure ≥ 130/80 mmHg.
- **Recommendation 10.8 (Grade A):** Start with two drugs or a fixed-dose combination for blood pressure ≥ 150/90 mmHg.
- **Recommendation 10.6 (Grade A):** Lifestyle intervention (weight loss, DASH diet, sodium reduction, increased physical activity, moderation of alcohol) for blood pressure > 120/80 mmHg.

### Preferred Antihypertensive Agents

| Agent Class | Notes |
|---|---|
| ACE inhibitor | First-line, especially with albuminuria or CAD |
| ARB | Alternative to ACEi (do not combine ACEi + ARB) |
| Dihydropyridine CCB | Amlodipine, nifedipine ER |
| Thiazide-like diuretic | Chlorthalidone, indapamide preferred |

- **Recommendation 10.11 (Grade A/B):** Maximize ACEi or ARB dose for UACR ≥ 300 mg/g (Grade A) or 30–299 mg/g (Grade B).
- **Recommendation 10.12 (Grade B):** Monitor serum creatinine/eGFR and potassium within 7–14 days of initiation, then at least annually.
- **Recommendation 10.13 (Grade A):** Add MRA for resistant hypertension on 3 or more agents.

---

## Lipid Management

### Statin Therapy Framework

#### Primary Prevention (No Prior ASCVD)

| Patient Group | Recommendation | Intensity | LDL Target | Grade |
|---|---|---|---|---|
| Age 40–75, no ASCVD risk factors | Moderate-intensity statin | Moderate | — | A |
| Age 40–75, with ASCVD risk factors | High-intensity statin | High | < 70 mg/dL | A |
| Age 20–39, with additional CV risk factors | Consider statin | Moderate | — | C |
| Age > 75, already on statin | Continue | Current | — | B |
| Age > 75, new initiation | Consider after discussion | Moderate | — | C |

**ASCVD risk factors include:** LDL ≥ 100 mg/dL, hypertension, smoking, overweight/obesity, family history of premature ASCVD, CKD, albuminuria.

#### Secondary Prevention (Established ASCVD)

- **Recommendation 10.26 (Grade A):** High-intensity statin therapy for all patients with diabetes and ASCVD, regardless of age.
- **Recommendation 10.27 (Grade B):** Target LDL < 55 mg/dL. If not achieved on maximally tolerated statin, add ezetimibe or PCSK9 inhibitor.

### Statin Intensity Reference

| Intensity | Expected LDL Reduction | Examples |
|---|---|---|
| High | ≥ 50% | Atorvastatin 40–80 mg, Rosuvastatin 20–40 mg |
| Moderate | 30–49% | Atorvastatin 10–20 mg, Rosuvastatin 5–10 mg, Simvastatin 20–40 mg, Pravastatin 40–80 mg |

### Additional Lipid Agents

- **Ezetimibe:** Add to maximally tolerated statin if LDL goal not reached.
- **PCSK9 inhibitors (evolocumab, alirocumab):** Add to statin ± ezetimibe for secondary prevention if LDL ≥ 55 mg/dL (Grade B).
- **Bempedoic acid:** For statin-intolerant patients (Rec 10.24, Grade A).
- **Icosapent ethyl 4 g/day:** For ASCVD or CV risk factors with triglycerides 135–499 mg/dL on statin (Rec 10.31, Grade A).
- Statins are **contraindicated in pregnancy** (Rec 10.25, Grade B).

---

## Antiplatelet Therapy

### Secondary Prevention (Recommendation 10.34, Grade A)

Aspirin **75–162 mg/day** for all patients with diabetes and established ASCVD.

- **Clopidogrel 75 mg/day** if aspirin allergy (Rec 10.35a, Grade B).
- **DAPT duration** after ACS or acute stroke should be guided by interprofessional team (Rec 10.35b, Grade E).
- **Aspirin + low-dose rivaroxaban** may be considered for stable CAD and/or PAD with low bleeding risk (Rec 10.36, Grade A).

### Primary Prevention (Recommendation 10.37, Grade A)

Aspirin 75–162 mg/day may be considered for primary prevention in patients with diabetes at increased cardiovascular risk, after a comprehensive discussion on benefits versus increased bleeding risk.

---

## Heart Failure in Diabetes

- **SGLT2 inhibitors** reduce HF hospitalization rates in patients with type 2 diabetes regardless of HF history.
- **Recommendation 9.19 (Grade A):** In adults with type 2 diabetes who have HF (with either reduced or preserved ejection fraction), an SGLT2 inhibitor is recommended.
- **Avoid TZDs** (pioglitazone, rosiglitazone) in patients with NYHA class III–IV heart failure due to fluid retention.
- **Saxagliptin** should be avoided in patients with HF (increased hospitalization risk in SAVOR-TIMI 53).

---

## Chronic Kidney Disease in Diabetes

- **Recommendation 9.20 (Grade A):** SGLT2 inhibitor for confirmed eGFR 20–60 mL/min/1.73 m² and/or albuminuria. Glycemic benefits diminish at eGFR < 45 mL/min/1.73 m², but cardiorenal benefits persist.
- **Recommendation 9.21 (Grade B):** GLP-1 RA is preferred for glycemic management when eGFR < 30 mL/min/1.73 m².
- **Metformin:** Safe at eGFR ≥ 30 mL/min/1.73 m². Contraindicated below 30.
- **Sulfonylureas:** Increased hypoglycemia risk with declining eGFR; avoid glyburide at eGFR < 30.
- **DPP-4 inhibitors:** Dose adjustment required for all except linagliptin.

## Limitations

- ASCVD risk calculators may underestimate risk in patients with long-standing diabetes, albuminuria, or other diabetes-specific risk factors.
- CV outcome trial populations may not be fully representative of all patients with type 2 diabetes.
- Blood pressure targets are based on randomized trials that often excluded patients with significant comorbidities.
- Cost and access remain significant barriers to SGLT2i and GLP-1 RA use in many populations.

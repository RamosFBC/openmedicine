# Risk Assessment in Upper Gastrointestinal Bleeding — NICE CG141 (2012)

## Pre-Endoscopy Risk Stratification

### Glasgow-Blatchford Score (GBS)

The Glasgow-Blatchford Score (GBS) should be used at **first assessment** for all patients presenting with acute upper gastrointestinal bleeding to determine the need for intervention (NICE CG141, Recommendation 1.1.1).

| Parameter | Criteria | Score |
|---|---|---|
| **BUN (mg/dL)** | 18.2–22.3 | 2 |
| | 22.4–27.9 | 3 |
| | 28.0–69.9 | 4 |
| | ≥ 70.0 | 6 |
| **Hemoglobin — Male (g/dL)** | 12.0–12.9 | 1 |
| | 10.0–11.9 | 3 |
| | < 10.0 | 6 |
| **Hemoglobin — Female (g/dL)** | 10.0–11.9 | 1 |
| | < 10.0 | 6 |
| **Systolic BP (mmHg)** | 100–109 | 1 |
| | 90–99 | 2 |
| | < 90 | 3 |
| **Heart Rate** | ≥ 100 bpm | 1 |
| **Other Markers** | Melena at presentation | 1 |
| | Syncope at presentation | 1 |
| | Hepatic disease | 1 |
| | Cardiac failure | 1 |

**Total possible score: 0–23**

> **OpenMedicine Calculator:** `calculate_glasgow_blatchford` — available via MCP for automated GBS scoring.

### GBS-Based Disposition Algorithm

```
Patient presents with acute upper GI bleeding
  → Calculate Glasgow-Blatchford Score at first assessment
      → GBS = 0
          → Low risk. Consider early discharge with outpatient follow-up
             (NICE CG141 Recommendation 1.1.2)
      → GBS = 1
          → Low risk. Consider outpatient management with close follow-up if
             no other indication for admission
      → GBS ≥ 2
          → Moderate-to-high risk. Hospital admission for further evaluation,
             resuscitation, and endoscopy
      → GBS ≥ 7
          → High risk. Urgent intervention likely needed. Prioritize
             resuscitation and early endoscopy
```

## Post-Endoscopy Risk Assessment

### Full Rockall Score

The full Rockall Score should be used **after endoscopy** to assess risk of re-bleeding and mortality (NICE CG141, Recommendation 1.1.1).

| Variable | 0 Points | 1 Point | 2 Points | 3 Points |
|---|---|---|---|---|
| **Age** | < 60 | 60–79 | ≥ 80 | — |
| **Shock** | No shock (HR < 100, SBP ≥ 100) | Tachycardia (HR ≥ 100, SBP ≥ 100) | Hypotension (SBP < 100) | — |
| **Comorbidity** | None | — | CHF, IHD, major comorbidity | Renal failure, liver failure, disseminated malignancy |
| **Endoscopic diagnosis** | Mallory-Weiss, no lesion | All other diagnoses | Upper GI malignancy | — |
| **Stigmata of recent hemorrhage** | None or dark spot | — | Blood in upper GI tract, adherent clot, visible/spurting vessel | — |

**Total possible score: 0–11**

| Rockall Score | Re-Bleeding Risk | Mortality Risk |
|---|---|---|
| ≤ 2 | Low (4.3%) | Low (0.1%) |
| 3–5 | Moderate (14%) | Moderate (6%) |
| 6–7 | High (37%) | High (17%) |
| ≥ 8 | Very high (42%) | Very high (41%) |

> **OpenMedicine Calculator:** `calculate_rockall` — available via MCP for automated Rockall scoring post-endoscopy.

## Limitations

- GBS does not include endoscopic findings and may overestimate risk in some patients; it is specifically designed as a **pre-endoscopy** tool.
- A GBS of 0 is highly specific for patients who can be safely discharged, but this represents only a small proportion of all patients.
- Rockall score requires endoscopy data and cannot be fully calculated at initial presentation.
- Neither score accounts for anticoagulant or antiplatelet therapy, which may independently affect bleeding risk.

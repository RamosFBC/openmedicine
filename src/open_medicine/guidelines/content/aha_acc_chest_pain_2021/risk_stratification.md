# Risk Stratification for Acute Chest Pain — AHA/ACC 2021

## HEART Score Interpretation & Disposition

The HEART Score (History, ECG, Age, Risk factors, Troponin) is endorsed within the 2021 AHA/ACC Chest Pain Guideline as part of Clinical Decision Pathways (CDPs) for risk stratification.

### Scoring Components (0-2 points each, total 0-10)

| Component | 0 Points | 1 Point | 2 Points |
|---|---|---|---|
| **H**istory | Slightly suspicious | Moderately suspicious | Highly suspicious |
| **E**CG | Normal | Non-specific repolarization disturbance | Significant ST deviation |
| **A**ge | < 45 years | 45–64 years | ≥ 65 years |
| **R**isk factors | No known risk factors | 1–2 risk factors | ≥ 3 risk factors OR history of atherosclerotic disease |
| **T**roponin | ≤ normal limit | 1–3× normal limit | > 3× normal limit |

> Risk factors include: Hypertension, Diabetes Mellitus, current smoker, obesity (BMI > 30), hypercholesterolemia, family history of premature CAD. History of atherosclerotic disease includes prior PCI/CABG, stroke/TIA, or peripheral arterial disease.

### Actionable Disposition by HEART Score

- **HEART Score 0–3 (Low Risk, ~1.7% MACE at 6 weeks):**
  - **Action:** Consider early discharge with outpatient follow-up if serial high-sensitivity troponin (hs-cTn) at 0 and 1–3 hours remains below the 99th percentile (Class I).
  - **Follow-up:** Schedule outpatient cardiology or primary care follow-up within 72 hours.
  - **No routine stress testing required** prior to discharge for low-risk patients (Class III: No Benefit).

- **HEART Score 4–6 (Moderate Risk, ~16.6% MACE at 6 weeks):**
  - **Action:** Admit to observation unit for serial cardiac troponin monitoring and further risk stratification (Class I).
  - **Workup:** Obtain repeat hs-cTn at 1–3 hours (or 3–6 hours if using conventional troponin). If troponin is stable and below the 99th percentile, consider non-invasive functional testing (stress echocardiography or nuclear MPI) or anatomical testing (coronary CTA) prior to discharge.
  - **If troponin rises above the 99th percentile with a significant delta (> 20% change):** Treat as acute MI — initiate ACS pathway, consult cardiology.

- **HEART Score 7–10 (High Risk, ~50.7% MACE at 6 weeks):**
  - **Action:** Hospital admission and urgent cardiology consultation (Class I).
  - **Workup:** Initiate ACS protocol — serial ECGs, continuous telemetry monitoring, dual antiplatelet therapy (Aspirin 325 mg load + P2Y12 inhibitor), and parenteral anticoagulation (see TIMI UA/NSTEMI guideline).
  - **Invasive strategy:** Coronary angiography within 24 hours is recommended for high-risk patients. Immediate angiography for hemodynamic instability, refractory angina, or new heart failure.

## High-Sensitivity Cardiac Troponin (hs-cTn) Protocol

The 2021 AHA/ACC guideline recommends hs-cTn as the preferred biomarker for diagnosing acute myocardial infarction (Class I).

### Serial Sampling Strategy
- **Time zero:** Draw hs-cTn immediately upon ED arrival.
- **Repeat draw:** At **1 to 3 hours** after the initial sample (assay-specific; consult institutional protocol).
- **Rule-out criteria:** Both hs-cTn values below the 99th percentile AND no significant delta change (< 20% relative change) between the two draws.
- **Rule-in criteria:** hs-cTn above the 99th percentile with a rising and/or falling pattern indicating acute myocardial injury.

### Key Caveats
- **Chronic troponin elevation (e.g., CKD, HF, pulmonary hypertension):** A stable, non-dynamic troponin level above the 99th percentile does NOT indicate acute MI. Look for a rise-and-fall pattern.
- **Very early presenters (< 2 hours from symptom onset):** A single normal hs-cTn does NOT exclude MI. Serial sampling is mandatory.

> **OpenMedicine Calculator:** `calculate_heart_score` — available via MCP for automated scoring and risk stratification.

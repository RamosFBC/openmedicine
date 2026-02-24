# Risk Stratification in Acute Coronary Syndromes — ESC 2023

## GRACE Score for NSTE-ACS Risk Assessment

The GRACE (Global Registry of Acute Coronary Events) 2.0 risk score is recommended for risk stratification of NSTE-ACS patients to determine prognosis and guide invasive strategy timing (Class I, Level of Evidence B).

### GRACE Score Components

| Parameter | Scoring Range |
|---|---|
| Age | 0–100 points |
| Heart rate | 0–46 points |
| Systolic blood pressure | 0–58 points (inverse) |
| Serum creatinine | 1–28 points |
| Killip class (I–IV) | 0–59 points |
| Cardiac arrest at admission | 39 points |
| ST-segment deviation | 28 points |
| Elevated cardiac enzymes | 14 points |

### In-Hospital Mortality Risk Categories

| GRACE Score | Risk Category | Estimated In-Hospital Mortality |
|---|---|---|
| ≤ 108 | Low | < 1% |
| 109–140 | Intermediate | 1–3% |
| > 140 | High | > 3% |

### 6-Month Post-Discharge Mortality

| GRACE Score | Risk Category | 6-Month Mortality |
|---|---|---|
| ≤ 88 | Low | < 3% |
| 89–118 | Intermediate | 3–8% |
| > 118 | High | > 8% |

> **OpenMedicine Calculator:** `calculate_grace_score` — available via MCP for automated GRACE 2.0 scoring.

## Very High-Risk Criteria (Immediate Invasive Strategy)

The following features mandate **immediate invasive angiography (< 2 hours)** regardless of GRACE score (Class I, Level of Evidence C):

- Hemodynamic instability or cardiogenic shock
- Recurrent or refractory chest pain despite medical treatment
- Life-threatening arrhythmias (ventricular tachycardia, ventricular fibrillation)
- Mechanical complications of myocardial infarction (papillary muscle rupture, VSD)
- Acute heart failure clearly related to ongoing myocardial ischemia
- Recurrent dynamic ST-segment or T-wave changes, particularly intermittent ST-segment elevation

## High-Risk Criteria (Early Invasive Strategy Within 24 Hours)

An early invasive strategy (coronary angiography within 24 hours) should be considered in NSTE-ACS patients with at least one of the following (Class I, Level of Evidence A):

- Confirmed diagnosis of NSTEMI (rise and/or fall of cardiac troponin with at least one value above the 99th percentile URL)
- Dynamic new or presumably new ST-segment or T-wave changes (symptomatic or silent)
- Transient ST-segment elevation
- **GRACE risk score > 140**

## Decision Algorithm

```
Patient presents with suspected NSTE-ACS
  → Any very high-risk feature (shock, refractory pain, VT/VF, mechanical complication)?
      → YES → Immediate coronary angiography (< 2 hours)
      → NO → Calculate GRACE score + assess for high-risk criteria
             → GRACE > 140 OR confirmed NSTEMI OR dynamic ST/T changes?
                 → YES → Early invasive strategy (angiography within 24 hours)
                 → NO → Inpatient invasive strategy (angiography during index hospitalization)
                        → Consider selective/conservative approach if very low risk
```

## Limitations

- The GRACE score was derived from in-hospital populations and may not fully capture risk in very early presenters.
- Score should be recalculated if clinical status changes significantly.
- Troponin and creatinine values at presentation may not reflect peak values; serial measurements are essential.
- Clinical judgment remains necessary for patients at the boundary of risk categories.

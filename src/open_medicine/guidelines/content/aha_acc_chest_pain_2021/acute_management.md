# Acute Management of Chest Pain — AHA/ACC 2021

## Initial Evaluation (First 10 Minutes)

Upon presentation with acute chest pain, the following should be completed immediately:

1. **12-Lead ECG:** Obtain within 10 minutes of arrival (Class I). If STEMI criteria are met, activate the catheterization lab immediately — this guideline does NOT apply to STEMI.
2. **Cardiac Troponin:** Draw first hs-cTn sample (time zero) at initial contact.
3. **Focused History:** Assess chest pain characteristics (onset, location, radiation, quality, duration, provocation/palliation), associated symptoms (dyspnea, diaphoresis, nausea), and risk factors.
4. **Physical Examination:** Vitals (including bilateral BP if aortic dissection suspected), cardiac/pulmonary auscultation, assessment for signs of heart failure or hemodynamic instability.

## Anti-Ischemic Therapy (For Suspected ACS)

Initiate the following if acute coronary syndrome is suspected:

### Pharmacotherapy
- **Aspirin:** 162–325 mg non-enteric coated, chewed, given immediately (Class I). Continue 81 mg daily.
- **Nitroglycerin:** 0.4 mg sublingual every 5 minutes × 3 doses for ongoing ischemic chest pain (Class I).
  - **Contraindications:** SBP < 90 mmHg, recent PDE-5 inhibitor use (sildenafil/vardenafil within 24 hours, tadalafil within 48 hours), right ventricular infarction, severe aortic stenosis.
  - **Escalation:** If pain persists after 3 sublingual doses, initiate IV nitroglycerin infusion (start 5–10 mcg/min, titrate by 5–10 mcg/min every 3–5 min).
- **Supplemental Oxygen:** Only if SpO2 < 90% or signs of respiratory distress (Class I). Do NOT routinely administer oxygen to normoxic patients (Class III: Harm — associated with increased infarct size).
- **Morphine:** 2–4 mg IV for pain not relieved by nitroglycerin. Use with caution; associated with potential hypotension. NOT a first-line agent.

### Anticoagulation (If ACS Confirmed/Likely)
See TIMI UA/NSTEMI guideline for full anticoagulation and P2Y12 inhibitor recommendations based on TIMI risk score stratification.

## Non-ACS Causes of Chest Pain — Key Differential Diagnoses

The 2021 guideline emphasizes that chest pain has a broad differential beyond ACS. An agent should consider the following life-threatening diagnoses before attributing chest pain to a benign cause:

| Diagnosis | Key Distinguishing Features | Immediate Action |
|---|---|---|
| **Aortic Dissection** | Tearing pain radiating to back, BP differential between arms, widened mediastinum | Urgent CT angiography, IV beta-blocker (Esmolol) to HR < 60 and SBP < 120 |
| **Pulmonary Embolism** | Pleuritic pain, dyspnea, tachycardia, risk factors for DVT | Wells Score → D-dimer or CTPA (see Wells PE guideline) |
| **Tension Pneumothorax** | Sudden onset, unilateral absent breath sounds, tracheal deviation, hypotension | Immediate needle decompression (2nd ICS, midclavicular) |
| **Esophageal Rupture (Boerhaave)** | Pain after forceful vomiting, subcutaneous emphysema | Urgent CT chest with oral contrast, surgical consultation |
| **Cardiac Tamponade** | Beck's Triad (hypotension, JVD, muffled heart sounds) | Emergent pericardiocentesis or surgical drainage |

## Disposition Decision Algorithm

```
Patient presents with acute chest pain
  → Obtain ECG within 10 min
  → STEMI? → YES → Activate cath lab (not this guideline)
           → NO → Draw hs-cTn (time zero)
                  → Calculate HEART Score
                  → HEART 0-3 AND hs-cTn < 99th percentile at 0 AND 1-3h?
                      → YES → Discharge with 72h follow-up
                      → NO (HEART 4-6) → Observation, serial troponin, stress/CTA
                      → NO (HEART 7-10) → Admit, ACS protocol, angiography < 24h
```

> **OpenMedicine Calculator:** `calculate_heart_score` — available via MCP for automated scoring.

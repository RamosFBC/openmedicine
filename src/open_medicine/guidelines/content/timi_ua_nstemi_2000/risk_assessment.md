# Risk Assessment in UA/NSTEMI — TIMI Study Group 2000

## TIMI Risk Score Calculation

The TIMI Risk Score for Unstable Angina/Non-ST Elevation MI (UA/NSTEMI) estimates the 14-day risk of all-cause mortality, new or recurrent MI, or severe recurrent ischemia requiring urgent revascularization.

### Scoring Criteria
Assign 1 point for each of the following 7 independent variables present at admission:

- Age ≥ 65 years
- ≥3 CAD risk factors (family history of CAD, hypertension, hypercholesterolemia, diabetes mellitus, or current smoker)
- Known CAD (prior coronary stenosis ≥50%)
- Aspirin use in the past 7 days
- Severe angina (≥2 anginal events in the past 24 hours)
- ST-segment deviation ≥ 0.5 mm on presenting ECG
- Elevated cardiac markers (troponin or CK-MB)

*Total Possible Score: 0 to 7 points*

## Actionable Risk Stratification & Clinical Pathways

Patients are stratified into three risk groups. The 2014/2020 ACC/AHA and ESC guidelines utilize this stratification to determine the timing of invasive strategies and intensity of pharmacotherapy.

| Risk Group | Score | Actionable Recommendation |
| :--- | :--- | :--- |
| **Low Risk** | 0-2 | **Conservative Strategy:** Ischemia-guided approach. Non-invasive stress testing prior to discharge. Optimize medical therapy (Aspirin, statin, beta-blocker). |
| **Intermediate Risk** | 3-4 | **Early Invasive Strategy:** Coronary angiography within 24–72 hours. Initiate DAPT and parenteral anticoagulation. |
| **High Risk** | 5-7 | **Immediate/Early Invasive Strategy:** Coronary angiography < 24 hours (immediate if hemodynamically unstable). Aggressive medical therapy. |

## Actionable Pharmacotherapy for Intermediate/High Risk (TIMI ≥ 3)

Upon determining an intermediate or high-risk TIMI score, initiate the following prior to angiography:

1. **Antiplatelet Therapy (DAPT):**
   - **Aspirin:** 162–325 mg loading dose, then 81 mg daily.
   - **P2Y12 Inhibitor:** Add Ticagrelor (180 mg load, 90 mg BID) OR Prasugrel (only after coronary anatomy is known/at time of PCI). Clopidogrel is second-line if others are contraindicated or unavailable.
2. **Parenteral Anticoagulation:**
   - **Enoxaparin:** 1 mg/kg SC every 12 hours (dose adjust for CrCl < 30).
   - **OR Unfractionated Heparin (UFH):** IV bolus + infusion, titrated to aPTT.
   - **OR Fondaparinux:** 2.5 mg SC daily (preferred for high bleeding risk).
3. **Anti-Ischemic Therapy:**
   - Sublingual Nitroglycerin (followed by IV if persistent pain).
   - High-intensity Statin (e.g., Atorvastatin 80 mg).
   - Beta-blocker (oral, if no signs of heart failure or risk for cardiogenic shock).

> **OpenMedicine Calculator:** `calculate_timi_ua_nstemi` — available via MCP for automated scoring.

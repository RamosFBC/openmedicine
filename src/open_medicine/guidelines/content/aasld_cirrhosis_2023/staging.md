# Cirrhosis Staging — AASLD 2023

## Child-Pugh Classification

The Child-Pugh score assesses the severity of chronic liver disease using five clinical and laboratory parameters (5–15 points total).

### Scoring Criteria

| Parameter | 1 Point | 2 Points | 3 Points |
|---|---|---|---|
| **Bilirubin** (mg/dL) | < 2 | 2–3 | > 3 |
| **Albumin** (g/dL) | > 3.5 | 2.8–3.5 | < 2.8 |
| **INR** | < 1.7 | 1.7–2.3 | > 2.3 |
| **Ascites** | None | Mild (diuretic-responsive) | Moderate-Severe (refractory) |
| **Encephalopathy** | None | Grade I–II (managed) | Grade III–IV (poorly controlled) |

### Classification and Clinical Implications

- **Child-Pugh A (5–6 points): Compensated cirrhosis**
  - **Action:** Monitor every 6–12 months. Lifestyle modifications (alcohol abstinence, weight management). Screen for HCC every 6 months (ultrasound + AFP). Screen for varices (or start carvedilol empirically if CSPH identified). Avoid hepatotoxic medications and NSAIDs.
  - **Perioperative risk:** Low (mortality ~10% for abdominal surgery).

- **Child-Pugh B (7–9 points): Significant hepatic impairment**
  - **Action:** Active complication management. Diuretics for ascites (Spironolactone 100 mg + Furosemide 40 mg, titrate). Lactulose for encephalopathy. Initiate or continue carvedilol for portal hypertension. **Refer to hepatology for transplant evaluation.** Dose-adjust or avoid renally- and hepatically-cleared medications.
  - **Perioperative risk:** Moderate (mortality ~30%).

- **Child-Pugh C (10–15 points): Decompensated cirrhosis**
  - **Action:** Urgent transplant evaluation. Aggressive complication management. Frequent paracentesis for refractory ascites. Consider TIPS if appropriate. Avoid elective surgery (mortality ~80%). Optimize nutrition (35 kcal/kg/day, 1.2–1.5 g protein/kg/day). Screen for micronutrient deficiencies annually.
  - **Perioperative risk:** Very high (mortality ~80%).

> **OpenMedicine Calculator:** `calculate_child_pugh` — available via MCP for automated scoring.

## MELD-Na Score and Transplant Prioritization

The Model for End-Stage Liver Disease with Sodium (MELD-Na) uses objective laboratory values (bilirubin, INR, creatinine, sodium) to predict 90-day mortality and prioritize liver transplant listing.

### Actionable Thresholds

- **MELD-Na < 10:** Low short-term mortality. Continue monitoring and outpatient management.
- **MELD-Na 10–14:** Moderate risk. Consider hepatology referral and transplant center evaluation.
- **MELD-Na ≥ 15:** **Refer for liver transplant evaluation** (standard listing threshold per UNOS/OPTN). 90-day mortality risk increases significantly above this threshold.
- **MELD-Na ≥ 25:** High priority listing. 90-day mortality ~20%.
- **MELD-Na ≥ 40:** Very high mortality. Consider urgent or exception listing.

> **OpenMedicine Calculator:** `calculate_meld_na` — available via MCP for automated scoring.

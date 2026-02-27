# Anticoagulation Therapy for VTE — ASH 2020

## DOAC vs VKA for Primary Treatment (Recommendation 3)

The ASH guideline panel suggests using **DOACs over vitamin K antagonists (VKAs)** for patients with DVT and/or PE (conditional recommendation, moderate certainty of evidence ⨁⨁⨁○).

**Exclusions from DOAC preference:**
- Severe renal insufficiency (CrCl < 30 mL/min)
- Moderate-to-severe hepatic disease (associated with coagulopathy)
- Antiphospholipid antibody syndrome

### DOAC Selection (Recommendation 4)

The panel does not suggest one DOAC over another (conditional recommendation, very low certainty of evidence ⨁○○○). Selection should be guided by:
- Lead-in parenteral anticoagulation requirements
- Dosing frequency preferences
- Cost and insurance coverage
- Renal function
- Drug–drug interactions

---

## DOAC Regimens for DVT and PE

### Single-Drug Approach (No Parenteral Lead-In Required)

| Drug | Initial Phase | Maintenance Phase |
|---|---|---|
| **Apixaban** | 10 mg orally twice daily for **7 days** | 5 mg orally twice daily |
| **Rivaroxaban** | 15 mg orally twice daily for **21 days** | 20 mg orally once daily (with food) |

> **OpenMedicine Calculators:** `calculate_apixaban_dosing` and `calculate_rivaroxaban_dosing` — available via MCP for automated dosing.

### Parenteral Lead-In Required (5–10 Days)

| Drug | Lead-In Phase | Maintenance Phase |
|---|---|---|
| **Dabigatran** | LMWH or UFH for 5–10 days | 150 mg orally twice daily |
| **Edoxaban** | LMWH or UFH for 5–10 days | 60 mg orally once daily (30 mg if CrCl 15–50 mL/min, body weight ≤ 60 kg, or concomitant P-gp inhibitor) |

> **OpenMedicine Calculators:** `calculate_dabigatran_dosing` and `calculate_edoxaban_dosing` — available via MCP for automated dosing.

---

## Parenteral Anticoagulation

### LMWH

For initial parenteral anticoagulation (when required as lead-in or as primary therapy):

| Drug | Dose | Route | Frequency |
|---|---|---|---|
| Enoxaparin | 1 mg/kg | Subcutaneous | Every 12 hours |
| Enoxaparin (alternative) | 1.5 mg/kg | Subcutaneous | Once daily |

- Dose reduction for CrCl < 30 mL/min: 1 mg/kg subcutaneously once daily.
- Monitoring: Anti-Xa levels may be used in obesity, renal impairment, or pregnancy.

> **OpenMedicine Calculator:** `calculate_enoxaparin_dosing` — available via MCP for weight-based dosing.

### Unfractionated Heparin (UFH)

- **IV bolus:** 80 units/kg, then continuous infusion at 18 units/kg/hour.
- **Target aPTT:** 1.5–2.5 times control (or per institutional nomogram).
- UFH is preferred when rapid reversal may be needed (e.g., pending surgery, high bleeding risk) or in severe renal impairment (CrCl < 30 mL/min).

> **OpenMedicine Calculator:** `calculate_heparin_dosing` — available via MCP for weight-based dosing.

---

## Vitamin K Antagonist (Warfarin) Therapy

When VKA is chosen (e.g., severe renal impairment, antiphospholipid syndrome, patient preference, or cost):

### INR Target (Recommendation 21 — Strong, Moderate Certainty ⨁⨁⨁○)

**INR range of 2.0–3.0** is recommended over a lower INR range (e.g., 1.5–1.9) for secondary prevention.

- Overlap with parenteral anticoagulant (LMWH or UFH) for a minimum of 5 days AND until INR ≥ 2.0 for at least 24 hours.
- Warfarin starting dose: typically 5 mg daily, adjusted based on INR response.

> **OpenMedicine Calculator:** `calculate_warfarin_initiation` — available via MCP for initial dosing.

---

## Treatment Setting

### DVT — Home vs Hospital (Recommendation 1, Conditional, Low Certainty ⨁⨁○○)

Home treatment is suggested over hospital treatment for uncomplicated DVT.

**Criteria for home treatment:**
- Stable clinical condition
- Ability to comply with treatment and follow-up
- Adequate social support
- No high-risk features (massive iliofemoral DVT, phlegmasia)

### PE — Home vs Hospital (Recommendation 2, Conditional, Very Low Certainty ⨁○○○)

Home treatment may be suggested over hospital treatment for selected low-risk PE patients.

- Requires risk stratification with PESI or simplified PESI score.
- Low-risk PE (sPESI = 0 or PESI class I–II) may be considered for home treatment.

> **OpenMedicine Calculators:** `calculate_wells_pe` and `calculate_wells_dvt` — available via MCP for pre-test probability assessment.

---

## Anticoagulation Selection Algorithm

```
Patient with confirmed acute DVT or PE
  → Hemodynamically stable?
      → NO → Assess for thrombolysis (see advanced_management section)
      → YES → Continue to anticoagulation selection
  → CrCl < 30 mL/min?
      → YES → Use UFH or dose-adjusted LMWH initially → transition to warfarin (INR 2.0–3.0)
              DOACs generally avoided (limited data)
  → Antiphospholipid syndrome?
      → YES → Use warfarin (INR 2.0–3.0); DOACs NOT recommended
  → Moderate-severe liver disease?
      → YES → Use LMWH or UFH; warfarin with caution; DOACs generally avoided
  → None of above → DOAC preferred (Rec 3)
      → Prefer single-drug approach (apixaban or rivaroxaban)?
          → YES → Start apixaban 10 mg BID x 7 days then 5 mg BID
                   OR rivaroxaban 15 mg BID x 21 days then 20 mg daily
      → Prefer parenteral lead-in approach?
          → YES → Start LMWH (enoxaparin 1 mg/kg BID) for 5–10 days
                   then dabigatran 150 mg BID or edoxaban 60 mg daily
```

## Limitations

- DOAC evidence is derived primarily from clinical trials that excluded severe renal impairment, extremes of body weight (< 50 kg or > 120 kg in some trials), and active cancer.
- Head-to-head comparison trials between individual DOACs do not exist; the recommendation not to prefer one DOAC over another is based on indirect evidence.
- Home treatment for PE requires careful risk stratification; the evidence base is limited and clinical judgment is essential.

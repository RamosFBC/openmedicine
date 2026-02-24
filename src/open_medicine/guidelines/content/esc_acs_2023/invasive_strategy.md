# Invasive Strategy Timing in NSTE-ACS — ESC 2023

## Overview

The ESC 2023 guideline defines three tiers of invasive strategy timing based on clinical risk features and the GRACE score. All NSTE-ACS patients should be assessed for the appropriate timing of coronary angiography.

## Tiered Invasive Strategy Algorithm

### Tier 1: Immediate Invasive Strategy (< 2 Hours) — Class I, Level C

**Indication:** Any one of the following very high-risk features:
- Hemodynamic instability or cardiogenic shock
- Recurrent or refractory chest pain despite medical treatment
- Life-threatening arrhythmias (sustained VT, VF, or hemodynamically significant arrhythmia)
- Mechanical complications of MI (acute mitral regurgitation from papillary muscle rupture, ventricular septal defect, free wall rupture)
- Acute heart failure clearly attributable to ongoing ischemia
- Recurrent dynamic ST-segment or T-wave changes, particularly intermittent ST-segment elevation

**Action:** Transfer directly to catheterization laboratory. Do NOT delay for additional risk scoring or serial biomarkers.

### Tier 2: Early Invasive Strategy (Within 24 Hours) — Class I, Level A

**Indication:** At least one high-risk criterion present:
- Confirmed diagnosis of NSTEMI (troponin rise and/or fall with at least one value above 99th percentile URL)
- Dynamic new or presumably new ST-segment or T-wave changes (symptomatic or silent)
- Transient ST-segment elevation
- **GRACE risk score > 140**

**Action:**
1. Initiate medical therapy (aspirin, parenteral anticoagulation — see Antithrombotic Therapy section).
2. **Do NOT routinely pre-treat with P2Y12 inhibitor** before knowing coronary anatomy (Class III).
3. Arrange coronary angiography within 24 hours of presentation.
4. Administer P2Y12 inhibitor (prasugrel or ticagrelor) once coronary anatomy is known and PCI is planned.

> **OpenMedicine Calculator:** `calculate_grace_score` — available via MCP for automated GRACE 2.0 scoring.

### Tier 3: Inpatient Invasive Strategy (During Hospitalization) — Class I, Level C

**Indication:** NSTE-ACS patients with high-risk criteria or a high index of suspicion for unstable angina who do not meet Tier 1 or Tier 2 criteria.

**Action:**
1. Initiate full medical therapy (aspirin, anticoagulation, consider pre-treatment with P2Y12 if delay > 24 hours anticipated).
2. Arrange coronary angiography during index hospital admission (within 72 hours).
3. Perform non-invasive ischemia testing (stress echocardiography, stress MRI, or CCTA) if clinical suspicion is low and diagnosis uncertain.

### Selective (Conservative) Strategy

**When to consider:**
- Very low-risk patients: low GRACE score (< 109), negative serial hs-cTn, no recurrent symptoms
- Severe comorbidities or frailty where invasive management is unlikely to improve quality of life

**Action:** Optimal medical therapy + non-invasive testing for inducible ischemia. Escalate to invasive if recurrent symptoms or positive stress test.

---

## Revascularization Details

### PCI (Percutaneous Coronary Intervention)
- **Culprit-lesion PCI** is recommended during index procedure for NSTE-ACS.
- **Complete revascularization** (all significant stenoses) should be considered before or during hospitalization (Class IIa, Level of Evidence A).
- **Radial access** is the default access site (reduced bleeding and mortality vs. femoral) (Class I).
- **DES (drug-eluting stents)** are recommended over BMS (Class I).

### CABG (Coronary Artery Bypass Grafting)
- Consider for left main disease, three-vessel disease, or complex coronary anatomy where PCI is not feasible.
- **Timing:** If CABG is planned, discontinue ticagrelor ≥ 3 days and prasugrel ≥ 7 days before surgery to reduce surgical bleeding (Class I). Clopidogrel: discontinue ≥ 5 days before.

---

## Post-Angiography Decision Tree

```
Coronary angiography performed
  → Culprit lesion identified?
      → YES → PCI amenable?
              → YES → Proceed to PCI (radial access, DES)
                      → Start P2Y12 inhibitor (prasugrel preferred for PCI; ticagrelor if conservative/no PCI)
              → NO → Consider CABG (discontinue P2Y12 per washout periods above)
      → NO → Consider non-obstructive ACS:
             → Assess for MINOCA (myocardial infarction with non-obstructive coronary arteries)
             → Perform cardiac MRI to evaluate for myocarditis, Takotsubo, or microvascular dysfunction
             → Treat underlying etiology
```

## Limitations

- Optimal timing within the 24-hour window (e.g., immediate overnight vs. next morning) remains debated; the guideline states "within 24 hours" without specifying a narrower window.
- GRACE score was not validated in very elderly or severely frail populations.
- The conservative strategy should not delay invasive management if clinical deterioration occurs.

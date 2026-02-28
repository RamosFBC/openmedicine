# Initial Assessment and Grading of Aneurysmal Subarachnoid Hemorrhage — AHA/ASA 2023

## Clinical Presentation

Aneurysmal subarachnoid hemorrhage (aSAH) classically presents with:

- **Sudden severe headache** ("worst headache of my life" / thunderclap headache)
- Nausea and vomiting
- Neck stiffness (meningismus)
- Photophobia
- Altered level of consciousness (ranging from confusion to coma)
- Focal neurological deficits (cranial nerve palsies, hemiparesis)
- Seizures at onset (in approximately 10% of patients)

## Diagnosis

### Non-Contrast CT Head

- Non-contrast CT is the first-line diagnostic study for suspected SAH (Class I, LOE B-NR).
- Sensitivity is approximately **95–100%** within the first 6 hours and decreases to approximately **85–90%** at 24 hours and **50%** at 1 week.
- CT sensitivity decreases significantly after 6 hours from onset.

### Lumbar Puncture

- When CT is negative but clinical suspicion persists, **lumbar puncture** should be performed to detect xanthochromia or elevated red blood cells (Class I, LOE B-NR).
- Xanthochromia (yellowish discoloration of CSF due to bilirubin from hemoglobin breakdown) is the most reliable CSF finding.

### CT Angiography (CTA)

- CTA should be performed to identify the source aneurysm once SAH is diagnosed (Class I, LOE B-NR).
- Sensitivity for detecting aneurysms ≥ 3 mm is approximately 95–100%.
- Digital subtraction angiography (DSA) remains the gold standard when CTA is negative or equivocal.

## Clinical Grading Scales

### Hunt and Hess (HH) Scale

The Hunt and Hess scale grades clinical severity based on symptoms and level of consciousness.

| Grade | Clinical Description | Approximate Mortality |
|-------|---------------------|----------------------|
| **1** | Asymptomatic or mild headache, slight nuchal rigidity | 1% |
| **2** | Moderate to severe headache, nuchal rigidity, no neurological deficit other than cranial nerve palsy | 5% |
| **3** | Drowsiness, confusion, or mild focal deficit | 19% |
| **4** | Stupor, moderate to severe hemiparesis, possible early decerebrate rigidity | 42% |
| **5** | Deep coma, decerebrate rigidity, moribund appearance | 77% |

> **OpenMedicine Calculator:** `calculate_hunt_hess` — available via MCP for automated Hunt and Hess grading.

### Glasgow Coma Scale (GCS)

The GCS should be assessed at presentation as part of clinical grading. GCS is a component of the WFNS scale and independently predicts outcome.

> **OpenMedicine Calculator:** `calculate_gcs` — available via MCP for automated GCS scoring.

### World Federation of Neurosurgical Societies (WFNS) Scale

| Grade | GCS Score | Motor Deficit |
|-------|-----------|--------------|
| **I** | 15 | Absent |
| **II** | 13–14 | Absent |
| **III** | 13–14 | Present |
| **IV** | 7–12 | Present or absent |
| **V** | 3–6 | Present or absent |

## Radiographic Grading: Modified Fisher Scale

The modified Fisher scale grades the amount and distribution of subarachnoid blood on CT to predict vasospasm risk.

| Grade | CT Findings | Vasospasm Risk |
|-------|------------|----------------|
| **0** | No SAH or IVH | Low |
| **1** | Thin SAH, no IVH | Low |
| **2** | Thin SAH with IVH | Moderate |
| **3** | Thick SAH, no IVH | High |
| **4** | Thick SAH with IVH | Highest |

- Thick SAH is defined as a clot > 1 mm in the vertical plane (interhemispheric fissure, insular cistern, or ambient cistern) or a completely filled cistern.

> **OpenMedicine Calculator:** `calculate_fisher_grade` — available via MCP for automated Fisher Grade classification.

## Risk Stratification and Prognosis

- Clinical grading (HH and WFNS) and radiographic grading (modified Fisher) together inform prognosis and facilitate shared decision-making with patients and families.
- Prognostication should NOT be performed in the first 72 hours in high-grade SAH patients, as early aggressive management may lead to meaningful recovery.

## Limitations

- No single grading system perfectly predicts outcome. Clinical judgment remains essential.
- Inter-rater reliability for clinical grading scales can be variable, particularly for intermediate grades.
- GCS motor score alone may have predictive value comparable to the full WFNS grade.
- CT sensitivity for SAH diminishes significantly after 6 hours from onset; lumbar puncture should be used when CT is negative but clinical suspicion persists.

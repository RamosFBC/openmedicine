# Emergency Diagnosis and Assessment of Spontaneous Intracerebral Hemorrhage — AHA/ASA 2022

## Scope

This guideline addresses spontaneous intracerebral hemorrhage (ICH) in adults. It explicitly excludes ICH caused by head trauma and hemorrhages with a visualized structural cause such as vascular malformation, saccular aneurysm, or hemorrhage-prone neoplasm.

## Emergency Imaging

### Non-Contrast CT (NCCT)

- **Emergent non-contrast CT of the head** is the first-line imaging modality to confirm or exclude ICH due to its widespread availability, speed, high diagnostic accuracy, and simplicity (Class I, LOE B-NR).
- NCCT can estimate hematoma volume, identify mass effect, midline shift, intraventricular hemorrhage (IVH), and hydrocephalus.

### Advanced Imaging for Etiology

- **CT angiography (CTA), CT venography (CTV), contrast-enhanced CT, contrast-enhanced MRI, MRA, and MRV** can be useful to evaluate for underlying structural lesions including vascular malformations and tumors when there is clinical or radiological suspicion (Class IIa, LOE B-NR).
- In patients without a clear cause of ICH, further vascular and structural imaging should be performed to identify secondary causes.

### Imaging for Hematoma Expansion Risk

- **CTA and contrast-enhanced CT** may be considered to help identify patients at risk for hematoma expansion (Class IIb, LOE B-NR).
  - The **spot sign** (active contrast extravasation within the hematoma on CTA) is a predictor of hematoma expansion.
  - Sensitivity and positive predictive value of the spot sign are highest between 0 and 2 hours from ICH onset and decrease over time.
- **NCCT markers** (heterogeneous densities within the hematoma, irregular margins, satellite lesions) may also be considered to identify patients at risk for hematoma expansion (Class IIb, LOE B-NR).
- Hematoma expansion tends to occur early, typically within 24 hours of ICH onset, and is associated with poor outcomes and increased mortality.

## Initial Neurological Assessment

### Standardized Stroke Scales

- Use of a **standardized stroke rating scale, preferably the NIHSS**, is recommended during the initial emergency evaluation (Class I, LOE B-NR).
- Nurses and clinicians should be trained in detailed assessment of neurological function using standardized scales including:
  - **National Institutes of Health Stroke Scale (NIHSS)**
  - **Glasgow Coma Scale (GCS)**
  - **Glasgow Outcome Scale (GOS)**

> **OpenMedicine Calculator:** `calculate_gcs` -- available via MCP for automated GCS scoring.

### ICH Score

The ICH Score is a validated clinical grading scale used for severity assessment in spontaneous ICH. The guideline recommends using ICH scores as a **measure of severity, not solely as a predictor of mortality**, and **not limiting treatments based on severity scores alone** (Class IIa, LOE B-NR).

| Component | Criteria | Points |
|-----------|----------|--------|
| **GCS score** | 3-4 | 2 |
| | 5-12 | 1 |
| | 13-15 | 0 |
| **ICH volume** | >= 30 mL | 1 |
| | < 30 mL | 0 |
| **IVH** | Yes | 1 |
| | No | 0 |
| **Infratentorial origin** | Yes | 1 |
| | No | 0 |
| **Age** | >= 80 years | 1 |
| | < 80 years | 0 |

- **Score range:** 0-6 (higher scores indicate greater severity).

## Organized Inpatient Care

- In patients with spontaneous ICH, provision of care in a **specialized inpatient stroke unit** with a multidisciplinary team is recommended to improve outcomes and reduce mortality (Class I, LOE A).
- Access to neurosurgery, neurocritical care, and neuroradiology should be available.

## Goals of Care and Prognostication

- In patients with spontaneous ICH who do not have preexisting documented requests for life-sustaining therapy limitations, **aggressive care, including postponement of new do-not-attempt-resuscitation (DNAR) orders or withdrawal of medical support until at least the second full day of hospitalization**, is reasonable to decrease mortality and improve functional outcome (Class IIa, LOE B-NR).
- In patients with spontaneous ICH who have DNAR status, limiting other medical and surgical interventions, unless explicitly specified by the patient or surrogate, is associated with increased patient mortality.
- **Prognostication should be exercised with great caution** in the early period after ICH, particularly if the purpose is to consider withdrawal of support or DNAR orders. No outcome prediction model for ICH has adequately accounted for the impact of early care limitations on outcomes.

## Emergency Decision Algorithm

```
Patient with suspected spontaneous ICH
  --> Emergent non-contrast CT head
      --> ICH confirmed?
          --> YES:
              --> Perform NIHSS and GCS assessment
              --> Calculate ICH Score (GCS, volume, IVH, infratentorial, age)
              --> Admit to stroke unit / neurocritical care
              --> Initiate BP management (see blood_pressure_management section)
              --> Check coagulation status (INR, aPTT, platelet count, thrombin time)
                  --> On anticoagulant? --> Initiate reversal (see hemostatic_therapy section)
              --> CTA to evaluate for structural lesion and spot sign
              --> Neurosurgery consultation
              --> Postpone DNAR orders until >= day 2 (in absence of prior directives)
              --> Aggressive guideline-concordant therapy for all patients
          --> NO:
              --> Consider alternative diagnoses
              --> If clinical suspicion remains, consider MRI or repeat imaging
```

## Limitations

- CT sensitivity for ICH is highest in the acute phase but can miss small or chronic hemorrhages; MRI with gradient-echo or susceptibility-weighted imaging is more sensitive for microbleeds and chronic hemorrhage.
- The ICH Score was developed primarily as a mortality prediction tool. Its use for functional outcome prediction is less well validated. The guideline explicitly recommends against limiting treatments based on severity scores alone.
- Inter-rater reliability for neurological grading scales can vary, particularly in intubated or sedated patients.
- No outcome prediction model has been validated in a way that accounts for the impact of care limitations such as early DNAR orders.

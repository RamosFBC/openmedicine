# Severity Assessment in Acute Pancreatitis — ACG 2024

## Diagnosis

The diagnosis of acute pancreatitis requires **2 of the following 3 criteria**:

1. Characteristic abdominal pain (epigastric, often radiating to the back)
2. Serum amylase and/or lipase **≥ 3 times the upper limit of normal**
3. Characteristic findings on imaging (CT, MRI, or ultrasound)

**Lipase is superior to amylase** because it is more specifically associated with pancreatic disease. Imaging is not required for diagnosis if the first two criteria are met.

## Etiology

| Cause | Frequency | Key Diagnostic Feature |
|---|---|---|
| **Gallstones** | 40–70% | Transabdominal ultrasound |
| **Alcohol** | 25–35% | Significant history of alcohol use |
| **Hypertriglyceridemia** | 1–4% | Serum triglycerides > 1,000 mg/dL |
| **Idiopathic** | 10–25% | No identifiable cause after initial workup |

- The ACG **suggests** transabdominal ultrasound in all patients with AP to evaluate for biliary pancreatitis (Conditional, Very Low).
- In the absence of gallstones and/or significant alcohol use, serum triglyceride should be obtained and considered the etiology if **> 1,000 mg/dL**.

### Idiopathic Acute Pancreatitis

- The ACG **recommends** additional diagnostic evaluation with repeat abdominal ultrasound, MRI, and/or endoscopic ultrasound (EUS) in patients with idiopathic AP (Conditional, Very Low).
- EUS identifies an underlying etiology in approximately **one-third** of patients after an initial attack.
- Routine diagnostic ERCP should **NOT** be performed because of the risk of inducing pancreatitis.

## Revised Atlanta Classification (2012)

The ACG endorses the Revised Atlanta Classification for severity grading:

| Severity | Definition | Frequency |
|---|---|---|
| **Mild** | No organ failure AND no local or systemic complications | ~80% of cases |
| **Moderately Severe** | Transient organ failure (resolves within 48 hours) AND/OR local complications without persistent organ failure | ~15% |
| **Severe** | Persistent organ failure (> 48 hours) AND/OR death | ~5% |

The critical threshold is the **48-hour mark** distinguishing transient from persistent organ failure.

### Organ Failure — Modified Marshall Scoring System

Organ failure is defined as a **Modified Marshall score ≥ 2** in at least one system:

| Organ System | Score = 0 | Score = 2 (Organ Failure) |
|---|---|---|
| **Respiratory** | PaO2/FiO2 > 400 | PaO2/FiO2 < 300 (PaO2 < 60 mmHg on room air) |
| **Renal** | Creatinine < 1.4 mg/dL | Creatinine > 1.8 mg/dL (> 2 mg/dL after rehydration) |
| **Cardiovascular** | SBP > 90 mmHg | SBP < 90 mmHg, not fluid responsive |

## Morphologic Classification (Revised Atlanta)

### Two Types of Pancreatitis

1. **Interstitial edematous pancreatitis** — diffuse or focal enlargement of the pancreas without necrosis
2. **Necrotizing pancreatitis** — presence of pancreatic and/or peripancreatic necrosis

### Four Types of Pancreatic Collections

| Collection | Timing | Necrosis Present? | Wall |
|---|---|---|---|
| **Acute peripancreatic fluid collection (APFC)** | < 4 weeks | No | No capsule |
| **Pseudocyst** | > 4 weeks | No | Well-defined capsule |
| **Acute necrotic collection (ANC)** | < 4 weeks | Yes | No capsule |
| **Walled-off necrosis (WOPN)** | > 4 weeks | Yes | Well-defined capsule |

## Severity Scoring Systems

The ACG acknowledges that severity scoring systems are **cumbersome, typically require 48 hours**, and when predictive of severity, the patient's condition is often clinically obvious.

### BISAP Score

The BISAP (Bedside Index for Severity in Acute Pancreatitis) is regarded as **the most accurate and applicable in routine practice** for predicting severity, death, and organ failure. It can be calculated within the first 24 hours using 5 bedside parameters.

> **OpenMedicine Calculator:** `calculate_bisap` — available via MCP for automated BISAP scoring.

### Ranson's Criteria

Ranson's Criteria remain a historically important prognostic tool for acute pancreatitis severity. A score ≥ 3 at 48 hours indicates severe disease.

> **OpenMedicine Calculator:** `calculate_ransons` — available via MCP for automated Ranson's scoring.

### Clinical Risk Factors for Severe Disease

Independent risk factors for a severe course include:

- Obesity (BMI > 30)
- Altered mental status
- Significant comorbidities
- SIRS at admission
- Elevated creatinine
- Elevated BUN
- Elevated hematocrit
- Pleural effusions or pulmonary infiltrates

## Imaging for Severity Assessment

- The ACG **recommends against** early/admission routine CT for determining severity (Conditional, Very Low).
- CT should be reserved for patients with an **unclear diagnosis** or who **fail to improve clinically within 48–72 hours** after admission.

## Limitations

- The inability to reliably predict the development of severe disease within the first 24–48 hours after admission remains a significant clinical challenge.
- Scoring systems (BISAP, Ranson's, APACHE II) have moderate sensitivity and specificity; none is sufficient as a sole determinant of management decisions.
- The Revised Atlanta Classification requires clinical reassessment at 48 hours to distinguish transient from persistent organ failure.

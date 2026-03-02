# Diagnosis of Diabetic Ketoacidosis and Hyperglycemic Hyperosmolar State — ADA 2024

## Overview

This consensus report provides updated diagnostic criteria for diabetic ketoacidosis (DKA) and hyperglycemic hyperosmolar state (HHS) in adults with diabetes. It was jointly developed by the ADA, EASD, JBDS, AACE, and DTS, and represents the first update since 2009.

## DKA Diagnostic Criteria (D-K-A Framework)

The diagnosis of DKA requires **all three** of the following criteria:

| Criterion | Parameter | Threshold |
|---|---|---|
| **D — Diabetes/Hyperglycemia** | Plasma glucose | >= 200 mg/dL (11.1 mmol/L) OR prior history of diabetes (irrespective of glucose) |
| **K — Ketosis** | Beta-hydroxybutyrate (preferred) | >= 3.0 mmol/L |
| | Urine ketones (if beta-hydroxybutyrate unavailable) | >= 2+ |
| **A — Acidosis** | Venous pH | < 7.3 |
| | OR Bicarbonate | < 18 mmol/L |

### Key Diagnostic Updates From Prior Guidelines

- **Glucose threshold lowered** from > 250 mg/dL to >= 200 mg/dL (11.1 mmol/L), or any glucose level with a prior diabetes history.
- **Quantitative beta-hydroxybutyrate** replaces urine ketones as the preferred diagnostic and monitoring tool.
- **Anion gap removed** from diagnostic criteria. The report states that various factors influencing acid-base status make the anion gap less reliable than direct beta-hydroxybutyrate measurement. However, anion gap may have value if ketone measurement is unavailable.
- **Euglycemic DKA** is explicitly recognized: approximately 10% of patients present with glucose < 200 mg/dL (11.1 mmol/L). This is increasingly common with SGLT2 inhibitor use; in one series, 35% of people treated with SGLT2 inhibitors presenting with DKA had glucose levels < 200 mg/dL.

> **OpenMedicine Calculator:** `calculate_anion_gap` — available via MCP for automated anion gap calculation. Note: the 2024 consensus report removed anion gap from DKA diagnostic criteria, favoring direct beta-hydroxybutyrate measurement, but anion gap remains useful when ketone assays are unavailable.

## DKA Severity Classification

| Severity | Beta-Hydroxybutyrate | pH | Bicarbonate | Mental Status | Recommended Setting |
|---|---|---|---|---|---|
| **Mild** | 3.0-6.0 mmol/L | > 7.25 | >= 15 mmol/L | Normal | Regular ward / observation unit |
| **Moderate** | 3.0-6.0 mmol/L | 7.0-7.25 | 10 to < 15 mmol/L | Normal or drowsy | Step-down / intermediate care |
| **Severe** | > 6.0 mmol/L | < 7.0 | < 10 mmol/L | Stupor or coma | ICU |

**Not all criteria must be met** to classify severity. Clinical judgment and resource availability should ultimately determine the severity classification and guide decisions on admission level of care.

## HHS Diagnostic Criteria

The diagnosis of HHS requires **all four** of the following:

| Criterion | Threshold |
|---|---|
| **Severe hyperglycemia** | Plasma glucose >= 600 mg/dL (33.3 mmol/L) |
| **Hyperosmolality** | Effective serum osmolality > 300 mOsm/kg OR total serum osmolality > 320 mOsm/kg |
| **Absence of significant ketonemia** | Beta-hydroxybutyrate < 3.0 mmol/L OR urine ketones <= 2+ |
| **Absence of acidosis** | pH >= 7.3 AND bicarbonate >= 15 mmol/L |

### Key HHS Updates

- **Mental status impairment is no longer a diagnostic criterion**, although altered mental status is commonly present and correlates with osmolality.
- **Effective serum osmolality** is calculated as: 2 x [measured Na+ (mEq/L)] + glucose (mg/dL) / 18.
- Total serum osmolality includes BUN: 2 x [Na+ (mEq/L)] + glucose (mg/dL) / 18 + BUN (mg/dL) / 2.8.

> **OpenMedicine Calculator:** `calculate_corrected_sodium` — available via MCP for corrected sodium calculation in hyperglycemia. The corrected sodium is essential for assessing true hydration status and guiding fluid replacement in DKA and HHS.

## Mixed DKA/HHS

When patients present with **mixed features** (hyperosmolality with significant ketonemia or acidosis), the condition should be treated as DKA with a fixed-rate intravenous insulin infusion at **0.1 units/kg per hour**.

## Corrected Sodium

To assess true sodium status in the setting of hyperglycemia, the consensus report references the corrected sodium calculation:

- Corrected Na+ = measured Na+ + 0.36 x (plasma glucose [mmol/L] - 5.6)
- Equivalently: Corrected Na+ = measured Na+ + 1.6 x [(glucose [mg/dL] - 100) / 100]

A reduction of 100 mg/dL of glucose results in a 1.6 mmol/L rise in sodium concentration. The initial rise in serum sodium during treatment is an expected finding and is **not** an indication to give hypotonic fluids.

## Precipitating Factors

Identifying and treating the precipitating cause is essential for management:

| Factor | Notes |
|---|---|
| **Infection** | Most common precipitant (30-60% of HHS cases); UTI and pneumonia most frequent |
| **Insulin omission/insufficiency** | Second most common cause; includes nonadherence, pump failure, or inadequate dosing |
| **New-onset diabetes** | 6-21% of adults present with DKA as initial diagnosis of T1D |
| **Medications** | Glucocorticoids, antipsychotics, checkpoint inhibitors (1-2% develop autoimmune diabetes with high DKA risk) |
| **SGLT2 inhibitors** | Increase DKA risk, especially in T1D; often cause euglycemic presentation |
| **Psychological/socioeconomic** | Psychological stress, low socioeconomic status, younger age, and substance abuse are risk factors for recurrent DKA |

## Limitations

- The D-K-A diagnostic framework relies on the availability of quantitative beta-hydroxybutyrate testing, which may not be universally available in all clinical settings.
- The consensus report is based on expert opinion and review of available evidence rather than a formal systematic review with graded recommendations.
- Severity classification thresholds are consensus-based and may not apply uniformly to all patient populations.
- Anion gap, while removed from diagnostic criteria, remains clinically useful in resource-limited settings where beta-hydroxybutyrate is unavailable.

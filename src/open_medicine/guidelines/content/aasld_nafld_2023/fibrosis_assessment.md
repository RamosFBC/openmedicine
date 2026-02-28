# Noninvasive Fibrosis Assessment — AASLD 2023

## Two-Step Algorithm

The AASLD recommends a sequential approach to fibrosis assessment using noninvasive tests (NITs):

### Step 1: FIB-4 Index (First-Line Blood-Based Test)

The **FIB-4 index** is recommended as the first-line noninvasive test for risk stratification.

| FIB-4 Result | Age < 65 | Age ≥ 65 | Action |
|---|---|---|---|
| **< 1.3** | Low risk | Low risk | Follow in primary care; reassess every 1–2 years |
| **1.3–2.67** | Indeterminate | Use > 2.0 cutoff | Proceed to Step 2 (secondary NIT) |
| **> 2.67** | High risk | High risk | Refer directly to hepatology |

- In patients **older than age 65**, a FIB-4 cutoff of **> 2.0** should be used for the indeterminate range to account for age-related increases.
- FIB-4 calculation uses: age, AST, ALT, and platelet count.

> **OpenMedicine Calculator:** `calculate_fib4` — available via MCP for automated FIB-4 scoring.

### Step 2: Secondary NIT (For FIB-4 ≥ 1.3)

When FIB-4 is ≥ 1.3 (or > 2.0 in age ≥ 65), a secondary assessment should be performed:

#### Vibration-Controlled Transient Elastography (VCTE / FibroScan)

- **< 8 kPa:** Advanced fibrosis unlikely; monitor and reassess
- **8–12 kPa:** Indeterminate; consider liver biopsy or additional testing
- **> 12 kPa:** Advanced fibrosis likely; refer to hepatology

#### Enhanced Liver Fibrosis (ELF) Test

- **< 9.8:** Advanced fibrosis unlikely
- **≥ 9.8:** Advanced fibrosis likely; refer to hepatology

#### MR Elastography (MRE)

- **< 3.63 kPa:** Advanced fibrosis unlikely
- **≥ 3.63 kPa:** Advanced fibrosis likely

## NAFLD Fibrosis Score (NFS)

The NFS is an alternative blood-based scoring system. The AASLD guidance notes FIB-4 is generally preferred, but NFS remains a validated option.

| NFS Result | Interpretation |
|---|---|
| **< −1.455** | Low risk of advanced fibrosis (NPV 93%) |
| **−1.455 to 0.676** | Indeterminate |
| **> 0.676** | High risk of advanced fibrosis (PPV 90%) |

NFS uses 6 variables: age, BMI, IFG/diabetes status, AST/ALT ratio, platelet count, and albumin.

> **OpenMedicine Calculator:** `calculate_nafld_fibrosis` — available via MCP for automated NFS calculation.

## Referral Algorithm

```
Patient with suspected NAFLD/MASLD
  → Calculate FIB-4
    → FIB-4 < 1.3 → Low risk → Primary care follow-up (reassess every 1–2 years)
    → FIB-4 1.3–2.67 → Indeterminate → Perform VCTE or ELF
      → VCTE < 8 kPa or ELF < 9.8 → Low risk → Primary care follow-up
      → VCTE 8–12 kPa → Consider liver biopsy
      → VCTE > 12 kPa or ELF ≥ 9.8 → Refer to hepatology
    → FIB-4 > 2.67 → High risk → Direct referral to hepatology
```

## Limitations

- FIB-4 has reduced specificity in patients aged > 65 due to age-related increases in the score.
- VCTE can be unreliable in patients with BMI > 40 kg/m² or narrow intercostal spaces; the XL probe improves accuracy in obesity.
- All noninvasive tests have an indeterminate range where liver biopsy may still be needed.
- Serial monitoring intervals for NITs have not been established in prospective studies.

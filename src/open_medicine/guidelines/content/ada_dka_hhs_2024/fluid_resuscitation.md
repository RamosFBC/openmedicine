# Fluid Resuscitation in DKA and HHS — ADA 2024

## Goals of Fluid Therapy

Fluid resuscitation aims to restore intravascular volume, correct dehydration, improve tissue perfusion, and reduce plasma glucose concentration. Patients with DKA typically have a total body water deficit of 5-7 L; patients with HHS may have deficits of 7-12 L.

## Initial Fluid Resuscitation (First 2-4 Hours)

### Patients Without Cardiac or Renal Compromise

- **Fluid type:** Isotonic saline (0.9% NaCl) or balanced crystalloid solutions (e.g., lactated Ringer's, Plasma-Lyte).
- **Rate:** 500-1,000 mL/hour for the first 2-4 hours.
- Balanced crystalloids are suggested when available, as they are associated with faster resolution, less hyperchloremic metabolic acidosis, and shorter hospital stay.

### Patients With Cardiac or Renal Compromise (Including Older Adults)

- **Rate:** 250 mL boluses with frequent hemodynamic reassessment.
- Requires careful monitoring for volume overload.
- Older adults should receive smaller, more cautious fluid volumes due to the higher risk of fluid overload.

### Patients With End-Stage Renal Disease (ESRD) on Dialysis

- **Rate:** 250 mL boluses with careful fluid administration.
- Frequent potassium monitoring is essential.

## Subsequent Fluid Replacement

Once intravascular volume is restored, subsequent fluid replacement depends on:

1. **Hemodynamic status** (blood pressure, heart rate)
2. **Fluid input-output balance**
3. **Sodium concentration**

### Sodium-Based Fluid Selection

```
Intravascular volume restored
  --> Assess corrected serum sodium
      --> Corrected Na+ low:
          --> Continue 0.9% NaCl
      --> Corrected Na+ high or normal:
          --> 0.45% NaCl is indicated ONLY if osmolality is not declining
              despite adequate positive fluid balance and appropriate insulin
              administration
          --> Otherwise, continue isotonic fluids
```

**Key principle:** The initial rise in serum sodium during treatment is an expected physiological response (a decrease of 100 mg/dL glucose results in a 1.6 mmol/L rise in Na+). This rise is **not** an indication to switch to hypotonic fluids.

> **OpenMedicine Calculator:** `calculate_corrected_sodium` — available via MCP for automated corrected sodium calculation. Essential for determining true sodium status in hyperglycemia and guiding fluid type selection.

## Dextrose Addition

- **When plasma glucose falls below 250 mg/dL:** Switch to or add **5-10% dextrose** to the IV fluid regimen.
- Continue insulin therapy to resolve ketonemia/acidosis; dextrose prevents hypoglycemia while allowing continued insulin administration.
- In DKA, the goal is to maintain glucose around 200 mg/dL while insulin continues until ketone resolution.

## HHS-Specific Correction Rate Limits

In HHS, overly rapid correction of glucose, sodium, and osmolality carries a risk of neurologic complications including cerebral edema. The following maximum correction rates apply:

| Parameter | Maximum Correction Rate |
|---|---|
| **Glucose decline** | <= 90-120 mg/dL per hour |
| **Sodium decline** | <= 10 mmol/L per 24 hours |
| **Osmolality decline** | 3.0-8.0 mOsm/kg per hour |

## Monitoring During Fluid Resuscitation

| Parameter | Frequency |
|---|---|
| **Capillary glucose** | Every 1-2 hours |
| **Serum electrolytes, creatinine, beta-hydroxybutyrate, pH** | Every 4 hours |
| **Osmolality (HHS)** | Every 4 hours |
| **Fluid balance (input/output)** | Continuous |
| **Hemodynamic assessment** | Continuous; more frequent in cardiac/renal compromise |

## Fluid Resuscitation Algorithm

```
Patient presents with DKA or HHS
  --> Hemodynamic assessment
      --> Hemodynamically unstable (hypotensive, tachycardic)?
          --> Isotonic crystalloid 500-1,000 mL/hr x 2-4 hours
              --> Cardiac/renal compromise or age > 65?
                  --> 250 mL boluses with reassessment after each bolus
      --> Hemodynamically stable?
          --> Isotonic crystalloid at lower end (500 mL/hr)

  --> After 2-4 hours: Reassess
      --> Intravascular volume restored?
          --> Assess corrected serum sodium
          --> Adjust fluid type and rate accordingly (see above)
          --> Reduce rate to 150-250 mL/hr (guided by clinical status)

  --> Glucose < 250 mg/dL?
      --> Add dextrose 5-10% to IV fluids
      --> Continue insulin until resolution criteria met
```

## Hyperchloremia Prevention

- Hyperchloremia can occur with large-volume 0.9% NaCl administration.
- This can be treated or prevented using 0.45% NaCl or a combination of KCl and KPhos.
- Balanced crystalloid solutions (when available) reduce the incidence of hyperchloremic metabolic acidosis.

## Limitations

- Fluid resuscitation recommendations are largely based on expert consensus and observational data rather than large randomized controlled trials in adults with hyperglycemic crises.
- Optimal fluid type (0.9% NaCl vs. balanced crystalloid) remains an area of active investigation; the consensus report suggests balanced crystalloids when available but acknowledges limited definitive evidence.
- Individualization is essential for patients with heart failure, kidney disease, or advanced age; no specific algorithms for these subpopulations are provided.

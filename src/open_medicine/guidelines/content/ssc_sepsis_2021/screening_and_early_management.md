# Screening and Early Management of Sepsis — SCCM/ESICM 2021

## Screening and Performance Improvement

The SSC **recommends** using a performance improvement programme for sepsis, including screening for acutely ill, high-risk patients and standard operating procedures for treatment (Strong recommendation, Moderate quality of evidence).

- A meta-analysis of 50 observational studies demonstrated that performance improvement programmes are associated with significant mortality reduction (OR 0.66; 95% CI 0.61-0.72).

### Against qSOFA as a Single Screening Tool

The SSC **recommends against** using qSOFA compared to SIRS, NEWS, or MEWS as a **single screening tool** for sepsis or septic shock (Strong recommendation, Moderate quality of evidence).

- qSOFA is more specific but **less sensitive** than SIRS criteria for sepsis identification.
- qSOFA retains prognostic value (predicting poor outcomes), but should not be used alone for screening due to insufficient sensitivity.
- Hospital screening programmes should use validated tools (e.g., NEWS, MEWS, SIRS) as the primary screening instrument.

> **OpenMedicine Calculator:** `calculate_qsofa` -- available via MCP for automated qSOFA scoring. Note: per SSC 2021, qSOFA should NOT be used as a sole screening tool; it retains value as a bedside prognostic prompt.

## Blood Lactate Measurement

The SSC **suggests** measuring blood lactate in adults with suspected sepsis (Weak recommendation, Low quality of evidence).

- Lactate sensitivity: 66-83%; specificity: 80-85%.
- Clinically relevant lactate cutoffs: **1.6-2.5 mmol/L** (elevated) and **> 2 mmol/L** (septic shock criterion per Sepsis-3).
- Lactate elevation may reflect tissue hypoperfusion but can also result from aerobic glycolysis, catecholamine excess, or liver dysfunction.
- Lactate should not be used as a standalone diagnostic marker but as one component of clinical assessment.

## Initial Resuscitation

### Immediate Treatment Initiation

Treatment and resuscitation should **begin immediately** once sepsis or septic shock is recognised (Best Practice Statement).

- Resuscitation should not be delayed pending ICU admission.

### ICU Admission Timing

The SSC **suggests** admitting patients with sepsis or septic shock who require ICU-level care to the ICU **within 6 hours** (Weak recommendation, Low quality of evidence).

- Observational data demonstrate approximately **1.5% increased mortality per hour of delay** from the emergency department to ICU admission.

## Fluid Resuscitation

### Initial Crystalloid Volume

The SSC **suggests** administering **at least 30 mL/kg of IV crystalloid fluid within the first 3 hours** of resuscitation for patients with sepsis-induced hypoperfusion or septic shock (Weak recommendation, Low quality of evidence).

- Volume is calculated based on **ideal body weight**.
- This recommendation was downgraded from strong (2016) to weak (2021) due to the absence of prospective RCTs directly comparing different initial fluid volumes.
- Supporting evidence derives from the ProCESS, ProMISe, and ARISE trials, where average fluid volumes administered in the first 6 hours were approximately 30 mL/kg.

### Crystalloid Type

The SSC **suggests** using **balanced crystalloids (e.g., lactated Ringer's, Plasma-Lyte) over 0.9% normal saline** for resuscitation (Weak recommendation, Low quality of evidence).

- The SMART trial demonstrated lower 30-day mortality in the sepsis subgroup with balanced crystalloids (OR 0.90).
- Normal saline is associated with hyperchloraemic metabolic acidosis and potential renal vasoconstriction.

### Albumin

The SSC **suggests** using albumin in addition to crystalloids for patients who have received **large volumes of crystalloids** (Weak recommendation, Moderate quality of evidence).

- Albumin may help expand intravascular volume with less total fluid; however, there is no clear mortality benefit over crystalloids alone for initial resuscitation.
- Consider albumin when crystalloid volumes exceed 30 mL/kg and further volume is needed.

### Against Starches and Gelatins

- The SSC **recommends against** using **hydroxyethyl starches (HES)** for resuscitation in patients with sepsis or septic shock (Strong recommendation, Moderate quality of evidence). HES is associated with increased renal replacement therapy use and increased mortality.
- The SSC **suggests against** using **gelatins** for resuscitation (Weak recommendation, Moderate quality of evidence).

## Resuscitation Targets and Monitoring

### Lactate-Guided Resuscitation

The SSC **suggests** guiding resuscitation to **decrease serum lactate** in patients with elevated lactate levels (Weak recommendation, Low quality of evidence).

- Serial lactate measurements can help assess the adequacy of resuscitation.
- Normalisation of lactate is a favourable sign; persistent elevation suggests ongoing tissue hypoperfusion or other causes.
- Interpretation must be context-dependent; isolated lactate values should not drive resuscitation decisions without clinical correlation.

### Capillary Refill Time

The SSC **suggests** using **capillary refill time** to guide resuscitation as an adjunct to other measures of perfusion (Weak recommendation, Low quality of evidence).

- Informed by the ANDROMEDA-SHOCK trial, capillary refill time-guided resuscitation was non-inferior to lactate-guided resuscitation.
- Target: **capillary refill time < 3 seconds**.

### Dynamic Measures for Fluid Responsiveness

The SSC **suggests** using **dynamic measures** to guide fluid resuscitation over physical examination or static parameters alone (Weak recommendation, Very Low quality of evidence).

- Preferred methods include:
  - **Passive leg raise test** with stroke volume measurement
  - **Stroke volume variation (SVV)**
  - **Pulse pressure variation (PPV)**
  - **Echocardiography** (assessment of fluid responsiveness)
- Static parameters (CVP alone) should not be relied upon for fluid resuscitation decisions.

### Peripheral Vasopressor Initiation

The SSC **suggests** starting vasopressors **peripherally** rather than delaying initiation until central venous access is secured (Weak recommendation, Very Low quality of evidence).

- Evidence supports safety when infused through a proximal peripheral IV for **< 6 hours**.
- Peripheral initiation allows faster achievement of blood pressure goals.
- Transition to central venous access should occur as soon as logistically feasible.

## Resuscitation Decision Algorithm

```
Patient with suspected sepsis or septic shock
  --> Measure blood lactate immediately
  --> Begin IV crystalloid resuscitation (balanced preferred)
      --> Administer at least 30 mL/kg within first 3 hours
          --> Hypotensive despite initial bolus?
              --> Start norepinephrine (may use peripheral IV)
              --> Target MAP >= 65 mmHg
          --> Reassess using dynamic measures (passive leg raise, SVV, PPV)
              --> Fluid responsive? --> Continue careful fluid boluses
              --> Not fluid responsive? --> Stop further boluses, optimise vasopressors
  --> Monitor lactate serially
      --> Decreasing lactate? --> Continue current management
      --> Persistent elevation? --> Reassess perfusion, consider additional interventions
  --> Assess capillary refill time as adjunct
      --> Target < 3 seconds
  --> Admit to ICU within 6 hours if ICU-level care required
```

> **OpenMedicine Calculator:** `calculate_sofa` -- available via MCP for automated organ dysfunction scoring. A SOFA increase >= 2 points identifies sepsis per Sepsis-3 criteria.

> **OpenMedicine Calculator:** `calculate_apache2` -- available via MCP for ICU severity assessment using the first 24 hours of physiologic data.

## Limitations

- The 30 mL/kg initial fluid volume recommendation is based on observational and trial data where this volume was commonly administered, not on prospective RCTs comparing different volumes. The recommendation was downgraded from strong to weak in 2021.
- Lactate has imperfect sensitivity and specificity for tissue hypoperfusion; elevations can occur from other causes (liver dysfunction, catecholamines, aerobic glycolysis).
- Dynamic fluid responsiveness measures require specific equipment and expertise that may not be available in all settings.
- Most evidence supporting these recommendations comes from high-income country settings; adaptation may be needed for resource-limited environments.

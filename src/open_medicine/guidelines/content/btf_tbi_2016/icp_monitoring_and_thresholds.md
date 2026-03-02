# ICP Monitoring and Thresholds in Severe Traumatic Brain Injury — BTF 2016

## Intracranial Pressure Monitoring Indications

### Who Should Be Monitored

- Management of severe TBI patients using information from ICP monitoring is recommended to reduce in-hospital and 2-week post-injury mortality (Level IIB).
- ICP should be monitored in all salvageable patients with a severe TBI (GCS 3-8 after resuscitation) and an **abnormal CT scan** (Level IIB).
  - Abnormal CT scan: presence of hematomas, contusions, swelling, herniation, or compressed basal cisterns.
- ICP monitoring is indicated in patients with a severe TBI with a **normal CT scan** if two or more of the following features are noted at admission (Level III):
  - Age > 40 years
  - Unilateral or bilateral motor posturing
  - Systolic blood pressure (SBP) < 90 mmHg

> **OpenMedicine Calculator:** `calculate_gcs` -- available via MCP for automated GCS scoring to identify patients qualifying for ICP monitoring (GCS 3-8).

### Monitoring Technology

- A combination of ICP values and clinical and brain CT findings may be used to make management decisions (Level IIB).
- There is insufficient evidence to recommend one ICP monitoring technology (intraparenchymal vs. external ventricular drain) over another for improved outcomes. Both are acceptable.

## ICP Treatment Threshold

### 22 mmHg Threshold

- Treating intracranial pressure above **22 mmHg** is recommended because values above this level are associated with increased mortality (Level IIB).
  - This threshold replaces the previously used threshold of 20 mmHg from the 3rd Edition.
  - The 22 mmHg threshold is derived from a single-center retrospective study of 459 severe TBI patients treated over 12 years. The univariate association between ICP (average value for the whole monitoring period) and outcome was examined using sequential chi-squares testing ICP values in steps of 1 mmHg increments. At an ICP of 22 mmHg, the highest chi-square was obtained.

### Management Decision-Making

- A combination of ICP values, clinical examination findings, and brain CT findings should be used to make management decisions rather than ICP values alone (Level IIB).
- Decisions about the aggressiveness of ICP-lowering therapy should incorporate the entire clinical picture, not solely a single ICP number.

## Cerebral Perfusion Pressure (CPP) Monitoring

### CPP Target Range

- The recommended target CPP value for survival and favorable outcomes is between **60 and 70 mmHg** (Level IIB).
  - Whether 60 or 70 mmHg is the minimum optimal CPP threshold is unclear and may depend upon the patient's autoregulatory status.
  - This range was narrowed from 50-70 mmHg (3rd Edition) to 60-70 mmHg (4th Edition).

### Upper CPP Limit

- Avoiding aggressive attempts to maintain CPP above **70 mmHg** with fluids and pressors may be considered because of the risk of adult respiratory distress syndrome (ARDS) (Level III).

### CPP Calculation

- CPP = Mean Arterial Pressure (MAP) - ICP
- Accurate CPP calculation requires reliable ICP monitoring and continuous arterial blood pressure monitoring.

## Advanced Cerebral Monitoring

- Jugular venous oxygen saturation (SjO2) or brain tissue oxygen partial pressure (BtpO2) measurements may be used to supplement ICP/CPP-guided management, particularly when hyperventilation is employed (Level III).
- SjO2 values < 50% indicate cerebral ischemia and should prompt intervention.
- BtpO2 values < 15 mmHg are associated with poor outcome and indicate the need for treatment.

## ICP Monitoring and Treatment Algorithm

```
Patient with severe TBI (GCS 3-8 after resuscitation)
  --> Abnormal CT scan?
      --> YES: ICP monitoring indicated [Level IIB]
      --> NO: Age > 40 AND/OR motor posturing AND/OR SBP < 90 mmHg? (2 or more)
          --> YES: ICP monitoring indicated [Level III]
          --> NO: Clinical observation; consider monitoring if clinical deterioration
  --> ICP monitoring in place
      --> ICP > 22 mmHg?
          --> Initiate ICP-lowering therapy [Level IIB]
          --> Stepwise approach:
              --> 1. Head of bed elevation 30 degrees, midline head position
              --> 2. Sedation and analgesia
              --> 3. CSF drainage (if EVD in place)
              --> 4. Hyperosmolar therapy (mannitol or hypertonic saline)
              --> 5. Consider advanced interventions if refractory
      --> CPP < 60 mmHg?
          --> Optimize MAP with fluids and/or vasopressors
          --> Target CPP 60-70 mmHg [Level IIB]
          --> Avoid CPP > 70 mmHg (ARDS risk) [Level III]
      --> Use clinical examination + CT findings to supplement ICP data [Level IIB]
```

## Limitations

- The 22 mmHg ICP threshold is based on a single-center retrospective study, which limits generalizability. The previous 20 mmHg threshold was more widely validated in clinical practice.
- ICP monitoring practices vary widely across institutions. No randomized trial has demonstrated that ICP monitoring itself improves outcomes compared with clinical and imaging-based management alone. The BEST:TRIP trial (2012) found no outcome difference between ICP monitoring-based management and imaging/clinical examination-based management in a resource-limited setting.
- The optimal CPP range of 60-70 mmHg may not apply to all patients. Individual autoregulatory status significantly influences the ideal CPP threshold, and tools to assess autoregulation (e.g., pressure reactivity index, PRx) are not universally available.
- There is insufficient evidence to recommend a specific ICP monitoring technology (intraparenchymal vs. EVD) over another. EVDs have the advantage of allowing therapeutic CSF drainage but carry infection risk.

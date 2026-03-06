# Severity Assessment and Site-of-Care Decision in Community-Acquired Pneumonia — ATS/IDSA 2019

## Site-of-Care Decision: PSI vs CURB-65

The guideline recommends using a validated clinical prediction rule for determining the need for hospitalization in adults with CAP. The **Pneumonia Severity Index (PSI)** is preferred over the CURB-65 for guiding the initial site of treatment (Strong recommendation, Moderate quality of evidence).

- **If PSI Class I–II:** Outpatient treatment is generally appropriate.
- **If PSI Class III:** Consider short observation or outpatient with close follow-up.
- **If PSI Class IV–V:** Inpatient admission is recommended.

Clinical judgment should always supplement the PSI score, particularly regarding social circumstances, ability to maintain oral intake, and patient preferences.

> **OpenMedicine Calculator:** `calculate_curb65` — available via MCP for automated scoring.

> **OpenMedicine Calculator:** `calculate_psi_port` — available via MCP for automated scoring.

### Limitations of Severity Scores

- Neither PSI nor CURB-65 was designed to determine the level of inpatient care (ward vs ICU).
- PSI may under-triage young patients with severe disease due to heavy age-weighting.
- CURB-65 has less supporting evidence than PSI as a decision aid for initial site of treatment.
- Clinical judgment must be applied alongside any score — patients with unstable comorbidities, inability to tolerate oral medications, or inadequate home support may require admission regardless of score.

## IDSA/ATS Criteria for Severe CAP

For patients who are already hospitalized, the IDSA/ATS criteria for severe CAP are recommended to predict the need for intensive care (Strong recommendation, Low quality of evidence).

**Severe CAP is defined as the presence of one major criterion OR three or more minor criteria.**

### Major Criteria (either one sufficient for ICU admission)

| Criterion | Definition |
|-----------|------------|
| **Septic shock** | Hypotension requiring vasopressor support |
| **Respiratory failure** | Need for invasive mechanical ventilation |

### Minor Criteria (3 or more required)

| Criterion | Threshold |
|-----------|-----------|
| **Respiratory rate** | >= 30 breaths/min |
| **PaO2/FiO2 ratio** | <= 250 |
| **Multilobar infiltrates** | Radiographic involvement of more than one lobe |
| **Confusion/disorientation** | New onset |
| **Uremia** | BUN >= 20 mg/dL |
| **Leukopenia** | WBC < 4,000 cells/mm3 (due to infection alone, not chemotherapy) |
| **Thrombocytopenia** | Platelets < 100,000 cells/mm3 |
| **Hypothermia** | Core temperature < 36 degrees C |
| **Hypotension** | Requiring aggressive fluid resuscitation |

### ICU Admission Decision Algorithm

1. **Does the patient require vasopressors or mechanical ventilation?**
   - Yes: Direct ICU admission (major criterion met).
   - No: Proceed to step 2.
2. **Does the patient meet >= 3 minor criteria?**
   - Yes: Direct ICU admission or higher level of care (Strong recommendation, Low quality of evidence).
   - No: Admit to general medical ward; reassess if clinical deterioration occurs.

### Predictive Performance

- One major criterion OR >= 3 minor criteria: pooled sensitivity 84%, specificity 78% for predicting ICU admission.
- Without major criteria, >= 3 minor criteria alone: pooled sensitivity 56%, specificity 91%.

## Limitations

- The IDSA/ATS severity criteria were developed for research purposes and have been validated primarily in retrospective studies.
- These criteria should be used alongside clinical judgment, not as a sole determinant of disposition.
- Patients with rapidly evolving clinical status may not meet criteria at presentation but can deteriorate quickly; serial reassessment is essential.

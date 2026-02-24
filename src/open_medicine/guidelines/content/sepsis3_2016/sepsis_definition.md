# Sepsis Definition — SCCM/ESICM 2016

## The Sepsis-3 Consensus Definition

The Third International Consensus Definitions for Sepsis and Septic Shock (Sepsis-3) redefined sepsis to emphasize the dysregulated host response and the presence of organ dysfunction.

- **Sepsis** is defined as life-threatening organ dysfunction caused by a dysregulated host response to infection.

### Clinical Criteria for Organ Dysfunction (SOFA)

Organ dysfunction can be identified as an acute change in total SOFA (Sequential Organ Failure Assessment) score.

- A baseline SOFA score can be assumed to be zero in patients not known to have preexisting organ dysfunction.
- **Threshold for Sepsis:** An acute increase in the SOFA score of **≥ 2 points** consequent to the infection.
- This threshold of a SOFA score ≥ 2 is associated with an overall mortality risk of approximately 10% in a general hospital population with suspected infection.

Even patients presenting with modest dysfunction can deteriorate rapidly, emphasizing the seriousness of this condition.

> **OpenMedicine Calculator:** `calculate_sofa` — available via MCP for scoring organ failure across 6 systems (respiration, coagulation, liver, cardiovascular, CNS, renal).

## Septic Shock

Septic shock is a subset of sepsis in which underlying circulatory and cellular/metabolic abnormalities are profound enough to substantially increase mortality.

**Clinical Criteria for Septic Shock:**
Patients with sepsis who, despite adequate fluid resuscitation, require:
- Vasopressors to maintain a mean arterial pressure (MAP) ≥ 65 mmHg
- AND have a serum lactate level > 2 mmol/L (> 18 mg/dL)

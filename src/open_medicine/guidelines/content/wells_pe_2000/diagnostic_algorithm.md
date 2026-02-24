# Diagnostic Algorithm for Pulmonary Embolism — Wells PS et al. 2000

## Risk Stratification Models

The total Wells Score is used to categorize the likelihood of pulmonary embolism (PE), utilizing either a traditional three-tier model or a simplified two-tier model.

### Three-Tier Model (Historical)
- **Low probability:** Score < 2.0
- **Moderate probability:** Score 2.0 to 6.0
- **High probability:** Score > 6.0

### Two-Tier Model (Simplified & Recommended)
For clinical utility, particularly when paired with D-dimer testing, the two-tier model is widely recommended:
- **PE Unlikely:** Score ≤ 4.0 points
- **PE Likely:** Score > 4.0 points

## Actionable Diagnostic Algorithm

The categorization directs the subsequent diagnostic workup to safely and efficiently rule in or rule out PE.

### For "PE Unlikely" (Score ≤ 4.0)
- **Primary Action:** Obtain high-sensitivity D-dimer testing.
- **Negative D-dimer:** PE can be safely excluded. Further diagnostic imaging for PE is NOT indicated. Stop PE workup.
- **Positive D-dimer:** Proceed to definitive diagnostic imaging.

### For "PE Likely" (Score > 4.0)
- **Primary Action:** Proceed directly to definitive diagnostic imaging.
- **Contraindication for D-dimer:** D-dimer testing is **NOT recommended** because a negative result does not sufficiently reduce the probability to safely rule out PE.

### Definitive Diagnostic Imaging Choice
- **First-Line:** Computed Tomography Pulmonary Angiography (CTPA).
- **Alternative (V/Q Scan):** Use Ventilation/Perfusion (V/Q) scan if CTPA is contraindicated (e.g., severe renal impairment eGFR < 30, severe iodine contrast allergy, or pregnancy where radiation to breast tissue is a concern and CXR is normal).

> **OpenMedicine Calculator:** `calculate_wells_pe` — available via MCP for automated scoring and exact algorithm routing.

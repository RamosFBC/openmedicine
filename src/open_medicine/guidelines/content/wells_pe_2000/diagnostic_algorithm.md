# Diagnostic Algorithm for Pulmonary Embolism — Wells PS et al. 2000

## Risk Stratification Models

The total Wells Score is used to categorize the likelihood of pulmonary embolism (PE), utilizing either a traditional three-tier model or a simplified two-tier model.

### Three-Tier Model

Historically, the model stratified patients into three probability tiers:
- **Low probability:** Score < 2.0
- **Moderate probability:** Score 2.0 to 6.0
- **High probability:** Score > 6.0

### Two-Tier Model (Simplified)

For clinical utility, particularly when paired with D-dimer testing, the two-tier model is widely recommended:

- **PE Unlikely:** Score ≤ 4.0 points
- **PE Likely:** Score > 4.0 points

## Diagnostic Algorithm

The categorization directs the subsequent diagnostic workup to safely and efficiently rule in or rule out PE.

### For "PE Unlikely" (Score ≤ 4.0)

- **Action:** Consider high-sensitivity D-dimer testing.
- **Negative D-dimer:** PE can be safely excluded. Further diagnostic imaging for PE is generally not indicated and workup may be stopped.
- **Positive D-dimer:** Proceed to definitive diagnostic imaging, typically Computed Tomography Pulmonary Angiography (CTPA).

### For "PE Likely" (Score > 4.0)

- **Action:** Proceed directly to definitive diagnostic imaging (e.g., CTPA).
- D-dimer testing is **not recommended** for patients categorized as PE Likely, because a negative D-dimer result does not sufficiently reduce the probability of PE to safely rule it out.

> **OpenMedicine Calculator:** `calculate_wells_pe` — available via MCP for automated scoring and exact algorithm routing.

---
name: Bug Report
about: Report incorrect calculator output, crashes, or unexpected behavior
title: "[BUG] "
labels: bug
assignees: ''
---

## Description

A clear description of the bug.

## Calculator Affected

Which calculator or MCP tool is producing incorrect results? (e.g., `calculate_chadsvasc`, `execute_clinical_calculator`)

## Steps to Reproduce

```python
from open_medicine.mcp.calculators.xxx import calculate_xxx, XXXParams

params = XXXParams(...)
result = calculate_xxx(params)
print(result.value)  # Got: X, Expected: Y
```

## Expected vs Actual Behavior

- **Expected:** (What the correct output should be, with clinical reference if applicable)
- **Actual:** (What the tool returned)

## Clinical Reference (if applicable)

If reporting a clinical accuracy issue, please cite the source DOI, study, or reference.

## Environment

- open-medicine version:
- Python version:
- OS:

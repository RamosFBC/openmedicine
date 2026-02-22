## Description

Brief description of what this PR does.

## Clinical Evidence

- **Source DOI:** `10.xxxx/...`
- **Guideline/Study:** (Name and year)
- **Evidence Level:** (e.g., Validation Study, Clinical Practice Guideline)

## Checklist

- [ ] All existing tests pass (`uv run pytest -v`)
- [ ] New unit tests added covering boundary cases (min score, max score, edge cases)
- [ ] Hypothesis property-based bounds test added (if calculator)
- [ ] DOI citation is present and verified against original publication
- [ ] Clinical content validated against primary source
- [ ] Calculator registered in `src/open_medicine/mcp/registry.py` (if applicable)
- [ ] Guideline registered in `src/open_medicine/guidelines/registry.json` (if applicable)
- [ ] Code follows existing patterns (`ClinicalResult`, Pydantic models)

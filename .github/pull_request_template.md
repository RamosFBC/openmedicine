## Description

Brief description of what this PR does.

## Clinical Evidence

- **Source DOI:** `10.xxxx/...`
- **Source study or reference:** (Name and year)
- **Evidence Level:** (e.g., Validation Study, Clinical Practice Guideline)

## Checklist

- [ ] All existing tests pass (`uv run python -m pytest -v`)
- [ ] New unit tests added covering boundary cases, representative cases, and edge cases
- [ ] DOI citation is present and verified against the original source when available
- [ ] Calculator registered in `src/open_medicine/mcp/registry.py`
- [ ] Calculator execution is deterministic and performs no network calls
- [ ] Code follows existing patterns (`ClinicalResult`, Pydantic models)

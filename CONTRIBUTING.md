# Contributing to Open Medicine

Thank you for considering contributing to Open Medicine! This project provides evidence-based clinical reasoning tools for AI agents. Because the output of these tools may influence clinical decisions, we hold contributions to a higher standard than typical software projects.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/RamosFBC/openmedicine.git
cd openmedicine

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync --extra test

# Run the test suite
uv run pytest -v
```

All 2350+ tests must pass before submitting a PR.

## Adding a New Calculator

Every calculator follows the same pattern. Use any existing calculator as a reference (e.g., [`chadsvasc.py`](src/open_medicine/mcp/calculators/chadsvasc.py)).

### Required Files

1. **Calculator module** — `src/open_medicine/mcp/calculators/<name>.py`
   - Pydantic `BaseModel` for input parameters with `Field` descriptions
   - Pure function returning a `ClinicalResult` with `Evidence`

2. **Unit tests** — `tests/test_<name>.py`
   - Boundary cases: minimum score, maximum score, edge cases
   - Verify `evidence.source_doi` is present and correct

3. **Property-based bounds test** — add to `tests/comparative_validation/test_bounds.py`
   - Hypothesis test ensuring the score stays within valid range across random inputs

4. **Registry entry** — add to `src/open_medicine/mcp/registry.py`
   - Import and register the calculator so it's discoverable via MCP

### Clinical Accuracy Requirements

- **DOI citation required** — every calculator must reference a specific published study or guideline
- **Evidence level** — specify the evidence level (e.g., "Validation Study", "Clinical Practice Guideline")
- **LOINC/FHIR code** — include the appropriate LOINC code for interoperability when available

## Adding a New Guideline

Guidelines live in the `src/open_medicine/guidelines/` directory.

1. **Register** — add an entry to `registry.json` with `id`, `title`, `doi`, `topics[]`, `sections[]`
2. **Content** — create markdown files in `content/<guideline_id>/<section>.md`
3. **Validate** — cross-reference every clinical claim against the original publication

## Pull Request Checklist

Before submitting, ensure:

- [ ] All existing tests pass (`uv run pytest -v`)
- [ ] New calculator has unit tests covering min/max/edge cases
- [ ] New calculator has a Hypothesis bounds test
- [ ] DOI citation is present and correct
- [ ] Clinical content has been validated against the primary source
- [ ] Registry entry added (for calculators)
- [ ] Code follows existing patterns (Pydantic models, ClinicalResult output)

## Code Style

- Type hints on all function signatures
- Pydantic `Field(...)` with descriptive `description` strings for all model fields
- `ClinicalResult` as the return type for all calculators
- Docstrings referencing the source publication

## Questions?

Open an issue with the "question" label or start a discussion.

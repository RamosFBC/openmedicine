import ast
from pathlib import Path


CALCULATOR_DIR = Path("src/open_medicine/mcp/calculators")


def test_none_valued_clinical_results_declare_failure_contract():
    offenders = []

    for module in sorted(CALCULATOR_DIR.glob("*.py")):
        tree = ast.parse(module.read_text(), filename=str(module))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = node.func
            is_clinical_result = (
                isinstance(function, ast.Name) and function.id == "ClinicalResult"
            ) or (
                isinstance(function, ast.Attribute)
                and function.attr == "ClinicalResult"
            )
            if not is_clinical_result:
                continue

            keywords = {keyword.arg: keyword.value for keyword in node.keywords}
            value = keywords.get("value")
            if not (isinstance(value, ast.Constant) and value.value is None):
                continue

            missing = [name for name in ("status", "errors") if name not in keywords]
            if missing:
                offenders.append(
                    f"{module}:{node.lineno}: missing {', '.join(missing)}"
                )

    assert not offenders, (
        "ClinicalResult(value=None) must declare explicit status and errors:\n"
        + "\n".join(offenders)
    )

from src.sandbox.runner import run_pytest
from src.validator.validator import parse_junit_xml
from src.validator.validator import validate

repo_path = "tests/fixtures"
result = run_pytest(
    ".",
    "tests/fixtures/test_buggy_math.py"
)
# print(
# parse_junit_xml(result.junit_xml, result.output))

# print(result)
# print("\n--- OUTPUT ---")
# print(result.output)

validation = validate(
    repo_path,
    "test_buggy_math.py",
    ".",
)

print(validation)
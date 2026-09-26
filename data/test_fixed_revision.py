from src.sandbox.workspace import disposable_repo_copy
from src.sandbox.runner import run_test

with disposable_repo_copy("data/requests") as temp_path:
    test_path = temp_path / "tests/generated_test.py"
    test_path.parent.mkdir(parents=True, exist_ok=True)

    test_path.write_text(
        open("data/day9_generated_test.py").read()
    )

    result = run_test(
        str(temp_path),
        "tests/generated_test.py"
    )

    print(result)
from pathlib import Path  # noqa: F401

from src.sandbox.runner import run_pytest
from src.sandbox.workspace import disposable_repo_copy
from src.test_generator.schemas import GeneratedTest


def run_generated_test(repo_path: str, generated_test: GeneratedTest):
    print("\nGENERATED TEST CODE")
    print("-------------------")
    print(generated_test.test_code)

    test_path = Path(repo_path) / "tests/generated_test.py"

    test_path.parent.mkdir(parents=True, exist_ok=True)

    with open(test_path, "w") as file:
        file.write(generated_test.test_code)

    with disposable_repo_copy(repo_path) as temp_path:
        test_path = temp_path / "tests/generated_test.py"

        test_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(test_path, "w") as file:
            file.write(generated_test.test_code)

        return run_pytest(
            str(temp_path),
            "tests/generated_test.py"
        )


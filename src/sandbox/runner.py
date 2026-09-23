import os 
import docker
from dataclasses import dataclass

@dataclass
class SandboxResult:
    passed: bool
    exit_code: int
    output: str

client = docker.from_env()

repo_path = os.path.abspath("data/requests")

def run_test(repo_path, test_path):
    container = client.containers.create(
        "python:3.12-slim",
        ["sh", "-c", f"pip install pytest requests -q && pytest {test_path}"],
        volumes={repo_path: {"bind": "/repo", "mode": "ro"}},
        
    )


    container.start()

    result = container.wait()
    output = container.logs().decode()

    container.remove()

    exit_code = result["StatusCode"]

    sandbox_result = SandboxResult(
        passed=exit_code==0,
        exit_code=exit_code,
        output=output
    )

    return sandbox_result

result = run_test(
    repo_path,
    "/repo/tests/test_hooks.py"
)

print(result)


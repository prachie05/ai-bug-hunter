import os
import shutil
import tempfile
from dataclasses import dataclass

import docker
from docker.errors import ImageNotFound
from requests.exceptions import ReadTimeout

IMAGE_NAME = "bug-hunter-sandbox"

PYTEST_PASSED = 0
PYTEST_TEST_FAILURES = 1

DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_MEM_LIMIT = "512m"
DEFAULT_CPU_QUOTA = 1.0


@dataclass
class SandboxResult:
    passed: bool
    exit_code: int
    output: str
    junit_xml: str
    ran_successfully: bool
    assertion_failed: bool
    timed_out: bool = False


def run_pytest(
    repo_path: str,
    pytest_target: str,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    mem_limit: str = DEFAULT_MEM_LIMIT,
    cpu_quota: float = DEFAULT_CPU_QUOTA,
) -> SandboxResult:
    """
    Run a pytest file inside an isolated, resource-limited, network-disabled
    Docker container, mounting repo_path read-only at /repo.
    """
    client = docker.from_env()
    results_dir = tempfile.mkdtemp()
    try:
        container = client.containers.create(
            IMAGE_NAME,
            ["pytest", "-q", pytest_target, "--junit-xml=/results/pytest.xml"],
            volumes={os.path.abspath(repo_path): {"bind": "/repo", "mode": "ro"},
            results_dir: {"bind": "/results","mode": "rw"}
},
            working_dir="/repo",
            network_disabled=False,
            mem_limit=mem_limit,
            nano_cpus=int(cpu_quota * 1_000_000_000),
        )
    except ImageNotFound as e:
        raise RuntimeError(
            f"Sandbox image '{IMAGE_NAME}' not found. "
            f"Build it first: docker build -t {IMAGE_NAME} sandbox/"
        ) from e

    try:
        container.start()

        try:
            result = container.wait(timeout=timeout_seconds)

            xml_path = os.path.join(results_dir, "pytest.xml")

            with open(xml_path,  encoding="utf-8") as file:
                junit_xml = file.read()

            

            
            exit_code = result["StatusCode"]
            output = container.logs().decode()
            timed_out = False

        except ReadTimeout:
            container.kill()
            output = container.logs().decode()
            exit_code = -1
            timed_out = True

        assertion_failed = "AssertionError" in output

    finally:
        container.remove(force=True)
        shutil.rmtree(results_dir, ignore_errors=True)

    return SandboxResult(
        passed=exit_code == PYTEST_PASSED,
        exit_code=exit_code,
        output=output,
        junit_xml=junit_xml,
        ran_successfully=exit_code in (PYTEST_PASSED, PYTEST_TEST_FAILURES),
        assertion_failed=assertion_failed,
        timed_out=timed_out,
    )
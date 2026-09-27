import xml.etree.ElementTree as ET

from src.sandbox.runner import SandboxResult, run_pytest
from src.validator.schemas import Status, TestResult, ValidationResult


def interpret_test_result(result: SandboxResult) -> TestResult:
    if result.timed_out or not result.ran_successfully:
        return TestResult(
            status=Status.INCONCLUSIVE,
            failed_tests=[],
            assertion=None,
            output=result.output,
        )

    return parse_junit_xml(result.junit_xml, result.output)


def parse_junit_xml(junit_xml: str, output:str):
    root = ET.fromstring(junit_xml)

    failed_tests = []
    assertion = None

    for testcase in root.iter("testcase"):
        failure = testcase.find("failure")

        if failure is not None:
            test_id = f"{testcase.attrib['classname']}::{testcase.attrib['name']}"
            failed_tests.append(test_id)
            assertion = failure.attrib.get("message")

    return TestResult(
        status=Status.FAIL if failed_tests else Status.PASS,
        failed_tests=failed_tests,
        assertion=assertion,
        output=output,
    )


def validate(repo_path: str, regression_test_path:str,existing_suite_path: str,)->ValidationResult:
    regression_result = run_pytest(repo_path, regression_test_path)
    existing_suite_result = run_pytest(repo_path, existing_suite_path, timeout_seconds=240)

    regression_test = interpret_test_result(regression_result)

    existing_suite = interpret_test_result(existing_suite_result)
    
    if (
    regression_test.status == Status.INCONCLUSIVE
    or existing_suite.status == Status.INCONCLUSIVE):
        overall_status = Status.INCONCLUSIVE

    elif (
        regression_test.status == Status.FAIL
        or existing_suite.status == Status.FAIL
    ):
        overall_status = Status.FAIL

    else:
        overall_status = Status.PASS

    return ValidationResult(
    overall_status=overall_status,
    regression_test=regression_test,
    existing_suite=existing_suite,
)
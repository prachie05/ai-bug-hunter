from enum import Enum

from pydantic import BaseModel


class Status(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"


class TestResult(BaseModel):
    status: Status
    failed_tests: list[str]
    assertion: str | None
    output: str


class ValidationResult(BaseModel):
    overall_status: Status
    regression_test: TestResult
    existing_suite: TestResult
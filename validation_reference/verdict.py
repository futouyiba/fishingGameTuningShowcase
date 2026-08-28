from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class ValidationExecutionStatus(str, Enum):
    EXECUTED = "EXECUTED"
    FIXTURE_INVALID = "FIXTURE_INVALID"


@dataclass(frozen=True)
class CheckResult:
    assertion_id: str
    passed: bool
    failure_class: str | None = None


@dataclass(frozen=True)
class ValidationVerdict:
    execution_status: ValidationExecutionStatus
    structural_pass: bool | None
    outcome_pass: bool | None
    overall_pass: bool
    violated_invariants: tuple[str, ...]
    failure_class: tuple[str, ...]
    fixture_error: str | None = None


def fixture_invalid(reason: str) -> ValidationVerdict:
    """Return a non-model verdict for an incompatible or malformed fixture."""
    return ValidationVerdict(
        execution_status=ValidationExecutionStatus.FIXTURE_INVALID,
        structural_pass=None,
        outcome_pass=None,
        overall_pass=False,
        violated_invariants=(),
        failure_class=(),
        fixture_error=reason,
    )


def evaluate_validation(
    structural_checks: Iterable[CheckResult],
    outcome_checks: Iterable[CheckResult],
) -> ValidationVerdict:
    """Combine structural and outcome gates without cross-gate compensation.

    A fixture that executed successfully passes only when every required
    structural assertion and every required outcome assertion passes.
    Structural failures cannot be repaired by matching a downstream KPI, and
    outcome failures cannot be hidden by a clean dependency shape.
    """
    structural = tuple(structural_checks)
    outcome = tuple(outcome_checks)

    structural_pass = all(check.passed for check in structural)
    outcome_pass = all(check.passed for check in outcome)

    failures = structural + outcome
    violated = tuple(check.assertion_id for check in failures if not check.passed)
    classes = tuple(
        dict.fromkeys(
            check.failure_class
            for check in failures
            if not check.passed and check.failure_class is not None
        )
    )

    return ValidationVerdict(
        execution_status=ValidationExecutionStatus.EXECUTED,
        structural_pass=structural_pass,
        outcome_pass=outcome_pass,
        overall_pass=structural_pass and outcome_pass,
        violated_invariants=violated,
        failure_class=classes,
    )

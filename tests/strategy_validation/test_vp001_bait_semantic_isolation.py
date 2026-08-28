from __future__ import annotations

from validation_reference import (
    BoundaryAssertionKind,
    BoundarySnapshot,
    CheckResult,
    ValidationExecutionStatus,
    evaluate_boundary_assertion,
    evaluate_validation,
)


def _boundary(boundary_id: str, digest: str) -> BoundarySnapshot:
    return BoundarySnapshot(boundary_id=boundary_id, semantic_digest=digest)


def _validate_vp001(*, opportunity_digest: str = "opp:v1"):
    baseline = {
        "PB-SPATIAL": _boundary("PB-SPATIAL", "spatial:same"),
        "PB-INTERACTION": _boundary("PB-INTERACTION", "interaction:bait-a"),
        "PB-OPPORTUNITY": _boundary("PB-OPPORTUNITY", "opp:v1"),
        "PB-CANDIDATE": _boundary("PB-CANDIDATE", "candidate:bait-a"),
    }
    counterfactual = {
        "PB-SPATIAL": _boundary("PB-SPATIAL", "spatial:same"),
        "PB-INTERACTION": _boundary("PB-INTERACTION", "interaction:bait-b"),
        "PB-OPPORTUNITY": _boundary("PB-OPPORTUNITY", opportunity_digest),
        "PB-CANDIDATE": _boundary("PB-CANDIDATE", "candidate:bait-b"),
    }

    boundary_checks = [
        evaluate_boundary_assertion(
            assertion_id="VP001.SPATIAL_UNCHANGED",
            kind=BoundaryAssertionKind.FORBID_DELTA_PATH,
            baseline=baseline["PB-SPATIAL"],
            counterfactual=counterfactual["PB-SPATIAL"],
            failure_class="BASIS_LEAK",
        ),
        evaluate_boundary_assertion(
            assertion_id="VP001.INTERACTION_DELTA_REQUIRED",
            kind=BoundaryAssertionKind.REQUIRE_DELTA_PATH,
            baseline=baseline["PB-INTERACTION"],
            counterfactual=counterfactual["PB-INTERACTION"],
            failure_class="MECHANISM_INVALID",
        ),
        evaluate_boundary_assertion(
            assertion_id="VP001.OPPORTUNITY_UNCHANGED",
            kind=BoundaryAssertionKind.FORBID_DELTA_PATH,
            baseline=baseline["PB-OPPORTUNITY"],
            counterfactual=counterfactual["PB-OPPORTUNITY"],
            failure_class="BASIS_LEAK",
        ),
        evaluate_boundary_assertion(
            assertion_id="VP001.CANDIDATE_DELTA_REQUIRED",
            kind=BoundaryAssertionKind.REQUIRE_DELTA_PATH,
            baseline=baseline["PB-CANDIDATE"],
            counterfactual=counterfactual["PB-CANDIDATE"],
            failure_class="MECHANISM_INVALID",
        ),
    ]
    structural_checks = [
        CheckResult(check.assertion_id, check.passed, check.failure_class)
        for check in boundary_checks
    ]
    outcome_checks = [
        CheckResult("VP001.B1_ALLOWED", True),
        CheckResult("VP001.B2_EXPECTED", True),
        CheckResult("VP001.B3_FORBIDDEN", opportunity_digest == "opp:v1", "BASIS_LEAK"),
        CheckResult("VP001.B4_STABLE", True),
    ]
    return evaluate_validation(structural_checks, outcome_checks)


def test_vp001_bait_semantic_change_isolated_to_interaction_and_candidate() -> None:
    verdict = _validate_vp001()

    assert verdict.execution_status is ValidationExecutionStatus.EXECUTED
    assert verdict.structural_pass is True
    assert verdict.outcome_pass is True
    assert verdict.overall_pass is True


def test_vp001_bait_to_opportunity_productivity_negative_control_fails() -> None:
    verdict = _validate_vp001(opportunity_digest="opp:productivity-x1.5")

    assert verdict.execution_status is ValidationExecutionStatus.EXECUTED
    assert verdict.structural_pass is False
    assert verdict.outcome_pass is False
    assert verdict.overall_pass is False
    assert "VP001.OPPORTUNITY_UNCHANGED" in verdict.violated_invariants
    assert "VP001.B3_FORBIDDEN" in verdict.violated_invariants
    assert "BASIS_LEAK" in verdict.failure_class


def test_boundary_assertion_equal_and_require_delta_are_not_interchangeable() -> None:
    baseline = _boundary("PB-INTERACTION", "same")
    same = _boundary("PB-INTERACTION", "same")
    changed = _boundary("PB-INTERACTION", "changed")

    assert evaluate_boundary_assertion(
        assertion_id="equal",
        kind=BoundaryAssertionKind.EQUAL,
        baseline=baseline,
        counterfactual=same,
        failure_class="MECHANISM_INVALID",
    ).passed
    assert evaluate_boundary_assertion(
        assertion_id="delta",
        kind=BoundaryAssertionKind.REQUIRE_DELTA_PATH,
        baseline=baseline,
        counterfactual=changed,
        failure_class="MECHANISM_INVALID",
    ).passed

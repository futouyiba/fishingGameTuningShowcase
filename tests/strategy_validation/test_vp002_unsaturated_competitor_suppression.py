from __future__ import annotations

from candidate_weight_reference.kernel import calculate_true_pool
from validation_reference import (
    CheckResult,
    ValidationExecutionStatus,
    evaluate_validation,
    fixture_invalid,
)

FIXTURE_ID = "VP-002"
PAN_CAPACITY = 1000.0
OPPORTUNITY_RATE = 1.0
BASELINE_WEIGHTS = {"A": 100.0, "B": 50.0}
SUPPRESSED_WEIGHTS = {"A": 100.0, "B": 10.0}
HIDDEN_TARGET_BOOST_WEIGHTS = {"A": 110.0, "B": 10.0}


def _run(weights: dict[str, float], *, pan_capacity: float = PAN_CAPACITY, opportunity_rate: float = OPPORTUNITY_RATE):
    return calculate_true_pool(
        weights,
        pan_capacity=pan_capacity,
        opportunity_rate_per_sec=opportunity_rate,
    )


def _validate_pair(
    baseline_weights: dict[str, float],
    counterfactual_weights: dict[str, float],
    *,
    baseline_pan_capacity: float = PAN_CAPACITY,
    counterfactual_pan_capacity: float = PAN_CAPACITY,
    baseline_opportunity_rate: float = OPPORTUNITY_RATE,
    counterfactual_opportunity_rate: float = OPPORTUNITY_RATE,
):
    if set(baseline_weights) != set(counterfactual_weights):
        return fixture_invalid(f"{FIXTURE_ID}: candidate set changed")
    if baseline_pan_capacity != counterfactual_pan_capacity:
        return fixture_invalid(f"{FIXTURE_ID}: panCapacity must be held constant")
    if baseline_opportunity_rate != counterfactual_opportunity_rate:
        return fixture_invalid(f"{FIXTURE_ID}: Opportunity cadence must be held constant")

    baseline = _run(
        baseline_weights,
        pan_capacity=baseline_pan_capacity,
        opportunity_rate=baseline_opportunity_rate,
    )
    counterfactual = _run(
        counterfactual_weights,
        pan_capacity=counterfactual_pan_capacity,
        opportunity_rate=counterfactual_opportunity_rate,
    )

    structural_checks = [
        CheckResult(
            "VP002.TARGET_NATIVE_WEIGHT_UNCHANGED",
            counterfactual.species["A"].weight == baseline.species["A"].weight,
            "BASIS_LEAK",
        ),
        CheckResult(
            "VP002.COMPETITOR_NATIVE_WEIGHT_SUPPRESSED",
            counterfactual.species["B"].weight < baseline.species["B"].weight,
            "MECHANISM_INVALID",
        ),
        CheckResult(
            "VP002.REMAIN_UNSATURATED",
            not baseline.saturated and not counterfactual.saturated,
            "FIXTURE_REGIME_MISMATCH",
        ),
    ]
    outcome_checks = [
        CheckResult(
            "VP002.TARGET_ABSOLUTE_PER_OPPORTUNITY_UNCHANGED",
            counterfactual.species["A"].probability_per_opportunity
            == baseline.species["A"].probability_per_opportunity,
            "BASIS_LEAK",
        ),
        CheckResult(
            "VP002.TARGET_ROLL_TIME_UNCHANGED",
            counterfactual.species["A"].roll_time_seconds
            == baseline.species["A"].roll_time_seconds,
            "BASIS_LEAK",
        ),
        CheckResult(
            "VP002.TARGET_PURITY_INCREASES",
            counterfactual.species["A"].conditional_purity
            > baseline.species["A"].conditional_purity,
            "METRIC_ENVELOPE_FAIL",
        ),
        CheckResult(
            "VP002.ANY_SPAWN_PROBABILITY_DECREASES",
            counterfactual.spawn_probability_per_opportunity
            < baseline.spawn_probability_per_opportunity,
            "METRIC_ENVELOPE_FAIL",
        ),
        CheckResult(
            "VP002.COMPETITOR_ABSOLUTE_RATE_DECREASES",
            counterfactual.species["B"].probability_per_opportunity
            < baseline.species["B"].probability_per_opportunity,
            "METRIC_ENVELOPE_FAIL",
        ),
    ]
    return evaluate_validation(structural_checks, outcome_checks)


def test_vp002_positive_control_passes_structural_and_outcome_gates() -> None:
    verdict = _validate_pair(BASELINE_WEIGHTS, SUPPRESSED_WEIGHTS)

    assert verdict.execution_status is ValidationExecutionStatus.EXECUTED
    assert verdict.structural_pass is True
    assert verdict.outcome_pass is True
    assert verdict.overall_pass is True
    assert verdict.violated_invariants == ()
    assert verdict.failure_class == ()


def test_vp002_positive_control_matches_current_unsaturated_invariant() -> None:
    baseline = _run(BASELINE_WEIGHTS)
    counterfactual = _run(SUPPRESSED_WEIGHTS)

    assert baseline.species["A"].probability_per_opportunity == 0.1
    assert counterfactual.species["A"].probability_per_opportunity == 0.1
    assert baseline.species["A"].roll_time_seconds == 10.0
    assert counterfactual.species["A"].roll_time_seconds == 10.0
    assert counterfactual.species["A"].conditional_purity > baseline.species["A"].conditional_purity
    assert counterfactual.spawn_probability_per_opportunity < baseline.spawn_probability_per_opportunity


def test_vp002_hidden_target_boost_negative_control_fails_even_if_purity_improves() -> None:
    baseline = _run(BASELINE_WEIGHTS)
    injected = _run(HIDDEN_TARGET_BOOST_WEIGHTS)
    verdict = _validate_pair(BASELINE_WEIGHTS, HIDDEN_TARGET_BOOST_WEIGHTS)

    # The bad implementation can still make the player-facing purity KPI look better.
    assert injected.species["A"].conditional_purity > baseline.species["A"].conditional_purity

    # But it illegally changes the target Native mass and absolute roll rate.
    assert verdict.execution_status is ValidationExecutionStatus.EXECUTED
    assert verdict.structural_pass is False
    assert verdict.outcome_pass is False
    assert verdict.overall_pass is False
    assert "VP002.TARGET_NATIVE_WEIGHT_UNCHANGED" in verdict.violated_invariants
    assert "VP002.TARGET_ABSOLUTE_PER_OPPORTUNITY_UNCHANGED" in verdict.violated_invariants
    assert "BASIS_LEAK" in verdict.failure_class


def test_vp002_incompatible_counterfactual_is_fixture_invalid_not_model_failure() -> None:
    verdict = _validate_pair(
        BASELINE_WEIGHTS,
        SUPPRESSED_WEIGHTS,
        counterfactual_opportunity_rate=2.0,
    )

    assert verdict.execution_status is ValidationExecutionStatus.FIXTURE_INVALID
    assert verdict.structural_pass is None
    assert verdict.outcome_pass is None
    assert verdict.overall_pass is False
    assert verdict.failure_class == ()
    assert verdict.fixture_error is not None

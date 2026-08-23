from __future__ import annotations

import pytest

from candidate_weight_reference import calculate_true_pool


def test_unsaturated_competitor_suppression_does_not_change_target_absolute_rate() -> None:
    before = calculate_true_pool({"A": 100, "B": 50}, pan_capacity=1000, opportunity_rate_per_sec=1)
    after = calculate_true_pool({"A": 100, "B": 10}, pan_capacity=1000, opportunity_rate_per_sec=1)

    assert before.species["A"].roll_time_seconds == pytest.approx(10.0)
    assert after.species["A"].roll_time_seconds == pytest.approx(10.0)
    assert after.species["A"].conditional_purity > before.species["A"].conditional_purity
    assert after.any_spawn_roll_time_seconds > before.any_spawn_roll_time_seconds


def test_saturated_uniform_weight_scale_preserves_probabilities_and_times() -> None:
    before = calculate_true_pool({"A": 60, "B": 60}, pan_capacity=100, opportunity_rate_per_sec=1)
    after = calculate_true_pool({"A": 120, "B": 120}, pan_capacity=100, opportunity_rate_per_sec=1)

    assert before.saturated is True
    assert after.saturated is True
    assert before.spawn_probability_per_opportunity == pytest.approx(1.0)
    assert after.spawn_probability_per_opportunity == pytest.approx(1.0)
    assert before.species["A"].conditional_purity == pytest.approx(0.5)
    assert after.species["A"].conditional_purity == pytest.approx(0.5)
    assert before.species["A"].roll_time_seconds == pytest.approx(2.0)
    assert after.species["A"].roll_time_seconds == pytest.approx(2.0)


def test_runtime_integer_scale_of_weights_and_pan_capacity_is_invariant() -> None:
    before = calculate_true_pool({"A": 100, "B": 50}, pan_capacity=1000, opportunity_rate_per_sec=2)
    after = calculate_true_pool(
        {"A": 1000, "B": 500}, pan_capacity=10000, opportunity_rate_per_sec=2
    )

    assert after.spawn_probability_per_opportunity == pytest.approx(
        before.spawn_probability_per_opportunity
    )
    assert after.species["A"].probability_per_opportunity == pytest.approx(
        before.species["A"].probability_per_opportunity
    )
    assert after.species["A"].roll_time_seconds == pytest.approx(
        before.species["A"].roll_time_seconds
    )

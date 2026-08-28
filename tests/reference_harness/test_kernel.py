"""TrueRoll kernel blockers rebuilt from Fixture Catalog A/B pinned goldens.

Weights flow through the admitted multiplicative Candidate
specialization (``Combine_prod(L, C) = localSpeciesIntensity x
captureRetention``; the canonical ``Combine`` operator stays upstream
authority) before reaching the shared fixed-pan kernel, so every golden
below is end-to-end for that specialization's numeric surface.
"""

from __future__ import annotations

import pytest

from candidate_weight_reference import (
    CandidateWeightInputs,
    TruePoolResult,
    calculate_true_pool,
    resolve_multiplicative_candidate_weights,
)


def _pool(
    rows: dict[str, tuple[float, float]],
    pan_capacity: float,
    opportunity_rate_per_sec: float = 1.0,
) -> TruePoolResult:
    weights = resolve_multiplicative_candidate_weights(
        {
            species_id: CandidateWeightInputs(
                local_species_intensity=intensity,
                capture_retention=retention,
            )
            for species_id, (intensity, retention) in rows.items()
        }
    )
    return calculate_true_pool(
        weights,
        pan_capacity=pan_capacity,
        opportunity_rate_per_sec=opportunity_rate_per_sec,
    )


FIXTURE_A_ROWS = {"A": (100.0, 1.0), "B": (50.0, 1.0)}
FIXTURE_B_ROWS = {"A": (60.0, 1.0), "B": (60.0, 1.0)}


def test_fixture_a_baseline_unsaturated_micro() -> None:
    pool = _pool(FIXTURE_A_ROWS, pan_capacity=1000)

    assert pool.total_weight == 100.0 + 50.0
    assert pool.saturated is False
    assert pool.spawn_probability_per_opportunity == pytest.approx(0.15)
    assert pool.species["A"].weight == 100.0
    assert pool.species["B"].weight == 50.0
    assert pool.species["A"].probability_per_opportunity == pytest.approx(0.10)
    assert pool.species["B"].probability_per_opportunity == pytest.approx(0.05)
    assert pool.species["A"].conditional_purity == pytest.approx(0.6666667)
    assert pool.species["A"].roll_time_seconds == pytest.approx(10.0)
    assert pool.species["B"].roll_time_seconds == pytest.approx(20.0)
    assert pool.any_spawn_roll_time_seconds == pytest.approx(6.6666667)


def test_a1_opportunity_rate_doubles_times_only() -> None:
    before = _pool(FIXTURE_A_ROWS, pan_capacity=1000, opportunity_rate_per_sec=1)
    after = _pool(FIXTURE_A_ROWS, pan_capacity=1000, opportunity_rate_per_sec=2)

    assert after.any_spawn_roll_time_seconds == pytest.approx(
        before.any_spawn_roll_time_seconds / 2
    )
    assert after.species["A"].roll_time_seconds == pytest.approx(
        before.species["A"].roll_time_seconds / 2
    )
    assert after.species["B"].roll_time_seconds == pytest.approx(
        before.species["B"].roll_time_seconds / 2
    )
    assert after.total_weight == before.total_weight
    assert after.species["A"].conditional_purity == pytest.approx(
        before.species["A"].conditional_purity
    )
    assert after.spawn_probability_per_opportunity == pytest.approx(
        before.spawn_probability_per_opportunity
    )


def test_cr03_a2_competitor_suppression_purifies_without_target_lift() -> None:
    """CR-03: only competitor W drops; target absolute per-Opportunity rate is fixed."""
    before = _pool(FIXTURE_A_ROWS, pan_capacity=1000)
    after = _pool({"A": (100.0, 1.0), "B": (50.0, 0.2)}, pan_capacity=1000)

    assert after.species["B"].weight == 10.0
    assert after.total_weight == 110.0
    assert after.species["A"].probability_per_opportunity == pytest.approx(
        before.species["A"].probability_per_opportunity
    )
    assert after.species["A"].roll_time_seconds == pytest.approx(10.0)
    assert after.species["B"].roll_time_seconds == pytest.approx(100.0)
    assert after.species["A"].conditional_purity == pytest.approx(0.9090909)
    assert after.any_spawn_roll_time_seconds == pytest.approx(9.090909)
    assert after.any_spawn_roll_time_seconds > before.any_spawn_roll_time_seconds


def test_cr04_a3_target_supply_lift_raises_target_absolute_rate() -> None:
    """CR-04: raising target localSpeciesIntensity lifts target absolute rate."""
    before = _pool(FIXTURE_A_ROWS, pan_capacity=1000)
    after = _pool({"A": (150.0, 1.0), "B": (50.0, 1.0)}, pan_capacity=1000)

    assert after.species["A"].weight == 150.0
    assert after.total_weight == 200.0
    assert after.species["A"].probability_per_opportunity == pytest.approx(0.15)
    assert after.species["A"].roll_time_seconds == pytest.approx(6.6666667)
    assert after.species["B"].probability_per_opportunity == pytest.approx(
        before.species["B"].probability_per_opportunity
    )
    assert after.species["B"].roll_time_seconds == pytest.approx(20.0)
    assert after.species["A"].conditional_purity == pytest.approx(0.75)
    assert after.any_spawn_roll_time_seconds == pytest.approx(5.0)


def test_cr03_cr04_contrast_suppression_is_not_supply_lift() -> None:
    baseline = _pool(FIXTURE_A_ROWS, pan_capacity=1000)
    suppressed = _pool({"A": (100.0, 1.0), "B": (50.0, 0.2)}, pan_capacity=1000)
    lifted = _pool({"A": (150.0, 1.0), "B": (50.0, 1.0)}, pan_capacity=1000)

    assert suppressed.species["A"].probability_per_opportunity == pytest.approx(
        baseline.species["A"].probability_per_opportunity
    )
    assert (
        lifted.species["A"].probability_per_opportunity
        > baseline.species["A"].probability_per_opportunity
    )


def test_a4_runtime_integer_scale_of_weights_and_pan_capacity_is_invariant() -> None:
    before = _pool(FIXTURE_A_ROWS, pan_capacity=1000, opportunity_rate_per_sec=2)
    baseline_weights = resolve_multiplicative_candidate_weights(
        {
            species_id: CandidateWeightInputs(
                local_species_intensity=intensity,
                capture_retention=retention,
            )
            for species_id, (intensity, retention) in FIXTURE_A_ROWS.items()
        }
    )
    after = calculate_true_pool(
        {species_id: weight * 10 for species_id, weight in baseline_weights.items()},
        pan_capacity=10000,
        opportunity_rate_per_sec=2,
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
    assert after.saturated is before.saturated


def test_cr05_fixture_b_baseline_saturated_regime() -> None:
    pool = _pool(FIXTURE_B_ROWS, pan_capacity=100)

    assert pool.total_weight == 120.0
    assert pool.saturated is True
    assert pool.spawn_probability_per_opportunity == pytest.approx(1.0)
    assert pool.species["A"].probability_per_opportunity == pytest.approx(0.5)
    assert pool.species["A"].roll_time_seconds == pytest.approx(2.0)
    assert pool.species["B"].roll_time_seconds == pytest.approx(2.0)


def test_cr05_b1_saturated_added_weight_squeezes_competitor_absolute_rate() -> None:
    pool = _pool({"A": (120.0, 1.0), "B": (60.0, 1.0)}, pan_capacity=100)

    assert pool.total_weight == 180.0
    assert pool.saturated is True
    assert pool.species["A"].probability_per_opportunity == pytest.approx(2 / 3)
    assert pool.species["B"].probability_per_opportunity == pytest.approx(1 / 3)
    assert pool.species["A"].roll_time_seconds == pytest.approx(1.5)
    assert pool.species["B"].roll_time_seconds == pytest.approx(3.0)


def test_cr05_b2_saturated_uniform_scale_changes_nothing() -> None:
    before = _pool(FIXTURE_B_ROWS, pan_capacity=100)
    after = _pool({"A": (120.0, 1.0), "B": (120.0, 1.0)}, pan_capacity=100)

    assert after.saturated is True
    assert after.spawn_probability_per_opportunity == pytest.approx(1.0)
    assert after.species["A"].conditional_purity == pytest.approx(0.5)
    assert after.species["A"].roll_time_seconds == pytest.approx(2.0)
    assert after.species["A"].roll_time_seconds == pytest.approx(
        before.species["A"].roll_time_seconds
    )


def test_cr05_b3_exit_saturation_restores_unsaturated_denominator() -> None:
    pool = _pool(FIXTURE_B_ROWS, pan_capacity=240)

    assert pool.saturated is False
    assert pool.spawn_probability_per_opportunity == pytest.approx(0.5)
    assert pool.species["A"].probability_per_opportunity == pytest.approx(0.25)
    assert pool.species["A"].roll_time_seconds == pytest.approx(4.0)


def test_cr05_saturation_boundary_uses_max_n_f_continuously() -> None:
    """p_i = W_i / max(N, F) is continuous across the F == N boundary."""
    boundary = _pool({"A": (60.0, 1.0), "B": (40.0, 1.0)}, pan_capacity=100)
    unsaturated = _pool({"A": (59.4, 1.0), "B": (39.6, 1.0)}, pan_capacity=100)

    assert boundary.total_weight == 100.0
    assert boundary.saturated is True
    assert boundary.spawn_probability_per_opportunity == pytest.approx(1.0)
    assert boundary.species["A"].probability_per_opportunity == pytest.approx(0.6)
    assert unsaturated.saturated is False
    assert unsaturated.spawn_probability_per_opportunity == pytest.approx(0.99)
    assert unsaturated.species["A"].probability_per_opportunity == pytest.approx(0.594)

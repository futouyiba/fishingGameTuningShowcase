"""LEGACY pinned fixtures: historical reproduction of the retired factorized chain.

These tests intentionally reproduce the pre-Cut ``B x P x E x G x V x C``
downstream math (Fixture H's historical golden). They are migration
regressions only: the legacy producer materializes a final W that feeds the
shared Current TrueRoll kernel, and the Current Candidate consumer is never
wired through this path. Do not extend this file toward Current assertions.
"""

from __future__ import annotations

import pytest

from candidate_weight_reference import calculate_true_pool
from candidate_weight_reference.legacy import legacy_factorized_weight


def test_legacy_pinned_h1_factorized_chain_golden() -> None:
    """Fixture H historical golden: 72 * 1.10 * 0.80 * 0.50 = 31.68."""
    final_weight = legacy_factorized_weight(
        ambient_weight=72.0,
        aggregation=1.10,
        readiness=0.80,
        capture=0.50,
    )
    assert final_weight == pytest.approx(31.68)


def test_legacy_materialized_weight_feeds_shared_current_kernel() -> None:
    """Legacy producer -> materialized final W -> shared Current TrueRoll kernel."""
    final_weight = legacy_factorized_weight(
        ambient_weight=72.0,
        aggregation=1.10,
        readiness=0.80,
        capture=0.50,
    )
    pool = calculate_true_pool({"A": final_weight}, pan_capacity=1000)

    assert pool.total_weight == pytest.approx(31.68)
    assert pool.saturated is False
    assert pool.spawn_probability_per_opportunity == pytest.approx(0.03168)
    assert pool.species["A"].probability_per_opportunity == pytest.approx(0.03168)

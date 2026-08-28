"""HISTORICAL / LEGACY pinned reproduction of the retired factorized chain.

The pre-Cut surface continued a fully baked Ambient artifact with
independent Candidate-level multipliers:

    W = ambient_weight * aggregation * readiness * capture

The Current contract resolves aggregation inside the Spatial Owner's
``localSpeciesIntensity`` and settles behavioral context inside the
Interaction Owner's ``captureRetention``, so this chain must not be
consumed by any Current path. It exists only so explicitly marked legacy
fixtures can reproduce the old math and materialize a final W for the
shared TrueRoll kernel (migration regression). Do not export it on the
Current package surface and do not wire it into Current consumers.
"""

from __future__ import annotations


def legacy_factorized_weight(
    ambient_weight: float,
    aggregation: float,
    readiness: float,
    capture: float,
) -> float:
    """Pinned legacy downstream product (Fixture H historical golden math)."""
    return ambient_weight * aggregation * readiness * capture

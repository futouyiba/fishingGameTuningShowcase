from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import inf, isfinite


@dataclass(frozen=True)
class SpeciesRollResult:
    weight: float
    conditional_purity: float
    probability_per_opportunity: float
    rate_per_second: float
    roll_time_seconds: float


@dataclass(frozen=True)
class TruePoolResult:
    total_weight: float
    saturated: bool
    spawn_probability_per_opportunity: float
    any_spawn_roll_time_seconds: float
    species: dict[str, SpeciesRollResult]


def calculate_true_pool(
    weights: Mapping[str, float],
    pan_capacity: float,
    opportunity_rate_per_sec: float = 1.0,
) -> TruePoolResult:
    """Deterministic fixed-pan reference kernel."""
    if not isfinite(pan_capacity) or pan_capacity <= 0:
        raise ValueError("pan_capacity must be finite and > 0")
    if not isfinite(opportunity_rate_per_sec) or opportunity_rate_per_sec < 0:
        raise ValueError("opportunity_rate_per_sec must be finite and >= 0")

    normalized: dict[str, float] = {}
    for species_id, raw_weight in weights.items():
        weight = float(raw_weight)
        if not isfinite(weight) or weight < 0:
            raise ValueError(f"weight for {species_id!r} must be finite and >= 0")
        normalized[species_id] = weight

    total_weight = sum(normalized.values())
    denominator = max(pan_capacity, total_weight)
    spawn_probability = min(total_weight / pan_capacity, 1.0)

    if total_weight == 0 or opportunity_rate_per_sec == 0:
        any_spawn_roll_time = inf
    else:
        any_spawn_roll_time = denominator / (opportunity_rate_per_sec * total_weight)

    species_results: dict[str, SpeciesRollResult] = {}
    for species_id, weight in normalized.items():
        probability = weight / denominator
        rate = opportunity_rate_per_sec * probability
        purity = 0.0 if total_weight == 0 else weight / total_weight
        roll_time = inf if rate == 0 else 1.0 / rate
        species_results[species_id] = SpeciesRollResult(
            weight=weight,
            conditional_purity=purity,
            probability_per_opportunity=probability,
            rate_per_second=rate,
            roll_time_seconds=roll_time,
        )

    return TruePoolResult(
        total_weight=total_weight,
        saturated=total_weight >= pan_capacity,
        spawn_probability_per_opportunity=spawn_probability,
        any_spawn_roll_time_seconds=any_spawn_roll_time,
        species=species_results,
    )

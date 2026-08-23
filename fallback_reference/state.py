from __future__ import annotations

from dataclasses import dataclass, replace
from math import exp, isfinite, log1p
from typing import Literal

from candidate_weight_reference import ContractViolation

Phase = Literal["SEARCHING", "OCCUPIED_POST_SPAWN"]


@dataclass(frozen=True)
class FallbackSafetyState:
    phase: Phase = "SEARCHING"
    context_epoch: int = 0
    streak_ordinal: int = 0
    debt: float = 0.0
    active_time_credited: float = 0.0
    applied_extra_hazard: float = 0.0
    last_processed_opportunity_seq: int | None = None


@dataclass(frozen=True)
class TrueNoneSettlement:
    state: FallbackSafetyState
    opportunity_seq: int
    duplicate: bool
    delta_debt: float
    delta_g: float
    fallback_gate_probability: float
    fallback_gate_hit: bool
    fallback_species: str | None
    rng_calls: tuple[str, ...]
    alarms: tuple[str, ...]


def _unit_interval(value: float, name: str, *, allow_one: bool = True) -> float:
    value = float(value)
    upper_ok = value <= 1.0 if allow_one else value < 1.0
    if not isfinite(value) or value < 0.0 or not upper_ok:
        bound = "[0, 1]" if allow_one else "[0, 1)"
        raise ValueError(f"{name} must be finite and in {bound}")
    return value


def _choose_species(pool: tuple[str, ...], u: float) -> str:
    u = _unit_interval(u, "fallback_species_u", allow_one=False)
    index = min(int(u * len(pool)), len(pool) - 1)
    return pool[index]


def settle_true_none(
    state: FallbackSafetyState,
    *,
    opportunity_seq: int,
    p_spawn: float,
    credited_active_delta: float,
    resolved_g_target: float,
    fallback_pool: tuple[str, ...],
    fallback_gate_u: float | None = None,
    fallback_species_u: float | None = None,
) -> TrueNoneSettlement:
    """Apply one authoritative-replay TrueNone to the fallback safety state.

    `p_spawn` is the authoritative post-floor TruePool spawn probability for the
    replayed opportunity. `resolved_g_target` is produced by the current Tail
    policy / envelope resolver; this runner only applies settlement order.
    """
    if state.phase != "SEARCHING":
        raise ContractViolation("OCCUPIED_HAS_NO_OPPORTUNITY")
    if opportunity_seq < 0:
        raise ValueError("opportunity_seq must be >= 0")
    if (
        state.last_processed_opportunity_seq is not None
        and opportunity_seq <= state.last_processed_opportunity_seq
    ):
        return TrueNoneSettlement(
            state=state,
            opportunity_seq=opportunity_seq,
            duplicate=True,
            delta_debt=0.0,
            delta_g=0.0,
            fallback_gate_probability=0.0,
            fallback_gate_hit=False,
            fallback_species=None,
            rng_calls=(),
            alarms=(),
        )

    p_spawn = _unit_interval(p_spawn, "p_spawn", allow_one=False)
    credited_active_delta = float(credited_active_delta)
    if not isfinite(credited_active_delta) or credited_active_delta < 0.0:
        raise ValueError("credited_active_delta must be finite and >= 0")
    resolved_g_target = float(resolved_g_target)
    if not isfinite(resolved_g_target) or resolved_g_target < 0.0:
        raise ValueError("resolved_g_target must be finite and >= 0")

    delta_debt = -log1p(-p_spawn)
    g_target = max(state.applied_extra_hazard, resolved_g_target)
    delta_g = g_target - state.applied_extra_hazard
    base_state = replace(
        state,
        debt=state.debt + delta_debt,
        active_time_credited=state.active_time_credited + credited_active_delta,
        last_processed_opportunity_seq=opportunity_seq,
    )

    if not fallback_pool:
        return TrueNoneSettlement(
            state=base_state,
            opportunity_seq=opportunity_seq,
            duplicate=False,
            delta_debt=delta_debt,
            delta_g=0.0,
            fallback_gate_probability=0.0,
            fallback_gate_hit=False,
            fallback_species=None,
            rng_calls=(),
            alarms=("FallbackPoolEmpty",),
        )

    if delta_g <= 0.0:
        return TrueNoneSettlement(
            state=base_state,
            opportunity_seq=opportunity_seq,
            duplicate=False,
            delta_debt=delta_debt,
            delta_g=0.0,
            fallback_gate_probability=0.0,
            fallback_gate_hit=False,
            fallback_species=None,
            rng_calls=(),
            alarms=(),
        )

    if fallback_gate_u is None:
        raise ContractViolation("PRODUCER_MISSING_REQUIRED_FIELD", "fallback_gate_u")
    gate_u = _unit_interval(fallback_gate_u, "fallback_gate_u", allow_one=False)
    gate_probability = 1.0 - exp(-delta_g)
    gate_hit = gate_u < gate_probability

    applied_state = replace(base_state, applied_extra_hazard=g_target)
    rng_calls: tuple[str, ...] = ("FALLBACK_GATE",)
    species: str | None = None

    if gate_hit:
        if fallback_species_u is None:
            raise ContractViolation("PRODUCER_MISSING_REQUIRED_FIELD", "fallback_species_u")
        species = _choose_species(fallback_pool, fallback_species_u)
        rng_calls += ("FALLBACK_SPECIES",)
        applied_state = replace(
            applied_state,
            phase="OCCUPIED_POST_SPAWN",
            debt=0.0,
            active_time_credited=0.0,
            applied_extra_hazard=0.0,
        )

    return TrueNoneSettlement(
        state=applied_state,
        opportunity_seq=opportunity_seq,
        duplicate=False,
        delta_debt=delta_debt,
        delta_g=delta_g,
        fallback_gate_probability=gate_probability,
        fallback_gate_hit=gate_hit,
        fallback_species=species,
        rng_calls=rng_calls,
        alarms=(),
    )

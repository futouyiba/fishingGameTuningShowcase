from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from hashlib import sha256
from json import dumps
from typing import Any

from candidate_weight_reference import calculate_true_pool
from fallback_reference import (
    FallbackSafetyState,
    TrueNoneSettlement,
    fallback_gate_hits,
    plan_fallback_gate,
    settle_spawn_commit,
    settle_true_none,
)


@dataclass(frozen=True)
class RandomAddress:
    rng_epoch: str
    domain: str
    logical_event: int
    draw_slot: int


@dataclass(frozen=True)
class ReplayLease:
    rng_epoch: str
    algorithm_version: str = "reference-v1"


@dataclass(frozen=True)
class ReplayEntry:
    opportunity_seq: int
    candidate_weights: Mapping[str, float]
    pan_capacity: float
    credited_active_delta: float = 0.0
    resolved_g_target: float = 0.0
    fallback_pool: tuple[str, ...] = ()
    client_debug_claims: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class AuthoritativeEntryResult:
    opportunity_seq: int
    canonical_candidate_digest: str
    p_spawn: float
    true_roll_result: str
    random_addresses: tuple[RandomAddress, ...]
    fallback_settlement: TrueNoneSettlement | None


@dataclass(frozen=True)
class ReplayRun:
    final_fallback_state: FallbackSafetyState
    entries: tuple[AuthoritativeEntryResult, ...]
    commit_seq: int | None
    commit_species: str | None
    commit_source: str | None
    random_addresses: tuple[RandomAddress, ...]
    transport_request_count: int

    def semantic_signature(self) -> tuple[object, ...]:
        return (
            self.final_fallback_state,
            self.entries,
            self.commit_seq,
            self.commit_species,
            self.commit_source,
            self.random_addresses,
        )


def _deterministic_u(address: RandomAddress) -> float:
    payload = (
        f"{address.rng_epoch}|{address.domain}|{address.logical_event}|{address.draw_slot}"
    ).encode()
    raw = sha256(payload).digest()[:8]
    return int.from_bytes(raw, "big") / 2**64


def _candidate_digest(weights: tuple[tuple[str, float], ...], pan_capacity: float) -> str:
    payload = dumps(
        {"panCapacity": float(pan_capacity), "weights": weights},
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return sha256(payload).hexdigest()


def _true_roll(
    entry: ReplayEntry,
    *,
    rng_epoch: str,
) -> tuple[float, str, RandomAddress, str]:
    pool = calculate_true_pool(entry.candidate_weights, entry.pan_capacity)
    canonical_species = tuple(sorted(pool.species))
    canonical_weights = tuple(
        (species_id, pool.species[species_id].weight) for species_id in canonical_species
    )

    address = RandomAddress(rng_epoch, "TRUE_ROLL", entry.opportunity_seq, 0)
    draw = _deterministic_u(address)
    cumulative_probability = 0.0
    result = "TrueNone"
    for species_id in canonical_species:
        cumulative_probability += pool.species[species_id].probability_per_opportunity
        if draw < cumulative_probability:
            result = f"TrueSpawn:{species_id}"
            break

    return (
        pool.spawn_probability_per_opportunity,
        result,
        address,
        _candidate_digest(canonical_weights, entry.pan_capacity),
    )


def _run(
    state: FallbackSafetyState,
    lease: ReplayLease,
    ordered_entries: tuple[ReplayEntry, ...],
) -> ReplayRun:
    results: list[AuthoritativeEntryResult] = []
    addresses: list[RandomAddress] = []
    commit_seq: int | None = None
    commit_species: str | None = None
    commit_source: str | None = None

    for entry in ordered_entries:
        if state.phase != "SEARCHING":
            break
        p_spawn, true_result, true_address, digest = _true_roll(
            entry,
            rng_epoch=lease.rng_epoch,
        )
        entry_addresses = [true_address]
        addresses.append(true_address)

        if true_result.startswith("TrueSpawn:"):
            commit_species = true_result.split(":", 1)[1]
            commit_seq = entry.opportunity_seq
            commit_source = "TRUE"
            state = settle_spawn_commit(
                state,
                opportunity_seq=entry.opportunity_seq,
            )
            results.append(
                AuthoritativeEntryResult(
                    entry.opportunity_seq,
                    digest,
                    p_spawn,
                    true_result,
                    tuple(entry_addresses),
                    None,
                )
            )
            break

        gate_plan = plan_fallback_gate(
            state,
            resolved_g_target=entry.resolved_g_target,
            fallback_pool=entry.fallback_pool,
        )
        gate_u = None
        species_u = None
        if gate_plan.should_attempt:
            gate_address = RandomAddress(
                lease.rng_epoch,
                "FALLBACK_GATE",
                entry.opportunity_seq,
                0,
            )
            gate_u = _deterministic_u(gate_address)
            entry_addresses.append(gate_address)
            addresses.append(gate_address)
            if fallback_gate_hits(gate_plan, gate_u):
                species_address = RandomAddress(
                    lease.rng_epoch,
                    "FALLBACK_SPECIES",
                    entry.opportunity_seq,
                    0,
                )
                species_u = _deterministic_u(species_address)
                entry_addresses.append(species_address)
                addresses.append(species_address)

        fallback = settle_true_none(
            state,
            opportunity_seq=entry.opportunity_seq,
            p_spawn=p_spawn,
            credited_active_delta=entry.credited_active_delta,
            resolved_g_target=entry.resolved_g_target,
            fallback_pool=entry.fallback_pool,
            fallback_gate_u=gate_u,
            fallback_species_u=species_u,
        )
        state = fallback.state
        if fallback.fallback_species is not None:
            commit_seq = entry.opportunity_seq
            commit_species = fallback.fallback_species
            commit_source = "FALLBACK"
        results.append(
            AuthoritativeEntryResult(
                entry.opportunity_seq,
                digest,
                p_spawn,
                true_result,
                tuple(entry_addresses),
                fallback,
            )
        )
        if commit_seq is not None:
            break

    return ReplayRun(
        final_fallback_state=state,
        entries=tuple(results),
        commit_seq=commit_seq,
        commit_species=commit_species,
        commit_source=commit_source,
        random_addresses=tuple(addresses),
        transport_request_count=0,
    )


def replay_stepwise(
    state: FallbackSafetyState,
    lease: ReplayLease,
    entries: tuple[ReplayEntry, ...],
) -> ReplayRun:
    run = _run(state, lease, entries)
    return replace(run, transport_request_count=len(run.entries))


def replay_batch(
    state: FallbackSafetyState,
    lease: ReplayLease,
    entries: tuple[ReplayEntry, ...],
) -> ReplayRun:
    run = _run(state, lease, entries)
    return replace(run, transport_request_count=1 if entries else 0)

from __future__ import annotations

import math

import pytest

from fallback_reference import FallbackSafetyState, settle_true_none


def test_true_none_uses_exact_hazard_from_authoritative_post_floor_p_spawn() -> None:
    result = settle_true_none(
        FallbackSafetyState(),
        opportunity_seq=1,
        p_spawn=0.30,
        credited_active_delta=5.0,
        resolved_g_target=0.0,
        fallback_pool=("background-a",),
    )

    assert result.delta_debt == pytest.approx(-math.log(0.70))
    assert result.state.debt == pytest.approx(-math.log(0.70))
    assert result.state.active_time_credited == pytest.approx(5.0)
    assert result.rng_calls == ()


def test_rt_fb_017_empty_pool_does_not_burn_applied_hazard_or_rng() -> None:
    before = FallbackSafetyState(
        debt=0.4,
        active_time_credited=90.0,
        applied_extra_hazard=0.25,
    )
    result = settle_true_none(
        before,
        opportunity_seq=42,
        p_spawn=0.10,
        credited_active_delta=2.0,
        resolved_g_target=0.80,
        fallback_pool=(),
    )

    assert result.state.debt == pytest.approx(0.4 - math.log(0.90))
    assert result.state.active_time_credited == pytest.approx(92.0)
    assert result.state.applied_extra_hazard == pytest.approx(0.25)
    assert result.delta_g == 0.0
    assert result.rng_calls == ()
    assert result.alarms == ("FallbackPoolEmpty",)
    assert result.fallback_gate_hit is False


def test_rt_fb_017_retry_same_seq_is_idempotent() -> None:
    first = settle_true_none(
        FallbackSafetyState(applied_extra_hazard=0.25),
        opportunity_seq=42,
        p_spawn=0.10,
        credited_active_delta=2.0,
        resolved_g_target=0.80,
        fallback_pool=(),
    )
    retry = settle_true_none(
        first.state,
        opportunity_seq=42,
        p_spawn=0.10,
        credited_active_delta=2.0,
        resolved_g_target=0.80,
        fallback_pool=("now-present",),
        fallback_gate_u=0.0,
        fallback_species_u=0.0,
    )

    assert retry.duplicate is True
    assert retry.state == first.state
    assert retry.rng_calls == ()
    assert retry.delta_debt == 0.0
    assert retry.delta_g == 0.0


def test_nonempty_pool_applies_g_even_when_gate_misses() -> None:
    result = settle_true_none(
        FallbackSafetyState(applied_extra_hazard=0.25),
        opportunity_seq=7,
        p_spawn=0.05,
        credited_active_delta=1.0,
        resolved_g_target=0.80,
        fallback_pool=("a", "b"),
        fallback_gate_u=0.99,
    )

    assert result.delta_g == pytest.approx(0.55)
    assert result.state.applied_extra_hazard == pytest.approx(0.80)
    assert result.rng_calls == ("FALLBACK_GATE",)
    assert result.fallback_gate_hit is False


def test_gate_hit_uses_species_rng_then_spawn_commit_resets_streak() -> None:
    result = settle_true_none(
        FallbackSafetyState(
            debt=0.2,
            active_time_credited=80.0,
            applied_extra_hazard=0.1,
        ),
        opportunity_seq=8,
        p_spawn=0.05,
        credited_active_delta=1.0,
        resolved_g_target=2.0,
        fallback_pool=("a", "b"),
        fallback_gate_u=0.0,
        fallback_species_u=0.75,
    )

    assert result.fallback_gate_hit is True
    assert result.fallback_species == "b"
    assert result.rng_calls == ("FALLBACK_GATE", "FALLBACK_SPECIES")
    assert result.state.phase == "OCCUPIED_POST_SPAWN"
    assert result.state.debt == 0.0
    assert result.state.active_time_credited == 0.0
    assert result.state.applied_extra_hazard == 0.0

from __future__ import annotations

from fallback_reference import FallbackSafetyState
from replay_reference import ReplayEntry, ReplayLease, replay_batch, replay_stepwise


def _transport_fixture() -> tuple[ReplayEntry, ...]:
    return (
        ReplayEntry(
            1,
            {"A": 1.0},
            1_000_000_000.0,
            credited_active_delta=5.0,
        ),
        ReplayEntry(
            2,
            {"A": 1.0},
            1_000_000_000.0,
            credited_active_delta=5.0,
            resolved_g_target=0.5,
            fallback_pool=(),
        ),
        ReplayEntry(
            3,
            {"A": 1.0},
            1_000_000_000.0,
            credited_active_delta=5.0,
            resolved_g_target=100.0,
            fallback_pool=("background-a", "background-b"),
        ),
        ReplayEntry(
            4,
            {"A": 1.0},
            1_000_000_000.0,
            credited_active_delta=5.0,
        ),
    )


def test_rp_auth_034_logical_sequence_is_transport_shape_invariant() -> None:
    state = FallbackSafetyState()
    lease = ReplayLease("epoch-001")

    stepwise = replay_stepwise(state, lease, _transport_fixture())
    batch = replay_batch(state, lease, _transport_fixture())

    assert (
        stepwise.semantic_signature() == batch.semantic_signature()
    ), "REPLAY_SEMANTICS_ASSUMED_AS_RPC"
    assert stepwise.transport_request_count == 3
    assert batch.transport_request_count == 1
    assert stepwise.commit_source == "FALLBACK"
    assert stepwise.commit_seq == 3
    assert len(stepwise.entries) == 3


def test_client_debug_claims_are_not_authority_inputs() -> None:
    lease = ReplayLease("epoch-002")
    clean = ReplayEntry(10, {"A": 2.0, "B": 1.0}, 1000.0)
    poisoned = ReplayEntry(
        10,
        {"A": 2.0, "B": 1.0},
        1000.0,
        client_debug_claims={
            "pSpawn": 1.0,
            "trueRollResult": "TrueSpawn:B",
            "fishIdentity": "B",
        },
    )

    authoritative_clean = replay_batch(FallbackSafetyState(), lease, (clean,))
    authoritative_poisoned = replay_batch(FallbackSafetyState(), lease, (poisoned,))

    assert authoritative_clean.semantic_signature() == authoritative_poisoned.semantic_signature()


def test_candidate_input_order_is_canonical() -> None:
    lease = ReplayLease("epoch-003")
    first = replay_batch(
        FallbackSafetyState(),
        lease,
        (ReplayEntry(20, {"B": 1.0, "A": 2.0}, 1000.0),),
    )
    second = replay_batch(
        FallbackSafetyState(),
        lease,
        (ReplayEntry(20, {"A": 2.0, "B": 1.0}, 1000.0),),
    )

    assert first.semantic_signature() == second.semantic_signature()

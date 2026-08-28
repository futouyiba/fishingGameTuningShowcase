from __future__ import annotations

import pytest

from persistent_cause_reference import (
    CauseEvent,
    replay_cause_events_batch,
    replay_cause_events_stepwise,
)


def event_fixture() -> tuple[CauseEvent, ...]:
    return (
        CauseEvent(1, "FeedingCommitted", 0.35),
        CauseEvent(2, "QualifiedActiveTimeElapsed", -0.10),
        CauseEvent(3, "FeedingCommitted", 0.20),
        CauseEvent(4, "QualifiedActiveTimeElapsed", -0.05),
    )


def test_pc09_reconstruction_is_transport_shape_invariant() -> None:
    stepwise = replay_cause_events_stepwise(
        "satiation:species:trout",
        "SatiationReducer.v1",
        event_fixture(),
    )
    batch = replay_cause_events_batch(
        "satiation:species:trout",
        "SatiationReducer.v1",
        (event_fixture()[:1], event_fixture()[1:3], event_fixture()[3:]),
    )

    assert stepwise.semantic_digest == batch.semantic_digest
    assert stepwise.final_value == batch.final_value == pytest.approx(0.4)
    assert stepwise.applied_event_ids == batch.applied_event_ids == (1, 2, 3, 4)
    assert stepwise.transport_chunk_count == 4
    assert batch.transport_chunk_count == 3


def test_pc09_reconstruction_is_canonical_for_same_logical_sequence() -> None:
    one_chunk = replay_cause_events_batch(
        "satiation:species:trout",
        "SatiationReducer.v1",
        (event_fixture(),),
    )
    duplicate_transport = replay_cause_events_batch(
        "satiation:species:trout",
        "SatiationReducer.v1",
        (event_fixture()[:2], event_fixture()[1:]),
    )

    assert one_chunk.semantic_digest == duplicate_transport.semantic_digest
    assert duplicate_transport.applied_event_ids == (1, 2, 3, 4)


def test_pc09_semantic_order_is_not_canonicalized_by_event_id() -> None:
    in_declared_order = replay_cause_events_stepwise(
        "satiation:species:trout",
        "SatiationReducer.v1",
        (
            CauseEvent(20, "Increase", 0.4),
            CauseEvent(10, "Decrease", -0.2),
        ),
    )
    reordered = replay_cause_events_stepwise(
        "satiation:species:trout",
        "SatiationReducer.v1",
        (
            CauseEvent(10, "Decrease", -0.2),
            CauseEvent(20, "Increase", 0.4),
        ),
    )

    assert in_declared_order.applied_event_ids == (20, 10)
    assert reordered.applied_event_ids == (10, 20)
    assert in_declared_order.final_value == pytest.approx(0.2)
    assert reordered.final_value == pytest.approx(0.4)
    assert in_declared_order.semantic_digest != reordered.semantic_digest


def test_pc09_reducer_version_is_part_of_semantic_digest() -> None:
    version_one = replay_cause_events_stepwise(
        "satiation:species:trout",
        "SatiationReducer.v1",
        event_fixture(),
    )
    version_two = replay_cause_events_stepwise(
        "satiation:species:trout",
        "SatiationReducer.v2",
        event_fixture(),
    )

    assert version_one.final_value == version_two.final_value
    assert version_one.semantic_digest != version_two.semantic_digest

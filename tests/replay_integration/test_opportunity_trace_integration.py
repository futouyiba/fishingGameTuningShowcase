from fallback_reference import FallbackSafetyState
from opportunity_reference import (
    EvaluationPolicy,
    FormationPolicy,
    MeasureSpan,
    OpportunitySemanticFixture,
    ProgressSlot,
    SupportDomainValue,
    resolve_opportunity_candidate_weights,
    resolve_opportunity_semantic_fixture,
)
from replay_reference import ReplayEntry, ReplayLease, replay_batch


def _static_fixture(spans: tuple[MeasureSpan, ...]) -> OpportunitySemanticFixture:
    policy = EvaluationPolicy("static-point", "event_point", "point")
    slot = ProgressSlot(
        "static-renew",
        "static-renewal",
        "dwell",
        "static_scope",
        4.0,
        "renewal",
        policy.evaluation_policy_id,
    )
    return OpportunitySemanticFixture(
        active_channel_ref="channel-opportunity-replay",
        formation_policy=FormationPolicy((slot,)),
        evaluation_policies={policy.evaluation_policy_id: policy},
        semantic_source_trace=spans,
    )


def _replay_entries(trace):
    entries = []
    for item in trace:
        support_stub = {
            support.support_id: {"A": SupportDomainValue(0.0, 1.0)}
            for support in item.weighted_support
        }
        resolved = resolve_opportunity_candidate_weights(item, support_stub)
        entries.append(
            ReplayEntry(
                opportunity_seq=item.opportunity_seq,
                candidate_weights=resolved.weights,
                pan_capacity=1_000.0,
            )
        )
    return tuple(entries)


def test_opportunity_partition_invariance_survives_candidate_handoff_and_replay() -> None:
    coarse = _static_fixture(
        (
            MeasureSpan(
                "coarse",
                "static_scope",
                "static#1",
                "dwell",
                0.0,
                10.0,
                10.0,
            ),
        )
    )
    partitioned = _static_fixture(
        (
            MeasureSpan(
                "part-1",
                "static_scope",
                "static#1",
                "dwell",
                0.0,
                3.0,
                3.0,
            ),
            MeasureSpan(
                "part-2",
                "static_scope",
                "static#1",
                "dwell",
                3.0,
                7.0,
                4.0,
            ),
            MeasureSpan(
                "part-3",
                "static_scope",
                "static#1",
                "dwell",
                7.0,
                10.0,
                3.0,
            ),
        )
    )

    coarse_trace = resolve_opportunity_semantic_fixture(coarse)
    partitioned_trace = resolve_opportunity_semantic_fixture(partitioned)

    assert coarse_trace == partitioned_trace
    assert [item.occurrence_logical_time for item in coarse_trace] == [4.0, 8.0]

    lease = ReplayLease("epoch-opportunity-partition")
    coarse_run = replay_batch(
        FallbackSafetyState(),
        lease,
        _replay_entries(coarse_trace),
    )
    partitioned_run = replay_batch(
        FallbackSafetyState(),
        lease,
        _replay_entries(partitioned_trace),
    )

    assert coarse_run.semantic_signature() == partitioned_run.semantic_signature()
    assert [entry.opportunity_seq for entry in coarse_run.entries] == [1, 2]
    assert [address.logical_event for address in coarse_run.random_addresses] == [1, 2]
    assert coarse_run.commit_seq is None

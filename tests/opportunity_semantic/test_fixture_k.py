from math import isclose

import pytest

from candidate_weight_reference import calculate_true_pool
from opportunity_reference import (
    ChannelClose,
    EvaluationPolicy,
    EventSlot,
    FormationPolicy,
    MeasureSpan,
    OpportunitySemanticFixture,
    ProgressSlot,
    SemanticEvent,
    SupportDomainValue,
    resolve_opportunity_candidate_weights,
    resolve_opportunity_semantic_fixture,
)


def _fixture(slots, policies, trace, phase_masks=None):
    return OpportunitySemanticFixture(
        active_channel_ref="channel-1",
        formation_policy=FormationPolicy(tuple(slots)),
        evaluation_policies={policy.evaluation_policy_id: policy for policy in policies},
        semantic_source_trace=tuple(trace),
        phase_masks={} if phase_masks is None else phase_masks,
    )


def test_k1_large_dwell_chunk_emits_at_each_crossing_not_packet_endpoint():
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
    trace = [
        MeasureSpan(
            "dwell-0",
            "static_scope",
            "static#1",
            "dwell",
            0.0,
            10.0,
            10.0,
        )
    ]

    result = resolve_opportunity_semantic_fixture(_fixture([slot], [policy], trace))

    assert [item.occurrence_logical_time for item in result] == [4.0, 8.0]
    assert [item.opportunity_seq for item in result] == [1, 2]
    assert all(item.weighted_support[0].alpha == 1.0 for item in result)


def test_k2_retrieve_uses_traversal_alpha_not_time_share():
    policy = EvaluationPolicy(
        "retrieve-traversal",
        "formation_interval",
        "traversal",
    )
    slot = ProgressSlot(
        "retrieve",
        "retrieve-renewal",
        "retrieve_progress",
        "retrieve_scope",
        4.0,
        "renewal",
        policy.evaluation_policy_id,
    )
    trace = [
        MeasureSpan(
            "r1",
            "retrieve_scope",
            "retrieve#1",
            "retrieve_progress",
            0.0,
            3.0,
            1.0,
            traversal_mass=1.0,
        ),
        MeasureSpan(
            "r2",
            "retrieve_scope",
            "retrieve#1",
            "retrieve_progress",
            3.0,
            4.0,
            3.0,
            traversal_mass=3.0,
        ),
    ]

    result = resolve_opportunity_semantic_fixture(_fixture([slot], [policy], trace))

    assert len(result) == 1
    assert result[0].occurrence_logical_time == 4.0
    assert [support.support_id for support in result[0].weighted_support] == [
        "r1",
        "r2",
    ]
    assert [support.alpha for support in result[0].weighted_support] == [0.25, 0.75]


def test_k3_drift_uses_qualified_time_share():
    policy = EvaluationPolicy("drift-time", "formation_interval", "time")
    slot = ProgressSlot(
        "drift",
        "sustained-drift",
        "drift_time",
        "drift_scope",
        3.0,
        "once_per_scope",
        policy.evaluation_policy_id,
    )
    trace = [
        MeasureSpan("d1", "drift_scope", "drift#1", "drift_time", 0.0, 1.0, 1.0),
        MeasureSpan("d2", "drift_scope", "drift#1", "drift_time", 1.0, 3.0, 2.0),
    ]

    result = resolve_opportunity_semantic_fixture(_fixture([slot], [policy], trace))

    assert len(result) == 1
    alpha = [support.alpha for support in result[0].weighted_support]
    assert alpha == pytest.approx([1 / 3, 2 / 3])


def test_k4_event_identity_dedupes_callback_duplicates_and_context_is_zero_mass():
    policy = EvaluationPolicy(
        "bottom-contact-point",
        "event_point",
        "point",
        context_scope_ref="antecedent_same_source_scope",
    )
    slot = EventSlot(
        "bottom-contact",
        "bottom-contact-strike",
        "bottom_contact",
        "fall_scope",
        policy.evaluation_policy_id,
    )
    trace = [
        MeasureSpan(
            "fall-history",
            "fall_scope",
            "fall#7",
            "fall_time",
            4.0,
            5.0,
            1.0,
            phase="fall",
        ),
        SemanticEvent(
            "contact#7",
            "bottom_contact",
            "fall_scope",
            "fall#7",
            5.0,
            phase="contact",
        ),
        SemanticEvent(
            "contact#7",
            "bottom_contact",
            "fall_scope",
            "fall#7",
            5.0,
            phase="contact",
        ),
    ]

    result = resolve_opportunity_semantic_fixture(_fixture([slot], [policy], trace))

    assert len(result) == 1
    assert result[0].weighted_support[0].support_id == "event:contact#7"
    assert result[0].weighted_support[0].alpha == 1.0
    assert [ref.source_item_id for ref in result[0].context_refs] == ["fall-history"]


def test_k5_once_per_scope_and_no_future_duration_leakage():
    policy = EvaluationPolicy(
        "pause-time",
        "formation_interval",
        "time",
        phase_mask_ref="pause_only",
    )
    slot = ProgressSlot(
        "pause",
        "pause-strike-window",
        "pause_time",
        "pause_scope",
        0.3,
        "once_per_scope",
        policy.evaluation_policy_id,
    )
    short = [
        MeasureSpan(
            "pause-short",
            "pause_scope",
            "pause#1",
            "pause_time",
            0.0,
            1.0,
            1.0,
            phase="pause",
        )
    ]
    long = [
        MeasureSpan(
            "pause-long",
            "pause_scope",
            "pause#1",
            "pause_time",
            0.0,
            2.0,
            2.0,
            phase="pause",
        )
    ]
    masks = {"pause_only": frozenset({"pause"})}

    result_short = resolve_opportunity_semantic_fixture(_fixture([slot], [policy], short, masks))
    result_long = resolve_opportunity_semantic_fixture(_fixture([slot], [policy], long, masks))

    assert len(result_short) == len(result_long) == 1
    assert result_short[0].occurrence_logical_time == pytest.approx(0.3)
    assert result_long[0].occurrence_logical_time == pytest.approx(0.3)
    assert result_short[0].weighted_support[0].end_time == pytest.approx(0.3)
    assert result_long[0].weighted_support[0].end_time == pytest.approx(0.3)


def test_k6_same_technique_can_have_point_and_time_slots():
    contact_policy = EvaluationPolicy("jig-contact", "event_point", "point")
    pause_policy = EvaluationPolicy(
        "jig-pause",
        "formation_interval",
        "time",
        phase_mask_ref="pause_only",
    )
    contact_slot = EventSlot(
        "contact",
        "contact-strike",
        "bottom_contact",
        "jig_scope",
        contact_policy.evaluation_policy_id,
    )
    pause_slot = ProgressSlot(
        "pause",
        "pause-window",
        "pause_time",
        "jig_scope",
        0.5,
        "once_per_scope",
        pause_policy.evaluation_policy_id,
    )
    trace = [
        SemanticEvent(
            "jig-contact#1",
            "bottom_contact",
            "jig_scope",
            "jig#1",
            1.0,
            phase="contact",
        ),
        MeasureSpan(
            "jig-pause#1",
            "jig_scope",
            "jig#1",
            "pause_time",
            1.0,
            2.0,
            1.0,
            phase="pause",
        ),
    ]
    masks = {"pause_only": frozenset({"pause"})}

    result = resolve_opportunity_semantic_fixture(
        _fixture(
            [contact_slot, pause_slot],
            [contact_policy, pause_policy],
            trace,
            masks,
        )
    )

    assert [(item.slot_id, item.occurrence_logical_time) for item in result] == [
        ("contact", 1.0),
        ("pause", 1.5),
    ]
    assert result[0].weighted_support[0].alpha == 1.0
    assert result[1].weighted_support[0].measure_mass == pytest.approx(0.5)


def test_k7_channel_close_suppresses_later_opportunities():
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
    trace = [
        MeasureSpan(
            "dwell",
            "static_scope",
            "static#1",
            "dwell",
            0.0,
            10.0,
            10.0,
        ),
        ChannelClose(5.0),
    ]

    result = resolve_opportunity_semantic_fixture(_fixture([slot], [policy], trace))

    assert [item.occurrence_logical_time for item in result] == [4.0]


def test_k8_join_before_reduce_blocks_phantom_mass():
    policy = EvaluationPolicy(
        "retrieve-traversal",
        "formation_interval",
        "traversal",
    )
    slot = ProgressSlot(
        "retrieve",
        "retrieve-renewal",
        "retrieve_progress",
        "retrieve_scope",
        2.0,
        "once_per_scope",
        policy.evaluation_policy_id,
    )
    trace = [
        MeasureSpan(
            "s1",
            "retrieve_scope",
            "retrieve#1",
            "retrieve_progress",
            0.0,
            1.0,
            1.0,
            traversal_mass=1.0,
        ),
        MeasureSpan(
            "s2",
            "retrieve_scope",
            "retrieve#1",
            "retrieve_progress",
            1.0,
            2.0,
            1.0,
            traversal_mass=1.0,
        ),
    ]
    opportunity = resolve_opportunity_semantic_fixture(_fixture([slot], [policy], trace))[0]
    stub = {
        "s1": {"A": SupportDomainValue(1.0, 0.0)},
        "s2": {"A": SupportDomainValue(0.0, 1.0)},
    }

    resolved = resolve_opportunity_candidate_weights(opportunity, stub)

    assert resolved.weights["A"] == 0.0
    reduce_then_multiply = 0.5 * 0.5
    assert reduce_then_multiply == 0.25
    assert not isclose(resolved.weights["A"], reduce_then_multiply)


def test_k9_support_species_coverage_mismatch_fails_closed():
    policy = EvaluationPolicy(
        "retrieve-traversal",
        "formation_interval",
        "traversal",
    )
    slot = ProgressSlot(
        "retrieve",
        "retrieve-renewal",
        "retrieve_progress",
        "retrieve_scope",
        2.0,
        "once_per_scope",
        policy.evaluation_policy_id,
    )
    trace = [
        MeasureSpan(
            "s1",
            "retrieve_scope",
            "retrieve#1",
            "retrieve_progress",
            0.0,
            1.0,
            1.0,
            traversal_mass=1.0,
        ),
        MeasureSpan(
            "s2",
            "retrieve_scope",
            "retrieve#1",
            "retrieve_progress",
            1.0,
            2.0,
            1.0,
            traversal_mass=1.0,
        ),
    ]
    opportunity = resolve_opportunity_semantic_fixture(_fixture([slot], [policy], trace))[0]
    stub = {
        "s1": {"A": SupportDomainValue(1.0, 1.0)},
        "s2": {
            "A": SupportDomainValue(1.0, 1.0),
            "B": SupportDomainValue(1.0, 1.0),
        },
    }

    with pytest.raises(ValueError, match="species coverage differs"):
        resolve_opportunity_candidate_weights(opportunity, stub)


def test_k10_candidate_handoff_feeds_existing_true_pool_kernel():
    policy = EvaluationPolicy(
        "retrieve-traversal",
        "formation_interval",
        "traversal",
    )
    slot = ProgressSlot(
        "retrieve",
        "retrieve-renewal",
        "retrieve_progress",
        "retrieve_scope",
        4.0,
        "once_per_scope",
        policy.evaluation_policy_id,
    )
    trace = [
        MeasureSpan(
            "r1",
            "retrieve_scope",
            "retrieve#1",
            "retrieve_progress",
            0.0,
            3.0,
            1.0,
            traversal_mass=1.0,
        ),
        MeasureSpan(
            "r2",
            "retrieve_scope",
            "retrieve#1",
            "retrieve_progress",
            3.0,
            4.0,
            3.0,
            traversal_mass=3.0,
        ),
    ]
    opportunity = resolve_opportunity_semantic_fixture(_fixture([slot], [policy], trace))[0]
    stub = {
        "r1": {
            "A": SupportDomainValue(4.0, 1.0),
            "B": SupportDomainValue(0.0, 1.0),
        },
        "r2": {
            "A": SupportDomainValue(0.0, 1.0),
            "B": SupportDomainValue(4.0, 1.0),
        },
    }

    resolved = resolve_opportunity_candidate_weights(opportunity, stub)
    pool = calculate_true_pool(resolved.weights, pan_capacity=10.0)

    assert resolved.weights == pytest.approx({"A": 1.0, "B": 3.0})
    assert pool.total_weight == pytest.approx(4.0)
    assert pool.spawn_probability_per_opportunity == pytest.approx(0.4)
    assert pool.species["A"].probability_per_opportunity == pytest.approx(0.1)
    assert pool.species["B"].probability_per_opportunity == pytest.approx(0.3)


def test_k11_scope_clip_is_fail_closed_until_owner_policy_is_implemented():
    policy = EvaluationPolicy(
        "clipped",
        "formation_interval",
        "time",
        scope_clip_policy_ref="clip-policy-working",
    )
    slot = ProgressSlot(
        "drift",
        "sustained-drift",
        "drift_time",
        "drift_scope",
        1.0,
        "once_per_scope",
        policy.evaluation_policy_id,
    )
    trace = [
        MeasureSpan(
            "d",
            "drift_scope",
            "drift#1",
            "drift_time",
            0.0,
            1.0,
            1.0,
        )
    ]

    with pytest.raises(NotImplementedError, match="scope_clip_policy_ref"):
        _fixture([slot], [policy], trace)

from __future__ import annotations

from dataclasses import replace

import pytest

from fallback_reference import FallbackSafetyState
from persistent_cause_reference import (
    AdmissionStatus,
    CardinalityDeclaration,
    HistoryNecessityProof,
    LifecycleDeclaration,
    MutationDeclaration,
    PersistentCauseProposal,
    ReplayDeclaration,
    TemporalStep,
    validate_persistent_cause_proposal,
    validate_persistent_cause_proposals,
)


def complete_proposal(**overrides: object) -> PersistentCauseProposal:
    proposal = PersistentCauseProposal(
        cause_id="satiation:species:trout",
        semantic_kind="SatiationCause",
        canonical_owner="Behavioral.SatiationOwner",
        bearer_identity="species:trout",
        scope="population:pond-1001",
        history_necessity_proof=HistoryNecessityProof(
            same_present_inputs=True,
            different_admissible_histories=True,
            desired_future_outputs_differ=True,
            fixture_ref="fixture:satiation-history-divergence-v1",
        ),
        formation_events=(MutationDeclaration("FeedingCommitted", "authoritative_typed_event"),),
        update_events=(MutationDeclaration("QualifiedActiveTimeElapsed", "admitted_process"),),
        consumer_domains=("Readiness.MotivationResolver",),
        lifecycle=LifecycleDeclaration(
            reducer_ref="SatiationReducer.v1",
            logical_time_semantics="authoritative_active_time",
            decay_or_recovery_rule="recover_toward_baseline",
            merge_or_stack_rule="not_applicable",
            reset_or_expiration_rule="expire_on_population_scope_close",
            version_migration_invalidation="invalidate_on_reducer_major_change",
        ),
        replay_contract=ReplayDeclaration(
            authoritative_source="ServerEventJournal",
            reconstructable_or_verifiable=True,
            checkpoint_or_event_lineage_ref="event-lineage:satiation-v1",
        ),
        cardinality=CardinalityDeclaration(
            bearer_count_class="species_per_population_scope",
            retention_budget="bounded_by_active_population_scopes",
            is_high_cardinality=False,
            lower_cardinality_alternative_considered=True,
            lower_cardinality_rejection_reason="A pond-global cause loses species-specific history.",
        ),
        represents_underlying_cause=True,
        temporal_trace=(
            TemporalStep(7, 10, "resolve_input", False),
            TemporalStep(7, 20, "emit_event", False),
            TemporalStep(8, 10, "mutate_state", False),
            TemporalStep(8, 20, "resolve_input", True),
        ),
    )
    return replace(proposal, **overrides)


def assert_failure(
    proposal: PersistentCauseProposal,
    status: AdmissionStatus,
    gate: str,
    reason: str,
) -> None:
    result = validate_persistent_cause_proposal(proposal)

    assert result.status is status
    assert gate in result.failed_gates
    assert reason in result.reason_codes


def test_pc01_no_history_divergence_rejects_derived_or_cache() -> None:
    proposal = complete_proposal(
        history_necessity_proof=HistoryNecessityProof(
            same_present_inputs=True,
            different_admissible_histories=True,
            desired_future_outputs_differ=False,
            fixture_ref="fixture:no-divergence",
        )
    )

    assert_failure(
        proposal,
        AdmissionStatus.REJECT_DERIVED_OR_CACHE,
        "G1_HISTORY_NECESSITY",
        "HISTORY_DIVERGENCE_NOT_ESTABLISHED",
    )


def test_pc02_valid_history_divergence_allows_admission_to_continue() -> None:
    result = validate_persistent_cause_proposal(complete_proposal())

    assert result.status is AdmissionStatus.ADMITTED
    assert result.failed_gates == ()
    assert result.reason_codes == ()


@pytest.mark.parametrize(
    "owner",
    [None, "", ("World.Owner", "Behavioral.Owner")],
)
def test_pc03_missing_or_multiple_owner_is_blocker(owner: object) -> None:
    assert_failure(
        complete_proposal(canonical_owner=owner),
        AdmissionStatus.OWNER_UNRESOLVED,
        "EXACTLY_ONE_CONCRETE_OWNER",
        "CANONICAL_OWNER_NOT_EXACTLY_ONE",
    )


def test_pc04_client_only_mutation_authority_is_blocker() -> None:
    proposal = complete_proposal(
        formation_events=(MutationDeclaration("client-click-count", "client_click"),),
        update_events=(MutationDeclaration("animation-finished", "animation_callback"),),
    )

    assert_failure(
        proposal,
        AdmissionStatus.AUTHORITY_REPLAY_INCOMPLETE,
        "G2_ACCEPTED_FORMATION_UPDATE_EVENT",
        "AUTHORITATIVE_MUTATION_SOURCE_MISSING",
    )


def test_pc04_any_declared_unauthorized_mutation_path_is_blocker() -> None:
    proposal = complete_proposal(
        update_events=(
            MutationDeclaration("QualifiedActiveTimeElapsed", "admitted_process"),
            MutationDeclaration("raw-packet-count", "raw_packet_counter"),
        ),
    )

    assert_failure(
        proposal,
        AdmissionStatus.AUTHORITY_REPLAY_INCOMPLETE,
        "G2_ACCEPTED_FORMATION_UPDATE_EVENT",
        "UNAUTHORIZED_MUTATION_SOURCE_DECLARED",
    )


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"bearer_identity": None}, "BEARER_IDENTITY_MISSING"),
        ({"scope": None}, "CAUSE_SCOPE_MISSING"),
    ],
)
def test_pc05_missing_bearer_or_scope_is_blocker(overrides: dict[str, object], reason: str) -> None:
    assert_failure(
        complete_proposal(**overrides),
        AdmissionStatus.DECLARATION_INCOMPLETE,
        "G3_BEARER_IDENTITY_SCOPE",
        reason,
    )


def test_pc06_derived_response_bonus_is_not_an_underlying_cause() -> None:
    proposal = complete_proposal(
        cause_id="catchabilityPenalty:0.7",
        semantic_kind="catchabilityPenalty",
        represents_underlying_cause=False,
    )

    assert_failure(
        proposal,
        AdmissionStatus.CAUSE_EFFECT_CONFUSION,
        "CAUSE_NOT_DERIVED_EFFECT",
        "UNDERLYING_CAUSE_IDENTITY_NOT_ESTABLISHED",
    )


def test_pc07_complete_lifecycle_declaration_is_admitted() -> None:
    result = validate_persistent_cause_proposal(complete_proposal())

    assert result.status is AdmissionStatus.ADMITTED

    missing_reset = replace(
        complete_proposal().lifecycle,
        reset_or_expiration_rule=None,
    )
    assert_failure(
        complete_proposal(lifecycle=missing_reset),
        AdmissionStatus.DECLARATION_INCOMPLETE,
        "G4_INDEPENDENT_LIFECYCLE",
        "LIFECYCLE_RESET_OR_EXPIRATION_MISSING",
    )


def test_pc08_high_cardinality_requires_lower_cardinality_analysis() -> None:
    cardinality = CardinalityDeclaration(
        bearer_count_class="species_x_spot_x_lure_x_cause",
        retention_budget="bounded_by_active_spot_lure_pairs",
        is_high_cardinality=True,
        lower_cardinality_alternative_considered=False,
        lower_cardinality_rejection_reason=None,
    )

    assert_failure(
        complete_proposal(cardinality=cardinality),
        AdmissionStatus.CARDINALITY_NOT_JUSTIFIED,
        "G7_CARDINALITY_BUDGET",
        "LOWER_CARDINALITY_ANALYSIS_MISSING",
    )


def test_pc10_same_epoch_writeback_cycle_is_blocker() -> None:
    cyclic_trace = (
        TemporalStep(11, 10, "resolve_input", False),
        TemporalStep(11, 20, "emit_event", False),
        TemporalStep(11, 30, "mutate_state", False),
        TemporalStep(11, 40, "resolve_input", True),
    )

    assert_failure(
        complete_proposal(temporal_trace=cyclic_trace),
        AdmissionStatus.TEMPORAL_CYCLE_VIOLATION,
        "NO_SAME_EPOCH_CAUSAL_CYCLE",
        "SAME_EPOCH_WRITEBACK_AFFECTS_CURRENT_RESULT",
    )


def test_pc10_same_epoch_mutation_without_emitted_event_is_not_the_forbidden_cycle() -> None:
    non_causal_trace = (
        TemporalStep(11, 10, "resolve_input", False),
        TemporalStep(11, 20, "mutate_state", False),
        TemporalStep(11, 30, "resolve_input", True),
    )

    result = validate_persistent_cause_proposal(complete_proposal(temporal_trace=non_causal_trace))

    assert result.status is AdmissionStatus.ADMITTED


def test_pc11_distinct_cause_ids_and_owners_coexist_without_universal_history_state() -> None:
    satiation = complete_proposal()
    disturbance = complete_proposal(
        cause_id="disturbance:spot:north-bank",
        semantic_kind="DisturbanceCause",
        canonical_owner="Spatial.DisturbanceOwner",
        bearer_identity="spot:north-bank",
        scope="pond:pond-1001",
        consumer_domains=("Spatial.LocalSupplyResolver",),
        lifecycle=replace(
            complete_proposal().lifecycle,
            reducer_ref="DisturbanceReducer.v1",
            decay_or_recovery_rule="decay_by_authoritative_active_time",
        ),
    )

    results = validate_persistent_cause_proposals((satiation, disturbance))

    assert [result.status for result in results] == [
        AdmissionStatus.ADMITTED,
        AdmissionStatus.ADMITTED,
    ]
    assert [result.cause_id for result in results] == [satiation.cause_id, disturbance.cause_id]
    assert satiation.canonical_owner != disturbance.canonical_owner


def test_pc12_existing_replayable_state_does_not_imply_admission() -> None:
    existing_state = FallbackSafetyState(debt=0.4, active_time_credited=90.0)
    proposal = PersistentCauseProposal.from_existing_state(
        cause_id="fallback-safety-existing-state",
        semantic_kind=type(existing_state).__name__,
        existing_state=existing_state,
    )

    result = validate_persistent_cause_proposal(proposal)

    assert result.status is not AdmissionStatus.ADMITTED
    assert "HISTORY_DIVERGENCE_NOT_ESTABLISHED" in result.reason_codes
    assert "LIFECYCLE_DECLARATION_MISSING" in result.reason_codes
    assert "REPLAYABLE_EXISTENCE_IS_NOT_ADMISSION" in result.reason_codes

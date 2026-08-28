from __future__ import annotations

from collections.abc import Iterable

from .model import (
    AdmissionResult,
    AdmissionStatus,
    MutationDeclaration,
    PersistentCauseProposal,
    TemporalStep,
)

G1_HISTORY_NECESSITY = "G1_HISTORY_NECESSITY"
G2_ACCEPTED_FORMATION_UPDATE_EVENT = "G2_ACCEPTED_FORMATION_UPDATE_EVENT"
G3_BEARER_IDENTITY_SCOPE = "G3_BEARER_IDENTITY_SCOPE"
G4_INDEPENDENT_LIFECYCLE = "G4_INDEPENDENT_LIFECYCLE"
G5_INDEPENDENT_CONSUMER_VALUE = "G5_INDEPENDENT_CONSUMER_VALUE"
G6_AUTHORITY_REPLAYABILITY = "G6_AUTHORITY_REPLAYABILITY"
G7_CARDINALITY_BUDGET = "G7_CARDINALITY_BUDGET"
EXACTLY_ONE_CONCRETE_OWNER = "EXACTLY_ONE_CONCRETE_OWNER"
CAUSE_NOT_DERIVED_EFFECT = "CAUSE_NOT_DERIVED_EFFECT"
NO_SAME_EPOCH_CAUSAL_CYCLE = "NO_SAME_EPOCH_CAUSAL_CYCLE"

_AUTHORITATIVE_MUTATION_SOURCES = frozenset({"authoritative_typed_event", "admitted_process"})

_STATUS_PRECEDENCE = (
    AdmissionStatus.REJECT_DERIVED_OR_CACHE,
    AdmissionStatus.OWNER_UNRESOLVED,
    AdmissionStatus.CAUSE_EFFECT_CONFUSION,
    AdmissionStatus.TEMPORAL_CYCLE_VIOLATION,
    AdmissionStatus.AUTHORITY_REPLAY_INCOMPLETE,
    AdmissionStatus.CARDINALITY_NOT_JUSTIFIED,
    AdmissionStatus.DECLARATION_INCOMPLETE,
)


class _Failures:
    def __init__(self) -> None:
        self.gates: list[str] = []
        self.reasons: list[str] = []
        self.statuses: set[AdmissionStatus] = set()

    def add(self, gate: str, reason: str, status: AdmissionStatus) -> None:
        if gate not in self.gates:
            self.gates.append(gate)
        if reason not in self.reasons:
            self.reasons.append(reason)
        self.statuses.add(status)

    def result(self, cause_id: str) -> AdmissionResult:
        status = AdmissionStatus.ADMITTED
        for candidate in _STATUS_PRECEDENCE:
            if candidate in self.statuses:
                status = candidate
                break
        return AdmissionResult(cause_id, status, tuple(self.gates), tuple(self.reasons))


def _is_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _mutation_source_is_authoritative(declaration: MutationDeclaration) -> bool:
    return (
        _is_non_empty_string(declaration.event_ref)
        and declaration.authority in _AUTHORITATIVE_MUTATION_SOURCES
    )


def _has_same_epoch_cycle(trace: tuple[TemporalStep, ...]) -> bool:
    ordered = sorted(trace, key=lambda step: (step.epoch, step.order))
    for index, step in enumerate(ordered):
        if step.operation != "mutate_state":
            continue
        earlier_in_epoch = tuple(
            earlier for earlier in ordered[:index] if earlier.epoch == step.epoch
        )
        resolve_seen = False
        event_seen_after_resolve = False
        for earlier in earlier_in_epoch:
            if earlier.operation == "resolve_input":
                resolve_seen = True
            elif earlier.operation == "emit_event" and resolve_seen:
                event_seen_after_resolve = True
        if not event_seen_after_resolve:
            continue
        later_in_epoch = ordered[index + 1 :]
        if any(
            later.epoch == step.epoch
            and later.operation == "resolve_input"
            and later.affects_current_result
            for later in later_in_epoch
        ):
            return True
    return False


def validate_persistent_cause_proposal(proposal: PersistentCauseProposal) -> AdmissionResult:
    """Evaluate the Current admission gates without implementing a state store."""
    failures = _Failures()

    proof = proposal.history_necessity_proof
    if (
        proof is None
        or not proof.same_present_inputs
        or not proof.different_admissible_histories
        or not proof.desired_future_outputs_differ
        or not _is_non_empty_string(proof.fixture_ref)
    ):
        failures.add(
            G1_HISTORY_NECESSITY,
            "HISTORY_DIVERGENCE_NOT_ESTABLISHED",
            AdmissionStatus.REJECT_DERIVED_OR_CACHE,
        )

    mutation_events = proposal.formation_events + proposal.update_events
    authoritative_events = tuple(
        event for event in mutation_events if _mutation_source_is_authoritative(event)
    )
    if not authoritative_events:
        failures.add(
            G2_ACCEPTED_FORMATION_UPDATE_EVENT,
            "AUTHORITATIVE_MUTATION_SOURCE_MISSING",
            AdmissionStatus.AUTHORITY_REPLAY_INCOMPLETE,
        )
    if len(authoritative_events) != len(mutation_events):
        failures.add(
            G2_ACCEPTED_FORMATION_UPDATE_EVENT,
            "UNAUTHORIZED_MUTATION_SOURCE_DECLARED",
            AdmissionStatus.AUTHORITY_REPLAY_INCOMPLETE,
        )
    if not proposal.formation_events:
        failures.add(
            G2_ACCEPTED_FORMATION_UPDATE_EVENT,
            "FORMATION_EVENT_DECLARATION_MISSING",
            AdmissionStatus.DECLARATION_INCOMPLETE,
        )
    if not proposal.update_events:
        failures.add(
            G2_ACCEPTED_FORMATION_UPDATE_EVENT,
            "UPDATE_EVENT_DECLARATION_MISSING",
            AdmissionStatus.DECLARATION_INCOMPLETE,
        )

    if not _is_non_empty_string(proposal.cause_id):
        failures.add(
            G3_BEARER_IDENTITY_SCOPE,
            "CAUSE_ID_MISSING",
            AdmissionStatus.DECLARATION_INCOMPLETE,
        )
    if not _is_non_empty_string(proposal.semantic_kind):
        failures.add(
            G3_BEARER_IDENTITY_SCOPE,
            "SEMANTIC_KIND_MISSING",
            AdmissionStatus.DECLARATION_INCOMPLETE,
        )
    if not _is_non_empty_string(proposal.bearer_identity):
        failures.add(
            G3_BEARER_IDENTITY_SCOPE,
            "BEARER_IDENTITY_MISSING",
            AdmissionStatus.DECLARATION_INCOMPLETE,
        )
    if not _is_non_empty_string(proposal.scope):
        failures.add(
            G3_BEARER_IDENTITY_SCOPE,
            "CAUSE_SCOPE_MISSING",
            AdmissionStatus.DECLARATION_INCOMPLETE,
        )

    owner = proposal.canonical_owner
    if not _is_non_empty_string(owner):
        failures.add(
            EXACTLY_ONE_CONCRETE_OWNER,
            "CANONICAL_OWNER_NOT_EXACTLY_ONE",
            AdmissionStatus.OWNER_UNRESOLVED,
        )

    lifecycle = proposal.lifecycle
    if lifecycle is None:
        failures.add(
            G4_INDEPENDENT_LIFECYCLE,
            "LIFECYCLE_DECLARATION_MISSING",
            AdmissionStatus.DECLARATION_INCOMPLETE,
        )
    else:
        lifecycle_requirements = (
            ("reducer_ref", "LIFECYCLE_REDUCER_MISSING"),
            ("logical_time_semantics", "LIFECYCLE_LOGICAL_TIME_MISSING"),
            ("decay_or_recovery_rule", "LIFECYCLE_DECAY_OR_RECOVERY_MISSING"),
            ("merge_or_stack_rule", "LIFECYCLE_MERGE_OR_STACK_MISSING"),
            ("reset_or_expiration_rule", "LIFECYCLE_RESET_OR_EXPIRATION_MISSING"),
            ("version_migration_invalidation", "LIFECYCLE_VERSION_POLICY_MISSING"),
        )
        for field_name, reason in lifecycle_requirements:
            if not _is_non_empty_string(getattr(lifecycle, field_name)):
                failures.add(
                    G4_INDEPENDENT_LIFECYCLE,
                    reason,
                    AdmissionStatus.DECLARATION_INCOMPLETE,
                )

    if not proposal.consumer_domains or not all(
        _is_non_empty_string(consumer) for consumer in proposal.consumer_domains
    ):
        failures.add(
            G5_INDEPENDENT_CONSUMER_VALUE,
            "INDEPENDENT_CONSUMER_MISSING",
            AdmissionStatus.REJECT_DERIVED_OR_CACHE,
        )

    replay = proposal.replay_contract
    if replay is None:
        failures.add(
            G6_AUTHORITY_REPLAYABILITY,
            "REPLAY_DECLARATION_MISSING",
            AdmissionStatus.AUTHORITY_REPLAY_INCOMPLETE,
        )
    else:
        if not _is_non_empty_string(replay.authoritative_source):
            failures.add(
                G6_AUTHORITY_REPLAYABILITY,
                "REPLAY_AUTHORITATIVE_SOURCE_MISSING",
                AdmissionStatus.AUTHORITY_REPLAY_INCOMPLETE,
            )
        if not replay.reconstructable_or_verifiable:
            failures.add(
                G6_AUTHORITY_REPLAYABILITY,
                "CAUSE_NOT_RECONSTRUCTABLE_OR_VERIFIABLE",
                AdmissionStatus.AUTHORITY_REPLAY_INCOMPLETE,
            )
        if not _is_non_empty_string(replay.checkpoint_or_event_lineage_ref):
            failures.add(
                G6_AUTHORITY_REPLAYABILITY,
                "REPLAY_LINEAGE_MISSING",
                AdmissionStatus.AUTHORITY_REPLAY_INCOMPLETE,
            )

    cardinality = proposal.cardinality
    if cardinality is None:
        failures.add(
            G7_CARDINALITY_BUDGET,
            "CARDINALITY_DECLARATION_MISSING",
            AdmissionStatus.CARDINALITY_NOT_JUSTIFIED,
        )
    else:
        if not _is_non_empty_string(cardinality.bearer_count_class):
            failures.add(
                G7_CARDINALITY_BUDGET,
                "BEARER_COUNT_CLASS_MISSING",
                AdmissionStatus.CARDINALITY_NOT_JUSTIFIED,
            )
        if not _is_non_empty_string(cardinality.retention_budget):
            failures.add(
                G7_CARDINALITY_BUDGET,
                "RETENTION_BUDGET_MISSING",
                AdmissionStatus.CARDINALITY_NOT_JUSTIFIED,
            )
        if cardinality.is_high_cardinality and (
            not cardinality.lower_cardinality_alternative_considered
            or not _is_non_empty_string(cardinality.lower_cardinality_rejection_reason)
        ):
            failures.add(
                G7_CARDINALITY_BUDGET,
                "LOWER_CARDINALITY_ANALYSIS_MISSING",
                AdmissionStatus.CARDINALITY_NOT_JUSTIFIED,
            )

    if not proposal.represents_underlying_cause:
        failures.add(
            CAUSE_NOT_DERIVED_EFFECT,
            "UNDERLYING_CAUSE_IDENTITY_NOT_ESTABLISHED",
            AdmissionStatus.CAUSE_EFFECT_CONFUSION,
        )

    if _has_same_epoch_cycle(proposal.temporal_trace):
        failures.add(
            NO_SAME_EPOCH_CAUSAL_CYCLE,
            "SAME_EPOCH_WRITEBACK_AFFECTS_CURRENT_RESULT",
            AdmissionStatus.TEMPORAL_CYCLE_VIOLATION,
        )

    return failures.result(proposal.cause_id)


def validate_persistent_cause_proposals(
    proposals: Iterable[PersistentCauseProposal],
) -> tuple[AdmissionResult, ...]:
    """Validate each concrete Cause independently; no universal HistoryState merge exists."""
    return tuple(validate_persistent_cause_proposal(proposal) for proposal in proposals)

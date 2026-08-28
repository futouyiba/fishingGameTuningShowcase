from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal

MutationAuthority = Literal[
    "authoritative_typed_event",
    "admitted_process",
    "client_click",
    "ui_action",
    "raw_packet_counter",
    "animation_callback",
]
TemporalOperation = Literal["resolve_input", "emit_event", "mutate_state"]


class AdmissionStatus(str, Enum):
    ADMITTED = "ADMITTED"
    REJECT_DERIVED_OR_CACHE = "REJECT_DERIVED_OR_CACHE"
    OWNER_UNRESOLVED = "OWNER_UNRESOLVED"
    DECLARATION_INCOMPLETE = "DECLARATION_INCOMPLETE"
    AUTHORITY_REPLAY_INCOMPLETE = "AUTHORITY_REPLAY_INCOMPLETE"
    CARDINALITY_NOT_JUSTIFIED = "CARDINALITY_NOT_JUSTIFIED"
    TEMPORAL_CYCLE_VIOLATION = "TEMPORAL_CYCLE_VIOLATION"
    CAUSE_EFFECT_CONFUSION = "CAUSE_EFFECT_CONFUSION"


@dataclass(frozen=True)
class HistoryNecessityProof:
    same_present_inputs: bool
    different_admissible_histories: bool
    desired_future_outputs_differ: bool
    fixture_ref: str | None


@dataclass(frozen=True)
class MutationDeclaration:
    event_ref: str
    authority: MutationAuthority


@dataclass(frozen=True)
class LifecycleDeclaration:
    reducer_ref: str | None
    logical_time_semantics: str | None
    decay_or_recovery_rule: str | None
    merge_or_stack_rule: str | None
    reset_or_expiration_rule: str | None
    version_migration_invalidation: str | None


@dataclass(frozen=True)
class ReplayDeclaration:
    authoritative_source: str | None
    reconstructable_or_verifiable: bool
    checkpoint_or_event_lineage_ref: str | None


@dataclass(frozen=True)
class CardinalityDeclaration:
    bearer_count_class: str | None
    retention_budget: str | None
    is_high_cardinality: bool
    lower_cardinality_alternative_considered: bool
    lower_cardinality_rejection_reason: str | None


@dataclass(frozen=True)
class TemporalStep:
    epoch: int
    order: int
    operation: TemporalOperation
    affects_current_result: bool


@dataclass(frozen=True)
class PersistentCauseProposal:
    cause_id: str
    semantic_kind: str
    canonical_owner: str | tuple[str, ...] | None
    bearer_identity: str | None
    scope: str | None

    history_necessity_proof: HistoryNecessityProof | None
    formation_events: tuple[MutationDeclaration, ...]
    update_events: tuple[MutationDeclaration, ...]
    consumer_domains: tuple[str, ...]

    lifecycle: LifecycleDeclaration | None
    replay_contract: ReplayDeclaration | None
    cardinality: CardinalityDeclaration | None

    represents_underlying_cause: bool
    temporal_trace: tuple[TemporalStep, ...] = ()
    existing_state_type: str | None = None

    @classmethod
    def from_existing_state(
        cls,
        *,
        cause_id: str,
        semantic_kind: str,
        existing_state: Any,
    ) -> PersistentCauseProposal:
        """Represent existing state without treating its existence as admission evidence."""
        return cls(
            cause_id=cause_id,
            semantic_kind=semantic_kind,
            canonical_owner=None,
            bearer_identity=None,
            scope=None,
            history_necessity_proof=None,
            formation_events=(),
            update_events=(),
            consumer_domains=(),
            lifecycle=None,
            replay_contract=None,
            cardinality=None,
            represents_underlying_cause=False,
            existing_state_type=type(existing_state).__name__,
        )


@dataclass(frozen=True)
class AdmissionResult:
    cause_id: str
    status: AdmissionStatus
    failed_gates: tuple[str, ...]
    reason_codes: tuple[str, ...]

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from math import isclose, isfinite
from typing import Literal

MeasureKind = Literal["point", "time", "traversal"]
OccurrenceMode = Literal["renewal", "once_per_scope"]


@dataclass(frozen=True)
class MeasureSpan:
    """Fixture-level, already-semantic measure span.

    `formation_mass` is the accepted mass for the slot's Formation measure.
    `traversal_mass` is optional Evaluation traversal mass. Time mass is derived
    from logical duration. Linear interpolation inside a span is a Fixture-K
    encoding convention only; it is not a Production sampling contract.
    """

    span_id: str
    semantic_scope_ref: str
    source_scope_id: str
    measure_ref: str
    start_time: float
    end_time: float
    formation_mass: float
    phase: str | None = None
    traversal_mass: float | None = None

    def __post_init__(self) -> None:
        if (
            not self.span_id
            or not self.semantic_scope_ref
            or not self.source_scope_id
            or not self.measure_ref
        ):
            raise ValueError("measure span identity fields must be non-empty")
        if not all(isfinite(v) for v in (self.start_time, self.end_time, self.formation_mass)):
            raise ValueError("measure span numeric fields must be finite")
        if self.end_time <= self.start_time:
            raise ValueError("measure span end_time must be > start_time")
        if self.formation_mass < 0:
            raise ValueError("formation_mass must be >= 0")
        if self.traversal_mass is not None:
            if not isfinite(self.traversal_mass) or self.traversal_mass < 0:
                raise ValueError("traversal_mass must be finite and >= 0")


@dataclass(frozen=True)
class SemanticEvent:
    event_id: str
    event_ref: str
    semantic_scope_ref: str
    source_scope_id: str
    logical_time: float
    phase: str | None = None

    def __post_init__(self) -> None:
        if (
            not self.event_id
            or not self.event_ref
            or not self.semantic_scope_ref
            or not self.source_scope_id
        ):
            raise ValueError("semantic event identity fields must be non-empty")
        if not isfinite(self.logical_time):
            raise ValueError("semantic event logical_time must be finite")


@dataclass(frozen=True)
class ChannelClose:
    logical_time: float

    def __post_init__(self) -> None:
        if not isfinite(self.logical_time):
            raise ValueError("channel close logical_time must be finite")


SemanticSourceItem = MeasureSpan | SemanticEvent | ChannelClose


@dataclass(frozen=True)
class EvaluationPolicy:
    evaluation_policy_id: str
    support_scope_ref: Literal["formation_interval", "event_point"]
    base_measure_ref: MeasureKind
    phase_mask_ref: str | None = None
    context_scope_ref: Literal["antecedent_same_source_scope"] | None = None
    scope_clip_policy_ref: str | None = None

    def __post_init__(self) -> None:
        if not self.evaluation_policy_id:
            raise ValueError("evaluation_policy_id must be non-empty")
        if self.support_scope_ref == "event_point" and self.base_measure_ref != "point":
            raise ValueError("event_point evaluation requires point base measure")
        if self.support_scope_ref == "formation_interval" and self.base_measure_ref == "point":
            raise ValueError("formation_interval evaluation cannot use point base measure")


@dataclass(frozen=True)
class ProgressSlot:
    slot_id: str
    opportunity_meaning: str
    measure_ref: str
    semantic_scope_ref: str
    threshold: float
    occurrence_mode: OccurrenceMode
    evaluation_policy_id: str

    def __post_init__(self) -> None:
        if (
            not self.slot_id
            or not self.opportunity_meaning
            or not self.measure_ref
            or not self.semantic_scope_ref
        ):
            raise ValueError("progress slot identity fields must be non-empty")
        if not isfinite(self.threshold) or self.threshold <= 0:
            raise ValueError("progress threshold must be finite and > 0")
        if not self.evaluation_policy_id:
            raise ValueError("evaluation_policy_id must be non-empty")


@dataclass(frozen=True)
class EventSlot:
    slot_id: str
    opportunity_meaning: str
    event_ref: str
    semantic_scope_ref: str
    evaluation_policy_id: str

    def __post_init__(self) -> None:
        if (
            not self.slot_id
            or not self.opportunity_meaning
            or not self.event_ref
            or not self.semantic_scope_ref
        ):
            raise ValueError("event slot identity fields must be non-empty")
        if not self.evaluation_policy_id:
            raise ValueError("evaluation_policy_id must be non-empty")


OpportunitySlot = ProgressSlot | EventSlot


@dataclass(frozen=True)
class FormationPolicy:
    slots: tuple[OpportunitySlot, ...]

    def __post_init__(self) -> None:
        slot_ids = [slot.slot_id for slot in self.slots]
        if len(slot_ids) != len(set(slot_ids)):
            raise ValueError("slot_id must be unique within a FormationPolicy")


@dataclass(frozen=True)
class WeightedSupport:
    support_id: str
    source_scope_id: str
    start_time: float
    end_time: float
    measure_mass: float
    alpha: float
    phase: str | None = None


@dataclass(frozen=True)
class ContextRef:
    source_item_id: str
    source_scope_id: str
    start_time: float
    end_time: float


@dataclass(frozen=True)
class OpportunityTraceItem:
    opportunity_seq: int
    slot_id: str
    opportunity_meaning: str
    occurrence_logical_time: float
    source_scope_id: str
    evaluation_policy_id: str
    weighted_support: tuple[WeightedSupport, ...]
    context_refs: tuple[ContextRef, ...]


@dataclass(frozen=True)
class OpportunitySemanticFixture:
    active_channel_ref: str
    formation_policy: FormationPolicy
    evaluation_policies: Mapping[str, EvaluationPolicy]
    semantic_source_trace: tuple[SemanticSourceItem, ...]
    phase_masks: Mapping[str, frozenset[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.active_channel_ref:
            raise ValueError("active_channel_ref must be non-empty")
        for policy in self.evaluation_policies.values():
            if policy.scope_clip_policy_ref is not None:
                raise NotImplementedError(
                    "scope_clip_policy_ref is not implemented in Reference Adapter V1"
                )
            if policy.phase_mask_ref is not None and policy.phase_mask_ref not in self.phase_masks:
                raise ValueError(f"missing phase mask {policy.phase_mask_ref!r}")
        for slot in self.formation_policy.slots:
            if slot.evaluation_policy_id not in self.evaluation_policies:
                raise ValueError(
                    f"slot {slot.slot_id!r} references missing evaluation policy "
                    f"{slot.evaluation_policy_id!r}"
                )


@dataclass(frozen=True)
class SupportDomainValue:
    local_species_intensity: float
    capture_retention: float

    def __post_init__(self) -> None:
        for value in (self.local_species_intensity, self.capture_retention):
            if not isfinite(value) or value < 0:
                raise ValueError("support domain values must be finite and >= 0")


@dataclass(frozen=True)
class ResolvedOpportunityWeights:
    weights: dict[str, float]


@dataclass(frozen=True)
class _OccurrenceDraft:
    slot: OpportunitySlot
    slot_order: int
    logical_time: float
    source_scope_id: str
    interval_start_time: float
    source_event: SemanticEvent | None = None


@dataclass
class _ProgressScopeState:
    consumed_mass: float = 0.0
    interval_start_time: float | None = None
    emitted_once: bool = False


def resolve_opportunity_semantic_fixture(
    fixture: OpportunitySemanticFixture,
) -> tuple[OpportunityTraceItem, ...]:
    """Resolve semantic source trace into deterministic ordered opportunities.

    The adapter starts from already-semantic source evidence. It deliberately
    does not recognize raw gestures, physics callbacks, or fish preference.
    """

    close_time = _first_channel_close_time(fixture.semantic_source_trace)
    measure_spans = sorted(
        (item for item in fixture.semantic_source_trace if isinstance(item, MeasureSpan)),
        key=lambda span: (span.start_time, span.end_time, span.span_id),
    )
    semantic_events = sorted(
        (item for item in fixture.semantic_source_trace if isinstance(item, SemanticEvent)),
        key=lambda event: (event.logical_time, event.event_id),
    )

    drafts: list[_OccurrenceDraft] = []
    for slot_order, slot in enumerate(fixture.formation_policy.slots):
        if isinstance(slot, ProgressSlot):
            drafts.extend(_resolve_progress_slot(slot, slot_order, measure_spans, close_time))
        else:
            drafts.extend(_resolve_event_slot(slot, slot_order, semantic_events, close_time))

    drafts.sort(key=lambda draft: (draft.logical_time, draft.slot_order))
    trace: list[OpportunityTraceItem] = []
    for seq, draft in enumerate(drafts, start=1):
        policy = fixture.evaluation_policies[draft.slot.evaluation_policy_id]
        weighted_support = resolve_evaluation_support(
            draft, policy, measure_spans, fixture.phase_masks
        )
        context_refs = _resolve_context_refs(draft, policy, measure_spans)
        trace.append(
            OpportunityTraceItem(
                opportunity_seq=seq,
                slot_id=draft.slot.slot_id,
                opportunity_meaning=draft.slot.opportunity_meaning,
                occurrence_logical_time=draft.logical_time,
                source_scope_id=draft.source_scope_id,
                evaluation_policy_id=policy.evaluation_policy_id,
                weighted_support=weighted_support,
                context_refs=context_refs,
            )
        )
    return tuple(trace)


def _resolve_progress_slot(
    slot: ProgressSlot,
    slot_order: int,
    spans: Sequence[MeasureSpan],
    close_time: float | None,
) -> list[_OccurrenceDraft]:
    state_by_scope: dict[str, _ProgressScopeState] = {}
    drafts: list[_OccurrenceDraft] = []

    for span in spans:
        if (
            span.measure_ref != slot.measure_ref
            or span.semantic_scope_ref != slot.semantic_scope_ref
        ):
            continue
        if close_time is not None and span.start_time >= close_time:
            continue

        usable_end = span.end_time if close_time is None else min(span.end_time, close_time)
        if usable_end <= span.start_time:
            continue
        usable_fraction = (usable_end - span.start_time) / (span.end_time - span.start_time)
        remaining_span_mass = span.formation_mass * usable_fraction
        span_cursor_time = span.start_time

        state = state_by_scope.setdefault(span.source_scope_id, _ProgressScopeState())
        if state.interval_start_time is None:
            state.interval_start_time = span.start_time
        if slot.occurrence_mode == "once_per_scope" and state.emitted_once:
            continue

        while remaining_span_mass > 0:
            needed = slot.threshold - state.consumed_mass
            if remaining_span_mass + 1e-12 < needed:
                state.consumed_mass += remaining_span_mass
                remaining_span_mass = 0.0
                break

            if span.formation_mass == 0:
                break
            fraction_of_full_span = needed / span.formation_mass
            crossing_time = span_cursor_time + fraction_of_full_span * (
                span.end_time - span.start_time
            )
            crossing_time = min(crossing_time, usable_end)

            drafts.append(
                _OccurrenceDraft(
                    slot=slot,
                    slot_order=slot_order,
                    logical_time=crossing_time,
                    source_scope_id=span.source_scope_id,
                    interval_start_time=state.interval_start_time,
                )
            )
            remaining_span_mass -= needed
            state.consumed_mass = 0.0
            state.interval_start_time = crossing_time
            span_cursor_time = crossing_time

            if slot.occurrence_mode == "once_per_scope":
                state.emitted_once = True
                break

    return drafts


def _resolve_event_slot(
    slot: EventSlot,
    slot_order: int,
    events: Sequence[SemanticEvent],
    close_time: float | None,
) -> list[_OccurrenceDraft]:
    drafts: list[_OccurrenceDraft] = []
    consumed_event_ids: set[str] = set()
    for event in events:
        if event.event_ref != slot.event_ref or event.semantic_scope_ref != slot.semantic_scope_ref:
            continue
        if close_time is not None and event.logical_time >= close_time:
            continue
        if event.event_id in consumed_event_ids:
            continue
        consumed_event_ids.add(event.event_id)
        drafts.append(
            _OccurrenceDraft(
                slot=slot,
                slot_order=slot_order,
                logical_time=event.logical_time,
                source_scope_id=event.source_scope_id,
                interval_start_time=event.logical_time,
                source_event=event,
            )
        )
    return drafts


def resolve_evaluation_support(
    draft: _OccurrenceDraft,
    policy: EvaluationPolicy,
    spans: Sequence[MeasureSpan],
    phase_masks: Mapping[str, frozenset[str]],
) -> tuple[WeightedSupport, ...]:
    if policy.support_scope_ref == "event_point":
        event = draft.source_event
        support_id = (
            f"event:{event.event_id}"
            if event is not None
            else f"point:{draft.slot.slot_id}:{draft.logical_time:.9f}"
        )
        phase = event.phase if event is not None else None
        return (
            WeightedSupport(
                support_id=support_id,
                source_scope_id=draft.source_scope_id,
                start_time=draft.logical_time,
                end_time=draft.logical_time,
                measure_mass=1.0,
                alpha=1.0,
                phase=phase,
            ),
        )

    pieces: list[tuple[str, str, float, float, float, str | None]] = []
    for span in spans:
        if span.source_scope_id != draft.source_scope_id:
            continue
        overlap_start = max(span.start_time, draft.interval_start_time)
        overlap_end = min(span.end_time, draft.logical_time)
        if overlap_end <= overlap_start:
            continue
        if (
            policy.phase_mask_ref is not None
            and span.phase not in phase_masks[policy.phase_mask_ref]
        ):
            continue

        overlap_fraction = (overlap_end - overlap_start) / (span.end_time - span.start_time)
        if policy.base_measure_ref == "time":
            mass = overlap_end - overlap_start
        elif policy.base_measure_ref == "traversal":
            if span.traversal_mass is None:
                raise ValueError(
                    f"span {span.span_id!r} lacks traversal_mass required by policy "
                    f"{policy.evaluation_policy_id!r}"
                )
            mass = span.traversal_mass * overlap_fraction
        else:
            raise AssertionError("point measure handled by event_point branch")

        if mass > 0:
            pieces.append(
                (
                    span.span_id,
                    span.source_scope_id,
                    overlap_start,
                    overlap_end,
                    mass,
                    span.phase,
                )
            )

    total_mass = sum(piece[4] for piece in pieces)
    if total_mass <= 0:
        raise ValueError(
            f"evaluation policy {policy.evaluation_policy_id!r} produced no positive support mass"
        )

    weighted = tuple(
        WeightedSupport(
            support_id=piece[0],
            source_scope_id=piece[1],
            start_time=piece[2],
            end_time=piece[3],
            measure_mass=piece[4],
            alpha=piece[4] / total_mass,
            phase=piece[5],
        )
        for piece in pieces
    )
    if not isclose(sum(support.alpha for support in weighted), 1.0, rel_tol=0, abs_tol=1e-12):
        raise AssertionError("evaluation support alpha must normalize to 1")
    return weighted


def _resolve_context_refs(
    draft: _OccurrenceDraft,
    policy: EvaluationPolicy,
    spans: Sequence[MeasureSpan],
) -> tuple[ContextRef, ...]:
    if policy.context_scope_ref is None:
        return ()
    refs: list[ContextRef] = []
    for span in spans:
        if span.source_scope_id != draft.source_scope_id:
            continue
        context_start = (
            span.start_time if draft.source_event is not None else draft.interval_start_time
        )
        start = max(span.start_time, context_start)
        end = min(span.end_time, draft.logical_time)
        if end <= start:
            continue
        refs.append(
            ContextRef(
                source_item_id=span.span_id,
                source_scope_id=span.source_scope_id,
                start_time=start,
                end_time=end,
            )
        )
    return tuple(refs)


def resolve_opportunity_candidate_weights(
    trace_item: OpportunityTraceItem,
    support_domain_stub: Mapping[str, Mapping[str, SupportDomainValue]],
) -> ResolvedOpportunityWeights:
    """Fixture-only Join-Before-Reduce bridge into the existing TruePool kernel."""

    positive_support = [support for support in trace_item.weighted_support if support.alpha > 0]
    if not positive_support:
        raise ValueError("opportunity has no positive weighted support")

    species_sets: list[set[str]] = []
    for support in positive_support:
        if support.support_id not in support_domain_stub:
            raise ValueError(f"missing support-domain stub for {support.support_id!r}")
        species_sets.append(set(support_domain_stub[support.support_id]))
    expected_species = species_sets[0]
    if any(species_set != expected_species for species_set in species_sets[1:]):
        raise ValueError("support-domain species coverage differs across positive support")

    weights: dict[str, float] = {}
    for species_id in sorted(expected_species):
        weight = 0.0
        for support in positive_support:
            value = support_domain_stub[support.support_id][species_id]
            weight += support.alpha * value.local_species_intensity * value.capture_retention
        weights[species_id] = weight
    return ResolvedOpportunityWeights(weights=weights)


def _first_channel_close_time(trace: Sequence[SemanticSourceItem]) -> float | None:
    close_times = [item.logical_time for item in trace if isinstance(item, ChannelClose)]
    return min(close_times) if close_times else None

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from json import dumps
from math import isfinite


@dataclass(frozen=True)
class CauseEvent:
    logical_event_id: int
    event_kind: str
    delta: float

    def __post_init__(self) -> None:
        if self.logical_event_id < 0:
            raise ValueError("logical_event_id must be >= 0")
        if not self.event_kind:
            raise ValueError("event_kind must be a non-empty string")
        if not isfinite(self.delta):
            raise ValueError("delta must be finite")


@dataclass(frozen=True)
class CauseReplayResult:
    cause_id: str
    reducer_ref: str
    final_value: float
    applied_event_ids: tuple[int, ...]
    semantic_digest: str
    transport_chunk_count: int


def _canonical_events(chunks: tuple[tuple[CauseEvent, ...], ...]) -> tuple[CauseEvent, ...]:
    by_logical_id: dict[int, CauseEvent] = {}
    ordered_events: list[CauseEvent] = []
    for chunk in chunks:
        for event in chunk:
            prior = by_logical_id.get(event.logical_event_id)
            if prior is not None:
                same_payload = prior.event_kind == event.event_kind and (
                    prior.delta == event.delta or (prior.delta == 0.0 and event.delta == 0.0)
                )
                if not same_payload:
                    raise ValueError(
                        f"logical event {event.logical_event_id} has conflicting replay payloads"
                    )
                continue
            canonical_delta = 0.0 if event.delta == 0.0 else event.delta
            canonical_event = CauseEvent(
                logical_event_id=event.logical_event_id,
                event_kind=event.event_kind,
                delta=canonical_delta,
            )
            by_logical_id[event.logical_event_id] = canonical_event
            ordered_events.append(canonical_event)
    return tuple(ordered_events)


def _replay(
    cause_id: str,
    reducer_ref: str,
    chunks: tuple[tuple[CauseEvent, ...], ...],
) -> CauseReplayResult:
    if not cause_id:
        raise ValueError("cause_id must be a non-empty string")
    if not reducer_ref:
        raise ValueError("reducer_ref must be a non-empty string")

    events = _canonical_events(chunks)
    value = 0.0
    lineage: list[dict[str, object]] = []
    for event in events:
        value = max(0.0, value + event.delta)
        lineage.append(
            {
                "delta": event.delta,
                "eventKind": event.event_kind,
                "logicalEventId": event.logical_event_id,
            }
        )

    payload = dumps(
        {
            "causeId": cause_id,
            "finalValue": value,
            "lineage": lineage,
            "reducerRef": reducer_ref,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return CauseReplayResult(
        cause_id=cause_id,
        reducer_ref=reducer_ref,
        final_value=value,
        applied_event_ids=tuple(event.logical_event_id for event in events),
        semantic_digest=sha256(payload).hexdigest(),
        transport_chunk_count=len(chunks),
    )


def replay_cause_events_stepwise(
    cause_id: str,
    reducer_ref: str,
    events: tuple[CauseEvent, ...],
) -> CauseReplayResult:
    return _replay(cause_id, reducer_ref, tuple((event,) for event in events))


def replay_cause_events_batch(
    cause_id: str,
    reducer_ref: str,
    event_chunks: tuple[tuple[CauseEvent, ...], ...],
) -> CauseReplayResult:
    return _replay(cause_id, reducer_ref, event_chunks)

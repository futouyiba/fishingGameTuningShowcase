from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from .errors import ContractViolation


@dataclass(frozen=True)
class ResolvedBehavioralContextSurface:
    global_availability: float
    active_behavioral_states: tuple[str, ...]
    motivation_profile: Any
    enabled_response_modes: tuple[str, ...]


@dataclass(frozen=True)
class CaptureRuntimeSurface:
    capture_retention: float
    has_eligible_response_mode: bool

    @property
    def effective_capture(self) -> float:
        return self.capture_retention if self.has_eligible_response_mode else 0.0


def _required(packet: Mapping[str, Any], field: str) -> Any:
    if field not in packet:
        raise ContractViolation("PRODUCER_MISSING_REQUIRED_FIELD", field)
    return packet[field]


def derive_has_eligible_response_mode(
    mode_responses: Iterable[Mapping[str, Any]],
) -> bool:
    """Derive the Capture packet gate from mode-local eligibility only."""
    return any(bool(_required(response, "modeEligible")) for response in mode_responses)


def read_readiness_public_surface(
    packet: Mapping[str, Any],
) -> ResolvedBehavioralContextSurface:
    """Consume only the public Readiness-to-downstream contract."""
    return ResolvedBehavioralContextSurface(
        global_availability=float(_required(packet, "globalAvailability")),
        active_behavioral_states=tuple(_required(packet, "activeBehavioralStates")),
        motivation_profile=_required(packet, "motivationProfile"),
        enabled_response_modes=tuple(_required(packet, "enabledResponseModes")),
    )


def read_capture_runtime_surface(packet: Mapping[str, Any]) -> CaptureRuntimeSurface:
    """Consume only Current runtime-required fields from CaptureResponsePacket."""
    retention = float(_required(packet, "captureRetention"))
    has_eligible_response_mode = bool(_required(packet, "hasEligibleResponseMode"))
    if not 0.0 <= retention <= 1.0:
        raise ValueError("captureRetention must be in [0, 1]")
    return CaptureRuntimeSurface(
        capture_retention=retention,
        has_eligible_response_mode=has_eligible_response_mode,
    )

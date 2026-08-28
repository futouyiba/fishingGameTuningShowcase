from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from math import isfinite
from typing import Any

from .errors import ContractViolation


@dataclass(frozen=True)
class ResolvedBehavioralContextSurface:
    """Public Readiness-to-downstream contract (Interaction consumes this).

    `globalAvailability` is not part of the Current public surface: Candidate
    Weight no longer requires a mandatory Readiness scalar, and optional
    cross-mode behavioral retention is projected by Interaction into the
    CaptureResponsePacket instead.
    """

    active_behavioral_states: tuple[str, ...]
    motivation_profile: Any
    enabled_response_modes: tuple[str, ...]


@dataclass(frozen=True)
class CaptureRuntimeSurface:
    """Current runtime-required fields from CaptureResponsePacket.

    `has_eligible_response_mode` is typed zero / policy-guard / Explain
    metadata only; it is not a multiplier and must not re-enter arithmetic.
    """

    capture_retention: float
    has_eligible_response_mode: bool


@dataclass(frozen=True)
class LocalSpeciesIntensitySurface:
    """Spatial Owner output consumed by the Candidate numeric surface.

    `local_species_intensity` is already resolved from Ambient B/P/E stages
    plus the dynamic aggregation snapshot by the Spatial Owner. The optional
    fields are Explain/provenance metadata and never participate in arithmetic.
    """

    local_species_intensity: float
    baked_semantic_stages: frozenset[str] | None = None
    aggregation_context_ref: str | None = None


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
    if retention > 0.0 and not has_eligible_response_mode:
        raise ContractViolation(
            "CAPTURE_PACKET_INCONSISTENT",
            "positive captureRetention requires an eligible response mode; the "
            "Interaction Owner must project no-eligible-mode as typed zero retention",
        )
    return CaptureRuntimeSurface(
        capture_retention=retention,
        has_eligible_response_mode=has_eligible_response_mode,
    )


def read_local_species_intensity_surface(
    packet: Mapping[str, Any],
) -> LocalSpeciesIntensitySurface:
    """Consume only the Spatial Owner's resolved local intensity output."""
    intensity = float(_required(packet, "localSpeciesIntensity"))
    if not isfinite(intensity) or intensity < 0:
        raise ValueError("localSpeciesIntensity must be finite and >= 0")

    baked_raw = packet.get("bakedSemanticStages")
    baked_stages = None if baked_raw is None else frozenset(baked_raw)
    aggregation_context_ref = packet.get("aggregationContextRef")
    if aggregation_context_ref is not None and not isinstance(aggregation_context_ref, str):
        raise ValueError("aggregationContextRef must be a string when provided")
    return LocalSpeciesIntensitySurface(
        local_species_intensity=intensity,
        baked_semantic_stages=baked_stages,
        aggregation_context_ref=aggregation_context_ref,
    )

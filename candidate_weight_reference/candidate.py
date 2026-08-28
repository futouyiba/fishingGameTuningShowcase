"""Current Candidate numeric consumer.

The Current contract shrinks Candidate arithmetic to exactly two
Owner-resolved inputs:

    W_i = localSpeciesIntensity_i * captureRetention_i

The intensity arrives already resolved by the Spatial Owner (compiled
Ambient stages plus the dynamic local snapshot); the retention arrives
already resolved by the Interaction Owner as the CaptureResponsePacket
runtime surface. Upstream semantics have no numeric hook here: this module
must not re-read, re-derive, or re-settle any upstream Cause.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite

from .contracts import CaptureRuntimeSurface, LocalSpeciesIntensitySurface


@dataclass(frozen=True)
class CandidateWeightInputs:
    """The complete Current Candidate numeric input surface."""

    local_species_intensity: float
    capture_retention: float

    def __post_init__(self) -> None:
        intensity = self.local_species_intensity
        retention = self.capture_retention
        if not isfinite(intensity) or intensity < 0:
            raise ValueError("local_species_intensity must be finite and >= 0")
        if not isfinite(retention) or not 0.0 <= retention <= 1.0:
            raise ValueError("capture_retention must be finite and in [0, 1]")


def build_candidate_inputs(
    spatial: LocalSpeciesIntensitySurface,
    capture: CaptureRuntimeSurface,
) -> CandidateWeightInputs:
    """Assemble the Candidate numeric input from the two Owner surfaces."""
    return CandidateWeightInputs(
        local_species_intensity=spatial.local_species_intensity,
        capture_retention=capture.capture_retention,
    )


def calculate_candidate_weight(inputs: CandidateWeightInputs) -> float:
    """Current canonical Candidate weight: ``W = L x C`` with no other multiplier."""
    return inputs.local_species_intensity * inputs.capture_retention


def resolve_candidate_weights(
    species_inputs: Mapping[str, CandidateWeightInputs],
) -> dict[str, float]:
    """Materialize the per-species W vector for the shared TrueRoll kernel."""
    return {
        species_id: calculate_candidate_weight(inputs)
        for species_id, inputs in species_inputs.items()
    }

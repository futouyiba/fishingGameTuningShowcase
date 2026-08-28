"""Resolved-Scalar Native Retention projection.

Candidate Current (v5) closes the arbitrary Candidate-level Combine:
the Canonical Candidate Native Join is the TypedNativeRetentionJoin

    Spatial Native Supply Measure dM_i(s,t)
    x Interaction CaptureRetention C_i(s,p,t)
    -> retained Native Candidate measure dQ_i = C_i * dM_i
    -> Opportunity Reduce -> W_i^opp

For already-resolved, aligned, scalarized support representation its
canonical numeric branch is

    q_i,j = L_i,j x C_i,j
    W_i^opp = sum_j alpha_j * q_i,j

This module implements only that resolved-scalar numeric projection.
It does not implement or claim the full typed Candidate resolution
transaction: terminal TypedZero semantics, Unknown / Unsupported
handling, input-necessity authority, the ``0 x Unknown`` prohibition,
``CandidateResolutionResult`` / ``NativeCandidateSnapshot``
completeness, and the relational Candidate Source Envelope all stay
outside this scalar helper with their own Owners.

The intensity arrives already resolved by the Spatial Owner (compiled
Ambient stages plus the dynamic local snapshot); the retention arrives
already resolved by the Interaction Owner as the CaptureResponsePacket
runtime surface. Upstream semantics have no numeric hook here: this
module must not re-read, re-derive, or re-settle any upstream Cause.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite

from .contracts import CaptureRuntimeSurface, LocalSpeciesIntensitySurface


@dataclass(frozen=True)
class CandidateWeightInputs:
    """Resolved-scalar inputs to the TypedNativeRetentionJoin numeric branch.

    Exactly two arithmetic fields; readiness, aggregation, global
    availability, hard gates and any other upstream factor cannot be
    expressed here. Typed zero / Unknown / input necessity / snapshot
    completeness are outside this scalar surface.
    """

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
    """Assemble the resolved-scalar Join input from the two Owner surfaces."""
    return CandidateWeightInputs(
        local_species_intensity=spatial.local_species_intensity,
        capture_retention=capture.capture_retention,
    )


def calculate_multiplicative_candidate_weight(inputs: CandidateWeightInputs) -> float:
    """Resolved-scalar numeric branch of canonical TypedNativeRetentionJoin.

    Implements ``q = L x C`` for inputs already resolved numeric.
    Numeric zero alone does not establish terminality: typed zero /
    Unknown / input necessity / snapshot completeness are outside this
    scalar helper and stay with their Owners.
    """
    return inputs.local_species_intensity * inputs.capture_retention


def resolve_multiplicative_candidate_weights(
    species_inputs: Mapping[str, CandidateWeightInputs],
) -> dict[str, float]:
    """Materialize the per-species W vector for the shared TrueRoll kernel.

    Resolved-Scalar Native Retention projection only; the typed
    Candidate resolution transaction (``CandidateResolutionResult`` /
    ``NativeCandidateSnapshot``) is not implemented here.
    """
    return {
        species_id: calculate_multiplicative_candidate_weight(inputs)
        for species_id, inputs in species_inputs.items()
    }

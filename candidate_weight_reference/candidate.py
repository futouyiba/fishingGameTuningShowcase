"""Admitted multiplicative Candidate weight specialization.

The canonical Candidate contract (Candidate Resolver / Assembly Current)
composes Owner-resolved support outputs as

    q_i,j = Combine(L_i,j, C_i,j)
    W_i^opp = sum_j alpha_j * q_i,j

with support-wise Join before Reduce. The concrete ``Combine(L, C)``
operator remains upstream authority and is deliberately Open; it is not
frozen to multiplication, and this module does not define it.

This module implements the currently admitted Production / Reference
Harness specialization ``Combine_prod(L, C) = L x C``. Its complete
numeric input surface is exactly the two Owner-resolved fields below:
the intensity arrives already resolved by the Spatial Owner (compiled
Ambient stages plus the dynamic local snapshot) and the retention
arrives already resolved by the Interaction Owner as the
CaptureResponsePacket runtime surface. Upstream semantics have no
numeric hook here: this module must not re-read, re-derive, or
re-settle any upstream Cause, and this specialization is an
implementation fact of the Runtime projection — it must not be read
back as canonical Candidate semantics.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite

from .contracts import CaptureRuntimeSurface, LocalSpeciesIntensitySurface


@dataclass(frozen=True)
class CandidateWeightInputs:
    """Numeric inputs to the admitted multiplicative specialization.

    This is the complete numeric consumer surface for
    ``Combine_prod(L, C) = L x C`` only. It is not the canonical
    Candidate semantic surface, and it cannot express readiness,
    aggregation, global availability, hard gates or any other upstream
    factor as a multiplier.
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
    """Assemble the multiplicative specialization input from the two Owner surfaces."""
    return CandidateWeightInputs(
        local_species_intensity=spatial.local_species_intensity,
        capture_retention=capture.capture_retention,
    )


def calculate_multiplicative_candidate_weight(inputs: CandidateWeightInputs) -> float:
    """Admitted Production specialization ``Combine_prod(L, C) = L x C``.

    The canonical ``Combine(L, C)`` operator stays upstream authority
    (Open); this function verifies the multiplicative Runtime
    projection only and carries no Candidate semantic authority.
    """
    return inputs.local_species_intensity * inputs.capture_retention


def resolve_multiplicative_candidate_weights(
    species_inputs: Mapping[str, CandidateWeightInputs],
) -> dict[str, float]:
    """Materialize the per-species W vector for the shared TrueRoll kernel.

    The W vector is produced under the admitted multiplicative
    specialization only; it is the Runtime projection consumed by the
    fixed-pan kernel, not the canonical Candidate semantic surface.
    """
    return {
        species_id: calculate_multiplicative_candidate_weight(inputs)
        for species_id, inputs in species_inputs.items()
    }

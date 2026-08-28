from __future__ import annotations

import pytest

from candidate_weight_reference import (
    CandidateWeightInputs,
    CompiledAmbientCarrier,
    ContractViolation,
    calculate_multiplicative_candidate_weight,
    resolve_ambient_carrier,
)


def test_fully_baked_carrier_feeds_current_candidate_surface_only() -> None:
    """A fully baked artifact is already Owner-resolved: downstream is L x C only.

    The retired chain continued with independent G/V multipliers
    (72 * 1.10 * 0.80 * 0.50 = 31.68, now a pinned legacy fixture); the
    admitted multiplicative specialization surface has no hook for them.
    """
    carrier = CompiledAmbientCarrier(value=72.0, baked_semantic_stages=frozenset({"B", "P", "E"}))
    ambient = resolve_ambient_carrier(carrier, {})

    weight = calculate_multiplicative_candidate_weight(
        CandidateWeightInputs(local_species_intensity=ambient, capture_retention=0.50)
    )
    assert ambient == pytest.approx(72.0)
    assert weight == pytest.approx(36.0)

    with pytest.raises(TypeError):
        CandidateWeightInputs(
            local_species_intensity=ambient,
            capture_retention=0.50,
            aggregation=1.10,
            readiness=0.80,
        )


def test_duplicate_baked_stage_consumption_is_release_blocker() -> None:
    carrier = CompiledAmbientCarrier(value=72.0, baked_semantic_stages=frozenset({"B", "P", "E"}))

    with pytest.raises(ContractViolation) as exc_info:
        resolve_ambient_carrier(carrier, {"E": 0.5})

    assert exc_info.value.code == "DUPLICATE_STAGE_CONSUMPTION"
    assert exc_info.value.detail == "E"


def test_missing_bake_metadata_is_blocked() -> None:
    carrier = CompiledAmbientCarrier(value=72.0, baked_semantic_stages=None)

    with pytest.raises(ContractViolation) as exc_info:
        resolve_ambient_carrier(carrier, {})

    assert exc_info.value.code == "BAKED_STAGE_UNKNOWN"


def test_partial_bake_consumes_only_missing_population_stage() -> None:
    carrier = CompiledAmbientCarrier(value=8.0, baked_semantic_stages=frozenset({"B", "E"}))
    ambient = resolve_ambient_carrier(carrier, {"P": 0.5})

    assert ambient == pytest.approx(4.0)


def test_missing_ambient_stage_fails_closed() -> None:
    carrier = CompiledAmbientCarrier(value=8.0, baked_semantic_stages=frozenset({"E"}))

    with pytest.raises(ContractViolation) as exc_info:
        resolve_ambient_carrier(carrier, {})

    assert exc_info.value.code == "PRODUCER_MISSING_REQUIRED_FIELD"
    assert exc_info.value.detail == "ambient stage(s): B,P"

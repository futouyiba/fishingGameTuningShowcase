from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping

from .errors import ContractViolation

AMBIENT_STAGES = frozenset({"B", "P", "E"})


@dataclass(frozen=True)
class CompiledAmbientCarrier:
    value: float
    baked_semantic_stages: frozenset[str] | None


def resolve_ambient_carrier(
    carrier: CompiledAmbientCarrier,
    stages_to_consume: Mapping[str, float],
) -> float:
    """Consume exactly the B/P/E stages not already baked into an artifact."""
    if carrier.baked_semantic_stages is None:
        raise ContractViolation("BAKED_STAGE_UNKNOWN", "artifact stage metadata is missing")
    if not isfinite(carrier.value) or carrier.value < 0:
        raise ValueError("carrier.value must be finite and >= 0")

    baked = frozenset(carrier.baked_semantic_stages)
    invalid_baked = baked - AMBIENT_STAGES
    if invalid_baked:
        raise ValueError(f"unknown baked ambient stages: {sorted(invalid_baked)}")

    supplied = frozenset(stages_to_consume)
    invalid_supplied = supplied - AMBIENT_STAGES
    if invalid_supplied:
        raise ValueError(f"unknown ambient stages to consume: {sorted(invalid_supplied)}")

    duplicates = baked & supplied
    if duplicates:
        duplicate = ",".join(sorted(duplicates))
        raise ContractViolation("DUPLICATE_STAGE_CONSUMPTION", duplicate)

    missing = AMBIENT_STAGES - baked - supplied
    if missing:
        field = ",".join(sorted(missing))
        raise ContractViolation("PRODUCER_MISSING_REQUIRED_FIELD", f"ambient stage(s): {field}")

    result = carrier.value
    for stage in sorted(supplied):
        value = float(stages_to_consume[stage])
        if not isfinite(value) or value < 0:
            raise ValueError(f"ambient stage {stage} must be finite and >= 0")
        result *= value
    return result


def continue_candidate_chain(
    ambient_weight: float,
    aggregation: float,
    readiness: float,
    capture: float,
) -> float:
    """Continue only the downstream G-to-V-to-C stages after ambient materialization."""
    return ambient_weight * aggregation * readiness * capture

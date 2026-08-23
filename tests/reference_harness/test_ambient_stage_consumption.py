from __future__ import annotations

import pytest

from candidate_weight_reference import (
    CompiledAmbientCarrier,
    ContractViolation,
    continue_candidate_chain,
    resolve_ambient_carrier,
)


def test_fully_baked_ambient_carrier_continues_only_g_v_c() -> None:
    carrier = CompiledAmbientCarrier(
        value=72.0, baked_semantic_stages=frozenset({"B", "P", "E"})
    )
    ambient = resolve_ambient_carrier(carrier, {})
    final_weight = continue_candidate_chain(
        ambient, aggregation=1.10, readiness=0.80, capture=0.50
    )

    assert final_weight == pytest.approx(31.68)


def test_duplicate_baked_stage_consumption_is_release_blocker() -> None:
    carrier = CompiledAmbientCarrier(
        value=72.0, baked_semantic_stages=frozenset({"B", "P", "E"})
    )

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

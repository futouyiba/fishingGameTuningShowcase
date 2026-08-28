from __future__ import annotations

import pytest

from candidate_weight_reference import (
    CandidateWeightInputs,
    CompiledAmbientCarrier,
    ContractViolation,
    MaterializationLineage,
    MaterializedConsequence,
    SemanticConsequenceIdentity,
    StrongBakeManifest,
    calculate_multiplicative_candidate_weight,
    resolve_ambient_carrier,
)


def _lineage(source_revision: str = "rev-a") -> MaterializationLineage:
    return MaterializationLineage(
        source_revision=source_revision,
        dependency_fingerprint="fp-base-001",
        resolver_version="resolver-1",
        projection_version="projection-1",
        source_snapshot_ref="snap-001",
    )


def _consequence(
    cause_role: str,
    consequence_kind: str,
    instance_id: str,
    value: float,
    settled_stage: str,
) -> MaterializedConsequence:
    return MaterializedConsequence(
        identity=SemanticConsequenceIdentity(
            cause_role=cause_role,
            consequence_kind=consequence_kind,
            coverage_scope="scope-X",
            ownership_boundary="Spatial",
        ),
        instance_id=instance_id,
        value=value,
        typed_outcome="resolved-scalar",
        coverage_scope="scope-X",
        lineage=_lineage(),
        validity_region_ref="region-scope-X-v1",
        settled_stage=settled_stage,
        validity="valid",
    )


def full_bake_manifest() -> StrongBakeManifest:
    """8.0 x 3.0 x 3.0 mirrors the compiled carrier value 72.0."""
    return StrongBakeManifest(
        materialized=(
            _consequence("SeasonalBase", "BaselinePopulation", "inst-b", 8.0, "B"),
            _consequence("Aggregation", "LocalPopulation", "inst-p", 3.0, "P"),
            _consequence("Environment", "EnvironmentResponse", "inst-e", 3.0, "E"),
        ),
        baked_semantic_stages=frozenset({"B", "P", "E"}),
    )


def partial_bake_manifest() -> StrongBakeManifest:
    """Only B and E settled; P stays a runtime-supplied multiplier."""
    return StrongBakeManifest(
        materialized=(
            _consequence("SeasonalBase", "BaselinePopulation", "inst-b", 8.0, "B"),
            _consequence("Environment", "EnvironmentResponse", "inst-e", 1.0, "E"),
        ),
        baked_semantic_stages=frozenset({"B", "E"}),
    )


def environment_only_manifest() -> StrongBakeManifest:
    return StrongBakeManifest(
        materialized=(_consequence("Environment", "EnvironmentResponse", "inst-e", 8.0, "E"),),
        baked_semantic_stages=frozenset({"E"}),
    )


def test_fully_baked_carrier_feeds_current_candidate_surface_only() -> None:
    """A fully baked artifact is already Owner-resolved: downstream is L x C only.

    The retired chain continued with independent G/V multipliers
    (72 * 1.10 * 0.80 * 0.50 = 31.68, now a pinned legacy fixture); the
    resolved-scalar TypedNativeRetentionJoin branch has no hook for them.
    """
    carrier = CompiledAmbientCarrier(
        value=72.0,
        baked_semantic_stages=frozenset({"B", "P", "E"}),
        bake_manifest=full_bake_manifest(),
    )
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
    carrier = CompiledAmbientCarrier(
        value=72.0,
        baked_semantic_stages=frozenset({"B", "P", "E"}),
        bake_manifest=full_bake_manifest(),
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
    carrier = CompiledAmbientCarrier(
        value=8.0,
        baked_semantic_stages=frozenset({"B", "E"}),
        bake_manifest=partial_bake_manifest(),
    )
    ambient = resolve_ambient_carrier(carrier, {"P": 0.5})

    assert ambient == pytest.approx(4.0)


def test_missing_ambient_stage_fails_closed() -> None:
    carrier = CompiledAmbientCarrier(
        value=8.0,
        baked_semantic_stages=frozenset({"E"}),
        bake_manifest=environment_only_manifest(),
    )

    with pytest.raises(ContractViolation) as exc_info:
        resolve_ambient_carrier(carrier, {})

    assert exc_info.value.code == "PRODUCER_MISSING_REQUIRED_FIELD"
    assert exc_info.value.detail == "ambient stage(s): B,P"


def test_sb08_strong_manifest_preserves_existing_bake_arithmetic() -> None:
    """SB-08: the Strong Bake Manifest is a semantic-preservation envelope.

    Attaching the manifest must not change the numeric results of the
    pre-existing partial/full bake fixtures: same carrier values, same
    supplied multipliers, same resolved ambient, same Candidate L x C.
    """
    full = CompiledAmbientCarrier(
        value=72.0,
        baked_semantic_stages=frozenset({"B", "P", "E"}),
        bake_manifest=full_bake_manifest(),
    )
    assert resolve_ambient_carrier(full, {}) == pytest.approx(72.0)

    partial = CompiledAmbientCarrier(
        value=8.0,
        baked_semantic_stages=frozenset({"B", "E"}),
        bake_manifest=partial_bake_manifest(),
    )
    assert resolve_ambient_carrier(partial, {"P": 0.5}) == pytest.approx(4.0)

    ambient = resolve_ambient_carrier(full, {})
    weight = calculate_multiplicative_candidate_weight(
        CandidateWeightInputs(local_species_intensity=ambient, capture_retention=0.50)
    )
    assert weight == pytest.approx(36.0)

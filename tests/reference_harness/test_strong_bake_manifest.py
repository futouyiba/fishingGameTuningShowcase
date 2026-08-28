from __future__ import annotations

from dataclasses import fields

import pytest

from candidate_weight_reference import (
    CompiledAmbientCarrier,
    ContractViolation,
    MaterializationLineage,
    MaterializedConsequence,
    SemanticConsequenceIdentity,
    StrongBakeManifest,
    active_materializations,
    invalidate_materialized_consequence,
    resolve_ambient_carrier,
    settle_materialized_consequence,
)


def make_lineage(
    source_revision: str = "rev-a",
    dependency_fingerprint: str = "fp-base-001",
    resolver_version: str = "resolver-1",
    projection_version: str = "projection-1",
) -> MaterializationLineage:
    return MaterializationLineage(
        source_revision=source_revision,
        dependency_fingerprint=dependency_fingerprint,
        resolver_version=resolver_version,
        projection_version=projection_version,
        source_snapshot_ref="snap-001",
    )


def make_identity(
    cause_role: str = "Environment",
    consequence_kind: str = "EnvironmentResponse",
    coverage_scope: str = "scope-X",
    ownership_boundary: str = "Spatial",
) -> SemanticConsequenceIdentity:
    return SemanticConsequenceIdentity(
        cause_role=cause_role,
        consequence_kind=consequence_kind,
        coverage_scope=coverage_scope,
        ownership_boundary=ownership_boundary,
    )


def make_consequence(
    *,
    identity: SemanticConsequenceIdentity | None = None,
    instance_id: str = "inst-001",
    value: float = 2.0,
    typed_outcome: str = "resolved-scalar",
    settled_stage: str = "E",
    validity: str = "valid",
    lineage: MaterializationLineage | None = None,
) -> MaterializedConsequence:
    resolved_identity = identity if identity is not None else make_identity()
    return MaterializedConsequence(
        identity=resolved_identity,
        instance_id=instance_id,
        value=value,
        typed_outcome=typed_outcome,
        coverage_scope=resolved_identity.coverage_scope,
        lineage=lineage if lineage is not None else make_lineage(),
        validity_region_ref="region-scope-X-v1",
        settled_stage=settled_stage,
        validity=validity,
    )


def make_full_bake_manifest() -> StrongBakeManifest:
    """Three valid consequences settling B/P/E; 8.0 x 3.0 x 3.0 mirrors carrier 72.0."""
    return StrongBakeManifest(
        materialized=(
            make_consequence(
                identity=make_identity(
                    cause_role="SeasonalBase",
                    consequence_kind="BaselinePopulation",
                    ownership_boundary="Spatial",
                ),
                instance_id="inst-b",
                value=8.0,
                settled_stage="B",
            ),
            make_consequence(
                identity=make_identity(
                    cause_role="Aggregation",
                    consequence_kind="LocalPopulation",
                    ownership_boundary="Spatial",
                ),
                instance_id="inst-p",
                value=3.0,
                settled_stage="P",
            ),
            make_consequence(
                instance_id="inst-e",
                value=3.0,
                settled_stage="E",
            ),
        ),
        baked_semantic_stages=frozenset({"B", "P", "E"}),
    )


def test_sb01_missing_strong_manifest_fails_closed() -> None:
    """SB-01: value + stage summary alone can no longer reach the numeric kernel."""
    legacy_shape = CompiledAmbientCarrier(
        value=72.0, baked_semantic_stages=frozenset({"B", "P", "E"})
    )

    with pytest.raises(ContractViolation) as exc_info:
        resolve_ambient_carrier(legacy_shape, {})

    assert exc_info.value.code == "BAKE_MANIFEST_MISSING"

    # Negative control: a carrier that materialized nothing needs no manifest.
    runtime_only = CompiledAmbientCarrier(value=1.0, baked_semantic_stages=frozenset())
    assert resolve_ambient_carrier(runtime_only, {"B": 2.0, "P": 3.0, "E": 4.0}) == pytest.approx(
        24.0
    )


def test_sb02_same_identity_same_revision_duplicate_is_blocker() -> None:
    """SB-02: re-submitting an already active identity fails closed."""
    baked = make_consequence(instance_id="inst-001")
    manifest = StrongBakeManifest(materialized=(baked,), baked_semantic_stages=frozenset({"E"}))
    resubmission = make_consequence(instance_id="inst-002")

    with pytest.raises(ContractViolation) as exc_info:
        settle_materialized_consequence(manifest, resubmission)

    assert exc_info.value.code == "DUPLICATE_SEMANTIC_CONSEQUENCE"


def test_sb03_same_identity_different_revision_still_duplicate() -> None:
    """SB-03: revision change alone is not a second consequence."""
    identity = make_identity()
    revision_a = make_consequence(
        identity=identity,
        instance_id="inst-a",
        lineage=make_lineage(source_revision="rev-a", dependency_fingerprint="fp-a"),
    )
    revision_b = make_consequence(
        identity=identity,
        instance_id="inst-b",
        lineage=make_lineage(source_revision="rev-b", dependency_fingerprint="fp-b"),
    )
    manifest = StrongBakeManifest(
        materialized=(revision_a,), baked_semantic_stages=frozenset({"E"})
    )

    with pytest.raises(ContractViolation) as exc_info:
        settle_materialized_consequence(manifest, revision_b)

    assert exc_info.value.code == "DUPLICATE_SEMANTIC_CONSEQUENCE"

    # Hand-building a manifest with both revisions active is equally blocked.
    with pytest.raises(ContractViolation) as exc_info:
        StrongBakeManifest(
            materialized=(revision_a, revision_b), baked_semantic_stages=frozenset({"E"})
        )

    assert exc_info.value.code == "DUPLICATE_SEMANTIC_CONSEQUENCE"


def test_sb04_same_raw_fact_different_cause_roles_are_distinct() -> None:
    """SB-04: one raw fact may legitimately settle two different consequence identities."""
    thermal = make_consequence(
        identity=make_identity(
            cause_role="Temperature",
            consequence_kind="ThermalSuitability",
            ownership_boundary="Spatial",
        ),
        instance_id="inst-thermal",
        settled_stage="E",
    )
    aerobic = make_consequence(
        identity=make_identity(
            cause_role="Temperature",
            consequence_kind="AerobicConsequence",
            ownership_boundary="Functional",
        ),
        instance_id="inst-aerobic",
        settled_stage="E",
    )
    empty = StrongBakeManifest(materialized=(), baked_semantic_stages=frozenset())

    manifest = settle_materialized_consequence(
        settle_materialized_consequence(empty, thermal), aerobic
    )

    labels = {
        consequence.identity.canonical_label() for consequence in active_materializations(manifest)
    }
    assert labels == {"Spatial.ThermalSuitability@scope-X", "Functional.AerobicConsequence@scope-X"}


def test_sb05_invalid_old_instance_is_replaced_not_stacked() -> None:
    """SB-05: old invalid + new valid keeps exactly one active instance per identity."""
    identity = make_identity()
    old = make_consequence(
        identity=identity,
        instance_id="inst-old",
        value=2.0,
        lineage=make_lineage(source_revision="rev-a"),
    )
    manifest = StrongBakeManifest(materialized=(old,), baked_semantic_stages=frozenset({"E"}))

    invalidated = invalidate_materialized_consequence(manifest, "inst-old")
    assert active_materializations(invalidated) == ()

    new = make_consequence(
        identity=identity,
        instance_id="inst-new",
        value=3.0,
        lineage=make_lineage(source_revision="rev-b"),
    )
    replaced = settle_materialized_consequence(invalidated, new)

    active = active_materializations(replaced)
    assert [consequence.instance_id for consequence in active] == ["inst-new"]
    assert [consequence.value for consequence in active] == [3.0]
    # The replaced instance stays recorded as invalid history.
    assert {
        consequence.instance_id: consequence.validity for consequence in replaced.materialized
    } == {
        "inst-old": "invalid",
        "inst-new": "valid",
    }

    carrier = CompiledAmbientCarrier(
        value=3.0,
        baked_semantic_stages=frozenset({"E"}),
        bake_manifest=replaced,
    )
    ambient = resolve_ambient_carrier(carrier, {"B": 2.0, "P": 2.0})
    assert ambient == pytest.approx(12.0)


def test_sb06_missing_lineage_fails_closed() -> None:
    """SB-06: required lineage fields cannot be empty in a baked manifest."""
    for lineage_field in (
        "source_revision",
        "dependency_fingerprint",
        "resolver_version",
        "projection_version",
    ):
        incomplete = make_lineage(**{lineage_field: ""})
        consequence = make_consequence(lineage=incomplete)

        with pytest.raises(ContractViolation) as exc_info:
            StrongBakeManifest(materialized=(consequence,), baked_semantic_stages=frozenset({"E"}))

        assert exc_info.value.code == "BAKE_LINEAGE_INCOMPLETE"


def test_unknown_validity_fails_closed_before_numeric_kernel() -> None:
    unknown = make_consequence(instance_id="inst-unknown", validity="unknown")
    manifest = StrongBakeManifest(materialized=(unknown,), baked_semantic_stages=frozenset())
    carrier = CompiledAmbientCarrier(
        value=3.0,
        baked_semantic_stages=frozenset(),
        bake_manifest=manifest,
    )

    with pytest.raises(ContractViolation) as exc_info:
        resolve_ambient_carrier(carrier, {"B": 1.0, "P": 1.0, "E": 1.0})

    assert exc_info.value.code == "BAKE_VALIDITY_UNKNOWN"


def test_sb07_stage_summary_mismatch_fails_closed() -> None:
    """SB-07: the summary never overrides the manifest's actual coverage."""
    # Carrier summary conflicts with manifest truth.
    carrier = CompiledAmbientCarrier(
        value=72.0,
        baked_semantic_stages=frozenset({"B", "E"}),
        bake_manifest=make_full_bake_manifest(),
    )
    with pytest.raises(ContractViolation) as exc_info:
        resolve_ambient_carrier(carrier, {"P": 0.5})

    assert exc_info.value.code == "BAKE_STAGE_SUMMARY_MISMATCH"

    # Manifest summary claims a stage no valid consequence settles.
    single_stage = make_consequence(settled_stage="E")
    with pytest.raises(ContractViolation) as exc_info:
        StrongBakeManifest(
            materialized=(single_stage,),
            baked_semantic_stages=frozenset({"B", "E"}),
        )

    assert exc_info.value.code == "BAKE_STAGE_SUMMARY_MISMATCH"

    # An invalid instance never counts as stage coverage.
    invalid_only = make_consequence(settled_stage="P", validity="invalid")
    with pytest.raises(ContractViolation) as exc_info:
        StrongBakeManifest(
            materialized=(invalid_only,),
            baked_semantic_stages=frozenset({"P"}),
        )

    assert exc_info.value.code == "BAKE_STAGE_SUMMARY_MISMATCH"


def test_semantic_identity_never_carries_revision_or_version() -> None:
    """Hard identity rule: revision/version fields live only in the lineage layer."""
    identity_fields = {field.name for field in fields(SemanticConsequenceIdentity)}
    assert identity_fields == {
        "cause_role",
        "consequence_kind",
        "coverage_scope",
        "ownership_boundary",
    }

    lineage_fields = {field.name for field in fields(MaterializationLineage)}
    assert lineage_fields == {
        "source_revision",
        "dependency_fingerprint",
        "resolver_version",
        "projection_version",
        "source_snapshot_ref",
        "policy_overlay_provenance",
    }

"""Ambient carrier consumption and its Strong Bake Manifest envelope.

Strong Bake Manifest Current requires a baked artifact to prove three
separated layers:

1. ``SemanticConsequenceIdentity`` — which semantic consequence this is,
   revision-free (hard identity rule: source revision, resolver /
   projection version and artifact/build revision must never enter the
   identity; they live only in the lineage layer);
2. ``MaterializedConsequence`` — one materialization instance of that
   identity, with its value, settled ambient stage and explicit validity;
3. ``MaterializationLineage`` — provenance of the instance.

The old ``baked_semantic_stages`` set remains as a stage index /
compatibility summary only: it is cross-checked against the manifest's
actual coverage and is no longer the sole duplicate-settlement
authority. The manifest never recomputes or re-authorizes ambient
arithmetic: ``carrier.value`` stays the compiled Spatial-Owner number,
and the Candidate ``L x C`` surface is untouched.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from math import isfinite

from .errors import ContractViolation

AMBIENT_STAGES = frozenset({"B", "P", "E"})

VALIDITY_VALID = "valid"
VALIDITY_INVALID = "invalid"
VALIDITY_UNKNOWN = "unknown"
BAKE_VALIDITY_STATES = frozenset({VALIDITY_VALID, VALIDITY_INVALID, VALIDITY_UNKNOWN})

_REQUIRED_LINEAGE_FIELDS = (
    "source_revision",
    "dependency_fingerprint",
    "resolver_version",
    "projection_version",
)


@dataclass(frozen=True)
class SemanticConsequenceIdentity:
    """Layer 1: which semantic consequence this is.

    Equality on these four semantic fields is the only duplicate-settlement
    key; it is deliberately revision-blind.
    """

    cause_role: str
    consequence_kind: str
    coverage_scope: str
    ownership_boundary: str

    def __post_init__(self) -> None:
        for field_name in (
            "cause_role",
            "consequence_kind",
            "coverage_scope",
            "ownership_boundary",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{field_name} must be a non-empty string")

    def canonical_label(self) -> str:
        return f"{self.ownership_boundary}.{self.consequence_kind}@{self.coverage_scope}"


@dataclass(frozen=True)
class MaterializationLineage:
    """Layer 3: provenance of one materialization instance.

    Completeness is enforced by ``StrongBakeManifest`` (fail closed with
    ``BAKE_LINEAGE_INCOMPLETE``) so an incomplete lineage is representable
    as a record but can never enter a baked artifact.
    """

    source_revision: str
    dependency_fingerprint: str
    resolver_version: str
    projection_version: str
    source_snapshot_ref: str | None = None
    policy_overlay_provenance: tuple[str, ...] = ()


@dataclass(frozen=True)
class MaterializedConsequence:
    """Layer 2: one materialization instance of a semantic consequence."""

    identity: SemanticConsequenceIdentity
    instance_id: str
    value: float
    typed_outcome: str
    coverage_scope: str
    lineage: MaterializationLineage
    validity_region_ref: str
    settled_stage: str
    validity: str

    def __post_init__(self) -> None:
        if not isinstance(self.instance_id, str) or not self.instance_id:
            raise ValueError("instance_id must be a non-empty string")
        if not isfinite(self.value) or self.value < 0:
            raise ValueError("consequence value must be finite and >= 0")
        if not isinstance(self.typed_outcome, str) or not self.typed_outcome:
            raise ValueError("typed_outcome must be a non-empty string")
        if self.coverage_scope != self.identity.coverage_scope:
            raise ValueError("coverage_scope must match identity.coverage_scope")
        if not isinstance(self.validity_region_ref, str) or not self.validity_region_ref:
            raise ValueError("validity_region_ref must be a non-empty string")
        if self.settled_stage not in AMBIENT_STAGES:
            raise ValueError(f"settled_stage must be one of {sorted(AMBIENT_STAGES)}")
        if self.validity not in BAKE_VALIDITY_STATES:
            raise ValueError(f"validity must be one of {sorted(BAKE_VALIDITY_STATES)}")


def _derived_stage_coverage(materialized: tuple[MaterializedConsequence, ...]) -> frozenset[str]:
    """Actual stage coverage: stages settled by a currently valid instance."""
    return frozenset(
        consequence.settled_stage
        for consequence in materialized
        if consequence.validity == VALIDITY_VALID
    )


@dataclass(frozen=True)
class StrongBakeManifest:
    """Typed envelope of every consequence baked into an artifact.

    Reference V1 takes validity as an explicit input (valid / invalid /
    unknown) instead of implementing a dependency-graph evaluator; the
    guards below are what fail closed on it.
    """

    materialized: tuple[MaterializedConsequence, ...]
    baked_semantic_stages: frozenset[str]

    def __post_init__(self) -> None:
        for consequence in self.materialized:
            lineage = consequence.lineage
            for field_name in _REQUIRED_LINEAGE_FIELDS:
                value = getattr(lineage, field_name)
                if not isinstance(value, str) or not value:
                    raise ContractViolation(
                        "BAKE_LINEAGE_INCOMPLETE",
                        f"{consequence.identity.canonical_label()}: lineage {field_name} is missing",
                    )
        active: dict[SemanticConsequenceIdentity, str] = {}
        for consequence in self.materialized:
            if consequence.validity != VALIDITY_VALID:
                continue
            prior_instance = active.get(consequence.identity)
            if prior_instance is not None:
                raise ContractViolation(
                    "DUPLICATE_SEMANTIC_CONSEQUENCE",
                    f"{consequence.identity.canonical_label()}: active instances "
                    f"{prior_instance} and {consequence.instance_id} cannot coexist",
                )
            active[consequence.identity] = consequence.instance_id
        actual_coverage = _derived_stage_coverage(self.materialized)
        if self.baked_semantic_stages != actual_coverage:
            raise ContractViolation(
                "BAKE_STAGE_SUMMARY_MISMATCH",
                f"declared {sorted(self.baked_semantic_stages)} != "
                f"materialized {sorted(actual_coverage)}",
            )


def active_materializations(manifest: StrongBakeManifest) -> tuple[MaterializedConsequence, ...]:
    """The effective bake set: valid instances only, at most one per identity."""
    return tuple(
        consequence
        for consequence in manifest.materialized
        if consequence.validity == VALIDITY_VALID
    )


def settle_materialized_consequence(
    manifest: StrongBakeManifest,
    consequence: MaterializedConsequence,
) -> StrongBakeManifest:
    """Settle one materialization instance against the baked manifest.

    Settlement of an identity that already has an active instance fails
    closed (revision-blind); the manifest constructor raises
    ``DUPLICATE_SEMANTIC_CONSEQUENCE``. Replacement is not implicit: the
    old instance must be invalidated first via
    ``invalidate_materialized_consequence``.
    """
    grown_stages = manifest.baked_semantic_stages
    if consequence.validity == VALIDITY_VALID:
        grown_stages = manifest.baked_semantic_stages | frozenset({consequence.settled_stage})
    return StrongBakeManifest(
        materialized=manifest.materialized + (consequence,),
        baked_semantic_stages=grown_stages,
    )


def invalidate_materialized_consequence(
    manifest: StrongBakeManifest,
    instance_id: str,
) -> StrongBakeManifest:
    """Express dependency-change invalidation of one instance.

    The invalidated instance stays recorded as history but leaves the
    active set; a stage that loses its last valid instance loses its
    claimed coverage, so a stale summary fails closed on re-validation.
    """
    if instance_id not in {consequence.instance_id for consequence in manifest.materialized}:
        raise ValueError(f"unknown instance_id: {instance_id}")
    replaced = tuple(
        replace(consequence, validity=VALIDITY_INVALID)
        if consequence.instance_id == instance_id
        else consequence
        for consequence in manifest.materialized
    )
    return StrongBakeManifest(
        materialized=replaced,
        baked_semantic_stages=_derived_stage_coverage(replaced),
    )


@dataclass(frozen=True)
class CompiledAmbientCarrier:
    value: float
    baked_semantic_stages: frozenset[str] | None
    bake_manifest: StrongBakeManifest | None = None


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

    if baked and carrier.bake_manifest is None:
        raise ContractViolation(
            "BAKE_MANIFEST_MISSING",
            "carrier materialized semantic consequences but carries no Strong Bake Manifest",
        )
    if carrier.bake_manifest is not None:
        if any(
            consequence.validity == VALIDITY_UNKNOWN
            for consequence in carrier.bake_manifest.materialized
        ):
            raise ContractViolation(
                "BAKE_VALIDITY_UNKNOWN",
                "manifest contains a consequence whose validity is unknown",
            )
        if baked != carrier.bake_manifest.baked_semantic_stages:
            raise ContractViolation(
                "BAKE_STAGE_SUMMARY_MISMATCH",
                f"carrier summary {sorted(baked)} != manifest coverage "
                f"{sorted(carrier.bake_manifest.baked_semantic_stages)}",
            )

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

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, is_dataclass
from hashlib import sha256
from math import isfinite
from numbers import Real
from typing import Any, Literal

ResolutionStatus = Literal["Unknown", "Unsupported", "InsufficientEvidence"]
AuthorityMode = Literal["authoritative_projection", "client_claim"]

_CANONICAL_DIGITS = 9
_SEMANTIC_VERSION = "actual-presentation/v1"
_RESOLVER_VERSION = "reference-resolver/v1"
_PROJECTION_VERSION = "reference-kinematic-projection/v1"
_RESOLUTION_STATUSES = frozenset({"Unknown", "Unsupported", "InsufficientEvidence"})
_AUTHORITY_MODES = frozenset({"authoritative_projection", "client_claim"})
_OPAQUE_TEXT_FIELDS = frozenset(
    {
        "presentationidentity",
        "admittedinputfingerprint",
        "worldsnapshotref",
        "worldrevision",
        "resolverversion",
        "projectionversion",
        "semanticversion",
        "authoritymode",
    }
)

_FISH_ANTI_FIELDS = {
    "attractiveness",
    "fishaffinity",
    "catchability",
    "presentationquality",
    "fishvisibility",
    "techniquebonus",
    "baitbonus",
    "rigbonus",
    "responsedifficulty",
}
_OPPORTUNITY_ANTI_FIELDS = {
    "logicalopportunity",
    "cadence",
    "refractory",
    "nonoverlap",
    "formationconsumptionlifecycle",
    "opportunityevaluationscope",
}
_INTERACTION_ANTI_FIELDS = {
    "perceptualoutcome",
    "presentedtargethypotheses",
    "fishbelief",
    "fishpreference",
    "fishspecificresponsescore",
    "resolvedtargetsituation",
}
_INTERACTION_KEY_FRAGMENTS = (
    "interaction",
    "fishresponse",
    "response",
    "perception",
    "perceptual",
    "targethypoth",
    "targetinterpretation",
    "fishbelief",
    "fishpreference",
    "resolvedtargetsituation",
    "captureretention",
)
_OPPORTUNITY_KEY_FRAGMENTS = (
    "opportunity",
    "cadence",
    "refractory",
    "nonoverlap",
    "formation",
    "consumptionlifecycle",
    "candidate",
)
_FISH_KEY_FRAGMENTS = (
    "species",
    "fish",
    "attractiveness",
    "catchability",
    "presentationquality",
    "techniquebonus",
    "baitbonus",
    "rigbonus",
)

_PHASE_VOCABULARY = frozenset(
    {"pause", "retrieve", "sink", "drift", "lift", "hold", "fall", "twitch"}
)
_CUE_TAG_VOCABULARY = frozenset({"pressure-wave", "visual-motion", "acoustic-pulse", "vibration"})
_PRESENTATION_DESCRIPTOR_VOCABULARY = frozenset(
    {
        "bounded-retrieve",
        "single-target",
        "multi-target",
        "surface-pause",
        "steady-fall",
        "slow-drift",
        "vertical-lift",
        "erratic-dart",
    }
)
_SCHEMA_ROOT_KEYS = frozenset(
    {
        "presentation_identity",
        "realized_spatial_facts",
        "realized_motion_facts",
        "cue_emission_facts",
        "target_presentation_descriptors",
        "temporal_context",
        "completeness",
        "provenance",
        "semantic_version",
    }
)
_SCHEMA_SPATIAL_KEYS = frozenset({"origin", "end_position", "displacement"})
_SCHEMA_MOTION_KEYS = frozenset(
    {
        "controlled_velocity",
        "drift_velocity",
        "fall_velocity",
        "realized_average_velocity",
    }
)
_SCHEMA_CUE_KEYS = frozenset({"amplitude", "cue_tags"})
_SCHEMA_PHASE_KEYS = frozenset({"phase", "start_time", "end_time", "control_scale", "displacement"})
_SCHEMA_PROVENANCE_KEYS = frozenset(
    {
        "authority_mode",
        "admitted_input_fingerprint",
        "world_snapshot_ref",
        "world_revision",
        "resolver_version",
        "projection_version",
    }
)
_SCHEMA_VECTOR_KEYS = frozenset({"x", "y", "z"})
_SCHEMA_ALLOWED_KEYS = {
    "root": _SCHEMA_ROOT_KEYS,
    "spatial": _SCHEMA_SPATIAL_KEYS,
    "motion": _SCHEMA_MOTION_KEYS,
    "cue": _SCHEMA_CUE_KEYS,
    "phase": _SCHEMA_PHASE_KEYS,
    "provenance": _SCHEMA_PROVENANCE_KEYS,
    "vector": _SCHEMA_VECTOR_KEYS,
}
_SCHEMA_ROOT_CHILD_CONTEXTS = {
    "realized_spatial_facts": "spatial",
    "realized_motion_facts": "motion",
    "cue_emission_facts": "cue",
    "temporal_context": "temporal_list",
    "target_presentation_descriptors": "descriptor_list",
    "provenance": "provenance",
}
_SCHEMA_SEQUENCE_ITEM_CONTEXTS = {
    "temporal_list": "phase",
    "descriptor_list": "descriptor",
    "cue_tag_list": "cue_tag",
}


class PresentationContractViolation(ValueError):
    def __init__(self, code: str, path: str, message: str) -> None:
        super().__init__(f"{code} at {path}: {message}")
        self.code = code
        self.path = path


@dataclass(frozen=True)
class Vector3:
    x: float
    y: float
    z: float

    def __post_init__(self) -> None:
        for value in (self.x, self.y, self.z):
            _validate_finite_real(value, "Vector3 values")


@dataclass(frozen=True)
class UnresolvedInput:
    status: ResolutionStatus
    detail: str

    def __post_init__(self) -> None:
        if self.status not in _RESOLUTION_STATUSES:
            raise ValueError(
                "unresolved input status must be Unknown, Unsupported, or InsufficientEvidence"
            )
        if not self.detail:
            raise ValueError("unresolved input detail must be non-empty")


@dataclass(frozen=True)
class ActionPhase:
    phase: str
    start_time: float
    end_time: float
    control_scale: float = 1.0

    def __post_init__(self) -> None:
        if not self.phase:
            raise ValueError("action phase must be non-empty")
        if self.phase not in _PHASE_VOCABULARY:
            raise ValueError(
                "action phase labels must come from the closed action-phase vocabulary"
            )
        for value in (self.start_time, self.end_time, self.control_scale):
            _validate_finite_real(value, "action phase numeric values")
        if self.end_time <= self.start_time:
            raise ValueError("action phase end_time must be > start_time")
        if self.control_scale < 0:
            raise ValueError("action phase control_scale must be >= 0")


@dataclass(frozen=True)
class ActionFacts:
    action_id: str
    origin: Vector3
    commanded_velocity: Vector3
    cue_drive: float
    phases: tuple[ActionPhase, ...]

    def __post_init__(self) -> None:
        if not self.action_id:
            raise ValueError("action_id must be non-empty")
        _validate_vector(self.origin, "origin")
        _validate_vector(self.commanded_velocity, "commanded_velocity")
        _validate_nonnegative_real(self.cue_drive, "cue_drive")
        if not isinstance(self.phases, tuple):
            raise ValueError("phases must be a tuple")
        if not self.phases:
            raise ValueError("at least one action phase is required")
        if any(not isinstance(phase, ActionPhase) for phase in self.phases):
            raise ValueError("phases must contain ActionPhase values")


@dataclass(frozen=True)
class TechniqueCapability:
    technique_id: str
    action_gain: float
    cue_gain: float
    cue_tags: tuple[str, ...]
    presentation_descriptors: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_capability(self.technique_id, self.action_gain, self.cue_gain)
        _validate_tokens(self.cue_tags, "cue_tags", _CUE_TAG_VOCABULARY)
        _validate_tokens(
            self.presentation_descriptors,
            "presentation_descriptors",
            _PRESENTATION_DESCRIPTOR_VOCABULARY,
        )


@dataclass(frozen=True)
class RigCapability:
    rig_id: str
    flow_coupling: float
    gravity_coupling: float

    def __post_init__(self) -> None:
        if not self.rig_id:
            raise ValueError("rig_id must be non-empty")
        for value in (self.flow_coupling, self.gravity_coupling):
            _validate_nonnegative_real(value, "rig coupling values")


@dataclass(frozen=True)
class EquipmentCapability:
    equipment_id: str
    motion_gain: float
    cue_gain: float
    presentation_descriptors: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_capability(self.equipment_id, self.motion_gain, self.cue_gain)
        _validate_tokens(
            self.presentation_descriptors,
            "presentation_descriptors",
            _PRESENTATION_DESCRIPTOR_VOCABULARY,
        )


@dataclass(frozen=True)
class AuthoritativePhysics:
    world_snapshot_ref: str
    world_revision: str
    flow_velocity: Vector3
    gravity: Vector3

    def __post_init__(self) -> None:
        if not self.world_snapshot_ref or not self.world_revision:
            raise ValueError("authoritative World references must be non-empty")
        _validate_vector(self.flow_velocity, "flow_velocity")
        _validate_vector(self.gravity, "gravity")


@dataclass(frozen=True)
class ResolverLineage:
    resolver_version: str
    projection_version: str

    def __post_init__(self) -> None:
        if self.resolver_version != _RESOLVER_VERSION:
            raise ValueError(f"resolver_version must be {_RESOLVER_VERSION}")
        if self.projection_version != _PROJECTION_VERSION:
            raise ValueError(f"projection_version must be {_PROJECTION_VERSION}")


RequiredActionFacts = ActionFacts | UnresolvedInput
RequiredTechniqueCapability = TechniqueCapability | UnresolvedInput
RequiredRigCapability = RigCapability | UnresolvedInput
RequiredEquipmentCapability = EquipmentCapability | UnresolvedInput
RequiredAuthoritativePhysics = AuthoritativePhysics | UnresolvedInput


@dataclass(frozen=True)
class PresentationRealizationInput:
    action_facts: RequiredActionFacts
    technique_capability: RequiredTechniqueCapability
    rig_capability: RequiredRigCapability
    equipment_capability: RequiredEquipmentCapability
    authoritative_physics: RequiredAuthoritativePhysics
    semantic_version: str
    resolver_lineage: ResolverLineage
    authority_mode: AuthorityMode = "authoritative_projection"

    def __post_init__(self) -> None:
        if self.semantic_version != _SEMANTIC_VERSION:
            raise ValueError(f"semantic_version must be {_SEMANTIC_VERSION}")
        if self.authority_mode not in _AUTHORITY_MODES:
            raise ValueError("authority_mode must be authoritative_projection or client_claim")


@dataclass(frozen=True)
class RealizedSpatialFacts:
    origin: Vector3
    end_position: Vector3
    displacement: Vector3

    def __post_init__(self) -> None:
        _validate_vector(self.origin, "origin")
        _validate_vector(self.end_position, "end_position")
        _validate_vector(self.displacement, "displacement")


@dataclass(frozen=True)
class RealizedMotionFacts:
    controlled_velocity: Vector3
    drift_velocity: Vector3
    fall_velocity: Vector3
    realized_average_velocity: Vector3

    def __post_init__(self) -> None:
        _validate_vector(self.controlled_velocity, "controlled_velocity")
        _validate_vector(self.drift_velocity, "drift_velocity")
        _validate_vector(self.fall_velocity, "fall_velocity")
        _validate_vector(
            self.realized_average_velocity,
            "realized_average_velocity",
        )


@dataclass(frozen=True)
class CueEmissionFacts:
    amplitude: float
    cue_tags: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_nonnegative_real(self.amplitude, "cue amplitude")
        _validate_tokens(self.cue_tags, "cue_tags", _CUE_TAG_VOCABULARY)


@dataclass(frozen=True)
class TemporalPhase:
    phase: str
    start_time: float
    end_time: float
    control_scale: float
    displacement: Vector3

    def __post_init__(self) -> None:
        if not self.phase:
            raise ValueError("temporal phase must be non-empty")
        if self.phase not in _PHASE_VOCABULARY:
            raise ValueError(
                "temporal phase labels must come from the closed temporal-phase vocabulary"
            )
        for value in (self.start_time, self.end_time, self.control_scale):
            _validate_finite_real(value, "temporal phase numeric values")
        if self.end_time <= self.start_time:
            raise ValueError("temporal phase end_time must be > start_time")
        if self.control_scale < 0:
            raise ValueError("temporal phase control_scale must be >= 0")
        _validate_vector(self.displacement, "displacement")


@dataclass(frozen=True)
class PresentationProvenance:
    authority_mode: AuthorityMode
    admitted_input_fingerprint: str
    world_snapshot_ref: str
    world_revision: str
    resolver_version: str
    projection_version: str

    def __post_init__(self) -> None:
        if not isinstance(self.authority_mode, str) or (
            self.authority_mode not in _AUTHORITY_MODES
        ):
            raise ValueError("authority_mode must be authoritative_projection or client_claim")
        for value in (
            self.admitted_input_fingerprint,
            self.world_snapshot_ref,
            self.world_revision,
            self.resolver_version,
            self.projection_version,
        ):
            if not isinstance(value, str) or not value:
                raise ValueError("provenance lineage fields must be non-empty strings")


@dataclass(frozen=True)
class ActualPresentation:
    presentation_identity: str
    realized_spatial_facts: RealizedSpatialFacts
    realized_motion_facts: RealizedMotionFacts
    cue_emission_facts: CueEmissionFacts
    target_presentation_descriptors: tuple[str, ...]
    temporal_context: tuple[TemporalPhase, ...]
    completeness: Literal["Resolved"]
    provenance: PresentationProvenance
    semantic_version: str

    def __post_init__(self) -> None:
        if not isinstance(self.presentation_identity, str) or not self.presentation_identity:
            raise ValueError("presentation_identity must be a non-empty string")
        if not isinstance(self.realized_spatial_facts, RealizedSpatialFacts):
            raise ValueError("realized_spatial_facts must be RealizedSpatialFacts")
        if not isinstance(self.realized_motion_facts, RealizedMotionFacts):
            raise ValueError("realized_motion_facts must be RealizedMotionFacts")
        if not isinstance(self.cue_emission_facts, CueEmissionFacts):
            raise ValueError("cue_emission_facts must be CueEmissionFacts")
        _validate_tokens(
            self.target_presentation_descriptors,
            "target_presentation_descriptors",
            _PRESENTATION_DESCRIPTOR_VOCABULARY,
        )
        if not isinstance(self.temporal_context, tuple):
            raise ValueError("temporal_context must be a tuple")
        if not self.temporal_context:
            raise ValueError("temporal_context must contain at least one TemporalPhase")
        if any(not isinstance(phase, TemporalPhase) for phase in self.temporal_context):
            raise ValueError("temporal_context must contain TemporalPhase values")
        if self.completeness != "Resolved":
            raise ValueError("completeness must be Resolved")
        if not isinstance(self.provenance, PresentationProvenance):
            raise ValueError("provenance must be PresentationProvenance")
        if not isinstance(self.semantic_version, str) or not self.semantic_version:
            raise ValueError("semantic_version must be a non-empty string")


@dataclass(frozen=True)
class RealizationResult:
    presentation: ActualPresentation | None
    unresolved: tuple[tuple[str, ResolutionStatus, str], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.unresolved, tuple):
            raise ValueError("unresolved must be a tuple")

    @property
    def is_resolved(self) -> bool:
        return self.presentation is not None


def realize_actual_presentation(source: PresentationRealizationInput) -> RealizationResult:
    """Project admitted inputs into fish-agnostic realized Presentation semantics.

    This intentionally small deterministic projection is a Reference boundary,
    not a Production physics simulator or an authority promotion mechanism.
    """

    unresolved = _collect_unresolved(source)
    if unresolved:
        return RealizationResult(presentation=None, unresolved=unresolved)

    action = _require_type(source.action_facts, ActionFacts)
    technique = _require_type(source.technique_capability, TechniqueCapability)
    rig = _require_type(source.rig_capability, RigCapability)
    equipment = _require_type(source.equipment_capability, EquipmentCapability)
    physics = _require_type(source.authoritative_physics, AuthoritativePhysics)

    phases = _normalize_phases(action.phases)
    origin = _canonical_vector(action.origin)
    commanded_velocity = _canonical_vector(action.commanded_velocity)
    technique_action_gain = _canonical_float(technique.action_gain)
    equipment_motion_gain = _canonical_float(equipment.motion_gain)
    flow_velocity = _canonical_vector(physics.flow_velocity)
    gravity = _canonical_vector(physics.gravity)
    flow_coupling = _canonical_float(rig.flow_coupling)
    gravity_coupling = _canonical_float(rig.gravity_coupling)
    base_controlled_velocity = _scale(
        commanded_velocity,
        _multiply(technique_action_gain, equipment_motion_gain),
    )
    drift_velocity = _scale(flow_velocity, flow_coupling)
    fall_velocity = _scale(gravity, gravity_coupling)
    environmental_velocity = _add(drift_velocity, fall_velocity)

    temporal: list[TemporalPhase] = []
    displacement = Vector3(0.0, 0.0, 0.0)
    total_duration = 0.0
    for phase in phases:
        controlled = _scale(base_controlled_velocity, phase.control_scale)
        realized = _add(controlled, environmental_velocity)
        duration = _subtract(phase.end_time, phase.start_time)
        phase_displacement = _scale(realized, duration)
        displacement = _add(displacement, phase_displacement)
        total_duration = _add_numbers(total_duration, duration)
        temporal.append(
            TemporalPhase(
                phase=phase.phase,
                start_time=phase.start_time,
                end_time=phase.end_time,
                control_scale=phase.control_scale,
                displacement=phase_displacement,
            )
        )

    if total_duration <= 0:
        raise AssertionError("normalized temporal duration must be positive")

    controlled_distance = Vector3(0.0, 0.0, 0.0)
    for phase in phases:
        phase_duration = _subtract(phase.end_time, phase.start_time)
        controlled_distance = _add(
            controlled_distance,
            _scale(
                base_controlled_velocity,
                _multiply(phase_duration, phase.control_scale),
            ),
        )
    inverse_total_duration = _divide(1.0, total_duration)
    controlled_average = _scale(controlled_distance, inverse_total_duration)
    realized_average = _scale(displacement, inverse_total_duration)

    cue_amplitude = _multiply(
        _multiply(action.cue_drive, technique.cue_gain),
        equipment.cue_gain,
    )
    descriptors = tuple(
        sorted(set(technique.presentation_descriptors + equipment.presentation_descriptors))
    )
    cues = tuple(sorted(set(technique.cue_tags)))
    semantic_projection = {
        "realized_spatial_facts": {
            "origin": origin,
            "end_position": _add(origin, displacement),
            "displacement": displacement,
        },
        "realized_motion_facts": {
            "controlled_velocity": controlled_average,
            "drift_velocity": drift_velocity,
            "fall_velocity": fall_velocity,
            "realized_average_velocity": realized_average,
        },
        "cue_emission_facts": {
            "amplitude": cue_amplitude,
            "cue_tags": cues,
        },
        "target_presentation_descriptors": descriptors,
        "temporal_context": tuple(temporal),
        "completeness": "Resolved",
        "semantic_version": source.semantic_version,
    }
    validate_canonical_payload(semantic_projection)
    identity = "ap:" + sha256(_canonical_json_bytes(semantic_projection)).hexdigest()
    provenance = PresentationProvenance(
        authority_mode=source.authority_mode,
        admitted_input_fingerprint=_input_fingerprint(source),
        world_snapshot_ref=physics.world_snapshot_ref,
        world_revision=physics.world_revision,
        resolver_version=source.resolver_lineage.resolver_version,
        projection_version=source.resolver_lineage.projection_version,
    )
    presentation = ActualPresentation(
        presentation_identity=identity,
        realized_spatial_facts=RealizedSpatialFacts(
            origin=origin,
            end_position=_add(origin, displacement),
            displacement=displacement,
        ),
        realized_motion_facts=RealizedMotionFacts(
            controlled_velocity=controlled_average,
            drift_velocity=drift_velocity,
            fall_velocity=fall_velocity,
            realized_average_velocity=realized_average,
        ),
        cue_emission_facts=CueEmissionFacts(
            amplitude=cue_amplitude,
            cue_tags=cues,
        ),
        target_presentation_descriptors=descriptors,
        temporal_context=tuple(temporal),
        completeness="Resolved",
        provenance=provenance,
        semantic_version=source.semantic_version,
    )
    return RealizationResult(presentation=presentation, unresolved=())


def validate_actual_presentation(
    presentation: ActualPresentation,
    admitted_input: PresentationRealizationInput,
) -> None:
    """Fail closed unless carrier semantics and declared lineage match the input."""

    validate_canonical_payload(asdict(presentation))
    expected_result = realize_actual_presentation(admitted_input)
    if expected_result.presentation is None:
        raise PresentationContractViolation(
            "PRESENTATION_INPUT_UNRESOLVED",
            "input",
            "an ActualPresentation cannot validate against unresolved required input",
        )
    expected = expected_result.presentation

    comparisons = (
        (
            presentation.semantic_version == admitted_input.semantic_version,
            "SEMANTIC_VERSION_MISMATCH",
            "semantic_version",
        ),
        (
            presentation.provenance.resolver_version
            == admitted_input.resolver_lineage.resolver_version,
            "RESOLVER_LINEAGE_MISMATCH",
            "provenance.resolver_version",
        ),
        (
            presentation.provenance.projection_version
            == admitted_input.resolver_lineage.projection_version,
            "PROJECTION_VERSION_MISMATCH",
            "provenance.projection_version",
        ),
        (
            presentation.provenance.admitted_input_fingerprint
            == _input_fingerprint(admitted_input),
            "INPUT_FINGERPRINT_MISMATCH",
            "provenance.admitted_input_fingerprint",
        ),
        (
            presentation.presentation_identity == expected.presentation_identity,
            "PRESENTATION_IDENTITY_MISMATCH",
            "presentation_identity",
        ),
        (
            semantic_bytes(presentation) == semantic_bytes(expected),
            "PRESENTATION_PROJECTION_MISMATCH",
            "presentation",
        ),
        (
            carrier_bytes(presentation) == carrier_bytes(expected),
            "PRESENTATION_LINEAGE_MISMATCH",
            "provenance",
        ),
    )
    for matches, code, path in comparisons:
        if not matches:
            raise PresentationContractViolation(code, path, "declared carrier does not match")


def validate_canonical_payload(payload: Any) -> None:
    """Reject non-Presentation structure and downstream-owned concepts wherever they occur.

    Admission is layered fail-closed: the schema pass first admits only
    Presentation-owned structure, scalar positions and numeric leaves; the concept
    scan then attributes known downstream concepts at admitted positions to typed
    violation codes; the vocabulary pass finally enforces closed vocabularies.
    """

    def validate_owned_text(text: str, path: str) -> None:
        normalized = re.sub(r"[^a-z0-9]", "", text.casefold())
        if normalized in _INTERACTION_ANTI_FIELDS or any(
            fragment in normalized for fragment in _INTERACTION_KEY_FRAGMENTS
        ):
            raise PresentationContractViolation(
                "INTERACTION_FIELD_FORBIDDEN",
                path,
                "Fish perception/response and capture outcomes are downstream-owned",
            )
        if normalized in _OPPORTUNITY_ANTI_FIELDS or any(
            fragment in normalized for fragment in _OPPORTUNITY_KEY_FRAGMENTS
        ):
            raise PresentationContractViolation(
                "OPPORTUNITY_FIELD_FORBIDDEN",
                path,
                "Opportunity formation/lifecycle and Candidate evaluation are downstream-owned",
            )
        if normalized in _FISH_ANTI_FIELDS or any(
            fragment in normalized for fragment in _FISH_KEY_FRAGMENTS
        ):
            raise PresentationContractViolation(
                "FISH_SPECIFIC_FIELD_FORBIDDEN",
                path,
                "Fish-specific or evaluative fields are not Presentation truth",
            )

    def visit(value: Any, path: str, *, inspect_text: bool = True) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                key_text = str(key)
                normalized_key = re.sub(r"[^a-z0-9]", "", key_text.casefold())
                child_path = f"{path}.{key_text}" if path else key_text
                validate_owned_text(key_text, child_path)
                visit(
                    child,
                    child_path,
                    inspect_text=normalized_key not in _OPAQUE_TEXT_FIELDS,
                )
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]", inspect_text=inspect_text)
        elif is_dataclass(value) and not isinstance(value, type):
            visit(asdict(value), path, inspect_text=inspect_text)
        elif isinstance(value, str) and inspect_text:
            validate_owned_text(value, path)

    _check_canonical_schema(payload, "", "root")
    visit(payload, "")
    _check_canonical_vocabulary(payload, "", "root")


def _check_canonical_schema(value: Any, path: str, context: str) -> None:
    """Admit only Presentation-owned canonical structure and scalar types fail-closed."""

    if is_dataclass(value) and not isinstance(value, type):
        _check_canonical_schema(asdict(value), path, context)
        return
    if isinstance(value, Mapping):
        allowed = _SCHEMA_ALLOWED_KEYS.get(context)
        if allowed is None:
            raise PresentationContractViolation(
                "UNKNOWN_FIELD_FORBIDDEN",
                path,
                "unexpected mapping in a canonical Presentation payload",
            )
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}" if path else key_text
            if key_text not in allowed:
                raise PresentationContractViolation(
                    "UNKNOWN_FIELD_FORBIDDEN",
                    child_path,
                    "canonical Presentation payloads admit only Presentation-owned fields",
                )
            child_context = _schema_child_context(context, key_text)
            if child_context is not None:
                _check_canonical_schema(child, child_path, child_context)
            elif context == "phase" and key_text == "phase":
                _require_canonical_string(child, child_path, "temporal phase label")
            elif context == "root" and key_text == "completeness":
                _require_canonical_string(child, child_path, "completeness")
            elif context == "cue" and key_text == "amplitude":
                _require_canonical_number(child, child_path)
            elif context == "vector":
                _require_canonical_number(child, child_path)
            elif context == "phase" and key_text in (
                "start_time",
                "end_time",
                "control_scale",
            ):
                _require_canonical_number(child, child_path)
            elif isinstance(child, Mapping) or (
                isinstance(child, Sequence) and not isinstance(child, (str, bytes, bytearray))
            ):
                raise PresentationContractViolation(
                    "UNKNOWN_FIELD_FORBIDDEN",
                    child_path,
                    "unexpected nested structure beneath a scalar Presentation field",
                )
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        item_context = _SCHEMA_SEQUENCE_ITEM_CONTEXTS.get(context)
        if item_context is None:
            raise PresentationContractViolation(
                "UNKNOWN_FIELD_FORBIDDEN",
                path,
                "unexpected sequence in a canonical Presentation payload",
            )
        for index, child in enumerate(value):
            _check_canonical_schema(child, f"{path}[{index}]", item_context)
        return
    if context in ("temporal_list", "descriptor_list", "cue_tag_list"):
        raise PresentationContractViolation(
            "UNKNOWN_FIELD_FORBIDDEN",
            path,
            "expected a sequence of Presentation-owned values",
        )
    if context == "descriptor":
        _require_canonical_string(value, path, "presentation descriptor")
        return
    if context == "cue_tag":
        _require_canonical_string(value, path, "cue tag")
        return
    raise PresentationContractViolation(
        "UNKNOWN_FIELD_FORBIDDEN",
        path or "<root>",
        "unexpected scalar in a canonical Presentation payload",
    )


def _check_canonical_vocabulary(value: Any, path: str, context: str) -> None:
    """Enforce closed vocabularies at concept-scanned canonical positions."""

    if is_dataclass(value) and not isinstance(value, type):
        _check_canonical_vocabulary(asdict(value), path, context)
        return
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}" if path else key_text
            child_context = _schema_child_context(context, key_text)
            if child_context is not None:
                _check_canonical_vocabulary(child, child_path, child_context)
            elif context == "phase" and key_text == "phase":
                _require_closed_vocabulary(
                    child,
                    child_path,
                    _PHASE_VOCABULARY,
                    "temporal phase label",
                )
            elif context == "root" and key_text == "completeness":
                _require_closed_vocabulary(
                    child,
                    child_path,
                    frozenset({"Resolved"}),
                    "completeness",
                )
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        item_context = _SCHEMA_SEQUENCE_ITEM_CONTEXTS.get(context)
        for index, child in enumerate(value):
            child_path = f"{path}[{index}]"
            if item_context == "descriptor":
                _require_closed_vocabulary(
                    child,
                    child_path,
                    _PRESENTATION_DESCRIPTOR_VOCABULARY,
                    "presentation descriptor",
                )
            elif item_context == "cue_tag":
                _require_closed_vocabulary(
                    child,
                    child_path,
                    _CUE_TAG_VOCABULARY,
                    "cue tag",
                )
            else:
                _check_canonical_vocabulary(child, child_path, item_context or context)
        return


def _schema_child_context(context: str, key_text: str) -> str | None:
    if context == "root":
        return _SCHEMA_ROOT_CHILD_CONTEXTS.get(key_text)
    if context in ("spatial", "motion"):
        return "vector"
    if context == "phase":
        return "vector" if key_text == "displacement" else None
    if context == "cue":
        return "cue_tag_list" if key_text == "cue_tags" else None
    return None


def _require_closed_vocabulary(
    value: Any,
    path: str,
    vocabulary: frozenset[str],
    label: str,
) -> None:
    if not isinstance(value, str) or value not in vocabulary:
        raise PresentationContractViolation(
            "CLOSED_VOCABULARY_FORBIDDEN",
            path,
            f"{label} must come from the closed Presentation-owned vocabulary",
        )


def _require_canonical_string(value: Any, path: str, label: str) -> None:
    if not isinstance(value, str):
        raise PresentationContractViolation(
            "UNKNOWN_FIELD_FORBIDDEN",
            path,
            f"{label} must be a string in a canonical Presentation payload",
        )


def _require_canonical_number(value: Any, path: str) -> None:
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value):
        raise PresentationContractViolation(
            "NUMERIC_CONTRACT_FORBIDDEN",
            path,
            "canonical numeric leaves must be non-boolean finite real numbers",
        )


def semantic_bytes(presentation: ActualPresentation) -> bytes:
    """Canonical downstream semantic projection, excluding cause/authority lineage."""

    payload = asdict(presentation)
    payload.pop("provenance")
    return _canonical_json_bytes(payload)


def carrier_bytes(presentation: ActualPresentation) -> bytes:
    """Canonical complete Reference carrier, including provenance and authority mode."""

    return _canonical_json_bytes(presentation)


def semantically_equivalent(left: ActualPresentation, right: ActualPresentation) -> bool:
    return semantic_bytes(left) == semantic_bytes(right)


def _collect_unresolved(
    source: PresentationRealizationInput,
) -> tuple[tuple[str, ResolutionStatus, str], ...]:
    unresolved: list[tuple[str, ResolutionStatus, str]] = []
    for field_name in (
        "action_facts",
        "technique_capability",
        "rig_capability",
        "equipment_capability",
        "authoritative_physics",
    ):
        value = getattr(source, field_name)
        if isinstance(value, UnresolvedInput):
            unresolved.append((field_name, value.status, value.detail))
    return tuple(unresolved)


def _normalize_phases(phases: Sequence[ActionPhase]) -> tuple[ActionPhase, ...]:
    ordered = sorted(
        (
            ActionPhase(
                phase=phase.phase,
                start_time=_canonical_float(phase.start_time),
                end_time=_canonical_float(phase.end_time),
                control_scale=_canonical_float(phase.control_scale),
            )
            for phase in phases
        ),
        key=lambda phase: (phase.start_time, phase.end_time, phase.phase),
    )
    normalized: list[ActionPhase] = []
    for phase in ordered:
        if normalized and phase.start_time < normalized[-1].end_time:
            raise ValueError("action phases must not overlap")
        if (
            normalized
            and phase.start_time == normalized[-1].end_time
            and phase.phase == normalized[-1].phase
            and phase.control_scale == normalized[-1].control_scale
        ):
            previous = normalized[-1]
            normalized[-1] = ActionPhase(
                previous.phase,
                previous.start_time,
                phase.end_time,
                previous.control_scale,
            )
        else:
            normalized.append(phase)
    return tuple(normalized)


def _input_fingerprint(source: PresentationRealizationInput) -> str:
    return sha256(_canonical_json_bytes(source)).hexdigest()


def _canonical_json_bytes(value: Any) -> bytes:
    normalized = _to_canonical(value)
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _to_canonical(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _to_canonical(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _to_canonical(child) for key, child in value.items()}
    if isinstance(value, tuple | list):
        return [_to_canonical(child) for child in value]
    if isinstance(value, Real) and not isinstance(value, bool):
        return _canonical_float(value)
    return value


def _canonical_float(value: Real) -> float:
    numeric = float(value)
    if not isfinite(numeric):
        raise ValueError("canonical numeric values must be finite")
    rounded = round(numeric, _CANONICAL_DIGITS)
    return 0.0 if rounded == 0 else rounded


def _canonical_vector(vector: Vector3) -> Vector3:
    return Vector3(
        _canonical_float(vector.x),
        _canonical_float(vector.y),
        _canonical_float(vector.z),
    )


def _add_numbers(left: Real, right: Real) -> float:
    return _canonical_float(_canonical_float(left) + _canonical_float(right))


def _subtract(left: Real, right: Real) -> float:
    return _canonical_float(_canonical_float(left) - _canonical_float(right))


def _multiply(left: Real, right: Real) -> float:
    return _canonical_float(_canonical_float(left) * _canonical_float(right))


def _divide(numerator: Real, denominator: Real) -> float:
    return _canonical_float(_canonical_float(numerator) / _canonical_float(denominator))


def _add(left: Vector3, right: Vector3) -> Vector3:
    canonical_left = _canonical_vector(left)
    canonical_right = _canonical_vector(right)
    return Vector3(
        _add_numbers(canonical_left.x, canonical_right.x),
        _add_numbers(canonical_left.y, canonical_right.y),
        _add_numbers(canonical_left.z, canonical_right.z),
    )


def _scale(vector: Vector3, scalar: Real) -> Vector3:
    canonical_vector = _canonical_vector(vector)
    canonical_scalar = _canonical_float(scalar)
    return Vector3(
        _multiply(canonical_vector.x, canonical_scalar),
        _multiply(canonical_vector.y, canonical_scalar),
        _multiply(canonical_vector.z, canonical_scalar),
    )


def _require_type(value: Any, expected_type: type[Any]) -> Any:
    if not isinstance(value, expected_type):
        raise AssertionError(f"expected resolved {expected_type.__name__}")
    return value


def _validate_capability(identity: str, first: float, second: float) -> None:
    if not identity:
        raise ValueError("capability identity must be non-empty")
    for value in (first, second):
        _validate_nonnegative_real(value, "capability gains")


def _validate_vector(value: Any, field_name: str) -> None:
    if not isinstance(value, Vector3):
        raise ValueError(f"{field_name} must be a Vector3")


def _validate_finite_real(value: Any, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value):
        raise ValueError(f"{field_name} must be a finite real number")


def _validate_nonnegative_real(value: Any, field_name: str) -> None:
    _validate_finite_real(value, field_name)
    if value < 0:
        raise ValueError(f"{field_name} must be >= 0")


def _validate_tokens(
    tokens: Sequence[str],
    field_name: str,
    vocabulary: frozenset[str] | None = None,
) -> None:
    if not isinstance(tokens, tuple):
        raise ValueError(f"{field_name} must be a tuple")
    for token in tokens:
        if not isinstance(token, str) or not token:
            raise ValueError(f"{field_name} entries must be non-empty strings")
        if vocabulary is not None and token not in vocabulary:
            raise ValueError(
                f"{field_name} entries must come from the closed Presentation-owned vocabulary"
            )

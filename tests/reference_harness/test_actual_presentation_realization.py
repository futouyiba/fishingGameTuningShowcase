from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from opportunity_reference import (
    EvaluationPolicy,
    FormationPolicy,
    MeasureSpan,
    OpportunitySemanticFixture,
    ProgressSlot,
    resolve_opportunity_semantic_fixture,
)
from presentation_realization_reference import (
    ActionFacts,
    ActionPhase,
    AuthoritativePhysics,
    CueEmissionFacts,
    EquipmentCapability,
    PresentationContractViolation,
    PresentationRealizationInput,
    RealizedMotionFacts,
    RealizedSpatialFacts,
    ResolverLineage,
    RigCapability,
    TechniqueCapability,
    TemporalPhase,
    UnresolvedInput,
    Vector3,
    carrier_bytes,
    realize_actual_presentation,
    semantic_bytes,
    semantically_equivalent,
    validate_actual_presentation,
    validate_canonical_payload,
)


def _source(
    *,
    equipment_id: str = "item:minnow-01",
    technique_id: str = "technique:retrieve-01",
    rig_id: str = "rig:light-01",
    flow: Vector3 | None = None,
    world_ref: str = "world:snapshot-17",
    world_revision: str = "world-rev-17",
    phases: tuple[ActionPhase, ...] | None = None,
) -> PresentationRealizationInput:
    return PresentationRealizationInput(
        action_facts=ActionFacts(
            action_id="action:cast-42",
            origin=Vector3(10.0, 2.0, -1.0),
            commanded_velocity=Vector3(1.0, 0.5, 0.0),
            cue_drive=0.8,
            phases=phases
            or (
                ActionPhase("pause", 0.0, 2.0, 0.0),
                ActionPhase("retrieve", 2.0, 6.0, 1.0),
            ),
        ),
        technique_capability=TechniqueCapability(
            technique_id=technique_id,
            action_gain=1.2,
            cue_gain=0.75,
            cue_tags=("pressure-wave", "visual-motion"),
            presentation_descriptors=("bounded-retrieve",),
        ),
        rig_capability=RigCapability(
            rig_id=rig_id,
            flow_coupling=0.5,
            gravity_coupling=0.1,
        ),
        equipment_capability=EquipmentCapability(
            equipment_id=equipment_id,
            motion_gain=0.9,
            cue_gain=1.1,
            presentation_descriptors=("single-target",),
        ),
        authoritative_physics=AuthoritativePhysics(
            world_snapshot_ref=world_ref,
            world_revision=world_revision,
            flow_velocity=flow if flow is not None else Vector3(0.25, 0.0, 0.0),
            gravity=Vector3(0.0, 0.0, -9.81),
        ),
        semantic_version="actual-presentation/v1",
        resolver_lineage=ResolverLineage(
            resolver_version="reference-resolver/v1",
            projection_version="reference-kinematic-projection/v1",
        ),
    )


def _presentation(source: PresentationRealizationInput | None = None):
    result = realize_actual_presentation(source or _source())
    assert result.presentation is not None
    assert result.unresolved == ()
    return result.presentation


def test_ap01_same_realization_is_independent_of_external_species_choice() -> None:
    """AP-01: Species is neither an input nor a semantic output of realization."""

    presentation_by_species = {
        species: _presentation() for species in ("fish:trout", "fish:carp", "fish:tuna")
    }

    assert len({semantic_bytes(value) for value in presentation_by_species.values()}) == 1
    assert "species" not in semantic_bytes(_presentation()).decode().casefold()


def test_ap02_different_content_ids_with_same_capabilities_have_same_semantics() -> None:
    """AP-02: content identities remain causes, not realization identity setters."""

    first = _presentation()
    second = _presentation(
        _source(
            equipment_id="item:unrelated-catalog-id",
            technique_id="technique:alternate-id",
            rig_id="rig:alternate-id",
        )
    )

    assert first.presentation_identity == second.presentation_identity
    assert semantically_equivalent(first, second)
    assert first.provenance.admitted_input_fingerprint != (
        second.provenance.admitted_input_fingerprint
    )


def test_ap03_authoritative_flow_changes_realized_motion_and_position() -> None:
    """AP-03: authoritative physics affects derived Presentation facts."""

    still = _presentation(_source(flow=Vector3(0.0, 0.0, 0.0)))
    flowing = _presentation(_source(flow=Vector3(2.0, -1.0, 0.0)))

    assert still.realized_motion_facts.drift_velocity != (
        flowing.realized_motion_facts.drift_velocity
    )
    assert still.realized_spatial_facts.end_position != flowing.realized_spatial_facts.end_position
    assert still.presentation_identity != flowing.presentation_identity


@pytest.mark.parametrize(
    "field_name",
    (
        "preferred_layer_for_fish:trout",
        "species_id",
    ),
)
def test_ap04_fish_specific_field_injection_is_rejected_recursively(
    field_name: str,
) -> None:
    """AP-04: fish-specific/evaluative fields cannot enter canonical Presentation."""

    with pytest.raises(PresentationContractViolation) as exc_info:
        validate_canonical_payload(
            {"cue_emission_facts": {"amplitude": 1.0, field_name: "surface"}}
        )

    assert exc_info.value.code == "UNKNOWN_FIELD_FORBIDDEN"
    assert exc_info.value.path == f"cue_emission_facts.{field_name}"


def test_ap04_fish_specific_value_injection_is_rejected_before_realization() -> None:
    source = _source()

    with pytest.raises(ValueError, match="closed Presentation-owned vocabulary"):
        replace(
            source.technique_capability,
            presentation_descriptors=("species:trout",),
        )
    with pytest.raises(PresentationContractViolation) as exc_info:
        validate_canonical_payload({"target_presentation_descriptors": ["species:trout"]})

    assert exc_info.value.code == "FISH_SPECIFIC_FIELD_FORBIDDEN"
    assert exc_info.value.path == "target_presentation_descriptors[0]"


def test_ap04_unrecognized_ownership_synonyms_fail_closed() -> None:
    """AP-04: admission is allowlist-based, so unlisted synonyms cannot enter."""

    source = _source()

    with pytest.raises(ValueError, match="closed Presentation-owned vocabulary"):
        replace(
            source.technique_capability,
            presentation_descriptors=("trout-preferred",),
        )
    with pytest.raises(ValueError, match="closed Presentation-owned vocabulary"):
        replace(
            source.equipment_capability,
            presentation_descriptors=("strike-likelihood",),
        )
    with pytest.raises(ValueError, match="closed Presentation-owned vocabulary"):
        replace(source.technique_capability, cue_tags=("ticket-rate",))
    with pytest.raises(ValueError, match="closed action-phase vocabulary"):
        ActionPhase("strike-window", 0.0, 1.0)
    with pytest.raises(PresentationContractViolation) as exc_info:
        validate_canonical_payload({"nested": {"ticket_rate": 2.0, "strike_likelihood": 0.9}})

    assert exc_info.value.code == "UNKNOWN_FIELD_FORBIDDEN"
    assert exc_info.value.path == "nested"


@pytest.mark.parametrize("field_name", ("cadence", "opportunity_seq"))
def test_ap05_opportunity_field_injection_is_rejected_recursively(
    field_name: str,
) -> None:
    """AP-05: cadence and Opportunity lifecycle remain downstream-owned."""

    with pytest.raises(PresentationContractViolation) as exc_info:
        validate_canonical_payload({"temporal_context": [{"phase": "pause", field_name: 3.0}]})

    assert exc_info.value.code == "UNKNOWN_FIELD_FORBIDDEN"
    assert exc_info.value.path == f"temporal_context[0].{field_name}"


def test_ap05_opportunity_value_injection_is_rejected_before_realization() -> None:
    with pytest.raises(ValueError, match="closed action-phase vocabulary"):
        ActionPhase("opportunity-formation", 0.0, 1.0)
    with pytest.raises(PresentationContractViolation) as exc_info:
        validate_canonical_payload({"temporal_context": [{"phase": "opportunity-formation"}]})

    assert exc_info.value.code == "OPPORTUNITY_FIELD_FORBIDDEN"
    assert exc_info.value.path == "temporal_context[0].phase"


@pytest.mark.parametrize(
    "field_name",
    ("perceptual_outcome", "fish_response", "capture_retention"),
)
def test_ap06_interaction_field_injection_is_rejected_recursively(
    field_name: str,
) -> None:
    """AP-06: fish perception and response fields remain Interaction-owned."""

    with pytest.raises(PresentationContractViolation) as exc_info:
        validate_canonical_payload(
            {"provenance": {"resolver_version": "reference-resolver/v1", field_name: "noticed"}}
        )

    assert exc_info.value.code == "UNKNOWN_FIELD_FORBIDDEN"
    assert exc_info.value.path == f"provenance.{field_name}"


def test_ap06_interaction_value_injection_is_rejected_before_realization() -> None:
    source = _source()

    with pytest.raises(ValueError, match="closed Presentation-owned vocabulary"):
        replace(source.technique_capability, cue_tags=("fish-response",))
    with pytest.raises(PresentationContractViolation) as exc_info:
        validate_canonical_payload({"cue_emission_facts": {"cue_tags": ["fish-response"]}})

    assert exc_info.value.code == "INTERACTION_FIELD_FORBIDDEN"
    assert exc_info.value.path == "cue_emission_facts.cue_tags[0]"


def test_ap07_unresolved_status_rejects_values_outside_the_closed_type() -> None:
    """AP-07: runtime construction enforces the declared closed status vocabulary."""

    with pytest.raises(ValueError, match="unresolved input status"):
        UnresolvedInput(status="Resolved", detail="not an unresolved state")


@pytest.mark.parametrize(
    ("field_name", "status"),
    [
        ("action_facts", "Unknown"),
        ("technique_capability", "Unsupported"),
        ("rig_capability", "InsufficientEvidence"),
        ("equipment_capability", "Unknown"),
        ("authoritative_physics", "Unsupported"),
    ],
)
def test_ap07_required_unknowns_remain_typed_and_do_not_default_to_neutral(
    field_name: str,
    status: str,
) -> None:
    """AP-07: unresolved required inputs cannot fabricate numeric realization."""

    source = replace(
        _source(),
        **{field_name: UnresolvedInput(status=status, detail=f"missing {field_name}")},
    )
    result = realize_actual_presentation(source)

    assert result.presentation is None
    assert result.unresolved == ((field_name, status, f"missing {field_name}"),)


def test_ap08_world_truth_remains_lineage_while_output_contains_only_derived_facts() -> None:
    """AP-08: World is referenced as authority, not copied into competing truth."""

    presentation = _presentation(
        _source(world_ref="world:snapshot-99", world_revision="world-rev-99")
    )
    semantic_payload = semantic_bytes(presentation).decode()

    assert presentation.provenance.world_snapshot_ref == "world:snapshot-99"
    assert presentation.provenance.world_revision == "world-rev-99"
    assert "world:snapshot-99" not in semantic_payload
    assert "world-rev-99" not in semantic_payload
    assert presentation.realized_motion_facts.drift_velocity == Vector3(0.125, 0.0, 0.0)


@pytest.mark.parametrize(
    ("mutator", "code"),
    [
        (
            lambda value: replace(value, semantic_version="actual-presentation/v999"),
            "SEMANTIC_VERSION_MISMATCH",
        ),
        (
            lambda value: replace(
                value,
                provenance=replace(value.provenance, resolver_version="other-resolver/v1"),
            ),
            "RESOLVER_LINEAGE_MISMATCH",
        ),
        (
            lambda value: replace(
                value,
                provenance=replace(value.provenance, projection_version="other-projection/v1"),
            ),
            "PROJECTION_VERSION_MISMATCH",
        ),
        (
            lambda value: replace(
                value,
                provenance=replace(value.provenance, admitted_input_fingerprint="0" * 64),
            ),
            "INPUT_FINGERPRINT_MISMATCH",
        ),
        (
            lambda value: replace(value, presentation_identity="ap:" + "0" * 64),
            "PRESENTATION_IDENTITY_MISMATCH",
        ),
    ],
)
def test_ap09_version_or_lineage_mismatch_fails_closed(mutator, code: str) -> None:
    """AP-09: semantic version, lineage, fingerprint, and identity are validated."""

    source = _source()
    with pytest.raises(PresentationContractViolation) as exc_info:
        validate_actual_presentation(mutator(_presentation(source)), source)

    assert exc_info.value.code == code


def test_ap09_unsupported_input_contract_labels_fail_before_realization() -> None:
    source = _source()

    with pytest.raises(ValueError, match="semantic_version"):
        replace(source, semantic_version="actual-presentation/v999")
    with pytest.raises(ValueError, match="resolver_version"):
        replace(
            source,
            resolver_lineage=ResolverLineage(
                resolver_version="other-resolver/v1",
                projection_version="reference-kinematic-projection/v1",
            ),
        )
    with pytest.raises(ValueError, match="projection_version"):
        replace(
            source,
            resolver_lineage=ResolverLineage(
                resolver_version="reference-resolver/v1",
                projection_version="other-projection/v1",
            ),
        )
    with pytest.raises(ValueError, match="authority_mode"):
        replace(source, authority_mode="root_claim")


def test_ap10_deterministic_replay_and_numeric_canonicalization() -> None:
    """AP-10: replay and insignificant numeric representation noise canonicalize."""

    source = _source()
    replayed = tuple(_presentation(source) for _ in range(3))
    noisy_action = replace(
        source.action_facts,
        origin=Vector3(10.0 + 1e-12, 2.0, -1.0),
        commanded_velocity=Vector3(1.0, 0.5 + 1e-12, -0.0),
    )
    noisy = _presentation(replace(source, action_facts=noisy_action))

    assert len({carrier_bytes(value) for value in replayed}) == 1
    assert semantically_equivalent(replayed[0], noisy)
    assert replayed[0].presentation_identity == noisy.presentation_identity
    assert replayed[0].provenance.admitted_input_fingerprint == (
        noisy.provenance.admitted_input_fingerprint
    )
    assert noisy.realized_spatial_facts.origin == Vector3(10.0, 2.0, -1.0)
    assert noisy.realized_spatial_facts.origin.x == 10.0


def test_ap10_subprecision_inputs_are_canonicalized_before_amplification() -> None:
    source = _source()
    equipment = replace(source.equipment_capability, motion_gain=1_000_000_000.0)
    baseline = _presentation(replace(source, equipment_capability=equipment))
    noisy_action = replace(
        source.action_facts,
        commanded_velocity=Vector3(1.0000000004, 0.5, 0.0),
    )
    noisy = _presentation(
        replace(
            source,
            action_facts=noisy_action,
            equipment_capability=equipment,
        )
    )

    assert baseline.provenance.admitted_input_fingerprint == (
        noisy.provenance.admitted_input_fingerprint
    )
    assert baseline.presentation_identity == noisy.presentation_identity
    assert semantic_bytes(baseline) == semantic_bytes(noisy)
    assert carrier_bytes(baseline) == carrier_bytes(noisy)


def test_ap10_equivalent_real_number_representations_have_identical_bytes() -> None:
    source = _source()
    integer_action = replace(source.action_facts, cue_drive=1)
    float_action = replace(source.action_facts, cue_drive=1.0)
    integer_presentation = _presentation(replace(source, action_facts=integer_action))
    float_presentation = _presentation(replace(source, action_facts=float_action))

    assert integer_presentation.provenance.admitted_input_fingerprint == (
        float_presentation.provenance.admitted_input_fingerprint
    )
    assert integer_presentation.presentation_identity == (float_presentation.presentation_identity)
    assert semantic_bytes(integer_presentation) == semantic_bytes(float_presentation)
    assert carrier_bytes(integer_presentation) == carrier_bytes(float_presentation)


def test_ap10_non_contract_numeric_types_fail_closed() -> None:
    source = _source()

    for invalid_cue_drive in (True, Decimal("0.8")):
        with pytest.raises(ValueError, match="finite real number"):
            replace(source.action_facts, cue_drive=invalid_cue_drive)


def test_ap10_output_numeric_types_enforce_the_same_contract() -> None:
    invalid_values = (True, Decimal("1.0"))

    for invalid_value in invalid_values:
        with pytest.raises(ValueError, match="finite real number"):
            CueEmissionFacts(amplitude=invalid_value, cue_tags=())
        with pytest.raises(ValueError, match="finite real number"):
            TemporalPhase(
                phase="retrieve",
                start_time=0.0,
                end_time=1.0,
                control_scale=invalid_value,
                displacement=Vector3(0.0, 0.0, 0.0),
            )


def test_ap10_nested_numeric_carriers_fail_closed_at_construction() -> None:
    source = _source()
    vector = Vector3(0.0, 0.0, 0.0)

    for invalid_vector in (True, Decimal("1.0")):
        with pytest.raises(ValueError, match="must be a Vector3"):
            replace(source.action_facts, origin=invalid_vector)
        with pytest.raises(ValueError, match="must be a Vector3"):
            replace(source.action_facts, commanded_velocity=invalid_vector)
        with pytest.raises(ValueError, match="must be a Vector3"):
            replace(source.authoritative_physics, flow_velocity=invalid_vector)
        with pytest.raises(ValueError, match="must be a Vector3"):
            replace(source.authoritative_physics, gravity=invalid_vector)
        with pytest.raises(ValueError, match="must be a Vector3"):
            RealizedSpatialFacts(
                origin=invalid_vector,
                end_position=vector,
                displacement=vector,
            )
        with pytest.raises(ValueError, match="must be a Vector3"):
            RealizedMotionFacts(
                controlled_velocity=invalid_vector,
                drift_velocity=vector,
                fall_velocity=vector,
                realized_average_velocity=vector,
            )
        with pytest.raises(ValueError, match="must be a Vector3"):
            TemporalPhase(
                phase="retrieve",
                start_time=0.0,
                end_time=1.0,
                control_scale=1.0,
                displacement=invalid_vector,
            )


def test_ap10_carrier_construction_enforces_the_closed_descriptor_vocabulary() -> None:
    presentation = _presentation()

    with pytest.raises(ValueError, match="closed Presentation-owned vocabulary"):
        replace(presentation, target_presentation_descriptors=("strike-likelihood",))


def test_ap10_carriers_reject_mutable_and_malformed_provenance_types() -> None:
    presentation = _presentation()
    source = _source()

    with pytest.raises(ValueError, match="must be a tuple"):
        replace(
            presentation,
            target_presentation_descriptors=list(presentation.target_presentation_descriptors),
        )
    with pytest.raises(ValueError, match="must be a tuple"):
        replace(presentation, temporal_context=list(presentation.temporal_context))
    with pytest.raises(ValueError, match="must be a tuple"):
        replace(source.action_facts, phases=list(source.action_facts.phases))
    with pytest.raises(ValueError, match="non-empty strings"):
        replace(presentation.provenance, admitted_input_fingerprint=[])
    with pytest.raises(ValueError, match="authority_mode"):
        replace(presentation.provenance, authority_mode=17)
    with pytest.raises(ValueError, match="authority_mode"):
        replace(presentation.provenance, authority_mode=[])


def test_ap10_scalar_leaf_positions_reject_nested_structures() -> None:
    for payload in (
        {"presentation_identity": {"ticket_rate": 1}},
        {"semantic_version": {"unknown_field": 1}},
        {"provenance": {"resolver_version": {"unknown_field": 1}}},
        {"cue_emission_facts": {"cue_tags": "pressure-wave"}},
        {"target_presentation_descriptors": "single-target"},
    ):
        with pytest.raises(PresentationContractViolation) as exc_info:
            validate_canonical_payload(payload)

        assert exc_info.value.code == "UNKNOWN_FIELD_FORBIDDEN"


def test_ap10_canonical_numeric_leaves_reject_boolean_and_non_real_values() -> None:
    with pytest.raises(PresentationContractViolation) as amplitude_info:
        validate_canonical_payload({"cue_emission_facts": {"amplitude": True, "cue_tags": []}})

    assert amplitude_info.value.code == "NUMERIC_CONTRACT_FORBIDDEN"
    assert amplitude_info.value.path == "cue_emission_facts.amplitude"

    with pytest.raises(PresentationContractViolation) as component_info:
        validate_canonical_payload(
            {"realized_spatial_facts": {"origin": {"x": True, "y": 0.0, "z": 0.0}}}
        )

    assert component_info.value.code == "NUMERIC_CONTRACT_FORBIDDEN"
    assert component_info.value.path == "realized_spatial_facts.origin.x"

    with pytest.raises(PresentationContractViolation) as phase_info:
        validate_canonical_payload(
            {"temporal_context": [{"phase": "pause", "start_time": Decimal("0.0")}]}
        )

    assert phase_info.value.code == "NUMERIC_CONTRACT_FORBIDDEN"
    assert phase_info.value.path == "temporal_context[0].start_time"


def test_ap11_bounded_temporal_motif_survives_equivalent_segmentation() -> None:
    """AP-11: adjacent equivalent phases merge into one bounded semantic motif."""

    merged = _presentation(
        _source(
            phases=(
                ActionPhase("sink", 0.0, 2.0, 0.0),
                ActionPhase("drift", 2.0, 6.0, 0.25),
            )
        )
    )
    split = _presentation(
        _source(
            phases=(
                ActionPhase("sink", 0.0, 1.0, 0.0),
                ActionPhase("sink", 1.0, 2.0, 0.0),
                ActionPhase("drift", 2.0, 3.5, 0.25),
                ActionPhase("drift", 3.5, 6.0, 0.25),
            )
        )
    )

    assert [phase.phase for phase in split.temporal_context] == ["sink", "drift"]
    assert semantically_equivalent(merged, split)
    assert merged.presentation_identity == split.presentation_identity


def test_ap12_existing_opportunity_adapter_stays_downstream_and_unchanged() -> None:
    """AP-12: a test-local bridge feeds the existing downstream Opportunity API."""

    package_root = Path(__file__).parents[2] / "presentation_realization_reference"
    production_source = "\n".join(path.read_text() for path in package_root.glob("*.py"))
    assert "opportunity_reference" not in production_source

    merged = _presentation(_source(phases=(ActionPhase("retrieve", 0.0, 4.0, 1.0),)))
    split = _presentation(
        _source(
            phases=(
                ActionPhase("retrieve", 0.0, 1.5, 1.0),
                ActionPhase("retrieve", 1.5, 4.0, 1.0),
            )
        )
    )

    assert _opportunity_trace_from_presentation(merged) == _opportunity_trace_from_presentation(
        split
    )
    assert [
        item.occurrence_logical_time for item in _opportunity_trace_from_presentation(merged)
    ] == [2.0, 4.0]


def _opportunity_trace_from_presentation(presentation):
    spans = tuple(
        MeasureSpan(
            span_id=f"presentation-phase:{index}",
            semantic_scope_ref="presentation:active",
            source_scope_id=presentation.presentation_identity,
            measure_ref="qualified-time",
            start_time=phase.start_time,
            end_time=phase.end_time,
            formation_mass=phase.end_time - phase.start_time,
            phase=phase.phase,
        )
        for index, phase in enumerate(presentation.temporal_context)
    )
    fixture = OpportunitySemanticFixture(
        active_channel_ref="channel:reference",
        formation_policy=FormationPolicy(
            slots=(
                ProgressSlot(
                    slot_id="slot:qualified-time",
                    opportunity_meaning="reference-qualified-time",
                    measure_ref="qualified-time",
                    semantic_scope_ref="presentation:active",
                    threshold=2.0,
                    occurrence_mode="renewal",
                    evaluation_policy_id="policy:time",
                ),
            )
        ),
        evaluation_policies={
            "policy:time": EvaluationPolicy(
                evaluation_policy_id="policy:time",
                support_scope_ref="formation_interval",
                base_measure_ref="time",
            )
        },
        semantic_source_trace=spans,
    )
    return resolve_opportunity_semantic_fixture(fixture)

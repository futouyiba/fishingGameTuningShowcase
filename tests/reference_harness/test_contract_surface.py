from __future__ import annotations

import pytest

from candidate_weight_reference import (
    ContractViolation,
    derive_has_eligible_response_mode,
    read_capture_runtime_surface,
    read_local_species_intensity_surface,
    read_readiness_public_surface,
)


def _canonical_readiness_packet() -> dict[str, object]:
    """Fixture I1 baseline: no globalAvailability field is required."""
    return {
        "activeBehavioralStates": ["NORMAL"],
        "motivationProfile": {"feeding": 0.7},
        "enabledResponseModes": ["FEEDING"],
    }


def test_readiness_internal_explain_cannot_become_consumer_input() -> None:
    baseline = _canonical_readiness_packet()
    mutated_internal = {
        **baseline,
        "circadianArousal": 0.99,
        "appetiteState": "high",
        "globalStateCaps": [0.1, 0.2, 0.3],
    }

    before = read_readiness_public_surface(baseline)
    after = read_readiness_public_surface(mutated_internal)
    assert before == after, "CONSUMER_DEPENDS_ON_INTERNAL_EXPLAIN"


def test_readiness_global_availability_absence_is_legal_current_shape() -> None:
    """Fixture I2: the field is missing and no substitute V may be derived."""
    surface = read_readiness_public_surface(_canonical_readiness_packet())
    assert surface.active_behavioral_states == ("NORMAL",)
    assert surface.enabled_response_modes == ("FEEDING",)


def test_readiness_global_availability_cannot_reenter_public_surface() -> None:
    legacy_packet = {
        **_canonical_readiness_packet(),
        "globalAvailability": 0.01,
        "globalBehavioralRetention": 0.01,
        "globalBehavioralCap": 0.01,
    }

    with_legacy = read_readiness_public_surface(legacy_packet)
    without_legacy = read_readiness_public_surface(_canonical_readiness_packet())
    assert with_legacy == without_legacy, "LEGACY_AVAILABILITY_FIELD_REGAINED_CONSUMER_SURFACE"


@pytest.mark.parametrize("missing_field", ["motivationProfile", "enabledResponseModes"])
def test_readiness_missing_public_field_fails_closed(missing_field: str) -> None:
    packet = {k: v for k, v in _canonical_readiness_packet().items() if k != missing_field}

    with pytest.raises(ContractViolation) as exc_info:
        read_readiness_public_surface(packet)

    assert exc_info.value.code == "PRODUCER_MISSING_REQUIRED_FIELD"
    assert exc_info.value.detail == missing_field


def test_capture_explain_fields_cannot_change_runtime_surface() -> None:
    baseline = {
        "captureRetention": 0.43,
        "hasEligibleResponseMode": True,
        "winningMode": "feeding",
        "modeResponses": [
            {"modeId": "feeding", "modeEligible": True, "C_mode": 0.43},
            {"modeId": "territorial", "modeEligible": False, "C_mode": 0.0},
        ],
        "IdentityOnlyMatch": 0.7,
        "PerceptionHeadroom": 0.4,
    }
    mutated_explain = {
        **baseline,
        "winningMode": "territorial",
        "modeResponses": [
            {"modeId": "feeding", "modeEligible": False, "C_mode": 0.0},
            {"modeId": "territorial", "modeEligible": True, "C_mode": 0.43},
        ],
        "IdentityOnlyMatch": 0.01,
        "PerceptionHeadroom": 0.99,
    }

    assert read_capture_runtime_surface(baseline) == read_capture_runtime_surface(mutated_explain)


def test_capture_missing_retention_fails_closed() -> None:
    with pytest.raises(ContractViolation) as exc_info:
        read_capture_runtime_surface({"hasEligibleResponseMode": True, "winningMode": "feeding"})

    assert exc_info.value.code == "PRODUCER_MISSING_REQUIRED_FIELD"
    assert exc_info.value.detail == "captureRetention"


def test_capture_missing_eligibility_flag_fails_closed() -> None:
    with pytest.raises(ContractViolation) as exc_info:
        read_capture_runtime_surface({"captureRetention": 0.7})

    assert exc_info.value.code == "PRODUCER_MISSING_REQUIRED_FIELD"
    assert exc_info.value.detail == "hasEligibleResponseMode"


def test_legacy_hard_valid_does_not_replace_current_packet_gate() -> None:
    with pytest.raises(ContractViolation) as exc_info:
        read_capture_runtime_surface({"captureRetention": 0.7, "hardValid": True})

    assert exc_info.value.code == "PRODUCER_MISSING_REQUIRED_FIELD"
    assert exc_info.value.detail == "hasEligibleResponseMode"


def test_no_eligible_mode_with_positive_retention_fails_closed() -> None:
    """The typed-zero projection is owned by Interaction, not re-gated here."""
    with pytest.raises(ContractViolation) as exc_info:
        read_capture_runtime_surface({"captureRetention": 0.7, "hasEligibleResponseMode": False})

    assert exc_info.value.code == "CAPTURE_PACKET_INCONSISTENT"


def test_typed_zero_ineligible_packet_reads_with_zero_retention() -> None:
    surface = read_capture_runtime_surface(
        {"captureRetention": 0.0, "hasEligibleResponseMode": False}
    )
    assert surface.capture_retention == 0.0
    assert surface.has_eligible_response_mode is False


def test_capture_explain_only_fields_may_be_absent() -> None:
    """Fixture I5: missing provenance/confidence never blocks the runtime surface."""
    surface = read_capture_runtime_surface(
        {"captureRetention": 0.5, "hasEligibleResponseMode": True}
    )
    assert surface.capture_retention == 0.5


def test_one_mode_invalid_does_not_kill_eligible_sibling() -> None:
    assert (
        derive_has_eligible_response_mode(
            [
                {"modeId": "feeding", "modeEligible": False},
                {"modeId": "territorial", "modeEligible": True},
            ]
        )
        is True
    )


def test_all_modes_ineligible_make_capture_route_ineligible() -> None:
    assert (
        derive_has_eligible_response_mode(
            [
                {"modeId": "feeding", "modeEligible": False},
                {"modeId": "territorial", "modeEligible": False},
            ]
        )
        is False
    )


def test_local_intensity_surface_requires_owner_resolved_field() -> None:
    with pytest.raises(ContractViolation) as exc_info:
        read_local_species_intensity_surface({"ambientWeight": 100.0})

    assert exc_info.value.code == "PRODUCER_MISSING_REQUIRED_FIELD"
    assert exc_info.value.detail == "localSpeciesIntensity"


def test_local_intensity_surface_preserves_typed_provenance_metadata() -> None:
    surface = read_local_species_intensity_surface(
        {
            "localSpeciesIntensity": 100.0,
            "bakedSemanticStages": ["B", "P", "E"],
            "aggregationContextRef": "agg-snapshot#1",
            "invalidationEpoch": 7,
        }
    )

    assert surface.local_species_intensity == 100.0
    assert surface.baked_semantic_stages == frozenset({"B", "P", "E"})
    assert surface.aggregation_context_ref == "agg-snapshot#1"

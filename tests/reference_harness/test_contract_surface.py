from __future__ import annotations

import pytest

from candidate_weight_reference import (
    ContractViolation,
    derive_has_eligible_response_mode,
    read_capture_runtime_surface,
    read_readiness_public_surface,
)


def test_readiness_internal_explain_cannot_become_consumer_input() -> None:
    baseline = {
        "globalAvailability": 0.8,
        "activeBehavioralStates": ["feeding"],
        "motivationProfile": {"feeding": 0.9},
        "enabledResponseModes": ["feeding"],
        "circadianArousal": 0.1,
        "appetiteState": "low",
        "globalStateCaps": [0.8],
    }
    mutated_internal = {
        **baseline,
        "circadianArousal": 0.99,
        "appetiteState": "high",
        "globalStateCaps": [0.1, 0.2, 0.3],
    }

    before = read_readiness_public_surface(baseline)
    after = read_readiness_public_surface(mutated_internal)
    assert before == after, "CONSUMER_DEPENDS_ON_INTERNAL_EXPLAIN"


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
        read_capture_runtime_surface(
            {"hasEligibleResponseMode": True, "winningMode": "feeding"}
        )

    assert exc_info.value.code == "PRODUCER_MISSING_REQUIRED_FIELD"
    assert exc_info.value.detail == "captureRetention"


def test_legacy_hard_valid_does_not_replace_current_packet_gate() -> None:
    with pytest.raises(ContractViolation) as exc_info:
        read_capture_runtime_surface({"captureRetention": 0.7, "hardValid": True})

    assert exc_info.value.code == "PRODUCER_MISSING_REQUIRED_FIELD"
    assert exc_info.value.detail == "hasEligibleResponseMode"


def test_readiness_missing_public_field_fails_closed() -> None:
    with pytest.raises(ContractViolation) as exc_info:
        read_readiness_public_surface(
            {
                "globalAvailability": 0.8,
                "activeBehavioralStates": ["feeding"],
                "motivationProfile": {"feeding": 0.9},
            }
        )

    assert exc_info.value.code == "PRODUCER_MISSING_REQUIRED_FIELD"
    assert exc_info.value.detail == "enabledResponseModes"


def test_no_eligible_response_mode_overrides_soft_capture_retention() -> None:
    surface = read_capture_runtime_surface(
        {"captureRetention": 0.7, "hasEligibleResponseMode": False}
    )
    assert surface.effective_capture == 0.0


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

from __future__ import annotations

import pytest

from candidate_weight_reference import (
    ContractViolation,
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
        "hardValid": True,
        "winningMode": "feeding",
        "modeResponses": {"feeding": 0.43},
        "IdentityOnlyMatch": 0.7,
        "PerceptionHeadroom": 0.4,
    }
    mutated_explain = {
        **baseline,
        "winningMode": "territorial",
        "modeResponses": {"territorial": 0.99},
        "IdentityOnlyMatch": 0.01,
        "PerceptionHeadroom": 0.99,
    }

    assert read_capture_runtime_surface(baseline) == read_capture_runtime_surface(mutated_explain)


def test_capture_missing_required_runtime_field_fails_closed() -> None:
    with pytest.raises(ContractViolation) as exc_info:
        read_capture_runtime_surface({"hardValid": True, "winningMode": "feeding"})

    assert exc_info.value.code == "PRODUCER_MISSING_REQUIRED_FIELD"
    assert exc_info.value.detail == "captureRetention"


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


def test_hard_invalid_overrides_soft_capture_retention() -> None:
    surface = read_capture_runtime_surface({"captureRetention": 0.7, "hardValid": False})
    assert surface.effective_capture == 0.0

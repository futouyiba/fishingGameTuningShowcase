"""Current Candidate surface blockers (CR-01 / CR-02) and structural negatives.

These tests protect the resolved-scalar numeric branch of canonical
TypedNativeRetentionJoin (Candidate Current v5: ``q = L x C`` for
already-resolved inputs): its arithmetic consumes exactly the two
Owner-resolved inputs, and legacy factors (readiness, aggregation,
global availability, hard gates, environment/adaptation/access/
technique multipliers) cannot re-enter the consumer even when they
still ride along in packets as Explain metadata. The typed Candidate
resolution transaction (typed-zero terminality / Unknown / completeness
/ CandidateResolutionResult) is outside this scalar surface.
"""

from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

import pytest

from candidate_weight_reference import (
    CandidateWeightInputs,
    CaptureRuntimeSurface,
    LocalSpeciesIntensitySurface,
    ResolvedBehavioralContextSurface,
    build_candidate_inputs,
    calculate_multiplicative_candidate_weight,
    read_capture_runtime_surface,
    read_local_species_intensity_surface,
    read_readiness_public_surface,
    resolve_multiplicative_candidate_weights,
)

REFERENCE_PACKAGE = Path(__file__).resolve().parents[2] / "candidate_weight_reference"

# Concepts that must never reappear in the Candidate numeric path.
FORBIDDEN_NUMERIC_IDENTIFIERS = frozenset(
    {
        "readiness",
        "motivation",
        "aggregation",
        "aggregationcontext",
        "global_availability",
        "globalavailability",
        "availability",
        "global_gate",
        "globalgate",
        "hard_gate",
        "hardgate",
        "hard_valid",
        "hardvalid",
        "environment",
        "adaptation",
        "capture_access",
        "access",
        "technique",
        "stimulus",
        "ambient",
        "stage",
        "effective_capture",
    }
)
FORBIDDEN_NUMERIC_FIELD_STRINGS = frozenset(
    {
        "readiness",
        "motivation",
        "aggregation",
        "globalAvailability",
        "globalBehavioralRetention",
        "globalBehavioralCap",
        "globalHardValid",
        "hardValid",
        "captureEligible",
        "captureAccess",
        "envCoeff",
        "adaptCoeff",
        "techniqueBonus",
        "access",
    }
)
# The ambient module legitimately owns environment-stage vocabulary, but the
# retired G/V factors must not regrow there either.
FORBIDDEN_AMBIENT_IDENTIFIERS = frozenset(
    {
        "readiness",
        "motivation",
        "aggregation",
        "aggregationcontext",
        "global_availability",
        "globalavailability",
        "availability",
    }
)

NUMERIC_PATH_MODULES = ("candidate.py", "kernel.py")


def test_cr01_current_candidate_weight_is_exactly_local_times_capture() -> None:
    weight = calculate_multiplicative_candidate_weight(
        CandidateWeightInputs(local_species_intensity=100.0, capture_retention=0.4)
    )
    assert weight == 40.0


def test_cr01_candidate_input_surface_has_no_other_arithmetic_field() -> None:
    field_names = [field.name for field in fields(CandidateWeightInputs)]
    assert field_names == ["local_species_intensity", "capture_retention"]


def test_candidate_capture_surface_has_no_gate_property_or_field() -> None:
    field_names = [field.name for field in fields(CaptureRuntimeSurface)]
    assert field_names == ["capture_retention", "has_eligible_response_mode"]
    assert not hasattr(CaptureRuntimeSurface, "effective_capture")


def test_candidate_readiness_surface_has_no_global_availability_field() -> None:
    field_names = [field.name for field in fields(ResolvedBehavioralContextSurface)]
    assert field_names == [
        "active_behavioral_states",
        "motivation_profile",
        "enabled_response_modes",
    ]


def test_cr02_forbidden_legacy_packet_metadata_cannot_change_candidate_weight() -> None:
    spatial_packet = {
        "localSpeciesIntensity": 100.0,
        "bakedSemanticStages": ["B", "P", "E"],
        "aggregationContextRef": "agg-snapshot#1",
        "readiness": 0.01,
        "aggregation": 0.01,
        "globalAvailability": 0.01,
        "globalHardValid": False,
        "envCoeff": 0.01,
        "adaptCoeff": 0.01,
        "captureAccess": 0.01,
        "techniqueBonus": 0.01,
    }
    capture_packet = {
        "captureRetention": 0.4,
        "hasEligibleResponseMode": True,
        "readiness": 0.01,
        "aggregation": 0.01,
        "globalAvailability": 0.01,
        "globalHardValid": False,
        "envCoeff": 0.01,
        "adaptCoeff": 0.01,
        "captureAccess": 0.01,
        "techniqueBonus": 0.01,
    }
    readiness_packet = {
        "activeBehavioralStates": ["NORMAL"],
        "motivationProfile": {"feeding": 0.7},
        "enabledResponseModes": ["FEEDING"],
        "globalAvailability": 0.01,
        "readiness": 0.01,
        "aggregation": 0.01,
    }

    spatial = read_local_species_intensity_surface(spatial_packet)
    capture = read_capture_runtime_surface(capture_packet)
    read_readiness_public_surface(readiness_packet)
    weight = calculate_multiplicative_candidate_weight(build_candidate_inputs(spatial, capture))

    assert weight == 40.0


def test_cr02_candidate_inputs_reject_unknown_legacy_kwargs() -> None:
    with pytest.raises(TypeError):
        CandidateWeightInputs(
            local_species_intensity=100.0,
            capture_retention=0.4,
            readiness=0.01,
        )
    with pytest.raises(TypeError):
        CandidateWeightInputs(
            local_species_intensity=100.0,
            capture_retention=0.4,
            aggregation=0.01,
        )
    with pytest.raises(TypeError):
        CandidateWeightInputs(
            local_species_intensity=100.0,
            capture_retention=0.4,
            globalAvailability=0.01,
        )


def _collect_docstrings(tree: ast.AST) -> set[int]:
    docstring_ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                if isinstance(body[0].value.value, str):
                    docstring_ids.add(id(body[0].value))
    return docstring_ids


def _identifier_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
        elif isinstance(node, ast.keyword):
            if node.arg is not None:
                names.add(node.arg)
        elif isinstance(node, ast.alias):
            names.add(node.asname or node.name.split(".")[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
    return names


def _field_strings(tree: ast.AST) -> set[str]:
    docstrings = _collect_docstrings(tree)
    values: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstrings
        ):
            values.add(node.value)
    return values


@pytest.mark.parametrize("module_name", NUMERIC_PATH_MODULES)
def test_negative_a_b_c_numeric_modules_never_reference_legacy_factors(
    module_name: str,
) -> None:
    """Structural negative: legacy factors cannot regrow in the numeric path.

    Fails when the Candidate consumer reintroduces a readiness / motivation
    scalar (A), a global availability / gate read (B), or re-settles an
    already-resolved aggregation / environment surface (C) — even if the
    numeric outcome would still be correct.
    """
    source = (REFERENCE_PACKAGE / module_name).read_text()
    tree = ast.parse(source)

    offenders = _identifier_names(tree) & FORBIDDEN_NUMERIC_IDENTIFIERS
    assert not offenders, f"{module_name} references forbidden legacy factors: {sorted(offenders)}"

    string_offenders = _field_strings(tree) & FORBIDDEN_NUMERIC_FIELD_STRINGS
    assert not string_offenders, (
        f"{module_name} reads forbidden legacy packet fields: {sorted(string_offenders)}"
    )


def test_negative_ambient_module_never_regrows_g_v_factors() -> None:
    source = (REFERENCE_PACKAGE / "ambient.py").read_text()
    tree = ast.parse(source)

    offenders = _identifier_names(tree) & FORBIDDEN_AMBIENT_IDENTIFIERS
    assert not offenders, f"ambient.py references retired G/V factors: {sorted(offenders)}"


def test_fixture_i_owner_packets_flow_into_current_candidate_surface() -> None:
    """Fixture I end-to-end: two Owner outputs in, W out, TruePool downstream."""
    spatial = read_local_species_intensity_surface(
        {
            "localSpeciesIntensity": 100.0,
            "bakedSemanticStages": ["B", "P", "E"],
            "aggregationContextRef": "agg-snapshot#1",
        }
    )
    capture = read_capture_runtime_surface(
        {
            "captureRetention": 0.4,
            "hasEligibleResponseMode": True,
            "winningMode": "FEEDING",
            "modeResponses": [
                {"modeId": "FEEDING", "modeEligible": True, "C_mode": 0.4},
            ],
            "reasonCodes": [],
            "provenance": [{"stage": "interaction-resolved"}],
            "confidence": "HIGH",
        }
    )

    inputs = build_candidate_inputs(spatial, capture)
    weights = resolve_multiplicative_candidate_weights({"A": inputs})

    assert calculate_multiplicative_candidate_weight(inputs) == 40.0
    assert weights == {"A": 40.0}
    assert spatial.baked_semantic_stages == frozenset({"B", "P", "E"})
    assert spatial.aggregation_context_ref == "agg-snapshot#1"


def test_candidate_inputs_validate_owner_resolved_ranges() -> None:
    with pytest.raises(ValueError):
        CandidateWeightInputs(local_species_intensity=-1.0, capture_retention=0.4)
    with pytest.raises(ValueError):
        CandidateWeightInputs(local_species_intensity=100.0, capture_retention=1.4)


def test_local_intensity_surface_is_typed_metadata_not_arithmetic() -> None:
    field_names = [field.name for field in fields(LocalSpeciesIntensitySurface)]
    assert field_names == [
        "local_species_intensity",
        "baked_semantic_stages",
        "aggregation_context_ref",
    ]


# Candidate Current v5 closed the arbitrary Candidate-level Combine:
# the Canonical Native Join is TypedNativeRetentionJoin and the
# resolved-scalar branch is q = L x C. Stale v3 authority wording must
# not regrow, and the harness must not overclaim the typed transaction.
STALE_V3_AUTHORITY_WORDING = (
    "remains open",
    "remains upstream authority",
    "stays upstream authority",
    "admitted specialization",
    "admitted multiplicative",
    "combine_prod",
    "not canonical candidate semantics",
    "not frozen to multiplication",
    "not frozen here",
)
OVERCLAIM_V5_WORDING = (
    "full candidate v5 implemented",
    "full typed candidate resolution implemented",
    "nativecandidatesnapshot implemented",
    "typed resolution complete",
    "source envelope implemented",
)
WORDING_SCOPE_PATHS = (
    REFERENCE_PACKAGE / "candidate.py",
    REFERENCE_PACKAGE / "contracts.py",
    REFERENCE_PACKAGE / "ambient.py",
    REFERENCE_PACKAGE.parent / "opportunity_reference" / "adapter.py",
    REFERENCE_PACKAGE.parent / "docs" / "overview.md",
    REFERENCE_PACKAGE.parent / "docs" / "data_schema.md",
)


@pytest.mark.parametrize("path", WORDING_SCOPE_PATHS, ids=lambda path: path.name)
def test_candidate_wording_matches_current_v5_scope(path: Path) -> None:
    text = path.read_text().lower()

    stale = [phrase for phrase in STALE_V3_AUTHORITY_WORDING if phrase in text]
    assert not stale, f"{path.name} carries stale v3 authority wording: {stale}"

    overclaim = [phrase for phrase in OVERCLAIM_V5_WORDING if phrase in text]
    assert not overclaim, f"{path.name} overclaims Candidate v5 scope: {overclaim}"

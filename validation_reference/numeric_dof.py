from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum


class RequestedNumericMode(str, Enum):
    FREE = "FREE"
    TIED = "TIED"
    FIXED = "FIXED"
    DERIVED = "DERIVED"


class AdmittedNumericMode(str, Enum):
    FREE = "FREE"
    TIED = "TIED"
    FIXED = "FIXED"
    DERIVED = "DERIVED"
    REJECTED = "REJECTED"


class CalibrationScope(str, Enum):
    GLOBAL_SYSTEM = "GLOBAL_SYSTEM"
    MECHANISM_FAMILY = "MECHANISM_FAMILY"
    ARCHETYPE = "ARCHETYPE"
    SPECIES_RESIDUAL = "SPECIES_RESIDUAL"
    SIGNATURE_OVERRIDE = "SIGNATURE_OVERRIDE"


@dataclass(frozen=True)
class NumericDOFRequest:
    dof_id: str
    semantic_owner_ref: str
    parameter_family: str
    scope: CalibrationScope
    scope_ref: str
    requested_mode: RequestedNumericMode
    tie_group_ref: str | None = None
    derivation_ref: str | None = None
    design_constraint_ref: str | None = None
    evidence_refs: tuple[str, ...] = ()
    fixture_refs: tuple[str, ...] = ()
    counterfactual_refs: tuple[str, ...] = ()
    shared_baseline_ref: str | None = None
    residual_stable_across_contexts: bool = False
    residual_pattern_group: str | None = None
    split_from_dof_ref: str | None = None


@dataclass(frozen=True)
class IdentifiabilityEvidence:
    independently_constraining_measurement: bool = False
    isolatable_fixture: bool = False
    isolatable_counterfactual_or_ablation: bool = False
    explicit_tying_or_design_constraint: bool = False
    compensation_equivalence_group: str | None = None
    kpi_match_only: bool = False


@dataclass(frozen=True)
class DOFAdmissionResult:
    dof_id: str
    requested_mode: RequestedNumericMode
    admitted_mode: AdmittedNumericMode
    reason_code: str


@dataclass(frozen=True)
class NumericDOFAdmissionReport:
    results: tuple[DOFAdmissionResult, ...]
    requested_dof_count: int
    admitted_free_dof_count: int
    admitted_tied_count: int
    admitted_fixed_count: int
    admitted_derived_count: int
    rejected_count: int
    free_dof_by_scope: tuple[tuple[CalibrationScope, int], ...]
    species_residual_free_count: int
    compensation_group_conflicts: tuple[str, ...]
    refactor_required_groups: tuple[str, ...]


def _reject(request: NumericDOFRequest, reason_code: str) -> DOFAdmissionResult:
    return DOFAdmissionResult(
        dof_id=request.dof_id,
        requested_mode=request.requested_mode,
        admitted_mode=AdmittedNumericMode.REJECTED,
        reason_code=reason_code,
    )


def _admit(
    request: NumericDOFRequest,
    mode: AdmittedNumericMode,
    reason_code: str,
) -> DOFAdmissionResult:
    return DOFAdmissionResult(
        dof_id=request.dof_id,
        requested_mode=request.requested_mode,
        admitted_mode=mode,
        reason_code=reason_code,
    )


def _has_reference(ref: str | None) -> bool:
    return isinstance(ref, str) and bool(ref.strip())


def _has_references(refs: tuple[str, ...]) -> bool:
    return _valid_reference_collection(refs) and bool(refs)


def _valid_reference_collection(refs: object) -> bool:
    return isinstance(refs, tuple) and all(_has_reference(ref) for ref in refs)


def _canonical_reference(ref: str) -> str:
    return ref.strip()


def _requires_free_group_guard(
    request: NumericDOFRequest,
    malformed_dof_ids: frozenset[str],
) -> bool:
    return (
        request.requested_mode is RequestedNumericMode.FREE or request.dof_id in malformed_dof_ids
    )


def _requires_species_residual_guard(request: NumericDOFRequest) -> bool:
    if request.scope is CalibrationScope.SPECIES_RESIDUAL:
        return True
    if (
        isinstance(request.scope, str)
        and request.scope.strip() == CalibrationScope.SPECIES_RESIDUAL.value
    ):
        return True
    return not isinstance(request.scope, CalibrationScope) and any(
        (
            request.shared_baseline_ref is not None,
            request.residual_stable_across_contexts is not False,
            request.residual_pattern_group is not None,
        )
    )


def _nonfree_mode_requirement_error(
    request: NumericDOFRequest,
    evidence: object,
) -> str | None:
    if not isinstance(evidence, IdentifiabilityEvidence):
        return None
    if request.requested_mode is RequestedNumericMode.DERIVED:
        if not _has_reference(request.derivation_ref):
            return "DERIVATION_NOT_DECLARED"
    if request.requested_mode is RequestedNumericMode.TIED:
        if (
            not _has_reference(request.tie_group_ref)
            or evidence.explicit_tying_or_design_constraint is not True
        ):
            return "TIE_NOT_DECLARED"
    if request.requested_mode is RequestedNumericMode.FIXED:
        if (
            not _has_reference(request.design_constraint_ref)
            or evidence.explicit_tying_or_design_constraint is not True
        ):
            return "DESIGN_CONSTRAINT_NOT_DECLARED"
    return None


def _metadata_error(request: NumericDOFRequest) -> str | None:
    if not isinstance(request.requested_mode, RequestedNumericMode):
        return "INVALID_REQUESTED_NUMERIC_MODE"
    if not isinstance(request.scope, CalibrationScope):
        return "INVALID_CALIBRATION_SCOPE"
    if not _has_reference(request.dof_id):
        return "DOF_ID_REQUIRED"
    if not _has_reference(request.semantic_owner_ref):
        return "SEMANTIC_OWNER_REFERENCE_REQUIRED"
    if not _has_reference(request.parameter_family):
        return "PARAMETER_FAMILY_REQUIRED"
    if not _has_reference(request.scope_ref):
        return "SCOPE_REFERENCE_REQUIRED"
    if not isinstance(request.residual_stable_across_contexts, bool):
        return "INVALID_RESIDUAL_STABILITY_FLAG"
    reference_collections = (
        (request.evidence_refs, "MEASUREMENT_REFERENCE_REQUIRED"),
        (request.fixture_refs, "FIXTURE_REFERENCE_REQUIRED"),
        (request.counterfactual_refs, "COUNTERFACTUAL_REFERENCE_REQUIRED"),
    )
    for refs, reason_code in reference_collections:
        if not _valid_reference_collection(refs):
            return reason_code
    if request.tie_group_ref is not None and not _has_reference(request.tie_group_ref):
        return "TIE_REFERENCE_REQUIRED"
    if request.derivation_ref is not None and not _has_reference(request.derivation_ref):
        return "DERIVATION_REFERENCE_REQUIRED"
    if request.design_constraint_ref is not None and not _has_reference(
        request.design_constraint_ref
    ):
        return "DESIGN_CONSTRAINT_REFERENCE_REQUIRED"
    if request.shared_baseline_ref is not None and not _has_reference(request.shared_baseline_ref):
        return "SPECIES_RESIDUAL_BASELINE_REQUIRED"
    if request.residual_pattern_group is not None and not _has_reference(
        request.residual_pattern_group
    ):
        return "SPECIES_RESIDUAL_PATTERN_REQUIRED"
    if request.split_from_dof_ref is not None and not _has_reference(request.split_from_dof_ref):
        return "SPLIT_SOURCE_REFERENCE_REQUIRED"
    return None


def _evidence_metadata_error(evidence: IdentifiabilityEvidence) -> str | None:
    if not isinstance(evidence, IdentifiabilityEvidence):
        return "INVALID_IDENTIFIABILITY_EVIDENCE"
    flags = (
        evidence.independently_constraining_measurement,
        evidence.isolatable_fixture,
        evidence.isolatable_counterfactual_or_ablation,
        evidence.explicit_tying_or_design_constraint,
        evidence.kpi_match_only,
    )
    if not all(isinstance(flag, bool) for flag in flags):
        return "INVALID_IDENTIFIABILITY_EVIDENCE_FLAG"
    group = evidence.compensation_equivalence_group
    if group is not None and not _has_reference(group):
        return "COMPENSATION_GROUP_REFERENCE_REQUIRED"
    return None


def _independent_reason(
    request: NumericDOFRequest,
    evidence: IdentifiabilityEvidence,
) -> str | None:
    if evidence.independently_constraining_measurement and _has_references(request.evidence_refs):
        return "INDEPENDENT_MEASUREMENT"
    if evidence.isolatable_fixture and _has_references(request.fixture_refs):
        return "ISOLATABLE_FIXTURE"
    if evidence.isolatable_counterfactual_or_ablation and _has_references(
        request.counterfactual_refs
    ):
        return "ISOLATABLE_COUNTERFACTUAL"
    return None


def _evaluate_request(
    request: NumericDOFRequest,
    evidence: IdentifiabilityEvidence,
) -> DOFAdmissionResult:
    if request.requested_mode is RequestedNumericMode.DERIVED:
        if not _has_reference(request.derivation_ref):
            return _reject(request, "DERIVATION_NOT_DECLARED")
        return _admit(request, AdmittedNumericMode.DERIVED, "EXPLICIT_DERIVATION")

    if request.requested_mode is RequestedNumericMode.TIED:
        if (
            not _has_reference(request.tie_group_ref)
            or not evidence.explicit_tying_or_design_constraint
        ):
            return _reject(request, "TIE_NOT_DECLARED")
        return _admit(request, AdmittedNumericMode.TIED, "EXPLICIT_TIE")

    if request.requested_mode is RequestedNumericMode.FIXED:
        if (
            not _has_reference(request.design_constraint_ref)
            or not evidence.explicit_tying_or_design_constraint
        ):
            return _reject(request, "DESIGN_CONSTRAINT_NOT_DECLARED")
        return _admit(
            request,
            AdmittedNumericMode.FIXED,
            "EXPLICIT_DESIGN_CONSTRAINT",
        )

    if evidence.kpi_match_only:
        return _reject(request, "KPI_MATCH_NOT_IDENTIFIABILITY")

    if evidence.explicit_tying_or_design_constraint:
        if _has_reference(request.design_constraint_ref):
            return _admit(
                request,
                AdmittedNumericMode.FIXED,
                "FREE_DOWNGRADED_TO_FIXED",
            )
        if _has_reference(request.tie_group_ref):
            return _admit(
                request,
                AdmittedNumericMode.TIED,
                "FREE_DOWNGRADED_TO_TIED",
            )
        return _reject(request, "CONSTRAINT_REFERENCE_NOT_DECLARED")

    if _has_reference(request.design_constraint_ref):
        return _reject(request, "DESIGN_CONSTRAINT_NOT_DECLARED")
    if _has_reference(request.tie_group_ref):
        return _reject(request, "TIE_NOT_DECLARED")

    independent_reason = _independent_reason(request, evidence)
    if request.scope is CalibrationScope.SPECIES_RESIDUAL:
        if not _has_reference(request.shared_baseline_ref):
            return _reject(request, "SPECIES_RESIDUAL_BASELINE_REQUIRED")
        if not request.residual_stable_across_contexts:
            return _reject(request, "SPECIES_RESIDUAL_STABILITY_NOT_PROVEN")

    if independent_reason is not None:
        return _admit(request, AdmittedNumericMode.FREE, independent_reason)

    return _reject(request, "IDENTIFIABILITY_NOT_PROVEN")


def _group_conflicts(
    requests: tuple[NumericDOFRequest, ...],
    evidence_by_dof: Mapping[str, IdentifiabilityEvidence],
    malformed_dof_ids: frozenset[str],
) -> tuple[dict[str, str], tuple[str, ...]]:
    members: dict[str, list[str]] = defaultdict(list)
    for request in requests:
        group = evidence_by_dof[request.dof_id].compensation_equivalence_group
        if _requires_free_group_guard(request, malformed_dof_ids) and group is not None:
            members[_canonical_reference(group)].append(request.dof_id)

    conflicts = {
        dof_id: "COMPENSATION_EQUIVALENCE_CONFLICT"
        for group_members in members.values()
        if len(group_members) > 1
        for dof_id in group_members
    }
    groups = tuple(
        sorted(group for group, group_members in members.items() if len(group_members) > 1)
    )
    return conflicts, groups


def _refactor_conflicts(
    requests: tuple[NumericDOFRequest, ...],
    malformed_dof_ids: frozenset[str],
) -> tuple[dict[str, str], tuple[str, ...]]:
    residuals = tuple(
        request
        for request in requests
        if _requires_free_group_guard(request, malformed_dof_ids)
        and _requires_species_residual_guard(request)
    )
    missing_pattern = len(residuals) > 1 and any(
        not _has_reference(request.residual_pattern_group) for request in residuals
    )
    conflicts = (
        {request.dof_id: "SPECIES_RESIDUAL_PATTERN_REQUIRED" for request in residuals}
        if missing_pattern
        else {}
    )

    members: dict[str, list[str]] = defaultdict(list)
    if missing_pattern:
        return conflicts, ()
    for request in residuals:
        if _has_reference(request.residual_pattern_group):
            group = _canonical_reference(request.residual_pattern_group)  # type: ignore[arg-type]
            members[group].append(request.dof_id)

    conflicts.update(
        {
            dof_id: "SHARED_MODEL_REFACTOR_REQUIRED"
            for group_members in members.values()
            if len(group_members) > 1
            for dof_id in group_members
        }
    )
    groups = tuple(
        sorted(group for group, group_members in members.items() if len(group_members) > 1)
    )
    return conflicts, groups


def _independent_evidence_key(
    request: NumericDOFRequest,
    evidence: IdentifiabilityEvidence,
) -> tuple[str, ...] | None:
    if _evidence_metadata_error(evidence) is not None:
        return None
    reason = _independent_reason(request, evidence)
    refs_by_reason = {
        "INDEPENDENT_MEASUREMENT": request.evidence_refs,
        "ISOLATABLE_FIXTURE": request.fixture_refs,
        "ISOLATABLE_COUNTERFACTUAL": request.counterfactual_refs,
    }
    if reason is None:
        return None
    return tuple(sorted({_canonical_reference(ref) for ref in refs_by_reason[reason]}))


def _split_conflicts(
    requests: tuple[NumericDOFRequest, ...],
    evidence_by_dof: Mapping[str, IdentifiabilityEvidence],
    malformed_dof_ids: frozenset[str],
) -> dict[str, str]:
    members: dict[str, list[NumericDOFRequest]] = defaultdict(list)
    for request in requests:
        if _requires_free_group_guard(request, malformed_dof_ids) and _has_reference(
            request.split_from_dof_ref
        ):
            group = _canonical_reference(request.split_from_dof_ref)  # type: ignore[arg-type]
            members[group].append(request)

    conflicts: dict[str, str] = {}
    for group_members in members.values():
        if len(group_members) < 2:
            continue
        evidence_keys = {
            request.dof_id: _independent_evidence_key(
                request,
                evidence_by_dof[request.dof_id],
            )
            for request in group_members
        }
        if any(evidence_key is None for evidence_key in evidence_keys.values()):
            conflicts.update(
                {request.dof_id: "FREE_SPLIT_WITHOUT_NEW_EVIDENCE" for request in group_members}
            )
            continue
        key_counts = Counter(evidence_keys.values())
        for request in group_members:
            evidence_key = evidence_keys[request.dof_id]
            if key_counts[evidence_key] > 1:
                conflicts[request.dof_id] = "FREE_SPLIT_WITHOUT_NEW_EVIDENCE"
    return conflicts


def evaluate_numeric_dof_requests(
    requests: Iterable[NumericDOFRequest],
    evidence_by_dof: Mapping[str, IdentifiabilityEvidence] | None = None,
) -> NumericDOFAdmissionReport:
    """Evaluate explicit numeric-freedom metadata without fitting coefficients.

    This is a Reference admission gate, not a symbolic identifiability solver or
    a parameter-semantic owner. Set-level conflicts are resolved by reducing
    freedom: the validator never chooses an arbitrary winner among equivalent
    FREE requests and never purchases repeated species residuals.
    """
    requested_items = tuple(requests)
    if not all(isinstance(request, NumericDOFRequest) for request in requested_items):
        raise ValueError("requests must contain only NumericDOFRequest values")

    dof_ids: list[str] = []
    for request in requested_items:
        if not _has_reference(request.dof_id):
            raise ValueError("dof_id must be a nonblank string")
        dof_ids.append(request.dof_id)

    unordered_input = isinstance(requests, (set, frozenset))
    requested = requested_items
    if unordered_input:
        requested = tuple(sorted(requested, key=lambda request: request.dof_id))

    dof_id_tuple = tuple(dof_ids)
    if unordered_input:
        dof_id_tuple = tuple(request.dof_id for request in requested)
    if len(set(dof_id_tuple)) != len(dof_id_tuple):
        raise ValueError("dof_id must be unique within an admission batch")

    supplied_evidence = {} if evidence_by_dof is None else dict(evidence_by_dof)
    if not all(_has_reference(dof_id) for dof_id in supplied_evidence):
        raise ValueError("evidence keys must be nonblank string dof_id values")
    unknown_evidence = set(supplied_evidence).difference(dof_id_tuple)
    if unknown_evidence:
        raise ValueError("evidence supplied for an unknown dof_id")
    evidence = {
        dof_id: supplied_evidence.get(dof_id, IdentifiabilityEvidence()) for dof_id in dof_id_tuple
    }
    metadata_errors = {request.dof_id: _metadata_error(request) for request in requested}
    evidence_errors = {dof_id: _evidence_metadata_error(item) for dof_id, item in evidence.items()}

    nonfree_requirement_errors = {
        request.dof_id: _nonfree_mode_requirement_error(
            request,
            evidence[request.dof_id],
        )
        for request in requested
    }
    malformed_dof_ids = frozenset(
        request.dof_id
        for request in requested
        if metadata_errors[request.dof_id] is not None
        or evidence_errors[request.dof_id] is not None
        or nonfree_requirement_errors[request.dof_id] is not None
    )

    conflict_requests = tuple(
        request
        for request in requested
        if isinstance(evidence[request.dof_id], IdentifiabilityEvidence)
        and (
            evidence[request.dof_id].compensation_equivalence_group is None
            or _has_reference(evidence[request.dof_id].compensation_equivalence_group)
        )
    )
    compensation_conflicts, compensation_groups = _group_conflicts(
        conflict_requests,
        evidence,
        malformed_dof_ids,
    )
    refactor_conflicts, refactor_groups = _refactor_conflicts(
        requested,
        malformed_dof_ids,
    )
    split_conflicts = _split_conflicts(
        requested,
        evidence,
        malformed_dof_ids,
    )

    results: list[DOFAdmissionResult] = []
    for request in requested:
        reason = (
            metadata_errors[request.dof_id]
            or evidence_errors[request.dof_id]
            or nonfree_requirement_errors[request.dof_id]
            or refactor_conflicts.get(request.dof_id)
            or compensation_conflicts.get(request.dof_id)
            or split_conflicts.get(request.dof_id)
        )
        if reason is not None:
            results.append(_reject(request, reason))
        else:
            results.append(_evaluate_request(request, evidence[request.dof_id]))

    result_tuple = tuple(results)
    admitted_counts = Counter(result.admitted_mode for result in result_tuple)
    request_by_id = {request.dof_id: request for request in requested}
    free_scopes = Counter(
        request_by_id[result.dof_id].scope
        for result in result_tuple
        if result.admitted_mode is AdmittedNumericMode.FREE
    )
    free_dof_by_scope = tuple(
        (scope, free_scopes[scope]) for scope in CalibrationScope if free_scopes[scope]
    )
    species_residual_free_count = sum(
        1
        for result in result_tuple
        if result.admitted_mode is AdmittedNumericMode.FREE
        and request_by_id[result.dof_id].scope is CalibrationScope.SPECIES_RESIDUAL
    )

    return NumericDOFAdmissionReport(
        results=result_tuple,
        requested_dof_count=len(requested),
        admitted_free_dof_count=admitted_counts[AdmittedNumericMode.FREE],
        admitted_tied_count=admitted_counts[AdmittedNumericMode.TIED],
        admitted_fixed_count=admitted_counts[AdmittedNumericMode.FIXED],
        admitted_derived_count=admitted_counts[AdmittedNumericMode.DERIVED],
        rejected_count=admitted_counts[AdmittedNumericMode.REJECTED],
        free_dof_by_scope=free_dof_by_scope,
        species_residual_free_count=species_residual_free_count,
        compensation_group_conflicts=compensation_groups,
        refactor_required_groups=refactor_groups,
    )

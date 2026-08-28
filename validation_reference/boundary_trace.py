from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BoundaryAssertionKind(str, Enum):
    EQUAL = "EQUAL"
    REQUIRE_DELTA_PATH = "REQUIRE_DELTA_PATH"
    FORBID_DELTA_PATH = "FORBID_DELTA_PATH"


@dataclass(frozen=True)
class BoundarySnapshot:
    boundary_id: str
    semantic_digest: str


@dataclass(frozen=True)
class BoundaryAssertionResult:
    assertion_id: str
    passed: bool
    failure_class: str | None = None


def evaluate_boundary_assertion(
    *,
    assertion_id: str,
    kind: BoundaryAssertionKind,
    baseline: BoundarySnapshot,
    counterfactual: BoundarySnapshot,
    failure_class: str,
) -> BoundaryAssertionResult:
    """Evaluate a semantic boundary delta assertion.

    The digest is an opaque, deterministic semantic signature supplied by the
    boundary owner or a validation adapter. This helper owns only comparison
    semantics; it does not define the contents of Spatial, Interaction,
    Opportunity, or Candidate boundaries.
    """
    if baseline.boundary_id != counterfactual.boundary_id:
        raise ValueError("boundary_id must match within a paired assertion")

    equal = baseline.semantic_digest == counterfactual.semantic_digest
    if kind is BoundaryAssertionKind.EQUAL:
        passed = equal
    elif kind is BoundaryAssertionKind.REQUIRE_DELTA_PATH:
        passed = not equal
    elif kind is BoundaryAssertionKind.FORBID_DELTA_PATH:
        passed = equal
    else:  # pragma: no cover - Enum makes this unreachable for valid callers.
        raise ValueError(f"unsupported boundary assertion kind: {kind}")

    return BoundaryAssertionResult(
        assertion_id=assertion_id,
        passed=passed,
        failure_class=None if passed else failure_class,
    )

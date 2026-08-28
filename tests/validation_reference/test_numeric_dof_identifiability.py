from __future__ import annotations

import pytest

from validation_reference import (
    AdmittedNumericMode,
    CalibrationScope,
    IdentifiabilityEvidence,
    NumericDOFRequest,
    RequestedNumericMode,
    evaluate_numeric_dof_requests,
)


def _request(
    dof_id: str,
    *,
    semantic_owner_ref: str = "owner:candidate",
    requested_mode: RequestedNumericMode = RequestedNumericMode.FREE,
    scope: CalibrationScope = CalibrationScope.MECHANISM_FAMILY,
    scope_ref: str = "family:capture",
    **overrides: object,
) -> NumericDOFRequest:
    values: dict[str, object] = {
        "dof_id": dof_id,
        "semantic_owner_ref": semantic_owner_ref,
        "parameter_family": "capture-response",
        "scope": scope,
        "scope_ref": scope_ref,
        "requested_mode": requested_mode,
    }
    values.update(overrides)
    return NumericDOFRequest(**values)  # type: ignore[arg-type]


def _counterfactual_evidence() -> IdentifiabilityEvidence:
    return IdentifiabilityEvidence(isolatable_counterfactual_or_ablation=True)


def test_id_01_unconstrained_free_coefficient_is_rejected() -> None:
    report = evaluate_numeric_dof_requests([_request("capture.free")])

    assert report.results[0].admitted_mode is AdmittedNumericMode.REJECTED
    assert report.results[0].reason_code == "IDENTIFIABILITY_NOT_PROVEN"
    assert report.requested_dof_count == 1
    assert report.admitted_free_dof_count == 0
    assert report.rejected_count == 1


def test_id_02_semantic_independence_alone_does_not_buy_two_free_dofs() -> None:
    report = evaluate_numeric_dof_requests(
        [
            _request("spatial.coefficient", semantic_owner_ref="owner:spatial"),
            _request("interaction.coefficient", semantic_owner_ref="owner:interaction"),
        ]
    )

    assert [result.admitted_mode for result in report.results] == [
        AdmittedNumericMode.REJECTED,
        AdmittedNumericMode.REJECTED,
    ]
    assert {result.reason_code for result in report.results} == {"IDENTIFIABILITY_NOT_PROVEN"}
    assert report.requested_dof_count == 2
    assert report.admitted_free_dof_count == 0


def test_id_03_compensation_equivalent_free_pair_is_rejected() -> None:
    group = "thermal_x_activity_product"
    requests = [
        _request("thermal.coefficient"),
        _request("activity.coefficient"),
    ]
    evidence = {
        request.dof_id: IdentifiabilityEvidence(compensation_equivalence_group=group)
        for request in requests
    }

    report = evaluate_numeric_dof_requests(requests, evidence)

    assert all(
        result.reason_code == "COMPENSATION_EQUIVALENCE_CONFLICT" for result in report.results
    )
    assert report.compensation_group_conflicts == (group,)
    assert report.admitted_free_dof_count == 0
    assert report.rejected_count == 2


def test_id_04_isolatable_counterfactual_admits_free() -> None:
    request = _request(
        "capture.recovery",
        counterfactual_refs=("fixture:single-target-mutation",),
    )

    report = evaluate_numeric_dof_requests(
        [request],
        {request.dof_id: _counterfactual_evidence()},
    )

    assert report.results[0].admitted_mode is AdmittedNumericMode.FREE
    assert report.results[0].reason_code == "ISOLATABLE_COUNTERFACTUAL"
    assert report.admitted_free_dof_count == 1
    assert report.free_dof_by_scope == ((CalibrationScope.MECHANISM_FAMILY, 1),)


def test_id_05_explicit_tying_admits_tied_but_not_free() -> None:
    tied = _request(
        "species.family-retention",
        requested_mode=RequestedNumericMode.TIED,
        tie_group_ref="tie:family-retention",
    )
    free = _request(
        "species.free-retention",
        tie_group_ref="tie:family-retention",
    )
    evidence = {
        tied.dof_id: IdentifiabilityEvidence(explicit_tying_or_design_constraint=True),
        free.dof_id: IdentifiabilityEvidence(explicit_tying_or_design_constraint=True),
    }

    report = evaluate_numeric_dof_requests([tied, free], evidence)

    assert report.results[0].admitted_mode is AdmittedNumericMode.TIED
    assert report.results[0].reason_code == "EXPLICIT_TIE"
    assert report.results[1].admitted_mode is AdmittedNumericMode.TIED
    assert report.results[1].reason_code == "FREE_DOWNGRADED_TO_TIED"
    assert report.admitted_tied_count == 2
    assert report.admitted_free_dof_count == 0


def test_id_06_fixed_design_policy_is_not_counted_as_free() -> None:
    fixed = _request(
        "pan.reference-scale",
        requested_mode=RequestedNumericMode.FIXED,
        scope=CalibrationScope.GLOBAL_SYSTEM,
        scope_ref="system:true-roll",
        design_constraint_ref="policy:reference-pan-scale",
    )

    report = evaluate_numeric_dof_requests(
        [fixed],
        {fixed.dof_id: IdentifiabilityEvidence(explicit_tying_or_design_constraint=True)},
    )

    assert report.results[0].admitted_mode is AdmittedNumericMode.FIXED
    assert report.results[0].reason_code == "EXPLICIT_DESIGN_CONSTRAINT"
    assert report.admitted_fixed_count == 1
    assert report.admitted_free_dof_count == 0
    assert report.free_dof_by_scope == ()


def test_id_07_sparse_species_residual_with_independent_evidence_is_allowed() -> None:
    residual = _request(
        "signature-species.residual",
        scope=CalibrationScope.SPECIES_RESIDUAL,
        scope_ref="species:signature-fish",
        shared_baseline_ref="archetype:cold-deep",
        residual_stable_across_contexts=True,
        evidence_refs=("measurement:signature-residual",),
        counterfactual_refs=("fixture:signature-residual-ablation",),
    )

    report = evaluate_numeric_dof_requests(
        [residual],
        {
            residual.dof_id: IdentifiabilityEvidence(
                independently_constraining_measurement=True,
                isolatable_counterfactual_or_ablation=True,
            )
        },
    )

    assert report.results[0].admitted_mode is AdmittedNumericMode.FREE
    assert report.results[0].reason_code == "INDEPENDENT_MEASUREMENT"
    assert report.species_residual_free_count == 1
    assert report.free_dof_by_scope == ((CalibrationScope.SPECIES_RESIDUAL, 1),)


def test_id_08_repeated_residual_hotspot_requires_shared_model_refactor() -> None:
    requests = [
        _request(
            f"species-{index}.thermal-residual",
            scope=CalibrationScope.SPECIES_RESIDUAL,
            scope_ref=f"species:{index}",
            shared_baseline_ref="archetype:cold-deep",
            residual_stable_across_contexts=True,
            residual_pattern_group="thermal:positive",
            counterfactual_refs=(f"fixture:species-{index}-ablation",),
        )
        for index in (1, 2, 3)
    ]
    evidence = {request.dof_id: _counterfactual_evidence() for request in requests}

    report = evaluate_numeric_dof_requests(requests, evidence)

    assert all(result.reason_code == "SHARED_MODEL_REFACTOR_REQUIRED" for result in report.results)
    assert report.refactor_required_groups == ("thermal:positive",)
    assert report.species_residual_free_count == 0
    assert report.rejected_count == 3


def test_id_09_kpi_compensation_is_not_identifiability_evidence() -> None:
    request = _request(
        "purity.kpi-compensator",
        evidence_refs=("kpi:purity-band-hit",),
    )

    report = evaluate_numeric_dof_requests(
        [request],
        {request.dof_id: IdentifiabilityEvidence(kpi_match_only=True)},
    )

    assert report.results[0].admitted_mode is AdmittedNumericMode.REJECTED
    assert report.results[0].reason_code == "KPI_MATCH_NOT_IDENTIFIABILITY"
    assert report.admitted_free_dof_count == 0


def test_id_10_shared_parameter_split_without_new_evidence_is_rejected() -> None:
    requests = [
        _request(
            "capture.shared-split-a",
            split_from_dof_ref="capture.shared-retention",
        ),
        _request(
            "capture.shared-split-b",
            split_from_dof_ref="capture.shared-retention",
        ),
    ]

    report = evaluate_numeric_dof_requests(requests)

    assert all(result.reason_code == "FREE_SPLIT_WITHOUT_NEW_EVIDENCE" for result in report.results)
    assert report.admitted_free_dof_count == 0
    assert report.rejected_count == 2


def test_report_separates_declared_fields_from_independent_free_dofs() -> None:
    free = _request(
        "family.free",
        fixture_refs=("fixture:family-isolation",),
    )
    tied = _request(
        "family.tied",
        requested_mode=RequestedNumericMode.TIED,
        tie_group_ref="tie:family",
    )
    fixed = _request(
        "system.fixed",
        requested_mode=RequestedNumericMode.FIXED,
        design_constraint_ref="policy:fixed",
    )
    derived = _request(
        "archetype.derived",
        requested_mode=RequestedNumericMode.DERIVED,
        scope=CalibrationScope.ARCHETYPE,
        scope_ref="archetype:cold-deep",
        derivation_ref="derivation:shared-to-archetype",
    )
    rejected = _request("species.rejected")
    evidence = {
        free.dof_id: IdentifiabilityEvidence(isolatable_fixture=True),
        tied.dof_id: IdentifiabilityEvidence(explicit_tying_or_design_constraint=True),
        fixed.dof_id: IdentifiabilityEvidence(explicit_tying_or_design_constraint=True),
    }

    report = evaluate_numeric_dof_requests(
        [free, tied, fixed, derived, rejected],
        evidence,
    )

    assert report.requested_dof_count == 5
    assert report.admitted_free_dof_count == 1
    assert report.admitted_tied_count == 1
    assert report.admitted_fixed_count == 1
    assert report.admitted_derived_count == 1
    assert report.rejected_count == 1


def test_malformed_metadata_fails_closed() -> None:
    invalid_scope = _request(
        "invalid.scope",
        scope="SPECIES_RESIDUAL",  # type: ignore[arg-type]
        counterfactual_refs=("fixture:isolation",),
    )
    blank_counterfactual = _request(
        "blank.counterfactual",
        counterfactual_refs=("",),
    )
    invalid_reference_collection = _request(
        "invalid.reference-collection",
        counterfactual_refs="fixture:not-a-tuple",  # type: ignore[arg-type]
    )
    invalid_stability_flag = _request(
        "invalid.stability-flag",
        scope=CalibrationScope.SPECIES_RESIDUAL,
        scope_ref="species:invalid-stability",
        shared_baseline_ref="archetype:cold-deep",
        residual_stable_across_contexts="false",  # type: ignore[arg-type]
        counterfactual_refs=("fixture:invalid-stability",),
    )

    report = evaluate_numeric_dof_requests(
        [
            invalid_scope,
            blank_counterfactual,
            invalid_reference_collection,
            invalid_stability_flag,
        ],
        {
            invalid_scope.dof_id: _counterfactual_evidence(),
            blank_counterfactual.dof_id: _counterfactual_evidence(),
            invalid_reference_collection.dof_id: _counterfactual_evidence(),
            invalid_stability_flag.dof_id: _counterfactual_evidence(),
        },
    )

    assert [result.reason_code for result in report.results] == [
        "INVALID_CALIBRATION_SCOPE",
        "COUNTERFACTUAL_REFERENCE_REQUIRED",
        "COUNTERFACTUAL_REFERENCE_REQUIRED",
        "INVALID_RESIDUAL_STABILITY_FLAG",
    ]
    assert report.admitted_free_dof_count == 0
    assert report.rejected_count == 4


def test_malformed_evidence_flags_fail_closed() -> None:
    request = _request(
        "invalid.evidence-flag",
        counterfactual_refs=("fixture:invalid-evidence",),
    )

    report = evaluate_numeric_dof_requests(
        [request],
        {
            request.dof_id: IdentifiabilityEvidence(
                isolatable_counterfactual_or_ablation="false",  # type: ignore[arg-type]
            )
        },
    )

    assert report.results[0].reason_code == "INVALID_IDENTIFIABILITY_EVIDENCE_FLAG"
    assert report.admitted_free_dof_count == 0
    assert report.rejected_count == 1


def test_kpi_or_explicit_constraint_cannot_be_overridden_by_free_evidence() -> None:
    kpi = _request(
        "kpi.with-counterfactual",
        counterfactual_refs=("fixture:kpi-ablation",),
    )
    tied = _request(
        "tied.with-counterfactual",
        tie_group_ref="tie:family",
        counterfactual_refs=("fixture:tied-ablation",),
    )
    fixed = _request(
        "fixed.with-counterfactual",
        design_constraint_ref="policy:fixed",
        counterfactual_refs=("fixture:fixed-ablation",),
    )
    undeclared_tie = _request(
        "undeclared-tie.with-counterfactual",
        tie_group_ref="tie:undeclared",
        counterfactual_refs=("fixture:undeclared-tie-ablation",),
    )
    undeclared_fixed = _request(
        "undeclared-fixed.with-counterfactual",
        design_constraint_ref="policy:undeclared",
        counterfactual_refs=("fixture:undeclared-fixed-ablation",),
    )

    report = evaluate_numeric_dof_requests(
        [kpi, tied, fixed, undeclared_tie, undeclared_fixed],
        {
            kpi.dof_id: IdentifiabilityEvidence(
                isolatable_counterfactual_or_ablation=True,
                kpi_match_only=True,
            ),
            tied.dof_id: IdentifiabilityEvidence(
                isolatable_counterfactual_or_ablation=True,
                explicit_tying_or_design_constraint=True,
            ),
            fixed.dof_id: IdentifiabilityEvidence(
                isolatable_counterfactual_or_ablation=True,
                explicit_tying_or_design_constraint=True,
            ),
            undeclared_tie.dof_id: _counterfactual_evidence(),
            undeclared_fixed.dof_id: _counterfactual_evidence(),
        },
    )

    assert [result.reason_code for result in report.results] == [
        "KPI_MATCH_NOT_IDENTIFIABILITY",
        "FREE_DOWNGRADED_TO_TIED",
        "FREE_DOWNGRADED_TO_FIXED",
        "TIE_NOT_DECLARED",
        "DESIGN_CONSTRAINT_NOT_DECLARED",
    ]
    assert report.admitted_free_dof_count == 0


def test_split_children_require_distinct_new_evidence() -> None:
    requests = [
        _request(
            "capture.split-a",
            split_from_dof_ref="capture.shared",
            fixture_refs=("fixture:shared-a", "fixture:shared-b"),
        ),
        _request(
            "capture.split-b",
            split_from_dof_ref="capture.shared",
            fixture_refs=("fixture:shared-b", "fixture:shared-a"),
        ),
    ]
    evidence = {
        request.dof_id: IdentifiabilityEvidence(isolatable_fixture=True) for request in requests
    }

    report = evaluate_numeric_dof_requests(requests, evidence)

    assert all(result.reason_code == "FREE_SPLIT_WITHOUT_NEW_EVIDENCE" for result in report.results)
    assert report.admitted_free_dof_count == 0


def test_species_residual_requires_pattern_metadata_when_batch_has_multiple_residuals() -> None:
    requests = [
        _request(
            f"species-{index}.residual",
            scope=CalibrationScope.SPECIES_RESIDUAL,
            scope_ref=f"species:{index}",
            shared_baseline_ref="archetype:cold-deep",
            residual_stable_across_contexts=True,
            counterfactual_refs=(f"fixture:species-{index}",),
        )
        for index in (1, 2)
    ]

    report = evaluate_numeric_dof_requests(
        requests,
        {request.dof_id: _counterfactual_evidence() for request in requests},
    )

    assert all(
        result.reason_code == "SPECIES_RESIDUAL_PATTERN_REQUIRED" for result in report.results
    )
    assert report.admitted_free_dof_count == 0


def test_results_are_deterministic_for_unordered_input() -> None:
    requests = {
        _request("dof.c"),
        _request("dof.a"),
        _request("dof.b"),
    }

    report = evaluate_numeric_dof_requests(requests)

    assert [result.dof_id for result in report.results] == [
        "dof.a",
        "dof.b",
        "dof.c",
    ]


def test_duplicate_or_unknown_evidence_metadata_is_rejected() -> None:
    duplicate = _request("duplicate")

    with pytest.raises(ValueError, match="dof_id must be unique"):
        evaluate_numeric_dof_requests([duplicate, duplicate])

    with pytest.raises(ValueError, match="unknown dof_id"):
        evaluate_numeric_dof_requests(
            [duplicate],
            {"other": IdentifiabilityEvidence()},
        )


def test_malformed_batch_inputs_raise_deterministic_validation_errors() -> None:
    with pytest.raises(ValueError, match="NumericDOFRequest"):
        evaluate_numeric_dof_requests([object()])  # type: ignore[list-item]

    invalid_id = _request(["not", "hashable"])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="dof_id must be a nonblank string"):
        evaluate_numeric_dof_requests([invalid_id])

    request = _request("valid")
    with pytest.raises(ValueError, match="evidence keys must be nonblank string"):
        evaluate_numeric_dof_requests(
            [request],
            {1: IdentifiabilityEvidence()},  # type: ignore[dict-item]
        )


def test_invalid_peer_cannot_become_arbitrary_compensation_winner() -> None:
    requests = [
        _request("valid.peer"),
        _request(
            "invalid.peer",
            scope="MECHANISM_FAMILY",  # type: ignore[arg-type]
        ),
    ]
    evidence = {
        request.dof_id: IdentifiabilityEvidence(
            compensation_equivalence_group="group:shared-product"
        )
        for request in requests
    }

    report = evaluate_numeric_dof_requests(requests, evidence)

    assert [result.reason_code for result in report.results] == [
        "COMPENSATION_EQUIVALENCE_CONFLICT",
        "INVALID_CALIBRATION_SCOPE",
    ]
    assert report.compensation_group_conflicts == ("group:shared-product",)
    assert report.admitted_free_dof_count == 0


def test_invalid_mode_peer_cannot_escape_compensation_conflict() -> None:
    valid = _request(
        "valid.peer",
        counterfactual_refs=("fixture:valid-peer",),
    )
    invalid = _request(
        "invalid.peer",
        requested_mode="BROKEN",  # type: ignore[arg-type]
    )
    evidence = {
        valid.dof_id: IdentifiabilityEvidence(
            isolatable_counterfactual_or_ablation=True,
            compensation_equivalence_group="group:shared-product",
        ),
        invalid.dof_id: IdentifiabilityEvidence(
            compensation_equivalence_group="group:shared-product"
        ),
    }

    report = evaluate_numeric_dof_requests([valid, invalid], evidence)

    assert [result.reason_code for result in report.results] == [
        "COMPENSATION_EQUIVALENCE_CONFLICT",
        "INVALID_REQUESTED_NUMERIC_MODE",
    ]
    assert report.admitted_free_dof_count == 0


def test_invalid_split_peer_cannot_leave_valid_child_free() -> None:
    valid = _request(
        "valid.split",
        split_from_dof_ref="capture.shared",
        counterfactual_refs=("fixture:valid-split",),
    )
    invalid = _request(
        "invalid.split",
        requested_mode="BROKEN",  # type: ignore[arg-type]
        split_from_dof_ref="capture.shared",
    )

    report = evaluate_numeric_dof_requests(
        [valid, invalid],
        {valid.dof_id: _counterfactual_evidence()},
    )

    assert [result.reason_code for result in report.results] == [
        "FREE_SPLIT_WITHOUT_NEW_EVIDENCE",
        "INVALID_REQUESTED_NUMERIC_MODE",
    ]
    assert report.admitted_free_dof_count == 0


def test_invalid_mode_peer_cannot_escape_residual_refactor_group() -> None:
    valid = _request(
        "valid.residual",
        scope=CalibrationScope.SPECIES_RESIDUAL,
        scope_ref="species:valid",
        shared_baseline_ref="archetype:cold-deep",
        residual_stable_across_contexts=True,
        residual_pattern_group="thermal:positive",
        counterfactual_refs=("fixture:valid-residual",),
    )
    invalid = _request(
        "invalid.residual",
        requested_mode="BROKEN",  # type: ignore[arg-type]
        scope=CalibrationScope.SPECIES_RESIDUAL,
        scope_ref="species:invalid",
        residual_pattern_group="thermal:positive",
    )

    report = evaluate_numeric_dof_requests(
        [valid, invalid],
        {valid.dof_id: _counterfactual_evidence()},
    )

    assert [result.reason_code for result in report.results] == [
        "SHARED_MODEL_REFACTOR_REQUIRED",
        "INVALID_REQUESTED_NUMERIC_MODE",
    ]
    assert report.refactor_required_groups == ("thermal:positive",)
    assert report.admitted_free_dof_count == 0


def test_invalid_nonfree_peer_still_guards_all_set_level_groups() -> None:
    valid_compensation = _request(
        "valid.compensation",
        counterfactual_refs=("fixture:valid-compensation",),
    )
    invalid_compensation = _request(
        "invalid.compensation",
        requested_mode=RequestedNumericMode.TIED,
        scope="BROKEN",  # type: ignore[arg-type]
    )
    valid_split = _request(
        "valid.split-nonfree",
        split_from_dof_ref="capture.shared-nonfree",
        counterfactual_refs=("fixture:valid-split-nonfree",),
    )
    invalid_split = _request(
        "invalid.split-nonfree",
        requested_mode=RequestedNumericMode.FIXED,
        split_from_dof_ref="capture.shared-nonfree",
        counterfactual_refs="invalid",  # type: ignore[arg-type]
    )
    valid_residual = _request(
        "valid.residual-nonfree",
        scope=CalibrationScope.SPECIES_RESIDUAL,
        scope_ref="species:valid-nonfree",
        shared_baseline_ref="archetype:cold-deep",
        residual_stable_across_contexts=True,
        residual_pattern_group="thermal:nonfree-peer",
        counterfactual_refs=("fixture:valid-residual-nonfree",),
    )
    invalid_residual = _request(
        "invalid.residual-nonfree",
        requested_mode=RequestedNumericMode.DERIVED,
        scope=CalibrationScope.SPECIES_RESIDUAL,
        scope_ref="species:invalid-nonfree",
        residual_pattern_group="thermal:nonfree-peer",
        evidence_refs="invalid",  # type: ignore[arg-type]
    )
    requests = [
        valid_compensation,
        invalid_compensation,
        valid_split,
        invalid_split,
        valid_residual,
        invalid_residual,
    ]
    evidence = {
        valid_compensation.dof_id: IdentifiabilityEvidence(
            isolatable_counterfactual_or_ablation=True,
            compensation_equivalence_group="group:nonfree-peer",
        ),
        invalid_compensation.dof_id: IdentifiabilityEvidence(
            compensation_equivalence_group="group:nonfree-peer"
        ),
        valid_split.dof_id: _counterfactual_evidence(),
        valid_residual.dof_id: _counterfactual_evidence(),
    }

    report = evaluate_numeric_dof_requests(requests, evidence)

    assert [result.reason_code for result in report.results] == [
        "COMPENSATION_EQUIVALENCE_CONFLICT",
        "INVALID_CALIBRATION_SCOPE",
        "FREE_SPLIT_WITHOUT_NEW_EVIDENCE",
        "COUNTERFACTUAL_REFERENCE_REQUIRED",
        "SHARED_MODEL_REFACTOR_REQUIRED",
        "MEASUREMENT_REFERENCE_REQUIRED",
    ]
    assert report.admitted_free_dof_count == 0


def test_malformed_residual_without_pattern_blocks_valid_peer() -> None:
    valid = _request(
        "valid.residual-pattern",
        scope=CalibrationScope.SPECIES_RESIDUAL,
        scope_ref="species:valid-pattern",
        shared_baseline_ref="archetype:cold-deep",
        residual_stable_across_contexts=True,
        residual_pattern_group="thermal:positive",
        counterfactual_refs=("fixture:valid-pattern",),
    )
    malformed = _request(
        "malformed.residual-pattern",
        requested_mode=RequestedNumericMode.TIED,
        scope=CalibrationScope.SPECIES_RESIDUAL,
        scope_ref="species:malformed-pattern",
        shared_baseline_ref="archetype:cold-deep",
        residual_stable_across_contexts=True,
        evidence_refs="invalid",  # type: ignore[arg-type]
    )

    report = evaluate_numeric_dof_requests(
        [valid, malformed],
        {valid.dof_id: _counterfactual_evidence()},
    )

    assert [result.reason_code for result in report.results] == [
        "SPECIES_RESIDUAL_PATTERN_REQUIRED",
        "MEASUREMENT_REFERENCE_REQUIRED",
    ]
    assert report.admitted_free_dof_count == 0


def test_split_evidence_category_cannot_relabel_shared_proof() -> None:
    measurement = _request(
        "capture.measurement-relabel",
        split_from_dof_ref="capture.shared-relabel",
        evidence_refs=("proof:same",),
    )
    fixture = _request(
        "capture.fixture-relabel",
        split_from_dof_ref="capture.shared-relabel",
        fixture_refs=("proof:same",),
    )

    report = evaluate_numeric_dof_requests(
        [measurement, fixture],
        {
            measurement.dof_id: IdentifiabilityEvidence(
                independently_constraining_measurement=True
            ),
            fixture.dof_id: IdentifiabilityEvidence(isolatable_fixture=True),
        },
    )

    assert all(result.reason_code == "FREE_SPLIT_WITHOUT_NEW_EVIDENCE" for result in report.results)
    assert report.admitted_free_dof_count == 0


def test_string_species_scope_peer_blocks_valid_residual() -> None:
    valid = _request(
        "valid.string-scope-residual",
        scope=CalibrationScope.SPECIES_RESIDUAL,
        scope_ref="species:valid-string-scope",
        shared_baseline_ref="archetype:cold-deep",
        residual_stable_across_contexts=True,
        residual_pattern_group="thermal:string-scope",
        counterfactual_refs=("fixture:valid-string-scope",),
    )
    malformed = _request(
        "malformed.string-scope-residual",
        requested_mode=RequestedNumericMode.TIED,
        scope="SPECIES_RESIDUAL",  # type: ignore[arg-type]
        scope_ref="species:malformed-string-scope",
    )

    report = evaluate_numeric_dof_requests(
        [valid, malformed],
        {valid.dof_id: _counterfactual_evidence()},
    )

    assert [result.reason_code for result in report.results] == [
        "SPECIES_RESIDUAL_PATTERN_REQUIRED",
        "INVALID_CALIBRATION_SCOPE",
    ]
    assert report.admitted_free_dof_count == 0


def test_missing_nonfree_requirement_still_guards_explicit_groups() -> None:
    valid_compensation = _request(
        "valid.requirement-compensation",
        counterfactual_refs=("fixture:requirement-compensation",),
    )
    missing_tie = _request(
        "missing.tie-requirement",
        requested_mode=RequestedNumericMode.TIED,
    )
    valid_split = _request(
        "valid.requirement-split",
        split_from_dof_ref="capture.shared-requirement",
        counterfactual_refs=("fixture:requirement-split",),
    )
    missing_fixed = _request(
        "missing.fixed-requirement",
        requested_mode=RequestedNumericMode.FIXED,
        split_from_dof_ref="capture.shared-requirement",
    )
    valid_residual = _request(
        "valid.requirement-residual",
        scope=CalibrationScope.SPECIES_RESIDUAL,
        scope_ref="species:valid-requirement",
        shared_baseline_ref="archetype:cold-deep",
        residual_stable_across_contexts=True,
        residual_pattern_group="thermal:requirement",
        counterfactual_refs=("fixture:requirement-residual",),
    )
    missing_derivation = _request(
        "missing.derivation-requirement",
        requested_mode=RequestedNumericMode.DERIVED,
        scope=CalibrationScope.SPECIES_RESIDUAL,
        scope_ref="species:missing-requirement",
        residual_pattern_group="thermal:requirement",
    )
    requests = [
        valid_compensation,
        missing_tie,
        valid_split,
        missing_fixed,
        valid_residual,
        missing_derivation,
    ]
    evidence = {
        valid_compensation.dof_id: IdentifiabilityEvidence(
            isolatable_counterfactual_or_ablation=True,
            compensation_equivalence_group="group:missing-requirement",
        ),
        missing_tie.dof_id: IdentifiabilityEvidence(
            compensation_equivalence_group="group:missing-requirement"
        ),
        valid_split.dof_id: _counterfactual_evidence(),
        valid_residual.dof_id: _counterfactual_evidence(),
    }

    report = evaluate_numeric_dof_requests(requests, evidence)

    assert [result.reason_code for result in report.results] == [
        "COMPENSATION_EQUIVALENCE_CONFLICT",
        "TIE_NOT_DECLARED",
        "FREE_SPLIT_WITHOUT_NEW_EVIDENCE",
        "DESIGN_CONSTRAINT_NOT_DECLARED",
        "SHARED_MODEL_REFACTOR_REQUIRED",
        "DERIVATION_NOT_DECLARED",
    ]
    assert report.admitted_free_dof_count == 0


def test_whitespace_string_species_scope_peer_blocks_valid_residual() -> None:
    valid = _request(
        "valid.whitespace-scope-residual",
        scope=CalibrationScope.SPECIES_RESIDUAL,
        scope_ref="species:valid-whitespace-scope",
        shared_baseline_ref="archetype:cold-deep",
        residual_stable_across_contexts=True,
        residual_pattern_group="thermal:whitespace-scope",
        counterfactual_refs=("fixture:valid-whitespace-scope",),
    )
    malformed = _request(
        "malformed.whitespace-scope-residual",
        requested_mode=RequestedNumericMode.TIED,
        scope=" SPECIES_RESIDUAL ",  # type: ignore[arg-type]
        scope_ref="species:malformed-whitespace-scope",
    )

    report = evaluate_numeric_dof_requests(
        [valid, malformed],
        {valid.dof_id: _counterfactual_evidence()},
    )

    assert [result.reason_code for result in report.results] == [
        "SPECIES_RESIDUAL_PATTERN_REQUIRED",
        "INVALID_CALIBRATION_SCOPE",
    ]
    assert report.admitted_free_dof_count == 0


def test_split_evidence_duplicate_references_are_canonicalized() -> None:
    requests = [
        _request(
            "capture.single-proof",
            split_from_dof_ref="capture.shared-duplicate-proof",
            fixture_refs=("proof:same",),
        ),
        _request(
            "capture.duplicate-proof",
            split_from_dof_ref="capture.shared-duplicate-proof",
            fixture_refs=(" proof:same ", "proof:same"),
        ),
    ]
    evidence = {
        request.dof_id: IdentifiabilityEvidence(isolatable_fixture=True) for request in requests
    }

    report = evaluate_numeric_dof_requests(requests, evidence)

    assert all(result.reason_code == "FREE_SPLIT_WITHOUT_NEW_EVIDENCE" for result in report.results)
    assert report.admitted_free_dof_count == 0


def test_split_evidence_reference_whitespace_is_canonicalized() -> None:
    requests = [
        _request(
            "capture.whitespace-a",
            split_from_dof_ref=" capture.shared-whitespace ",
            fixture_refs=("fixture:same",),
        ),
        _request(
            "capture.whitespace-b",
            split_from_dof_ref="capture.shared-whitespace",
            fixture_refs=(" fixture:same ",),
        ),
    ]
    evidence = {
        request.dof_id: IdentifiabilityEvidence(isolatable_fixture=True) for request in requests
    }

    report = evaluate_numeric_dof_requests(requests, evidence)

    assert all(result.reason_code == "FREE_SPLIT_WITHOUT_NEW_EVIDENCE" for result in report.results)
    assert report.admitted_free_dof_count == 0


def test_unordered_invalid_id_raises_deterministic_validation_error() -> None:
    requests = {
        _request("valid"),
        _request(1),  # type: ignore[arg-type]
    }

    with pytest.raises(ValueError, match="dof_id must be a nonblank string"):
        evaluate_numeric_dof_requests(requests)

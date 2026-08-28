from __future__ import annotations

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
    assert {result.reason_code for result in report.results} == {
        "IDENTIFIABILITY_NOT_PROVEN"
    }
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
        result.reason_code == "COMPENSATION_EQUIVALENCE_CONFLICT"
        for result in report.results
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
        {
            fixed.dof_id: IdentifiabilityEvidence(
                explicit_tying_or_design_constraint=True
            )
        },
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

    assert all(
        result.reason_code == "SHARED_MODEL_REFACTOR_REQUIRED"
        for result in report.results
    )
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

    assert all(
        result.reason_code == "FREE_SPLIT_WITHOUT_NEW_EVIDENCE"
        for result in report.results
    )
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

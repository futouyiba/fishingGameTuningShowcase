# Verification strategy

## Verification tracks

### Legacy environment-field tests
Existing tests under `tests/test_sanity.py` and `tests/test_determinism.py` protect the older environment-field prototype. `test_weights_are_normalized_per_voxel` remains a legacy/precompute invariant and must not be generalized into Current Candidate Weight.

### Current Candidate Weight reference tests
Tests under `tests/reference_harness/` protect the current deterministic contract.

Release-blocking coverage includes:
- fixed-pan kernel identities and scale invariance;
- Readiness public packet isolation;
- Current Capture runtime surface `hasEligibleResponseMode + captureRetention`;
- mode-local sibling isolation and all-mode-ineligible behavior;
- legacy `hardValid / captureEligible` cannot replace the canonical packet gate;
- explicit B/P/E baked-stage consumption and duplicate-stage blockers.

### Current Fallback settlement reference tests
Tests under `tests/fallback_integration/` protect the state transition between authoritative replay TrueNone results and Fallback safety state.

Coverage includes:
- exact Debt: `D += -ln(1-p_spawn)` from authoritative post-floor actual TruePool probability;
- Fallback-owned Gate planning: Pool eligibility, monotone `G`, `P_gate=1-exp(-ΔG)`;
- Fish Spawn Commit lifecycle reset via `settle_spawn_commit(...)`;
- `RT-FB-017`: empty Pool still updates Debt but cannot advance `G` or consume Gate/Species RNG;
- retry/idempotency for the same logical `OpportunitySeq`;
- Gate miss applies deliverable extra hazard but consumes no Species RNG;
- Gate hit consumes Species RNG and enters `OCCUPIED_POST_SPAWN`.

### Current Server replay reference tests
Tests under `tests/replay_integration/` protect logical replay semantics independently of transport shape.

Coverage includes:
- `RP-AUTH-034`: step-hook and single-batch paths over the same logical Opportunity sequence must produce the same canonical Candidate digest, `p_spawn`, TrueRoll, Fallback state, RandomAddresses and Fish Spawn Commit boundary; only request count may differ;
- Replay authoritative `p_spawn` must equal Candidate Weight `calculate_true_pool(...).spawn_probability_per_opportunity`;
- Client-derived debug claims are ignored as authority inputs;
- Candidate insertion order is canonicalized before stochastic branching;
- Replay consumes Fallback-owned `plan_fallback_gate`, `fallback_gate_hits`, `settle_spawn_commit` and `settle_true_none`, rather than duplicating Fallback math/lifecycle.

The reference `RandomAddress = RngEpoch + Domain + LogicalEvent + DrawSlot` is a semantic address model. The fixture SHA-256 uniform resolver is not the Production RNG contract.

### Current Opportunity semantic reference tests
Tests under `tests/opportunity_semantic/` protect Fixture-K semantics from already-resolved Opportunity-facing source traces through Candidate-kernel handoff.

Coverage includes:
- **Logical-time crossing locality:** one accepted measure span that crosses multiple thresholds emits multiple ordered Opportunities at their individual crossing times; packet/chunk endpoint cannot collapse them into one occurrence;
- **Continuous measure != Renewal:** `ProgressSlot.occurrence_mode` explicitly distinguishes `renewal` from `once_per_scope` rather than treating every continuous source as a periodic ticket clock;
- **Formation/Evaluation separation:** Static renewal may form from Dwell while evaluating a Point; Retrieve may form from effective progress while evaluating Traversal support;
- **Evaluation-measure identity:** Qualified Time and Qualified Traversal produce different `alpha` shares from the same logical history; runtime sample count is not a measure source;
- **Stable event identity:** duplicate callbacks with the same semantic `event_id` produce one admitted EventSlot occurrence; callback count cannot create extra tickets;
- **Weighted support vs context:** Event Point can carry bounded antecedent context, but context refs have zero measure mass and do not alter `alpha`;
- **No Future-Duration Leakage:** a OncePerScope pause ticket at `t*` is unchanged when only the future continuation of the same pause is lengthened;
- **Technique != measure owner:** one technique can emit sequential Point and Time slots; slot order follows FormationPolicy order when logical times tie;
- **Channel close:** source mass after Active Channel close cannot create later Opportunities;
- **Join Before Reduce:** fixture-only `L_{i,j} * C_{i,j}` is joined on each positive support before `alpha` reduction, preventing phantom mass from `avg(L) * avg(C)`;
- **Coverage fail-closed:** every positive support must expose the same materialized Species set in the fixture stub; mismatched coverage raises instead of silently dropping or zero-filling a Species;
- **Kernel handoff:** resolved opportunity-scoped weights feed the existing Candidate Weight `calculate_true_pool(...)`; the Opportunity adapter does not duplicate TrueRoll math;
- **ScopeClip boundary:** non-null `scope_clip_policy_ref` is fail-closed in Adapter V1 until an admitted owner policy exists; tests must not invent a result-dependent clip.

Fixture-K `MeasureSpan` uses linear interpolation inside an already-semantic accepted span only as a deterministic fixture encoding for locating known crossings. It is not a Production sampling, packetization, or raw-presentation recognition contract.

### Reference Numeric DOF identifiability tests
Tests under `tests/validation_reference/test_numeric_dof_identifiability.py` protect the admission invariant `Semantic independence != independent tuning DOF`.

Blocker coverage includes:
- `ID-01`: an unconstrained requested FREE coefficient is rejected;
- `ID-02`: distinct semantic owners alone do not buy distinct FREE numeric degrees of freedom;
- `ID-03`: simultaneous FREE requests in one compensation-equivalence group are rejected without selecting an arbitrary winner;
- `ID-04`: a traceable isolatable counterfactual or ablation admits FREE;
- `ID-05`: an explicit tie admits or downgrades to TIED, not FREE;
- `ID-06`: an explicit design policy admits FIXED and does not increase the FREE count;
- `ID-07`: a sparse species residual requires a shared baseline, cross-context stability and independently constraining evidence;
- `ID-08`: repeated same-direction species residuals require shared-model refactoring rather than additional species FREE degrees of freedom;
- `ID-09`: KPI matching or compensation is not identifiability evidence;
- `ID-10`: splitting a shared parameter into multiple FREE requests requires new independent evidence.

The aggregate admission report keeps declared fields separate from independent numeric freedom through `requested_dof_count`, `admitted_free_dof_count`, `admitted_tied_count`, `admitted_fixed_count`, `admitted_derived_count`, `rejected_count`, `free_dof_by_scope`, `species_residual_free_count`, `compensation_group_conflicts`, and `refactor_required_groups`.

The gate consumes explicit synthetic metadata and fixture references. It does not fit coefficients, infer semantic ownership, require the Production species roster, or implement a symbolic identifiability solver. Green Reference CI does not prove that Production calibration admission enforcement exists or is wired to this validator.

## CI gate
`./verify.sh` is the repository gate and uses non-mutating `ruff format --check`, Ruff lint, and pytest.

A green repository CI proves only the registered Reference tests. Production compatibility still requires a pinned Production adapter and differential execution against these references.

## Regression policy
Store small deterministic fixtures and numeric results. Prefer numeric assertions over pixel-perfect image diffs. Do not use Monte Carlo to test deterministic fixed-pan or cumulative-hazard identities.

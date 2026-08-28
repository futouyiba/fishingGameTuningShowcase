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

### Current ActualPresentation realization reference tests
Tests in `tests/reference_harness/test_actual_presentation_realization.py` protect the upstream fish-agnostic realization boundary before Opportunity and Interaction.

Release-blocking coverage includes:
- **AP-01 — fish independence:** changing an external Species choice cannot change canonical Presentation output because Species is absent from the realization contract;
- **AP-02 — identity is causal lineage only:** different item, technique and rig IDs with equivalent capabilities preserve semantic identity while producing distinct opaque input fingerprints;
- **AP-03 — authoritative physics causality:** authoritative flow changes derived drift, motion and position;
- **AP-04 — fish/evaluative anti-fields:** recursive payload injection fails with a typed ownership violation, and admission is allowlist-based so unlisted fish-preference synonyms (`trout-preferred`, `ticket_rate`, `strike_likelihood`) fail closed rather than passing a denylist gap (ADR 0003);
- **AP-05 — Opportunity anti-fields:** cadence and Opportunity formation/lifecycle fields are rejected;
- **AP-06 — Interaction anti-fields:** fish perception and response fields are rejected;
- **AP-07 — typed incompleteness:** every required unresolved input returns `Unknown`, `Unsupported` or `InsufficientEvidence` and no numeric `ActualPresentation`;
- **AP-08 — World authority lineage:** World snapshot/revision stays in provenance while Presentation owns only derived realization facts;
- **AP-09 — version and lineage validation:** semantic version, resolver/projection version, input fingerprint and canonical identity mismatches fail closed;
- **AP-10 — deterministic replay:** replay bytes are stable and insignificant numeric representation noise canonicalizes without becoming an identity setter;
- **AP-11 — bounded temporal motif:** equivalent split/merged phase segmentation normalizes to equivalent semantic output;
- **AP-12 — downstream Opportunity boundary:** a test-local projection feeds the existing `opportunity_reference` API, while production Presentation code neither imports nor constructs Opportunity types.

The reference kinematic projection proves the semantic boundary only. It does not implement Production fishing physics, determine fish preference or perception, construct or consume `LogicalOpportunity`, own cadence/refractory/non-overlap, or calculate Candidate Weight. A validated client-derived carrier remains a claim; Reference lineage consistency does not grant Production authority.

## CI gate
`./verify.sh` is the repository gate and uses non-mutating `ruff format --check`, Ruff lint, and pytest.

A green repository CI proves only the registered Reference tests. Production compatibility still requires a pinned Production adapter and differential execution against these references.

## Regression policy
Store small deterministic fixtures and numeric results. Prefer numeric assertions over pixel-perfect image diffs. Do not use Monte Carlo to test deterministic fixed-pan or cumulative-hazard identities.

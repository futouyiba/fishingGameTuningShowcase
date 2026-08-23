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

## CI gate
`./verify.sh` is the repository gate and uses non-mutating `ruff format --check`, Ruff lint, and pytest.

A green repository CI proves only the registered Reference tests. Production compatibility still requires a pinned Production adapter and differential execution against these references.

## Regression policy
Store small deterministic fixtures and numeric results. Prefer numeric assertions over pixel-perfect image diffs. Do not use Monte Carlo to test deterministic fixed-pan or cumulative-hazard identities.

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

This runner consumes upstream `resolved_g_target`; it does not redefine adaptive-effective-time / Tail Envelope policy. `OpportunitySeq` is a logical replay identity, not a per-opportunity RPC requirement.

## CI gate
`./verify.sh` is the repository gate and uses non-mutating `ruff format --check`, Ruff lint, and pytest.

A green repository CI proves only the registered Reference tests. Production compatibility still requires a pinned Production adapter and differential execution against these references.

## Regression policy
Store small deterministic fixtures and numeric results. Prefer numeric assertions over pixel-perfect image diffs. Do not use Monte Carlo to test deterministic fixed-pan or cumulative-hazard identities.

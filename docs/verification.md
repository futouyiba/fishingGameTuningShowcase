# Verification strategy

## Verification tracks

### Legacy environment-field tests
Existing tests under `tests/test_sanity.py` and `tests/test_determinism.py` protect the older environment-field prototype. In particular, `test_weights_are_normalized_per_voxel` is a legacy/precompute invariant and must not be generalized into the current Candidate Weight model.

### Current Candidate Weight reference tests
Tests under `tests/reference_harness/` protect the current deterministic contract without importing production-runtime functions.

Initial release-blocking coverage:
- Fixed-pan kernel: unsaturated competitor suppression must not change another species' absolute target roll time; saturated whole-pool scale must preserve composition/throughput; proportional runtime encoding scale (`weights + N`) is invariant.
- Public packet surface: Readiness consumers only depend on the canonical `ResolvedBehavioralContext` public fields; Capture runtime only consumes `captureRetention` + `hardValid`; missing required fields fail closed with `PRODUCER_MISSING_REQUIRED_FIELD`.
- Explain isolation: changing internal Readiness or Capture explain-only fields must not change the runtime-facing surface (`CONSUMER_DEPENDS_ON_INTERNAL_EXPLAIN` class of regression).
- Compiled ambient stage consumption: an artifact that already baked `B/P/E` must not consume those stages again (`DUPLICATE_STAGE_CONSUMPTION`); unknown bake metadata blocks evaluation with `BAKED_STAGE_UNKNOWN`; partial bake consumes only missing stages.
- Hard invalid remains outside soft capture retention: `hardValid=false` yields effective capture `0` even when `captureRetention>0`.

### Current Fallback settlement reference tests
Tests under `tests/fallback_integration/` protect the state transition between authoritative replay TrueNone results and Fallback safety state.

Initial release-blocking coverage:
- Exact Debt: `D += -ln(1-p_spawn)` using the authoritative **post-floor actual** TruePool probability.
- `RT-FB-017`: if the authoritative Fallback Pool is empty, TrueNone still updates `D`, but `G` must not advance and neither `FALLBACK_GATE` nor `FALLBACK_SPECIES` RNG may be consumed.
- Retry/idempotency: repeating the same logical `OpportunitySeq` is a no-op even if a Pool becomes available later.
- Non-empty Pool: once extra hazard is actually offered to a deliverable pool, a Gate miss still advances applied `G` and consumes only the Gate RNG domain.
- Gate hit: Species RNG is consumed only after Gate hit, then Fallback Fish Spawn Commit ends the No-Spawn streak and enters `OCCUPIED_POST_SPAWN`.

This runner deliberately consumes an upstream `resolved_g_target`; it does not redefine the current adaptive-effective-time / Tail Envelope policy. It also treats `OpportunitySeq` as a logical replay identity, not a per-opportunity RPC requirement.

### Current Server replay reference tests
Tests under `tests/replay_integration/` protect replay semantics independently from transport shape.

Initial release-blocking coverage:
- `RP-AUTH-034`: the same ordered logical Opportunity sequence produces the same canonical candidate digests, `p_spawn`, TrueRoll results, Fallback state transitions, RandomAddresses, and Fish Spawn Commit boundary whether evaluated through step hooks or one batch replay window. Only transport request count may differ; failure class=`REPLAY_SEMANTICS_ASSUMED_AS_RPC`.
- Inputs-only authority: changing Client-derived debug claims (`pSpawn`, TrueRoll, Fish identity) does not alter authoritative replay output.
- Canonical candidate order: dictionary/insertion order cannot change the canonical digest or stochastic result.
- Addressed RNG: reference draws are separated by `RngEpoch + Domain + LogicalEvent + DrawSlot`; optional Fallback branches do not define the `TRUE_ROLL` address.

This is a reference implementation of addressed deterministic replay semantics, not a production RNG library, network protocol, cadence guard, lease/persistence implementation, or anti-cheat proof.

## CI gate
`./verify.sh` remains the repository gate and GitHub Actions runs it on push and pull request. The gate uses non-mutating `ruff format --check`, Ruff lint, and pytest.

A green repository CI means only that the registered reference tests passed. It does **not** prove production FG runtime compatibility until a production adapter is pinned to a real repo/branch/commit/build and differential-tested against these references.

## Regression policy
Store small deterministic fixtures and numeric results. Prefer numeric assertions over pixel-perfect image diffs. Do not use Monte Carlo to test deterministic fixed-pan, cumulative-hazard, or replay-identity invariants.

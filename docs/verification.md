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

## CI gate
`./verify.sh` remains the repository gate and GitHub Actions runs it on push and pull request. The current reference tests are ordinary pytest tests, so once this branch is evaluated by the existing workflow they run in the same gate as the legacy tests.

A green repository CI means only that the registered tests passed. It does **not** prove production FG runtime compatibility until a production adapter is pinned to a real repo/branch/commit/build and differential-tested against this reference.

## Regression policy
Store small deterministic fixtures and numeric results. Prefer numeric assertions over pixel-perfect image diffs. Do not use Monte Carlo to test deterministic fixed-pan identities.

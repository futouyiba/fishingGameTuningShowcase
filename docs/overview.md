# Overview

This repo exists to turn fishing-sim numeric systems into **verifiable artifacts**.

It now contains four explicitly separated verification tracks:

1. **Legacy environment-field track**
   - Configs (nested JSON) -> derived environment field (`x*y*z*fish`)
   - Existing visualization and voxel-oriented sanity tests remain useful as historical/precompute tooling.
   - Those tests do **not** define the current Candidate Weight constitution.

2. **Current Candidate Weight reference track**
   - Pure deterministic fixed-pan reference kernel
   - Public cross-domain packet-contract tests
   - Current Capture runtime surface: `hasEligibleResponseMode + captureRetention`; legacy `hardValid/captureEligible` is not a canonical required field
   - Mode-local eligibility derivation protects sibling isolation: one ineligible Mode does not invalidate another eligible Mode
   - Compiled ambient `B/P/E` stage-consumption guards
   - Implemented under `candidate_weight_reference/` with tests under `tests/reference_harness/`

3. **Current Fallback settlement reference track**
   - Pure deterministic `FallbackSafetyState` transition runner
   - Consumes authoritative replay results rather than transport/RPC semantics
   - `p_spawn` is the already-resolved **post-floor actual TruePool probability**; this runner does not recompute Candidate Weight
   - Tail/Envelope policy resolves `G_target` upstream; Fallback owns Pool eligibility, applied-hazard/Gate math and Spawn-Commit lifecycle helpers
   - Implemented under `fallback_reference/` with tests under `tests/fallback_integration/`

4. **Current Server replay reference track**
   - Replays ordered logical `OpportunitySeq` entries independently of transport request count
   - Uses reference `RandomAddress = RngEpoch + Domain + LogicalEvent + DrawSlot`
   - Ignores Client-derived debug claims as authority inputs and canonicalizes Candidate ordering before stochastic branching
   - Consumes Candidate Weight `calculate_true_pool(...)` for fixed-pan probabilities rather than recalculating `F/max(N,F)` or `P_spawn`
   - Calls Fallback-owned planning, Gate and Spawn-Commit lifecycle helpers rather than duplicating Fallback formulas/state transitions
   - Protects `RP-AUTH-034` step-hook vs batch replay transport-shape invariance
   - Implemented under `replay_reference/` with tests under `tests/replay_integration/`

The current reference tracks are intentionally isolated from `compute/`: they must not inherit the legacy invariant that fish weights are normalized to 1 per voxel. Future production adapters should be differential-tested against these references rather than reusing production functions as their oracle.

See:
- `docs/data_schema.md`
- `docs/verification.md`

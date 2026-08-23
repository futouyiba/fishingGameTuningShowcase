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
   - Compiled ambient `B/P/E` stage-consumption guards
   - Implemented under `candidate_weight_reference/` with tests under `tests/reference_harness/`

3. **Current Fallback settlement reference track**
   - Pure deterministic `FallbackSafetyState` transition runner
   - Consumes authoritative replay results rather than transport/RPC semantics
   - `p_spawn` is the already-resolved **post-floor actual TruePool probability**; this runner does not recompute Candidate Weight
   - Tail/Envelope policy resolves the desired `G_target` upstream; this runner owns Pool eligibility, applied-hazard/Gate math and Spawn-Commit lifecycle helpers
   - Implemented under `fallback_reference/` with tests under `tests/fallback_integration/`

4. **Current Server replay reference track**
   - Replays ordered logical `OpportunitySeq` entries independently of transport request count
   - Uses reference `RandomAddress = RngEpoch + Domain + LogicalEvent + DrawSlot`
   - Ignores Client-derived debug claims as authority inputs and canonicalizes Candidate ordering before stochastic branching
   - Calls Fallback-owned planning, Gate and Spawn-Commit lifecycle helpers rather than duplicating Fallback formulas/state transitions
   - Protects `RP-AUTH-034` step-hook vs batch replay transport-shape invariance
   - Implemented under `replay_reference/` with tests under `tests/replay_integration/`

The current reference tracks are intentionally isolated from `compute/`: they must not inherit the legacy invariant that fish weights are normalized to 1 per voxel. Current Candidate Weight, Fallback settlement and Replay semantics are tested independently, and future production adapters should be differential-tested against these references rather than reusing production functions as their oracle.

See:
- `docs/data_schema.md`
- `docs/verification.md`

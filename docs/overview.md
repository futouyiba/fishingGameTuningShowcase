# Overview

This repo exists to turn fishing-sim numeric systems into **verifiable artifacts**.

It now contains five explicitly separated verification tracks:

1. **Legacy environment-field track**
   - Configs (nested JSON) -> derived environment field (`x*y*z*fish`)
   - Existing visualization and voxel-oriented sanity tests remain useful as historical/precompute tooling.
   - Those tests do **not** define the current Candidate Weight constitution.

2. **Current Candidate Weight reference track**
   - Pure deterministic fixed-pan reference kernel
   - Canonical Candidate composition (`q_i,j = Combine(L_i,j, C_i,j)` → support-wise Join → Reduce) is owned by the Candidate Resolver / Assembly Current and the concrete `Combine` operator stays Open; this track implements and verifies the admitted Production specialization `Combine_prod(L, C) = localSpeciesIntensity × captureRetention` via `CandidateWeightInputs`, whose numeric consumer surface still admits no readiness / aggregation / global-availability multiplier
   - Readiness public surface no longer requires `globalAvailability`; Interaction consumes states / motivation / enabled modes and projects behavioral effects into the resolved `captureRetention`
   - Current Capture runtime surface: `hasEligibleResponseMode + captureRetention`; the flag is typed zero / policy-guard metadata (a positive retention without an eligible mode fails closed as `CAPTURE_PACKET_INCONSISTENT`), not a consumer-side gate multiplier; legacy `hardValid/captureEligible` is not a canonical required field
   - Mode-local eligibility derivation protects sibling isolation: one ineligible Mode does not invalidate another eligible Mode
   - Compiled ambient `B/P/E` stage-consumption guards
   - The retired `×G×V×C` factorized chain exists only in `candidate_weight_reference/legacy.py` behind explicitly marked pinned legacy fixtures that materialize a final W for the shared kernel
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

5. **Current Opportunity semantic reference track**
   - Starts from already-semantic `Qualified Measure / Semantic Event / Channel Close` traces; it does not recognize raw gestures or physics callbacks
   - Resolves `ProgressSlot | EventSlot` into ordered `LogicalOpportunity` trace items at their logical crossing/event times
   - Keeps Formation measure, Evaluation measure, weighted support and zero-mass context distinct
   - Supports Point/Event, Qualified Time and Qualified Traversal reference evaluation; Phase masks consume pinned semantic tags rather than fish preference
   - Preserves multiple threshold crossings inside one accepted source chunk instead of collapsing them to the chunk endpoint
   - Event occurrences dedupe by stable semantic event identity; callback count cannot create extra tickets
   - Optional fixture-only support joins apply `Join Before Reduce` before feeding opportunity-scoped weights into the existing Candidate Weight `calculate_true_pool(...)`
   - ScopeClip remains fail-closed until an admitted owner policy is implemented; the adapter does not invent a clipping rule
   - Implemented under `opportunity_reference/` with Fixture-K tests under `tests/opportunity_semantic/`

The current reference tracks are intentionally isolated from `compute/`: they must not inherit the legacy invariant that fish weights are normalized to 1 per voxel. Future production adapters should be differential-tested against these references rather than reusing production functions as their oracle.

See:
- `docs/data_schema.md`
- `docs/verification.md`

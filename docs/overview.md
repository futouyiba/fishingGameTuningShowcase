# Overview

This repo exists to turn fishing-sim numeric systems into **verifiable artifacts**.

It now contains six explicitly separated verification tracks:

1. **Legacy environment-field track**
   - Configs (nested JSON) -> derived environment field (`x*y*z*fish`)
   - Existing visualization and voxel-oriented sanity tests remain useful as historical/precompute tooling.
   - Those tests do **not** define the current Candidate Weight constitution.

2. **Current Candidate Weight reference track**
   - Pure deterministic fixed-pan reference kernel
   - Per Candidate Current v5 the Canonical Native Join is the TypedNativeRetentionJoin (`dQ = C · dM`; resolved-scalar branch `q = L × C` then support-wise Join Before Reduce); this track implements and verifies only that resolved-scalar numeric projection (`localSpeciesIntensity × captureRetention` via `CandidateWeightInputs`) and does not implement the typed Candidate resolution transaction (typed-zero terminality / Unknown handling / `CandidateResolutionResult` / `NativeCandidateSnapshot` / relational Source Envelope); the numeric consumer surface still admits no readiness / aggregation / global-availability multiplier
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

6. **Current ActualPresentation realization reference track**
   - Resolves Player Action + technique/equipment/rig capabilities + authoritative World/Physics into a deterministic, fish-agnostic `ActualPresentation`
   - Uses a deliberately thin kinematic projection to prove causality and ownership boundaries; it is not a Production physics simulator
   - Keeps content IDs as opaque input lineage rather than semantic identity setters, while authoritative World snapshot/revision remains provenance rather than copied Presentation-owned truth
   - Canonicalizes finite numbers, ordering and adjacent equivalent phase segments so physically equivalent episodes have equivalent semantic output; the `actual-presentation/v1` nine-digit numeric policy is pinned in `docs/adr/0002-actual-presentation-canonical-precision.md`
   - Represents required `Unknown / Unsupported / InsufficientEvidence` inputs explicitly and emits no fabricated neutral presentation
   - Rejects fish/evaluative, Opportunity-owned and Interaction-owned anti-fields recursively and validates semantic version, resolver/projection lineage, input fingerprint and canonical identity fail-closed
   - Admits canonical output through a Presentation-owned schema and closed phase/cue/descriptor vocabularies pinned in `docs/adr/0003-actual-presentation-closed-vocabularies.md`, so unlisted fish/Opportunity/Interaction synonyms fail closed instead of being admitted by a denylist gap
   - Does not calculate fish preference/perception, form or consume `LogicalOpportunity`, own cadence/refractory/non-overlap, or calculate/modify Candidate Weight
   - Client-materialized output remains a claim carrier: Reference validation checks projection consistency but does not promote it to Production authority
   - Implemented under `presentation_realization_reference/` with AP-01 through AP-12 blockers under `tests/reference_harness/`

The current reference tracks are intentionally isolated from `compute/`: they must not inherit the legacy invariant that fish weights are normalized to 1 per voxel. Future production adapters should be differential-tested against these references rather than reusing production functions as their oracle.

See:
- `docs/data_schema.md`
- `docs/verification.md`

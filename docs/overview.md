# Overview

This repo exists to turn fishing-sim numeric systems into **verifiable artifacts**.

It now contains two explicitly separated verification tracks:

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

The current reference track is intentionally isolated from `compute/`: it must not inherit the legacy invariant that fish weights are normalized to 1 per voxel. Current Candidate Weight semantics are tested independently, and future production adapters should be differential-tested against this reference rather than reusing production functions as their oracle.

See:
- `docs/data_schema.md`
- `docs/verification.md`

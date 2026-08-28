# Data schema (minimal demo)

## `data/static/fish_species.json`
Fields per species:
- `species_id` (int)
- `name` (str)
- `temp_pref_c` (float)
- `temp_tolerance_c` (float)
- `structure_affinity` (map[str,float])

## `data/static/pond_config.json`
Fields per pond:
- `pond_id` (int)
- `grid`: `{x,y,z,dx,dy,dz}`
- `structure_map`: CSV path (labels per cell)
- `base_abundance`: map[species_id -> weight]

## `data/samples/*.json` scenario
- `pond_id`
- `water_temp_profile_c`: `{surface, thermocline_depth, gradient}`
- `weather`: placeholder for future

## Current reference-only contract surfaces
These Python dataclasses/functions are verification contracts, not production wire schemas.

### Candidate Weight reference
- Resolved-Scalar Native Retention projection (Candidate Current v5: Canonical Native Join = TypedNativeRetentionJoin, `dQ = C · dM`; resolved-scalar branch `q = L × C`): `CandidateWeightInputs(local_species_intensity, capture_retention)` with `localSpeciesIntensity × captureRetention` (`calculate_multiplicative_candidate_weight` / `resolve_multiplicative_candidate_weights`); PR scope is this numeric branch only — typed closure / `CandidateResolutionResult` / `NativeCandidateSnapshot` / relational Source Envelope are not implemented here, and the consumer interface accepts no other multiplier
- Spatial output surface: `localSpeciesIntensity` (required) — the admitted resolved scalar of the Native Species Supply Measure M (density / intensity or equivalent integrated local-mass representation; not fish count, not probability) — plus optional `bakedSemanticStages / aggregationContextRef` provenance metadata that never enters arithmetic
- Readiness public surface: `activeBehavioralStates`, `motivationProfile`, `enabledResponseModes`; `globalAvailability` is not a required field and cannot re-enter the surface
- Capture runtime surface: `hasEligibleResponseMode`, `captureRetention ∈ [0,1]` — conditional retention on already-present Native Supply, not Bernoulli bite probability and not Supply amplification; the flag is typed metadata and a positive retention without an eligible mode fails closed (`CAPTURE_PACKET_INCONSISTENT`)
- `derive_has_eligible_response_mode(modeResponses[])`: `any(modeEligible[m])`
- legacy `hardValid / captureEligible` does not satisfy the Current canonical reader
- `calculate_true_pool(...)`: fixed-pan total weight, saturation, `spawn_probability_per_opportunity`, and Species `probability_per_opportunity`
- `CompiledAmbientCarrier.baked_semantic_stages`: explicit subset of `B/P/E`; missing metadata blocks evaluation
- Strong Bake Manifest envelope (`candidate_weight_reference/ambient.py`): `CompiledAmbientCarrier.bake_manifest: StrongBakeManifest | None`; a carrier with non-empty baked stages and no manifest fails closed (`BAKE_MANIFEST_MISSING`). `StrongBakeManifest(materialized, baked_semantic_stages)` validates at construction that every instance's lineage has non-empty `source_revision / dependency_fingerprint / resolver_version / projection_version` (`BAKE_LINEAGE_INCOMPLETE`), that every `instance_id` globally addresses exactly one record across all valid and invalid manifest history (`DUPLICATE_MATERIALIZATION_INSTANCE_ID`), that at most one `valid` instance exists per identity (`DUPLICATE_SEMANTIC_CONSEQUENCE`), and that the declared stage summary equals the coverage actually settled by valid instances (`BAKE_STAGE_SUMMARY_MISMATCH`). `SemanticConsequenceIdentity(cause_role, consequence_kind, coverage_scope, ownership_boundary)` is the revision-blind duplicate key — revisions/versions live only in `MaterializationLineage(source_revision, dependency_fingerprint, resolver_version, projection_version, source_snapshot_ref?, policy_overlay_provenance?)`. `MaterializedConsequence` adds `instance_id / value / typed_outcome / coverage_scope / validity_region_ref / settled_stage ∈ {B,P,E} / validity ∈ {valid, invalid, unknown}`. `settle_materialized_consequence(...)` re-submits through both duplicate guards; `invalidate_materialized_consequence(...)` addresses exactly one immutable history record by globally unique `instance_id` and expresses dependency-change replacement (invalid instances stay as history, leave the active set and never count as coverage); `active_materializations(...)` returns the valid bake set. Unknown validity blocks the numeric kernel (`BAKE_VALIDITY_UNKNOWN`). Validity is an explicit input in Reference V1 — no dependency-graph evaluator or production invalidation service is implemented here
- `legacy_factorized_weight(...)` in `candidate_weight_reference/legacy.py`: pinned historical `×G×V×C` reproduction for explicitly marked legacy fixtures only; it is not exported on the Current package surface

### Fallback settlement reference
`FallbackSafetyState` stores:
- `phase`: `SEARCHING | OCCUPIED_POST_SPAWN`
- `context_epoch`
- `streak_ordinal`
- `debt`
- `active_time_credited`
- `applied_extra_hazard`
- `last_processed_opportunity_seq`

Fallback-owned helpers:
- `plan_fallback_gate(...)`: non-empty Pool eligibility, monotone applied-`G` delta and Gate probability
- `fallback_gate_hits(...)`: Gate branch comparison
- `settle_spawn_commit(...)`: streak reset / occupancy at Fish Spawn Commit
- `settle_true_none(...)`: authoritative TrueNone Debt and Fallback settlement order

The Fallback reference does not define protobuf/RPC shape, does not recompute Candidate Weight, and does not own Tail calibration.

### Server replay reference
`ReplayLease` is a minimal reference carrier:
- `rng_epoch`
- `algorithm_version`

`ReplayEntry` contains replayable inputs plus optional non-authoritative debug claims:
- `opportunity_seq`
- `candidate_weights`
- `pan_capacity`
- `credited_active_delta`
- `resolved_g_target`
- `fallback_pool`
- `client_debug_claims`

`RandomAddress` models logical random identity as:
- `rng_epoch`
- `domain`
- `logical_event`
- `draw_slot`

`replay_stepwise(...)` and `replay_batch(...)` share one semantic evaluator and differ only in reference transport request count. Replay consumes `calculate_true_pool(...)` for fixed-pan probability surfaces and Fallback-owned helpers for Gate/lifecycle semantics. The SHA-256 based uniform resolver is only a deterministic fixture primitive and does not define the Production RNG algorithm.

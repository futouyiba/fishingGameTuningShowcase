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
- `CompiledAmbientCarrier.value`
- `CompiledAmbientCarrier.baked_semantic_stages`: explicit subset of `B/P/E`; missing metadata blocks evaluation
- Readiness public surface: `globalAvailability`, `activeBehavioralStates`, `motivationProfile`, `enabledResponseModes`
- Capture runtime surface: `captureRetention`, `hardValid`
- `calculate_true_pool(...)`: canonical fixed-pan reference result containing total weight, saturation, `spawn_probability_per_opportunity`, and each Species `probability_per_opportunity`

### Fallback settlement reference
`FallbackSafetyState` stores only state-machine semantics needed by the deterministic reference:
- `phase`: `SEARCHING | OCCUPIED_POST_SPAWN`
- `context_epoch`
- `streak_ordinal`
- `debt`: cumulative TrueNone hazard `D`
- `active_time_credited`: Server-credited active fishing time
- `applied_extra_hazard`: actually applied fallback hazard `G`
- `last_processed_opportunity_seq`: logical replay/idempotency identity

Fallback-owned helpers:
- `plan_fallback_gate(...)`: owns non-empty Pool eligibility, monotone applied-`G` delta and Gate probability
- `fallback_gate_hits(...)`: owns Gate branch comparison semantics
- `settle_spawn_commit(...)`: owns reset/occupancy transition at Fish Spawn Commit
- `settle_true_none(...)`: owns authoritative TrueNone Debt and Fallback settlement order

The reference runner does not define protobuf/RPC shape, does not recompute Candidate Weight, and does not own Tail calibration.

### Server replay reference
`ReplayLease` is a minimal reference carrier:
- `rng_epoch`
- `algorithm_version`

`ReplayEntry` contains replayable reference inputs plus optional non-authoritative debug claims:
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

`replay_stepwise(...)` and `replay_batch(...)` intentionally share the same semantic evaluator and differ only in reference transport request count. Replay canonicalizes Species order, then consumes `calculate_true_pool(...)` for fixed-pan probabilities; it does not independently compute `F`, `max(N,F)` or `P_spawn`. It also calls the Fallback-owned helpers above rather than owning Fallback Gate math or Spawn-Commit lifecycle. The SHA-256 based uniform resolver is only a deterministic fixture primitive and does not define the Production RNG algorithm.

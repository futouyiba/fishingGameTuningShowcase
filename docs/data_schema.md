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
- Readiness public surface: `globalAvailability`, `activeBehavioralStates`, `motivationProfile`, `enabledResponseModes`
- Capture runtime surface: `hasEligibleResponseMode`, `captureRetention`
- `derive_has_eligible_response_mode(modeResponses[])`: `any(modeEligible[m])`
- legacy `hardValid / captureEligible` does not satisfy the Current canonical reader
- `calculate_true_pool(...)`: fixed-pan total weight, saturation, `spawn_probability_per_opportunity`, and Species `probability_per_opportunity`
- `CompiledAmbientCarrier.baked_semantic_stages`: explicit subset of `B/P/E`; missing metadata blocks evaluation

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

The reference runner does not define protobuf/RPC shape, does not recompute Candidate Weight, and does not own Tail calibration.

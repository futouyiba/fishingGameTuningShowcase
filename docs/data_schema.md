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

### Fallback settlement reference
`FallbackSafetyState` stores only state-machine semantics needed by the deterministic reference:
- `phase`: `SEARCHING | OCCUPIED_POST_SPAWN`
- `context_epoch`
- `streak_ordinal`
- `debt`: cumulative TrueNone hazard `D`
- `active_time_credited`: Server-credited active fishing time
- `applied_extra_hazard`: actually applied fallback hazard `G`
- `last_processed_opportunity_seq`: logical replay/idempotency identity

`settle_true_none(...)` consumes:
- `opportunity_seq`
- authoritative **post-floor actual** `p_spawn`
- `credited_active_delta`
- `resolved_g_target` from the current Tail/Envelope policy resolver
- immutable authoritative `fallback_pool`
- deterministic test-hook values for `FALLBACK_GATE` / `FALLBACK_SPECIES` RNG

The reference runner does not define protobuf/RPC shape, does not recompute Candidate Weight, and does not own Tail calibration.

### Server replay reference
`ReplayLease` currently pins a reference `rng_epoch` plus a reference algorithm-version label. It is not a production lease schema.

`ReplayEntry` contains authoritative-replayable reference inputs:
- logical `opportunity_seq`
- candidate weights + `pan_capacity` used by the reference TrueRoll kernel
- credited active-time delta already accepted for this reference replay
- resolved `G_target`
- immutable fallback pool snapshot
- optional Client debug claims, which are explicitly ignored by authoritative derivation

Reference randomness is addressed by:
- `rng_epoch`
- `domain`
- logical event (`opportunity_seq` for current TrueRoll/Fallback fixtures)
- `draw_slot`

The reference resolver uses a deterministic hash only to make fixtures reproducible. It does **not** define the production RNG library or cryptographic contract.

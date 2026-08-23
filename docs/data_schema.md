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
- Capture runtime surface: `hasEligibleResponseMode`, `captureRetention`
- `derive_has_eligible_response_mode(modeResponses[])`: derives the packet gate as `any(modeEligible[m])`; one false Mode cannot invalidate an eligible sibling
- legacy `hardValid / captureEligible` may exist in adapters as compatibility aliases but do not satisfy the Current canonical reader
- `calculate_true_pool(...)`: canonical fixed-pan reference result containing total weight, saturation, `spawn_probability_per_opportunity`, and each Species `probability_per_opportunity`

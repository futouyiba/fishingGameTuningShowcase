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

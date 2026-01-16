# Porting guide (your real project -> this hub)

This repo is a scaffold. To port your existing logic:

## 1) Identify your existing inputs
From your previous description, common sources are like:
- `data\1\1001` (nested weather / fish stock / env affinity json)
- `Fishing_1006001_Dense_...\map_data.json` (grid origin, step, pools, etc.)
- Unity-exported sampling points (npy + json)

## 2) Create an adapter layer
Add `compute/adapters/` with:
- `load_project_json.py` : your nested lookup + caching
- `load_map_data.py`     : parse map_data.json into a `Grid` + structure/depth inputs

Then keep `derive_env_field.py` as the stable entrypoint.

## 3) Lock down invariants first
Before copying full formulas, add tests for:
- determinism
- no negative weights
- basic conservation-like sums

## 4) Only then port formulas
Replace the demo temp/structure scoring with your real model.

## 5) Make it one command
Update `verify.sh` so it runs:
- lint
- tests
- one derivation scenario
- one visualization export

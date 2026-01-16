# Fishing Simulation Verification Hub

A small, **engineering-first** repo to make your fishing simulation changes **provable**:

- Derive an environment field (e.g. `x*y*z*fishTypes` weights)
- Generate quick visual artifacts (PNGs)
- Enforce invariants via tests (regression + sanity checks)
- Keep docs in-sync with code

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .

# Run the full verification gate
./verify.sh

# Produce a sample derived field + PNGs
python -m scripts.run_sample
```

## What to port from your current project

This repo is designed so you can **drop in your current JSON config layout** and write a small adapter:

- Your nested config roots (e.g. `data\1\1001`) can remain unchanged
- Add a loader in `compute/adapters/` that maps your real schema → the minimal schema used by `compute/derive_env_field.py`

See: `docs/verification.md` and `compute/adapters/unity_nested_json_adapter.py`.

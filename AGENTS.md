# AGENTS.md (Codex / AI Agent Operating Rules)

## What this repo is
A verification harness for a fishing simulation pipeline:
- Read configs (nested JSON OK)
- Derive an environment weight field
- Visualize slices
- Enforce invariants with tests
- Keep docs updated

## Golden rule
**No change is "done" unless `./verify.sh` is green.**

## Commands you must use
- Format/lint: `python -m ruff format . && python -m ruff check .`
- Tests: `pytest`
- Full gate: `./verify.sh`

## When you change compute logic
1) Add/adjust tests under `tests/`
2) Keep results deterministic (seeded RNG only)
3) Avoid magical constants: move them to `data/static/` or `docs/adr/`

## Documentation expectations
- Docs are Markdown under `docs/`
- Any new concept must be added to `docs/overview.md`
- Any new invariant must be documented in `docs/verification.md`

## Style constraints
- Prefer pure functions + explicit inputs/outputs
- Keep IO (filesystem) at the edges (scripts/)
- Use `dataclasses` for structured config

# AGENTS.md (Codex / AI Agent Operating Rules)

## How to verify changes
- **Always run `./verify.sh` after code changes.**
- If tests fail, fix tests and code until green.
- No change is "done" unless `./verify.sh` is green.

## Project constraints
- **Keep everything runnable from a fresh clone.**
- Do not introduce interactive prompts in scripts.
- Prefer deterministic outputs; avoid randomness unless seeded.
- Use `dataclasses` for structured config.
- Prefer pure functions + explicit inputs/outputs.

## Data access
- **Do not assume local absolute paths.**
- Use repo-relative paths under `data/`.
- If you need external data, add a small sample under `data/samples/` and document it in `docs/data_schema.md`.
- Keep IO (filesystem) at the edges (`scripts/`).

## Docs
- **Update `docs/` when behavior changes.**
- Keep docs in Markdown.
- Any new concept must be added to `docs/overview.md`.
- Any new invariant must be documented in `docs/verification.md`.

## Commands you must use
- Format/lint: `python -m ruff format . && python -m ruff check .`
- Tests: `pytest`
- Full gate: `./verify.sh`

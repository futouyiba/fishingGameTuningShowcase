# ADR 0001: Env-field derivation as the verification anchor

## Context
We need a stable artifact to verify numeric systems across iterations.

## Decision
Use `env_field.npy` (`x*y*z*fish`) as the primary derived artifact.

## Consequences
- Tests can assert invariants on `env_field.npy` and summary metrics.
- Visualization becomes optional convenience, not the proof.

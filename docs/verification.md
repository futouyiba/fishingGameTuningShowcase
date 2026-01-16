# Verification strategy

## Invariants
- Determinism: same inputs -> same outputs
- Basic sanity: weights are finite and non-negative
- (Optional later) monotonicity wrt temperature shifts for certain species

## Regression
Store small snapshot outputs (CSV metrics) for sample scenarios.
Prefer numeric snapshots over pixel-perfect image diffs.

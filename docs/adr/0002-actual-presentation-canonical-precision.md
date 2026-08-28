# ADR 0002: ActualPresentation canonical numeric precision

## Context
`ActualPresentation` semantic identities and replay bytes must be stable when equivalent floating-point inputs differ only by insignificant representation noise. The Reference realization is not a Production physics simulator, but it needs one explicit precision policy for canonical semantic output.

## Decision
Canonicalize every finite floating-point value to nine decimal digits before serialization, identity hashing, phase comparison, or derived-vector accumulation. Normalize any rounded zero to positive `0.0`. Reject non-finite values rather than encoding them.

Nine decimal digits are the pinned Reference-Harness policy for `actual-presentation/v1`; changing this value is a semantic-version change because it can change equality, temporal merging, hashes, and downstream replay bytes.

## Consequences
- Equivalent numeric representations within the pinned precision produce equivalent semantic output.
- Values that differ beyond the pinned precision remain distinct.
- Production adapters must either reproduce this policy or use differential tests to establish an explicitly versioned mapping.
- This decision proves deterministic Reference canonicalization only; it does not prescribe Production simulation precision.

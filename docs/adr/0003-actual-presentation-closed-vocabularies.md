# ADR 0003: ActualPresentation closed ownership vocabularies

## Context
Ownership rejection for `ActualPresentation` cannot be fail-closed if it only matches a
denylist of known fish/Opportunity/Interaction field names: unrecognized synonyms such as
`trout-preferred`, `ticket_rate`, or `strike_likelihood` would be admitted as
Presentation truth. The Reference harness needs an admission policy, not only a
recognition policy.

## Decision
Admission to the canonical `ActualPresentation` payload is allowlist-based:

- The canonical payload schema admits only Presentation-owned fields
  (`realized_spatial_facts`, `realized_motion_facts`, `cue_emission_facts`,
  `target_presentation_descriptors`, `temporal_context`, `completeness`,
  `semantic_version`, `presentation_identity`, `provenance`) with their fixed nested key
  sets; any other key fails closed as `UNKNOWN_FIELD_FORBIDDEN`.
- Temporal phase labels, cue tags, and target-presentation descriptors come from closed
  Presentation-owned vocabularies pinned for `actual-presentation/v1`; anything else
  fails closed at dataclass construction and at canonical payload validation as
  `CLOSED_VOCABULARY_FORBIDDEN`.
- The recursive fish/Opportunity/Interaction concept scan is retained only to attribute
  known downstream concepts to their typed violation codes; it never grants admission.

Extending the schema or a vocabulary is a semantic-version change because it can change
which presentations validate.

## Consequences
- Unlisted synonyms of downstream-owned concepts can no longer enter canonical output.
- Content that needs new descriptors, cue tags, or phase labels requires an explicit,
  versioned vocabulary extension rather than silent admission.
- Production adapters must reproduce these vocabularies or establish an explicitly
  versioned mapping through differential tests; this decision does not prescribe
  Production content taxonomies.

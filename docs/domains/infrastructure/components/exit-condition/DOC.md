# Exit Condition (component)

Internal building block of the infrastructure domain.

**Source:** `src/beadloom/infrastructure/exit_condition.py`

---

## Overview

One definition of what retires a declared exclusion. Three surfaces require an
`until:` and must promise the same thing by it: `forbid_import.exempt[].until`
in `rules.yml`, the same-layer `exempt[].until` on `architecture-layers`, and
`guards.<name>.exclusions[].until` in `flow.yml`. The first two are read by the
`graph` domain, the third by `onboarding`.

An exit condition has two honest forms and only one of them is checkable: a
**date** (`2026-09-01`, optionally followed by the prose explaining it) and an
**event** (`the repository read seam lands`). The date must lead the string —
`some time after 2026-01-01` is an event, not a deadline.

The definition lives here rather than in `graph`, where it was first written,
because a vocabulary two peer domains share belongs below both of them:
`onboarding` was importing `beadloom.graph.rules` to read it, which was two of
the sixteen same-layer crossings BDL-070 B2 (`beadloom-xmfs`) triaged.
`scan-paths` and `doc-roots` sit here for the same reason. The public path
`beadloom.graph.rules.exit_condition_deadline` is unchanged: `graph/rules/`
re-exports it.

The deadline names the **last day the exclusion covers**, so an entry whose
`until` is today is still live. Reading it one day early would make every entry
expire before its own author's deadline.

## Public surface

- `exit_condition_deadline(until)` — the date an exit condition names, or
  `None` when it names an event.
- `deadline_passed(until, *, today=None)` — whether that day is behind us.
  `False` for an event, always: nothing in a date can observe whether the event
  happened.

## Collaborators

- `graph/rules/exemptions.py` — expiry of a `forbid_import` exemption.
- `graph/rules/layer_exemptions.py` — expiry of a same-layer exemption.
- `onboarding/config_sync.py` and `onboarding/flow_suppression.py` — the
  `until:` on a `flow.yml` guard exclusion.

> Component doc (BDL-070 B2). Public surface verified against
> `exit_condition.py`.

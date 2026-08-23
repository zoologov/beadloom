# Flow Suppression

A declared stand-down of a shipped core rule — named, reasoned, dated, reported.

**Source:** `src/beadloom/onboarding/flow_suppression.py`

---

## Specification

### Purpose

Overlays are append-only, so nothing in the project layer can delete core text.
That is deliberate: silent override is a way to switch the gate off without
saying so, and a rule that vanished from a composed file leaves no trace that
anyone decided it should.

A project that genuinely must stand down a core rule declares it in
`.beadloom/flow.yml`:

```yaml
overlays:
  suppress:
    - rule: "Anti-patterns / Shell"
      reason: "the team runs on Windows; the -f idiom does not apply"
      until: "a windows stack overlay ships"
```

### Rules

- `rule`, `reason` and `until` are **all mandatory**. The same bar
  `guards.<name>.exclusions` holds (BDL-061 S1), for the same reason: an
  unnamed, undated suppression is permanent by accident.
- `until` may name a date or an event. Which it is, is decided by
  `beadloom.graph.rules.exit_condition_deadline` — the one function both
  surfaces use, because restating it would let the two drift apart.
- An unknown key under `overlays` or under a suppress entry is a config error;
  project *additions* are files under `.beadloom/flow/`, never keys here.

### Reporting

Every suppression is reported twice:

1. appended to each composed artifact as a "Project rule suppressions" notice,
   so the reader about to follow the core rule is told it was stood down, by
   whom and until when;
2. surfaced through `config-check` — as the `flow.yml` validation path for a
   malformed entry, and as a **liveness finding** for one that has stopped
   earning its place.

### Liveness: expired, and dead

`config-check` reports two conditions, both at `warn`. They are the findings
`graph.rules.exemptions` already makes for a `forbid_import` exemption, one layer
up (BDL-061 `.48`/`.49`):

| condition | reported as |
|-----------|-------------|
| `until` names a day and that day has passed | `the suppression of '<rule>' expired on <date> and is still standing the rule down` |
| `rule` names no heading in anything the project composes | `the suppression of '<rule>' matches no rule in the composed flow — it stands nothing down` |

`rule` is read as a heading **path**: every `/`-separated segment must be named
by some heading in the composed corpus — `CLAUDE.md`, the four slash commands and
the four role protocols. `Anti-patterns / Shell` is matched by
`### Anti-patterns (shell)`; `Section 42 / Tap dance` is matched by nothing. The
corpus is the whole composition rather than one artifact, because a core rule may
live in any of them and a "suppresses nothing" reported from a partial corpus is
the false positive that teaches people to ignore the finding.

### Expiry is a finding, never a byte

`describe()` says which rule, why, and what retires it. It says **nothing about
today**.

It used to append `— EXPIRED`, and that made the composition a function of the
clock — the property `composer` asserts in its own docstring and the entire
licence for `config-check` to compare against a composition rather than against
stored bytes. Measured (review `.11`): a scaffolded project with one dated
suppression went from 0 findings / exit 0 to **9 errors / exit 1** three days
later with nothing on disk touched — `CLAUDE.md`, four agents, four commands —
under a reason that named three causes which had not occurred. A gate that turns
red while everyone is asleep, for a reason that names the wrong cause, gets
worked around rather than debugged.

So expiry moved to check time (`expired_suppressions`), which is also what
CONTEXT promised in the first place: a suppression carries a named reason, an
exit condition, **and is itself reported**.

`GuardExclusion.describe()` keeps its `— EXPIRED` verdict on purpose. That string
is a runtime `skip` reason, read by the person whose edit was just let through;
it is not a byte anything is later diffed against.

## API

Module `src/beadloom/onboarding/flow_suppression.py`:
- `FlowSuppression(rule, reason, until)` with `.expired(today=None)` /
  `.describe()`
- `build_suppression(entry)` / `build_suppressions(value)`
- `render_suppression_notice(suppressions)` → `str` (empty when none, so a
  project that suppresses nothing gets byte-identical output)
- `composed_headings(texts)` / `suppresses_nothing(suppression, headings)` —
  the dead-declaration check
- `expired_suppressions(suppressions, *, today=None)`

## Testing

Tests: `tests/test_flow_composition.py::TestSuppressionIsDeclaredAndReported`.

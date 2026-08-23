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
   so the reader about to follow the core rule is told it was stood down;
2. surfaced through `config-check`, via the `flow.yml` validation path.

A suppression whose date has passed renders as `— EXPIRED` at the point it
suppresses something, not only in a separate liveness report.

## API

Module `src/beadloom/onboarding/flow_suppression.py`:
- `FlowSuppression(rule, reason, until)` with `.expired()` / `.describe()`
- `build_suppression(entry)` / `build_suppressions(value)`
- `render_suppression_notice(suppressions)` → `str` (empty when none, so a
  project that suppresses nothing gets byte-identical output)

## Testing

Tests: `tests/test_flow_composition.py::TestSuppressionIsDeclaredAndReported`.

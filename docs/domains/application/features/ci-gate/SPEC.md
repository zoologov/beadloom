# CI Gate

The unified `beadloom ci` gate for the application domain.

**Source:** `src/beadloom/application/gate.py`

---

## Specification

### Purpose

Compose Beadloom's individual checkers into ONE `GateResult` with a single `ok`
verdict, so CI is the only true enforcement point — identical for any author,
whether Claude Code, Cursor, or a human. `run_ci_gate` runs every step in order
and never short-circuits, so a later failure is never hidden by an earlier one.

### Steps

`run_ci_gate(project_root, *, fail_on, hub_exports, no_reindex)` runs, in order:

1. **reindex** (unless `--no-reindex`) — rebuild the index.
2. **lint** — `lint --strict`, architecture boundaries.
3. **sync-check** — symbol-pair doc freshness; fails on stale pairs.
4. **docs-audit** — numeric/version fact freshness; fails on `stale>0`.
5. **config-check** — agent-config drift (AgentConfigAsCode).
6. **doctor** — graph integrity.
7. **federate** — `federate --fail-on` when hub exports are supplied.

The **docs-audit** step (BDL-057 Layer 1) reuses
`beadloom.doc_sync.audit.run_audit` — the same path `beadloom docs audit` calls —
and fails the step when any documentation mention disagrees with a ground-truth
fact (version, node/edge counts, language/framework counts, MCP-tool count,
CLI-command count). The audit's false-positive masking and per-fact tolerances
keep this honest; targeted exceptions live in `.beadloom/config.yml`
(`docs_audit.tolerances` / `docs_audit.ignore`).

Each step reports a `GateStep` with `PASS` / `FAIL` / `SKIP` — never an
ambiguous green — and its findings in the shared finding shape. `GateResult.ok`
is True only when every step passed.

## Invariants

- Every step runs; the gate never short-circuits on the first failure.
- A skipped step counts as passed (it cannot block the build).
- `docs-audit` blocks on `stale>0`; `sync-check` `surface_drift` warnings are
  advisory and never fail the gate.
- `fail_on=None` selects the safe default federate set
  (`breaking,drift,orphaned_consumer,undeclared_producer`); the
  no-false-gate verdicts are never included.

## API

Module `src/beadloom/application/gate.py`:

- `GateStep` — one step: `name`, `passed`, `skipped`, `findings`, `summary`,
  and the `status` property (`PASS` / `FAIL` / `SKIP`).
- `GateResult` — aggregate: `steps`, plus the `ok` and `findings` properties.
- `run_ci_gate(project_root, *, fail_on, hub_exports, no_reindex) -> GateResult`
  — run every gate step and aggregate the result.

## Testing

Tests: `tests/test_gate.py`, `tests/test_ci_gate.py`,
`tests/test_f3_gate_coverage.py`, `tests/test_f3_gate_dogfood.py`

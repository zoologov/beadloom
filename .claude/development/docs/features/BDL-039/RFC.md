# RFC: BDL-039 — F3: Tool-Agnostic Enforcement Everywhere

> **Status:** Approved
> **Created:** 2026-06-01

---

## Summary

Turn Beadloom's detection signals into **enforcement**: (1) `beadloom federate --fail-on <verdicts>` so a hub CI *blocks* a cross-service `BREAKING`/`DRIFT`; (2) **agent-actionable** violation output (remediation, not just detection) in JSON + GitHub-annotation form; (3) **AgentConfigAsCode** — a regenerate-and-diff freshness check that fails when `AGENTS.md` / `CLAUDE.md` auto-sections / generated IDE adapters drift from the graph; (4) a single `beadloom ci` gate composing reindex → lint → sync-check → config-check → optional landscape gate, shipped as a reusable **composite GitHub Action** + a GitLab template; (5) dogfood on Beadloom's own CI.

Purely additive: no graph-format / schema-version changes. Existing commands keep their behavior; F3 adds flags, one new checker, one new orchestrator command, and CI packaging. The existing per-repo gate (`beadloom-aac-lint.yml`) is subsumed by — not broken by — `beadloom ci`.

## Design principles (from STRATEGY-3)

1. **CI is the only true enforcement point** (principle 7) — local rules files are hints; the gate that fails the build is what holds the line, identically for every tool and human.
2. **Generated, verified-fresh adapters** (principle 7 / #93) — agent-config is derived from the graph and *checked*, never hand-maintained.
3. **Honest gates, no false failures** — `external` / `expected` / `dead` / `unmapped` never fail a gate; only real breaks do. A gate that cries wolf gets disabled.
4. **Agent-actionable** — a violation an agent can fix unaided (what + where + how), in its native channel.
5. **No new infra to depend on** — F3 ships the gate + a documented pull-based hub pattern; it does not build a registry/SaaS.

---

## Architecture

### Module layout

| Module | Change |
|--------|--------|
| `graph/federation.py` | `gate_failures(fed, fail_on: set[str]) -> list[GateFailure]` — scan edge `EdgeVerdict`s + contract `ContractVerdict`s against the fail-set; pure, testable. |
| `services/cli.py` | `federate --fail-on <csv>` (exit 1 on failures, still writes artifacts first); **new `ci` command** (the unified gate). |
| `graph/rule_engine.py` | `Violation.remediation: str \| None` (additive field) + a per-rule-type remediation deriver. |
| `application/gate.py` (**new**) | The `ci` orchestrator: compose reindex → lint → sync-check → config-check → (optional) federate gate into one `GateResult` with a single exit code; formatters (`rich` / `json` / `github`). |
| `onboarding/config_sync.py` (**new**) | **AgentConfigAsCode**: re-derive the canonical agent-config (AGENTS.md / CLAUDE.md auto-sections / adapters) from the graph in-memory and diff vs disk → `list[ConfigDrift]`. Reuses the EXISTING `setup-rules --refresh` generation logic (no second generator). |
| `.github/actions/beadloom-gate/action.yml` (**new**) | Composite Action running `beadloom ci`; referenceable by satellites. |
| `docs/guides/ci-setup.md` | Updated: landscape gate, the Action, `--fail-on`, AgentConfigAsCode, the pull-based hub pattern + GitLab template. |

No new SQLite tables, no schema bump. AgentConfigAsCode is a *generated-artifact* freshness check (regenerate-and-compare), distinct from the hash-based doc↔code `sync_state` mechanism — so it does not overload `sync_state`.

### 1. Federated landscape gate (G1)

`beadloom federate <exports...> --fail-on breaking,drift,orphaned_consumer,undeclared_producer`:

- After aggregation, `gate_failures(fed, fail_on)` collects every edge whose `EdgeVerdict` and every contract whose `ContractVerdict` is in `fail_on`. Verdict names are matched case-insensitively against the existing enum values.
- The hub **still writes** `federated.json` + `federated.txt` and prints the report, THEN exits `1` if there are failures (so the artifact is always available for inspection/CI upload). Exit `0` when clean.
- **Safe default** (when `--fail-on` is given the bare flag or a `default` token): `breaking,drift,orphaned_consumer,undeclared_producer`. **Never** in any fail-set: `external`, `expected`, `dead`, `unmapped`, `confirmed`, `ok`, `cleanup_candidate` (principle 3 — no false gates; `cleanup_candidate` is a warning, not a block).
- Output lists each failing verdict with its contract/edge identity + (for BREAKING) the missing names — agent-actionable (§2).

### 2. Agent-actionable violation output (G2)

- Add optional `Violation.remediation` (additive; existing rows/tests default `None`). A small `_remediation_for(rule_type, violation)` derives a templated hint per rule kind: deny/forbid → "remove the import/edge `X→Y`, or route through `<allowed>`"; cycle → "break the cycle at edge `X→Y`"; layer → "`X` (layer L) must not depend on `Y` (layer L+1); invert or extract a shared abstraction"; cardinality → "split `X` (N symbols > limit)".
- Contract findings (from `gate_failures`) carry an analogous hint: BREAKING → "consumer references `<name>` absent from producer `<schema>` SDL; align the client or restore the field"; ORPHANED_CONSUMER → "no producer for `<contract>`; add a producer or drop the consumer".
- **Formats:** the gate emits `--format json` (a stable findings array: `{kind, rule, severity, locations[], why, remediation}`) and `--format github` (GitHub Actions workflow commands: `::error file=…,line=…::<message>` so violations appear as inline PR annotations). `rich` stays the human default.

### 3. AgentConfigAsCode (G3)

- `onboarding/config_sync.py`: `check_config_drift(project_root, conn) -> list[ConfigDrift]`. It re-runs the existing canonical generator (the same code `setup-rules --refresh` uses to produce `.beadloom/AGENTS.md` + the CLAUDE.md auto-managed section between `<!-- beadloom:auto-start -->` / `auto-end`, + IDE adapters) into memory, and diffs against the on-disk content. Any mismatch → a `ConfigDrift(file, reason)` (e.g. "AGENTS.md domain list stale: graph has `contracts`, file lists old set").
- Scope of what's checked = only the **auto-managed** regions (never user-authored prose), so editing the human parts of CLAUDE.md never trips it (avoids the #73 false-positive class).
- Surfaced via `beadloom ci` (fails the gate) and a standalone `beadloom config-check [--fix]` (where `--fix` = regenerate, i.e. `setup-rules --refresh`). This makes the generated adapters **verified-fresh**.

### 4. The unified gate — `beadloom ci` (G2 + G4)

```
beadloom ci [--hub <export>...] [--fail-on <csv>] [--format rich|json|github] [--no-reindex]
```

`application/gate.py` composes, in order, short-circuiting to a single exit code:
1. `reindex` (unless `--no-reindex`) — so the gate runs against current code.
2. `lint --strict` (boundary rules at error).
3. `sync-check` (doc↔code freshness).
4. `config-check` (AgentConfigAsCode, §3).
5. If `--hub` given: `federate <exports> --fail-on …` (landscape gate, §1).

Returns a `GateResult` aggregating all findings; exit `1` if any step failed, `0` if all clean. `--format` applies uniformly. This is the single convergence point principle 7 demands — identical for Cursor / Claude Code / human authors. `beadloom-aac-lint.yml`'s reindex+lint+sync steps collapse into one `beadloom ci` call.

### 5. Reusable CI integration + dogfood (G4 / G5)

- **Composite GitHub Action** `.github/actions/beadloom-gate/action.yml`: inputs (`fail-on`, `hub-exports`, `format: github`), runs `beadloom ci`. Satellites reference `zoologov/beadloom/.github/actions/beadloom-gate@<ref>`.
- **GitLab template** documented in `ci-setup.md` (script block calling `beadloom ci`), plus the **pull-based hub pattern** (satellites publish commit-SHA-tagged `beadloom export` artifacts; a hub CI job pulls ≥2 and runs `federate --fail-on`) — documented, not built.
- **Dogfood:** Beadloom's own CI (`beadloom-aac-lint.yml` → rename/extend to `beadloom-gate.yml`) calls the Action. Demonstrate the gate blocking: (a) a deliberately-introduced boundary violation, (b) a cross-service `BREAKING` via committed anonymized hub fixtures (NOT the gitignored scratch — small committed `tests/fixtures/` exports), (c) a drifted `AGENTS.md`. Each fails with agent-actionable output. Friction → `BDL-UX-Issues.md`.

---

## Schema & versioning

No `EXPORT` / `FEDERATION` / DB schema-version changes. `Violation.remediation` is an additive in-memory field. The lint/gate `json` output is additive (new optional keys). Backward-compatible by construction.

## Determinism & honesty

- Gate output is deterministic (sorted findings). `--format github` annotations are stable.
- **No false gates** (principle 3): the fail-set excludes `external`/`expected`/`dead`/`unmapped`/`cleanup_candidate`; AgentConfigAsCode checks only auto-managed regions.
- `beadloom ci` reports exactly which steps ran and their result — never a green that skipped a step silently (honest gate, the Phase-0 lesson).

## Build order (waves — detail in PLAN)

1. **Landscape gate** — `gate_failures` + `federate --fail-on` (foundation; F2 verdicts gain teeth).
2. **Agent-actionable output** — `Violation.remediation` + remediation derivers + json/github formats.
3. **AgentConfigAsCode** — `onboarding/config_sync.py` regenerate-and-diff + `config-check`.
4. **`beadloom ci`** — `application/gate.py` orchestrator composing 1–3 + lint + sync.
5. **Reusable CI** — composite Action + GitLab template + wire Beadloom's own CI.
6. **Dogfood** — gate blocks violation / BREAKING / config-drift with agent-actionable output.

Then test → review → tech-writer (ci-setup guide, SPEC, CHANGELOG, STRATEGY F3→delivered).

## Risks & mitigations

| Risk | Mitigation |
|------|------------|
| False gates erode trust (a noisy gate gets disabled) | Hard-exclude `external`/`expected`/`dead`/`unmapped`/`cleanup_candidate`; AgentConfigAsCode checks only auto-managed regions; explicit tests for "clean landscape → exit 0". |
| AgentConfigAsCode re-implements the generator (drift between gen + check) | `config_sync` calls the SAME generation code as `setup-rules --refresh` (regenerate-and-diff), never a parallel reimplementation. |
| `beadloom ci` reindex slow in CI | `--no-reindex` for callers that reindex separately; cache `.beadloom` in CI; reindex is incremental. |
| Composite Action coupling to repo layout | Keep the Action thin (just invokes `beadloom ci`); all logic in the CLI, testable without CI. |
| Hub gate needs committed fixtures (scratch is gitignored) | Small anonymized `tests/fixtures/` export artifacts for the dogfood + tests; the real landscape stays in gitignored scratch. |
| Scope creep (SARIF, registry infra, F4 dashboard) | Hard non-goals in PRD; JSON+annotations only; registry pattern documented not built. |

## Out of scope (→ F4 / follow-ups)

SARIF/Security-tab; production artifact-registry plumbing; AI-tech-writer-in-CI + VitePress + dashboard + visual landscape map; new adapter kinds; REST/gRPC contracts; SaaS hub.

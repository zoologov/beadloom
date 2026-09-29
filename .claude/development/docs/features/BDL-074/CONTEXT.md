# CONTEXT: BDL-074 — Tests that belong to the graph

> **Status:** Done
> **Created:** 2026-09-28
> **Last updated:** 2026-09-28

---

## Goal

Every test in this repository is isolated from its live state, lives where the code it tests lives,
and is bound to that code's graph node — so `beadloom ctx` shows real tests, lint judges them the way
it judges code and documents, and mutation runs per change through the binding in minutes. Proven on
the rule engine in full; every other file with a clear node relocated.

## Key Constraints

- **No test is lost in a move.** Every relocation commit shows an identical collected-test set (ids
  modulo path) and an identical result before and after.
- **No self-check leaves without its replacement named.** A check removed as a Gate duplicate names the
  required Gate leg that checks the same thing on the real repository, and the checker keeps a product
  test on a synthetic fixture.
- **The product's 52 `Path.cwd()` defaults stay.** Tests stop relying on them; the CLI keeps them.
- **Tests do not become code.** They are indexed in their own tables, never added to `scan_paths`.
- **`extra["tests"]` keeps its four-key shape** (`framework`, `test_files`, `test_count`,
  `coverage_estimate`) so its six consumers keep working.
- **mutmut is used as it is.** No patch; the per-run selection is generated configuration.
- **Every new rule states its population**, and every exemption carries a reason and an exit condition.

## Code Standards

### Language and Environment

- **Language:** Python 3.10+ (type hints, `str | None` syntax)
- **Package manager:** uv
- **Architecture:** DDD packages — `ai_agents/`, `application/`, `context_oracle/`, `doc_sync/`,
  `graph/`, `infrastructure/`, `onboarding/`, `services/`, `tui/`

### Methodologies

| Methodology | Application |
|---|---|
| TDD | New product behaviour (the index, the binding, the rules, the per-change job) is test-first; a relocation is proven by the collected-set invariant instead, because it adds no behaviour. |
| Clean Code | SRP, DRY, KISS; test helpers in `tests/support/`, never imported across test modules |
| Architecture | `services -> application -> domains -> infrastructure`; test layout mirrors it: `tests/<kind>/<path under src/beadloom/>` |

### Testing

- **Framework:** pytest + pytest-cov; pytest-bdd for acceptance
- **Coverage:** minimum 80%
- **Kinds:** `unit`, `integration`, `acceptance`, `self_check` — by folder; the `self_check` marker
  runs against a snapshot, never the live repository.

### Code Quality

- **Linter:** ruff (lint + format) — `uv run ruff check src/ tests/`
- **Typing:** mypy --strict — `uv run mypy src/`
- **Gate:** `beadloom ci` rc 0

### Restrictions

- No `Any` or `# type: ignore` without a stated reason
- No `print()` / `breakpoint()` — use logging
- No bare `except:` — name the exception
- No `os.path` — pathlib only; no f-strings in SQL — parameters `?`; no `yaml.load` — `safe_load`
- **Never pipe a command whose exit code is the answer** — redirect to a file and read `$?`.
- **Subagents run long suites in the foreground.**
- **Commit only your own files, by explicit path**, with `git commit --only`; never let an
  already-staged `.beads/issues.jsonl` ride along.
- **A mutant run by hand needs `PYTHONPATH=<repo>/mutants/src`**, or it is never activated.

## Architectural Decisions

| Date | Decision | Reason |
|---|---|---|
| 2026-09-27 | One epic: isolation, binding, rules, per-change mutation, restructuring | Owner decision; the whole-scope nightly was retired the same day. |
| 2026-09-27 | A measured map of the suite before the PRD | Owner decision; `map/test-map.json` and three companion files. |
| 2026-09-28 | Relocate the 227 clear-node files mechanically; the rule engine in full as the pilot | Owner decision; the 201 mixed files need splitting and go to follow-up slices, except the rule engine's. |
| 2026-09-28 | Acceptance tests follow the same rule | Owner decision; layout by feature node mirroring `docs/domains/…`, a tag-folder-execution agreement rule, content rewritten on the pilot. |
| 2026-09-28 | Self-checks triaged, Gate duplicates removed | Owner decision; with the replacing leg named each time. |
| 2026-09-28 | Kind first, then the mirrored source path | RFC; common Python layout, CI selects a kind by path, the binding follows from the mirror. |
| 2026-09-28 | The binding is derived from the mirror, with an optional `tests:` override in node YAML | RFC; one fact, stated once, resolved by the ownership rule the graph already uses. |
| 2026-09-28 | Kept nodes: test-mapping, context-builder, rule-engine, graph, reindex, debt-report, mutation-scope, cli-commands, onboarding | Owner ruling on the RFC's axes. |
| 2026-09-28 | Acceptance: one folder per node, `tests/acceptance/<domain>/<node>/*.feature`, mirroring `docs/domains/…` | Owner ruling after B3 stopped at package level (`tests/acceptance/<package>/`) because seven nodes have several feature files. A folder per node needs no merge and lets the tag-folder agreement rule check to the node. Bead `beadloom-2mj3.4`; C3 and E1 wait for it. |

## Related Files

- `map/` — the suite map this epic rests on (per-file kind, nodes, live contact, time)
- `src/beadloom/context_oracle/test_mapper.py` — the heuristic being retired
- `src/beadloom/application/reindex/enrichment.py:27-79`, `full.py:183` — where the guess is stored
- `src/beadloom/infrastructure/repository.py:335-425` — the ownership rule the binding reuses
- `src/beadloom/graph/rules/loader.py:854-907`, `types.py:486-499`, `__init__.py:214-273`, `liveness.py:444-515`
- `tests/conftest.py:89-106` (`live_repo_reindexed`), `tests/tracked_write_guard` — isolation's starting points
- `pyproject.toml:327-484` — the mutation pool the relocation regenerates

## What this work item knows it has not established

- How many tests the chdir guard breaks — estimated 40-70 files statically, not measured.
- Whether per-change mutation fits 10 minutes when a changed function has many survivors.
- How many of the 547 self-checks are Gate duplicates — the triage measures it.

## Current Phase

Done (2026-09-29). Three PRs merged: #83 (phase A, `4890f28c`), #84 (phase B, `7cbc1874`), #86 (phases C–E
and every review fix, `45a3c2fc`). The follow-ups this work filed are in ACTIVE.md's Outcome.

# CONTEXT: BDL-073 — The mutation duty becomes executable

> **Status:** Approved
> **Created:** 2026-09-25
> **Last updated:** 2026-09-25 (correction)

---

## Goal

A dispatched `Mutation` run completes and prints a score for both scoring steps, over a declared
scope whose cost fits the job's budget — reached by ordering each mutant's covering tests by the
durations mutmut already measured, by taking `load_rules` from 333 mutants to at most 160, and by
closing the five gaps its surviving mutants name.

## Key Constraints

- **The floors do not move.** 0.94 (rules slice) and 0.88 (declared scope) are re-derived only from
  the first honest aggregate, and a breach is reported as a finding.
- **The runner's killer is not this work item's to settle.** `beadloom-5isv` stays open; eight runs
  now show seven deaths at queue positions 4146-4226 and one at 3281 after 102 min. This work item
  shrinks the job; it does not claim the job then survives.
- **A patch that stops applying must say so.** The ordered entry point asserts the shape of the
  expression it replaces and refuses to run otherwise.
- **Nothing is removed from the mutation scope to make it fit.** `only_mutate` and
  `mutation.targets` keep every declared target.
- **The twelve authoring keys stay twelve, and stay one list.** `AUTHORING_KEYS` becomes the table's
  keys; the SPEC's `**Twelve** rule types exist` and the three tests that pin the key set keep their
  meaning.
- **Pushing a workflow change needs a token with `workflow` scope.** Over HTTPS the current `gh`
  token is refused for `.github/workflows/*`; SSH pushes have failed intermittently. The owner's
  `gh auth refresh -s workflow` is a precondition for the pull request and the verify bead.

## Code Standards

### Language and Environment

- **Language:** Python 3.10+ (type hints, `str | None` syntax)
- **Package manager:** uv
- **Architecture:** DDD packages — `ai_agents/`, `application/`, `context_oracle/`, `doc_sync/`,
  `graph/`, `infrastructure/`, `onboarding/`, `services/`, `tui/`

### Methodologies

| Methodology | Application |
|---|---|
| TDD | The gap tests are written first and seen red against the mutant each one answers; the table refactor then lands against them green. |
| Clean Code | SRP, DRY, KISS — one table for the authoring keys, not two twelve-key maps |
| Architecture | `services -> application -> domains -> infrastructure`; unchanged by this work |

### Testing

- **Framework:** pytest + pytest-cov
- **Coverage:** minimum 80%
- **A mutant run by hand needs `PYTHONPATH` pointing at `mutants/src`.** Without it pytest imports
  the editable install and `MUTANT_UNDER_TEST` acts on nothing — measured 2026-09-19 as a false
  survival (`206 passed` without, a kill in 7.8 s with). Every "seen red against its mutant" claim
  names the invocation it used.

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
- **Subagents run long suites in the foreground.** A subagent that backgrounds its own run and ends
  its turn is never woken.
- **Commit only your own files, by explicit path** — never `git add -A`, and never let an
  already-staged `.beads/issues.jsonl` ride along in a commit that is about something else.
- **Sum-of-RSS is not a memory measurement** after `fork`: children share the parent's pages. Use
  `/usr/bin/time -l` on the interpreter itself (not through `uv run`, which measures the wrapper),
  or PSS on Linux.

## Architectural Decisions

| Date | Decision | Reason |
|---|---|---|
| 2026-09-20 | Full scope: tooling, tests and product | Owner decision after the fan-out analysis on `beadloom-5isv`. |
| 2026-09-20 | Kept nodes: `rule-engine`, `reindex`, `graph`, `tui`, `onboarding` | Owner ruling on the RFC's axes; `onboarding` kept although `beadloom impact` cannot show it, for its second twelve-key map. |
| 2026-09-20 | The double parse is removed by a memo keyed on `(path, st_mtime_ns, st_size)` | Owner decision. A path-only key breaks a named test and blinds the TUI. **Superseded 2026-09-25 by the row below.** |
| 2026-09-20 | Ordering is applied by a thin repo-local entry point, not by patching the installed package or vendoring mutmut | RFC front 1: visible, survives `uv sync`, and can refuse when the patched line moves. |
| 2026-09-20 | `--max-children` 4 → 2 | A measured false kill through the shared live index at 4-way concurrency; nothing pins the value. |
| 2026-09-25 | The gap tests land before the table refactor | They pin today's messages and codec, so the refactor is proven against them rather than alongside them. |
| 2026-09-25 | Front 1 (ordering) withdrawn; B2 restated as `--max-children 2` | mutmut 3.7.0 already orders covering tests cheapest-first (`__main__.py:1478-1479`); the premise came from misreading `:1443`. |
| 2026-09-25 | A real dispatched run goes first, after wave 1; B3 and B4 proceed while it runs | Owner decision: the first aggregate, or the first honest death at two children, is worth more than finishing the plan blind. |
| 2026-09-25 | The memo compares the file's text rather than trusting `(st_mtime_ns, st_size)`; it is forgotten before every test | A same-size edit inside one timestamp tick was served the old rules under the stat key, red in two tests; a hit costs 50.5 us against a 15.94 ms parse, measured. mutmut forks each mutant's run from a parent that ran the clean suite, so an inherited memo would answer without executing the mutant. |
| 2026-09-25 | **Owner accepted** the text-comparing memo in place of `(st_mtime_ns, st_size)` | Asked explicitly because it departs from the owner's 2026-09-20 decision; accepted on the measurement (stale rules served after a same-size edit inside one tick; 50 µs per compare against 15.94 ms per parse). B6 need not rule on it. |

## Related Files

- `src/beadloom/graph/rules/loader.py` — `load_rules`, `AUTHORING_KEYS` (line 347), the dispatch (~954-1067)
- `src/beadloom/onboarding/scanner/rules_gen.py:82` — `_detect_rule_type`, the second twelve-key map
- `src/beadloom/application/reindex/rules_loader.py:225`, `src/beadloom/graph/linter.py:199` — the two sides of the double parse
- `src/beadloom/tui/data_providers.py:158-177` — the long-lived caller the memo must not blind
- `.github/workflows/mutation.yml:254`, `:265`; `tests/test_mutation_ci_job.py:103`
- `docs/domains/graph/features/rule-engine/SPEC.md` — pinned against `AUTHORING_KEYS`

## What this work item knows it has not established

- What kills the runner. Seven of eight deaths sit at the `load_rules` tail; one does not.
- Whether the slice fits the budget on the runner rather than on paper. The projection (≈14.7 h
  after ordering, less after the table) is mutmut's worst-case metric, not a timed run.
- How many of the nightly's kills are false. At `--max-children 4` at least one was.

## Current Phase

Development — PRD, RFC, CONTEXT and PLAN approved (2026-09-25); beads created from the approved PLAN.

# CONTEXT: BDL-075 — Release 7.0.0 with the documentation current

> **Status:** Done
> **Created:** 2026-09-29
> **Last updated:** 2026-09-29

---

## Goal

Publish 7.0.0 from `main` with BDL-072, BDL-073 and BDL-074, verified on the wheel downloaded from
PyPI. Ship it with a README pair that tells the truth about the version it describes, a ROADMAP
ranked on what is open, and an issue log whose Open section holds only what is open.

## Key Constraints

- **No product code change** beyond the version literal and the PLAN and BRIEF templates
  (`beadloom-10er`, `beadloom-3nwz`, both added by the owner on 2026-09-29), and the `--sample-of`
  help text (owner, 2026-09-29: a new flag must not ship with a false description). A defect found
  on the way is filed, not fixed.
- **A green publish run is not evidence.** The build reads its version from `__init__.py`, nothing
  checks it against the tag, and the upload uses `skip-existing: true`. The evidence is
  `beadloom --version` on the downloaded wheel.
- **History is never rewritten.** A line that states what 6.0.0 or earlier did keeps saying it. If
  the docs audit misreads such a line, it gets a `docs_audit.ignore` triple with its reason.
- **`.claude/CLAUDE.md` is regenerated** with `beadloom setup-agentic-flow`. It is never edited by
  hand.
- **README: Russian first, English follows.** Every number and command in it is measured against
  the 7.0.0 build. `readme-pair` compares shape only, and no check reads the Russian file's numbers.
- **Russian text:** grammatically correct, easy to read, clear and concise. No abbreviations, no
  terms the reader has to translate, no AI-writing patterns.
- **Publishing is owner-gated.** The merge, the tag and the GitHub release each wait for the owner's
  agreement.
- **No commit and no push while a gate owner's own suite runs.** Commit only your own files, by
  explicit path, under `bd merge-slot acquire/release --holder <bead-id>`.
- **Subagents run long suites in the foreground.**
- **Never pipe a command whose exit code is the answer.**

## Code Standards

### Language and Environment

- **Language:** Python 3.10+ (type hints, `str | None` syntax)
- **Package manager:** uv
- **Architecture:** DDD packages — `ai_agents/`, `application/`, `context_oracle/`, `doc_sync/`,
  `graph/`, `infrastructure/`, `onboarding/`, `services/`, `tui/`

### Methodologies

| Methodology | Application |
|---|---|
| TDD | Not exercised: no code changes. The release harness is a test artifact, and it must be shown to distinguish 6.0.0 from 7.0.0 before it is trusted. |
| Clean Code | SRP, DRY, KISS |
| Architecture | `services -> application -> domains -> infrastructure`; unchanged |

### Testing

- **Framework:** pytest + pytest-cov
- **Fixtures that are not this repository.** Release behaviour is shown on a project built for the
  purpose, because this repository hides the shapes an adopter meets.

### Code Quality

- **Linter:** ruff: `uv run ruff check src/ tests/`
- **Typing:** mypy --strict: `uv run mypy src/`
- **Gate:** `beadloom ci` exits 0 on the release commit, and the suite passes on it.

### Restrictions

- No `Any` or `# type: ignore` without a stated reason.
- No `print()` or `breakpoint()`; use logging.
- No bare `except:`; name the exception.
- Use pathlib, not `os.path`. Pass SQL parameters as `?`, never in f-strings. Use `safe_load`, not
  `yaml.load`.

## Architectural Decisions

| Date | Decision | Reason |
|---|---|---|
| 2026-09-29 | Release 7.0.0, major | Owner, approving the PRD. Two changes alter a verdict and a JSON value set on an unedited project: the debt report's untested count, and the values in `extra.tests`. That meets the bar 4.0.0 recorded and BDL-071 applied. |
| 2026-09-29 | The README describes what 7.0.0 publishes, and ships with it | Owner. A README ahead of PyPI promises what `pip install` does not deliver. |
| 2026-09-29 | ROADMAP ranking: `jwfc` → adopter sweep → `tsqz` → release → three lessons → `r9t5` → class gaps → BDL-066 → `uxqc` → mutation follow-ups → `cxal` | Owner accepted the audit's proposal. |
| 2026-09-29 | Federation deferred until a need for it appears | Owner: higher priorities first. |
| 2026-09-29 | Issue log: fixed entries move to Closed with evidence, and the structure is repaired; the chronology is historical up to 2026-08-26 | Owner. |
| 2026-09-29 | PLAN's bead table carries tracker ids and no status | `beadloom-10er` (owner, 2026-09-28): status lives in ACTIVE.md only. |
| 2026-09-29 | The `--sample-of` help text is corrected in this release | Owner, after F1 found `mutation --help`, its docstring and `cli.md` calling the value the sample size — it is the population the sample is drawn from. |
| 2026-09-29 | The shipped BRIEF template changes in this release too | Owner, after T1 found the same hand-kept status column in BRIEF: `beadloom-3nwz` joins BDL-075 before R1. |
| 2026-09-29 | The shipped PLAN template changes in this release | Owner, approving CONTEXT and PLAN: `beadloom-10er` joins BDL-075 as bead T1, so 7.0.0 ships the template with no status column. |

## Related Files

Discover them with `beadloom ctx <ref-id>`; never hardcode paths. The version surface is listed in
the RFC's Axes. The audits are in the coordinator's scratchpad: `audit_readme.md`,
`audit_roadmap.md` and `audit_bdlux.md`.

## Current Phase

Done (2026-09-29). 7.0.0 is on PyPI, published from `main` at `e02c347e` (PR #88) and verified on
the downloaded wheel. The close-out is in ACTIVE.md's Outcome.

# CONTEXT: BDL-071 — Release 5.0.0, then 6.0.0: the population report ships before the verdict change

> **Status:** Done
> **Created:** 2026-09-13
> **Last updated:** 2026-09-14

---

## Goal

Publish BDL-069 and BDL-070 Release A as **5.0.0** from `7efa4006`, then BDL-070 Release B as
**6.0.0** from `main`, each verified on the wheel downloaded from PyPI, so that an adopter can see how
far `architecture-layers` reaches in a release before a release that acts on it.

## Key Constraints

- **Order.** 5.0.0 is published and verified before 6.0.0 starts. BDL-070's CONTEXT forbids a
  verdict change reaching an adopter in the release that first makes its number visible.
- **No code change.** Neither release fixes anything; a defect found on the way is filed.
- **A green publish run is not evidence of a publish.** The build takes its version from
  `src/beadloom/__init__.py`, nothing checks it against the tag, and both uploads run with
  `skip-existing: true`. Evidence is `beadloom --version` on the wheel downloaded from PyPI.
- **`release/5.0.0` gets no pull-request CI** — `ci.yml` runs only on pull requests to `main`. Its
  verification is local, plus the publish workflow's own test matrix and gates.
- **History is never rewritten.** A line that states what 4.0.0 was or did keeps saying 4.0.0.
- **No commit and no push while the gate owner's own full suite runs.** Every git hook here
  re-indexes the live index that suite reads (BDL-UX #298).
- **Verification records go to `ROADMAP.md` and the issue log only**, never into a document the docs
  audit scans, or the next bump fails the Gate on a true line.

## Code Standards

### Language and Environment

- **Language:** Python 3.10+ (type hints, `str | None` syntax)
- **Package manager:** uv
- **Architecture:** DDD packages — `ai_agents/`, `application/`, `context_oracle/`, `doc_sync/`,
  `graph/`, `infrastructure/`, `onboarding/`, `services/`, `tui/`

### Methodologies

| Methodology | Application |
|---|---|
| TDD | Not exercised: no code changes. The verification harness is a test artifact and is shown to distinguish the three versions before it is trusted. |
| Clean Code | SRP, DRY, KISS |
| Architecture | `services -> application -> domains -> infrastructure`; unchanged by this work |

### Testing

- **Framework:** pytest + pytest-cov
- **Coverage:** minimum 80%
- **Fixtures that are not this repository.** Release behaviour is shown on a project built for it,
  because this repository hides the shapes an adopter meets.

### Code Quality

- **Linter:** ruff (lint + format) — `uv run ruff check src/ tests/`
- **Typing:** mypy --strict — `uv run mypy src/`
- **Gate:** `beadloom ci` rc 0 on every release commit before it is tagged

### Restrictions

- No `Any` or `# type: ignore` without a stated reason
- No `print()` / `breakpoint()` — use logging
- No bare `except:` — name the exception
- No `os.path` — pathlib only; no f-strings in SQL — parameters `?`; no `yaml.load` — `safe_load`
- **Never pipe a command whose exit code is the answer** — redirect to a file and read `$?`.
- **In a git worktree, run `uv run` from inside it.** The `beadloom` command otherwise resolves to
  the main checkout's code, and a comparison between revisions silently compares one revision with
  itself.
- **Subagents run long suites in the foreground.** A subagent that backgrounds its own run and ends
  its turn is never woken, and its work sits uncommitted.
- **Commit only your own files, by explicit path** — never `git add -A`.

## Architectural Decisions

| Date | Decision | Reason |
|---|---|---|
| 2026-09-13 | Two releases, 5.0.0 then 6.0.0 | Owner. BDL-070's order holds only if the halves are published separately. |
| 2026-09-13 | 5.0.0 for BDL-069 + Release A; 6.0.0 for Release B | Owner, by the bar 4.0.0 recorded: a JSON value-set change (`declared` widened to `bool \| null`) makes A major; B changes verdicts and narrows the population contract. |
| 2026-09-13 | Publish both once every check passes | Owner. Stop and ask on any failure that is not a flake. |
| 2026-09-13 | 5.0.0 from a `release/5.0.0` branch on `7efa4006` | Tagging `7efa4006` directly would build 4.0.0 and be skipped silently; reverting B on `main` rewrites history twice. |
| 2026-09-13 | The three docs-audit history lines get `docs_audit.ignore` triples | Measured: the Gate fails on them after a bump. Rewording would game the instrument; raising them would make three true lines false. |
| 2026-09-13 | `[5.0.0]` on `main` is copied byte-for-byte from the published branch | A change log that says something other than what shipped is the class this project removes. |
| 2026-09-13 | `ROADMAP.md`'s Current version moved to 6.0.0 with the bump in R5, ahead of the R8 the plan named, and was marked verified only in R8 | `tests/test_version_surface.py` pins that line to `__version__`, so a ROADMAP left behind the bump fails the suite on the release commit (R4's correction on `beadloom-7foi`). The word "verified" had to wait for R7's harness on the downloaded 6.0.0 wheel, so R5 wrote the line as not yet verified. Recorded by R8 after R6 found the move unexplained. |

## Related Files

Discover via `beadloom ctx <ref-id>` — never hardcode. The nodes kept in scope are `beadloom`, `cli`
and `docs-audit`; the rest of the surface is owned by no node and named in the RFC's axes.

## What this work item knows it has not established

- **Whether 5.0.0 and 6.0.0 behave as documented on a project that is not this repository.** That
  is what the verification harness exists to show, and nothing has been run yet.
- **Whether a place states a version other than 4.0.0 that should move.** `version-surface` sweeps
  for the current literal only; it says so itself.
- **Whether the publish workflow's full suite hits the #298 torn read.** It has not run on either
  release commit.

## Current Phase

- **Phase:** Planning
- **Current bead:** none — beads are created after PLAN is approved
- **Blockers:** none

# CONTEXT: BDL-081 — Release 9.0.0

> **Status:** Approved
> **Approval:** delegated by the owner on 2026-10-10.
> **Created:** 2026-10-10

---

## Goal

Publish 9.0.0 with a change log that tells an 8.0.0 adopter what moves and what to run, the
documentation read against the release, the harness verifying the new surfaces on the downloaded
wheel, and one product fix (the leftover `other/` page on upgrade).

## State

Branch `features/BDL-081` from `main` at `290507b2` (BDL-080 shipped). The measured diff is in
`axes.md`; the owner's eight rulings are in PRD.md.

## Key Constraints

- Semantic Versioning 2.0.0 against the declared public API (`CONTRIBUTING.md`,
  `docs/guides/public-api.md`); MAJOR, Breaking first and complete by the measurement.
- The harness runs on the downloaded artifact, never the local build, and must fail on 8.0.0.
- Two-level verification; one bead per agent; commits by path under the landing lock; the
  README pair: Russian first; documents in English.
- `.claude/CLAUDE.md` is composed (`setup-agentic-flow`), never edited by hand.

## Code Standards

Python >= 3.10, ruff, mypy --strict, pytest; documents in English; commits
`[BDL-081] <type>: <description>`; one PR; merge on green CI.

## Architectural Decisions

| Date | Decision | Why |
|---|---|---|
| 2026-10-10 | MAJOR; the Breaking section names the five measured classes (site alias; the new import readings; composed-role drift; the fsd auto-detection; configuration 8.0.0 ignored) | Owner's rulings 2, 3, 4, 8 on the PRD |
| 2026-10-10 | The scaffold theme's internal paths are not in the promise; `landscape.data.json` is undeclared; the fsd overlay's vocabulary is Changed | Owner's rulings 1, 5, 7 |
| 2026-10-10 | The leftover `other/<ref>.md` is retired on upgrade before the release | Owner's ruling 6 |
| 2026-10-10 | The role model stays `opus` in the templates | Owner |

## Related Files

`src/beadloom/__init__.py`, `CHANGELOG.md`, `docs/guides/public-api.md`, `docs/getting-started.md`,
`docs/services/cli.md`, `README.md`, `README.ru.md`, `.beadloom/_graph/beadloom.yml`,
`tests/release/verify_the_release.py`, `tests/test_integration_v1.py`,
`tests/self_check/process/test_the_release_harness_reports_what_ran.py`,
`src/beadloom/application/site/scaffold.py`, `.claude/development/ROADMAP.md`.

## Current Phase

- **Phase:** Development
- **Current bead:** see ACTIVE.md
- **Blockers:** none

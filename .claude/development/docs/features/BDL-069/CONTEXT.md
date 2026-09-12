# CONTEXT: BDL-069 — The checks an adopter meets first, and the populations they run over

> **Status:** Approved
> **Created:** 2026-09-10
> **Last updated:** 2026-09-10

---

## Goal

Make the first two commands an outside user runs end green on the ordinary Python layouts, and
make three existing checks name the population they ran over. Four defects, one shape: a check
reporting on a population that is empty, partial, or unnamed.

## Key Constraints

- **The defects are not reproducible here.** Both adopter blockers were found on the published
  4.0.0 wheel against projects that are not this repository, and this repository's own
  arrangement hides them. Every test for them builds a foreign project — one package named
  after the project, and several under `src/` — and the acceptance runs against the built
  artifact rather than the working tree.
- **`beadloom impact` reads Python.** Four of the nine version-stating surfaces are
  `unreadable-target` to it. S3 needs its own reader and cannot be built on `impact`.
- **`.beadloom/_graph/` has seven readers and one declared policy.** Six read the directory
  without going through `graph_files.each_graph_file`. Whether that is a defect or a
  too-broad claim is S2's first measurement, not an assumption.
- **No adopter's Gate may change verdict on upgrade.** The new leg skips with a reason unless a
  pair is declared, as `issue-log` does. A report added to the loader is a report, not a refusal.
- **A pair is a document AND a code file.** Two files in a package give two pairs over one
  README. Any change to how pairs are counted or rendered has to keep that true.

## Code Standards

### Language and Environment
- Filled from the STACK section of `CLAUDE.md`, composed from `.beadloom/flow.yml`:
  Python >= 3.10, `uv` for environment and runs.

### Methodologies

| Methodology | Application |
|-------------|-------------|
| TDD | Red -> Green -> Refactor; the red is measured on a foreign project where the defect lives |
| Clean Code | SRP, DRY, KISS |
| Architecture | DDD packages, as `.beadloom/flow.yml` declares; `beadloom lint --strict` enforces the boundaries |

### Testing
- **Framework:** pytest + pytest-cov
- **Coverage:** minimum 80%
- **Acceptance:** every behaviour-bearing criterion in the PRD is a scenario in
  `tests/acceptance/features/`, tagged `@bead:` and `@node:`; `beadloom lint` reports a
  referenced scenario the suite does not contain.

### Code Quality
- **Linter/formatter:** `uv run ruff check src/ tests/`
- **Type checker:** `uv run mypy src/` (strict; `[tool.mypy] python_version = "3.10"`)
- **Gate:** `beadloom ci` rc 0 is required before any push.

### Restrictions
- No `Any` or `# type: ignore` without a stated reason
- No `print()` or `breakpoint()` — use logging
- No bare `except:` — name the exception
- No `os.path` where `pathlib` fits; no f-strings in SQL; `yaml.safe_load`, never `yaml.load`
- **Never pipe a command whose exit code is the answer.** `cmd | tail` returns `tail`'s code.
  This cost two false green reports during the release that preceded this epic.
- **Never edit `.claude/CLAUDE.md` or `.claude/agents/*`** — they are composed. The source is
  `.beadloom/flow/claude/CLAUDE.md`; recompose with `beadloom setup-agentic-flow`.

## Architectural Decisions

| Date | Decision | Reason |
|------|----------|--------|
| 2026-09-10 | The duplicate-`ref_id` report goes in `graph/loader.py` at parse, not in `each_graph_file` | six of seven readers do not reach the policy; a report there would cover one reader and read as covering the directory |
| 2026-09-10 | `version_subjects` is not extended to cover the graph YAML and the tests | its population is documents and its question is which SUBJECT a token belongs to; merging gives one module two populations and no way to report either |
| 2026-09-10 | The README pair is compared by SHAPE, never by text | the files are two languages; a text comparison is a check that has to be switched off |
| 2026-09-10 | `init` names the modules in the skeleton rather than attesting the pair at write time | attesting asserts a freshness nobody checked — the false-green shape removed in BDL-061 |
| 2026-09-10 | The command is `version-surface` | symmetry with the shipped `typed-surface`: the same shape of question earns the same shape of name |
| 2026-09-10 | `sync-update` reports what it did NOT clear; its scope is untouched | scope is BDL-UX #279; the defect here is a command reporting over the population it attested and staying silent about the rest |
| 2026-09-10 | The three graph-domain readers restate `each_graph_file`'s guards rather than routing to it | `onboarding` already imports `graph`, so the reverse import is a cycle `no-dependency-cycles` refuses at error severity; moving the policy is filed as `beadloom-4axf` rather than done mid-wave |

## Related Files

Discover via `beadloom ctx <ref-id>` — never hardcode. The thirteen nodes in scope are listed in
the RFC's *Affected Areas*, and each bead's `refs:` is generated from the axes rows kept in
scope rather than typed.

## Current Phase

- **Phase:** Planning
- **Current bead:** none yet — beads are created after PLAN is approved
- **Blockers:** none

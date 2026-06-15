# BRIEF: BDL-058 — Release 2.1.0

> **Status:** Approved
> **Created:** 2026-06-15
> **Type:** chore

---

## Problem

BDL-056 + BDL-057 shipped to `main` (#17, #18) but are unreleased: `__version__` is still 2.0.0, the CHANGELOG `[Unreleased]` is empty, and the two planning files that drive future work — `ROADMAP.md` and `BDL-UX-Issues.md` — stop at v2.0.0/BDL-052 and don't reflect what shipped (positioning, reference-doc freshness, docs-audit-in-Gate) or what is now resolved.

## Solution

Cut **2.1.0** (MINOR — additive, backward-compatible: `docs audit` in the Gate + `reference`/`watches` + `docs_audit.ignore`; no breaking changes). Bring the planning files current so the next cycle starts from an accurate picture.

## Beads

Single chore bead (inline, no parallelism). Scope:
- **Version:** `__version__` 2.0.0→2.1.0 (`src/beadloom/__init__.py`) + `.claude/CLAUDE.md` §0.1 + the `test_integration_v1` version pin.
- **CHANGELOG:** `[Unreleased]` → dated `[2.1.0]` (BDL-056 + BDL-057, additive note).
- **ROADMAP currency:** add the v2.1.0 entry + baseline; reword P3 "Semantic docs audit" (BDL-057 shipped a `docs_audit.ignore` workaround, not a semantic fix); mark the REVIEW-2 §4 docs-debt block resolved.
- **BDL-UX currency:** close #130 (rule-type names fixed) + #121 (RU FP suppressed) + #131 (3 nits fixed this release); log #132 (`setup-agentic-flow --force` corrupts vendored CLAUDE.md placeholder) + #133 (per-worktree `beadloom.db` mass re-baseline); update tallies (Total 133 / Open 23 / Closed 87).
- **3 doc nits (closes #131):** drop `--non-interactive` from getting-started; fix the architecture domain count; CONTRIBUTING `your-org`→`zoologov` + add a Release Process section.
- **Version-fact hygiene:** version-neutralize the multi-agent guide title/intro (was "Beadloom 2.0.0"); `docs_audit.ignore` the guide's historical body version refs; make the snapshot-label example non-version.
- **Release:** one PR → merge → GitHub Release `v2.1.0` (triggers `pypi-publish.yml` → PyPI) → `deploy-site.yml` refreshes the portal → delete the `archive/BDL-051-docs` tag.

## Acceptance criteria

- `beadloom --version` == 2.1.0; CHANGELOG has a dated `[2.1.0]`; CLAUDE.md §0.1 = 2.1.0.
- `beadloom ci` rc 0 (docs-audit PASS — the version bump's stale facts resolved); pytest green; ruff/mypy clean.
- ROADMAP + BDL-UX reflect BDL-056/057 + the closed/new issues; planning picture accurate.
- v2.1.0 tag/Release cut + PyPI publish confirmed; portal redeployed.

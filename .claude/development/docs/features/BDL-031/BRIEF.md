# BRIEF: BDL-031 — v1.8.0 Release Preparation

> **Type:** chore
> **Status:** Approved
> **Created:** 2026-02-21

---

## Problem

v1.8.0 has been developed across BDL-023 through BDL-030 (47 commits since v1.7.0) but the release artifacts are incomplete:

1. **CHANGELOG.md** — only lists TUI (BDL-025). Missing: C4 diagrams (BDL-023), Debt Report (BDL-024), Docs Audit (BDL-026), Agent Instructions Freshness (BDL-030), UX bugfix rounds (BDL-027, BDL-028, BDL-029).
2. **Version** — still 1.7.0 in pyproject.toml (uses dynamic versioning via hatch, but CLAUDE.md section 0.1 says 1.7.0).
3. **README.md / README.ru.md** — stale counts: "13 MCP tools" (actual: 14), "22 CLI commands" (actual: 29), "10 nodes, 12 edges" in example (actual: 23 nodes, 63 edges). Also "docs audit" command not listed.
4. **docs/architecture.md** — stale counts: "22 commands", "13 MCP tools", "20 nodes". Missing: docs audit, TUI, snapshots architecture.
5. **CONTRIBUTING.md** — "80" test count matches coverage threshold, not stale. "22 commands" and "13 tools" in project structure are stale.
6. **SECURITY.md** — "11 tools" in MCP section is stale (actual: 14, with 11 read + 3 write, not 11+2).
7. **STRATEGY-2.md** — needs status update: "Current version: 1.7.0" -> 1.8.0, phase statuses to reflect completed work.
8. **CLAUDE.md** — section 0.1 auto-refreshable, but version needs bump.

## Solution

Parallel `/tech-writer` agents update all documents. Version bump via `beadloom setup-rules --refresh` after version change.

## Beads

| ID | Name | Priority | Status |
|----|------|----------|--------|
| BEAD-01 | Version bump + CHANGELOG completion | P0 | Pending |
| BEAD-02 | README.md + README.ru.md update | P1 | Pending |
| BEAD-03 | docs/architecture.md + docs/getting-started.md update | P1 | Pending |
| BEAD-04 | CONTRIBUTING.md + SECURITY.md update | P1 | Pending |
| BEAD-05 | STRATEGY-2.md status update | P1 | Pending |
| BEAD-06 | CLAUDE.md refresh + beadloom validation | P1 | Pending |
| BEAD-07 | Review — final verification | P2 | Pending |

## Acceptance Criteria

- [ ] Version bumped to 1.8.0
- [ ] CHANGELOG.md complete for v1.8.0 (all phases, all BDL issues)
- [ ] README.md and README.ru.md counts and features up to date
- [ ] docs/architecture.md reflects current state
- [ ] CONTRIBUTING.md and SECURITY.md accurate
- [ ] STRATEGY-2.md reflects v1.8.0 completion
- [ ] CLAUDE.md section 0.1 refreshed
- [ ] `beadloom sync-check` clean
- [ ] `uv run pytest` passes
- [ ] All beads closed

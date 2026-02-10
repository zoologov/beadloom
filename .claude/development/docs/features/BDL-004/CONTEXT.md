# CONTEXT: BDL-004 — Phase 3: Team Adoption (v0.5)

> **Last updated:** 2026-02-10
> **Phase:** Strategy Phase 3
> **Status:** COMPLETE
> **Depends on:** BDL-003 (v0.4.0 complete)

---

## Goal

Make Beadloom useful for the whole team, not just the person who set it up.

## Design Principle

**Existing infrastructure + team workflows = adoption.**

## Deliverables

| # | Item | Status | Bead |
|---|------|--------|------|
| 3.2 | Health dashboard + trend data | TODO | — |
| 3.4 | MCP templates (Cursor, Claude Code, Windsurf) | TODO | — |
| 3.3 | Issue tracker linking | TODO | — |
| 3.1 | CI integration (GitHub Action + GitLab CI) | TODO | — |

## Key Decisions

| Decision | Reason |
|----------|--------|
| **Composite Action in beadloom repo** | No separate repo overhead; versioned with code |
| **GitLab CI template alongside GitHub Action** | Teams use different platforms; core is platform-agnostic |
| **`--json` and `--report` flags for sync-check** | `--report` generates Markdown, CI templates just post it |
| **Trend data in `health_snapshots` table** | Populated per-reindex; simple delta comparison |
| **Links in `extra` JSON via YAML** | YAML stays source of truth, versioned in Git |
| **`--tool` flag on setup-mcp** | One command, multiple editors |
| **Additive schema only** | No SCHEMA_VERSION bump, backward compatible |

## Existing Infrastructure (validated)

| Component | Status | Location |
|-----------|--------|----------|
| `sync-check --porcelain` | EXISTS | `cli.py:363-413` |
| Exit code 2 on stale | EXISTS | `cli.py:412-413` |
| `beadloom status` | EXISTS (basic) | `cli.py:308-360` |
| `doctor` checks | EXISTS | `doctor.py:106-113` |
| `nodes.extra` JSON field | EXISTS | `db.py:23` |
| Extra passthrough in graph_loader | EXISTS | `graph_loader.py:93-97` |
| `setup-mcp` command | EXISTS | `cli.py:602-648` |
| MCP server (5 tools) | EXISTS | `mcp_server.py:124-209` |
| Pre-commit hooks | EXISTS | `cli.py:416-499` |

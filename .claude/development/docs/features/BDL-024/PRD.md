# PRD: BDL-024 — Architecture Debt Report

> **Status:** Approved
> **Created:** 2026-02-20

---

## Problem

Architecture debt is invisible until it's too late. Teams say "we have tech debt" but can't quantify it. Beadloom already collects all the signals — lint violations, stale docs, missing coverage, complexity metrics, dormant domains — but they're scattered across 4 separate commands (`lint`, `sync-check`, `doctor`, `status`). There is no single aggregated view that says "your architecture debt is 23/100 and trending down."

## Impact

- **Developers** lack a single metric to track architecture health over time.
- **Tech leads** can't set CI gates that prevent debt from creeping in.
- **AI agents** can't autonomously prioritize architectural fixes without a structured debt signal.
- Without aggregation, teams run 4 commands and mentally combine results — error-prone and not CI-friendly.

## Goals

- [ ] Single command (`beadloom status --debt-report`) that produces a numeric debt score 0-100
- [ ] Score broken down by categories: rule violations, doc gaps, complexity smells, test gaps
- [ ] JSON output (`--json`) for CI/CD integration and scripting
- [ ] CI gate (`--fail-if=score>N` / `--fail-if=errors>0`) with non-zero exit codes
- [ ] Trend tracking vs last snapshot (delta per category)
- [ ] MCP tool `get_debt_report` for AI agent consumption
- [ ] Top offenders list ranking nodes by individual debt contribution

## Non-goals

- Custom remediation suggestions (future)
- Historical chart generation (visual charts are for TUI in Phase 12.10)
- Cross-repo debt aggregation (Phase 14)
- Weight optimization ML (out of scope)

## User Stories

### US-1: Developer checks project health
**As** a developer, **I want** to run `beadloom status --debt-report` and see a scored breakdown, **so that** I know where to invest refactoring effort.

**Acceptance criteria:**
- [ ] Report shows numeric score 0-100 with severity label
- [ ] Categories show counts and point contributions
- [ ] Top offenders list shows worst nodes

### US-2: CI pipeline gates on debt
**As** a tech lead, **I want** to add `beadloom status --debt-report --fail-if=score>30` to CI, **so that** PRs that increase debt beyond threshold are blocked.

**Acceptance criteria:**
- [ ] `--fail-if=score>N` exits with code 1 when score exceeds threshold
- [ ] `--fail-if=errors>0` exits with code 1 when any lint errors exist
- [ ] JSON output available for CI artifact storage

### US-3: AI agent uses debt data
**As** an AI agent, **I want** to call `get_debt_report` MCP tool, **so that** I can autonomously identify and prioritize architectural fixes.

**Acceptance criteria:**
- [ ] MCP tool returns structured JSON with score, categories, top offenders
- [ ] Output matches the JSON CLI format

### US-4: Team tracks debt trend
**As** a team, **I want** to see how debt score changed since last snapshot, **so that** we can celebrate improvements and catch regressions.

**Acceptance criteria:**
- [ ] `--trend` flag shows delta vs last snapshot per category
- [ ] Clear visual indicators for improvement (down arrow) vs regression (up arrow)

## Acceptance Criteria (overall)

- [ ] `beadloom status --debt-report` produces human-readable report with Rich formatting
- [ ] `--json` flag produces machine-readable JSON matching the spec schema
- [ ] `--fail-if=score>N` and `--fail-if=errors>0` work as CI gates
- [ ] `--trend` shows delta vs last snapshot
- [ ] `--category=<cat>` filters output by category
- [ ] MCP tool `get_debt_report` exposed and functional
- [ ] All weights configurable in `config.yml`
- [ ] Score formula: weighted sum capped at 100
- [ ] Severity labels: clean (0), low (1-10), medium (11-25), high (26-50), critical (51-100)
- [ ] Tests: >=80% coverage for new code
- [ ] Backward compatible: `beadloom status` without `--debt-report` unchanged

# CONTEXT: BDL-024 — Architecture Debt Report

> **Status:** Approved
> **Created:** 2026-02-20
> **Last updated:** 2026-02-20

---

## Goal

Add a single command (`beadloom status --debt-report`) that aggregates all architecture health signals into a quantified debt report with a numeric score 0-100, category breakdown, trend tracking, CI gate support, and MCP exposure.

## Key Constraints

- All data sources already exist in v1.7 — no new DB tables
- Must not break existing `beadloom status` output (additive `--debt-report` flag)
- Configurable weights via `config.yml` section `debt_report`
- Score formula: weighted sum capped at 100
- Frozen dataclasses for all data structures
- DDD: new module in `infrastructure/` domain (aggregates infra-level data)

## Code Standards

### Language and Environment
- **Language:** Python 3.10+ (type hints, `str | None` syntax)
- **Package manager:** uv
- **Virtual environment:** uv venv

### Methodologies

| Methodology | Application |
|-------------|-------------|
| TDD | Red -> Green -> Refactor |
| Clean Code | snake_case, SRP, DRY, KISS |
| Modular architecture | CLI -> Core -> Storage |

### Testing
- **Framework:** pytest + pytest-cov
- **Coverage:** minimum 80%

### Code Quality
- **Linter:** ruff (lint + format)
- **Typing:** mypy --strict

### Restrictions
- No `Any` without justification
- No `print()` / `breakpoint()` — use logging
- No bare `except:` — only `except SpecificError:`
- No `os.path` — pathlib only
- No f-strings in SQL — parameterized queries `?`
- No `yaml.load()` — safe_load only

## Architectural Decisions

| Date | Decision | Reason |
|------|----------|--------|
| 2026-02-20 | Place in `infrastructure/debt_report.py` | Aggregates infrastructure-level health data from multiple domains |
| 2026-02-20 | Extend `status` command, not new command | Per Strategy decision: debt is a deeper view of project status |
| 2026-02-20 | Config via `config.yml` `debt_report` section | Consistent with project patterns, no new config files |
| 2026-02-20 | Recompute trend from snapshot, not store score | No new storage; snapshots from 12.6.3 already capture full graph |
| 2026-02-20 | Weights configurable with sensible defaults | Teams can tune formula for their priorities |

## Related Files

- `src/beadloom/infrastructure/debt_report.py` — NEW core module
- `src/beadloom/infrastructure/doctor.py` — data source (graph integrity checks)
- `src/beadloom/infrastructure/git_activity.py` — data source (dormant detection)
- `src/beadloom/graph/rule_engine.py` — data source (lint violations)
- `src/beadloom/graph/snapshot.py` — data source (trend tracking)
- `src/beadloom/doc_sync/engine.py` — data source (stale docs)
- `src/beadloom/context_oracle/test_mapper.py` — data source (test gaps)
- `src/beadloom/services/cli.py` — CLI integration (status command)
- `src/beadloom/services/mcp_server.py` — MCP tool integration
- `tests/test_debt_report.py` — NEW test file

## Current Phase

- **Phase:** Planning
- **Current bead:** none (awaiting approval)
- **Blockers:** none

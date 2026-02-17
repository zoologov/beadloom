# CONTEXT: BDL-021 — v1.7.0: AaC Rules v2, Init Quality, Architecture Intelligence

> **Status:** Approved
> **Created:** 2026-02-17
> **Last updated:** 2026-02-17 (Wave 1 done)

---

## Goal

Transform Beadloom from a documentation tool to an architecture enforcement platform by adding 4 new rule types with tag-based matching, fixing bootstrap to capture 80%+ of project architecture, and adding architecture change tracking with snapshots and enhanced impact analysis.

## Key Constraints

- Backward compatibility: rules.yml v1/v2 must continue to work (new rules require v3)
- No external LLM calls (agent-native principle)
- Tags stored in existing `extra` JSON column (no schema migration for nodes table)
- `graph_snapshots` table is the only new DDL addition
- All existing tests must pass; 80%+ coverage for new code
- Python 3.10+, SQLite WAL mode

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
| 2026-02-17 | Tags inline in services.yml (not separate file) | Simpler, tags belong to nodes |
| 2026-02-17 | Schema v3 (not extend v2) | Clean versioning, backward compat preserved |
| 2026-02-17 | ForbidEdgeRule separate from DenyRule | Different evaluation logic (edges table vs code_imports) |
| 2026-02-17 | Snapshots in main SQLite DB | Simpler queries, no extra file management |
| 2026-02-17 | Glob-based import rules (not node-level) | More granular file-level control |

## Related Files

(discover via `beadloom ctx <ref-id>`)

- `graph/rule_engine.py` — Rule types, evaluators, loader
- `graph/linter.py` — Lint orchestrator
- `graph/loader.py` — Graph YAML parsing
- `graph/diff.py` — Graph diff
- `onboarding/scanner.py` — Bootstrap, init, rules generation
- `onboarding/doc_generator.py` — Doc skeleton generation
- `context_oracle/why.py` — Impact analysis
- `infrastructure/db.py` — SQLite schema
- `services/cli.py` — CLI commands
- `services/mcp_server.py` — MCP tools

## Current Phase

- **Phase:** Development (Wave 1 complete)
- **Current bead:** Wave 2 ready
- **Blockers:** none

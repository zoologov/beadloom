# CONTEXT: BDL-026 — Documentation Audit (Phase 12.11)

> **Status:** Approved
> **Created:** 2026-02-20
> **Last updated:** 2026-02-20

---

## Goal

Implement `beadloom docs audit` — a zero-config command that detects stale facts (versions, counts) in project-level markdown documentation by comparing keyword-proximity-matched mentions against auto-computed ground truth from Beadloom infrastructure.

## Key Constraints

- Python 3.10+ (type hints, `str | None` syntax)
- SQLite (WAL mode) for graph DB access
- Zero-config: works without user configuration
- Ships as experimental in v1.8 (API may change)
- Must integrate with existing `docs` CLI group and debt report infrastructure
- Single new module `doc_sync/audit.py` — no new domain

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
| 2026-02-20 | Single module `doc_sync/audit.py` | Feature fits doc_sync domain; single module sufficient for v1.8 scope |
| 2026-02-20 | Keyword-proximity matching over AST parsing | Simpler, zero-config, sufficient for numeric facts. Can revisit in v1.9 |
| 2026-02-20 | Exclude CHANGELOG.md by default | Too many intentionally historical numbers — high false positive risk |
| 2026-02-20 | Frozen dataclasses for all data types | Immutable results, clean API boundaries |

## Related Files

(discover via `beadloom ctx doc-sync`)

- `src/beadloom/doc_sync/` — domain home (engine.py, doc_indexer.py)
- `src/beadloom/doc_sync/__init__.py` — public API exports
- `src/beadloom/services/cli.py` — CLI entry point, `@docs` group at ~line 1617
- `src/beadloom/infrastructure/debt_report.py` — debt score computation
- `.beadloom/_graph/services.yml` — graph node definitions
- `.beadloom/config.yml` — project configuration

## Current Phase

- **Phase:** Planning
- **Current bead:** —
- **Blockers:** none

# CONTEXT: BDL-034 — UX Issues & Improvements Batch Fix

> **Status:** Approved
> **Created:** 2026-03-10
> **Last updated:** 2026-03-10

---

## Goal

Fix 3 open bugs (#67, #68, #69) and implement 3 improvements (#65, #66, #70) from BDL-UX-Issues.md to improve data accuracy, developer trust, and agent reliability in Beadloom v1.9.0.

## Key Constraints

- All changes must be backward-compatible (no breaking CLI or schema changes)
- Schema migration via additive columns with DEFAULT values
- No new external dependencies
- Issue #66 (snapshot diffing) needs verification first — may already be resolved
- All 6 issues must have test coverage before closing

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
| 2026-03-10 | Generic class-name serialization for rule types in DB (#67) | Forward-compatible, avoids N isinstance branches |
| 2026-03-10 | HTML comment markers for AGENTS.md custom section (#69) | Unambiguous, not confused with user content |
| 2026-03-10 | 3-layer FP reduction for docs audit (#65) | Pattern-based, no LLM dependency |
| 2026-03-10 | Additive `doc_hash_at_last_edit` column for two-phase sync (#70) | Backward-compatible, no schema rebuild |

## Related Files

(discover via `beadloom ctx <ref-id>` — never hardcode)

- infrastructure domain: reindex.py, db.py
- onboarding domain: scanner.py
- doc-sync domain: scanner.py, engine.py
- services: cli.py

## Current Phase

- **Phase:** Planning
- **Current bead:** —
- **Blockers:** none

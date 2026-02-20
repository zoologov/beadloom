# CONTEXT: BDL-027 — UX Issues Batch Fix (Phase 12.12)

> **Status:** Approved
> **Created:** 2026-02-20
> **Last updated:** 2026-02-20

---

## Goal

Fix all 15 open UX issues from BDL-UX-Issues.md across 5 independent domain areas: C4 diagrams, docs audit, doctor/debt report, init/onboarding, and route/test context.

## Key Constraints

- All 5 areas are independent — no cross-dependencies between areas
- No breaking API changes
- All existing 2389+ tests must continue to pass
- Each area gets its own dev bead for parallel execution

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
| 2026-02-20 | 5 parallel dev beads by domain area | Areas are independent, maximizes throughput |
| 2026-02-20 | Keep test_count as symbol count, label it | pytest --collect-only too slow for CI |
| 2026-02-20 | Use importlib.metadata for dynamic version | Works for all packaging backends |

## Related Files

(discover via `beadloom ctx <ref-id>`)

- C4: `graph/c4.py`
- Docs audit: `doc_sync/scanner.py`, `doc_sync/audit.py`, `services/cli.py`
- Doctor/debt: `infrastructure/doctor.py`, `infrastructure/debt_report.py`
- Init: `onboarding/scanner.py`, `services/cli.py`
- Route/test: `context_oracle/route_extractor.py`, `context_oracle/test_mapper.py`

## Current Phase

- **Phase:** Planning
- **Current bead:** —
- **Blockers:** none

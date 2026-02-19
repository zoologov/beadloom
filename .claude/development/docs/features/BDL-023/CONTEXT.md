# CONTEXT: BDL-023 — C4 Architecture Diagrams

> **Status:** Approved
> **Created:** 2026-02-19
> **Last updated:** 2026-02-19

---

## Goal

Auto-generate C4 model diagrams (Context, Container, Component) from the existing architecture graph via `beadloom graph --format=c4|c4-plantuml` with `--level` and `--scope` controls.

## Key Constraints

- Extend existing `graph` command, do not create a new command
- Backward compatibility: default `beadloom graph` output remains unchanged (Mermaid flowchart)
- New module `graph/c4.py` in graph domain — no cross-domain changes
- Zero new dependencies — Mermaid/PlantUML are text output formats
- `c4_level` explicit field > `part_of` depth heuristic > tag-based inference

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
| 2026-02-19 | Extend `graph` command, not new command | Consistent UX, reuses existing infrastructure |
| 2026-02-19 | New module `graph/c4.py` | Keeps domain logic in graph package, CLI stays thin |
| 2026-02-19 | No new DB tables | All data sourced from existing nodes, edges, code_symbols |
| 2026-02-19 | `part_of` edges → boundaries, not Rel() | C4 semantics: containment ≠ relationship |
| 2026-02-19 | Only `uses`/`depends_on` → Rel() | `touches_code`, `part_of` have no architectural relationship meaning in C4 |

## Related Files

(discover via `beadloom ctx graph`)

- `src/beadloom/graph/c4.py` — NEW: C4 mapping + rendering
- `src/beadloom/graph/loader.py` — graph loader (no changes, extra JSON handles c4_* fields)
- `src/beadloom/services/cli.py` — graph command extension
- `src/beadloom/infrastructure/db.py` — DB schema (no changes)
- `tests/test_c4.py` — NEW: C4 unit tests
- `tests/test_cli_graph.py` — CLI integration tests

## Current Phase

- **Phase:** Planning
- **Current bead:** None (awaiting PLAN approval)
- **Blockers:** none

# CONTEXT: BDL-006 — Phase 5: Developer Experience (v0.7)

> **Last updated:** 2026-02-11
> **Phase:** Strategy Phase 5
> **Status:** COMPLETE
> **Version:** 0.7.0
> **Depends on:** BDL-005 (v0.6.0 complete)

---

## Goal

Make Beadloom enjoyable and intuitive — visual graph exploration, impact analysis, change visibility, zero-friction reindexing.

## Design Principle

> **Show, don't tell.** Every feature visualizes data that already exists in the index.

No new data collection. All features are read-only consumers of the existing SQLite schema (except watch, which triggers existing reindex).

## Deliverables

| # | Item | Status | Bead |
|---|------|--------|------|
| 5.1 | `beadloom why` — impact analysis | DONE | beadloom-fzb |
| 5.2 | `beadloom diff` — graph delta | DONE | beadloom-q6b |
| 5.3 | `beadloom ui` — TUI dashboard | DONE | beadloom-1c1 |
| 5.4 | `beadloom watch` — auto-reindex | DONE | beadloom-6fr |

## Key Decisions

| Decision | Reason |
|----------|--------|
| **Textual for TUI** | Modern, CSS-styled, async, mouse support, 24-bit color |
| **textual + watchfiles as optional extras** | No bloat for CLI/MCP-only users |
| **Bidirectional BFS in why** | Separate upstream/downstream for clear presentation |
| **git show for diff** | Zero new deps, works with any git ref |
| **500ms debounce in watch** | Handles editor multi-write patterns |
| **Exit code 0/1 for diff** | CI-friendly gate |
| **TUI iterative build (A→D)** | Each phase is shippable, reduces risk |
| **No schema changes** | SCHEMA_VERSION stays "1", all features read existing data |

## Code Standards

### Language and environment
- **Language:** Python 3.10+ (type hints, `str | None` syntax)
- **Package manager:** uv
- **Virtual environment:** uv venv

### Methodologies
| Methodology | Application |
|-------------|-------------|
| TDD | Red -> Green -> Refactor for each bead |
| Clean Code | Naming (snake_case), SRP, DRY, KISS |
| Modular architecture | CLI -> Core -> Storage, dependencies point inward |

### Testing
- **Framework:** pytest + pytest-cov
- **Coverage:** minimum 80%
- **Fixtures:** conftest.py, tmp_path
- **TUI testing:** Textual `pilot` for headless tests

### Code quality
- **Linter:** ruff (lint + format)
- **Typing:** mypy --strict

### Restrictions
- [x] No `Any` without justification
- [x] No `print()` / `breakpoint()` — use logging or Rich console
- [x] No bare `except:` — only `except SpecificError:`
- [x] No `os.path` — use `pathlib.Path`
- [x] No f-strings in SQL — parameterized queries `?`
- [x] No `yaml.load()` — only `yaml.safe_load()`
- [x] No magic numbers — extract into constants

## Existing Infrastructure to Reuse

| Module | Reuse in Phase 5 |
|--------|-------------------|
| `context_builder.py:bfs_subgraph()` | Reference for why BFS algorithm |
| `graph_loader.py:parse_graph_file()` | Diff: parse YAML at git refs |
| `reindex.py:incremental_reindex()` | Watch: triggered on file changes |
| `health.py:take_snapshot()` | TUI: status bar metrics |
| `search.py:search_fts5()` | TUI: search panel |
| `db.py:open_db()` | TUI: read-only connection |

## New Dependencies

| Package | Extra group | Version | Purpose |
|---------|-------------|---------|---------|
| `textual` | `[tui]` | >= 0.50 | Interactive terminal dashboard |
| `watchfiles` | `[watch]` | >= 0.20 | File system watcher |

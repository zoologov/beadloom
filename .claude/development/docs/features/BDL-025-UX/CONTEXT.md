# CONTEXT: BDL-025-UX — TUI UX Polish (12.10.8)

> **Status:** Approved
> **Created:** 2026-02-20
> **Last updated:** 2026-02-20

---

## Goal

Improve TUI usability with 4 targeted widget-level changes: replace redundant Explorer edges with symbols, add screen descriptions, add Dashboard keybindings, fix Context Inspector scroll.

## Key Constraints

- All 4 beads are independent — can run in parallel (Wave 1)
- No changes to data provider interfaces (except one new `get_symbols` method)
- No changes to CLI, MCP, graph, or infrastructure domains
- Existing 285+ TUI tests must pass
- Textual framework patterns: Static widget with `overflow-y: auto`, Label for action bars

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
| 2026-02-20 | Top-level symbols only (no nested methods) | Matches `extract_symbols()` output, keeps panel concise |
| 2026-02-20 | Screen descriptions always visible (no toggle) | 1 line is negligible overhead, always helps orientation |
| 2026-02-20 | Remove truncation entirely (not increase limit) | Textual scroll handles arbitrary content; truncation was premature optimization |

## Related Files

- `src/beadloom/tui/widgets/node_detail_panel.py` — BEAD-01 primary target
- `src/beadloom/tui/data_providers.py` — BEAD-01 new `get_symbols()` method
- `src/beadloom/tui/screens/dashboard.py` — BEAD-02 + BEAD-03
- `src/beadloom/tui/screens/explorer.py` — BEAD-02
- `src/beadloom/tui/screens/doc_status.py` — BEAD-02
- `src/beadloom/tui/styles/dashboard.tcss` — BEAD-02 + BEAD-03
- `src/beadloom/tui/styles/explorer.tcss` — BEAD-02
- `src/beadloom/tui/styles/doc_status.tcss` — BEAD-02
- `src/beadloom/tui/widgets/context_preview.py` — BEAD-04
- `src/beadloom/context_oracle/code_indexer.py` — symbol extraction API

## Current Phase

- **Phase:** Planning
- **Current bead:** —
- **Blockers:** none

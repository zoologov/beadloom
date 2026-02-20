# CONTEXT: BDL-025 — Interactive Architecture TUI

> **Status:** Approved
> **Created:** 2026-02-20
> **Last updated:** 2026-02-20

---

## Goal

Transform Beadloom's TUI from a basic read-only viewer (3 widgets, 1 screen) into an interactive architecture workstation with 3 screens, 10+ widgets, live file watching, and keyboard-driven actions. All data from existing infrastructure APIs — no new backend needed.

## Key Constraints

- Textual >= 0.80 (upgrade from >= 0.50)
- Optional dependency: `beadloom[tui]` — core stays lightweight
- All data access read-only via existing infrastructure APIs
- No built-in LLM calls (agent-native principle)
- Startup < 1s, 500+ nodes smooth, memory < 50MB
- Works over SSH, tmux, containers
- Test coverage >= 80% via Textual headless pilot

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
| Modular architecture | Screens -> Widgets -> DataProviders -> Infrastructure |

### Testing
- **Framework:** pytest + pytest-cov
- **Coverage:** minimum 80%
- **TUI testing:** Textual headless pilot (`app.run_test()`)

### Code Quality
- **Linter:** ruff (lint + format)
- **Typing:** mypy --strict

### Restrictions
- No `Any` without justification
- No `print()` / `breakpoint()` — use logging
- No bare `except:` — only `except SpecificError:`
- No `os.path` — pathlib only
- No f-strings in SQL — parameterized queries `?`

## Architectural Decisions

| Date | Decision | Reason |
|------|----------|--------|
| 2026-02-20 | Textual >= 0.80 (up from 0.50) | Need stable Screen API, CSS improvements, Worker reliability |
| 2026-02-20 | Data providers as thin wrappers | All data already available via existing infra APIs — no duplication |
| 2026-02-20 | Custom Rich sparklines over textual-plotext | Avoid extra dependency, Rich already in stack |
| 2026-02-20 | Separate TCSS files per screen | Textual best practice, maintainability |
| 2026-02-20 | `beadloom tui` primary, `ui` alias kept | Clearer naming, backward compat |
| 2026-02-20 | FileWatcher as Textual Worker | Native async integration, no threading complexity |

## Related Files

(discover via `beadloom ctx tui` — never hardcode)

Key areas:
- `src/beadloom/tui/` — TUI module (rewrite target)
- `src/beadloom/services/cli.py` — CLI command registration
- `src/beadloom/infrastructure/debt_report.py` — debt data provider
- `src/beadloom/graph/rule_engine.py` — lint data provider
- `src/beadloom/doc_sync/engine.py` — sync data provider
- `src/beadloom/infrastructure/git_activity.py` — activity data provider
- `src/beadloom/context_oracle/why.py` — dependency analysis
- `src/beadloom/context_oracle/builder.py` — context bundle
- `tests/test_tui.py` — TUI tests (rewrite target)

## Current Phase

- **Phase:** Planning
- **Current bead:** —
- **Blockers:** none

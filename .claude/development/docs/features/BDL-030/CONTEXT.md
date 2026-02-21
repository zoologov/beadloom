# CONTEXT: BDL-030 — Agent Instructions Freshness

> **Status:** Approved
> **Created:** 2026-02-21
> **Last updated:** 2026-02-21

---

## Goal

Automatically detect and fix stale facts in agent instruction files (CLAUDE.md, AGENTS.md) by adding a doctor check for drift detection and extending setup-rules with a `--refresh` flag for auto-regeneration of dynamic sections.

## Key Constraints

- Reuse existing `doctor` infrastructure (`Check` dataclass, `Severity` enum, `run_checks()` in `infrastructure/doctor.py`)
- Reuse existing `setup-rules` infrastructure (`generate_agents_md()`, `setup_rules_auto()` in `onboarding/scanner.py`)
- Must not break CLAUDE.md for projects without markers — graceful degradation
- Phase status parsing optional (not all projects have STRATEGY-2.md)
- Two-task delivery: detection first (12.12.1), then auto-fix (12.12.2)

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
| 2026-02-21 | Doctor check uses project_root param, not conn | Fact sources are files (CLAUDE.md, pyproject.toml), not DB |
| 2026-02-21 | Section markers use HTML comments | Invisible in rendered markdown, parseable, standard practice |
| 2026-02-21 | Phase parsing is optional with graceful skip | Not all projects have STRATEGY-2.md |
| 2026-02-21 | Auto-insert markers on first --refresh if section 0.1 detected | Reduces manual setup friction |

## Related Files

(discover via `beadloom ctx <ref-id>`)

- `infrastructure/doctor.py` — existing doctor checks, `run_checks()`, `Check` dataclass
- `onboarding/scanner.py` — existing `generate_agents_md()`, `setup_rules_auto()`
- `services/cli.py` — Click group `main()`, `setup-rules` command, `doctor` command
- `services/mcp_server.py` — `_TOOLS` list (14 tools)
- `src/beadloom/__init__.py` — `__version__`
- `.claude/CLAUDE.md` — target for markers and fact refresh
- `.beadloom/AGENTS.md` — target for refresh (already generated)

## Current Phase

- **Phase:** Planning
- **Current bead:** —
- **Blockers:** none

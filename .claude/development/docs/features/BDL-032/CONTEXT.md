# CONTEXT: BDL-032 — Enhanced Architecture Rules

> **Status:** Approved
> **Created:** 2026-02-21
> **Last updated:** 2026-02-21

---

## Goal

Expand beadloom's own rules.yml from 4 rules (2 types) to 9 rules (all 7 types), add `exclude` filter to NodeMatcher, and upgrade schema from v1 to v3. Makes beadloom a comprehensive dogfood project for its AAC system.

## Key Constraints

- NodeMatcher is a frozen dataclass — `exclude` must be an optional field with default None
- Schema v3 parser already exists — no loader changes needed
- Layer rule must use `severity: warn` due to known infra→domain coupling (reindex orchestrator)
- `forbid_import` checks actual Python imports via `code_imports` table (not graph edges)
- Backward compatibility: v1 rules.yml must still parse correctly

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
| 2026-02-21 | `exclude` as tuple[str, ...] on NodeMatcher | Frozen dataclass requires immutable type; tuple is hashable |
| 2026-02-21 | Accept both string and list in YAML, normalize to tuple | Ergonomic YAML authoring |
| 2026-02-21 | Layer rule severity: warn | Known infra coupling, out of scope to fix |
| 2026-02-21 | forbid_import for tui and onboarding | These domains should not bypass service layer to reach infrastructure |

## Related Files

- `src/beadloom/graph/rule_engine.py` — NodeMatcher dataclass + all 7 evaluators
- `.beadloom/_graph/rules.yml` — rule definitions (target of changes)
- `tests/test_rule_engine.py` — primary test file
- `tests/test_import_boundary_rule.py` — forbid_import tests
- `tests/test_cycle_rule.py` — forbid_cycles tests
- `tests/test_rule_severity.py` — severity tests

## Current Phase

- **Phase:** Planning
- **Current bead:** none
- **Blockers:** none

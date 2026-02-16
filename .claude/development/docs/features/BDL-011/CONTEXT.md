# CONTEXT: BDL-011 — Plug & Play Onboarding

> **Last updated:** 2026-02-16
> **Phase:** COMPLETE — delivered in v1.3.0
> **Epic:** BDL-011

---

## Goal

Transform `beadloom init --bootstrap` into a full Plug & Play setup:
graph + rules + doc skeletons + MCP config in one command.
Target: 5 minutes from install to first useful result.

## Decisions

| # | Decision | Status |
|---|----------|--------|
| D1 | `doc_generator.py` — new file in `onboarding/` | Approved |
| D2 | `docs` as Click group | Approved |
| D3 | Root node created during bootstrap | Approved |
| D4 | Skeleton docs with `<!-- enrich -->` markers | Approved |
| D5 | MCP default = claude-code format | Approved |
| D6 | `generate_polish_data()` returns prompt in `instructions` | Approved |
| D7 | Never overwrite existing files | Approved |
| D8 | Dogfooding wave as mandatory final step | Approved |

## Key Files

### Modify
- `src/beadloom/onboarding/scanner.py` — `bootstrap_project()`, `generate_rules()`, `setup_mcp_auto()`, `_detect_project_name()`
- `src/beadloom/onboarding/__init__.py` — re-exports
- `src/beadloom/services/cli.py` — `docs generate`, `docs polish`, enhanced `init` output
- `src/beadloom/services/mcp_server.py` — `generate_docs` tool

### Create
- `src/beadloom/onboarding/doc_generator.py` — `generate_skeletons()`, `generate_polish_data()`

### Tests
- `tests/test_doc_generator.py` — unit tests for doc_generator
- `tests/test_rules_generation.py` — unit tests for auto-rules
- `tests/test_mcp_auto.py` — unit tests for MCP auto-config
- `tests/test_integration_v1.py` — extend integration tests

### Update (Wave 5)
- `.beadloom/_graph/services.yml` — new nodes/edges
- `docs/domains/onboarding/README.md` — add doc_generator
- `docs/services/cli.md` — +2 commands
- `docs/services/mcp.md` — +1 tool
- `CHANGELOG.md` — new entry

## Code Standards

### Language and environment
- **Language:** Python 3.10+ (type hints, `str | None` syntax)
- **Package manager:** uv
- **Virtual environment:** uv venv

### Methodologies
| Methodology | Application |
|-------------|-------------|
| TDD | Red → Green → Refactor for each bead |
| Clean Code | snake_case, SRP, DRY, KISS |
| Modular architecture | CLI → Core → Storage |

### Testing
- **Framework:** pytest + pytest-cov
- **Coverage:** minimum 80%
- **Fixtures:** conftest.py, tmp_path

### Code quality
- **Linter:** ruff (lint + format)
- **Typing:** mypy --strict

### Restrictions
- [x] No `Any` without justification
- [x] No `print()` / `breakpoint()` — use logging
- [x] No bare `except:` — only `except SpecificError:`
- [x] No `os.path` — use `pathlib.Path`
- [x] No f-strings in SQL — parameterized queries `?`
- [x] No `yaml.load()` — only `yaml.safe_load()`
- [x] No magic numbers — extract into constants

## Related Documents
- [PRD](PRD.md)
- [RFC](RFC.md)
- [PLAN](PLAN.md)

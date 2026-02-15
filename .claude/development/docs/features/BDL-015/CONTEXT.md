# BDL-015: Beadloom v1.5 — Context

## Status
- **Phase:** Planning
- **Current bead:** —
- **Blockers:** none

## Goal (immutable)
Solve three critical problems in one release: shallow bootstrap, broken doc sync, and limited language support.

## Key constraints
- No external API dependencies (deterministic, local-first)
- No breaking changes to existing CLI/MCP interfaces
- tree-sitter grammars via pip packages (optional deps)
- All tests must pass, coverage >=80%
- Phase 8, 8.5, 9 run in parallel (no cross-phase dependencies)

## Code standards

### Language and environment
- **Language:** Python 3.10+ (type hints, `str | None` syntax)
- **Package manager:** uv
- **Virtual environment:** uv venv

### Methodologies
| Methodology | Application |
|-------------|-------------|
| TDD | Red -> Green -> Refactor for each bead |
| Clean Code | Naming (snake_case), SRP, DRY, KISS |
| DDD architecture | Services -> Domains -> Infrastructure |

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

## Key files

### Phase 8 (Smart Bootstrap)
- `src/beadloom/onboarding/scanner.py` — bootstrap_project(), _detect_framework_summary(), generate_rules()
- `src/beadloom/onboarding/presets.py` — detect_preset(), Preset dataclass
- `src/beadloom/onboarding/doc_generator.py` — generate_polish_data(), generate_skeletons()
- `src/beadloom/graph/import_resolver.py` — extract_imports(), index_imports()

### Phase 8.5 (Doc Sync v2)
- `src/beadloom/doc_sync/engine.py` — check_sync()
- `src/beadloom/infrastructure/doctor.py` — run_doctor()
- `src/beadloom/infrastructure/reindex.py` — incremental_reindex()
- `src/beadloom/onboarding/setup_rules.py` — setup_rules_auto()
- `src/beadloom/context_oracle/code_indexer.py` — extract_symbols()

### Phase 9 (Languages)
- `src/beadloom/context_oracle/code_indexer.py` — _EXTENSION_LOADERS, LangConfig, _load_*()
- `src/beadloom/infrastructure/reindex.py` — _CODE_EXTENSIONS
- `src/beadloom/graph/import_resolver.py` — _extract_*_imports()
- `pyproject.toml` — [project.optional-dependencies.languages]

## Current stack/dependencies
- Python 3.10+, SQLite (WAL), Click, Rich, PyYAML, tree-sitter
- tree-sitter-python (core), tree-sitter-{typescript,go,rust} (optional)

## Last updated
- **Date:** 2026-02-15
- **Agent:** Coordinator
- **Changes:** Initial context creation

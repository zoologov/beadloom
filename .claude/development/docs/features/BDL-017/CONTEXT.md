# BDL-017: Beadloom v1.6 — Context

## Status
- **Phase:** Approved — ready for development
- **Current bead:** — (none started)
- **Blockers:** none
- **Target version:** 1.6.0

## Goal (immutable)
Enrich graph nodes with runtime context (API routes, git activity, test mapping), expose validation tools to agents via MCP, and add rule severity levels for gradual adoption.

## Key constraints
- No external API dependencies (deterministic, local-first)
- No breaking changes to existing CLI/MCP interfaces
- `rules.yml` v1 → v2 must be backward compatible
- All new data in `nodes.extra` JSON (no new DB tables)
- Git analysis gracefully degrades if not a git repo
- All tests must pass, coverage >=80%
- Phase 10 and Phase 11 are independent (can parallelize)

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

### Phase 10 (Deep Code Analysis)
- `src/beadloom/context_oracle/code_indexer.py` — extract_symbols(), LangConfig, _EXTENSION_LOADERS
- `src/beadloom/onboarding/scanner.py` — _detect_framework_summary(), bootstrap_project(), scan_project()
- `src/beadloom/onboarding/doc_generator.py` — generate_polish_data(), _detect_symbol_changes()
- `src/beadloom/graph/rule_engine.py` — DenyRule, RequireRule, Violation, evaluate_rules()
- `src/beadloom/graph/linter.py` — lint(), LintResult
- `src/beadloom/infrastructure/db.py` — schema (nodes.extra, code_symbols, rules)
- `src/beadloom/infrastructure/reindex.py` — incremental_reindex(), _index_code_symbols()
- `src/beadloom/context_oracle/builder.py` — build_context_bundle()

### Phase 10 (New files)
- `src/beadloom/context_oracle/route_extractor.py` — Route, extract_routes()
- `src/beadloom/infrastructure/git_activity.py` — GitActivity, analyze_git_activity()
- `src/beadloom/context_oracle/test_mapper.py` — TestMapping, map_tests()

### Phase 11 (Agent Infrastructure)
- `src/beadloom/services/mcp_server.py` — MCP tools, _TOOLS, call_tool()
- `src/beadloom/services/cli.py` — lint(), why(), diff_cmd(), status()
- `src/beadloom/onboarding/scanner.py` — config reading during bootstrap

### Phase 11 (New files)
- `src/beadloom/onboarding/config_reader.py` — read_deep_config()

## Dependencies between phases
```
Phase 10:
  10.1 (API routes)      — independent
  10.2 (Git activity)    — independent
  10.3 (Test mapping)    — independent
  10.4 (Rule severity)   — independent
  10.5 (Smart polish)    — depends on 10.1 + 10.2 + 10.3

Phase 11:
  11.1 (MCP lint)        — depends on 10.4 (severity in JSON output)
  11.2 (MCP why)         — independent
  11.3 (MCP diff)        — independent
  11.4 (Cost metrics)    — independent
  11.5 (Deep config)     — independent
```

## Current stack/dependencies
- Python 3.10+, SQLite (WAL), Click, Rich, PyYAML, tree-sitter
- tree-sitter-python (core), tree-sitter-{typescript,go,rust,kotlin,java,swift,c,cpp,objc} (optional)

## Last updated
- **Date:** 2026-02-16
- **Agent:** Coordinator
- **Changes:** Initial context created

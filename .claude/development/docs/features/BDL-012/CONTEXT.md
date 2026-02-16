# BDL-012 CONTEXT — Onboarding Quality Bug-fixes

> **Phase:** COMPLETE — 10 bug-fixes delivered in v1.3.1
> **Last updated:** 2026-02-16

## Goal

Fix 10 UX issues from dogfooding `beadloom init --bootstrap` on cdeep (Django+Vue, 44 nodes) and dreamteam (React Native+TS, 6 nodes). After fixes: `doctor` 0 warnings, `lint` 0 false positives, skeletons contain real data.

## Constraints

- No new CLI commands or MCP tools
- No new SQLite tables
- All 756+ existing tests must pass
- Each fix gets its own test(s)
- Backward-compatible: existing graphs must continue to work

## Code Standards

### Language and Environment
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

### Code Quality
- **Linter:** ruff (lint + format)
- **Typing:** mypy --strict

### Restrictions
- [x] No `Any` without justification
- [x] No `print()` / `breakpoint()` — use logging
- [x] No bare `except:` — only specific exceptions
- [x] No `os.path` — use `pathlib.Path`
- [x] No f-strings in SQL — parameterized queries `?`
- [x] No `yaml.load()` — only `yaml.safe_load()`

## Key Files

| File | Purpose |
|------|---------|
| `src/beadloom/onboarding/doc_generator.py` | Skeleton generation, polish data |
| `src/beadloom/onboarding/scanner.py` | Bootstrap, rule generation, summaries |
| `src/beadloom/onboarding/presets.py` | Preset auto-detection |
| `src/beadloom/graph/rule_engine.py` | Lint rule engine, NodeMatcher |
| `src/beadloom/context_oracle/code_indexer.py` | Language parser detection |
| `src/beadloom/infrastructure/reindex.py` | Incremental reindex logic |
| `src/beadloom/services/cli.py` | CLI handlers |
| `tests/test_doc_generator.py` | Doc generator tests |
| `tests/test_scanner.py` | Scanner/bootstrap tests |
| `tests/test_rule_engine.py` | Rule engine tests |
| `tests/test_integration_onboarding.py` | Integration tests |

## Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | Use empty NodeMatcher `{}` for "any node" | Already works in `matches()`, minimal code change |
| D2 | Don't fix skeleton deps (#7) — fix polish instead | Skeletons run before reindex; deps don't exist yet |
| D3 | Check `app.json` content, not just existence (#14) | Avoids false positives on non-mobile projects |
| D4 | Strip parens from ref_ids (#10) at generation time | Don't break existing graphs |

## UX Feedback

See `.claude/development/docs/features/BDL-011/BDL-UX-Issues.md`

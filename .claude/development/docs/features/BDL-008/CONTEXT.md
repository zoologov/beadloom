# CONTEXT: BDL-008 — Eat Your Own Dogfood

> **Status:** COMPLETE — DDD restructuring delivered in v1.2.0
> **Epic:** BDL-008
> **PRD:** Approved | **RFC:** Approved

---

## Goal

Transform the Beadloom repository into a showcase of its own product:
1. Code → DDD domain packages
2. Docs → domain-first layout
3. `.beadloom/_graph/` → self-describing knowledge graph

## Current state

- **Code:** 23 flat modules in `src/beadloom/`, 14 annotated domains but no directory structure
- **Docs:** 8 flat files in `docs/`, 6 CLI commands undocumented, MCP docs stale
- **Graph:** `.beadloom/_graph/` exists with 11 nodes but outdated (says 5 MCP tools / 12 commands)
- **Entry point:** `beadloom.cli:main` (pyproject.toml) — must remain unchanged

## Key decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D1 | No backward-compatible re-exports | Internal API only; all consumers in-repo |
| D2 | Services stay at top level | Orchestrators, not domain logic; cli.py is entry point |
| D3 | git mv for moves | Preserve blame/log history |
| D4 | One commit per domain migration | Easy bisect/revert |
| D5 | Leaf-to-root migration order | Avoids circular dependency issues |

## Dependency graph (import analysis)

```
Self-contained (safe to move first):
  db, health, code_indexer, search, doc_indexer, sync_engine,
  presets, graph_loader, diff, rule_engine, doctor, watcher

One dependency:
  cache → db
  context_builder → db
  onboarding → presets
  why → context_builder

Multiple dependencies:
  reindex → db, code_indexer, doc_indexer, graph_loader, health
  linter → db, reindex, rule_engine
  import_resolver → code_indexer, reindex
  mcp_server → cache, context_builder, db, graph_loader, reindex, sync_engine
  cli → (everything)
```

## Code standards

### Language and environment
- **Language:** Python 3.10+ (type hints, `str | None` syntax)
- **Package manager:** uv
- **Virtual environment:** uv venv

### Methodologies
| Methodology | Application |
|-------------|-------------|
| TDD | Red → Green → Refactor for each bead |
| Clean Code | snake_case, SRP, DRY, KISS |
| Modular architecture | domains → infra → services |

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

## Validation checklist (run after each bead)

```bash
uv run pytest                    # tests pass
uv run mypy --strict             # type check
uv run ruff check src/           # lint
uv run ruff format --check src/  # format
```

# CONTEXT: BDL-001 — Beadloom v0

> **Last updated:** 2026-02-16
> **Phase:** 0 → 1 → 2 → 3 (Onboarding → Context Oracle → MCP → Doc Sync)
> **Status:** COMPLETE — delivered as v0.2.0

---

## Goal

Beadloom is a local CLI tool + MCP server for AI-assisted development:
- **Context Oracle** — instant delivery of context bundles by ref_id
- **Doc Sync Engine** — tracking doc↔code relationships, staleness detection

## Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.10+ (type hints, `str \| None` syntax) |
| Package manager | uv |
| CLI | Click + Rich |
| Code parsing | tree-sitter |
| Storage | SQLite (WAL mode) |
| Agent protocol | MCP (stdio transport) |
| Distribution | PyPI (`uv tool install beadloom`) |

## Code Standards

### Methodologies

| Methodology | Application |
|-------------|------------|
| TDD | Red → Green → Refactor for each bead |
| Clean Code | Naming (snake_case), SRP, DRY, KISS |
| Modular architecture | CLI → Core → Storage, dependencies point inward |

### Testing

- **Framework:** pytest + pytest-cov
- **Coverage:** minimum 80%
- **Fixtures:** conftest.py, tmp_path

### Code Quality

- **Linter:** ruff (lint + format)
- **Type checking:** mypy --strict

### Restrictions

- [x] No `Any` without justification
- [x] No `print()` / `breakpoint()` — use logging / Rich console
- [x] No bare `except:` — only `except SpecificError:`
- [x] No `os.path` — use `pathlib.Path`
- [x] No f-strings in SQL — use parameterized queries `?`
- [x] No `yaml.load()` — only `yaml.safe_load()`
- [x] No magic numbers — extract into constants
- [x] No `import *`
- [x] No mutable default arguments (`def f(x=[]):`)

## Architecture

```
src/beadloom/
├── __init__.py          # version
├── cli.py               # Click entry point
├── db.py                # SQLite connection + schema
├── graph_loader.py      # YAML → SQLite (nodes, edges)
├── doc_indexer.py        # Markdown → chunks
├── code_indexer.py       # tree-sitter → code_symbols
├── context_builder.py   # BFS + bundle assembly
├── sync_engine.py       # doc↔code sync tracking
├── mcp_server.py        # MCP tools (stdio)
├── onboarding.py        # init/bootstrap/import
└── doctor.py            # validation checks
```

## Key Decisions

| Decision | Reason |
|---------|---------|
| `ref_id` as PK (not composite) | Simple edges, unambiguous SQL queries |
| SQLite WAL mode | Concurrent reads from CLI + MCP |
| YAML in Git as source of truth | Versioning, review via PR |
| Deterministic BFS (no LLM) | Predictability, speed, 0 external dependencies |
| MCP stdio (not HTTP) | Native integration with Claude Code, no ports |
| drop + re-create on reindex (v0) | Simplicity, incremental — phase 4 |

## Related Files

| File | Purpose |
|------|-----------|
| `.claude/development/PRD.md` | Requirements (approved) |
| `.claude/development/RFC.md` | Technical solution (approved) |
| `.claude/development/docs/features/BDL-001/PLAN.md` | DAG beads |
| `pyproject.toml` | Project configuration |
| `src/beadloom/` | Source code |
| `tests/` | Tests |

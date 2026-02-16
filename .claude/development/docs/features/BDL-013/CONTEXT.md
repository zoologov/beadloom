# CONTEXT: BDL-013 — Dogfood Beadloom + Agent Instructions + CI

> **Status:** COMPLETE — dogfooding + CI + agent instructions delivered
> **Epic:** BDL-013
> **Date:** 2026-02-14
> **Last updated:** 2026-02-16

---

## Goal

Make Beadloom eat its own dogfood: use its own AaC lint, doc-sync, and
architecture graph during development. Update agent instructions so they
survive `/compact` and use Beadloom dynamically instead of hardcoded paths.
Add CI enforcement.

---

## Key Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Delete AGENTS.md, single source of truth in `.claude/` | Avoids triple maintenance, survives `/compact` |
| 2 | Replace static file trees in skills with `beadloom graph`/`ctx` | Always accurate, first dogfood use case |
| 3 | Pre-commit hook mode: `warn` (not `block`) | Advisory for now, less friction |
| 4 | AaC lint CI: separate workflow, single Python version | Different concern from tests, fast (~2s) |
| 5 | Tests CI: path filters for `src/`, `tests/`, `pyproject.toml` | Skip on docs-only changes, save CI minutes |
| 6 | Generate `.beadloom/README.md` during init | Parity with `.beads/README.md`, AI Agent Native branding |
| 7 | Skills: HOW (static) vs WHAT (dynamic from Beadloom) | Methodology rarely changes; structure changes on every refactor |

---

## Current State (v1.3.1)

- **Graph:** 19 nodes, 56 edges, 100% doc coverage, 0 stale docs
- **Lint:** 0 violations, 2 rules (domain-needs-parent, feature-needs-domain)
- **Doctor:** All checks pass
- **Pre-commit:** Not installed (config exists: `sync.hook_mode: warn`)
- **CI:** tests.yml only (ruff + mypy + pytest), no beadloom commands
- **Agent instructions:** Beads-only in `.claude/`, Beadloom only in AGENTS.md (stale)

---

## Code Standards

### Language and Environment
- **Language:** Python 3.10+ (type hints, `str | None` syntax)
- **Package manager:** uv
- **Virtual environment:** uv venv

### Methodologies
| Methodology | Application |
|-------------|-------------|
| TDD | Red -> Green -> Refactor for each bead |
| Clean Code | Naming (snake_case), SRP, DRY, KISS |
| Modular architecture | Services -> Domains -> Infrastructure |

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
- [x] No bare `except:` — only `except SpecificError:`
- [x] No `os.path` — use `pathlib.Path`
- [x] No f-strings in SQL — parameterized queries `?`
- [x] No `yaml.load()` — only `yaml.safe_load()`

---

## Related Files

### Documents
- `BDL-013/PRD.md` — requirements (approved)
- `BDL-013/RFC.md` — technical solution (approved)
- `BDL-013/PLAN.md` — bead DAG
- `BDL-013/ACTIVE.md` — current progress

### Code (changes expected)
- `src/beadloom/onboarding/doc_generator.py` — D12: add README.md generation
- `tests/test_doc_generator.py` — D12: test for README.md
- `.beadloom/_graph/rules.yml` — D10: expand rules
- `.beadloom/_graph/services.yml` — D11: fix edges if needed
- `.github/workflows/beadloom-aac-lint.yml` — D1: new workflow
- `.github/workflows/tests.yml` — D2: add path filters
- `.claude/CLAUDE.md` — D3: add Beadloom section
- `.claude/commands/dev.md` — D4: dynamic structure + workflow
- `.claude/commands/review.md` — D5: Beadloom checklist
- `.claude/commands/test.md` — D6: dynamic structure
- `.claude/commands/coordinator.md` — D7: wave validation
- `AGENTS.md` — D8: delete
- `.beadloom/README.md` — D12: create

---

## Known Issues

1. **Reverse edges in graph:** `infrastructure` has `depends_on` edges to
   `beadloom`, `context-oracle`, `doc-sync`, `graph`. Likely from `reindex`
   feature imports. Investigate in D11.
2. **AGENTS.md file paths outdated:** References `cli.py`, `sync_engine.py`
   (flat) instead of `services/cli.py`, `doc_sync/engine.py` (DDD).
3. **Skills fictional structure:** `/dev` and `/test` describe nonexistent
   `cli/main.py`, `core/graph.py`, `storage/database.py` etc.

# CONTEXT: BDL-007 — Architecture as Code & Ecosystem (v1.0)

> **Phase:** 6
> **Version:** 1.0.0
> **RFC:** RFC-0007
> **Status:** Completed

---

## 1. Goal

Transform Beadloom from architecture documentation into an **Architecture as Code** platform: describe → validate → deliver → keep in sync.

**Deliverables:**
1. `beadloom lint` — validates code imports against graph boundaries
2. `rules.yml` — declarative YAML constraint language (deny/require)
3. Agent-aware constraints — MCP `get_context` returns active rules
4. CI architecture gate — `beadloom lint --strict` for pipelines

---

## 2. Scope Boundaries

### In scope
- Import detection via tree-sitter (Python, TS/JS, Go, Rust)
- YAML deny/require rules (`rules.yml`)
- Lint CLI command with 3 output formats
- Context bundle v2 with constraints field
- CI integration recipes (GitHub Actions, GitLab CI)

### Out of scope
- Multi-repo federated graphs (6.5)
- Plugin system (6.6)
- Web dashboard (6.7)
- Rule severity levels / tags
- DSL-based rules (OPA/Rego)
- Re-export / alias resolution

---

## 3. Key Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Rule format | YAML deny/require | Simple, PR-reviewable, covers 80% |
| Import detection | tree-sitter AST | Already in stack, multi-language |
| Import storage | Separate `code_imports` table | Derived data, independent lifecycle |
| Node mapping | Annotations primary, file path fallback | Deterministic, leverages existing system |
| Context version | Bump to v2 | Additive, backward compatible |
| Schema version | Bump to 2 | New tables only, no migration |

---

## 4. Key Files

### New modules
| File | Purpose |
|------|---------|
| `src/beadloom/import_resolver.py` | Import extraction + graph node resolution |
| `src/beadloom/rule_engine.py` | Rules parser, validator, evaluator |
| `src/beadloom/linter.py` | Lint orchestrator + output formatters |

### Modified modules
| File | Changes |
|------|---------|
| `src/beadloom/db.py` | +`code_imports` table, +`rules` table, SCHEMA_VERSION="2" |
| `src/beadloom/reindex.py` | +import extraction step, +rules loading step |
| `src/beadloom/context_builder.py` | +`constraints` field in bundle, version bump |
| `src/beadloom/mcp_server.py` | +`lint` MCP tool, updated `get_context` description |
| `src/beadloom/cli.py` | +`lint` command |
| `src/beadloom/graph_loader.py` | Load `rules.yml` alongside graph YAML |

### Test files
| File | Bead |
|------|------|
| `tests/test_import_resolver.py` | 6.1a |
| `tests/test_rule_engine.py` | 6.1b |
| `tests/test_linter.py` | 6.1c |
| `tests/test_cli_lint.py` | 6.2 |
| `tests/test_constraints.py` | 6.3 |

### Config files
| File | Purpose |
|------|---------|
| `.beadloom/_graph/rules.yml` | Architecture rules definition |

---

## 5. Code Standards

### Language and environment
- **Language:** Python 3.10+ (type hints, `str | None` syntax)
- **Package manager:** uv
- **Virtual environment:** uv venv

### Methodologies
| Methodology | Application |
|-------------|-------------|
| TDD | Red → Green → Refactor for each bead |
| Clean Code | snake_case, SRP, DRY, KISS |
| Modular architecture | CLI → Core → Storage, dependencies inward |

### Testing
- **Framework:** pytest + pytest-cov
- **Coverage:** minimum 80%
- **Fixtures:** conftest.py, tmp_path
- **Target:** >= 85 new tests, total >= 620

### Code quality
- **Linter:** ruff (lint + format)
- **Typing:** mypy --strict

### Restrictions
- [x] No `Any` without justification
- [x] No `print()` / `breakpoint()` — use Rich console
- [x] No bare `except:` — only `except SpecificError:`
- [x] No `os.path` — use `pathlib.Path`
- [x] No f-strings in SQL — parameterized queries `?`
- [x] No `yaml.load()` — only `yaml.safe_load()`
- [x] No magic numbers — extract into constants

---

## 6. Dependencies & Integration Points

### Internal dependencies
- `code_indexer.py` — tree-sitter `LangConfig` (extend for import node types)
- `graph_loader.py` — YAML parsing (reuse for `rules.yml`)
- `db.py` — schema (add tables)
- `reindex.py` — pipeline (add import + rules steps)
- `context_builder.py` — bundle (add constraints)
- `mcp_server.py` — tool dispatch (add lint tool)

### External dependencies
- **No new dependencies** — tree-sitter already in stack
- tree-sitter grammars: Python (required), TS/Go/Rust (optional extras)

### Backward compatibility
- Projects without `rules.yml` → lint reports "no rules, 0 violations"
- Context bundle v1 consumers → `constraints` field is new, ignore if unknown
- Schema v1 databases → new tables added on next reindex via `IF NOT EXISTS`

---

## 7. Final State

- **Version:** 1.0.0
- **Tests:** 653 passing (112 new for Phase 6)
- **New modules:** import_resolver.py (404 lines), rule_engine.py (555 lines), linter.py (260 lines)
- **New CLI command:** `beadloom lint` (--format, --strict, --no-reindex)
- **DB schema:** v2 (+code_imports, +rules tables)
- **Context bundle:** v2 (+constraints field)
- **Self-lint:** clean (0 violations)
- **Quality:** mypy --strict clean, ruff clean

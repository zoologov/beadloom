# PRD: BDL-008 — Eat Your Own Dogfood: DDD Code Structure, Documentation & Knowledge Graph

> **Status:** Approved
> **Epic:** BDL-008

---

## 1. Problem

Beadloom sells three core values:

1. **Domain-first knowledge organization** — a knowledge graph with domains, features, services
2. **Up-to-date documentation** — Doc Sync Engine catches stale docs
3. **Architecture as Code** — boundary rules, lint, validation

But Beadloom itself violates all three:

| What we sell | What we actually have |
|--------------|----------------------|
| Domain-first documentation | Flat list of 8 files in `docs/` |
| DDD code structure | 23 modules in a single flat directory `src/beadloom/` |
| Project knowledge graph | No `.beadloom/_graph/` for ourselves |
| Up-to-date documentation | 6 CLI commands undocumented, MCP docs stale |

**This undermines trust.** A user clones the repo, sees a flat structure and outdated docs, and asks: "If they don't use it themselves, why should I?"

---

## 2. Goal

Make the Beadloom repository a **showcase of its own product**:

- Code organized by DDD domains → user sees how it looks in practice
- Documentation in domain-first layout → user sees a live example from the README
- `.beadloom/_graph/` describes Beadloom itself → `beadloom ctx` works on its own repo
- All docs up to date → `beadloom sync-check` passes with zero warnings

---

## 3. Scope

### 3.1 Code restructuring (DDD directories)

**Current:**
```
src/beadloom/
├── __init__.py
├── cache.py
├── cli.py
├── code_indexer.py
├── context_builder.py
├── db.py
├── diff.py
├── doc_indexer.py
├── doctor.py
├── graph_loader.py
├── health.py
├── import_resolver.py
├── linter.py
├── mcp_server.py
├── onboarding.py
├── presets.py
├── reindex.py
├── rule_engine.py
├── search.py
├── sync_engine.py
├── watcher.py
├── why.py
└── tui/
```

**Target** (grouped by domains):
```
src/beadloom/
├── __init__.py
├── context/                    # domain: context-oracle
│   ├── __init__.py
│   ├── builder.py              # ← context_builder.py
│   ├── code_indexer.py
│   ├── cache.py
│   └── search.py
├── graph/                      # domain: graph
│   ├── __init__.py
│   ├── loader.py               # ← graph_loader.py
│   ├── diff.py
│   ├── rule_engine.py
│   ├── import_resolver.py
│   └── linter.py
├── sync/                       # domain: doc-sync
│   ├── __init__.py
│   ├── engine.py               # ← sync_engine.py
│   └── doc_indexer.py
├── onboarding/                 # domain: onboarding
│   ├── __init__.py
│   ├── scanner.py              # ← onboarding.py
│   └── presets.py
├── infra/                      # shared infrastructure
│   ├── __init__.py
│   ├── db.py
│   ├── health.py
│   └── reindex.py
├── cli.py                      # service: CLI (entry point)
├── mcp_server.py               # service: MCP
├── doctor.py                   # service: diagnostics
├── why.py                      # service: impact analysis
├── watcher.py                  # service: file watcher
└── tui/                        # service: TUI
```

**Requirements:**
- All imports updated
- Backward compatibility: re-exports from old paths NOT needed (internal API)
- Tests pass
- mypy --strict passes
- ruff check/format pass

### 3.2 Documentation restructuring (domain-first)

**Current:** 8 flat files in `docs/`

**Target:**
```
docs/
├── architecture.md                 # system overview (updated)
├── getting-started.md              # quickstart (updated)
├── domains/
│   ├── context-oracle/
│   │   ├── README.md               # BFS, bundle, cache
│   │   ├── search.md               # FTS5 search
│   │   └── impact-analysis.md      # beadloom why
│   ├── doc-sync/
│   │   └── README.md               # sync engine, staleness
│   ├── graph/
│   │   ├── README.md               # YAML format, loader
│   │   ├── diff.md                 # graph diff
│   │   └── rules.md               # architecture rules, lint
│   ├── onboarding/
│   │   └── README.md               # bootstrap, import, presets
│   └── infrastructure/
│       └── README.md               # DB, health, reindex
├── services/
│   ├── cli.md                      # CLI reference (all 18 commands)
│   ├── mcp.md                      # MCP server (all 7+ tools)
│   └── tui.md                      # TUI dashboard
├── guides/
│   └── ci-setup.md                 # CI/CD integration
└── decisions/                      # ADR (future)
```

**Requirements:**
- All content from existing docs migrated and updated
- Undocumented features documented (search, why, diff, ui, watch, lint)
- MCP docs updated (7 tools, cache, auto-reindex)
- Links in README.md and README.ru.md updated
- "Documentation structure" block in README reflects reality

### 3.3 Self-bootstrap (Beadloom on itself)

- Run `beadloom init --bootstrap` on our own repo
- Create/refine `.beadloom/_graph/` with real architecture
- Nodes for all 14 domains + 3 services
- Edges: part_of, uses, depends_on
- Doc-to-node bindings
- `beadloom reindex` + `beadloom ctx` works
- `beadloom sync-check` passes
- `beadloom lint` passes (with rules.yml)

---

## 4. Out of scope

- New CLI/MCP functionality (only documenting what exists)
- Public API changes
- Test framework changes
- Build system migration

---

## 5. Success metrics

| Metric | Target |
|--------|--------|
| `beadloom doctor` | 0 errors |
| `beadloom sync-check` | 0 stale docs |
| `beadloom lint` | 0 violations |
| `uv run pytest` | all pass, >=80% coverage |
| `uv run mypy --strict` | 0 errors |
| `uv run ruff check src/` | 0 errors |
| CLI commands documented | 18/18 |
| MCP tools documented | 7+/7+ |

---

## 6. Risks

| Risk | Mitigation |
|------|------------|
| Mass import refactoring breaks tests | Incremental: one domain at a time, tests after each |
| Moving docs breaks external links | No published docs site; only README links |
| Large volume of work | Split into independent beads, parallelize |
| Self-bootstrap may reveal bugs | This is a plus — we find and fix them |

---

## 7. User Stories

1. **As a user** cloning the repo, I want to see domain-first code and documentation structure, to understand how a project following Beadloom's ideology looks in practice.

2. **As a Beadloom developer**, I want `beadloom ctx CONTEXT-ORACLE` to give me context about our own code, so I don't have to search manually.

3. **As a potential user** reading docs, I want to see up-to-date documentation for all 18 CLI commands and 7+ MCP tools.

4. **As a contributor**, I want `src/beadloom/` structure to reflect domains rather than being a flat list, so I know where to add code.

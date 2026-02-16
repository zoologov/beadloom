# PRD: BDL-011 — Plug & Play Onboarding

> **Epic:** BDL-011
> **Status:** Complete (delivered in v1.3.0)
> **Author:** v.zoologov + Claude
> **Date:** 2026-02-13

---

## 1. Problem Statement

Beadloom's current onboarding path requires too many manual steps between installation and first useful result:

```
Current path (7+ minutes, high friction):
1. uv tool install beadloom              ← ok
2. beadloom init --bootstrap             ← graph only, no docs, no rules
3. beadloom reindex                      ← empty index, no visible value
4. Manually create .mcp.json             ← user must know format + path
5. Manually write documentation          ← defeats purpose of the tool
6. Manually write rules.yml              ← advanced, no guidance
7. Finally: lint works, context is useful ← "wow moment" too late
```

**80% of potential users drop off before reaching value.** The "wow moment" (working lint + rich context bundles) comes only after step 6-7.

## 2. Goal

**5 minutes from `pip install` to first useful result:**

```
Target path (3 steps, <5 min):
1. uv tool install beadloom
2. cd my-project
3. beadloom init --bootstrap
   → graph ✓ rules ✓ doc skeletons ✓ MCP config ✓
   → "beadloom lint: 0 violations, 2 rules evaluated"
   → "Run 'beadloom docs polish' with your AI agent for richer docs"
```

## 3. User Stories

### US-1: First-time user with existing codebase
> As a developer who just installed beadloom, I want `beadloom init --bootstrap` to produce a working architecture graph **with rules, doc skeletons, and MCP config** so that I can immediately see value without manual setup.

**Acceptance criteria:**
- `beadloom init --bootstrap` creates `rules.yml` with auto-generated rules based on discovered graph structure
- `beadloom init --bootstrap` creates doc skeletons (`docs/domains/<name>/README.md`, `docs/architecture.md`) from graph + tree-sitter analysis
- `beadloom init --bootstrap` creates `.mcp.json` for detected editor (Claude Code by default)
- After init, `beadloom lint` runs and reports results
- After init, `beadloom ctx <any-node>` returns meaningful content (graph + code symbols + doc skeleton)

### US-2: AI-assisted doc polish
> As a developer using an AI agent (Cursor, Claude Code), I want a command that lets my agent enrich auto-generated doc skeletons with human-readable descriptions, so I get 90% docs quality without writing them myself.

**Acceptance criteria:**
- New CLI command: `beadloom docs generate [--project PATH]` — generates standalone doc skeletons
- New CLI command: `beadloom docs polish [--project PATH]` — outputs structured prompt for AI agent to enrich docs
- New MCP tool: `generate_docs` — returns structured data (graph + code analysis) for agent-driven doc enrichment
- Polish flow: agent calls `generate_docs` → receives node summaries + public API + dependencies → generates rich descriptions → calls `update_node` to save

### US-3: Auto-rules from graph structure
> As a developer, I want beadloom to auto-generate architecture rules based on discovered structure, so that `beadloom lint` works out of the box.

**Acceptance criteria:**
- If graph has nodes with `kind: domain`, generate `domain-needs-parent` rule (require domain → part_of root)
- If graph has nodes with `kind: feature`, generate `feature-needs-domain` rule (require feature → part_of domain)
- If graph has nodes with `kind: service`, generate `service-needs-parent` rule (require service → part_of root)
- Generated `rules.yml` includes explanatory comments
- Rules are conservative — only structural integrity, no deny rules by default

### US-4: Auto MCP configuration
> As a developer, I want beadloom to auto-create MCP config so my AI agent connects immediately.

**Acceptance criteria:**
- During `beadloom init`, detect editor: Claude Code (`.claude/` or `CLAUDE.md`), Cursor (`.cursor/`), Windsurf (`.windsurfrules`)
- Create appropriate `.mcp.json` at the correct path
- If no editor detected, create `.mcp.json` in project root (Claude Code format, most universal)
- Print instruction: "MCP configured for [editor]. Restart your editor to connect."

## 4. Scope

### In scope
| Feature | Priority | Description |
|---------|----------|-------------|
| Auto-rules generation | P0 | `rules.yml` from graph structure during `init` |
| Auto MCP config | P0 | `.mcp.json` during `init` |
| Doc skeleton generation | P0 | `docs/` tree from graph + tree-sitter during `init` |
| `beadloom docs generate` CLI | P1 | Standalone doc generation (re-runnable after init) |
| `beadloom docs polish` CLI | P1 | Structured output for AI agent to enrich docs |
| `generate_docs` MCP tool | P1 | Agent-native doc generation data |
| Enhanced `init` output | P2 | Summary with next steps, lint result, MCP status |

### Out of scope
- LLM API calls from beadloom itself (we are agent-native, not LLM-dependent)
- Auto-commit generated docs (user decides when to commit)
- IDE plugins (MCP is our integration layer)
- Auto-update rules when graph changes (future epic)

## 5. Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Steps from install to working lint | 7+ manual | 3 (install → cd → init) |
| Time to first `beadloom ctx` with content | 15+ min | < 5 min |
| Manual files user must create | 3+ (rules, docs, mcp config) | 0 |
| `beadloom lint` works after init | No (no rules.yml) | Yes |
| `beadloom ctx` returns docs after init | No (no docs/) | Yes (skeletons) |

## 6. Design Constraints

1. **No LLM dependency** — standalone mode must work without any AI. Beadloom is agent-native but self-sufficient.
2. **Idempotent** — running `init --bootstrap` twice must not duplicate nodes/edges/rules/docs.
3. **Non-destructive** — never overwrite user-modified files. Check for existing content.
4. **Composable** — each feature (rules, docs, mcp) can be generated independently via separate commands.
5. **Existing presets** — build on `monolith/microservices/monorepo` presets, not replace them.

## 7. User Flow Diagram

```
beadloom init --bootstrap
│
├── 1. Scan project (existing: scanner.py)
│   └── Detect dirs, manifests, preset
│
├── 2. Generate graph (existing: scanner.py)
│   └── services.yml with nodes + edges
│
├── 3. Generate rules (NEW)
│   └── rules.yml based on node kinds
│
├── 4. Generate doc skeletons (NEW)
│   ├── docs/architecture.md
│   ├── docs/domains/<name>/README.md (per domain)
│   └── Based on: graph nodes + tree-sitter symbols
│
├── 5. Configure MCP (NEW)
│   └── .mcp.json for detected editor
│
├── 6. Reindex (existing)
│   └── SQLite populated
│
└── 7. Print summary (NEW)
    ├── "✓ Graph: 12 nodes, 18 edges"
    ├── "✓ Rules: 3 rules in rules.yml"
    ├── "✓ Docs: 8 skeletons generated"
    ├── "✓ MCP: configured for Claude Code"
    ├── "✓ Lint: 0 violations"
    └── "→ Next: run 'beadloom docs polish' with your AI agent"
```

## 8. Dependencies

- Existing: `onboarding/scanner.py`, `onboarding/presets.py`, `graph/rule_engine.py`, `services/cli.py`
- Existing: tree-sitter code indexer (`context_oracle/code_indexer.py`)
- Existing: `setup-mcp` CLI command (already creates .mcp.json per editor)

## 9. Risks

| Risk | Mitigation |
|------|------------|
| Generated doc skeletons are too generic/useless | Include concrete data: public functions, import graph, file counts |
| Rules don't match user's architecture intent | Conservative defaults (structural only), easy to customize |
| MCP config conflicts with existing setup | Check before creating, warn if `.mcp.json` exists |
| Idempotency breaks on re-run | Check file existence, merge rather than overwrite |

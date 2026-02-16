# RFC: BDL-014 — Agent Prime (Cross-IDE Context Injection)

> **Status:** Implemented (v1.4.0)
> **Date:** 2026-02-14

---

## 1. Overview

Add Agent Prime mechanism — a single entry point for AI agents to get project context, working identically across all IDEs via a three-layer architecture: AGENTS.md (static) → IDE adapters (pointers) → `beadloom prime` (dynamic).

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Agent (any IDE)                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ① IDE loads rules file                                    │
│     .cursorrules / .windsurfrules / .clinerules             │
│     → "Read .beadloom/AGENTS.md"                           │
│                                                             │
│  ② Agent reads .beadloom/AGENTS.md                         │
│     → Instructions + MCP tools + rules                     │
│     → "Call prime tool at session start"                    │
│                                                             │
│  ③ Agent calls MCP prime (or CLI beadloom prime)           │
│     → Dynamic context: status, stale, violations           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Data flows

```
beadloom init --bootstrap
  ├── bootstrap_project()        (existing)
  ├── generate_agents_md()       (enhanced — D3)
  ├── setup_mcp_auto()           (existing)
  └── setup_rules_auto()         (new — D4)

beadloom prime [--json] [--update]
  ├── read .beadloom/AGENTS.md   (static instructions)
  ├── query SQLite DB            (nodes, edges, stale, symbols)
  ├── read rules.yml             (architecture rules)
  └── format output              (markdown or JSON)

beadloom setup-rules [--tool cursor|windsurf|cline]
  ├── detect IDE markers         (reuse _MCP_EDITOR_MARKERS pattern)
  └── write adapter files        (.cursorrules etc.)
```

---

## 3. Deliverables

| ID | Name | Priority | Description |
|----|------|----------|-------------|
| D1 | `prime_context()` core | P0 | Core function to gather project context |
| D2 | `beadloom prime` CLI | P0 | CLI command, calls prime_context() |
| D3 | AGENTS.md v2 | P0 | Enhanced template + generate_agents_md() |
| D4 | `beadloom setup-rules` CLI | P1 | IDE adapter generation |
| D5 | MCP tool `prime` | P1 | 10th MCP tool |
| D6 | Integration into `init --bootstrap` | P1 | setup-rules call during bootstrap |
| D7 | Tests | P0 | Unit + integration for all components |
| D8 | Documentation | P2 | Update docs + .beadloom graph |

---

## 4. Detailed Design

### D1: `prime_context()` — core function

**Location:** `src/beadloom/onboarding/scanner.py`

Next to `generate_agents_md()` — related function. scanner.py already contains all onboarding logic.

```python
def prime_context(
    project_root: Path,
    *,
    fmt: str = "markdown",  # "markdown" | "json"
) -> str | dict[str, Any]:
    """Build compact project context for AI agent injection.

    Works gracefully without DB (static-only mode).
    Target: ≤2000 tokens output.
    """
```

**Algorithm:**

```
1. Static layer (always available):
   ├── Read .beadloom/AGENTS.md → extract instructions
   ├── Read .beadloom/_graph/rules.yml → architecture rules
   └── Read .beadloom/config.yml → project name, preset

2. Dynamic layer (requires DB, graceful degradation):
   ├── Query nodes table → count by kind
   ├── Query sync_pairs → stale docs list
   ├── Run lint evaluation → violations count
   └── Query symbols → total count

3. Format:
   ├── markdown → compact Markdown for LLM injection
   └── json → structured dict for programmatic use
```

**Markdown output format (~1000-1500 tokens):**

```markdown
# Project: beadloom

Architecture: 5 domains, 4 services, 10 features | 239 symbols
Health: 0 stale docs, 0 lint violations | Last reindex: 2026-02-14

## Architecture Rules
- domain-needs-parent (require): Every domain must be part_of the root service
- feature-needs-domain (require): Every feature must be part_of a domain
- service-needs-parent (require): Every service must be part_of the root service
- no-domain-depends-on-service (deny): Domains must not depend_on services

## Key Commands
| Command | Description |
|---------|-------------|
| `beadloom ctx <ref_id>` | Full context bundle for a node |
| `beadloom search "<query>"` | FTS5 search across nodes and docs |
| `beadloom lint --strict` | Architecture boundary validation |
| `beadloom sync-check` | Check doc-code freshness |

## Agent Instructions
- Before work: call `get_context(ref_id)` or `prime` MCP tool
- After code changes: call `sync_check()`, update stale docs
- New features: add `# beadloom:feature=REF_ID` annotations
- Graph changes: run `beadloom reindex` after editing YAML

## Domains
- context-oracle: Context bundle building via BFS traversal
- doc-sync: Doc-code synchronization tracking
- graph: YAML graph format, loader, diff, rule engine
- onboarding: Project bootstrap, presets, doc generation
- infrastructure: SQLite layer, health metrics, reindex

## Stale Docs
(none)

## Lint Violations
(none)
```

**JSON output:**

```json
{
  "project": "beadloom",
  "version": "1.3.1",
  "architecture": {
    "domains": 5,
    "services": 4,
    "features": 10,
    "symbols": 239
  },
  "health": {
    "stale_docs": [],
    "lint_violations": [],
    "last_reindex": "2026-02-14T17:44:41"
  },
  "rules": [
    {"name": "domain-needs-parent", "type": "require", "description": "..."}
  ],
  "domains": [
    {"ref_id": "context-oracle", "summary": "..."}
  ],
  "instructions": "..."
}
```

**Graceful degradation (no DB):**

```markdown
# Project: beadloom

Warning: Database not found. Run `beadloom reindex` for full context.

## Agent Instructions
(from AGENTS.md)

## Architecture Rules
(from rules.yml)
```

---

### D2: `beadloom prime` CLI

**Location:** `src/beadloom/services/cli.py`

```python
@main.command()
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.option("--update", is_flag=True, help="Also regenerate AGENTS.md.")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: cwd).",
)
def prime(*, as_json: bool, update: bool, project: Path | None) -> None:
    """Output compact project context for AI agent injection."""
    project_root = project or Path.cwd()

    if update:
        generate_agents_md(project_root)

    fmt = "json" if as_json else "markdown"
    result = prime_context(project_root, fmt=fmt)

    if as_json:
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        click.echo(result)
```

---

### D3: AGENTS.md v2

**Changes to `generate_agents_md()`:**

1. Reads `rules.yml` → includes architecture rules
2. Reads DB (if available) → includes current MCP tools list
3. Adds instruction "call `prime` at session start"
4. Preserves user-edited sections on regeneration

**Updated template:**

```python
_AGENTS_MD_TEMPLATE_V2 = """\
# Beadloom — Agent Instructions

> Auto-generated by `beadloom init`. Safe to edit.
> Sections below `## Custom` are preserved on regeneration.

## Before starting work

- Call MCP tool `prime` to get current project context
- Or run `beadloom prime` in terminal
- For specific feature/domain: `get_context(ref_id)`
- If no ref_id is given: `list_nodes()` to discover the graph

## After changing code

1. `beadloom reindex` — update the index
2. `beadloom sync-check` — check for stale docs
3. If stale: update docs, then `beadloom reindex` again
4. `beadloom lint --strict` — verify architecture boundaries

## Conventions

- Feature IDs: DOMAIN-NNN (e.g., AUTH-001)
- Annotations: `# beadloom:feature=REF_ID` in code files
- Documentation: `docs/` directory
- Graph YAML: `.beadloom/_graph/`

## Available MCP Tools

| Tool | Description |
|------|-------------|
| `prime` | Compact project context for session start |
| `get_context` | Full context bundle (graph + docs + code) |
| `get_graph` | Subgraph around a node |
| `list_nodes` | List nodes, optionally by kind |
| `sync_check` | Check doc-code freshness |
| `get_status` | Index statistics and coverage |
| `search` | Full-text search across nodes and docs |
| `update_node` | Update node summary or source |
| `mark_synced` | Mark doc-code pair as synchronized |
| `generate_docs` | Enrichment data for AI doc polish |

{rules_section}
## Custom

<!-- Add project-specific instructions below this line -->
"""
```

**Logic for preserving user sections:**

```python
def generate_agents_md(project_root: Path) -> Path:
    agents_path = project_root / ".beadloom" / "AGENTS.md"

    # Preserve user content below ## Custom
    custom_content = ""
    if agents_path.exists():
        text = agents_path.read_text(encoding="utf-8")
        marker = "## Custom"
        idx = text.find(marker)
        if idx != -1:
            custom_content = text[idx + len(marker):]

    # Build rules section from rules.yml
    rules_section = _build_rules_section(project_root)

    # Render template
    content = _AGENTS_MD_TEMPLATE_V2.format(rules_section=rules_section)

    # Append preserved custom content
    if custom_content:
        content = content.rstrip() + "\n" + custom_content

    agents_path.write_text(content, encoding="utf-8")
    return agents_path
```

---

### D4: `beadloom setup-rules` CLI

**Location:** CLI in `cli.py`, logic in `scanner.py`

**IDE adapter format (same for all):**

```
# Beadloom: Architecture-as-Code context
# See .beadloom/AGENTS.md for full agent instructions

Read the file .beadloom/AGENTS.md before starting any work on this project.
It contains architecture rules, available MCP tools, and coding conventions.
```

**Markers and IDE adapter paths:**

```python
_RULES_CONFIGS: dict[str, dict[str, str]] = {
    "cursor": {
        "path": ".cursorrules",
        "marker": ".cursor",
    },
    "windsurf": {
        "path": ".windsurfrules",
        "marker": ".windsurfrules",
    },
    "cline": {
        "path": ".clinerules",
        "marker": ".clinerules",
    },
}
```

**Note:** Claude Code is excluded — it uses `.claude/CLAUDE.md`, and the user decides what goes there. Beadloom should not touch CLAUDE.md.

**Logic for `setup_rules_auto()`:**

```python
def setup_rules_auto(project_root: Path) -> list[str]:
    """Auto-detect IDEs and create adapter files.

    Returns list of created file names.
    """
    created: list[str] = []

    for ide, cfg in _RULES_CONFIGS.items():
        marker_path = project_root / cfg["marker"]
        rules_path = project_root / cfg["path"]

        # Only create if IDE marker exists AND rules file doesn't
        if marker_path.exists() and not rules_path.exists():
            rules_path.write_text(_RULES_ADAPTER_TEMPLATE, encoding="utf-8")
            created.append(cfg["path"])

    return created
```

**CLI command:**

```python
@main.command("setup-rules")
@click.option(
    "--tool",
    "tool_name",
    type=click.Choice(["cursor", "windsurf", "cline"]),
    default=None,
    help="Target IDE (default: auto-detect).",
)
def setup_rules(*, tool_name: str | None, ...) -> None:
    """Create IDE rules files that reference .beadloom/AGENTS.md."""
```

---

### D5: MCP tool `prime`

**Handler:**

```python
def handle_prime(
    conn: sqlite3.Connection,
    project_root: Path,
    *,
    format: str = "json",
) -> dict[str, Any]:
    """Return compact project context for AI agent."""
    result = prime_context(project_root, fmt="json")
    return result  # type: ignore[return-value]
```

**Tool schema:**

```python
mcp.Tool(
    name="prime",
    description=(
        "Get compact project context for session start. "
        "Returns architecture overview, health status, "
        "lint violations, stale docs, and agent instructions. "
        "Call this at the beginning of every session."
    ),
    inputSchema={"type": "object", "properties": {}},
)
```

**Note:** `prime` is the only MCP tool that needs `project_root` in addition to `conn`. Passed via closure in `create_server()` (project_root is already available).

---

### D6: Integration into `init --bootstrap`

**Change in `bootstrap_project()` (scanner.py):**

```python
def bootstrap_project(...) -> dict[str, Any]:
    # ... existing logic ...

    # Generate agent instructions (enhanced v2)
    generate_agents_md(project_root)  # already called, now uses v2 template

    # Setup IDE rules (NEW)
    rules_created = setup_rules_auto(project_root)

    return {
        # ... existing fields ...
        "rules_files": rules_created,  # NEW
    }
```

**Change in `init` CLI output:**

```
IDE rules: .cursorrules (auto-detected Cursor)
```

---

### D7: Tests

| Test | Type | Verifies |
|------|------|----------|
| `test_prime_context_markdown` | Unit | Markdown format, all sections present |
| `test_prime_context_json` | Unit | JSON structure, all fields |
| `test_prime_context_no_db` | Unit | Graceful degradation without DB |
| `test_prime_context_with_stale` | Unit | Stale docs output |
| `test_prime_context_with_violations` | Unit | Lint violations output |
| `test_prime_cli` | Integration | CLI `beadloom prime` exit 0, stdout |
| `test_prime_cli_json` | Integration | CLI `beadloom prime --json` valid JSON |
| `test_prime_cli_update` | Integration | CLI `--update` regenerates AGENTS.md |
| `test_generate_agents_md_v2` | Unit | New template, rules section |
| `test_generate_agents_md_preserves_custom` | Unit | User sections preserved |
| `test_setup_rules_auto_cursor` | Unit | Creates .cursorrules when .cursor marker exists |
| `test_setup_rules_auto_no_marker` | Unit | Does not create without IDE marker |
| `test_setup_rules_no_overwrite` | Unit | Does not overwrite existing file |
| `test_setup_rules_cli` | Integration | CLI `beadloom setup-rules` |
| `test_mcp_prime_tool` | Integration | MCP tool returns valid context |
| `test_init_bootstrap_creates_rules` | Integration | bootstrap calls setup_rules_auto |

---

### D8: Documentation and graph

**Graph:** add feature node `agent-prime` to `onboarding` domain:

```yaml
# .beadloom/_graph/services.yml
- ref_id: agent-prime
  kind: feature
  summary: "Cross-IDE context injection via prime CLI/MCP + AGENTS.md + IDE adapters"
  source: src/beadloom/onboarding/scanner.py

edges:
  - src: agent-prime
    dst: onboarding
    kind: part_of
```

**Docs:** `docs/domains/onboarding/features/agent-prime/SPEC.md`

---

## 5. Dependencies (DAG)

```
D3 (AGENTS.md v2) ──┐
                     ├──→ D1 (prime_context core) ──→ D2 (CLI)
                     │                              └──→ D5 (MCP tool)
D4 (setup-rules) ───┘
                     └──→ D6 (init integration)

D7 (tests) ← depends on all above
D8 (docs) ← depends on all above
```

**Waves:**

```
Wave 1 (parallel): D3 (AGENTS.md v2), D4 (setup-rules)
Wave 2 (depends on W1): D1 (prime_context core)
Wave 3 (parallel, depends on W2): D2 (CLI), D5 (MCP tool), D6 (init integration)
Wave 4 (depends on all): D7 (tests)
Wave 5: D8 (docs)
```

---

## 6. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Prime output too large (>2000 tokens) | Pollutes agent context | Hard limit: truncate domains/rules if >1500 tokens |
| AGENTS.md custom sections lost | User edits destroyed | `## Custom` marker, everything below is preserved |
| IDE adapter conflicts with existing | Overwrites user .cursorrules | Never overwrite, skip + warning |
| Lint/sync-check slow in prime | Delay >500ms | Read results from DB (last reindex), don't re-run lint |

---

## 7. Out of Scope

- Claude Code hooks (documented how to configure, but not written automatically)
- Auto-updating AGENTS.md on every commit
- IDE-specific logic in adapters
- TUI integration

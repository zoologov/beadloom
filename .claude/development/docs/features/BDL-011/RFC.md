# RFC: BDL-011 — Plug & Play Onboarding

> **Epic:** BDL-011
> **Status:** Draft → Pending Approval
> **Author:** v.zoologov + Claude
> **Date:** 2026-02-13
> **Depends on:** PRD BDL-011 (approved)

---

## 1. Overview

Transform `beadloom init --bootstrap` from "graph-only" to "full setup":
graph + rules + doc skeletons + MCP config — all in one command.

Add `beadloom docs generate` / `beadloom docs polish` for standalone and AI-assisted
documentation generation after init.

## 2. Current State (dogfooding analysis)

Running beadloom on itself revealed these UX gaps for a new user:

| What works | What's missing for new users |
|------------|------------------------------|
| `init --bootstrap` creates graph | No `rules.yml` → `lint` has nothing to evaluate |
| `init --bootstrap` creates config.yml | No `.mcp.json` → agent can't connect |
| `init --bootstrap` creates AGENTS.md | No `docs/` → `ctx` returns graph+symbols only |
| `setup-mcp` exists as separate command | User must know it exists and run manually |
| `doctor` checks graph integrity | Doesn't suggest missing rules/docs |

**Key insight from `beadloom ctx onboarding`:** the context bundle is rich (graph, 10+ edges, docs, 146 symbols) — but only because we manually wrote docs. A new user's bundle would be graph + symbols only, with zero documentation chunks.

## 3. Architecture

### 3.1 New module: `onboarding/doc_generator.py`

New file in the `onboarding` domain. Generates doc skeletons from graph + tree-sitter data.

```
src/beadloom/onboarding/
├── __init__.py          # add re-exports
├── scanner.py           # modify: call generate_rules, setup_mcp, generate_docs
├── presets.py           # unchanged
└── doc_generator.py     # NEW: doc skeleton + polish data generation
```

### 3.2 Modified: `onboarding/scanner.py`

Extend `bootstrap_project()` to call three new steps after graph generation:

```python
def bootstrap_project(project_root, *, preset_name=None):
    # ... existing: scan, cluster, write graph, write config, AGENTS.md ...

    # NEW step 3: Generate rules.yml
    if nodes:
        rules_path = graph_dir / "rules.yml"
        if not rules_path.exists():
            generate_rules(nodes, edges, project_name, rules_path)

    # NEW step 4: Generate doc skeletons
    docs_dir = project_root / "docs"
    if not docs_dir.exists():
        from beadloom.onboarding.doc_generator import generate_skeletons
        generate_skeletons(project_root, nodes, edges)

    # NEW step 5: Auto-configure MCP
    setup_mcp_auto(project_root)

    # ... existing: return summary (enhanced with new counts) ...
```

### 3.3 Modified: `services/cli.py`

Two new CLI commands under `docs` group + enhanced `init` output:

```
beadloom docs generate [--project PATH]     # standalone doc skeleton generation
beadloom docs polish [--project PATH]       # structured output for AI agent
```

### 3.4 Modified: `services/mcp_server.py`

One new MCP tool: `generate_docs`.

### 3.5 Domain ownership

All new code belongs to the **onboarding** domain (`# beadloom:domain=onboarding`),
except the MCP tool handler which belongs to **mcp-server** service.

---

## 4. Detailed Design

### 4.1 Auto-rules generation

**Location:** `onboarding/scanner.py` — new function `generate_rules()`

**Algorithm:**

```python
def generate_rules(
    nodes: list[dict],
    edges: list[dict],
    project_name: str,
    rules_path: Path,
) -> int:
    """Generate rules.yml from graph structure. Returns rule count."""
    kinds = {n["kind"] for n in nodes}
    rules: list[dict] = []

    # Find root node: the first node that has no outgoing part_of edge,
    # or the project_name if no such node exists.
    part_of_srcs = {e["src"] for e in edges if e["kind"] == "part_of"}
    root_candidates = [n for n in nodes if n["ref_id"] not in part_of_srcs]
    root_ref_id = root_candidates[0]["ref_id"] if root_candidates else project_name

    # Rule 1: domains must be part_of root
    if "domain" in kinds:
        rules.append({
            "name": "domain-needs-parent",
            "description": f"Every domain must be part_of {root_ref_id}",
            "require": {
                "for": {"kind": "domain"},
                "has_edge_to": {"ref_id": root_ref_id},
                "edge_kind": "part_of",
            },
        })

    # Rule 2: features must be part_of a domain
    if "feature" in kinds:
        rules.append({
            "name": "feature-needs-domain",
            "description": "Every feature must be part_of a domain",
            "require": {
                "for": {"kind": "feature"},
                "has_edge_to": {"kind": "domain"},
                "edge_kind": "part_of",
            },
        })

    # Rule 3: services must be part_of root
    if "service" in kinds:
        rules.append({
            "name": "service-needs-parent",
            "description": f"Every service must be part_of {root_ref_id}",
            "require": {
                "for": {"kind": "service"},
                "has_edge_to": {"ref_id": root_ref_id},
                "edge_kind": "part_of",
            },
        })

    data = {"version": 1, "rules": rules}
    rules_path.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )
    return len(rules)
```

**Edge case:** If bootstrap generates only flat nodes (no root), rules will
still validate structural integrity based on discovered `kind` values. The `root_ref_id`
will be the first node without outgoing `part_of` edges.

**Idempotency:** Only generates if `rules.yml` does not exist.

### 4.2 Doc skeleton generation

**Location:** `onboarding/doc_generator.py` — NEW file

**Input:** project root, graph nodes, edges (from bootstrap or from SQLite DB).

**Output:** Markdown files in `docs/` directory.

#### Skeleton structure

For each node, generate a README.md or SPEC.md based on node kind:

```
docs/
├── architecture.md               # project overview (always generated)
├── domains/
│   └── {domain-name}/
│       └── README.md             # per domain
├── services/
│   └── {service-name}.md         # per service (except root)
└── features/                     # only if features exist
    └── {feature-name}/
        └── SPEC.md               # per feature
```

#### Content generation (standalone, no LLM)

**`architecture.md`:**
```markdown
# {project_name} — Architecture

> Auto-generated by `beadloom docs generate`. Edit to add context.

## Domains

| Domain | Summary | Source |
|--------|---------|--------|
| {ref_id} | {summary} | `{source}` |

## Services

| Service | Summary | Source |
|---------|---------|--------|
| {ref_id} | {summary} | `{source}` |

## Dependency Map

{mermaid diagram from beadloom graph}
```

**`domains/{name}/README.md`:**
```markdown
# {ref_id}

> {summary}

## Source

`{source}`

## Public API

{table of public functions/classes from tree-sitter symbols}

| Symbol | Kind | File |
|--------|------|------|
| {name} | {function/class} | `{file_path}:{line}` |

## Dependencies

- Depends on: {list from edges where src=this, kind=depends_on}
- Used by: {list from edges where dst=this}

## Features

{list of child features if any, from part_of edges}
```

#### Implementation

```python
# onboarding/doc_generator.py

def generate_skeletons(
    project_root: Path,
    nodes: list[dict[str, Any]] | None = None,
    edges: list[dict[str, Any]] | None = None,
) -> dict[str, int]:
    """Generate doc skeletons from graph + code analysis.

    If nodes/edges not provided, reads from SQLite DB (for standalone mode).
    Returns {"files_created": N, "files_skipped": M}.
    """

def generate_polish_data(
    project_root: Path,
    ref_id: str | None = None,
) -> dict[str, Any]:
    """Generate structured data for AI agent to enrich docs.

    Returns dict with:
    - nodes: list of {ref_id, kind, summary, source, symbols, deps, dependents}
    - architecture: {project_name, domains, services, features, mermaid}
    - instructions: str (prompt for the AI agent)

    If ref_id is given, returns data for that node only.
    """
```

**Tree-sitter integration:** Uses existing `code_indexer` to get public symbols.
When called during `bootstrap_project()` (before reindex), symbols are not yet
in SQLite — we call `index_file()` inline for each node's source files.
When called standalone (after reindex), reads symbols from `code_symbols` table.

**Strategy:**
1. During `init --bootstrap`: generate skeletons with basic info (summary, source, edges).
   No tree-sitter yet (reindex hasn't run). Mark with `<!-- enrich with: beadloom docs polish -->`.
2. After `reindex`: `beadloom docs generate` regenerates with full symbol data.
3. `beadloom docs polish`: returns structured data for AI to rewrite in human-readable form.

**Idempotency:** Never overwrites existing files. Counts skipped files in return.

### 4.3 Auto MCP configuration

**Location:** `onboarding/scanner.py` — new function `setup_mcp_auto()`

Reuses logic from `cli.py:setup_mcp` but without Click dependencies:

```python
def setup_mcp_auto(project_root: Path) -> str | None:
    """Auto-detect editor and create MCP config. Returns editor name or None."""
    import shutil

    # Detection order (most specific first)
    detectors = [
        (".cursor", "cursor"),
        (".windsurfrules", "windsurf"),
        (".claude", "claude-code"),
        ("CLAUDE.md", "claude-code"),
    ]

    editor = "claude-code"  # default: most universal
    for marker, name in detectors:
        if (project_root / marker).exists():
            editor = name
            break

    # Path resolution (same as _MCP_TOOL_CONFIGS in cli.py)
    paths = {
        "claude-code": project_root / ".mcp.json",
        "cursor": project_root / ".cursor" / "mcp.json",
        "windsurf": Path.home() / ".codeium" / "windsurf" / "mcp_config.json",
    }
    mcp_path = paths[editor]

    # Don't overwrite existing config
    if mcp_path.exists():
        return None

    mcp_path.parent.mkdir(parents=True, exist_ok=True)

    beadloom_cmd = shutil.which("beadloom") or "beadloom"
    args = ["mcp-serve"]
    if editor == "windsurf":
        args.extend(["--project", str(project_root.resolve())])

    data = {
        "mcpServers": {
            "beadloom": {
                "command": beadloom_cmd,
                "args": args,
            }
        }
    }

    mcp_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return editor
```

**Idempotency:** Only creates if MCP config does not exist.

### 4.4 CLI commands

#### `beadloom docs generate`

```python
@main.group()
def docs():
    """Documentation generation and management."""
    pass

@docs.command("generate")
@click.option("--project", type=click.Path(...), default=None)
def docs_generate(*, project: Path | None) -> None:
    """Generate doc skeletons from knowledge graph."""
    from beadloom.onboarding.doc_generator import generate_skeletons
    project_root = project or Path.cwd()
    result = generate_skeletons(project_root)
    click.echo(f"Created {result['files_created']} files, skipped {result['files_skipped']} existing")
```

#### `beadloom docs polish`

```python
@docs.command("polish")
@click.option("--project", type=click.Path(...), default=None)
@click.option("--ref-id", default=None, help="Polish specific node docs.")
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def docs_polish(*, project: Path | None, ref_id: str | None, fmt: str) -> None:
    """Output structured data for AI agent to enrich documentation."""
    from beadloom.onboarding.doc_generator import generate_polish_data
    project_root = project or Path.cwd()
    data = generate_polish_data(project_root, ref_id=ref_id)
    if fmt == "json":
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        click.echo(data["instructions"])
```

#### Enhanced `init` output

After all steps complete, print summary:

```
✓ Graph: 12 nodes, 18 edges (preset: monolith)
✓ Rules: 3 rules in .beadloom/_graph/rules.yml
✓ Docs: 8 skeletons in docs/
✓ MCP: configured for Claude Code (.mcp.json)
✓ Index: 245 symbols, 37 imports, 12 dependency edges

Next steps:
  1. Review docs/ and .beadloom/_graph/services.yml
  2. Run 'beadloom lint' to validate architecture
  3. Run 'beadloom docs polish' with your AI agent for richer docs
```

### 4.5 MCP tool: `generate_docs`

**Location:** `services/mcp_server.py`

```python
mcp.Tool(
    name="generate_docs",
    description=(
        "Generate or enrich documentation for a node. Returns structured data: "
        "node summary, public API symbols, dependencies, dependents, "
        "and a prompt for writing human-readable documentation. "
        "After generating, use update_node to save improved summaries."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "ref_id": {
                "type": "string",
                "description": "Node to generate docs for. Omit for all nodes.",
            },
        },
    },
)
```

**Handler:** Calls `generate_polish_data()` and returns JSON with:
- Node metadata (ref_id, kind, summary, source)
- Public symbols from code_symbols table
- Dependency graph (incoming/outgoing edges)
- Existing doc content (if any)
- Structured prompt for AI to write documentation

**Workflow for AI agent:**
1. Agent calls `generate_docs(ref_id="auth")` → gets structured data + prompt
2. Agent writes documentation based on the data
3. Agent calls `update_node(ref_id="auth", summary="...")` to save improved summary
4. Agent creates/edits `docs/domains/auth/README.md` with full documentation

### 4.6 Root node creation during bootstrap

**Problem:** Current bootstrap doesn't create a root project node. Rules need a root
to reference (e.g., `domain-needs-parent` requires `has_edge_to: {ref_id: <root>}`).

**Solution:** Add root node creation at the start of `bootstrap_project()`:

```python
# Detect project name from manifest or directory.
project_name = _detect_project_name(project_root)

# Root node.
root_node = {
    "ref_id": project_name,
    "kind": "service",
    "summary": f"Root: {project_name}",
    "source": "",
}
nodes.insert(0, root_node)

# Add part_of edges from top-level nodes to root.
for name in clusters:
    edges.append({"src": name, "dst": project_name, "kind": "part_of"})
```

**`_detect_project_name()`:** Reads `name` from `pyproject.toml`, `package.json`,
`go.mod`, or `Cargo.toml`. Falls back to directory name.

This ensures:
- `beadloom lint` works out of the box (rules have a valid root to reference)
- Graph has a clear hierarchy root
- `beadloom ctx <project-name>` returns the full project context

---

## 5. Execution Order

### Wave 1 — Foundation (P0, no dependencies)

| Bead | What | Files |
|------|------|-------|
| BEAD-01 | Root node creation + project name detection in `bootstrap_project()` | `scanner.py` |
| BEAD-02 | Auto-rules generation: `generate_rules()` | `scanner.py` |
| BEAD-03 | Auto MCP config: `setup_mcp_auto()` | `scanner.py` |

All three are independent changes to `scanner.py` but touch different functions.
BEAD-01 should go first since BEAD-02 depends on root node existing.

### Wave 2 — Doc generation (P0-P1, depends on Wave 1)

| Bead | What | Files |
|------|------|-------|
| BEAD-04 | `doc_generator.py`: `generate_skeletons()` | `onboarding/doc_generator.py`, `onboarding/__init__.py` |
| BEAD-05 | `doc_generator.py`: `generate_polish_data()` | `onboarding/doc_generator.py` |

BEAD-05 depends on BEAD-04 (shared module).

### Wave 3 — CLI + MCP integration (P1, depends on Wave 2)

| Bead | What | Files |
|------|------|-------|
| BEAD-06 | `beadloom docs generate` + `beadloom docs polish` CLI commands | `services/cli.py` |
| BEAD-07 | `generate_docs` MCP tool | `services/mcp_server.py` |
| BEAD-08 | Enhanced `init` output (summary with ✓ lines) | `services/cli.py`, `scanner.py` |

BEAD-06 and BEAD-07 are independent (both depend on Wave 2).
BEAD-08 depends on all of Wave 1 + Wave 2.

### Wave 4 — Integration tests (P1)

| Bead | What | Files |
|------|------|-------|
| BEAD-09 | Integration tests: init produces rules + docs + MCP | `tests/` |

### Wave 5 — Dogfooding: self-apply on Beadloom (P0, depends on all)

| Bead | What | Files |
|------|------|-------|
| BEAD-10 | Self-apply: run new onboarding on Beadloom itself | all project files |
| BEAD-11 | Update knowledge graph + CHANGELOG + version bump | `.beadloom/`, `docs/`, `CHANGELOG.md` |

**BEAD-10 — Dogfooding UX test (critical!):**

This is the real validation. Run the new features on Beadloom's own codebase and
verify everything works end-to-end. The checklist:

```bash
# 1. Generate fresh docs with new command
beadloom docs generate --project .
#    → Expect: skipped (all docs already exist)
#    → Validates: idempotency works, existing docs not overwritten

# 2. Generate rules from our graph
#    → Our rules.yml already exists — verify generate_rules() would produce
#      the same rules we wrote by hand (or better)

# 3. Test polish flow
beadloom docs polish --project . --format json
#    → Expect: structured data for all 18 nodes with symbols, deps, prompt
#    → Verify: data is rich enough for an AI agent to write useful docs

# 4. Test MCP tool
#    → Call generate_docs via MCP, verify response matches polish output

# 5. Update knowledge graph for new code:
#    - Add doc_generator.py as feature node under onboarding domain
#    - Add generate_docs MCP tool to mcp-server node summary
#    - Update CLI node: "20 commands" (was 18, +docs generate, +docs polish)
#    - Add edges: doc_generator part_of onboarding
#    - Update rules.yml if new rules needed

# 6. Run full validation pipeline
beadloom reindex --project .
beadloom doctor --project .     # all checks pass
beadloom lint --project .       # 0 violations
beadloom ctx onboarding --project .  # rich context with new docs

# 7. Update documentation
#    - docs/domains/onboarding/README.md — add doc_generator module
#    - docs/domains/onboarding/features/doc-generator/SPEC.md — new feature spec
#    - docs/services/cli.md — add docs generate, docs polish commands
#    - docs/services/mcp.md — add generate_docs tool (9th tool)

# 8. Verify README examples still work
#    - Architecture rules example in README.md still valid
#    - Context bundle example still valid
```

**Why this matters:**
- We catch UX issues before users do
- We validate idempotency (our project already has docs/rules/MCP)
- We ensure the graph stays consistent after adding new features
- The updated project becomes a living showcase of the onboarding flow

---

## 6. Test Strategy

### Unit tests (per bead)

| Function | Test cases |
|----------|------------|
| `generate_rules()` | domains-only → 1 rule; domains+features → 2 rules; all kinds → 3 rules; empty graph → 0 rules; idempotent (skip existing) |
| `_detect_project_name()` | pyproject.toml, package.json, go.mod, directory fallback |
| `setup_mcp_auto()` | detect claude-code, cursor, windsurf, default; skip existing; correct JSON structure |
| `generate_skeletons()` | creates architecture.md; creates per-domain README; creates per-feature SPEC; skips existing; correct markdown structure |
| `generate_polish_data()` | returns symbols, edges, prompt; single ref_id mode; all-nodes mode |

### Integration tests

| Scenario | Assertion |
|----------|-----------|
| `beadloom init --bootstrap` on clean project | rules.yml exists, docs/ exists, .mcp.json exists |
| `beadloom lint` after init | ≥ 1 rule evaluated, 0 violations |
| `beadloom ctx <node>` after init | returns docs chunks (from skeletons) |
| `beadloom docs generate` after reindex | files created with symbol tables |
| `beadloom docs polish --format json` | valid JSON with instructions field |
| Re-run init (idempotent) | no files overwritten, same result |

---

## 7. Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Skeleton docs are too generic to be useful | Medium | Medium | Include concrete data: symbol counts, dependency lists, source paths. AI polish covers the rest. |
| Root node detection picks wrong name | Low | Medium | Multiple manifest parsers + directory fallback. User can edit graph. |
| MCP auto-config conflicts with existing setup | Low | Low | Check before creating. Never overwrite. |
| `bootstrap_project()` becomes too long | Medium | Low | Extract into composable steps, each independently testable. |
| `docs` group conflicts with existing CLI commands | Low | High | Verify no existing `docs` command. Currently none exists. |

---

## 8. API Contracts

### `generate_rules()` → `rules.yml`

```yaml
version: 1
rules:
  - name: domain-needs-parent
    description: "Every domain must be part_of {root}"
    require:
      for: { kind: domain }
      has_edge_to: { ref_id: "{root}" }
      edge_kind: part_of
```

### `generate_polish_data()` → JSON

```json
{
  "nodes": [
    {
      "ref_id": "auth",
      "kind": "domain",
      "summary": "Domain: auth (12 files)",
      "source": "src/auth/",
      "symbols": [
        {"name": "authenticate", "kind": "function", "file": "src/auth/service.py", "line": 15},
        {"name": "User", "kind": "class", "file": "src/auth/models.py", "line": 8}
      ],
      "depends_on": ["infrastructure"],
      "used_by": ["cli", "mcp-server"],
      "features": ["auth-api", "auth-models"],
      "existing_docs": null
    }
  ],
  "architecture": {
    "project_name": "myproject",
    "mermaid": "graph LR\n  auth --> infrastructure\n  ...",
    "preset": "monolith"
  },
  "instructions": "You are enriching documentation for a software project..."
}
```

### `generate_docs` MCP tool → response

Same JSON as `generate_polish_data()`, wrapped in MCP TextContent.

---

## 9. Decision Log

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | New `doc_generator.py` file, not extending `scanner.py` | SRP: scanner scans code, doc_generator generates docs. Different concerns. |
| D2 | `docs` as Click group (not standalone commands) | Namespace for future doc commands (`docs status`, `docs diff`). |
| D3 | Root node created during bootstrap | Required for rules to have a valid target. Also makes `beadloom ctx <project>` work. |
| D4 | Skeleton docs have `<!-- enrich with: beadloom docs polish -->` markers | Clear signal to user and AI agent that docs can be improved. |
| D5 | MCP default is claude-code format | Most universal `.mcp.json` format. Cursor and Windsurf are detected by markers. |
| D6 | `generate_polish_data()` returns prompt in `instructions` field | AI agent gets structured data AND a guiding prompt. No separate prompt file needed. |
| D7 | Never overwrite existing files | Core safety guarantee. User trust > convenience. |
| D8 | Dogfooding wave as mandatory final step | Self-apply validates UX, idempotency, and updates project docs/graph in one pass. Beadloom becomes its own showcase. |

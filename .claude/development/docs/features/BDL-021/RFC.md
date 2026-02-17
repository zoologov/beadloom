# RFC: BDL-021 — v1.7.0: AaC Rules v2, Init Quality, Architecture Intelligence

> **Status:** Approved
> **Created:** 2026-02-17

---

## Overview

v1.7.0 extends Beadloom in three directions: (1) a full architecture enforcement engine with 4 new rule types + node tags, (2) reliable first-time bootstrap with 80%+ coverage, and (3) architecture change tracking with diff and enhanced impact analysis. This transforms Beadloom from a documentation tool to an architecture enforcement platform — "ArchUnit for any stack."

## Motivation

### Problem

1. **Rule engine is primitive.** Only `require` (node must have edge) and `deny` (import-level boundary). Real projects need graph-level forbidden dependencies, layer enforcement, cycle detection, glob-based import boundaries, and cardinality checks. The existing `deny` rule checks `code_imports` table — we need graph-edge-level enforcement too.

2. **Bootstrap captures 35% of architecture.** `detect_source_dirs()` only checks a hardcoded `_SOURCE_DIRS` set first, falls back to scanning only if nothing found. React Native projects with `components/`, `hooks/`, `contexts/`, `modules/` at the top level are missed. Init is interactive-only, generates a failing `service-needs-parent` rule on root, doesn't generate docs, doesn't link existing docs.

3. **No architecture change visibility.** `beadloom diff` exists but only compares disk YAML vs a git ref. No snapshot storage, no symbol-level tracking. `beadloom why` works but lacks `--reverse`, configurable `--depth` display, and `--format tree`.

### Solution

Phase 12 adds 4 new rule types + tags. Phase 12.5 fixes init quality. Phase 12.6 adds architecture snapshots and enhanced impact analysis.

## Technical Context

### Constraints
- Python 3.10+, SQLite (WAL mode)
- tree-sitter for code parsing (9 languages)
- No external LLM calls (agent-native principle)
- rules.yml backward compatibility: v1/v2 schemas must still work
- `extra` JSON column in `nodes` table available for tag storage

### Affected Areas

| Domain | Impact |
|--------|--------|
| `graph` | Rule engine, loader, diff — heaviest changes |
| `graph/rule-engine` | 4 new rule types + tags matcher |
| `graph/graph-diff` | Snapshot storage, symbol-level diff |
| `onboarding` | Scanner, interactive_init, generate_rules |
| `context-oracle/why` | Enhanced traversal, reverse direction, tree format |
| `cli` | New flags for `init`, `why`, `diff`, `snapshot` |
| `mcp-server` | New `snapshot` tool, updated `diff` tool |

## Proposed Solution

### Phase 12: AaC Rules v2

#### 12.1 Node Tags/Labels

**services.yml change:**
```yaml
nodes:
  - ref_id: app-tabs
    kind: domain
    source: app/(tabs)/
    tags: [ui-layer, presentation]    # NEW field
    summary: "..."
```

**Storage:** `tags` goes into the `extra` JSON column (existing mechanism — all non-core fields land in `extra`). Add a helper to extract tags:

```python
# graph/loader.py
def get_node_tags(conn: sqlite3.Connection, ref_id: str) -> set[str]:
    """Extract tags from node's extra JSON."""
    row = conn.execute("SELECT extra FROM nodes WHERE ref_id = ?", (ref_id,)).fetchone()
    if not row:
        return set()
    extra = json.loads(row[0]) if row[0] else {}
    return set(extra.get("tags", []))
```

**NodeMatcher extension:**
```python
@dataclass(frozen=True)
class NodeMatcher:
    ref_id: str | None = None
    kind: str | None = None
    tag: str | None = None         # NEW: match nodes with this tag

def matches(self, ref_id: str, kind: str, tags: set[str]) -> bool:
    if self.ref_id and self.ref_id != ref_id:
        return False
    if self.kind and self.kind != kind:
        return False
    if self.tag and self.tag not in tags:
        return False
    return True
```

**Also support top-level `tags:` block in rules.yml for convenience:**
```yaml
tags:
  ui-layer: [app-tabs, app-auth, app-meshtastic]
  feature-layer: [map, calendar, profile]
```
This is syntactic sugar — auto-assigns tags to listed ref_ids in services.yml (or validates they match). Optional feature.

#### 12.2 Forbidden Dependency Rules (graph-level)

New rule type: `ForbidEdgeRule` — checks edges table (NOT imports).

```python
@dataclass(frozen=True)
class ForbidEdgeRule:
    name: str
    description: str
    from_matcher: NodeMatcher    # matches source node (by tag, kind, ref_id)
    to_matcher: NodeMatcher      # matches target node
    edge_kind: str | None        # optional: only check specific edge kind
    severity: str = "error"
```

**Evaluation:** Iterate edges table, for each edge check if `src` matches `from_matcher` and `dst` matches `to_matcher`. If yes → violation.

```yaml
# rules.yml
- name: ui-no-native
  forbid:
    from: { tag: ui-layer }
    to: { tag: native-layer }
    edge_kind: uses
  severity: error
  message: "UI layer must not depend on native modules directly"
```

#### 12.3 Layer Enforcement Rules

New rule type: `LayerRule` — ordered layer enforcement.

```python
@dataclass(frozen=True)
class LayerDef:
    name: str
    tag: str

@dataclass(frozen=True)
class LayerRule:
    name: str
    description: str
    layers: tuple[LayerDef, ...]    # ordered top-to-bottom
    enforce: str                     # "top-down" (upper cannot depend on lower)
    allow_skip: bool = True          # can skip layers (presentation → service)
    edge_kind: str = "uses"          # which edge kind to check
    severity: str = "error"
```

**Evaluation:** For each edge of the specified kind, determine which layer (if any) the src and dst belong to. If src is in a lower layer and dst is in an upper layer → violation. If `allow_skip=False` and src skips a layer → violation.

```yaml
- name: layer-direction
  layers:
    - { name: presentation, tag: ui-layer }
    - { name: features, tag: feature-layer }
    - { name: shared, tag: shared-layer }
    - { name: services, tag: service-layer }
    - { name: native, tag: native-layer }
  enforce: top-down
  allow_skip: true
```

#### 12.4 Circular Dependency Detection

New rule type: `CycleRule` — BFS/DFS cycle detection.

```python
@dataclass(frozen=True)
class CycleRule:
    name: str
    description: str
    edge_kind: str | tuple[str, ...]   # which edge kinds to traverse
    max_depth: int = 10                 # limit search depth
    severity: str = "error"
```

**Evaluation:** Iterative DFS with path tracking. For each node, walk outgoing edges of the specified kind. If we visit a node already in the current path → cycle found. Report the full cycle path.

```yaml
- name: no-circular-deps
  forbid_cycles:
    edge_kind: uses
    max_depth: 10
```

#### 12.5 Import-Based Boundary Rules

New rule type: `ImportBoundaryRule` — glob-path-based import restrictions.

```python
@dataclass(frozen=True)
class ImportBoundaryRule:
    name: str
    description: str
    from_glob: str                    # source path glob (e.g., "components/features/map/**")
    to_glob: str                      # target path glob
    severity: str = "error"
```

**Evaluation:** Query `code_imports` table. For each import, check if the source file matches `from_glob` (via `fnmatch`) and the resolved target file matches `to_glob`. If both match → violation.

This differs from existing `DenyRule` (which uses NodeMatcher) by operating on file paths with glob patterns.

```yaml
- name: no-cross-feature-imports
  forbid_import:
    from: "components/features/map/**"
    to: "components/features/calendar/**"
```

#### 12.6 Cardinality/Complexity Rules

New rule type: `CardinalityRule` — architectural smell detection.

```python
@dataclass(frozen=True)
class CardinalityRule:
    name: str
    description: str
    for_matcher: NodeMatcher
    max_symbols: int | None = None
    max_files: int | None = None
    min_doc_coverage: float | None = None   # 0.0-1.0
    severity: str = "warn"
```

**Evaluation:** For each matching node, count symbols (from `code_symbols`), files (from `file_index`), and doc coverage (from `sync_state`). Report if any threshold is exceeded.

```yaml
- name: domain-size
  check:
    for: { kind: domain }
    max_symbols: 200
    max_files: 30
  severity: warn
```

#### Rules Schema v3

Bump schema version to 3. Backward compatible: v1 and v2 continue to work. v3 adds new rule types + `tags` block.

```python
SUPPORTED_SCHEMA_VERSIONS = {1, 2, 3}
Rule = DenyRule | RequireRule | ForbidEdgeRule | LayerRule | CycleRule | ImportBoundaryRule | CardinalityRule
```

### Phase 12.5: Init Quality

#### 12.5.1 Scan All Code Directories

**Change `scan_project()` in `scanner.py`:**

Current: Pass 1 checks hardcoded `_SOURCE_DIRS`, Pass 2 only runs if Pass 1 finds nothing.

Fix: Always run Pass 2 (scan all non-hidden, non-vendor dirs with code files). Merge results from Pass 1 and Pass 2. Deduplicate.

```python
def scan_project(project_root: Path) -> dict[str, Any]:
    # Pass 1: known source dirs (always)
    known = _find_known_dirs(project_root)
    # Pass 2: all dirs with code files (always, not just as fallback)
    code_dirs = _find_code_dirs(project_root)
    # Merge + deduplicate
    source_dirs = sorted(set(known + code_dirs))
    ...
```

#### 12.5.2 Non-Interactive Init Mode

**Add CLI flags to `init` command:**

```python
@main.command()
@click.option("--mode", type=click.Choice(["bootstrap", "import", "both"]))
@click.option("--yes", "-y", "non_interactive", is_flag=True)
@click.option("--force", is_flag=True, help="Overwrite existing .beadloom/")
def init(mode, non_interactive, force, project):
    if non_interactive:
        non_interactive_init(project, mode=mode or "bootstrap", force=force)
    else:
        interactive_init(project)
```

New `non_interactive_init()` function: no prompts, uses defaults, returns result dict.

#### 12.5.3 Root Service Rule Fix

**Change `generate_rules()` in `scanner.py`:**

Don't generate `service-needs-parent` rule (root service has no parent by definition). Or generate it with an exclusion for root node.

Simplest fix: skip `service-needs-parent` rule entirely. The only service that typically exists at bootstrap is the root.

#### 12.5.4 Docs Generate in Init

**Add to `interactive_init()` and `non_interactive_init()`:**

After graph confirmation, prompt "Generate doc skeletons? [yes/no]" (default: yes). In non-interactive mode, always generate.

```python
# After bootstrap + reindex:
if should_generate_docs:
    from beadloom.onboarding.doc_generator import generate_skeletons
    count = generate_skeletons(project_root)
    console.print(f"Generated {count} doc skeletons")
```

#### 12.5.5 Doc Auto-Linking

**New function in `scanner.py` or `doc_generator.py`:**

```python
def auto_link_docs(project_root: Path, nodes: list[dict]) -> int:
    """Match existing docs to graph nodes by path similarity."""
    # Strategy:
    # 1. Scan docs/ for all .md files
    # 2. For each node, check if docs/{ref_id}/*.md or docs/*/{ref_id}*.md exists
    # 3. If match found, update services.yml docs field
    # Returns count of linked docs
```

Fuzzy matching: `docs/auth/README.md` → node `app-auth`, `docs/map.md` → node `map`.

### Phase 12.6: Architecture Intelligence

#### 12.6.1 Architecture Snapshots + Enhanced Diff

**New module: `graph/snapshot.py`**

```python
def save_snapshot(conn: sqlite3.Connection, label: str | None = None) -> int:
    """Save current graph state as a snapshot. Returns snapshot_id."""

def list_snapshots(conn: sqlite3.Connection) -> list[SnapshotInfo]:
    """List all saved snapshots."""

def compare_snapshots(conn: sqlite3.Connection, old_id: int, new_id: int) -> GraphDiff:
    """Compare two snapshots."""
```

**SQLite schema additions:**
```sql
CREATE TABLE IF NOT EXISTS graph_snapshots (
    id INTEGER PRIMARY KEY,
    label TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    nodes_json TEXT NOT NULL,     -- JSON array of node dicts
    edges_json TEXT NOT NULL,     -- JSON array of edge dicts
    symbols_count INTEGER NOT NULL DEFAULT 0
);
```

**Enhanced `compute_diff()`:** Add symbol-level change tracking (not just `kind` + `summary`). Include `source`, `tags` in change detection.

#### 12.6.2 Enhanced Impact Analysis

**Extend `why.py`:**

```python
def analyze_node(
    conn: sqlite3.Connection,
    ref_id: str,
    depth: int = 3,
    max_nodes: int = 50,
    reverse: bool = False,        # NEW: show what X depends on (upstream focus)
    format: str = "panel",        # NEW: "panel" | "tree"
) -> WhyResult
```

- `--reverse`: When True, emphasize upstream (what this node depends on) with deeper traversal. Currently both directions use same depth — allow asymmetric depths.
- `--format tree`: Render as a clean dependency tree (no Rich panels, simpler format for CI/piping).

CLI changes:
```python
@click.option("--reverse", is_flag=True, help="Focus on what this node depends on")
@click.option("--format", "fmt", type=click.Choice(["panel", "tree"]), default="panel")
```

#### 12.6.3 CLI Commands

```bash
beadloom snapshot save [--label "v1.6.0"]     # save current state
beadloom snapshot list                         # list saved snapshots
beadloom snapshot compare <id1> <id2>          # compare two snapshots
beadloom diff [--since HEAD] [--json]          # existing, enhanced
beadloom why <ref-id> [--reverse] [--depth N] [--format tree] [--json]
```

## Changes Summary

| File / Module | Change |
|---------------|--------|
| `graph/rule_engine.py` | 4 new rule dataclasses + evaluators, NodeMatcher `tag` field, schema v3 |
| `graph/linter.py` | Handle new rule types in `lint()` |
| `graph/loader.py` | `get_node_tags()` helper, tags in YAML parsing |
| `graph/diff.py` | Symbol-level diff, enhanced change detection |
| `graph/snapshot.py` | **NEW** — snapshot save/list/compare |
| `onboarding/scanner.py` | `scan_project()` fix, `non_interactive_init()`, rule fix, doc auto-link |
| `onboarding/doc_generator.py` | Doc generation in init flow |
| `context_oracle/why.py` | `--reverse`, `--format tree` |
| `infrastructure/db.py` | `graph_snapshots` table DDL |
| `services/cli.py` | New flags: `init --mode/--yes/--force`, `snapshot` subcommand, `why --reverse/--format` |
| `services/mcp_server.py` | Updated tools |

## Alternatives Considered

### Option A: Tags in a Separate `tags.yml` File
Pros: clean separation. Cons: extra file, harder to maintain, need cross-file validation.
**Rejected:** Tags belong to nodes, should be in `services.yml`.

### Option B: DSL-Based Rules (OPA/Rego)
Pros: very expressive. Cons: adds dependency, steep learning curve, over-engineering for 80% of use cases.
**Rejected:** YAML covers the needed scenarios without external dependencies.

### Option C: Store Snapshots in Git (not SQLite)
Pros: automatically versioned. Cons: bloats repo, harder to query, can't compare without checkout.
**Rejected:** SQLite is queryable and doesn't pollute git history.

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Schema v3 breaks existing rules.yml | Low | High | Backward compat: v1/v2 still work, v3 adds new features |
| Cycle detection performance on large graphs | Low | Medium | `max_depth` limit, early termination |
| Tag assignment effort for users | Medium | Low | Optional: rules work without tags; top-level `tags:` block is sugar |
| Init Pass 2 finds too many dirs | Low | Medium | Exclude `tests/`, `docs/`, `scripts/` etc. from code dirs |

## Open Questions

| # | Question | Decision |
|---|----------|----------|
| Q1 | Tags inline in services.yml vs separate tags.yml? | Decided: inline in services.yml (simpler) |
| Q2 | Import rules: glob vs node-level? | Decided: glob (12.5) for file-level, tag-based (12.2) for graph-level |
| Q3 | Schema version bump to v3 vs extend v2? | Decided: v3 (clean versioning) |
| Q4 | Snapshot storage in main DB vs separate file? | Pending: main DB likely simpler |
| Q5 | `ForbidEdgeRule` naming vs reusing `DenyRule`? | Decided: separate type (different evaluation logic) |

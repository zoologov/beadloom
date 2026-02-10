# RFC-0006: Phase 5 — Developer Experience (v0.7)

> **Status:** Implemented (v0.7.0)
> **Date:** 2026-02-11
> **Phase:** 5 (v0.7)
> **Depends on:** BDL-005 (v0.6.0 — Performance complete)
> **PRD:** BDL-006/PRD.md (approved)

---

## 1. Summary

Phase 5 transforms Beadloom from a CLI-only tool into a developer-friendly experience with four features:

1. **Why** — bidirectional graph traversal with impact analysis
2. **Diff** — graph delta between git refs
3. **TUI** — interactive Textual dashboard
4. **Watch** — file-watching auto-reindex

### Design Principle

> **Show, don't tell.** Every feature visualizes data that already exists in the index.

No new data collection or indexing logic. All four features are read-only consumers of the existing SQLite schema (except watch, which triggers existing reindex).

---

## 2. Deliverables

| # | Item | Priority | Effort | New deps | New module |
|---|------|----------|--------|----------|------------|
| 5.1 | `beadloom why <ref_id>` | P1 | M | — | `why.py` |
| 5.2 | `beadloom diff` | P1 | M | — | `diff.py` |
| 5.3 | `beadloom ui` (TUI) | P1 | L | `textual` | `tui/` package |
| 5.4 | `beadloom watch` | P2 | M | `watchfiles` | `watcher.py` |

**Version:** 0.7.0
**Schema:** SCHEMA_VERSION remains "1" (no schema changes)

---

## 3. Technical Design

### 3.1 Why — Impact Analysis (5.1)

**New module:** `src/beadloom/why.py`

#### Algorithm

Bidirectional BFS from the target node. Unlike `bfs_subgraph()` which traverses both directions in one pass, `why` separates upstream from downstream for clear presentation.

```python
def analyze_node(
    conn: sqlite3.Connection,
    ref_id: str,
    depth: int = 3,
    max_nodes: int = 50,
) -> WhyResult:
    """Bidirectional BFS: upstream (dependencies) + downstream (dependents)."""
```

**Upstream traversal:** Follow outgoing edges from the target.
"What does this node depend on?" — traverse `edges WHERE src_ref_id = ?`

**Downstream traversal:** Follow incoming edges to the target.
"What depends on this node?" — traverse `edges WHERE dst_ref_id = ?`

```python
@dataclass(frozen=True)
class WhyResult:
    node: NodeInfo              # ref_id, kind, summary
    upstream: list[TreeNode]    # dependency tree
    downstream: list[TreeNode]  # dependents tree
    impact: ImpactSummary       # aggregated metrics

@dataclass(frozen=True)
class TreeNode:
    ref_id: str
    kind: str
    summary: str
    edge_kind: str              # how connected to parent
    children: list[TreeNode]    # recursive

@dataclass(frozen=True)
class ImpactSummary:
    downstream_direct: int      # immediate dependents
    downstream_transitive: int  # total reachable downstream
    doc_coverage: float         # % of downstream with docs
    stale_count: int            # stale docs in downstream
```

#### Rendering (Rich)

```python
def render_why(result: WhyResult, console: Console) -> None:
    """Render WhyResult as Rich Tree + Panel."""
```

Output layout:
```
╭─ beadloom why AUTH-001 ──────────────────────────╮
│  auth/login (feature)                            │
│  "User authentication via email/password"        │
╰──────────────────────────────────────────────────╯

⬆ Upstream (depends on):
 └── user-service [uses]
      └── postgres-adapter [uses]

⬇ Downstream (used by):
 ├── session-manager [depends_on]
 ├── api-gateway [uses]
 └── billing/checkout [depends_on]
      └── payment-processor [uses]

╭─ Impact ─────────────────────────────────────────╮
│  Direct dependents:     3                        │
│  Transitive downstream: 4                        │
│  Doc coverage:          75% (3/4)                │
│  Stale docs:            1                        │
╰──────────────────────────────────────────────────╯
```

#### CLI

```python
@main.command()
@click.argument("ref_id")
@click.option("--depth", default=3, help="BFS depth")
@click.option("--json", "as_json", is_flag=True, help="JSON output")
def why(ref_id: str, depth: int, as_json: bool) -> None:
```

#### JSON output

```json
{
  "node": {"ref_id": "AUTH-001", "kind": "feature", "summary": "..."},
  "upstream": [
    {"ref_id": "user-service", "kind": "service", "edge_kind": "uses", "children": [...]}
  ],
  "downstream": [...],
  "impact": {
    "downstream_direct": 3,
    "downstream_transitive": 4,
    "doc_coverage": 75.0,
    "stale_count": 1
  }
}
```

---

### 3.2 Diff — Graph Delta (5.2)

**New module:** `src/beadloom/diff.py`

#### Algorithm

Compare current graph (from YAML on disk) with graph at a git ref (via `git show`).

```python
def compute_diff(
    project_root: Path,
    since: str = "HEAD",
) -> GraphDiff:
    """Compare current graph YAML with state at git ref."""
```

**Steps:**

1. **Current state:** Parse all `*.yml` from `.beadloom/_graph/` using `parse_graph_file()`
2. **Previous state:** For each YAML file, run `git show <ref>:<path>` and parse the output
   - If file didn't exist at ref → all nodes/edges are "added"
   - If file was deleted since ref → all nodes/edges are "removed"
3. **Diff computation:**
   - Nodes: compare by `ref_id` — added, removed, changed (summary or kind differ)
   - Edges: compare by `(src, dst, kind)` tuple — added or removed
4. **Return:** `GraphDiff` with categorized changes

```python
@dataclass(frozen=True)
class NodeChange:
    ref_id: str
    kind: str
    change_type: str            # "added" | "removed" | "changed"
    old_summary: str | None     # for "changed"
    new_summary: str | None     # for "changed"

@dataclass(frozen=True)
class EdgeChange:
    src: str
    dst: str
    kind: str
    change_type: str            # "added" | "removed"

@dataclass(frozen=True)
class GraphDiff:
    since_ref: str
    nodes: list[NodeChange]
    edges: list[EdgeChange]

    @property
    def has_changes(self) -> bool:
        return bool(self.nodes or self.edges)
```

#### Git integration

```python
def _read_yaml_at_ref(project_root: Path, rel_path: str, ref: str) -> str | None:
    """Read file content at a git ref. Returns None if file didn't exist."""
    result = subprocess.run(
        ["git", "show", f"{ref}:{rel_path}"],
        capture_output=True, text=True, cwd=project_root,
    )
    if result.returncode != 0:
        return None
    return result.stdout
```

#### Rendering (Rich)

```python
def render_diff(diff: GraphDiff, console: Console) -> None:
    """Render GraphDiff as Rich table."""
```

Output layout:
```
Graph diff (since HEAD):

  Nodes:
    + notifications (domain)    "Push notification system"
    ~ auth/login (feature)      "Basic auth" → "OAuth2 + basic auth"
    - legacy-api (service)

  Edges:
    + notifications ──uses──> email-service
    - legacy-api ──depends_on──> auth/login

  Summary: 1 added, 1 changed, 1 removed nodes; 1 added, 1 removed edges
```

Legend: `+` added, `~` changed, `-` removed (colors: green, yellow, red).

#### CLI

```python
@main.command()
@click.option("--since", default="HEAD", help="Git ref to compare against")
@click.option("--json", "as_json", is_flag=True, help="JSON output")
def diff(since: str, as_json: bool) -> None:
```

**Exit codes:** 0 = no changes, 1 = changes detected. Enables CI usage:
```bash
beadloom diff --since=main || echo "Graph changed in this PR"
```

---

### 3.3 TUI — Interactive Dashboard (5.3)

**New package:** `src/beadloom/tui/`

```
src/beadloom/tui/
├── __init__.py          # BeadloomApp class
├── app.py               # Main Textual Application
├── screens/
│   └── main.py          # MainScreen layout
├── widgets/
│   ├── domain_list.py   # Domain sidebar
│   ├── node_detail.py   # Node info panel
│   ├── graph_view.py    # ASCII graph visualization
│   └── status_bar.py    # Bottom status bar
└── styles/
    └── app.tcss         # Textual CSS stylesheet
```

#### Application Architecture

```python
class BeadloomApp(App[None]):
    """Beadloom interactive terminal dashboard."""

    CSS_PATH = "styles/app.tcss"
    TITLE = "Beadloom"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("/", "search", "Search"),
        Binding("w", "why", "Why"),
        Binding("d", "diff", "Diff"),
        Binding("r", "reindex", "Reindex"),
    ]

    def __init__(self, db_path: Path, project_root: Path) -> None:
        super().__init__()
        self.db_path = db_path
        self.project_root = project_root
```

#### Layout (3-panel)

```
┌─ Domains (1/3) ──────┬─ Detail (2/3) ────────────────────┐
│ ◉ auth           [3]  │ auth/login (feature)              │
│ ◉ billing        [2]  │ "User authentication via OAuth2"  │
│ ○ notifications  [1]  │                                   │
│                       │ Edges:                            │
│ ◉ = has docs          │  → user-service [uses]            │
│ ○ = no docs           │  ← api-gateway [depends_on]      │
│ [3] = node count      │                                   │
│                       │ Docs: 2 (1 stale)                 │
│                       │ Symbols: 5 functions, 2 classes   │
├───────────────────────┴───────────────────────────────────┤
│ Status: 12 nodes, 8 edges, 67% coverage, 1 stale         │
│ [/] Search  [w] Why  [d] Diff  [r] Reindex  [q] Quit     │
└───────────────────────────────────────────────────────────┘
```

#### Widget Responsibilities

**DomainList** — Left sidebar:
- Query: `SELECT ref_id, kind, summary FROM nodes WHERE kind = 'domain'`
- For each domain: count child nodes via `edges WHERE kind = 'part_of'`
- Doc indicator: check if any `docs` exist for this ref_id
- Selection emits `DomainSelected` message

**NodeDetail** — Right panel:
- Shows selected node's full info: summary, edges (in/out), docs, code symbols, sync status
- Queries: `nodes`, `edges`, `docs`, `code_symbols`, `sync_state`
- On domain select → show domain overview (child nodes list)
- On node select → show full node details

**StatusBar** — Bottom:
- Shows latest `HealthSnapshot` metrics
- Keyboard shortcut hints

#### Data Layer

The TUI opens a read-only SQLite connection and queries directly. No caching needed (SQLite WAL allows concurrent reads).

```python
def _open_readonly(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn
```

#### Import Guard

Textual is an optional dependency. The CLI command guards the import:

```python
@main.command()
def ui() -> None:
    """Launch interactive terminal dashboard."""
    try:
        from beadloom.tui import BeadloomApp
    except ImportError:
        click.echo("TUI requires 'textual'. Install with: pip install beadloom[tui]")
        raise SystemExit(1)
    app = BeadloomApp(db_path=..., project_root=...)
    app.run()
```

#### Iterative Approach

TUI is the largest deliverable. Build incrementally:

1. **Phase A:** Skeleton app + domain list + status bar (functional but minimal)
2. **Phase B:** Node detail panel with edges, docs, symbols
3. **Phase C:** Search integration (FTS5), keyboard navigation polish
4. **Phase D:** Why/Diff integration (press `w`/`d` to invoke inline)

Each sub-phase is testable independently.

---

### 3.4 Watch — File Watcher (5.4)

**New module:** `src/beadloom/watcher.py`

#### Architecture

```python
def watch(
    project_root: Path,
    debounce_ms: int = 500,
    callback: Callable[[ReindexResult], None] | None = None,
) -> None:
    """Watch project files and trigger incremental reindex on changes."""
```

**Uses `watchfiles`** (Rust-based, cross-platform):

```python
from watchfiles import watch as fs_watch, Change

def _get_watch_paths(project_root: Path) -> list[Path]:
    """Paths to watch: graph dir, docs dir, source dirs."""
    paths = [project_root / ".beadloom" / "_graph"]
    docs_dir = _resolve_docs_dir(project_root)
    if docs_dir.exists():
        paths.append(docs_dir)
    for scan_dir in ("src", "lib", "app"):
        d = project_root / scan_dir
        if d.exists():
            paths.append(d)
    return paths
```

#### Event Loop

```python
def watch(project_root: Path, debounce_ms: int = 500, ...) -> None:
    watch_paths = _get_watch_paths(project_root)
    console = Console()
    console.print(f"[dim][{_now()}] Watching {len(watch_paths)} directories...[/dim]")

    for changes in fs_watch(*watch_paths, debounce=debounce_ms):
        # Filter relevant extensions
        relevant = _filter_relevant(changes, project_root)
        if not relevant:
            continue

        graph_changed = any(
            _is_graph_file(path, project_root) for _, path in relevant
        )

        if graph_changed:
            result = reindex(project_root)
            label = "full reindex"
        else:
            result = incremental_reindex(project_root)
            label = "incremental"

        n_files = len(relevant)
        console.print(
            f"[dim][{_now()}][/dim] {n_files} file(s) changed → "
            f"{label} ({result.nodes_loaded}n, {result.docs_indexed}d, "
            f"{result.symbols_indexed}s)"
        )

        if callback:
            callback(result)
```

#### File Filtering

```python
_WATCH_EXTENSIONS = frozenset({
    ".yml", ".yaml",                          # graph
    ".md",                                    # docs
    ".py", ".ts", ".tsx", ".js", ".jsx",      # code
    ".go", ".rs",                             # code
})

def _filter_relevant(
    changes: set[tuple[Change, str]], project_root: Path
) -> list[tuple[Change, str]]:
    """Filter to relevant file extensions, ignore hidden/temp files."""
    result = []
    for change_type, path_str in changes:
        p = Path(path_str)
        if p.suffix not in _WATCH_EXTENSIONS:
            continue
        if any(part.startswith(".") for part in p.parts if part != ".beadloom"):
            continue
        if p.name.startswith("~") or p.name.endswith(".tmp"):
            continue
        result.append((change_type, path_str))
    return result
```

#### Import Guard

Same pattern as TUI:

```python
@main.command()
@click.option("--debounce", default=500, help="Debounce delay in ms")
def watch_cmd(debounce: int) -> None:
    """Watch files and auto-reindex on changes."""
    try:
        from beadloom.watcher import watch
    except ImportError:
        click.echo("Watch requires 'watchfiles'. Install with: pip install beadloom[watch]")
        raise SystemExit(1)
    watch(project_root=Path.cwd(), debounce_ms=debounce)
```

---

## 4. Dependency Changes

### pyproject.toml additions

```toml
[project.optional-dependencies]
tui = [
    "textual>=0.50",
]
watch = [
    "watchfiles>=0.20",
]
# Updated:
all = [
    "beadloom[languages,tui,watch,dev]",
]
```

**Core dependencies unchanged.** Both `textual` and `watchfiles` are optional.

---

## 5. Testing Strategy

### 5.1 Why tests (`tests/test_why.py`)

| Test | Description |
|------|-------------|
| `test_analyze_basic` | Single node with upstream + downstream |
| `test_analyze_no_edges` | Isolated node → empty trees |
| `test_analyze_depth_limit` | Respects depth parameter |
| `test_analyze_cycle` | Handles circular deps gracefully |
| `test_analyze_nonexistent` | LookupError with suggestions |
| `test_impact_summary` | Correct counts and coverage |
| `test_render_rich` | Rich output contains expected sections |
| `test_json_output` | Valid JSON with correct structure |

### 5.2 Diff tests (`tests/test_diff.py`)

| Test | Description |
|------|-------------|
| `test_diff_no_changes` | Same YAML → empty diff |
| `test_diff_added_node` | New node detected |
| `test_diff_removed_node` | Deleted node detected |
| `test_diff_changed_summary` | Modified summary detected |
| `test_diff_added_edge` | New edge detected |
| `test_diff_removed_edge` | Deleted edge detected |
| `test_diff_new_file` | File not in git → all nodes added |
| `test_diff_deleted_file` | File removed → all nodes removed |
| `test_diff_invalid_ref` | Bad git ref → clear error |
| `test_exit_code_no_changes` | Exit 0 |
| `test_exit_code_with_changes` | Exit 1 |

### 5.3 TUI tests (`tests/test_tui.py`)

Textual provides `pilot` for headless testing:

| Test | Description |
|------|-------------|
| `test_app_launches` | App starts without error |
| `test_domain_list_populated` | Domains appear in sidebar |
| `test_node_selection` | Clicking domain shows nodes |
| `test_node_detail_panel` | Node detail shows edges, docs |
| `test_status_bar_metrics` | Health metrics displayed |
| `test_search_shortcut` | `/` opens search |
| `test_quit_shortcut` | `q` exits app |
| `test_missing_textual` | ImportError → friendly message |

### 5.4 Watch tests (`tests/test_watcher.py`)

| Test | Description |
|------|-------------|
| `test_filter_relevant` | Correct file filtering |
| `test_filter_ignores_hidden` | Dotfiles excluded |
| `test_filter_ignores_temp` | Temp files excluded |
| `test_is_graph_file` | Graph YAML detection |
| `test_get_watch_paths` | Correct directories resolved |
| `test_missing_watchfiles` | ImportError → friendly message |

### 5.5 CLI integration tests

| Test | Description |
|------|-------------|
| `test_cli_why` | `beadloom why REF` end-to-end |
| `test_cli_why_json` | `beadloom why REF --json` |
| `test_cli_diff` | `beadloom diff` end-to-end |
| `test_cli_diff_since` | `beadloom diff --since=HEAD~1` |
| `test_cli_diff_json` | `beadloom diff --json` |
| `test_cli_ui_no_textual` | Graceful error without textual |
| `test_cli_watch_no_watchfiles` | Graceful error without watchfiles |

**Estimated total:** 464 (current) + ~60 new = ~524 tests

---

## 6. Implementation Order

```
5.1 Why ─────┐
             ├──> 5.3 TUI (phases A→D) ──> version bump 0.7.0
5.2 Diff ────┘              │
                            │
5.4 Watch ──────────────────┘
```

**DAG:**
1. **5.1 Why** (no deps) — `why.py` + tests + CLI command
2. **5.2 Diff** (no deps, parallel with 5.1) — `diff.py` + tests + CLI command
3. **5.3 TUI** (depends on 5.1 + 5.2) — `tui/` package + tests + CLI command
4. **5.4 Watch** (no deps, parallel with 5.3) — `watcher.py` + tests + CLI command

5.1 and 5.2 can be developed in parallel.
5.3 and 5.4 can be developed in parallel (after 5.1 + 5.2).

---

## 7. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Textual API changes | TUI breaks | Pin `textual>=0.50,<1.0` |
| Large graphs slow BFS in `why` | UX degradation | `max_nodes` limit, depth limit |
| `git show` subprocess in `diff` | Performance, error handling | Cache parsed YAML, handle non-git dirs |
| watchfiles FSEvents on macOS | Missing events | watchfiles handles this natively via Rust notify crate |
| TUI complexity creep | Delayed delivery | 4-phase iterative build, each phase is shippable |

---

## 8. Non-Goals

- No new SQLite tables or schema changes
- No new core dependencies (textual + watchfiles are optional)
- No MCP tool additions in this phase (TUI is human-only)
- No vector search / sqlite-vec (remains deferred)
- No multi-repo support
- No web dashboard

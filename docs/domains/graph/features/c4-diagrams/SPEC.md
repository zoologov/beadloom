# C4 Diagrams

Auto-generate C4 architecture diagrams from the Beadloom architecture graph.

**Source:** `src/beadloom/graph/c4.py`

---

## Specification

### Purpose

Map the internal architecture graph (nodes, edges, `part_of` hierarchy) to the C4 model (System / Container / Component) and render it as Mermaid C4 or C4-PlantUML syntax. Supports three diagram levels (context, container, component) and correctly handles external systems and databases.

### Entry Point

```python
def map_to_c4(conn: sqlite3.Connection) -> tuple[list[C4Node], list[C4Relationship]]
```

| Parameter | Type                 | Description                                   |
|-----------|----------------------|-----------------------------------------------|
| `conn`    | `sqlite3.Connection` | Database connection with `nodes` and `edges` tables. |

**Returns:** A tuple of (c4_nodes, c4_relationships).

### Data Structures

All dataclasses are frozen (immutable).

#### `C4Node`

| Field         | Type           | Description                                      |
|---------------|----------------|--------------------------------------------------|
| `ref_id`      | `str`          | Node identifier.                                 |
| `label`       | `str`          | Display label (from `summary`, fallback to `ref_id`). |
| `c4_level`    | `str`          | `"System"`, `"Container"`, or `"Component"`.     |
| `description` | `str`          | Node description (from `summary`).               |
| `boundary`    | `str \| None`  | Parent ref_id via `part_of` edge (`None` for roots). |
| `is_external` | `bool`         | `True` if node has `external` tag.               |
| `is_database` | `bool`         | `True` if node has `database` or `storage` tag.  |

#### `C4Relationship`

| Field   | Type  | Description                               |
|---------|-------|-------------------------------------------|
| `src`   | `str` | Source node ref_id.                       |
| `dst`   | `str` | Destination node ref_id.                  |
| `label` | `str` | Edge kind (`"uses"` or `"depends_on"`).   |

### Algorithm

1. **Load nodes.** Query all rows from `nodes` table. Parse `extra` JSON column. Extract tags for `is_external`/`is_database` flag detection.
2. **Load edges.** Query all rows from `edges` table. Separate `part_of` edges (hierarchy) from `uses`/`depends_on` edges (relationships).
3. **Compute depth.** BFS from root nodes (nodes without a `part_of` parent). Orphan nodes default to depth 0.
4. **Assign C4 level.** Priority: explicit `c4_level` in node's `extra` JSON > depth heuristic (0=System, 1=Container, 2+=Component).
5. **Build C4 nodes.** For each node, create a `C4Node` with computed level, boundary (parent via `part_of`), and external/database flags.
6. **Collect relationships.** Each `uses`/`depends_on` edge becomes a `C4Relationship`.

### Level Filtering

```python
def filter_c4_nodes(
    nodes: list[C4Node],
    relationships: list[C4Relationship],
    *,
    level: str = "container",
    scope: str | None = None,
) -> tuple[list[C4Node], list[C4Relationship]]
```

| Level       | Behavior                                             |
|-------------|------------------------------------------------------|
| `context`   | Keep only System-level nodes + external nodes.       |
| `container` | Keep System and Container nodes (default).           |
| `component` | Keep children of `--scope` container. Requires `scope`. |

**Raises:** `ValueError` if `level="component"` without `scope`, or if `scope` ref_id not found.

### Internal Helpers

| Function               | Purpose                                                |
|------------------------|--------------------------------------------------------|
| `_compute_depths`      | BFS depth computation from roots via `part_of` hierarchy. |
| `_depth_to_c4_level`   | Map depth integer to C4 level string.                  |
| `_load_nodes`          | Load and parse all nodes from DB.                      |
| `_load_edges`          | Load edges, separate `part_of` from relationships.     |
| `_build_c4_node`       | Construct a single `C4Node` from parsed data.          |
| `_c4_element_name`     | Return C4 element name with `_Ext`/`Db` suffix.        |
| `_sanitize_id`         | Replace non-alphanumeric characters with underscores.  |
| `_filter_context`      | Filter nodes for context level.                        |
| `_filter_container`    | Filter nodes for container level.                      |
| `_filter_component`    | Filter nodes for component level within scope.         |

---

## Renderers

### Mermaid C4

```python
def render_c4_mermaid(
    nodes: list[C4Node],
    relationships: list[C4Relationship],
) -> str
```

Produces a `C4Container` diagram with:
- `System()`, `Container()`, `Component()` elements
- `_Ext` / `Db` variants for external/database nodes
- `System_Boundary()` for grouping children by `part_of` parent
- Nested `Container_Boundary()` for grandchildren
- `Rel()` for relationships

#### Mermaid Helpers

| Function                   | Purpose                                       |
|----------------------------|-----------------------------------------------|
| `_mermaid_node_line`       | Single Mermaid C4 node line.                  |
| `_mermaid_grandchildren`   | Nested `Container_Boundary` for grandchildren.|
| `_mermaid_top_level_node`  | Top-level node with optional boundary.        |
| `_mermaid_orphan_boundaries` | Boundaries for non-top-level parents.       |

### PlantUML C4

```python
def render_c4_plantuml(
    nodes: list[C4Node],
    relationships: list[C4Relationship],
) -> str
```

Produces a complete `@startuml`/`@enduml` block with:
- `!include` for the C4-PlantUML stdlib
- Standard macros: `System()`, `Container()`, `Component()`, `Rel()`
- `_Ext` / `Db` variants: `System_Ext()`, `Container_Ext()`, `ContainerDb()`, `Component_Ext()`, `ComponentDb()`
- `System_Boundary()` for grouping

#### PlantUML Helpers

| Function                      | Purpose                                     |
|-------------------------------|---------------------------------------------|
| `_node_macro`                 | PlantUML macro call for a single node.      |
| `_plantuml_top_level_node`    | Top-level node with optional boundary.      |
| `_plantuml_orphan_boundaries` | Boundaries for non-top-level parents.       |

---

## API

### Public Functions

```python
def map_to_c4(conn: sqlite3.Connection) -> tuple[list[C4Node], list[C4Relationship]]: ...
def filter_c4_nodes(nodes, relationships, *, level="container", scope=None) -> tuple[list[C4Node], list[C4Relationship]]: ...
def render_c4_mermaid(nodes: list[C4Node], relationships: list[C4Relationship]) -> str: ...
def render_c4_plantuml(nodes: list[C4Node], relationships: list[C4Relationship]) -> str: ...
```

All functions are defined in `src/beadloom/graph/c4.py`.

### Public Classes

```python
@dataclass(frozen=True)
class C4Node:
    ref_id: str
    label: str
    c4_level: str             # "System" | "Container" | "Component"
    description: str
    boundary: str | None      # part_of parent ref_id
    is_external: bool
    is_database: bool

@dataclass(frozen=True)
class C4Relationship:
    src: str
    dst: str
    label: str                # "uses" | "depends_on"
```

### Constants

```python
C4_LEVELS: frozenset[str]     # {"context", "container", "component"}
```

### CLI

```
beadloom graph [--format FORMAT] [--level LEVEL] [--scope REF_ID]
```

| Flag       | Default    | Description                                       |
|------------|------------|---------------------------------------------------|
| `--format` | `mermaid`  | Output format: `mermaid`, `c4`, `c4-plantuml`.    |
| `--level`  | `container`| C4 level: `context`, `container`, `component`.    |
| `--scope`  | (none)     | Required with `--level=component`. Container ref_id to zoom into. |

**Examples:**

```bash
beadloom graph                                    # default Mermaid flowchart
beadloom graph --format=c4                        # Mermaid C4 container diagram
beadloom graph --format=c4-plantuml               # PlantUML C4 diagram
beadloom graph --format=c4 --level=context        # system-level overview
beadloom graph --format=c4 --level=component --scope=graph  # graph internals
```

---

## Invariants

- `C4Node` and `C4Relationship` are immutable (frozen dataclasses).
- `map_to_c4()` output is sorted by `ref_id`.
- Orphan nodes (not reached by BFS) default to depth 0 (System level).
- Explicit `c4_level` in node `extra` JSON always overrides depth heuristic.
- `_sanitize_id` replaces all non-alphanumeric characters (except underscore) with `_`.
- `filter_c4_nodes` raises `ValueError` for `component` level without `scope`.
- Renderers produce deterministic output for a given input.

---

## Constraints

- Requires a populated SQLite database with `nodes` and `edges` tables.
- Only `uses` and `depends_on` edge kinds are mapped to C4 relationships.
- `part_of` edges define hierarchy (boundary grouping), not relationships.
- `touches_code` edges are excluded from the C4 model.
- Tags must be stored as a JSON list in the node's `extra` column under the `tags` key.

---

## Testing

Test file: `tests/test_c4.py`

### Unit Tests

- **Dataclass basics.** Verify `C4Node` and `C4Relationship` are frozen, fields accessible.
- **Empty graph.** `map_to_c4()` returns empty lists for an empty database.
- **Single root node.** Verify root gets `c4_level="System"`, no boundary.
- **Depth heuristic.** Verify depth 0=System, 1=Container, 2+=Component.
- **Explicit override.** `c4_level` in `extra` JSON overrides depth heuristic.
- **Tag detection.** `external` → `is_external`, `database`/`storage` → `is_database`.
- **Boundary grouping.** Children get `boundary` set to parent ref_id.
- **Relationships.** `uses`/`depends_on` edges → `C4Relationship`, `part_of` excluded.
- **Labels.** Label from `summary`, fallback to `ref_id`.
- **Orphans and cycles.** Orphan nodes default to System, cycles don't crash.

### Renderer Tests

- **Mermaid C4.** Valid `C4Container` header, `System_Boundary()`, `Rel()`, `_Ext`/`Db` variants.
- **PlantUML C4.** Valid `@startuml`/`@enduml`, `!include`, macros, boundaries, variants.
- **Element name helper.** Parametrized tests for all level × flag combinations.

### Filter Tests

- **Context level.** Keeps System + external, filters relationships.
- **Container level.** Keeps System + Container, excludes Component.
- **Component level.** Keeps children of scope, error without scope.
- **Edge cases.** Empty nodes, single node, unknown scope.

### CLI Integration Tests

- **Format options.** `--format=c4`, `--format=c4-plantuml` produce valid output.
- **Level options.** `--level=context`, `--level=container`, `--level=component --scope=...`.
- **Error paths.** `--level=component` without `--scope` returns error.
- **Backward compatibility.** `beadloom graph` (no flags) still works.

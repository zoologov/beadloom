# RFC: BDL-023 — C4 Architecture Diagrams

> **Status:** Approved
> **Created:** 2026-02-19

---

## Overview

Add C4 diagram generation (Context, Container, Component) as new output formats for the existing `beadloom graph` command. Beadloom's architecture graph already contains all the data needed for C4: `part_of` hierarchy (boundaries), node kinds with depth (levels), `uses`/`depends_on` edges (relationships), tags, and summaries. C4 is a natural projection of this data into an industry-standard visualization format.

## Motivation

### Problem
`beadloom graph` outputs a flat Mermaid flowchart with no abstraction levels. Developers cannot distinguish system boundaries from internal components, or external actors from internal services. There is no way to "drill down" into a specific domain.

### Solution
Extend the `graph` command with `--format=c4|c4-plantuml` and `--level=context|container|component` options. A new module `graph/c4.py` handles mapping nodes to C4 levels and rendering in Mermaid C4 / PlantUML C4 syntax.

## Technical Context

### Constraints
- Python 3.10+
- SQLite (WAL mode)
- Mermaid C4 syntax (GitHub markdown rendering support)
- C4-PlantUML library macros (`!include <C4/C4_Container>`)
- Backward compatibility: existing `beadloom graph` (Mermaid flowchart) remains unchanged

### Affected Areas

Discovered via `beadloom ctx graph`:
- `src/beadloom/graph/` — graph domain, new module `c4.py`
- `src/beadloom/services/cli.py` — extend `graph` command (new options)
- `.beadloom/_graph/services.yml` — support for new fields (`c4_level`, `c4_technology`, `c4_description`)
- `src/beadloom/graph/loader.py` — new fields go to `extra` JSON (no changes needed, already supported)

## Proposed Solution

### Approach

New module `src/beadloom/graph/c4.py` with clean separation of concerns:

1. **C4 Level Mapper** — determines C4 level for each node:
   - Priority 1: explicit `c4_level` field in `extra` JSON (from services.yml)
   - Priority 2: `part_of` depth (root=0 → System, depth=1 → Container, depth=2+ → Component)
   - Priority 3: tags (`external` → `_Ext`, `database`/`storage` → `Db`)

2. **C4 Mermaid Renderer** — generates Mermaid C4 syntax:
   - `C4Context` / `C4Container` / `C4Component` diagram types
   - `Person()`, `System()`, `Container()`, `Component()`, `Rel()`
   - `System_Boundary()` / `Container_Boundary()` for grouping

3. **C4 PlantUML Renderer** — generates C4-PlantUML:
   - `@startuml` / `@enduml` wrapper
   - `!include <C4/C4_Container>` (Context/Component respectively)
   - Standard macros: `System()`, `Container()`, `Rel()`

4. **CLI Integration** — new options for the `graph` command:
   - `--format=mermaid|c4|c4-plantuml` (default: mermaid)
   - `--level=context|container|component` (default: container)
   - `--scope=<ref-id>` (for component level drill-down)

### Changes

| File / Module | Change |
|---------------|--------|
| `src/beadloom/graph/c4.py` | **NEW**: C4 level mapping + Mermaid/PlantUML renderers |
| `src/beadloom/services/cli.py` | Extend `graph` command: `--format`, `--level`, `--scope` options |
| `tests/test_c4.py` | **NEW**: Unit tests for c4 module |
| `tests/test_cli_graph.py` | Integration tests for CLI with new options |
| `.beadloom/_graph/services.yml` | No changes required (extra fields already supported) |
| `src/beadloom/graph/loader.py` | No changes (c4_level goes to `extra` JSON automatically) |

### API Changes

**CLI (public):**
```bash
# New options for existing command
beadloom graph --format=c4                              # Mermaid C4 Container
beadloom graph --format=c4-plantuml                     # PlantUML C4 Container
beadloom graph --format=c4 --level=context              # C4 Context diagram
beadloom graph --format=c4 --level=component --scope=graph  # C4 Component
```

**Python API (internal, graph/c4.py):**
```python
@dataclass
class C4Node:
    ref_id: str
    name: str
    c4_level: str          # system | container | component | person
    technology: str        # "Python, SQLite"
    description: str       # from summary
    is_external: bool
    is_database: bool
    boundary_ref_id: str | None  # parent for grouping

@dataclass
class C4Relationship:
    src: str
    dst: str
    label: str             # edge kind or description
    technology: str        # optional

def map_to_c4(
    conn: sqlite3.Connection,
    level: str = "container",
    scope: str | None = None,
) -> tuple[list[C4Node], list[C4Relationship]]:
    """Map graph nodes/edges to C4 model."""

def render_c4_mermaid(
    nodes: list[C4Node],
    relationships: list[C4Relationship],
    title: str,
    level: str,
) -> str:
    """Render C4 nodes as Mermaid C4 syntax."""

def render_c4_plantuml(
    nodes: list[C4Node],
    relationships: list[C4Relationship],
    title: str,
    level: str,
) -> str:
    """Render C4 nodes as C4-PlantUML syntax."""
```

## Alternatives Considered

### Option A: Separate `beadloom c4` command
A standalone command instead of extending `graph`. Rejected: breaks UX consistency, duplicates graph data retrieval infrastructure.

### Option B: Structurizr DSL export
Generate `.dsl` files for Structurizr. Rejected for v1.8: narrow audience, Mermaid + PlantUML cover 90% of use cases. May be added in future phases.

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Mermaid C4 syntax instability | Low | Med | Test against current Mermaid version, update on changes |
| Complex graphs don't fit C4 well | Med | Low | `--level` + `--scope` for filtering; max_nodes limit |
| `c4_level` conflicts with heuristic | Low | Low | Explicit override always takes priority over heuristic |

## Open Questions

| # | Question | Decision |
|---|----------|----------|
| Q1 | Where to get project name for `title`? | Decided: root service node `name` or `ref_id` |
| Q2 | Show `touches_code` edges in C4? | Decided: No, only `uses`, `depends_on` — they have architectural significance |
| Q3 | Show `part_of` edges as Rel()? | Decided: No, `part_of` → `System_Boundary`/`Container_Boundary`, not relationships |

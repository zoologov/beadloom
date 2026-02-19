# PRD: BDL-023 — C4 Architecture Diagrams

> **Status:** Approved
> **Created:** 2026-02-19

---

## Problem

Beadloom generates Mermaid flowcharts (`beadloom graph`) showing nodes and edges as a flat graph. This format lacks industry-standard abstraction levels — developers cannot distinguish system boundaries from internal components, external actors from internal services. The C4 model (Simon Brown) is the de-facto standard for architecture visualization, but currently there is no tool that auto-generates C4 diagrams from a code-derived architecture graph.

Beadloom already has all the data needed for C4: `part_of` hierarchy (boundaries), node kinds with depth (levels), `uses`/`depends_on` edges (relationships), tags, and summaries — but this data is projected only as a flat Mermaid flowchart.

## Impact

- **Developers** cannot communicate architecture decisions using standard C4 notation without manually drawing diagrams
- **AI agents** have no structured way to present architecture at different abstraction levels
- **Teams** lose time maintaining hand-drawn C4 diagrams that drift from actual code structure
- **Beadloom** misses a competitive advantage — no AaC tool auto-generates C4 from real code structure

## Goals

- [ ] `beadloom graph --format=c4` produces valid C4 Container diagram in Mermaid syntax that renders in GitHub markdown
- [ ] `--format=c4-plantuml` produces equivalent PlantUML output compatible with C4-PlantUML library
- [ ] `--level=context|container|component` controls abstraction level for drill-down
- [ ] External systems and databases render with correct C4 stereotypes (`System_Ext`, `ContainerDb`)
- [ ] Zero-config value: works automatically on any beadloom project via `part_of` depth heuristic

## Non-goals

- C4 Code level (Level 4) — too granular, not practical for architecture overview
- Interactive/clickable diagrams — that's TUI territory (Phase 12.10)
- Custom C4 styling/theming — standard rendering is sufficient
- Structurizr DSL export — may be added in future phases

## User Stories

### US-1: Architecture presentation
**As** a developer, **I want** to run `beadloom graph --format=c4`, **so that** I get a C4 Container diagram for documentation and architecture reviews.

**Acceptance criteria:**
- [ ] Output is valid Mermaid C4 syntax
- [ ] System boundaries group related containers
- [ ] Relationships show labels (edge descriptions)

### US-2: PlantUML integration
**As** a team lead, **I want** to run `beadloom graph --format=c4-plantuml`, **so that** I can include C4 diagrams in our PlantUML-based documentation pipeline.

**Acceptance criteria:**
- [ ] Output uses standard C4-PlantUML macros (`System()`, `Container()`, `Rel()`)
- [ ] Output renders correctly with C4-PlantUML library

### US-3: Abstraction level control
**As** an architect, **I want** to use `--level=context|container|component` and `--scope=<ref-id>`, **so that** I can drill down from system overview to component details.

**Acceptance criteria:**
- [ ] Context level shows system + external actors
- [ ] Container level shows top-level domains
- [ ] Component level shows internals of a specific container

### US-4: External system rendering
**As** a developer, **I want** nodes tagged `external` or `database` to render with correct C4 stereotypes, **so that** the diagram accurately represents system boundaries.

**Acceptance criteria:**
- [ ] `external` tag → `System_Ext` / `Container_Ext`
- [ ] `database`/`storage` tag → `ContainerDb`

## Acceptance Criteria (overall)

- [ ] `beadloom graph --format=c4` produces valid, renderable Mermaid C4 diagram
- [ ] `beadloom graph --format=c4-plantuml` produces valid C4-PlantUML output
- [ ] Three C4 levels supported: context, container, component
- [ ] External/database nodes render with correct C4 stereotypes
- [ ] Zero-config: works on any beadloom project via `part_of` depth heuristic
- [ ] Configurable: `c4_level`, `c4_technology`, `c4_description` fields in services.yml
- [ ] Tests: >=80% coverage for new code
- [ ] mypy --strict + ruff clean

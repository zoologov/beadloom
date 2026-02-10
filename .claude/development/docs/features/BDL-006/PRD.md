# PRD: BDL-006 — Phase 5: Developer Experience (v0.7)

> **Status:** Implemented (v0.7.0)
> **Date:** 2026-02-11
> **Phase:** 5 (v0.7)
> **Depends on:** BDL-005 (v0.6.0 — Performance complete)

---

## 1. Problem Statement

Beadloom v0.6 is powerful but CLI-only. Developers must memorize commands, mentally parse JSON/text output, and manually trigger reindexing. There is no visual way to explore the knowledge graph, understand node relationships, or see what changed. This friction slows adoption and limits the "aha moment" for new users.

## 2. Goals

| Goal | Metric |
|------|--------|
| **Intuitive graph exploration** | User can browse full graph interactively in < 30s |
| **Instant impact analysis** | `beadloom why <ref>` answers "what breaks?" in < 2s |
| **Change visibility** | `beadloom diff` shows graph delta in one command |
| **Zero-friction reindexing** | Watch mode keeps index fresh without manual commands |

## 3. User Stories

### US-1: Interactive Graph Explorer (TUI)
**As a** developer onboarding to a new codebase,
**I want** an interactive terminal UI showing domains, nodes, edges, and doc coverage,
**so that** I can understand the architecture visually without reading YAML files.

**Acceptance criteria:**
- `beadloom ui` launches a Textual-based TUI
- Left panel: domain list with doc coverage indicators
- Right panel: node details, edges, summary, sync status
- Bottom panel: graph visualization (ASCII edges)
- Keyboard navigation: arrows, Enter, `/` for search, `q` to quit
- Mouse support for panel selection
- Requires `beadloom[tui]` extra (Textual not in core deps)

### US-2: Node Impact Analysis (Why)
**As a** developer about to modify a feature,
**I want** to see what upstream dependencies and downstream dependents a node has,
**so that** I can assess the blast radius of my change.

**Acceptance criteria:**
- `beadloom why <ref_id>` outputs:
  - Node header (ref_id, kind, summary)
  - Upstream tree (what this node depends on)
  - Downstream tree (what depends on this node)
  - Impact summary (count of transitive downstream, doc coverage, sync status)
- Uses Rich Tree for rendering
- `--depth N` controls traversal depth (default: 3)
- `--json` for machine-readable output
- Completes in < 2s for graphs up to 200 nodes

### US-3: Graph Change Diff
**As a** developer reviewing a PR or preparing a release,
**I want** to see what nodes and edges changed since a given git ref,
**so that** I can understand architectural impact of code changes.

**Acceptance criteria:**
- `beadloom diff` compares current graph with HEAD (default)
- `beadloom diff --since=<ref>` compares with any git ref (commit, tag, branch)
- Output shows: added/removed/changed nodes, added/removed edges
- Changed nodes show before/after summary
- Rich-formatted table output
- `--json` for machine-readable output
- Exit code 0 = no changes, 1 = changes detected (CI-friendly)

### US-4: Watch Mode (Auto-Reindex)
**As a** developer actively coding,
**I want** Beadloom to automatically reindex when I save files,
**so that** the graph, search, and context are always up-to-date.

**Acceptance criteria:**
- `beadloom watch` starts file watcher in foreground
- Watches: graph YAML, source files, doc files (respects project config)
- 500ms debounce after last file change
- Uses incremental reindex (from Phase 4)
- Prints timestamped log: `[HH:MM:SS] 2 files changed -> reindexed (14ms)`
- Graph YAML change triggers full reindex, source/doc triggers incremental
- Ctrl+C for clean shutdown
- Requires `beadloom[watch]` extra (watchfiles not in core deps)

## 4. Out of Scope

- Web-based dashboard (Phase 6+)
- Multi-repo graph federation (Phase 6+)
- Architecture lint / constraint rules (Phase 6+)
- sqlite-vec vector search (deferred from Phase 4)

## 5. Dependencies

| Dependency | Version | Extra group | Size |
|------------|---------|-------------|------|
| `textual` | >= 0.50 | `[tui]` | ~5 MB |
| `watchfiles` | >= 0.20 | `[watch]` | ~2 MB |

No new core dependencies. Both are optional extras.

## 6. Priority & Effort

| # | Feature | Priority | Effort | Rationale |
|---|---------|----------|--------|-----------|
| 5.1 | Why | P1 | M | No new deps, high value, enables TUI |
| 5.2 | Diff | P1 | M | No new deps, CI-friendly, enables TUI |
| 5.3 | TUI | P1 | L | Integrates why + diff, flagship feature |
| 5.4 | Watch | P2 | M | Independent, lower priority |

## 7. Success Criteria

- All 4 features implemented with tests (>= 80% coverage)
- mypy --strict clean
- ruff clean
- TUI launches and is interactive on macOS + Linux
- `beadloom why` and `beadloom diff` work without optional extras
- Total test count >= 520
- Version bumped to 0.7.0

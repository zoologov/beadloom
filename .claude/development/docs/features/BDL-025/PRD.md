# PRD: BDL-025 — Interactive Architecture TUI

> **Status:** Approved
> **Created:** 2026-02-20

---

## Problem

Beadloom's CLI commands give snapshots: you run `beadloom status`, read the output, then forget it. Every exploration step (checking debt, tracing dependencies, inspecting docs) requires a separate command with separate output. There is no persistent workspace for architecture work.

The current TUI (`beadloom ui`) is a basic read-only viewer with three widgets (DomainList, NodeDetail, StatusBar). It can only display nodes and their metadata — no debt monitoring, no dependency tracing, no live updates, no keyboard-driven actions.

Architecture exploration is inherently interactive: developers need to navigate the graph, drill into nodes, trace dependency paths, check doc status, and trigger maintenance actions — all in a single session. The current tool-per-command model breaks this workflow.

## Impact

- **Developers** lose context switching between commands. Architecture exploration takes 10-15 CLI invocations that could be a single interactive session.
- **AI agents** benefit from TUI testing (Textual's headless mode) — the same data providers can serve both TUI widgets and MCP tools.
- **Competitive advantage** — no Architecture-as-Code competitor (Greptile, Augment, DeepDocs) has a terminal-native interactive interface. Works over SSH, in tmux, in containers.

## Goals

- [ ] `beadloom tui` opens an interactive multi-screen dashboard in < 1s
- [ ] Dashboard screen shows debt score, graph tree, lint violations, activity sparklines
- [ ] Graph explorer allows navigating 500+ nodes with expand/collapse and node detail
- [ ] Live file watcher detects source changes and triggers reindex on keypress
- [ ] Dependency path tracer shows upstream/downstream paths interactively
- [ ] Doc status panel shows fresh/stale/missing docs with action keys
- [ ] Context bundle inspector previews what agents see via `beadloom ctx`
- [ ] Keyboard-driven actions: reindex, lint, sync-check, generate docs, snapshot

## Non-goals

- Web-based dashboard (D3/Cytoscape) — future phase
- Built-in LLM integration — violates "agent-native" principle
- Multi-repo federation view — Phase 13+
- Custom themes/branding — keep Textual defaults with minimal CSS

## User Stories

### US-1: Architecture Dashboard
**As** a developer, **I want** to see the overall architecture health at a glance (debt score, graph overview, lint status, activity), **so that** I can prioritize maintenance work without running multiple commands.

**Acceptance criteria:**
- [ ] Dashboard shows debt score gauge with severity coloring
- [ ] Graph tree displays all nodes with expand/collapse
- [ ] Lint violations panel shows errors and warnings
- [ ] Activity section shows recent git activity
- [ ] Status bar shows node/edge/doc counts

### US-2: Interactive Graph Explorer
**As** a developer, **I want** to navigate the architecture graph interactively with keyboard, **so that** I can explore node details, edges, symbols, and routes without leaving the TUI.

**Acceptance criteria:**
- [ ] Tree widget with expand/collapse for domain hierarchy
- [ ] Enter opens node detail view (symbols, edges, routes, tests)
- [ ] `d` shows downstream dependents, `u` shows upstream dependencies
- [ ] `c` previews context bundle, `o` opens source in $EDITOR

### US-3: Live File Watcher
**As** a developer, **I want** the TUI to detect when source files change, **so that** I can reindex and see updated architecture data without restarting.

**Acceptance criteria:**
- [ ] File watcher monitors source directories from graph config
- [ ] Changes debounced (500ms) to avoid spam
- [ ] Status bar shows "changes detected, press [r]" badge
- [ ] `r` key triggers background reindex with progress indication

### US-4: Dependency Path Tracer
**As** a developer, **I want** to trace dependency paths between nodes interactively, **so that** I can understand impact and plan refactoring.

**Acceptance criteria:**
- [ ] Interactive `why` panel with source/target selection
- [ ] Shows all dependency paths between two nodes
- [ ] Highlights cycles in red
- [ ] Reverse mode: "who depends on me"

### US-5: Doc Status Panel
**As** a developer, **I want** to see all documentation status (fresh/stale/missing) in one view with actionable keys, **so that** I can maintain doc-code sync efficiently.

**Acceptance criteria:**
- [ ] Table showing all nodes with doc status (fresh/stale/missing)
- [ ] Color-coded: green (fresh), yellow (stale), red (missing)
- [ ] `g` generates doc skeleton, `p` views polish data

### US-6: Context Bundle Inspector
**As** a developer, **I want** to preview what `beadloom ctx` returns for any node, **so that** I understand what AI agents see.

**Acceptance criteria:**
- [ ] Shows exact context bundle content
- [ ] Displays token count and section breakdown
- [ ] Shows dependencies included in the bundle

### US-7: Keyboard-driven Actions
**As** a developer, **I want** to trigger common beadloom commands via keyboard shortcuts, **so that** I never leave the TUI during architecture work.

**Acceptance criteria:**
- [ ] `r` — reindex, `l` — lint, `s` — sync-check
- [ ] `g` — generate docs, `S` — save snapshot
- [ ] `/` — FTS5 search, `?` — help overlay
- [ ] Action results shown in status bar / notification panel

## Acceptance Criteria (overall)

- [ ] `beadloom tui` launches interactive dashboard in < 1s
- [ ] 3 screens: Dashboard, Explorer, DocStatus — navigable via `1`, `2`, `3` keys
- [ ] 15+ keyboard bindings working correctly
- [ ] File watcher with debounced change detection
- [ ] All data reads from existing infrastructure (read-only SQLite)
- [ ] TUI remains optional dependency: `beadloom[tui]`
- [ ] 500+ nodes render smoothly (< 100ms tree rebuild)
- [ ] Memory usage < 50MB
- [ ] Works in SSH, tmux, containers
- [ ] >= 80% test coverage using Textual's headless pilot

# PRD: BDL-021 — v1.7.0: AaC Rules v2, Init Quality, Architecture Intelligence

> **Status:** Approved
> **Created:** 2026-02-17

---

## Problem

Beadloom v1.6.0 has three critical gaps preventing adoption on real projects:

1. **Primitive rule engine** — The current engine supports only `require` rules (check that a node has a specific edge). This covers ~5% of architecture enforcement needs. Real projects need forbidden dependencies, layer direction enforcement, cycle detection, and import-level boundaries. The rule engine is Beadloom's core differentiator ("architecture enforcement, not just documentation"), but it's too limited to enforce real constraints.

2. **Poor bootstrap quality** — Dogfooding on a React Native + Expo project (UX Issues #32-37) revealed that `beadloom init` captures only 35% of real project architecture: 6 of 17 nodes detected, missing `components/`, `hooks/`, `contexts/`, `modules/`, `types/`, `constants/`, `utils/`. The init flow is interactive-only (no CI/agent support), generates a failing lint rule (`service-needs-parent` on root), doesn't offer doc generation, and doesn't link existing docs.

3. **No architecture change visibility** — No way to see what changed in the architecture graph between commits or branches. `beadloom why` shows impact but lacks reverse direction (what X depends on), depth control, and tree visualization. CI pipelines can't detect unexpected architecture drift.

**Evidence:**
- 533 imports already indexed for a typical project — import-based boundary enforcement is within reach
- Bootstrap quality ratio: 35% (6/17 nodes) on real-world React Native project
- UX Issues #32-37 filed during dogfooding
- No competitor offers local-first, Git-versioned architecture enforcement at this level

## Impact

- **Developers** get real architecture enforcement: forbidden imports, layer violations, circular dependencies caught at lint time
- **Teams** get reliable `beadloom init` that captures 80%+ of project architecture on first run
- **CI/CD pipelines** can gate on architecture drift with `beadloom diff` and `beadloom lint --strict`
- **AI agents** can use non-interactive init mode and richer `beadloom why` for impact analysis

Without this: Beadloom remains a documentation tool, not an architecture enforcement platform. The core value proposition ("ArchUnit for any stack") is not delivered.

## Goals

- [ ] Rule engine supports 6 rule types: require, forbid, layers, forbid_cycles, forbid_import, check
- [ ] `beadloom lint --strict` catches forbidden cross-layer imports, dependency cycles, and oversized domains
- [ ] `beadloom init` on a React Native project produces 15+ nodes (was 6), 80%+ architecture coverage
- [ ] `beadloom init --mode bootstrap --yes` works non-interactively for CI and agents
- [ ] `beadloom diff HEAD~5` shows added/removed/changed nodes, edges, symbols
- [ ] `beadloom why <ref-id> --reverse` shows transitive dependencies with tree format
- [ ] All UX Issues #32-36 resolved
- [ ] Tests: 80%+ coverage, all existing tests pass

## Non-goals

- Multi-repo federation (Phase 13, v1.8)
- Semantic search / embeddings (Phase 14, v2.0)
- Web dashboard or VS Code extension (STRATEGY-3)
- New language parsers (9 languages is sufficient)
- Plugin system (Phase 14.5, v2.0)

## User Stories

### US-1: Architecture Boundary Enforcement
**As** a developer, **I want** to define forbidden dependencies between architecture layers, **so that** `beadloom lint` catches violations before they reach production.

**Acceptance criteria:**
- [ ] Can define `forbid` rules in `rules.yml` preventing edges between tagged node groups
- [ ] Can define `layers` with ordered enforcement (top-down)
- [ ] `beadloom lint --strict` returns exit code 1 on violations
- [ ] Error messages show source node, target node, and violated rule

### US-2: Circular Dependency Detection
**As** a developer, **I want** Beadloom to detect circular dependencies in the architecture graph, **so that** I can prevent architectural spaghetti.

**Acceptance criteria:**
- [ ] `forbid_cycles` rule type detects cycles in `uses`/`depends_on` edges
- [ ] Reports the full cycle path (A → B → C → A)
- [ ] Configurable `max_depth` for performance

### US-3: Reliable First-Time Init
**As** a new user, **I want** `beadloom init` to detect 80%+ of my project architecture, **so that** I get value from Beadloom immediately without manual graph editing.

**Acceptance criteria:**
- [ ] All top-level directories with code files are scanned (not just manifest-adjacent)
- [ ] Non-interactive mode available (`--mode bootstrap --yes --force`)
- [ ] Root service doesn't fail lint
- [ ] Doc skeletons generated as part of init flow
- [ ] Existing docs auto-linked to graph nodes where possible

### US-4: Architecture Change Tracking
**As** a tech lead, **I want** to see what changed in the architecture graph between commits, **so that** I can review architecture drift in PRs and CI.

**Acceptance criteria:**
- [ ] `beadloom diff HEAD~5` shows added/removed/changed nodes and edges
- [ ] JSON output for CI integration (`--json`)
- [ ] `beadloom why <ref-id> --reverse` shows what X depends on
- [ ] `beadloom snapshot save/list/compare` for historical comparison

## Acceptance Criteria (overall)

- [ ] All 14 tasks from Phases 12, 12.5, 12.6 implemented and tested
- [ ] `beadloom lint --strict` passes on beadloom's own codebase with new rule types
- [ ] Dogfood: re-run `beadloom init` on external React Native project, verify 80%+ coverage
- [ ] UX Issues #32-36 closed in BDL-UX-Issues.md
- [ ] All tests pass, coverage >= 80%
- [ ] `beadloom sync-check` clean, `beadloom doctor` clean
- [ ] CHANGELOG.md updated for v1.7.0

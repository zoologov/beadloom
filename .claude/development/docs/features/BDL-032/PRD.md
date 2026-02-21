# PRD: BDL-032 — Enhanced Architecture Rules

> **Status:** Approved
> **Created:** 2026-02-21

---

## Problem

Beadloom's rule engine supports 7 rule types but its own project (`rules.yml`) uses only 2 (require + deny) across 4 rules. This means:

1. **Underutilized dogfooding** — 5 rule types (forbid_cycles, forbid_import, forbid, layer, cardinality) are never exercised on beadloom's own codebase. Bugs or UX issues in these features go undetected.
2. **Broken rule** — `service-needs-parent` requires every service to be `part_of beadloom`, but the root node `beadloom` is itself `kind: service`. The rule passes only because of a self-referencing `part_of` edge — an accidental workaround, not correct behavior.
3. **No cycle protection** — circular `depends_on` chains would break `beadloom why` and impact analysis, but nothing prevents them.
4. **No code boundary enforcement** — DDD domains exist in the graph but nothing verifies that actual Python imports respect these boundaries (e.g., TUI importing infrastructure directly).
5. **NodeMatcher lacks `exclude`** — the matcher supports only positive filters (`kind`, `ref_id`, `tag`). There's no way to say "all services except beadloom", forcing rule removal instead of refinement.

## Impact

- **Beadloom developers** lose architecture-as-code guarantees on the project that implements them.
- **External users** get no real-world example of advanced rules (forbid_cycles, layer, forbid_import, cardinality) — only basic require/deny.
- **Architecture drift** in beadloom itself goes undetected until manual review.

## Goals

- [ ] Rule engine covers all 7 rule types on beadloom's own codebase
- [ ] NodeMatcher supports `exclude` filter for root-node edge cases
- [ ] `beadloom lint --strict` catches real boundary violations (cycles, import leaks, layer violations)
- [ ] `rules.yml` serves as a comprehensive example for external users

## Non-goals

- Rewriting the rule engine architecture
- Adding new rule types beyond the existing 7
- Supporting regex or complex predicates in NodeMatcher

## User Stories

### US-1: Exclude filter for root node
**As** a beadloom user, **I want** to write `for: { kind: service, exclude: beadloom }` in a require rule, **so that** I can mandate edges for all services except the root.

**Acceptance criteria:**
- [ ] NodeMatcher accepts `exclude` field (single ref_id or list)
- [ ] Excluded nodes are skipped during rule evaluation
- [ ] `service-needs-parent` rule works correctly with exclude

### US-2: Cycle detection
**As** a beadloom user, **I want** `forbid_cycles` to catch circular dependencies, **so that** `beadloom why` and impact analysis remain correct.

**Acceptance criteria:**
- [ ] `forbid_cycles` rule added to rules.yml for `depends_on` edges
- [ ] Lint reports cycle path when found
- [ ] Beadloom's own graph passes (no cycles)

### US-3: Code boundary enforcement
**As** a beadloom user, **I want** `forbid_import` rules to enforce DDD boundaries, **so that** modules don't bypass the service layer.

**Acceptance criteria:**
- [ ] At least 2 `forbid_import` rules in rules.yml
- [ ] Actual Python imports are checked (not just graph edges)
- [ ] Beadloom's own codebase passes lint

### US-4: Layer architecture
**As** a beadloom user, **I want** `layer` rules to enforce dependency direction, **so that** lower layers never import from higher layers.

**Acceptance criteria:**
- [ ] Layer rule defines architecture tiers (service → domain → feature)
- [ ] Violations reported with source and target layer
- [ ] Beadloom's own graph passes

### US-5: Cardinality checks
**As** a beadloom user, **I want** `cardinality` rules to detect oversized modules, **so that** architecture smells are caught early.

**Acceptance criteria:**
- [ ] At least 1 cardinality rule in rules.yml
- [ ] Checks max_symbols or max_files per node
- [ ] Severity is `warn` (not blocking)

## Acceptance Criteria (overall)

- [ ] NodeMatcher `exclude` filter implemented with tests
- [ ] `rules.yml` upgraded from v1 to v3 (tags support)
- [ ] Rules expanded from 4 to 8+ covering all 7 types
- [ ] `beadloom lint --strict` passes on beadloom's own codebase (0 violations)
- [ ] All existing tests pass + new tests for exclude filter
- [ ] UX feedback collected in BDL-UX-Issues.md

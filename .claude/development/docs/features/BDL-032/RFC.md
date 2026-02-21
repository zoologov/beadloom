# RFC: BDL-032 — Enhanced Architecture Rules

> **Status:** Approved
> **Created:** 2026-02-21

---

## Overview

Expand beadloom's own `rules.yml` from 4 rules (2 types) to 8+ rules (all 7 types), add `exclude` filter to NodeMatcher, and upgrade schema from v1 to v3. This makes beadloom a comprehensive dogfood project for its own AAC (Architecture as Code) system.

## Motivation

### Problem
The rule engine supports 7 rule types but beadloom's own project exercises only `require` and `deny`. Five evaluators (forbid_cycles, forbid_import, forbid, layer, cardinality) are never tested against a real codebase. The `service-needs-parent` rule works by accident (self-referencing edge).

### Solution
1. Add `exclude` field to `NodeMatcher` dataclass — allows filtering out specific nodes (e.g., root service)
2. Upgrade `rules.yml` to v3 with tags — enables layer rules
3. Add rules covering all 7 types — comprehensive dogfooding

## Technical Context

### Constraints
- Python 3.10+
- NodeMatcher is a frozen dataclass (`rule_engine.py:33-52`)
- `matches()` method uses AND logic across set fields
- Schema v3 already supported (tags block) — no parser changes needed
- Current graph has known coupling: infrastructure `depends_on` context-oracle, doc-sync, graph (reindex orchestrator)

### Affected Areas
- `src/beadloom/graph/rule_engine.py` — NodeMatcher dataclass + `matches()` method
- `.beadloom/_graph/rules.yml` — rule definitions
- `tests/test_rule_engine.py` — unit tests for exclude filter

## Proposed Solution

### Approach

**Part A: NodeMatcher `exclude` filter**

Add optional `exclude` field to NodeMatcher. Semantics: if a node's `ref_id` is in the exclude list, `matches()` returns False even if all other filters pass.

```
NodeMatcher(kind="service", exclude=["beadloom"])
# Matches cli, mcp-server, tui — but NOT beadloom
```

YAML syntax:
```yaml
require:
  for: { kind: service, exclude: [beadloom] }
  has_edge_to: { ref_id: beadloom }
  edge_kind: part_of
```

**Part B: rules.yml upgrade to v3**

```yaml
version: 3
tags:
  layer-service: [cli, mcp-server, tui]
  layer-domain: [context-oracle, doc-sync, graph, onboarding]
  layer-infra: [infrastructure]
```

**Part C: New rules**

| # | Name | Type | Purpose |
|---|------|------|---------|
| 1 | domain-needs-parent | require | (existing) Every domain part_of beadloom |
| 2 | feature-needs-domain | require | (existing) Every feature part_of a domain |
| 3 | service-needs-parent | require | (fixed) Every service except beadloom part_of beadloom |
| 4 | no-domain-depends-on-service | deny | (existing) Domains must not import from services |
| 5 | no-dependency-cycles | forbid_cycles | No circular depends_on chains |
| 6 | tui-no-direct-infra | forbid_import | TUI must not import infrastructure directly |
| 7 | onboarding-no-direct-infra | forbid_import | Onboarding must not import infrastructure directly |
| 8 | architecture-layers | layer | Services → Domains → Infrastructure (warn) |
| 9 | domain-size-limit | cardinality | Max 15 features per domain (warn) |

**Note on layer rule severity:** The current graph has infrastructure → {context-oracle, doc-sync, graph} `depends_on` edges (reindex orchestrator). This is a known architectural coupling. Layer rule uses `severity: warn` to flag it without blocking CI. Resolving this coupling is out of scope for BDL-032.

### Changes

| File / Module | Change |
|---------------|--------|
| `src/beadloom/graph/rule_engine.py` | Add `exclude` field to NodeMatcher, update `matches()`, update `_parse_node_matcher()` |
| `.beadloom/_graph/rules.yml` | Upgrade to v3, add 5 new rules, fix service-needs-parent |
| `tests/test_rule_engine.py` | Tests for exclude filter: positive, negative, list, empty |

### API Changes

NodeMatcher dataclass gains one optional field:
- `exclude: tuple[str, ...] | None = None` — list of ref_ids to exclude from matching

No CLI changes. No new commands. Existing `beadloom lint` works unchanged.

## Alternatives Considered

### Option A: Change root node kind to `system`
Change beadloom from `kind: service` to `kind: system`, avoiding the exclude problem. Rejected — changes graph semantics, breaks existing rules, requires new kind in schema.

### Option B: Skip NodeMatcher changes, just add rules
Add only the rules that work without exclude, remove `service-needs-parent`. Rejected — loses the require rule for services, and `exclude` is valuable for external users too.

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Layer rule flags existing infra coupling | High | Low | severity: warn, documented as known |
| forbid_import may flag legitimate cross-domain imports | Medium | Low | Verify before adding; adjust globs |
| Exclude filter changes frozen dataclass API | Low | Low | Backward compatible (optional field) |

## Open Questions

| # | Question | Decision |
|---|----------|----------|
| Q1 | Should exclude accept single string or only list? | Decided: both — normalize to tuple internally |
| Q2 | Should layer rule be error or warn? | Decided: warn (known infra coupling) |

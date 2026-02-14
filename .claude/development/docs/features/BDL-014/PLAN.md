# PLAN: BDL-014 — Agent Prime (Cross-IDE Context Injection)

> **Date:** 2026-02-14

---

## DAG

```
D3 (AGENTS.md v2) ──┐
                     ├──→ D1 (prime_context core) ──→ D2 (CLI prime)
                     │                              └──→ D5 (MCP prime)
D4 (setup-rules) ───┘
                     └──→ D6 (init integration)

D7 (tests) ← depends on D1-D6
D8 (docs)  ← depends on D1-D6
```

---

## Waves

### Wave 1 (parallel, no dependencies)

| Bead | Deliverable | Priority | Description |
|------|-------------|----------|-------------|
| .1 | D3: AGENTS.md v2 | P0 | Enhanced template with rules.yml injection, `## Custom` preservation, `prime` instruction |
| .2 | D4: setup-rules | P1 | `setup_rules_auto()` in scanner.py + `setup-rules` CLI command |

### Wave 2 (depends on Wave 1)

| Bead | Deliverable | Priority | Description |
|------|-------------|----------|-------------|
| .3 | D1: prime_context() core | P0 | Core function: static (AGENTS.md + rules.yml) + dynamic (DB queries), markdown/JSON output |

### Wave 3 (parallel, depends on Wave 2)

| Bead | Deliverable | Priority | Description |
|------|-------------|----------|-------------|
| .4 | D2: CLI prime | P0 | `beadloom prime [--json] [--update] [--project]` |
| .5 | D5: MCP prime | P1 | 10th MCP tool, no params, returns JSON |
| .6 | D6: init integration | P1 | Call `setup_rules_auto()` in `bootstrap_project()`, update init output |

### Wave 4 (depends on all above)

| Bead | Deliverable | Priority | Description |
|------|-------------|----------|-------------|
| .7 | D7: Tests | P0 | 16 tests: unit (prime_context, agents_md, setup_rules) + integration (CLI, MCP) |

### Wave 5 (depends on all above)

| Bead | Deliverable | Priority | Description |
|------|-------------|----------|-------------|
| .8 | D8: Documentation | P2 | Graph node `agent-prime`, SPEC.md, update CLI/MCP docs |

---

## Critical Path

```
D3 (AGENTS.md v2) → D1 (prime core) → D2 (CLI) → D7 (tests) → D8 (docs)
```

---

## Estimates

| Wave | Beads | Parallel? |
|------|-------|-----------|
| Wave 1 | 2 | Yes |
| Wave 2 | 1 | No |
| Wave 3 | 3 | Yes |
| Wave 4 | 1 | No |
| Wave 5 | 1 | No |
| **Total** | **8** | |

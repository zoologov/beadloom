# ACTIVE: BDL-062 — Graph metadata is an unchecked surface

> **Created:** 2026-08-26
> **Branch:** `features/BDL-062` (from `main` @ `cdc16de`)

---

## Beads

| Bead | Role | Status | Note |
|---|---|---|---|
| `beadloom-viaj` | feature | open | parent |
| `.1` | dev | open | `graph_summary_facts` — waits on `.3`'s fact contract (see below) |
| `.2` | dev | open | `doc_area_coherence` |
| `.3` | dev | open | audit stops describing itself |
| `.4` | dev | blocked | the corrections |
| `.5` | test | blocked | bite tests + non-Beadloom fixture |
| `.6` | review | blocked | clean room |
| `.7` | tech-writer | blocked | README en+ru + guides |
| `.8` | chore | blocked | release 3.0.1 |

## Deviation from PLAN — wave 1 is split

PLAN.md runs `.1`, `.2`, `.3` as one wave. They are dependency-independent but **not
file-independent**: `.1` consumes the audit's fact set and `.3` reshapes exactly that
surface (`doc_sync/audit.py`). Three agents on one working tree would collide there.

Actual order:

```
wave 1a   .2 (graph/rules/)  ‖  .3 (doc_sync/audit.py, scanner.py)   — disjoint files
wave 1b   .1 (graph/rules/, consumes .3's fact contract)
wave 2    .4 → .5 → .6 → .7 → .8
```

`.2` needs no facts at all — it is pure graph — so it parallelises cleanly with `.3`.
Bead dependencies are unchanged; this is a scheduling decision, not a DAG change.

## Baseline to capture before `.4`

`.1`'s acceptance is that it is RED on `main`@`cdc16de`. That output must be captured while
the drift is still present — a rule first observed green proves nothing (TESTS MUST BITE,
CAPTURE DON'T RE-RUN).

Known-red instances at baseline:

- `beadloom` root summary — `v1.5.0` vs computed `3.0.0`
- `mcp-server` summary — `14 tools` vs `len(MCP_TOOL_CATALOG)` = 18
- `.2`: `doctor`, `watcher`, `debt-report`, `reindex` against a 69/73 dominant convention
- `.3`: `version` at `not_covered`, zero mentions; two facts sourced from Beadloom itself

## Progress log

**2026-08-26** — `/task-init` complete. PRD, RFC, CONTEXT, PLAN written and Approved (owner
authorised the whole chain in one instruction rather than four sequential approvals).
Parent + 8 beads created, dependencies wired, `bd ready` confirms only `.1`/`.2`/`.3` open.
Branch cut from `main` @ `cdc16de`.

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

**2026-08-26** — Wave 1a launched: `.2` (`doc_area_coherence`) and `.3` (audit stops
describing itself) running concurrently on disjoint files. `.1` held for `.3`'s fact contract.

Coordinator scoping pass while the wave runs (read-only, no files the agents own):

- **`.7`'s scope is smaller than the owner's audit suggested.** The "14 tools" drift does NOT
  exist in prose — README, guides and `docs/services/mcp.md` all say 18, and "14 graph
  read/write tools" is a documented subset with an `ignore` triple explaining it. The only
  stale 14 is the graph summary, already owned by `.4`.
- **`.7`'s real target found instead:** `docs/guides/multi-agent-development.md` and its `.ru`
  twin are pinned to 2.0.0 — "the core principle of 2.0.0", seven such framings each. Three
  majors of content (guards, waves, doc spaces, federation) are absent from the guide that
  claims to describe the process.
- **A false defect avoided, recorded because the reasoning nearly shipped.** `version` at
  `not_covered` with zero mentions looked like a broken scanner. It is not: every version
  literal in the repo is a dependency pin or an explicitly suppressed historical reference
  with a stated reason. The audit correctly reports that no document states the current
  version as a claim. `.3`'s requirement is unchanged; the "extraction is broken" theory is
  withdrawn. (REPORTS ARE NOT EVIDENCE, applied to the coordinator's own reasoning.)
- **BDL-UX #193 opened** — `framework_count` returns 84 (nodes declaring a framework) while
  the distinct count is 1 (pytest), and both the fact name and its scanner keywords promise
  the latter. Dormant until a document states the true number, then a false mismatch. Same
  family as this feature; handed to `.3` with two fix candidates and the choice left open.

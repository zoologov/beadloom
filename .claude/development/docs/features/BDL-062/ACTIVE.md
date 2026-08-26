# ACTIVE: BDL-062 — Graph metadata is an unchecked surface

> **Created:** 2026-08-26
> **Branch:** `features/BDL-062` (from `main` @ `cdc16de`)

---

## Beads

| Bead | Role | Status | Note |
|---|---|---|---|
| `beadloom-viaj` | feature | open | parent |
| `.1` | dev | open | `graph_summary_facts` — waits on `.3`'s fact contract (see below) |
| `.2` | dev | done | `doc_area_coherence` — names exactly the four drifting nodes; 9 live-repo tests left red for `.4` |
| `.3` | dev | done | audit stops describing itself — three populations; `FactRegistry.collect_set()` is `.1`'s contract |
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

**2026-08-26** — `.3` complete. The leak was captured before it was closed: a project named
`invoice-svc` was handed `mcp_tool_count=18` and `cli_command_count=43`, Beadloom's own
numbers, as facts about its documentation. Both surface facts are now gated on the audited
project's declared manifest name (`doc_sync/audit_self_surface.py`), and every collector that
cannot compute a value records the reason instead of dropping the fact.

The contract `.1` waits on: `FactRegistry().collect_set(project_root, db) -> FactSet`, where
`FactSet.facts` is `dict[str, Fact]` and `FactSet.not_applicable` is `dict[str, str]` mapping
a fact name to the reason no value was declared. The two are disjoint. `collect()` still
returns `facts` alone and cannot tell an absent fact from a declined one.

This repository's audit output was diffed against the 3.0.0 payload rather than asserted to
be unchanged: gained `not_applicable`, `verified_facts` and `summary.not_applicable_count`,
lost nothing, and the human output is byte-identical. Two facts moved for reasons outside
this bead — `test_count` 7494 -> 7529 (tests added by both wave-1a beads) and
`rule_type_count` 13 -> 14 with `architecture.md:133` now stale, which is `.2`'s new rule
arriving and belongs to `.4`.

**2026-08-26** — `.2` complete. `doc-area-coherence` ships in `graph/rules/doc_area.py`, wired
through the loader, the liveness counter, `evaluate_all`, the `rule_engine` shim and the
reindex serializer. No layout literal appears in it, and an AST test over the module's
non-docstring string constants fails the moment one does.

The derivation changed once mid-flight, and the reason is worth keeping. The first cut located
the docs area by matching each doc-path segment against the source-area vocabulary, which made
drift INTO a directory naming no source area invisible — the commonest shape of the defect.
It is now two passes: the vocabulary decides at what DEPTH this project names an area, and
that depth is then read for every doc path, whatever the segment is called there.

Measured on this repository: 83 node/doc pairs, 77 compare, 73 agree, **4 differ** —
`debt-report`, `doctor`, `reindex`, `watcher`, all `src/beadloom/application/…` documented
under `domains/infrastructure/…`. Exactly the four the bead names. The sample differs from
PLAN's stated 69/73 because this derivation drops 3 pairs whose source is the package root and
3 whose doc path is too short to carry an area segment (`services/{cli,mcp,tui}.md`), and
keeps the 7 domain READMEs; the four violations are identical either way.

`min_support` (default 2) was added to the design and is not decoration: without it every area
holding a single documented node is unanimous at one observation, and PLAN's "graph of six
nodes" would report a clean sweep having compared nothing that could disagree.

Left deliberately red for `.4`, measured with the rule disabled and re-enabled: **9** live-repo
tests assert `lint --strict` exits 0 and now fail on the four `error` findings
(`test_integration_v1::TestSelfLint` ×2, `test_s3_decomposition::TestLintRecalibrationGuard`
×4, `test_module_coverage_hardening::TestRealRepoCoveragePromoted` ×2,
`test_bead15_s3b_coverage::TestSiteGenerationCluster::test_no_site_module_is_flagged_by_coverage`).
`beadloom ci` is red for the same reason. Three further failures are NOT this bead's and were
failing with the rule disabled: `TestSyncCheckNewPairs` ×2 (stale pairs owned by `.3`'s files)
and `test_bead77_kind_and_root_disagree::test_this_repository_keeps_its_three_populations`
(190 -> 194 planning documents, this feature's own PRD/RFC/CONTEXT/PLAN).

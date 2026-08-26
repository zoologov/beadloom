# ACTIVE: BDL-062 — Graph metadata is an unchecked surface

> **Created:** 2026-08-26
> **Branch:** `features/BDL-062` (from `main` @ `cdc16de`)

---

## Beads

| Bead | Role | Status | Note |
|---|---|---|---|
| `beadloom-viaj` | feature | open | parent |
| `.1` | dev | done | `graph_summary_facts` — RED captured on 3 nodes; 32 tests; 12 neuterings verified |
| `.2` | dev | done | `doc_area_coherence` — names exactly the four drifting nodes; 9 live-repo tests left red for `.4` |
| `.3` | dev | done | audit stops describing itself — three populations; `FactRegistry.collect_set()` is `.1`'s contract |
| `.4` | dev | **ready** | the corrections — worklist grew, see below |
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

**2026-08-26** — `.2` CLOSED. `doc_area_coherence` fires on exactly `debt-report`, `doctor`,
`reindex`, `watcher` at `error`; 24 tests (21 unit + 3 scenarios); 77 pairs compared,
73 agree, 4 differ.

Coordinator verified independently rather than accepting the report: injected
`_FALLBACK_AREA_ROOT = "domains"` into the rule module and the layout-literal guard failed
as designed (`assert not ({'domains'} & {...})`), then reverted to a clean `git diff`. The
rule's own live output names the four and nothing else.

**Design change accepted, RFC superseded on one point.** RFC R2 said "the segment below the
docs root". Not implementable: `architecture.md` sits at the docs root and collapses the
common prefix, making the compared segment the `domains`/`services` bucket, which cannot
disagree. The agent's replacement derives the area *depth* in two passes — modal depth at
which a doc path names a source area, then read that depth everywhere — which also catches
drift INTO a directory naming no source area, a case its first cut missed. `min_support: 2`
is the agent's addition and closes PLAN's "graph of six nodes reports a clean sweep having
compared nothing".

**Brief correction:** severity escalation lives in `.beadloom/_graph/rules.yml`, not
`config.yml` — rule severity is a per-rule field and `config.yml` has no severity mechanism.
My brief said otherwise; the agent was right.

**Expected redness, owned by `.4`:** 9 live-repo tests assert `lint --strict` rc 0 and now
fail. They must go green again *by the corrections*, not by being relaxed — a test that
stops asserting the repo self-lints is the defect this feature exists to prevent. Three
further failures are NOT this bead's: `TestSyncCheckNewPairs` ×2 (stale pairs under `.3`'s
files) and `test_this_repository_keeps_its_three_populations` (190→194 planning documents —
this feature's own docs moved the count).

**BDL-UX #194 opened** — `bd merge-slot` is not an exclusion primitive. Every agent resolves
to the same actor (`BEADS_ACTOR` unset → `git user.name` → `$USER`, all `v.zoologov`), and
`release` is not owner-checked: a distinct `agent-B` unlocked `agent-A`'s hold and was told
it succeeded. The working-tree discipline in the project CLAUDE.md rests on this. Mitigation
adopted: a distinct `BEADS_ACTOR` per subagent, which restores acquire-time refusal and does
nothing about the release hazard.

**2026-08-26** — `.3` CLOSED, `.1` launched (wave 1b).

Coordinator verified the central claim on a real foreign project rather than accepting the
report: built `invoice-svc` (own `pyproject.toml`, one source file), ran `beadloom init` and
`docs audit` from this working copy. **`mcp_tool_count` and `cli_command_count` are gone from
its output.** Denominator moved 9 → 7 and says so, and every remaining fact names why it is
unverified — including `version: 0.4.1 -- NOT VERIFIED: no document states it`, the third
population made visible in the one place it was invisible before.

The identity gate reads the declared distribution name from the manifest with **no
directory-name fallback** — a clone in a directory called `beadloom` is not beadloom, and
unknown is not a match. That is the right shape.

## A diagnosis corrected before it became a bead

`.3` reported that `lint --json` "emits a trailing warning line onto stdout that breaks JSON
parsing in four test files" and suggested a bead. Two things are wrong with that and one is
right:

- There is no `--json` flag; it is `--format json`. `lint --json` exits 2 with a usage error.
- **The CLI does not pollute stdout.** Verified by redirection: JSON on stdout, `warning: 4
  error-severity violation(s)…` on stderr, `json.load` succeeds. No CLI bead is warranted.
- The observation underneath is real, and the mechanism is the test harness:

```
CliRunner().invoke(...)   result.output  len=78474  -> JSONDecodeError  (stderr merged in)
                          result.stdout  len=78384  -> PARSES
                          result.stderr  len=   90  -> the warning line
```

Click 8.4's `result.output` merges stderr. So `json.loads(result.output)` — the pattern in
`test_integration_v1.py::TestSelfLint::test_self_lint_clean` and its siblings — is safe only
while nothing warns. It will go green again on its own once `.4` corrects the four nodes and
the warning stops firing, which is exactly why it must NOT be left as is: the fragility
survives the symptom. **`.5` owns it — parse `result.stdout`.**

The coordinator's own first reading ("Click 8.4 no longer merges streams") was wrong and is
withdrawn here rather than left standing in chat.

## Handed on by `.3`, owned elsewhere

- `rule_type_count` moved 13 → 14, which makes `architecture.md:133` stale — **`.4`**.
- `test_count` moved 7494 → 7529 (both wave-1a beads' tests) — expected, not a defect.
- Clean room not claimable by `.3` (`git archive` blocked in its sandbox, and HEAD carried
  two agents' work by then) — **`.6`**, and it must be a real clean room, not a re-run.
- Surface ledger grew 344 → 347 pairs; `--record-surface` deliberately NOT run, so no ledger
  mixes two beads' work. Whoever integrates records it once.

## `framework_count` (#193) — `.3` judged it separate, with a reason that changes the fix

Not a scope preference. Changing its value breaks the equality `.3` had to hold fixed. And
`.3` measured that the "count DISTINCT frameworks" candidate makes it **worse**:
`unverifiable_reason('framework_count', 1)` returns *"its value is 1: 0 and 1 are too common
in prose to be read as claims"* — so that candidate renders the fact structurally uncheckable
on this repository and on every single-framework project.

On the evidence the **rename** candidate is the better one. It has prose consequences, so it
belongs with `.4`/`.7`, not with `.3`. #193 updated accordingly.

**2026-08-26** — `.1` complete. `graph-summary-facts` ships in `graph/rules/summary_facts.py`,
wired through the loader, the liveness counter, `evaluate_all`, the `rule_engine` shim and the
reindex serializer. It owns neither the extraction nor the comparison: `DocScanner.scan_line`
reads the summary and `compare_facts` judges it, so this codebase keeps one notion of "a version"
and one keyword table.

**The red was captured before anything corrected it** — `beadloom lint --format json` on the
working tree at `157eb8a`, three findings at `error`:

- `beadloom` — states version `v1.5.0`, project computes `3.0.0` (pyproject.toml)
- `mcp-server` — states `mcp_tool_count` 14, project computes 18 (MCP tool catalog)
- `route-extraction` — states `framework_count` 12, project computes 84 (graph DB)

Every message carries the population it is a fraction of: "read from 84 node summaries: 3 state
a checkable fact (0 agree, 3 disagree, 0 could not be verified) and 81 state none". The same
three reproduce in a clean room (`git archive HEAD` plus 16 files), so they are a property of the
graph and not of this working tree.

**A third finding, not on `.4`'s list.** `route-extraction`'s "12 web frameworks" is BDL-UX #193
reaching the graph: `framework_count` computes 84 (nodes declaring a framework) while the summary
means the parsers the route extractor ships. Fixing #193 to the distinct count (1) would not clear
it either, so the honest resolutions are to reword the summary or to add a graph-side suppression.
The identical sentence in prose is already suppressed for `docs/domains/context-oracle/README.md`
by a `docs_audit.ignore` triple. **No suppression mechanism was built** — building the silencer
before the owner has ruled is the wrong order, and it would have been a mechanism with no caller.

**Two deviations from the brief, both deliberate.** `DocScanner` gained a public `scan_line`
seam and `scan_file` is now written in terms of it, because the alternative was reaching into two
private methods across a domain boundary or forking the extractor. And `graph` now imports
`doc_sync`; that is domain-to-domain, unenforced here, and `graph -> context_oracle` was already
the precedent.

**Tests bite, measured by 12 explicit neuterings**, each reverted to a clean diff — dropping the
unverifiable findings (4 fail), collapsing unverifiable into inertness (5), returning `[]` instead
of "checked nothing" (3), forking the comparison to raw string equality (2), dropping the
population clause (1), hardcoding severity (1), rewording the decline reason (3), pasting a second
version regex (1), bypassing `scan_line` (1), removing the `evaluate_all` dispatch (1), accepting
a `summary_facts` key that does nothing (1), and bare-integer matching (15, including all six
false-positive tests).

**Inherited redness, unchanged by this bead.** The failing test set is byte-identical with the
rule enabled and disabled — measured, not assumed. It is now **10**, down from 12: the two
`TestSyncCheckNewPairs` failures went green because `sync-update -y` re-baselined the pairs this
bead's own doc edits made stale, which brought `sync-check` back to rc 0. `beadloom ci` is red at
`HEAD` too, verified in the clean room, on `architecture.md:133`, `doc-sync/README.md:95` and
`.beadloom/AGENTS.md` config-drift — none of them introduced here.

**Moved for `.4` to pick up:** `rule_type_count` is now **15**, not 14, so `architecture.md:133`
(which says 13) is two behind. `.beadloom/AGENTS.md` config-drift was already an error at `HEAD`
and this rule makes it staler; `beadloom setup-rules --refresh` is its remedy.

**2026-08-26** — `.1` CLOSED. Wave 1 complete; all three mechanisms exist.

The red captured before any correction, three `error` findings:

```
beadloom          states version v1.5.0        computes 3.0.0   (pyproject.toml)
mcp-server        states mcp_tool_count 14     computes 18      (MCP tool catalog)
route-extraction  states framework_count 12    computes 84      (graph DB)
```

Each message ends with its own denominator — *"read from 84 node summaries: 3 state a
checkable fact (0 agree, 3 disagree, 0 could not be verified) and 81 state none"*. That is
A GREEN COUNT IS NOT A CHECKED COUNT discharged by the rule itself.

## The third finding was on nobody's list, and it decides #193

`route-extraction`'s summary is **factually correct** — the coordinator verified 12 framework
literals in `context_oracle/route_extractor.py`: `echo, express, fastapi, fiber, flask, gin,
graphql_python, graphql_schema, graphql_ts, grpc, nestjs, spring`. Two unrelated meanings of
"framework" collide under one fact name: *web frameworks a component parses* vs *nodes
declaring a test framework*.

A true positive for the defect, a false positive for the node. `.1` built **no** suppression
mechanism and was right to — silencing a correct sentence to protect a misnamed fact is
backwards, and a silencer built before the owner ruled would have had no caller.

**Decision, made on the evidence rather than deferred:** rename `framework_count` →
`nodes_with_framework` with keywords that mean that. It clears the latent prose landmine,
this live finding, and the collision, all three, without suppressing anything true. The
DISTINCT alternative was measured worse by `.3` (value 1 is structurally uncheckable).
Added to `.4`. #193 updated with both measurements.

## `.4`'s worklist has grown since PLAN

Beyond the five originally scoped:

- `docs/architecture.md:133` says 13 rule types; the graph now has **15** (`.2` and `.1` each
  added one). Two behind, not one.
- `docs/domains/doc-sync/README.md:95` states version `3.0.1` — a version that does not exist
  yet. Pre-existing at `HEAD`, unrelated to this branch.
- `.beadloom/AGENTS.md` config-drift, an error at `HEAD` already; `beadloom setup-rules
  --refresh` is the remedy, unverified by `.1`.
- the `framework_count` rename above.

`beadloom ci` is rc 1 **at `HEAD` too**, on exactly those three. `.1` verified that in a clean
room and added zero failing tests — measured by removing its own rule, reindexing, and
diffing the failing set, which was byte-identical.

## Two scope deviations by `.1`, both accepted

**`DocScanner.scan_line(line, *, origin, line_number=1)` is now public**, and `scan_file` is
written in terms of it — same two calls, same order, behaviour unchanged. Reusing only
`_VERSION_RE` and `FACT_KEYWORDS` would have meant reimplementing the clause-scoped proximity,
the token-boundary policy and the modifier blocklist around them — precisely the fork the
brief forbade. The alternative was reaching into two privates across a domain boundary.

**`graph` now imports `doc_sync`** — domain-to-domain, unenforced here, with
`graph → context_oracle` (and `onboarding → graph`, `onboarding → context_oracle`) as
precedent. No graph edge added, because the model does not declare those peer imports either.

## The `lint --format json` misreading has now happened twice

`.1` reported it as "appends a non-JSON warning line to stdout". It does not — the warning
goes to stderr and `json.load` succeeds from a shell. `.1` was launched before the note
correcting this was written, so it could not have read it. **Every later bead's brief must
carry the correction inline**, not rely on ACTIVE.md having been read: the real mechanism is
Click 8.4's `CliRunner` merging stderr into `result.output`, and `result.stdout` is clean.

## Attestation to know about

`.1` ran `sync-update -y`, which attested `domains/graph/README.md ↔ graph/scenarios.py` — a
pair it did not cause. It says it read the code before attesting but did not author that
prose. Flagged for `.6`.

Ledger: `--record-surface` still deliberately unrun. Whoever integrates records it once.

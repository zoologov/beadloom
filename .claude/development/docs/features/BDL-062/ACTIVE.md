# ACTIVE: BDL-062 — Graph metadata is an unchecked surface

> **Created:** 2026-08-26
> **Branch:** `features/BDL-062` (from `main` @ `cdc16de`)

---

## Beads

| Bead | Role | Status | Note |
|---|---|---|---|
| beadloom-viaj | feature | ready | parent |
| beadloom-viaj.1 | dev | ✓ done | `graph_summary_facts` — RED captured on 3 nodes; 32 tests; 12 neuterings verified |
| beadloom-viaj.2 | dev | ✓ done | `doc_area_coherence` — names exactly the four drifting nodes; 9 live-repo tests left red for `.4` |
| beadloom-viaj.3 | dev | ✓ done | audit stops describing itself — three populations; `FactRegistry.collect_set()` is `.1`'s contract |
| beadloom-viaj.4 | dev | ✓ done | the corrections — 14 landed, each proved by reverting it alone; 2 BDL-UX opened, 1 withdrawn |
| beadloom-viaj.5 | test | ✓ done | bite tests + a fixture that is genuinely not Beadloom |
| beadloom-viaj.6 | review | ✓ done | clean room; 8 mutations, 6 killed, 2 survived (#203) |
| beadloom-viaj.7 | tech-writer | ✓ done | README en+ru + guides; 97 documents swept, 128 numeric claims reviewed |
| beadloom-viaj.8 | chore | ✓ done | release 3.0.1 |
| beadloom-viaj.9 | dev | ✓ done | the source root tolerates a minority; a total stand-down is no longer silent — found by a coordinator challenge to `.4`'s #195 |
| beadloom-viaj.10 | dev | ✓ done | the review's cheap true fixes, including two that damage our own verification |
| beadloom-viaj.11 | dev | ✓ done | `doc_area.py`'s docstring stopped describing `_common_prefix`; sweep of 11 modules / 32 named references found 0 more, and the sweep is now a test |
| beadloom-viaj.12 | tech-writer | ✓ done | README leads with harness governance (owner decision 2026-08-27) |
| beadloom-viaj.13 | tech-writer | ✓ done | all eleven guides read in full against current functionality; 9 changed, 2 left |
| beadloom-viaj.14 | dev | ✓ done | `graph-summary-facts` ships `error` and stood down at `warn` — measured TOTAL four ways, fixed, and the test that pinned the defect replaced with evidence; 6 documents corrected, #197 amended |
| beadloom-viaj.15 | dev | ✓ done | the description was fixed in 2 copies of 4 — swept and found 5, three removed rather than corrected, the check now sweeps 372 files and records its population; released as 3.0.2 (BDL-UX #211) |

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

**2026-08-26** — `.11` done. `doc_area.py`'s module docstring still said the source root is
"the longest directory prefix every node source shares", which is `_common_prefix` — the
function `.9` deleted at `c9f8325`. `docs/domains/graph/README.md` and the rule-engine SPEC
both describe `_source_root` correctly, so the document was right and the code's own prose was
wrong. `sync-check` cannot see this: a docstring is not a doc pair, it lives inside the file
whose hash defines the pair's freshness, and a file is always fresh with respect to itself.

The rejected alternative is now measured rather than asserted. Swapping the support-governed
descent for a `0.60` majority fails **5 of the 21** tests in `tests/test_doc_area_coherence.py`,
among them `.2`'s founding `test_a_node_documented_outside_its_area_is_named` — because a modal
segment covering 6 of 10 sources is accepted, the root settles one level below where the areas
start, and every pair is compared on the wrong segment.

Sweep: **11 of 11** modules under `src/beadloom/graph/rules/` carry a module docstring; **32**
named symbol references across them; **0** further dead references (two apparent hits were
false — `` `__init__` `` names the module file, and `FactSet.not_applicable` is a real dataclass
field that `hasattr` cannot see). The sweep is now `tests/test_rules_docstring_references.py`
so it does not decay, and that test states in its own docstring that it closes only the
*named-reference* half of the class — it could not have caught `.11`'s own defect, which
described the deleted function in prose without naming it.

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

**2026-08-26** — `.4` complete. `beadloom ci` rc 0; 7175 passed, 0 failed (from 10 failing at
`HEAD`). All 9 of `.2`'s live-repo `lint --strict` tests went green **by the corrections** —
no test that asserts this repository self-lints was edited.

**Green in a clean room over 33 files** (`git archive HEAD`, the four rename sources removed,
plus only this bead's files; every one `cmp`-identical to the working tree). One caveat stated
rather than glossed: the `beadloom` on `PATH` is the editable install, so the clean room
exercises the working tree's `src/` against the clean room's DATA. Since `src/` is byte-identical
between the two, the answer is the same, but the claim is about the graph and the documents, not
about a separately built package.

## Every correction, and what reverting it alone does

| # | Correction | Revert it alone → |
|---|---|---|
| 1 | root summary `v1.5.0` → `v3.0.0`, `Doc Sync v2 Engine` → the four current parts | `lint --strict` rc 1, 1 error naming `beadloom`, `v1.5.0` and `3.0.0` |
| 2 | `mcp-server` 14 → 18 tools | rc 1, 1 error naming `mcp-server`, 14 and 18 |
| 3 | four SPEC dirs `git mv`'d to `application/`, `docs:` following | rc 1, 4 errors naming each node and both areas |
| 4 | `framework_count` → `nodes_with_framework` + keywords that mean nodes | rc 1 on `route-extraction`, and 5 tests fail |
| 5 | the distance tie-break (`-len(kw_words)`) | 3 tests fail, including the acceptance scenario |
| 6 | `is_count_fact()` replacing the `_count` suffix | 3 tests fail |
| 7 | `docs_absent` read in `doctor` | 3 tests fail; `vitepress-site` prints as an unexplained gap |
| 8 | `vitepress-site`'s recorded reason | `doctor` prints `has no doc linked` — the same word as a gap |
| 9 | `_detect_rule_type`'s two new keys | 2 tests fail |
| 10 | `architecture.md:133` 13 → 15 rules | `docs audit` reports it stale |
| 11 | `doc-sync/README.md:95` version reword | `docs audit` reports `version "3.0.1" -> 3.0.0` |
| 12 | `.beadloom/AGENTS.md` refresh | `config-check` reports agent-config drift |
| 13 | the SPEC rule-type table | 1 test fails (shown twice: a dropped row, a wrong cardinal) |
| 14 | the package description | manifest/docstring agreement fails — **and see below** |

**14 is the one that cannot be fully checked, measured rather than asserted.** Reverting BOTH
copies to the 1.x sentence leaves `tests/test_package_description.py` GREEN. Agreement between
the manifest and the package docstring is checkable; currency is not, by any test, and that is
exactly how the 1.x description survived three majors. The module says so in its own docstring.
A retired-phrase blocklist was written there and then removed: `Doc Sync v2 Engine` lived in the
graph's root summary and never in the manifest, so it could not have fired on what it guarded.

## The brief was wrong about `doc-sync/README.md:95`, and the correction changes who owns it

The brief said the `3.0.1` line is "Pre-existing at `HEAD`, not from this branch". Measured:
`git show main:docs/domains/doc-sync/README.md | grep -c 3.0.1` returns **0**, and
`git log -S "Until 3.0.1"` names `7087465` — `.3`'s own commit, this morning, on this branch.
It is not an inherited forward reference to adjudicate; it is a sibling bead's prose written for
a release that has not happened.

Reworded rather than suppressed, because a domain README asserting a version that does not exist
is a claim nothing can hold it to, and `CHANGELOG.md` is where a release is named.

**Consequence `.7`/`.8` must know:** with that mention gone, **no document in this repository
states the current version as a claim**. `docs audit` now reads
`version: 3.0.0 -- NOT VERIFIED: no document states it` and the fraction moved 5/9 → 4/9. That
is the audit being honest — the coordinator already withdrew the "extraction is broken" theory
for the same observation — and the onboarding README's worked example was updated to the
measured output, including a sentence saying why `version` is in that list.

## `route-extraction` is fixed by the rename, with no suppression anywhere

`framework_count` → `nodes_with_framework`, keywords that name NODES
(`node with framework`, `node declar a test framework`, …). "across 12 web frameworks" now
matches nothing, so a correct summary stopped being reported and the summary was not touched.

**The `docs_audit.ignore` triple for `docs/domains/context-oracle/README.md` DID go inert.**
Measured after the rename: 0 framework-family mentions over 58 documents repo-wide. Retired from
`config.yml` with its reason, following the BDL-061.44/.45 precedent already recorded there.

Two couplings the rename would have broken in silence, both made explicit instead:

- `MIN_READABLE_COUNT` was gated on `fact_name.endswith("_count")`, so the new name would have
  dropped out of the single-digit floor. Now `scanner.is_count_fact()`, with a test asserting
  EVERY registered fact except `version` is recognised.
- The winner of a distance tie was `FACT_KEYWORDS` insertion order. "84 nodes declare a test
  framework" sits one word from both `node` and the five-word phrase, and `node_count` won
  because it is listed first. The score gained `-len(kw_words)`: the longer phrase wins.

## `vitepress-site` — the probe that changed the answer, then changed it back

**Superseded by `.9`. The paragraph that stood here was wrong on its evidence, and the wrong
number was acted on, so it is corrected rather than deleted.**

It said: attaching any document to `vitepress-site` collapses `doc-area-coherence`, turning
*"4 true findings into 6 false ones"*. There were no 4. The `services.yml` backup taken
immediately before the probe shows the four misfiled nodes were **already corrected**; the
measured baseline was **0**, and the 6 were manufactured from a clean graph. The claim compared
against `.2`'s pre-correction baseline instead of the one actually measured — a green count that
was not a checked count, written into the record of the feature about exactly that.

The coordinator could not reproduce it, which is how it surfaced. Both measurements were correct:
the collapse has **two faces**, and which one appears depends only on where the minority node's
document sits.

| document | outcome before `.9` |
|---|---|
| `site/vitepress-site/DOC.md` | area depth still found, bogus convention, **7 nodes reported wrong at `error`** |
| `guides/vitepress-site.md` | no area depth exists, **0 of 86 pairs compared, rule reports it checked nothing** |

The second is the worse one, and it is what made #195 HIGH: the stand-down went out at `warn`
because `liveness_finding` hardcoded it, so a rule this project escalated to `error` stood down
over its whole population with `lint --strict` at rc 0.

**`.9` fixed both.** Measured on this repository, both documents now give the identical answer —
derivable, 8 dominant areas, **0 contradicting**, `outside_root` 1 — against a baseline of the
same 8 areas and `outside_root` 0.

So the `docs_absent` reason no longer cites #195 at all: that clause is **withdrawn in the node
itself**, in those words. What remains is that `site/` is outside `scan_paths`, so no sync pair
can anchor a document there (#163), and that `docs/guides/vitepress-site.md` describes the
generator rather than the committed theme. Nothing about the rule constrains the decision now.

## Absence and excusal now print different words

`doctor`'s `nodes_without_docs` printed one WARNING for `cli-commands`, `status` and
`vitepress-site` alike. Three outcomes now: WARNING for an unexplained absence, **INFO with the
reason printed** for a decision, and WARNING again for a reason on a node that HAS a document,
because a suppression that suppresses nothing reads as coverage it does not have. A blank reason
is not a reason. **No schema change:** the loader already stores an unmapped key in `nodes.extra`.

`status` and `cli-commands` got real documents instead — `status` has three public symbols and
`cli-commands` fourteen modules, so absence there was a gap, not a decision.

## Found while correcting, and fixed: three of fifteen rules were `(unknown)` to every agent

`.beadloom/AGENTS.md` is what an agent reads to learn this project's rules, and
`rules_gen._detect_rule_type` mapped 7 of the loader's 12 authoring keys, so `module-coverage`,
`scenario-coverage` and `doc-area-coherence` were labelled `(unknown)`. The keys are now named
once as `graph.rules.loader.AUTHORING_KEYS` — the loader's own "must have exactly one of" message
is built from it — and two tests hold the readers to it.

`rule-engine/SPEC.md` claimed "the count and the rows are checked against the loader's own
dispatch". **Nothing checked it.** `TestTheSpecTableIsCheckedAgainstTheLoader` does now, proved
to bite twice.

`docs/architecture.md:133` had TWO stale numbers, not one: "the **ten** authoring keys" (12) and
"configures **13** rules" (15). Only the second was ever visible to `docs audit`, because
**"ten" is spelled as a word and the extractor reads digits**. The type count went stale twice
and no check could see it either time. Folded into BDL-UX #179.

## `setup-rules --refresh` does NOT carry #191's hazard — checked before running

#191 is about `generate_adapters(...)` recomposing a hand-edited role adapter. `setup-rules
--refresh` calls `refresh_claude_md()` + `generate_agents_md()` and never `generate_adapters`.
Ran `--dry-run` first (`.claude/CLAUDE.md: no changes needed` — the project layer untouched),
then ran it and **diffed** rather than trusting: two rules added, `## Custom` intact, nothing else.

## BDL-UX: two opened, one withdrawn before it was committed

- **#195** HIGH — `doc-area-coherence` collapses on a source outside the common root.
- **#179** re-measured — the SPEC table and the AGENTS.md map are both fixed and both now held to
  `AUTHORING_KEYS`; what stays open is the `rule_type_count` rename, and the new reason is that a
  count spelled as a word is invisible to the audit.
- **#196 withdrawn.** It duplicated #179's own last paragraph, and this log already has two
  issues numbered 187. Its content went into #179 instead.

## Handed on

- `test_bead77`'s three denominators updated with reasons: TO-BE 190 → **194** (this feature's
  own PRD/RFC/CONTEXT/PLAN), AS-IS 98 → **100** (`status`, `cli-commands`), WORKING 55 → **56**
  (this ACTIVE.md). The test's own comment already declares these as moving denominators.
- `--record-surface` still deliberately unrun. The declared surface is 344 → **352** pairs.
- `.beads/*.jsonl` were excluded from the clean room: they are tracker state, not this bead's work.

**2026-08-26** — `.9` complete. Opened by the coordinator failing to reproduce `.4`'s BDL-UX #195
and asking for conditions rather than assuming either side was wrong. Both measurements were
right; the issue text was not.

**Two defects, one trigger.** `_common_prefix` derived the source root from what EVERY paired
source shares, so a single `site/` vetoed the derivation for all 85 other pairs. `min_support`
guarded the dominant-mapping half and nothing guarded the prefix. `_source_root` replaces it: it
descends while there is **exactly one supported way down**, supported meaning `min_support`
sources agree on the next segment — the dial already declared, not a second threshold. A genuine
fork ends the descent, which is where the areas begin; a source too short for that depth is
`rootless` rather than a veto.

A pair outside the derived root is excluded from the comparison and **counted**:
`Convention.population()` now ends `"; N sit outside the source root"`, and `examined` adds up to
the pairs the graph offered. Measured on this repository, both of the two document paths now give
the identical answer — derivable, 8 dominant areas, 0 contradicting, `outside_root` 1 — against a
baseline of the same 8 areas and `outside_root` 0.

**The second defect is the one that blocked the release.** `liveness_finding` hardcoded
`severity="warn"`, so a rule this project escalated to `error` could stand down over 100% of its
population with `lint --strict` at rc 0. It now takes a keyword-only `severity` defaulting to
`warn`, so every existing caller is byte-identical, and `doc_area` passes the rule's declared
severity for a **total** stand-down. A **partial** inertness stays advisory, and the distinction
is the whole argument: a dead glob beside nine live ones is a configuration smell, while a rule
that checked none of its population is indistinguishable from one that never ran. It costs an
adopter nothing — the rule ships `warn`, so a small graph still reports `warn`.

**The test that is the point of the bead:**
`test_the_gate_cannot_pass_while_the_rule_checked_nothing` runs the real linter over an
underivable graph with the rule declared blocking, and fails if `has_errors` is not set. Its
sibling asserts the shipped default still leaves the Gate green, so the adopter guarantee is a
check and not a claim.

Both document paths are permanent fixtures (`TestBothFacesOfTheCollapse`). They produced
different observables from one cause, and nothing but the doc path varies between them —
which is exactly what neither of us would have thought to vary.

**Captured RED before the fix**, in the fixtures' own miniature: the first face reported
`['gateway-0', 'gateway-1']` — correct nodes called wrong — and the second reported
*"checked nothing: ... of 12 pairs ... 12 have a doc path with no segment at the depth this
project names areas"*. The fixture needed a second top-level docs bucket to exhibit face one at
all; a single-bucket fixture passed either way and proved nothing, which is why the first version
of it was rewritten.

**Three texts corrected, and the false line struck rather than quietly replaced:** #195 (closed,
with the "4 true findings" evidence explicitly marked false and the real baseline of 0 stated),
the `docs_absent` reason on `vitepress-site` (the #195 clause **withdrawn in the node itself**),
and the `ACTIVE.md` paragraph above.

**#197 opened for the named residual:** `summary_facts`, `scenario_coverage`, `module_coverage`
and `unregistered_feature_candidate` still report a total stand-down at `warn`. Only
`doc_area_coherence` was measured, and escalating four more rule types on one rule's evidence
would be shipping four untested changes inside a fix.

**Green in a clean room over 12 files**, and the clean room had to be built properly before it
could say anything. `git archive HEAD` plus only this bead's files gives a tree that is **not a
git work tree**, and `git_baseline` then answers *"git could not tell"* for every pair: all **363**
came back `unverified`, and `TestSyncCheckNewPairs` failed for that reason alone. Running
`git init` + one commit inside the clean room removes the artifact — 363 `ok` — and the result is
`beadloom ci` rc 0 with **7189 passed, 0 failed**. A clean room that is not a work tree measures
the absence of git, not the health of the change.

The one failure on the shared tree (`test_guards_parity.py::…::test_the_live_repo_index_is_byte_identical_after_a_real_evaluation`)
is a concurrency artifact and is now shown to be one: it hashes `.beads/issues.jsonl` and the live
index among its tracked files, both of which any concurrent `bd` or `beadloom` call mutates while
`.5` runs. It passes in isolation and it does not appear in the clean room at all.

**One representation trap, recorded because both of us nearly fell into it.** The index stores
doc paths **relative to the docs root** — `domains/graph/README.md`, not `docs/domains/...`. A
scratch probe that inserts a row by hand with the `docs/` prefix shifts the area depth by one and
produces a third, entirely spurious answer. `.4`'s first reproduction did exactly that and was
caught. **The fix itself depends on no such thing:** `_source_root` reads only `nodes.source`
segments, and nothing in it assumes a `docs/` prefix, a docs root, or any directory name.


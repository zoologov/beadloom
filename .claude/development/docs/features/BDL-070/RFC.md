# RFC: BDL-070 — The layer a node is in, answered once and reported over its population

> **Status:** Approved
> **Created:** 2026-09-12

---

## Overview

One function answers "what layer is this node in", derived through `part_of` ancestry and reading
the declaration rather than hardcoding it. The three current answers call it. `architecture-layers`
states its population on every run, and it states it before the answer changes what any verdict is.

The work lands in two releases, and the boundary between them is the constraint: everything that
changes no verdict ships first, everything that changes a verdict ships after, in a release that
says so.

## Motivation

### Problem

`architecture-layers` evaluates a `depends_on` edge only when both ends carry a layer tag of their
own. **Measured on this tree (`aa4bfad4`): 362 active `depends_on` edges, 16 evaluated.** By
`part_of` ancestry 354 have a layer at both ends. The green line names no population, so 16 of 362
is reported in the words that would report 362 of 362.

Three sites compute layer membership — `evaluators.py:588`, `liveness.py:285`,
`architecture_view.py:82`/`:193` — and they disagree on both inputs and verdict. The declaration is
doubled: `rules.yml:44`–`:58` is read, `rules.yml:3`–`:7` is a second catalog nothing in `src/`
reads. And a shipped role template tells adopters the rule proves something it does not.

### Solution

A single `layer_of(ref_id)` reading the rule's own `layers` list and climbing `part_of` to the
nearest tagged ancestor, with the population it ran over reported beside every verdict. The three
call sites become callers. The unread catalog is removed or made the declaration; `validate_rules`
learns `LayerRule`.

## Technical Context

### Constraints

- Python 3.10+, `mypy --strict`, `ruff`; pytest with the 80% floor (STACK section, below).
- **No adopter's Gate may change verdict on upgrade** (BDL-069 CONTEXT). This splits the work in
  two and fixes their order.
- `architecture-layers` is `severity: error`. A change to what it evaluates is a change to whether
  `main` and every adopter's `main` is mergeable.
- The five `_cached_tags` closures are per-call and in memory; no persisted projection carries a
  derived layer, so no migration is needed. `graph_snapshots.nodes_json` stores `nodes.extra`
  verbatim, so a snapshot compared across the change compares declared tags on both sides and is
  unaffected.

### Affected Areas

The rule engine owns the evaluation and four other rule kinds share its tag lookup. The renderers
of the verdict line are outside `graph/rules/` — in `graph/linter.py`, and two readers reach the
evaluators without passing through `lint()` at all. The declaration is a file no node owns.

## Axes

> **Derived by:** `beadloom impact evaluate_layer_rules` over `src/beadloom`
> **Seed:** none — no name the target reaches performs a declared effect under rule
> `reaches-an-effect-sink`, so every axis below is unresolved and not empty
> **Unresolved:** 1 name-defined-more-than-once, 1 no-seed, 20 unresolved-terminator-name

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| co-writers | — | unresolved — no declared effect rule found a sink this target reaches | — | no | The derivation established no seed, so this row names no node and contributes no work site. It is ruled out as a row, NOT as a question: the population it exists to name is established by the supplement below and ruled there, node by node. |
| callers | rule-engine | 2 — `graph/rules/__init__.py:171` | none | yes | `evaluate_all` is where a per-rule population is aggregated and handed to every renderer. |
| branches | rule-engine | `evaluate_layer_rules`: 4 branch(es), 3 exit form(s) | none | yes | The change itself. |
| branches | rule-engine | `_cached_tags` ×5 (`:111`, `:231`, `:494`, `:588`, `:720`) | none | yes | Five identical closures are the duplication the single lookup replaces. |
| branches | rule-engine | `evaluate_deny_rules`: 2 branch(es), 3 exit form(s) | none | yes | Holds one of the five closures; the shared lookup reaches it. Its own population is a non-goal. |
| branches | rule-engine | `evaluate_require_rules`: 4 branch(es), 3 exit form(s) | none | yes | As above. |
| branches | rule-engine | `evaluate_forbid_edge_rules`: 3 branch(es), 3 exit form(s) | none | yes | As above. |
| branches | rule-engine | `evaluate_cardinality_rules`: 10 branch(es), 3 exit form(s) | none | yes | As above. |
| branches | rule-engine | `evaluate_all`: 24 branch(es), 1 exit form(s), from a caller's seat | none | yes | The aggregation point for the population. |
| branches | rule-engine | `_get_node`, `_edge_exists`, `_first_matching_source` | none | no | Measured: none is used by `evaluate_layer_rules`, and none reads tags. |
| branches | rule-engine | `_liveness_finding`, `_dead_glob_finding` | none | no | Liveness rendering; the layer half of liveness is ruled in the supplement, this is not it. |
| branches | rule-engine | `_evaluate_one_import_rule`, `evaluate_import_boundary_rules` | none | no | Import boundaries are a separate rule kind and read no tags. |
| branches | rule-engine | `_file_annotations`, `_candidate_files_for_domain`, `evaluate_unregistered_feature_candidate_rules` | none | no | Feature-candidate rule; reads no tags. |
| branches | rule-engine | `_node_source_paths`, `_node_dir_source_prefixes` | none | no | Source-prefix helpers; no tag read. |
| branches | rule-engine | `_module_coverage_state`, `_disk_modules`, `evaluate_module_coverage_rules`, `_module_coverage_reasons` | none | no | Module coverage; reads the filesystem, not tags. |

**Supplement — the population the derivation could not establish.**

> **Derived by:** hand, by the Explore role — `grep -rn` over `src/` for `tags` / `get_node_tags` /
> `layer` / `part_of` / `load_rules` / `evaluate_all` / `LintResult`, each hit opened and read; the
> tagged node set and the edge counts read with `sqlite3` from `.beadloom/beadloom.db`.
> **Not a seeded derivation:** name-matching finds a reader that names `tags`; it cannot find one
> that reaches the column through an alias. These rows carry no seed and are not axis rows.

| Site | Node | In scope | Why |
|---|---|---|---|
| `graph/loader.py:33` `get_node_tags`, `:474`–`:482` materialisation | graph-loader | yes | The single read of `nodes.extra["tags"]` and the single write. The shared lookup is built on it. |
| `graph/rules/liveness.py:148` `_GraphFacts.tags`, `:285`–`:305` `_layer_reasons` | rule-engine | yes | The second implementation. Becomes a caller. |
| `application/architecture_view.py:46,57,82,187,193,268,283` | application | yes | The third implementation — hardcodes the tags and ranks, and already walks `part_of`. Becomes a caller. |
| `graph/rules/types.py:130`–`:146` `NodeMatcher.matches` | rule-engine | yes | Skips the tag check when the caller passes `tags=None`, so a tag-bearing matcher matches every node for such a caller — the same class as this rule's own gap. |
| `services/mcp_server.py:690`–`:716` `_active_rules_for_node` | mcp-server | yes | The caller that passes no tags and treats the layer rule as active for every node. |
| `graph/rules/loader.py:1021,1044` `load_rules_with_tags` | rule-engine | yes | Reads the second declaration; no production caller. |
| `graph/rules/loader.py:365,429,908,961`–`:962`, `:1060` `validate_rules`; `types.py:254,262` | rule-engine | yes | Parsing, dispatch, and the validation that has no `LayerRule` in its isinstance chain. |
| `.beadloom/_graph/rules.yml:44`–`:58` and `:3`–`:7` | — | yes | Both declarations. Owned by no node today — the ownership gap is a non-behavioural criterion in the PRD. |
| `graph/linter.py:47`–`:75`, `:185`–`:230`, `:248,259,274`, `:337,342`, `:349,383,432,467` | graph | yes | `LintResult` and all four renderings. `_inert_note` / `_suppressed_note` / `_unattributed_note` are the precedent for a qualifying clause in the summary. |
| `graph/linter.py:146,151` | graph | yes | The default `rules.yml` path and the `load_rules` call. |
| `services/commands/federation.py:325` | cli-commands | yes | `beadloom lint`'s own `0 violations, N rules evaluated` line. |
| `application/gate.py:282,298` `lint_step` | ci-gate | yes | The Gate's rendering of the same result. |
| `services/mcp_server.py:418` `handle_lint`, `:702,708` | mcp-server | yes | The MCP rendering, and the third load of `rules.yml`. |
| `tui/data_providers.py:160`–`:169`, `:162,168`; `tui/widgets/lint_panel.py:58`–`:99` | tui | yes | Calls `evaluate_all` directly, bypassing `lint()` and every counter, and loads `rules.yml` a second time. A clause in the summary line cannot reach it. |
| `application/debt_report/collect.py:235`–`:248` | debt-report | yes | The same bypass, and the fourth load. |
| `onboarding/scanner/prime.py:22,94`–`:98,158`–`:164` | agent-prime | yes | What an agent reads first; its violation count is the layer rule's reach into every session. |
| `graph/import_resolver.py:875` `_part_of_ancestors`, `:963` | graph | yes | The existing transitive ancestry walk. The shared lookup uses this or `architecture_view`'s, never a third. |
| `graph/rules/liveness.py:437` | rule-engine | yes | Calls `validate_rules` per rule; gains the `LayerRule` case. |
| `onboarding/templates/roles/architecture/ddd/dev.md.txt:13` | onboarding | yes | Shipped role template asserting a green `lint --strict` "genuinely enforces direction". Owner's decision, 2026-09-12. |
| `docs/domains/graph/features/rule-engine/SPEC.md:496`–`:497,551`–`:555` | rule-engine | yes | A doc copy of the declaration the code loads. |
| `docs/domains/graph/README.md:81`; `.beadloom/_graph/graph.yml:7` + 11 node files | graph | yes | States the active-edge restriction; carries the `layer-*` tags. |
| `docs/services/components/cli-commands/DOC.md:34,289` | cli-commands | yes | Cites the rule's severity as the reason a call lives where it does. |
| `docs/services/components/guard-probes/DOC.md:17` | guard-probes | yes | Same shape — the doc states what a green run proves. |
| `.beadloom/AGENTS.md:57`, `.claude/agents/dev.md` and the project-layer flow files | — | yes | Reproduce the rule's description. Edited at their source, `.beadloom/flow/`, then recomposed. |
| `graph/rules/scenario_coverage.py:87`, `:325`, `:373`, `:525` | rule-engine | no | The model this work copies — the population emitted as a finding from inside the evaluator — not a work site. Its own behaviour does not change. |
| `graph/c4.py:191` | c4-diagrams | no | Reads `extra["tags"]` for `is_external` / `is_database` only; ignores `layer-*`. |
| `graph/diff.py:143,321`–`:343,412,426,462`–`:484` | graph-diff | no | Handles the DECLARED tags, which this change does not alter. |
| `graph/snapshot.py:64` | snapshot | no | Stores `nodes.extra` verbatim, so a snapshot compared across the change compares own-tags on both sides — correct, and stated so the absence is measured. |
| `application/site_dashboard/gate_metrics.py:38`, `alerts.py:82`–`:85` | application | no | Consume counters this change adds to rather than replaces. Verified as consumers; no edit derived. |
| `application/status.py`; `context_oracle/builder.py:443`–`:472`; `context_oracle/why.py`; `graph/federation/export.py:103`; `application/doctor.py` | — | no | Checked and found NOT to read tags or layer membership. Listed so the set above is a population rather than a selection. Federation in particular does not select `extra`, so layer membership does not cross that boundary. |

**Nodes kept in scope:** `rule-engine`, `graph`, `graph-loader`, `application`, `tui`, `mcp-server`,
`ci-gate`, `agent-prime`, `debt-report`, `cli-commands`, `guard-probes`, `onboarding`.

## Proposed Solution

### Approach

**One function, two releases, and the release boundary is where a verdict changes.**

`layer_of(ref_id, layers, parents, tags) -> str | None` climbs `part_of` to the nearest ancestor
carrying a tag the rule declares, and returns the node's own tag when it has one. It reads the
rule's `layers` list — never a hardcoded table. It is pure, so it is directly testable and
mutation-checkable.

**Release A — changes no verdict.**
The rule reports its population. `evaluate_layer_rules` keeps deciding on own-tags only, and
additionally counts what it would have judged under ancestry. The population is emitted the way
`scenario-coverage` emits its own — a finding from inside the evaluator — so it reaches the two
readers that bypass `lint()` without them changing. The summary line gains a clause beside
`_inert_note`. The three implementations are unified onto `layer_of` **as a computation**, with
`architecture_view`'s verdict predicate left alone for now, so no rendered result moves.

**Release B — changes verdicts, and says so.**
`evaluate_layer_rules` decides on the derived layer. The same-layer predicate becomes the one
decided below. The `agent-prime -> reindex` edge is resolved first. `architecture_view`'s predicate
is brought onto the shared one. The role template, the SPEC and the READMEs are brought to what the
rule then checks.

### The same-layer predicate — decided

**Measured on `aa4bfad4`**, over the 354 edges layered at both ends by ancestry:

| | count |
|---|---|
| same layer, **same** tagged ancestor (internal to one domain) | **114** |
| same layer, **different** tagged ancestor (peer crossing) | **16** — see the correction below |

`evaluators.py:632` (`# Same layer -- always OK`) would pass all 130, including the 16 crossings the
project's own ARCHITECTURE section forbids: *"No domain depends on a peer domain."*
`architecture_view.py:268` (`dst_rank <= src_rank`) would flag all 130, including the 114 that are
plainly legal.

**CORRECTION, 2026-09-13, found by `beadloom-xmfs` (B2) and confirmed by the coordinator.** The 16
above was computed by the wrong rule — *the same nearest TAGGED container* — and reported under a
different one. The two differ on any pair whose ends each carry a tag of their own while sharing a
tagged parent; measured, exactly one pair does: `cli-commands -> guard-probes`, both `part_of cli`,
and `cli` carries `layer-service`. Under the predicate this section decides, that edge is internal.
**The figure should have read 15.** It is corrected here rather than overwritten, because a count
produced by one rule and published under another is the defect this whole epic exists to remove, and
the coordinator produced one inside the document that defines the rule.

**Neither survives. The predicate is the third one, decided by the owner on 2026-09-12:** an edge
within one layer is legal when both ends share a tagged ancestor, and a finding when they do not.
This is the first time the peer-domain rule this project states becomes machine-checked.

The 16 crossings, which Release B must triage: `onboarding -> graph` 5, `onboarding -> context-oracle`
3, `cli-commands -> mcp-server` 2, then one each of `graph -> context-oracle`, `graph -> doc-sync`,
`cli-commands -> tui`, `cli-commands -> guard-probes`, `guard-probes -> mcp-server`,
`mcp-server -> guard-probes`.

### Changes

| File / Module | Change |
|---|---|
| `graph/rules/layers.py` (new) | `layer_of`, the shared ancestry walk, and the population counter. Pure. |
| `graph/rules/evaluators.py` | `evaluate_layer_rules` calls `layer_of`; the five `_cached_tags` closures collapse to one lookup; emits the population finding. |
| `graph/rules/liveness.py` | `_layer_reasons` calls `layer_of`; `:437` validates `LayerRule`. |
| `graph/rules/loader.py` | `validate_rules` gains the `LayerRule` case; the `tags:` catalog is resolved (removed, or made the declaration). |
| `application/architecture_view.py` | Stops defining `_LAYER_TAGS` / `_LAYER_RANK` / `_layer_of`; calls the shared lookup. Predicate aligned in Release B. |
| `graph/linter.py` | `LintResult` carries a per-rule population; a clause beside `_inert_note`; all four renderings. |
| `application/gate.py`, `services/commands/federation.py`, `services/mcp_server.py`, `tui/`, `application/debt_report/`, `onboarding/scanner/prime.py` | Render or receive the population. |
| `graph/import_resolver.py` | `_part_of_ancestors` becomes the one ancestry walk, or is called by it. |
| `.beadloom/_graph/rules.yml`, `graph.yml` | One declaration; `rules.yml` gains an owning node. |
| `.beadloom/flow/`, SPEC, READMEs, `DOC.md`s | Brought to what the rule checks, in Release B. |

### API Changes

`LintResult` gains a per-rule population field — additive, so `format_json` consumers keep working.
`beadloom lint` and the Gate gain a clause in the summary line. No command is removed or renamed.

## Alternatives Considered

### Option A: report the population and stop

Ships the honesty and none of the enforcement. Rejected by the owner on 2026-09-12 in favour of the
full scope; kept here because it is the fallback if Release B's triage proves larger than the 16
crossings suggest.

### Option B: tag every node explicitly instead of inheriting

No ancestry, no shared lookup — just 106 nodes with tags. Rejected: it is a rule held by whoever
remembers to tag a new node, which is how the current 16-of-362 came about. It also makes the
declaration grow with the graph.

### Option C: make `architecture_view` the survivor

It already has ancestry. Rejected: it hardcodes the four tags and their ranks, so it cannot serve a
project whose layers are declared differently — and Beadloom ships to those projects.

## Risks

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Release B reddens an adopter's Gate on upgrade | **High** — it is the intent | High | Release A ships the population first, so the change is visible before it bites; the upgrade note names it; the two releases are separate. |
| The 16 crossings are not all fixable, and some must become exemptions | Medium | Medium | Triage is its own bead, before the verdict change. An exemption with a stated reason is an acceptable outcome; a silent allowance is not. |
| A fourth reader of layer membership exists that name-matching missed | Medium | Medium | Stated as a limit of the supplement rather than denied. The review bead re-derives the reader set by a different method. |
| Same-layer internal edges (114) are misjudged by the shared-ancestor test on a graph shaped unlike ours | Medium | High | The predicate is tested on fixtures that are not this repository — a graph with nested components, and one with no `part_of` at all. |
| The population finding is noisy in a project with no tags at all | Low | Medium | A rule declaring layers no node carries is already the `mutation-run-zero-mutants` shape: report the zero denominator once, not per edge. |

## Open Questions

| # | Question | Decision |
|---|---|---|
| Q1 | Same-layer edges: `evaluators.py:632` or `architecture_view.py:268`? | **Decided 2026-09-12, owner:** neither. Legal when both ends share a tagged ancestor, a finding when they do not — measured at 114 internal against 16 peer crossings. |
| Q2 | Scope of the epic | **Decided 2026-09-12, owner:** the widest — population, the three implementations, inheritance, and the declaration. |
| Q3 | `agent-prime -> reindex` | **Decided 2026-09-12, owner:** resolved inside the epic, as its own bead, before inheritance ships. |
| Q4 | The shipped role template `dev.md.txt:13` | **Decided 2026-09-12, owner:** in scope. |
| Q5 | Does the `tags:` catalog at `rules.yml:3`–`:7` become the declaration, or is it removed? | **Decided 2026-09-12:** deferred to bead A6, whose done-when requires the answer in the bead's comments with a reason BEFORE the code changes. It has no production reader, so either choice is invisible today — which is exactly why it must be stated rather than taken silently. |
| Q6 | Does the population clause belong in the summary line, in a finding, or both? | **Decided 2026-09-12:** both, and the split is derived — the finding carries it, because `tui/data_providers.py` and `debt_report/collect.py` reach the evaluators without `lint()` and a summary clause cannot reach them; the summary line carries it too, beside `_inert_note`, because that is where a person reads a verdict. Beads A2 and A3 implement the two halves. |

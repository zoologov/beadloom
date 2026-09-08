# RFC: BDL-068 — The flow's rules are advice; make them instruments

> **Status:** Approved
> **Created:** 2026-09-02

---

## Overview

Six ordered slices, each independently shippable, that convert this project's multi-agent
flow from a set of rules an agent is asked to follow into a set of instruments that report
when it did not. The first slice builds the instrument the other five are measured by, so it
is inside this epic rather than beside it.

The unifying technique is already proven on this repository and is not new work: BDL-067
wrote three AST derivations that answer "who else writes this, who else calls this, how many
branches does this have" from the source rather than from a list. They live in the test suite
and are lifted into a command here.

## Motivation

### Problem

Every measured failure of the flow has one shape: a rule that is correct as written, and no
instrument that can tell a followed rule from a claimed one. The PRD carries the four proofs.
The technical statement of the same thing is narrower and more useful:

**Every existing flow check reads a channel it declares, and is read as answering a question
about all channels.** `review-brief` counts bead comments and reports `0 withheld`, which is
true of bead comments and false about what the reviewer can reach. The commit-scoped hook
judges the paths a commit stages, which is true of that commit and blind to a neighbour's hunk
inside a file it touched. `sync-check` verifies the pairs it has a baseline for. `mutation-scope`
reports a declared target outside the configured source paths — and no runner produces the
score the target was declared for.

### Solution

Two moves, applied six times.

**Derive the population, do not list it.** Wherever a check today asks "is X in this list", it
asks the source for the list instead, and the derivation is over a SHAPE rather than a
spelling. BDL-067 measured the difference: a reader detector asking for `glob("*.yml")` plus
`yaml.safe_load` by name missed five bodies that read the same directory with `iterdir`,
`listdir`, `scandir`, `walk`, or `yaml.load` with an explicit loader.

**Report the unresolved population as part of the answer.** A derivation that omits what it
could not parse produces a clean list, and a clean list is what an agent trusts and stops at.
Recall over precision: the failure mode we are moving toward is false confidence, which is
worse than the ignorance we have now.

## Technical Context

### Constraints

- Python >= 3.10, `mypy --strict`, `ruff`; the stack section of `CLAUDE.md` is authoritative.
- **Tool-agnosticism.** Beadloom must not require a runner an adopter cannot have. The
  mutation slice therefore ships the SCOPE and the report, and names `mutmut` as this
  repository's own dev dependency rather than as a shipped requirement.
- **The coordinator cannot read source.** Any artifact that describes source must be produced
  by a role or by a command, never by the orchestrating loop.
- **A check that cannot fail must not be added.** Each slice states, per check, the tree on
  which it goes red.

## Axes

Derived, never authored. An epic is not a single `impact` target: its axes are the UNION of its
slices' axes, and each slice's rows are derived when that slice begins. The first nine rows are
S1's, derived on 2026-09-02 after `c7591a8`. The twenty-eight under them are S4's and the next
five are S2's and S3's, both derived on 2026-09-04 at `d0088ba`. The last fourteen are S5's,
derived on 2026-09-04 at `b350f6b`. A row is not repeated — a sweep that reaches an axis and
node the table already names adds a second site count and no axis, and where that happened it
is stated under the table. S6 adds its rows at its own start, which is the same rule as beads
being created per slice.

> **Derived by:** `beadloom impact` over `onboarding/role_composer.py`, `doc_sync/axes_section.py`
> and `services/commands/impact.py` — the three surfaces S1 changed
> **Seed:** `none`, under the rule `reaches-an-effect-sink`, on all three. Every axis below the
> seed is therefore unresolved and not empty — S1's surfaces are composition and rendering, and
> none of them reaches a declared effect sink.
> **Unresolved:** co-writers, on all three targets — no declared effect rule found a sink these
> targets reach, so there is no commit point to ask who else writes through. Measured on
> 2026-09-02 at `c7591a8`, macOS, `beadloom impact` in the foreground.

> **Derived by:** `beadloom impact` over the twenty-eight Python source files S4 changed, which
> `git diff --name-only main...HEAD` lists: `application/declared_scope.py`,
> `application/guards/contract.py`, `application/guards/evaluation.py`,
> `application/guards/hook_payload.py`, `application/guards/invocation.py`,
> `application/guards/paths.py`, `application/guards/shell_targets.py`,
> `application/guards/surface.py`, `application/review_brief/assembly.py`,
> `application/typed_surface.py`, `application/waves/__init__.py`,
> `application/waves/derivation.py`, `application/waves/media.py`,
> `application/waves/media_checks.py`, `application/waves/models.py`,
> `application/waves/planner.py`, `application/waves/scope.py`, `doc_sync/scope_check.py`,
> `onboarding/config_sync.py`, `onboarding/guard_hooks.py`, `onboarding/role_duties.py`,
> `services/cli.py`, `services/commands/docsync.py`, `services/commands/guard.py`,
> `services/commands/impact.py`, `services/commands/setup.py`,
> `services/commands/typed_surface.py` and `services/commands/waves.py`
> **Seed:** S4's sweep resolves no seed on 25 of its 28 targets, under the same
> `reaches-an-effect-sink` rule, so their co-writers axis is unresolved and not empty. Three
> targets do resolve one and answer that axis, which S1 had none of:
> `onboarding/config_sync.py` on `persist_flow_config` (`onboarding/flow_config.py:324`,
> `serialises-yaml`), `services/commands/docsync.py` on `flow_signature`
> (`doc_sync/surface.py:179`, `serialises-yaml`), and `services/commands/setup.py` on six, the
> first being `each_graph_file` (`onboarding/graph_files.py:24`, `reads-a-yaml-directory`).
> **Unresolved:** S4's 28 runs report 418 unresolved-terminator-name, 29
> name-defined-more-than-once, 25 no-seed, 1 call-through-a-variable and 1 dynamic-dispatch,
> counted as distinct name-and-file pairs.
> **Measured on:** 2026-09-04 at `d0088ba`, in a room built with `git archive HEAD` at
> `room-beadloom-0mdo.44`, macOS 25.6.0 arm64, CPython 3.13.7, `beadloom impact` in the
> foreground, 28 runs. The same 28 runs on the working tree returned the same nodes and the
> same site counts, so `beadloom-0mdo.43`'s uncommitted edits do not move this answer.

> **Derived by:** `beadloom impact` over the sixteen Python source files S2 and S3 changed,
> which `git diff --name-only 17eafb8 97e0504` lists: `application/gate.py`,
> `application/mutation_scope/__init__.py`, `application/mutation_scope/scope.py`,
> `application/mutation_scope/score.py`, `application/review_brief/__init__.py`,
> `application/review_brief/assembly.py`, `application/review_brief/models.py`,
> `application/review_brief/reachability.py`, `application/rooms.py`, `onboarding/composer.py`,
> `services/cli.py`, `services/commands/federation.py`, `services/commands/mutation.py`,
> `services/commands/review_brief.py`, `services/commands/rooms.py` and
> `services/mcp_server.py`
> **Seed:** The S2 and S3 sweep resolves no seed on 13 of its 16 targets. Three resolve one:
> `application/gate.py` and `services/commands/federation.py` on two each, the first being
> `flow_signature` (`doc_sync/surface.py:179`, `serialises-yaml`), and `services/mcp_server.py`
> on five, the first being `each_graph_file` (`onboarding/graph_files.py:24`,
> `reads-a-yaml-directory`).
> **Unresolved:** The S2 and S3 sweep's 16 runs report 297 unresolved-terminator-name, 13
> no-seed, 12 name-defined-more-than-once, 11 dynamic-dispatch and 1 call-through-a-variable.
> **Measured on:** 2026-09-04 at `d0088ba`, in the same room. That is forty commits after those
> slices closed, which is why the five rows below are recorded as this epic's union catching up
> and not as S2's or S3's own derivation.

> **Derived by:** `beadloom impact` over the thirteen Python files through which this project
> reaches the tracker, which is S5's subject. Nine are the seam and the files its own caller
> derivation names: `services/bd_seam.py`, `application/guards/checks/bead_claimed.py`,
> `application/guards/checks/working_branch.py`, `services/commands/docs.py`,
> `services/commands/docsync.py`, `services/commands/review_brief.py`,
> `services/commands/waves.py`, `services/guard_probes.py` and `services/mcp_server.py`. Three
> are the second channel, which does not pass through the seam at all —
> `application/doc_spaces.py`, `application/gate.py` and `application/intent_reader.py` read the
> committed `.beads/issues.jsonl` export. The thirteenth is `application/active_table.py`, the
> reconcile BDL-UX #210 names.
> **Seed:** nine of the thirteen targets resolve no seed under `reaches-an-effect-sink`. Four
> resolve one — `services/mcp_server.py` five, `services/commands/docs.py` four,
> `application/gate.py` two and `services/commands/docsync.py` one — and every one of those
> seeds is `each_graph_file` (`onboarding/graph_files.py:24`, `reads-a-yaml-directory`) or
> `flow_signature` (`doc_sync/surface.py:179`, `serialises-yaml`). Both declared effects are
> about YAML, so this sweep's co-writers axis answers who else writes the GRAPH FILES and says
> nothing about who else writes the tracker: no declared effect rule describes a body that
> writes the tracker, so for S5's own subject that axis is unresolved rather than empty.
> **Unresolved:** the regions this derivation could not reach. `beadloom impact` sweeps Python
> source under `src/beadloom`, and most of this project's `bd` call sites are not Python. Counted
> by a literal search for `bd <subcommand>`, which is a spelling and therefore a LOWER bound and
> not a derivation: 118 in this repository's own harness (`.claude/CLAUDE.md` 27,
> `.claude/commands/coordinator.md` 55, `task-init.md` 10, `checkpoint.md` 8, the four composed
> role adapters 17 and `.beadloom/flow/claude/CLAUDE.md` 1); 133 in the templates this project
> SHIPS (`onboarding/templates/agentic_flow/` 116, `onboarding/templates/roles/core/` 17); 8
> inside the two hook templates, which are Python string literals in
> `services/commands/docsync.py` and so are reachable as a file and invisible as a call; and 2 in
> `ai_agents/ai_techwriter/provision-runner.sh`. One region is outside the repository entirely:
> `beadloom-l2f2`'s subject is `.git/hooks/post-merge`, written by `bd init`, carrying the
> `bd import -i` that does not exist, untracked and named nowhere under `src/`. Three further
> Python files carry `bd` in prose and invoke nothing — `application/review_brief/release.py`,
> `application/waves/media_checks.py` and `infrastructure/mcp_tools.py`.
> Its own population, over the source it did reach: the thirteen runs report 240
> unresolved-terminator-name, 12 name-defined-more-than-once and 11 dynamic-dispatch as distinct
> name-and-file pairs, and nine of the thirteen targets resolve no seed.
> **Measured on:** 2026-09-04 at `b350f6b`, over a room built with `git archive HEAD` at
> `room-beadloom-0mdo.58` and reindexed there, macOS 26.6.2 arm64, `beadloom impact` in the
> foreground, 13 runs. The room isolates the SWEPT SOURCE and the index, not the tool: `beadloom`
> is an editable install rooted at the working tree, so the code doing the sweeping is the
> working tree's in both places. `diff -rq` reports every tracked file under `src/` identical
> between the two, so the distinction does not move this answer today.

| Axis | Node | Sites | In scope | Why |
|------|------|-------|----------|-----|
| co-writers | — | unresolved (no seed on any of the three targets) | no | Nothing can be taken into scope until a seed resolves, so the decision is `no` and not `n/a` — an undecided row is what the check reads as a derivation nobody acted on. When a later slice's target does reach a sink, this row is re-derived and decided then. It is recorded rather than dropped so the blank is not read as "nothing writes here" |
| callers | `config-check` | 2, first `_composed_corpus` (`onboarding/config_sync.py:808`) | yes | `.5` had to make the composed role visible to it, which is BDL-UX #191's shape |
| callers | `role-adapters` | 1, `generate_adapters` (`onboarding/role_adapters.py:107`) | yes | The fifth role file is written through it |
| callers | `ci-gate` | 1, `_step_doc_spaces` (`application/gate.py:590`) | yes | The `## Axes` checks report through the Gate step |
| callers | `flow-guards` | 3, first `_unanswerable` (`application/guards/invocation.py:473`) | yes | S4's slice is these guards; S1 already reaches them |
| callers | `planning-report` | 1, `planning_report` (`application/planning_report.py:136`) | yes | Where the section is read back |
| callers | `work-item-type` | 1, `_collect` (`doc_sync/work_item_type.py:121`) | yes | `.5` routes the type decision through it |
| callers | `impact` | 3, first `_rows` (`application/impact/section.py:92`) | yes | The command rendering its own section |
| callers | `cli-commands` | 1, `axes` (`services/commands/impact.py:88`) | yes | The command surface |
| co-writers | `agent-prime` | 4, first `bootstrap_project` (`onboarding/scanner/bootstrap.py:36`) | no | read by this change and not written by it — no path this epic changes is owned by it |
| co-writers | `agentic-flow-setup` | 1, `scaffold` (`onboarding/agentic_flow_setup.py:360`) | yes | written by this epic — 1 of the 239 paths it changes is owned by it |
| co-writers | `cli-commands` | 3, first `link` (`services/commands/index_ops.py:203`) | yes | written by this epic — 11 of the 239 paths it changes are owned by it |
| co-writers | `doc-generator` | 2, first `_load_graph_from_yaml` (`onboarding/doc_generator.py:28`) | no | read by this change and not written by it — no path this epic changes is owned by it |
| co-writers | `doc-sync` | 1, `surface_signature` (`doc_sync/surface.py:199`) | yes | written by this epic — 1 of the 239 paths it changes is owned by it |
| co-writers | `graph-loader` | 1, `update_node_in_yaml` (`graph/loader.py:171`) | no | read by this change and not written by it — no path this epic changes is owned by it |
| co-writers | `mcp-server` | 1, `handle_update_node` (`services/mcp_server.py:212`) | yes | written by this epic — 1 of the 239 paths it changes is owned by it |
| co-writers | `reindex` | 3, first `reindex` (`application/reindex/full.py:76`) | no | read by this change and not written by it — no path this epic changes is owned by it |
| callers | `ai-techwriter` | 1, `main` (`ai_agents/ai_techwriter/cli.py:195`) | no | read by this change and not written by it — no path this epic changes is owned by it |
| callers | `application` | 3, first `_routing` (`application/landscape_view.py:169`) | no | read by this change and not written by it — no path this epic changes is owned by it |
| callers | `axes-section` | 1, `_row` (`doc_sync/axes_section.py:189`) | yes | written by this epic — 1 of the 239 paths it changes is owned by it |
| callers | `contracts` | 1, `_is_explicit_cross_repo` (`graph/contracts.py:430`) | no | read by this change and not written by it — no path this epic changes is owned by it |
| callers | `declared-scope` | 4, first `describe` (`application/declared_scope.py:117`) | yes | written by this epic — 1 of the 239 paths it changes is owned by it |
| callers | `doc-roots` | 1, `_from_block` (`infrastructure/doc_roots.py:468`) | no | read by this change and not written by it — no path this epic changes is owned by it |
| callers | `doc-shape-requirements` | 1, `shipped_placeholders` (`application/doc_shape.py:139`) | yes | written by this epic — 1 of the 239 paths it changes is owned by it |
| callers | `federation` | 1, `parse_ref` (`graph/federation/refs.py:65`) | no | read by this change and not written by it — no path this epic changes is owned by it |
| callers | `flow-suppression` | 2, first `render_suppression_notice` (`onboarding/flow_suppression.py:130`) | no | read by this change and not written by it — no path this epic changes is owned by it |
| callers | `graph` | 2, first `lint` (`graph/linter.py:103`) | no | read by this change and not written by it — no path this epic changes is owned by it |
| callers | `ignore-block` | 1, `ensure_ignore_block` (`onboarding/ignore_block.py:157`) | yes | `beadloom-0mdo.43` rewrites the shipped ignore-block entry, because this slice changed what the file it invites a team to commit now holds |
| callers | `mcp-server` | 1, `handle_bead_context` (`services/mcp_server.py:691`) | yes | written by this epic — 1 of the 239 paths it changes is owned by it |
| callers | `review-brief` | 2, first `assemble_brief` (`application/review_brief/assembly.py:93`) | yes | written by this epic — 4 of the 239 paths it changes are owned by it |
| callers | `role-duties` | 1, `_performer` (`onboarding/role_duties.py:282`) | yes | written by this epic — 1 of the 239 paths it changes is owned by it |
| callers | `rule-engine` | 3, first `_contradiction` (`graph/rules/doc_area.py:431`) | yes | the `scenario-coverage` severity decision CONTEXT records on 2026-09-04 is implemented in `graph/rules/scenario_coverage.py` |
| callers | `scenario-binding` | 1, `_keyword_or_step` (`graph/scenarios.py:287`) | no | read by this change and not written by it — no path this epic changes is owned by it |
| callers | `scope-check` | 1, `_outside` (`doc_sync/scope_check.py:262`) | yes | written by this epic — 1 of the 239 paths it changes is owned by it |
| callers | `sdl` | 2, first `extract_surface` (`graph/sdl.py:44`) | no | read by this change and not written by it — no path this epic changes is owned by it |
| callers | `site-generation` | 1, `_render_docs_overview` (`application/site.py:260`) | no | read by this change and not written by it — no path this epic changes is owned by it |
| callers | `wave-plan` | 6, first `conflict_between` (`application/waves/independence.py:58`) | yes | written by this epic — 7 of the 239 paths it changes are owned by it |
| callers | `agentic-flow-setup` | 3, first `templates_root` (`onboarding/agentic_flow_setup.py:125`) | yes | written by this epic — 1 of the 239 paths it changes is owned by it |
| callers | `doc-templates` | 2, first `doc_template` (`onboarding/doc_templates.py:100`) | yes | written by this epic — 1 of the 239 paths it changes is owned by it |
| callers | `mutation-scope` | 2, first `describe_room` (`application/mutation_scope/score.py:124`) | yes | written by this epic — 3 of the 239 paths it changes are owned by it |
| callers | `role-composer` | 3, first `roles_templates_root` (`onboarding/role_composer.py:95`) | yes | written by this epic — 1 of the 239 paths it changes is owned by it |
| callers | `work-item-routing` | 1, `task_init_routing` (`application/work_item_routing.py:218`) | yes | written by this epic — 1 of the 239 paths it changes is owned by it |
| callers | `tui` | 16, first `__init__` (`tui/app.py:66`) | no | read by this change and not written by it — the TUI reaches `guard-probes` for its display and no path this epic changes is owned by it |
| callers | `agent-prime` | 8, first `_pyproject_version` (`onboarding/scanner/project_facts.py:71`) | no | read by this change and not written by it — no path this epic changes is owned by it, which is what its co-writers row above already decided |
| callers | `intent-reader` | 2, first `read_intent` (`application/intent_reader.py:50`) | no | the second channel to the tracker, read and not written — it reads the committed `.beads/issues.jsonl` export and no path this epic changes is owned by it |
| callers | `doc-sync` | 1, `declared_project_name` (`doc_sync/audit_self_surface.py:48`) | yes | written by this epic — 1 of the 88 owned paths it changes is owned by it |
| callers | `guard-probes` | 1, `claimed_beads` (`services/guard_probes.py:67`) | yes | `beadloom-0mdo.52` rewrites this consumer — it is the one site that already asks `bd list --json` for an unfiltered population (`--limit 0`), and BDL-UX #187 requires every consumer to state which population it asked for |
| branches | `bd-seam` | 2 at the target seat, `run_bd` (`services/bd_seam.py:88`) with 1 branch and 3 exit forms | yes | `beadloom-0mdo.51` builds the derived call-site population here: the seam is the single place this project's code reaches `bd`, and putting a new module under a node this table rules out is the finding the slice was opened to answer |
| branches | `active-table` | 15 at the target seat, first `short_form` (`application/active_table.py:52`); widest `resolve_row_bead_id`, 2 branches | yes | `beadloom-0mdo.54` rewrites `resolve_row_bead_id` and `_reconcile_one` for BDL-UX #210 |
| branches | `guard-probes` | 5 at the target seat, first `build_probes` (`services/guard_probes.py:153`), 1 branch and 1 exit form | yes | `beadloom-0mdo.52`'s #187 consumer, for the reason its callers row above carries |
| branches | `cli-commands` | 75 at the target seat, first `docs` (`services/commands/docs.py:23`); widest `_run_brief`, 4 branches | yes | written by this epic — 11 of the 88 owned paths it changes are owned by it |
| branches | `mcp-server` | 36 at the target seat, first `_compute_mtimes` (`services/mcp_server.py:61`); widest `_dispatch_tool`, 4 branches | yes | written by this epic — 1 of the 88 owned paths, and `beadloom-0mdo.53` changes `_bd_create_bead` and `handle_task_init` for BDL-UX #171 |
| branches | `flow-guards` | 3 at the target seat, first `_not_covered` (`application/guards/checks/bead_claimed.py:33`); widest `check_bead_claimed`, 3 branches | yes | written by this epic — 8 of the 88 owned paths it changes are owned by it |
| branches | `ci-gate` | 36 at the target seat, first `_run_doctor_checks` (`application/gate.py:73`); widest `run_ci_gate`, 1 branch | yes | written by this epic — 1 of the 88 owned paths it changes is owned by it |
| branches | `doc-spaces` | 22 at the target seat, first `_related_refs` (`application/doc_spaces.py:259`); widest `check_spaces`, 5 branches | no | the second channel, read and not written — no path this epic changes is owned by it |
| branches | `intent-reader` | 2 at the target seat, `read_intent` (`application/intent_reader.py:50`) with 2 branches and 2 exit forms | no | the second channel, read and not written — no path this epic changes is owned by it |

**The scope decision (S1).** Every caller row is in scope for this epic because each is a
surface a later slice edits — S4 is the guards, S6 is the composer and `config-check`. Nothing
is excluded, which is a decision and not an omission: an epic that declared a narrower scope
than its own slices would make `.6` red on its second commit.

**The scope decision (S4).** The rule, stated so a later slice can apply the same one: a row is
`yes` when this epic WRITES the node and `no` when it only READS it. Which nodes it writes is
measured rather than judged — the 239 paths BDL-068 changes since `17eafb8^` resolve to thirty
owning nodes, and every `yes` row's `Why` carries that node's share of them. Two rows are `yes`
on a commitment named elsewhere instead: `ignore-block`, which `beadloom-0mdo.43` edits because
this slice changed what the shipped ignore entry invites a team to commit, and `rule-engine`,
where the `scenario-coverage` severity decision CONTEXT records on 2026-09-04 is implemented.
Fourteen of S4's twenty-eight rows are `no`, and that is what S1's blanket `yes` did not have:
a `no` row makes a commit on that node a finding instead of a silence, whereas under S1's table
`scope-check` reported "36 staged path(s) a node owns, 65 no node owns" with zero findings
while none of the seven nodes S4 was editing was named anywhere. A later slice that needs one
of the fourteen re-derives and moves the row with its reason, which is the same per-slice rule
as the derivation itself. S4's sweep also reaches four nodes S1's rows already name — `ci-gate`
(3 sites), `cli-commands` (58), `config-check` (1) and `flow-guards` (14) — and those rows are
not repeated.

**The scope decision (S2 and S3), taken on 2026-09-04.** Their rows were never derived when
those slices began, which is the standing gap the S4 review named. They are added now rather
than left open, because this section's job is to be the union this epic is judged against, and
an incomplete union is a wrong verdict in the present: `beadloom waves` reported
`mutation-scope: not_derived — no row of RFC.md names it` against `beadloom-0mdo.45`, whose
declared scope is exactly that node. The sweep is dated and attributed to the tree it was
actually run on rather than to the tree those slices began on, because a derivation restated as
older than it is would be the defect this bead was opened to repair, one layer up. Nineteen of
its twenty-four rows name an axis and node the table already carries and are not repeated. The
five that are new are `yes` under the same measured rule.

**The scope decision (S5), taken on 2026-09-04.** Same measured rule as S4, re-measured on this
tree: BDL-068 changes 244 paths since `17eafb8^`, 88 of them owned, and those 88 resolve to 31
owning nodes. A row is `yes` when the node is among the 31, or when one of S5's six beads names
it as a write target in its own description; a row is `no` otherwise. Five rows are `yes` on the
measurement (`cli-commands` 11 paths, `flow-guards` 8, `doc-sync` 1, `mcp-server` 1, `ci-gate` 1)
and three on a named commitment: `bd-seam` and `guard-probes` for `beadloom-0mdo.51` and `.52`,
and `active-table` for `.54`. Six rows are `no`, four of them the two channels this slice reads
without writing — `doc-spaces` and `intent-reader` read the committed `.beads/issues.jsonl`
export, and `tui` and `agent-prime` reach the swept files for display and priming.

**`application` stays RULED OUT, and widening it was never the fix.** `beadloom waves` reported
`declared_outside_the_axes` against `beadloom-0mdo.51`, `.52` and `.53`, each of which carried a
hand-written `refs: cli-commands, application`. The declaration confused a LAYER with a NODE.
Node `application` owns eighteen files and every one of them renders a view —
`architecture_view.py`, `landscape_view.py`, `site_about.py`, `site_landscape.py`,
`site_mermaid_guard.py` and the `site_dashboard/` package — and none of them reaches the tracker.
BDL-068 has written none of them: `application` is not among the 31 nodes owning the 88 paths the
epic changes. The application-layer files S5 does touch are each owned by a node of their own —
`active-table`, `flow-guards`, `ci-gate`, `doc-spaces` and `intent-reader` — so approving
`application` would have put eighteen view-rendering files inside the approval to buy a name that
none of S5's surfaces needs. The three declarations are regenerated from the rows above instead.

**What this section cannot judge, stated because it is unresolved and not empty.** The
derivation reaches Python source only, and by the count in the S5 block above at least 261 of
this project's `bd` call sites are prose — the harness that instructs an agent, the templates it
ships, the hook bodies held as string literals, and `.git/hooks/post-merge`, which `bd` writes
outside the repository. No row below names them, and no `no` row should be read as covering
them: a commit that changes `.claude/commands/coordinator.md` is judged by no axis in this
table. That is the population `beadloom-0mdo.51` exists to derive, and until it does, the four
tracker findings this slice answers are asserted at their nine Python sites and instructed at
the rest. A second limit belongs beside it: a node whose file is named in a `Derived by` field
is inside the approval by construction (`WorkItemAxes.approved` is `kept | targets`), so
`doc-spaces` and `intent-reader` are approved by having been SWEPT even though their rows read
`no`. That rule was written when a slice's targets were the files it changed; S5's targets are
the files it reads, and the rows above are the record of the decision the widening does not
express.

## Proposed Solution

### Approach

**S1 — `beadloom impact`, the `## Axes` artifact, and the `Explore` protocol.**

`beadloom impact <path|symbol>` answers four questions from the source: who else writes the
files this writes, who else calls what this calls, how many branches the enclosing command
has and how many ways it terminates, and which of those the derivation could not resolve. The
graph supplies the boundary — the domain each found site belongs to — so the answer says when
a change leaves its domain. The three BDL-067 derivations are lifted out of `tests/` into a
production package; they are the bulk of the logic and they already carry anti-vacuity cases.

`## Axes` becomes a section of the BRIEF and RFC core templates. `doc_templates.required_sections`
already derives a document's required sections from the composed template's literal `## `
headings, so adding the heading makes it required by the same act, and `doc-quality` reports its
absence exactly as `missing_sections` reports any other.

`Explore` gets a file in `.claude/agents/` with a fixed deliverable — the `## Axes` section,
paths and lines, no narrative — and runs inside `/task-init` before the type is chosen.

**S2 — the review's independence, reported rather than asserted.**

`review-brief` stops reporting what it withheld and starts reporting what is REACHABLE:
bead comments, the epic documents a prompt may name, and the commit bodies of the reviewed
range. The count changes from `0 withheld` to a per-channel statement, and a channel it
cannot inspect is named rather than omitted.

**S3 — what we measure with.** `mutmut` over `graph/rules/` as this repository's first slice,
scoped by `source_paths` / `do_not_mutate` / test selection, with the score produced in CI.
`mutation-scope` gains its missing half: a declared target inside the paths still scores, and a
run that produced no mutants is a finding rather than a zero. Two further measurement gaps join
this slice because they are the same defect: a clean-room verdict cannot see a cross-bead
interaction (#181), and a verdict that does not name its platform is not a verdict (`mr2l.61`,
and the ten-to-one failure at the end of BDL-067).

**S4 — the guards' surface.** Each guard's enforcement surface is derived from its own matcher
and compared against the write paths that exist, so a file written through `Bash` where the
guard watches `Edit|Write` is reported (#170). The commit gate learns to see a neighbour's hunk
inside a file the committer touched (`mr2l.81`).

**S5 — the tracker adapters.** Every External finding is answered by our behaviour in the face
of it: never read `bd list --json` as complete (#187), never trust `merge-slot` as exclusion
between agents that share one identity (#194), never write an id into a title a concurrent
create can shift (#171).

**S6 — the flow's own documents and roles.** `ROADMAP.md` and `BDL-UX-Issues.md` become
document KINDS whose counts the tool computes (`mr2l.72`), which is also what makes a duplicate
issue number impossible (`mr2l.91`, and the near-duplicate #211 this session produced).
`setup-agentic-flow` stops recomposing a hand-edited role adapter without `--force` (#191), and
the vendored-agents snapshot loop is closed in the remaining direction (`beadloom-iur5`).

### Changes

| File / Module | Change |
|---------------|--------|
| new package under `application/` | the three AST derivations, lifted from `tests/`, plus the unresolved-population report |
| `services/commands/` | `beadloom impact` |
| `onboarding/doc_templates.py` + core templates | `## Axes` heading, hence required by derivation |
| `.claude/agents/explore.md` | new role file with a fixed deliverable |
| `application/` — `review_brief` | reachability report replaces the withheld count |
| `pyproject.toml`, `ci.yml` | `mutmut` dev dependency and the scoped CI job |
| `graph/rules/` — `mutation_scope` | the half that reports a target that produced no mutants |
| `guard-hooks` | surface derivation and the unwatched-path finding |
| `doc_sync/` — document kinds | `ROADMAP` / issue-log kinds with computed counts |

### API Changes

`beadloom impact` is new. `review-brief`'s output shape changes: consumers reading the
`withheld` count must read the reachability block instead. No graph schema change is planned;
if the impact node needs one, PLAN states it before S1 begins.

## Alternatives Considered

### Option A: build `impact` as a graph walk over `part_of` / `depends_on`

Rejected, and the reason is the whole risk of this epic. Not one axis BDL-067 needed is a fact
of the graph — the writers of `.beadloom/_graph/`, the branches of `init`, its exit forms, the
modes, the renderers, the YAML readers and their policies all live INSIDE one node. A graph walk
would answer confidently and miss all of them: a green describing the checker's ignorance,
shipped as a feature. The graph supplies the boundary and nothing else.

### Option B: keep the rules as prompt text and rely on role discipline

Rejected on three measurements. The mutation duty shipped into every role core with no runner;
the review's withholding was defeated through `ACTIVE.md` and then through commit bodies. Each
rule was correct as written and none of them held.

### Option C: one monolithic work item covering all 24 findings

Rejected on this project's own measurement. BDL-067 was one bug that became 28 beads and nine
review passes whose finding count did not decay, and the retro named the cause: nothing
re-plans a work item whose type stops being true. Twenty-four findings taken at once starts in
the state BDL-067 reached at its fourth cycle.

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| `impact` under-reports and agents trust it, inverting ignorance into false confidence | High | High | The unresolved population is part of the answer, not an omission; S1 ships no check that consumes the axes until the report names what it could not resolve |
| The axes declaration lives in two places — the document and the bead's `refs:` that `waves` already reads — and they disagree | High | Medium | Open question Q1; one home is chosen in PLAN, and the other derives from it |
| The mutation slice costs more CI minutes than the project accepted for `tests-windows` | Medium | Medium | Scoped to `graph/rules/` with per-mutant test selection; measured before the CI job is added, and the job is nightly if the PR budget cannot hold it |
| Lifting the derivations out of `tests/` weakens the tests that currently hold them | Medium | High | The tests keep their assertions and import the lifted code; a derivation with no test that fails on a fifth body is not lifted |
| Six slices become nine, the way nine review passes became nine cycles | Medium | High | The re-plan rule is armed from S1: a second ISSUES verdict on one slice re-plans rather than cycles, and the stop rule is written into each review bead |
| An External `bd` behaviour changes upstream and our adapter's workaround becomes the wrong shape | Low | Medium | S5 states the upstream issue beside each workaround so the workaround can be withdrawn deliberately |

## Open Questions

| # | Question | Decision |
|---|----------|----------|
| Q1 | Does the `## Axes` declaration live in the document, or in the bead notes where `waves` already reads `refs:`? Two homes are two things that can disagree. | **The document** (2026-09-02). The derivation's output and the person's scope decision live in the `## Axes` section, and the bead's `refs:` is generated from it by `beadloom axes --refs`. One computation, two renderings, and a disagreement between them is a finding. |
| Q2 | Does the commit-scope check compare against the axes of the claimed bead, or against the axes of the work item? A bead is narrower, and a work item is what the human approved. | **The work item's axes** (2026-09-02). A bead may narrow freely inside them, and a commit that leaves them means the approval no longer covers the change, which is the re-plan trigger. |
| Q3 | Does the mutation job run per PR or nightly? `tests-windows` was withdrawn at ~16-28 runner-minutes per PR, which is the budget this must fit under. | **Nightly** (S3.1, 2026-09-03). Measured: 3 989 mutants over `graph/rules/` in 54 min 55 s at 1.42 mutations/second, six workers, on a 10-core Darwin arm64 machine running CPython 3.13.7. That is two to three times the budget, on hardware faster than `ubuntu-latest`, so the decision does not turn on the CI figure. Against ~4-minute ubuntu legs the job would also be the pipeline's whole critical path — the second half of the `tests-windows` reasoning. |
| Q4 | For the External `bd` findings, is the deliverable a wrapper this project owns, or documented avoidance in every caller? | **Neither a wrapper nor prose** (2026-09-02). Our own `bd` call sites are derived and each one's behaviour in the face of the finding is asserted, because a wrapper is a second thing to keep in step with upstream and a derived population fails on a call site added later. |
| Q5 | Is `Explore` a fourth role subagent, or a mode of an existing one? A fifth role file is a fifth thing that can drift out of `setup-agentic-flow`. | **A role file** (2026-09-02), composed by the same composer as the other four. A mode has no protocol file, which is why the one `Explore` run in BDL-067 returned a trace of the defect and nothing about axes. |

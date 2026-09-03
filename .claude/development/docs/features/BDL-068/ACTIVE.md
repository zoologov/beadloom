# ACTIVE: BDL-068 — The flow's rules are advice; make them instruments

> **Last updated:** 2026-09-03
> **Phase:** Development

---

## Current Bead

**Bead:** `beadloom-0mdo.17` — the S1 re-review, now that the critical is closed on the tree
that shows it and the suite has a fixture per source layout that can disagree with the sweep.

**S3.7 just closed, and it is this epic's own shape found twice inside its own suite.** PR #60's
two `tests-locale` legs were red on two tests S2 and S3 wrote, each of which could not run in the
room it was about. One built a work-item folder whose CJK name an ASCII filesystem cannot hold, so
the ARRANGEMENT failed and the assertion was never reached; its guard now asks the room -- can this
run's filesystem encoding spell the name -- rather than the platform, because a platform guard would
delete the case on all of Linux including the four `tests` legs where it runs today, and the skip
states where it still fails. The other was a scenario about naming rooms that stepped aside on
exactly the legs where the run is inside one; it was REWRITTEN rather than skipped, because "entered
0 of 2" and "entered 1 of 2" are the same claim at different arithmetic. A run inside a declared leg
now judges what `entered` means, on a developer machine too.

**S3.6 just closed.** `beadloom-0mdo.29` — the duty and the instrument now arrive at the
same reader. S3 built `beadloom mutation` and left the test role telling an agent to write
the surviving count into a bead comment by hand, which is the defect this epic removes,
one layer up. The fix is one bullet in `roles/core/test.md.txt` and a recomposition through
the wiring that already existed, so `config-check` reports the composed adapter as drifted
the moment anyone edits it independently — verified by making that edit.

**S3.2 just closed, and this wave's combined tree is measured.** `beadloom-0mdo.23` — a verdict
now names the room it was taken in, and the room list is DERIVED: interpreters from the
packaging metadata, legs from every job of every workflow, so a leg added later is covered by
the same act that added it. Measured on this repository: 21 declared rooms, **0 entered** by a
local macOS run, four supported interpreters each with a leg, one unresolved job. The Gate, the
MCP `complete_bead` verdict and `beadloom mutation` all print the same room, and three tests
fail if naming it ever changes a status, an exit code or a finding count. The combined tree
after `.19` and `.23`: `beadloom ci` rc 0, 8369 passed, `ruff` clean, `mypy --strict` Success on
3.10, 3.11, 3.12 and 3.13 — macOS, which is 0 of the 21 declared rooms, and that sentence is now
computed rather than remembered.

**S2.2 just closed.** `beadloom-0mdo.19` (commit `8b3974a`) — the tests under `.18`'s
reachability report.

**S3.1 just closed.** `beadloom-0mdo.22` — the mutation runner over `graph/rules/`, and the
score produced by a command. Q3 is answered and the answer is nightly: 3 989 mutants take
54 min 55 s in a room this file names, against a budget of ~16-28 runner-minutes. The first
slice scores 96.2%, and the 152 survivors are a list somebody can now read rather than a
sentence somebody wrote.

**The bead just closed.** `beadloom-0mdo.7` — the derivations as shapes, the unresolved
population, and the two new checks.
**Goal:** audit what `.1`–`.6` built rather than add to it, and close the two gaps they
recorded and deliberately did not repair.
**The census came before the writing, and it changed what got written.** `.1`'s vacuity method
— blind a finding computation, re-run its module — was run over every real-tree finding list in
the lifted package's eight consumer modules. All eight survive the blinding, which is expected:
blinding an ASSERTION does not blind the DETECTOR. Seven of the eight have a detector
demonstrated capable of rejecting on a synthetic input; the prose sibling-reference scanner
`.1` refused to lift has none, so `.1`'s finding reproduces and nothing else in the package
shares the property. Three gaps closed and one recorded: each verb of `PUTS_BYTES_ON_DISK` is
now load-bearing and the vocabulary the commit point actually writes through is stated, the
prose scanner is given four trees built to dangle, the unresolved report's direction is pinned
at the two renderers where nothing reached it — and a routing row whose `Flow` cell spells
neither word is dropped with no note, which is recorded as a gap rather than repaired because
the obvious repair fires on the table's own alignment row.

**Previously closed.** `beadloom-0mdo.6` — the commit-scope check: a change outside the
work item's declared axes is a finding.
**Goal:** compare the paths a commit stages against the axes a human approved, so a commit
leaving the approval is a finding rather than something noticed afterwards.
**The rule was measured before it was chosen, because an always-red check is an ignored
check.** Judging a staged path's owning NODE against the nodes the kept rows name is red on
all three of this branch's own code commits — the table records what a change RANGES OVER and
the surfaces it CHANGES live in the `Derived by` field. Judged at the bounded context the
declared axes reach, the same three commits are silent and 115 of the 155 commits before this
branch that touch an owned path fall outside. Both halves verified on real commits: silent
over the branch's 36 owned paths against `origin/main`, and red on `a4738b7c` for
`src/beadloom/graph/linter.py`.

**Previously closed.** `beadloom-0mdo.5` — the `Explore` role, composed by `role-composer`,
inside `/task-init` step 0.5
**Goal:** give the role that derives the axes a protocol file with a FIXED deliverable, and put
it before the type decision so the axis count is what the route is chosen on.
**Both halves of the premise needed measuring, and both were half-false.** "Composed like the
other four" presumed one role population; there were TWO hand-maintained literals of it
(`role_composer.ROLE_NAMES`, `agentic_flow_setup.AGENT_FILES`) with eight readers between them,
and a third list spelled as prose inside the Cursor orchestrator pointer. The population is now
DERIVED from the shipped CORE fragments, so a role exists because a fragment ships for it.
"`/task-init` cannot reach the type decision without it having run" was false: measured at
`2a5c0d1`, `## Axes` was required by the BRIEF template and reported by nothing, because
`missing-section` is peer-relative and the corpus carried it in 0 of 12 briefs.

## Progress

- [x] PRD approved (2026-09-02)
- [x] RFC approved — six slices, three alternatives rejected with reasons
- [x] CONTEXT + PLAN approved — Q1, Q2, Q4, Q5 decided; Q3 left open with its decision rule
- [x] Beads created: epic `beadloom-0mdo`, nine S1 beads, five slice placeholders, DAG wired
- [x] S1.1 — the three derivations lifted into `application/source_derivation/` (dev)
- [x] S1.3 — the derivations validated against BDL-067 retroactively; the answer is partial
- [x] S1.2 — `beadloom impact`, seed derived and named, unresolved population as a field (dev)
- [x] S1.4 — `## Axes` required by the template that carries it; nine checks behind one
      composition; `beadloom axes` generates the bead `refs:` from the document (dev)
- [x] S1.5 — the `Explore` role composed from a shipped fragment; the role population derived
      rather than declared three times; `/task-init` step 0.5 before the type decision, and the
      route checked against the axes (dev)
- [x] S1.6 — `beadloom scope-check`: the paths a commit stages, judged against the axes its
      work item declared; wired into the pre-commit hook and into the Gate as a branch-scoped
      step (dev)
- [x] S1.7 — the derivations audited as shapes: every verb of the disk-write vocabulary made
      load-bearing, the prose scanner `.1` refused to lift given trees built to dangle, and the
      unresolved report's direction pinned at the renderers (test)
- [x] S1.10 — the epic's first CRITICAL closed: the sweep is a claim the answer can withdraw,
      and a branch count names the seat it was taken from (dev)
- [x] S1.11 — a fixture per source layout, because the critical was invisible to a suite whose
      every fixture built the one shape the old walk was right about (test)
- [ ] S1 — `impact` + `## Axes` + `Explore`
- [x] S2.1 — `review-brief` states what is REACHABLE per channel instead of what it withheld; the document population derived from the composed prompts, the launch prompt named as a channel nothing can inspect (dev)
- [ ] S2 — the review's independence
- [x] S2.2 — the reachability report's two properties, seeded from the populations (test)
- [x] S3.1 — `mutmut` over `graph/rules/`, the score produced by `beadloom mutation` rather
      than asserted in a bead comment, and Q3 answered by the measurement: nightly (dev)
- [x] S3.2 — a verdict names the room it was taken in, and the room list is derived from the
      packaging metadata and the CI workflows rather than written down (dev)
- [x] S3.7 — the two tests of this epic's own that could not run in the rooms they are about: one
      guarded by the encoding rather than the platform, one rewritten to hold inside a declared leg
      as well as outside it (dev)
- [ ] S3 — what we measure with
- [ ] S4 — the guards' surface
- [ ] S5 — the tracker adapters
- [ ] S6 — the flow's documents and roles

## Results

| Bead | Status | Details |
|------|--------|---------|
| `beadloom-0mdo.1` | Done | the three derivations lifted into `src/beadloom/application/source_derivation/` (six modules by responsibility, a `component` node with a DOC). The tests keep their assertions and supply the seeds; measured with `git diff --numstat`, the five affected test modules shrink by 329 lines net (466 deleted, 137 added) and the package is 716 lines. Each lifted shape is demonstrated capable of failing by mutating it and running the suite: reader verbs narrowed → 5 red, the call vocabulary narrowed to attribute calls → 1 red, the writer payload half removed → 4 red, the reachability fixpoint frozen → 13 red, the terminator reduced to `Return \| Raise` → 2 red, the bypass sweep made blind → 1 red. One derivation REFUSED and reported: the prose sibling-reference scanner, which passes 27/27 with its finding computation replaced by `[]`. Green on the tree, macOS: 7867 passed, `ruff` and `mypy --strict` clean, `beadloom ci` rc 0. |
| `beadloom-0mdo.2` | Done | `beadloom impact <path\|symbol>` in `src/beadloom/application/impact/` (six modules by responsibility, a `feature` node with a SPEC) plus `services/commands/impact.py`, human and `--json`. The seed is DERIVED under the rule `reaches-an-effect-sink` — a name the target reaches transitively whose own body performs a declared effect directly — and the answer names the seed, the rule and the effect. Measured at `af26750d`, macOS, foreground, through `git archive` with no argument naming a commit point: `bootstrap.py` → seed `write_yaml_atomic`, co-writers 6 including `bootstrap_project` and `import_docs`; `setup.py` → 7 seeds including it and none of the first-hop names, `init` 4 branches, exits `{return, sys.exit(0)}`. A target no rule finds a sink for reports `co_writers.resolved = false` with the reason, never an empty list. Eight kinds in the unresolved population. 9 scenarios (red before the code existed) + 20 cases; every case demonstrated red by eight mutants — forward closure frozen at the first hop → 8, seeds taken from what reaches a sink → 12, an absent seed rendered as empty → 2, the population dropped → 7, the effect conjunction turned into a disjunction → 3, `ends_the_branch` reduced to `Return \| Raise` → 3, the boundary claiming an index it did not read → 2, `PUTS_BYTES_ON_DISK` added to the effect table → 2. Green on the tree, macOS: 7905 passed, `ruff` and `mypy --strict` clean, `beadloom ci` rc 0. |
| `beadloom-0mdo.3` | Done | measured at `af26750d` (the parent of `acf4066`, 2026-08-31), macOS, foreground, the lifted package imported from `430d9ae` and pointed at a detached worktree. Seeded with the commit point `write_yaml_atomic` the derivations list 2 writers (`bootstrap_project`, `import_docs`) and 4 branches of `init`; seeded with `bootstrap_project`, the function that bead was changing, they list 0 writers and 3 branches — the number the epic carried throughout. Both facts were in reach on the day and neither is reached from the function under change, so the premise survives as a conditional and the condition is now S1.2's hardest criterion. Second measurement: the seed is derivable from the target under `SERIALISES_YAML` (2 candidates from `bootstrap.py`) and unreachable under `PUTS_BYTES_ON_DISK`, which does not contain the commit point at all. Kept as 8 cases in `tests/test_the_seed_decides_what_impact_reports.py`, each demonstrated red. |
| `beadloom-0mdo.4` | Done | `## Axes` in the BRIEF and RFC skeletons, required by the same act that adds it: `required_sections_by_document_kind` runs `doc_templates`' own heading extraction over the composed `/templates` command's fenced blocks. `doc_shape`'s peer-majority policy extracted into `peer_section_shape` and used over both corpora; `check_planning_sections` reports `missing-section` (peer-relative) and `empty-section` (not). `doc_sync/axes_section.py` holds the section's grammar — `axes-without-a-seed`, `axis-without-a-scope-decision` — and `application/impact/section.py` renders one from an `ImpactAnswer` using that grammar, so the writer and the reader are one shape. `application/planning_report.py` is now the ONE composition of all nine checks behind the gate step and `beadloom docs quality`. New CLI: `beadloom impact --section` and `beadloom axes <document> [--refs]`. Measured on this repository, foreground, no pipe: `missing-section` 102 over 256 read, `empty-section` 0 over 256, 17 kind-level conventions including `BRIEF Axes (0/12)` and `RFC Axes (0/48)`; the 767 findings a non-peer-relative policy would give is why the peer one was chosen. `empty-section` was 155 until a defect the run exposed — a section whose content lives in its subsections read as empty — was fixed by propagating content up the heading depth. 9 scenarios + 29 cases, every case demonstrated red by eleven mutants. Green on the tree, macOS: 7944 passed (baseline 7905), `ruff` and `mypy --strict` clean, `beadloom ci` rc 0. Green in a clean room over 33 files, with the pre-existing sync-baseline failure reproduced at HEAD alone. |
| `beadloom-0mdo.5` | Done | `Explore` is a role FILE with a fixed deliverable — the `## Axes` section rendered by `beadloom impact --section`, every site a path and a line, the scope column left for the person, no narrative — read-only tools, `ddd`/`fsd` and `python` overlays. **A role exists because a core fragment ships for it:** `roles_in()` derives the population from `templates/roles/core/*.md.txt` over a shape (front matter naming its own file), so `ROLE_NAMES`, `AGENT_FILES` and the Cursor pointer are one fact instead of three. `/task-init` gains a mandatory step 0.5 stated BEFORE the type table, and the routing table is read back out of the composed command by `application/work_item_routing.py` — so the command cannot state a route the check does not police. `doc_sync/work_item_type.py` adds `routed-without-axes` and `route-not-supported-by-the-axes` over the work-item FOLDER. Measured on this repository, foreground, no pipe: `routed-without-axes` 12 findings over 12 work items — including BDL-067's own BRIEF, the item this slice exists because of — and `route-not-supported-by-the-axes` 0 over the same 12, which cannot fire until a work item carries axes and is verified red on fixtures instead. The `BRIEF Axes (0/12)` convention line is gone: the absence is now reported absolutely and withdrawn from the peer half alone, so `empty-section` still reads it. 11 scenarios (red before the code existed) + 43 cases, every case demonstrated red by sixteen mutants; two further mutants SURVIVED and both guards were DELETED rather than re-tested, because a guard nobody can make fail is a guard nobody can argue with. Green on the tree, macOS: 8023 passed (baseline 7944), `ruff` and `mypy --strict` clean, `beadloom ci` rc 0. |
| `beadloom-0mdo.6` | Done | `beadloom scope-check` compares the paths a commit stages — or, with `--since`, the paths a branch changes against its trunk — against the `## Axes` its WORK ITEM declared. `doc_sync/scope_check.py` holds the check, pure: paths, a `DeclaredScope` and an ownership map in, a verdict out. `application/declared_scope.py` makes the join `scope-check` cannot make for itself — the branch names the work item (the pre-commit hook runs before the commit message is finalised, so the `[KEY]` prefix is unreadable there), the index owns the paths, and the planning corpus says which folders are work items. **The rule was measured before it was chosen:** the node-level rule is red on all three of this branch's code commits (11, 5 and 6 paths) because the table records what a change RANGES OVER while the surfaces it CHANGES are in the `Derived by` field; the bounded-context rule is silent on all three and outside for 115 of the 155 preceding commits that touch an owned path. A node an axis rules OUT of scope is reported by that axis's name; an undecided row neither widens nor narrows and its count travels with the verdict; a path no node owns is counted, never reported. Verified on REAL commits: silent over the branch's 36 owned paths against `origin/main`, red on `a4738b7c` for `src/beadloom/graph/linter.py` naming `callers`. One measured contract detail: `--since main` reported that path where `--since origin/main` was silent, because a local trunk two commits behind makes another work item's LANDED change read as this branch's — hence `ref...HEAD` and `origin/<trunk>`. Wired into both pre-commit hook templates (WARN in both, because one work item in 64 carries a section today) and as the branch-scoped Gate step `scope-check`. 9 scenarios (red at collection before the code existed) + 54 cases; every case demonstrated red by sixteen mutants, four of which SURVIVED the first pass and each exposed a real gap — including a two-dot/three-dot case that `--diff-filter=ACMR` masked until it was rebuilt on the shape `a4738b7` actually has. Green on the tree, macOS: 8087 passed (baseline 8026), `ruff` and `mypy --strict` clean, `beadloom ci` rc 0. |
| `beadloom-0mdo.7` | Done | An AUDIT of what `.1`–`.6` built, not a quota. **The census came first:** `.1`'s vacuity method (blind the finding computation, re-run the module) was run over every real-tree finding list in the lifted package's eight consumer modules — eight survive the blinding, and seven of the eight have a detector demonstrated capable of REJECTING on a synthetic input, so `.1`'s prose sibling-reference scanner is the only one with that property and nothing else in the package shares it. **Three gaps closed.** (1) `PUTS_BYTES_ON_DISK` now has one synthetic writer per verb, where `write_bytes` and `open` were carried by nothing (the real package names one body and it writes with `write_text`), plus the shape that ACTUALLY holds and was nowhere stated: the commit point writes through `fdopen`, `write` and `replace`, which the set spells none of — so a widening is a red test naming the re-measurement it owes rather than a silent re-answer of every `impact` target. (2) The scanner `.1` refused to lift takes a package parameter and is given four trees built to dangle; blinding it was 0 red before and is 2 red now. (3) The unresolved report's DIRECTION at the two renderers, which nothing reached: one answer carries an unresolved population and a resolved-and-empty one, `sites` is `[]` on both sides, and the text and the JSON must keep them apart. Plus `.5`'s handed spellings — four launch forms found, two near-misses refused — and one GAP recorded rather than repaired: a routing row whose `Flow` cell spells neither word is dropped with no note, taking its document kinds and its work items out of `routed-without-axes`' population silently. 25 cases, eleven mutants, one re-applied because the first form did not run. `.6`'s two scope-check directions re-derived independently and reproduced exactly. Green on the tree: 8115 passed (baseline 8090), `ruff` and `mypy --strict` clean, `beadloom ci` rc 0. Green in a clean room over 3 files; and the clean-room measurement `.6` never took was taken in a pristine room at `803ef06`: Gate rc 0, 8071 passed with the one pre-existing environmental failure every sibling recorded. |
| `beadloom-0mdo.8` | Done | REVIEW ISSUES — 1 critical, 3 major. The assigned question was answered and the answer is the finding: `beadloom impact` under-reports on a PEP 420 namespace tree, not on this repository's, where every package carries `__init__.py`. Routed: critical 1 + major 2 + minor 5 → `.15`, major 3 → `.16`, major 4 → `.9`, re-review → `.17`. |
| `beadloom-0mdo.9` | Pending | blocked by `.17` — tech-writer, and it owns finding 4 (`docs/services/cli.md` carries no `### beadloom impact` and no `### beadloom scope-check`) |
| `beadloom-0mdo.15` | Done | the critical closed on the tree that shows it. `package_root_of` no longer requires `__init__.py` on the way up — it stops below a `src`-named directory, below one carrying `pyproject.toml`, and never above the project root — and `source_root_of` counts a child of `src/` that HOLDS Python at any depth. `callers.resolved` is a predicate over whether the swept root holds the target, and two new unresolved kinds (`target-outside-the-sweep`, `sweep-narrower-than-the-project`, the second carrying both paths) mean a narrowed answer cannot read as a complete one. Both renderers print the sites an unresolved axis DID find, under the caveat rather than instead of it. MAJOR 2: the branch axis is computed for the caller sites already found and every count carries its seat — `impact bootstrap.py --section` now writes `init: 4 branch(es), 1 exit form(s), from a caller's seat` beside the arithmetically-correct `bootstrap_project: 3 branch(es)`, which is the number this project carried for nine review passes. Measured on a namespace tree built for it: before, the two spellings of one target gave opposite answers and the wrong one was clean; after, they give one. Red verified by stashing only the package and re-running the four new scenarios — 4 failed, the text being `assert ['run'] == []` and its mirror. `impact_of` over `bootstrap.py` went 1.48 s → 1.65 s, mean of three runs each, the cost of one parse per caller file, recorded in the SPEC. 18 tests added (14 unit, 4 scenarios). Green on the tree, macOS: 8133 passed (baseline 8115), `ruff` and `mypy --strict` clean, `beadloom ci` rc 0. |
| `beadloom-0mdo.16` | Done | MAJOR 3: the axis that had no fixture able to disagree with it. `tests/test_impact_over_every_source_layout.py`, 53 cases over five BUILT layouts — a regular package, a PEP 420 namespace package, a lone file outside any package, a plain directory that is not a package, and two packages under `src/` where `source_root_of` falls back to the project root. The last two are the layouts `.15`'s close named as unbuilt. Every expectation travels on a `Layout` dataclass with the tree that produces it, so a sixth layout cannot be added without stating what it must answer. Each layout is asked the same three questions: the swept root; whether a caller outside the target's own directory is FOUND or DECLARED; and whether the same function spelled as a path, as a symbol and as the directory holding it gives one answer — the shape of the defect rather than one of its instances, since a case checking one spelling would have been green. Where two spellings legitimately sweep different roots the narrower one must carry `sweep-narrower-than-the-project`, and that is asserted rather than assumed. RED verified against the pre-`9db8e5a` package in a detached worktree on `PYTHONPATH` — never by reverting this shared working tree — 31 failed, 22 passed. The 22 are declared with their reason: 16 are controls on the four layouts the OLD walk already got right, 3 are a negative assertion over a kind that did not exist pre-fix, and 3 are new arms whose pre-fix failure is a `TypeError` on a signature `.15` changed, which is not evidence about the old behaviour. Two hand-written mutants killed 8 and 5 cases, so neither the controls nor the negative assertion is vacuous on the shipped tree. Coverage of `application/impact` 86.97% (was 86.35%), `answer.py` 99% statements with 2 partial branches (was 97% with 4). Green on the tree, macOS: 8186 passed — baseline 8133 plus 53 added, exactly, so no scenario was deleted; `ruff` and `mypy --strict` clean, `beadloom ci` rc 0. |
| `beadloom-0mdo.17` | Pending | blocked by `.16` — re-review |
| `beadloom-0mdo.18` | Done | `review-brief`'s `WITHHELD — N author comment(s)` block is replaced by a REACHABILITY statement over four channels: bead comments, the documents of the work item the branch names, the commit bodies of `git log <base>..HEAD`, and the launch prompt — which is NAMED as a channel nothing in this process can inspect rather than omitted, the rule `impact` follows for a `Population` it could not resolve. **The channels are derived, not listed:** `prompts_naming_documents` composes every role in `ROLE_NAMES` and every shipped command fragment for this project's `flow.yml`, INCLUDING its project layer, and matches a document by shape — so `.beadloom/flow/roles/review.md` naming `DECISIONS.md` moves the report by that act, which is asserted in both directions. The work item comes from `work_item_of_branch` and the range from the review's own base; nothing in the module spells a document name. A commit body is COUNTED, never quoted. It raises detectability and closes nothing: the review protocol sends the reviewer to the diff and the bodies come with it. Exit codes unmoved on purpose — the launch prompt is never inspectable, so a finding per uninspected channel would put every brief on exit 1. 7 scenarios (red at collection before the code existed) + 17 unit cases + 4 CLI cases; every case demonstrated capable of failing by eight mutants — the document population reduced to a hand-written list → 2 red, the command fragments dropped → 2, the project layer skipped → 2, git's silence rendered as an empty range → 3, a branch naming no work item reported as an empty folder → 4, the uninspectable channel omitted → 3, `NOT INSPECTED` rendered as `0 item(s)` → 3, the commit body travelling with the count → 1. API change: the JSON `withheld` object is REPLACED by `reachability`, not joined by it. Green in a clean room over 11 files, macOS: Gate rc 0, 8195 passed / 29 skipped / 1 xfailed with the one pre-existing environmental failure reproduced at HEAD alone in a second pristine room. `mypy` over 3.10, 3.11, 3.12 and 3.13, Success on each (BDL-UX #227). |
| `beadloom-0mdo.22` | Done | `mutmut` configured over `src/beadloom/graph/rules/` as this repository's own dev dependency (its own `mutation` extra — absent from `dev` and from `all`, so no other leg installs it), and `beadloom mutation` produces the score from whatever counters a run wrote. **The score, produced by the command:** 96.2% over 3 989 mutants — 3 836 killed, 1 timeout, 152 survived, 0 with no covering test. **Q3 answered by the number rather than by preference: NIGHTLY.** 54 min 55 s wall clock at 1.42 mutations/second with six workers, room named: Darwin arm64, CPython 3.13.7, 10 cores — two to three times the ~16-28 runner-minute budget that withdrew `tests-windows`, on hardware faster than `ubuntu-latest`, so no CI figure can move the answer; and against ~4-minute ubuntu legs it would be the pipeline's whole critical path. `mutation_scope.py` became a package split by responsibility (`scope.py` — could this target run a mutant; `score.py` — what did a run over it produce), public import path unchanged. Three rules decide what the number means: a missing counter is reported rather than read as zero, a timeout counts as killed while a mutant no test covers does not, and a run that does not say what it covered is refused. `--only` keeps a first slice answerable for what it ran and NAMES the declared targets it did not judge, so BDL-061's three-target declaration is neither narrowed nor permanently red. **The test pool is derived, not chosen** — 73 files by coverage contexts plus one the import check found — and the whole suite was tried in the `mutants/` room first and does not fit it: 14 failures and 7 errors, structurally, because the meta-tests lint a package that is mutated by construction and walk a git history the copy does not have. That room found a real defect in this bead's own tests (JSON parsed out of Click's merged stream). 51 tests added; every one verified red first, the scenarios by blinding the detector, the two load-bearing CI-job assertions by making the change they forbid. Green on the tree, macOS: 8266 passed, `ruff` clean, `mypy --strict` Success on 3.10, 3.11, 3.12 and 3.13, `beadloom ci` rc 0. |
| `beadloom-0mdo.19` | Done | the tests under `.18`'s reachability report: the three channels asserted as DERIVED rather than listed, and the direction of the statement — a channel inspected and found empty must not read the same as a channel that could not be inspected. Landed as `8b3974a`; it carries one xfail recording FINDING BDL-068.19-1, that `prompts_naming_documents` reads `flow.yml` outside the `FlowConfigError` guard, so a malformed config costs the whole brief rather than one channel. |
| `beadloom-0mdo.23` | Done | A verdict names the room it was taken in, and the room list is DERIVED — `application/rooms.py` reads the supported interpreters from the `Programming Language :: Python :: X.Y` classifiers and the legs from every job of every workflow with its matrix expanded, so a leg added later is covered by the same act that added it. `requires-python` stays a FLOOR (counting `>=3.10` upward needs a hardcoded newest Python) and the packaging metadata is read without a TOML parser, so the answer does not differ between 3.10 and 3.13. **One rule decides coverage:** a run enters a leg only when every dimension is comparable and equal, so a self-hosted label and the `locale` legs both resolve to NOT ENTERED — a comparison that cannot be made must never manufacture coverage. `beadloom rooms` reports the census and `--dimension python` prints the axis the python checklist now loops over instead of spelling `3.10 3.11 3.12 3.13`; `beadloom ci` prints the room in all three formats and the MCP `complete_bead` verdict carries it. **Naming the room does not make a verdict stronger, and three tests fail if it ever does** — no step, no finding, no change of exit code. The clean-room limit moved from the coordinator, read by the loop that orchestrates, into `_rooms`, a second shared role layer read by the roles that measure. Measured here: 21 declared rooms, 0 entered locally, 1 unresolved job. 47 tests + 5 scenarios, every one verified red first — the scenarios by blinding the derivation and then the census, which reddened 4 and 2 of the 5 and caught one scenario of mine that could not fail. |
| `beadloom-0mdo.28` | Done | S2's review found `review-brief` CRASHING on a malformed `flow.yml`: the config the prompts compose from was resolved outside the `FlowConfigError` guard the composition already had, so a config that will not parse raised out of `reachability_of` and the command produced no brief at all — the instrument the whole review protocol runs on, removed by one broken file. `prompts_naming_documents` now answers `None` for a project file that will not parse, which is NOT `{}`: composing nothing and composing every prompt to find none names a document are two different facts, and the documents channel reports `NOT INSPECTED — the project's flow.yml will not parse, so no prompt could be composed`. The strict xfail `beadloom-0mdo.19` filed as FINDING BDL-068.19-1 was dropped in the same change, which is what makes the fix checkable: it flips the moment the crash stops. Second half, Major 1(a): the bead-comment channel now NAMES the bead its count was taken over and says the beads that made the change are neither read nor counted — on the S2 review's own run `0 item(s)` stood beside 31,544 characters on `.18` and `.19`, so the number was right and the sentence a reader took from it was false. Widening the report to the sibling beads and the tracker export is BDL-UX #229 and stays there. Minor taken by halves: the `--release` refusal speaks the brief's vocabulary and names the bead, the RELEASED line is left alone because it prints the comments themselves, and the release half's `withheld_count` JSON key is unchanged because RFC.md:165 declares the break for the BEFORE half only. 11 new tests (2 scenarios, 8 unit, 1 CLI), each seen red first. Green in a clean room over 12 files: 8410 passed / 29 skipped / 1 xfailed with the one pre-existing environmental failure (`test_bead15_s3b_coverage`'s sync-freshness pairs read `unverified` with no recorded baseline) reproduced at HEAD alone in a second pristine room. On the tree: `beadloom ci` rc 0, 8429 passed, `ruff` clean, `mypy --strict` Success over 255 files targeting 3.10, 3.11, 3.12 and 3.13. Darwin arm64 · CPython 3.13.7 — 0 of the 21 declared rooms. |
| `beadloom-0mdo.29` | Done | S3's review found the slice had answered its own question for the REPOSITORY and not for the ROLE: `beadloom mutation` exists, the nightly job runs it under a floor, and `roles/core/test.md.txt` still read "Record the tool, the target and the surviving count in the bead comment" while the string `beadloom mutation` appeared in no role file. One bullet in the test role core now names the command, and the clause that routed the RESULT to prose was re-pointed at it; the tool-agnostic half is untouched, because Beadloom still ships no runner and still only reads what one wrote. **The wiring is the existing one**, not a second beside it: the statement has a single home in the core, `role-composer` composes it, `generate_adapters` writes it, and the flow manifest fingerprints it — `setup-agentic-flow --force` rewrote exactly one adapter and the vendored `agents/test.md.txt` was re-copied byte-identical, as its drift guard requires. **The check's population is derived, not spelled:** it splits the composed role's mutation section into bullets and asserts that every bullet routing a result to a bead comment or a checkpoint names the command, so it bites on a bullet nobody has written yet; all four tests were seen red first. That `config-check` sees the result as a composed artifact was verified by SABOTAGE rather than asserted — a two-line hand edit to `.claude/agents/test.md` made it report `hand-edited: the body differs from the composition`, and restoring it returned rc 0. Green on the tree, foreground and unpiped: 8433 passed (baseline 8429, so +4 and nothing else moved), 11 skipped, 1 xfailed, 244.66 s. Green in a clean room over 1136 files: 8413 passed with the one pre-existing environmental failure (`test_bead15_s3b_coverage`, which `git archive` leaves without a `.git` to ask). `beadloom ci` rc 0, `ruff` clean, `mypy --strict` Success over 255 files targeting 3.10, 3.11, 3.12 and 3.13. Darwin arm64 · CPython 3.13.7 — 0 of the 21 declared rooms, and a single-writer wave, so a clean tree here had nothing to collide with. |
| `beadloom-0mdo.30` | Done | PR #60's two locale legs, red on two tests this epic wrote. **The CJK work-item folder:** the guard is `_the_filesystem_can_spell(key)` — `name.encode(sys.getfilesystemencoding())`, the codec `os.mkdir` will use — so the case steps aside only where the room cannot hold the name, and the skip says where it still fails: every UTF-8 filesystem, macOS unconditionally and the `tests`/`gate`/`site-build` legs of every PR. That is the INVERSE polarity of `test_ci_locale_dimension.py:298` and says so instead of borrowing its wording; the reason is ASCII because `-ra` prints it on the two legs whose stdout cannot encode the name. **The scenario:** `a run names the declared rooms it did not enter` no longer contrasts one state against another. The two declared legs differ only in the interpreter, so at least one is always not entered — true at 0-of-2 on a developer machine and at 1-of-2 on the 3.10 leg — and a third step judges what `entered` means, the half that had never executed anywhere because the step skipped on Linux. `TestTheScenarioIsJudgedInsideADeclaredLegToo` writes a workflow declaring THIS run's platform and interpreter, so one leg is genuinely entered in whatever room the suite runs in, macOS included. `test_bead14_s4_binding` was NOT weakened; it gained a static sibling that reads the step modules, because its runtime check only catches a skip in the room where the skip fires. 7 tests added, each seen red first: the static scan reddened on exactly `test_verdict_room_steps.py:86`, sabotaging the room guard to `sys.platform != 'linux'` reddened 2, blinding the entered judgement reddened 1. Green on the tree, foreground and unpiped: 8440 passed (baseline 8433, so +7 and nothing else moved), 11 skipped — UNCHANGED, so nothing new steps aside here — 1 xfailed, 249.50 s. `beadloom ci` rc 0, `ruff` clean, `mypy --strict` Success over 255 files targeting 3.10, 3.11, 3.12 and 3.13. Darwin arm64 · CPython 3.13.7 — 0 of the 21 declared rooms. **The measurement not taken:** neither locale leg. CPython forces a UTF-8 filesystem encoding on macOS, so `LC_ALL=C` here does not reproduce the Linux room and the coordinator's 98-passed run said nothing about it; both claims about those legs rest on reasoning stated in the bead. |
| `beadloom-0mdo.10` .. `.14` | Pending | S2–S6, ordered by dependency; their beads are created when the preceding slice's review closes |

## Notes

**Handed up by `.4`, not fixed by it.** Requiring the planning templates' sections reports
**102** documents on this repository's archive: old RFCs with no `## Overview`, old PRDs with
no `## Impact`. Every one is a true departure from the shape its peers keep, every check is
`warn`, and the Gate stays rc 0 on them. Whether the archive is revised or the corpus is scoped
by `doc_quality.paths` is an owner's decision rather than a dev bead's, and it is stated here so
the number is not discovered later as a surprise.

**The two axes checks read 0 documents today**, and the Gate says so rather than reporting them
clean (`NOT CHECKED: axes-without-a-seed, axis-without-a-scope-decision`). No planning document
in this repository carries an `## Axes` section yet. BDL-068's own RFC deliberately does NOT get
one from this bead: an epic is not an `impact` target, its axes span six slices and several
runs, and a guessed table is exactly what `.6` would then measure every commit against.


**Handed up by `.7`, measured and not repaired.** A routing row whose `Flow` cell spells
neither `simplified` nor `full` is dropped by `work_item_routing._routes_in` with no note, and
`Routing.notes` — the field that exists for exactly this — stays empty. Measured on a
three-row table: two routes returned, `notes` empty, `flow_of('spike')` indistinguishable from
a type nobody declared. The consequence reaches a check, because the dropped type's document
kinds leave `simplified_kinds` and every work item of that type leaves
`check_work_item_types`' population, so the report reads as a clean run over a smaller corpus.
It is this epic's own third clause — a derivation that resolved everything and one that
silently omitted what it could not parse must not read the same — failing inside the epic's own
instrument. Not repaired by a test bead for a measured reason: the obvious repair, a note per
unreadable cell, fires on the table's own `|---|---|` alignment row, which `.5` already has a
mutant for, so repairing it means re-measuring `.5`'s sixteen mutants. Pinned as a gap class
with the instruction to DELETE rather than repair it when it goes red.

**The structural decision this epic is run under.** Beads are created per slice, not for the
epic. Writing 24 beads now would mean writing 20 of them before the first slice has taught
anything — which is the plan BDL-067 wrote blind, five times larger. The re-plan rule is
expressed as structure rather than as discipline.

**The decisions taken at planning, so they are not re-litigated per bead.**

- Q1 — the axes are DERIVED by `beadloom impact`; the document records the derivation's output
  and the human's scope decision; the bead's `refs:` is generated from the document. A
  disagreement between the three is a finding. One computation, two renderings, one check.
- Q2 — the commit-scope check compares against the WORK ITEM's axes, not the bead's. A bead may
  narrow freely inside what the human approved; leaving the work item's axes is the re-plan
  trigger.
- Q4 — External `bd` findings are answered by deriving our own call sites, not by a wrapper.
- Q5 — `Explore` is a role file composed by `role-composer`, not a mode. A mode has no protocol
  file, and that is why the one `Explore` run in BDL-067 returned a trace of the defect and
  nothing about axes.
- Q3 stays open with its decision rule stated: the mutation job runs per PR if it fits under
  the budget that withdrew `tests-windows`, nightly otherwise — measured in S3 before the job
  is added.

**The bead that could invalidate the epic's premise, and partly did.** `.3` ran the lifted
derivations against the tree as it stood at BDL-067's first dev bead. Both facts the epic
claims an axes artifact would have surfaced are inside the derivations' reach on that tree —
and only under a seed BDL-067 did not choose until its own fifteenth bead. Seeded from the
function the first dev bead was changing, the same derivations report three branches and no
writers, confidently and cleanly. So the premise holds as a conditional, the condition is seed
derivation, and `.2`'s acceptance was rewritten to make it the load-bearing criterion rather
than an implementation detail. The measurement was not softened into a pass and the derivation
was not repaired to make it come out yes; a repair would have measured the repair.

**A second measurement `.3` did not go looking for.** `PUTS_BYTES_ON_DISK` — the lifted
shape for *this body puts bytes on disk* — does not contain `write_yaml_atomic`, the product's
own single commit point, because that function writes through `os.fdopen(...).write` and
`Path.replace` while the shape spells `write_text`, `write_bytes` and `open`. A shape stated
over three spellings walking past the thing it exists to protect is this epic's own defect
class, found inside this epic's own instrument. Left unrepaired on purpose and handed to `.7`,
which already owns the other half of the same gap.

**Three counts this epic's own planning commit broke.** `409e977` added four planning
documents and a PRD carrying fourteen scenario references, and left three hand-maintained
literals in the suite at their BDL-067 values: TO-BE documents (199), scenario references in
PRD/BRIEF (36) and WORKING documents (57). The branch was Gate-green and suite-red at the same
time for that whole interval, because `beadloom ci` does not run pytest. Corrected in `.1`
with the reason recorded beside each literal; the class is `mr2l.72` and S6 owns it.

**Why the seed rule is stated over two effects and not three.** `serialises-yaml` and
`reads-a-yaml-directory` are declared; `PUTS_BYTES_ON_DISK` is deliberately excluded, and the
exclusion is a check rather than a comment. Beyond `.3`'s finding that it does not contain this
product's own commit point, it is not a sound predicate ALONE, because `open` also READS —
measured at `af26750d` it gives `bootstrap.py` four seeds none of which is the commit point,
and `setup.py` nineteen seeds and 65 co-writers, most of them readers. `.1` handed its
narrowing to `.7` and nothing in `impact` is built on top of it. The synthetic tree in
`tests/test_impact_derives_the_seed_it_answers_from.py` reproduces the finding in miniature —
its sink writes through `os.fdopen(...).write` and `Path.replace`, exactly as
`write_yaml_atomic` does — so that case runs on every leg rather than only where the history is
in the checkout.

**The archive gains 12 warnings, and they are true.** `routed-without-axes` reports every one
of this repository's 12 simplified-flow work items, because none of them carries an `## Axes`
section — they were all written before the section existed. The check is `warn` and the Gate is
rc 0 on them. The number is small because the requirement is scoped to the simplified route
rather than to all 60 typed work items: the full route writes a PRD and an RFC and each passes
an approval gate, so a mis-route there meets a person, while the simplified route passes one
gate on work already scoped. Whether the twelve briefs are revised or the corpus is narrowed
with `doc_quality.paths` is the owner's call and not a dev bead's.

**A check that reads a population it cannot fire on, stated rather than hidden.**
`route-not-supported-by-the-axes` enters 12 work items and finds 0, and it cannot find anything
until one of them carries axes. It is verified red on fixtures — two kept nodes reported, one
kept node silent, a node ruled out of scope not counted, one node named by two rows counted
once — and the population is in the report so the Gate can say so.

**Two guards were deleted rather than defended.** A mutant run showed that the localisation
guard in `roles_in` and the empty-routing early return in `check_work_item_types` could not be
made to fail: the front-matter equality rule already excludes a localisation, and `_collect`
already keeps no folder that nothing routes. Both were removed, with the reason recorded where
they stood. The alternative — keeping a guard nobody can demonstrate — is the shape of a check
that cannot fail, which this epic's CONTEXT forbids.

**Still open, and still nobody's bead.** BDL-068's RFC carries Q1–Q5 as `Pending` while CONTEXT
records four of them as decided, and the Gate warns `pending-in-approved` on all five. `.3`
raised it and `.2` did not repair it either: two documents disagreeing about whether a decision
was taken is this epic's own class, inside this epic, and which document wins is the
coordinator's call rather than a dev bead's.

**Branch.** `features/BDL-068`. PR #58 landed on `main` as `a4738b7`, so the three lifted
derivations are no longer stacked on an open branch.

**The reachability report's first run was on itself, and it found its own limit.**
`beadloom review-brief beadloom-0mdo.18` reads `the work item's documents: NOT INSPECTED — the branch 'features/BDL-068-S2S3' names no work item among the project's planning documents`. The convention is `work_item_of_branch`'s: a `/`-separated segment must equal a work item's folder name, and `BDL-068-S2S3` is not `BDL-068`. The channel states the reason rather than reporting an empty folder, which is the behaviour wanted, and the convention was NOT patched inside `review_brief` — a second reader of the branch-to-work-item rule is the two-sources-of-truth defect this epic exists to remove. Recorded in the SPEC's Honest limits with the measurement, for whoever decides whether the rule should match a prefix.

**A Gate that ran nothing and returned 0.** The clean-room measurement was first taken with `python -m beadloom.services.cli ci`, which exited 0 and printed nothing, because that module has no `__main__` block. Re-run through `main()` it printed 40 lines and rc 0. The first reading was a green that would have been reported; it is recorded because this epic is about exactly that class.

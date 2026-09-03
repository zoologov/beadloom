# ACTIVE: BDL-068 — The flow's rules are advice; make them instruments

> **Last updated:** 2026-09-03
> **Phase:** Development

---

## Current Bead

**Bead:** `beadloom-0mdo.17` — the S1 re-review, now that the critical is closed on the tree
that shows it and the suite has a fixture per source layout that can disagree with the sweep.

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
- [ ] S2 — the review's independence
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

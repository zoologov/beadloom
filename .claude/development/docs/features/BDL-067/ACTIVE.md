# ACTIVE: BDL-067 — A virgin `beadloom init` leaves the Gate red

> **Last updated:** 2026-09-01
> **Phase:** Development

---

## Current Bead

**Bead:** `beadloom-e8s4.7` — the wizard branch, and a test that distinguishes a binding from a branch
**Goal:** the branch count `THE_BRANCHES` claims is read out of `init`'s own source rather than
maintained by hand, so a FOURTH branch that bootstraps without a verdict fails a test on the day it
is written instead of shipping unguarded as the third one did.
**Done when:** the enumeration is demonstrated to fail on a command that has such a branch, the
three assertions `.6` declared vacuous either fail against the pre-`.6` source or are declared with
a reason, and `beadloom ci` is rc 0.

## Progress

- [x] BRIEF.md written and approved (2026-08-31)
- [x] Beads created under `beadloom-e8s4`, dependencies wired
- [x] Wave shape decided by `beadloom waves` (exit 0): `.1` and `.2` serialised on `shared_node: agent-prime`
- [x] Branch `features/BDL-067` cut from `main`
- [x] Wave 1 — `.1` dev (closed; `lint --strict` rc 1 -> rc 0 and `ci` rc 1 -> rc 0 on a virgin adopter project)
- [x] Wave 2 — `.2` dev (closed 2026-08-31, commit `e52aa06`)
- [x] Wave 3 — `.3` test (closed 2026-08-31, commits `e870b0b`, `fee64db`)
- [x] Wave 4 — `.4` review (closed 2026-08-31, verdict ISSUES: 0 critical, 2 major)
- [x] Wave 4b — `.6` dev (closed; wizard rc 0 → rc 1 on the sabotaged fixture, `beadloom ci` rc 0)
- [ ] Wave 4b — `.7` test (closed) / `.8` re-review (fix cycle)
- [x] Wave 4c — `.9` dev (`9eac01f`) / `.10` test (`28f1cd2`) / `.11` review (launched)
- [x] Wave 4d — `.12` dev (`5bdd1b0`) / `.13` review (launched)
- [ ] Wave 5 — `.5` tech-writer (re-pointed a third time: now depends on `.13`)
- [ ] Gate green, PR opened

## Results

| Bead | Status | Details |
|------|--------|---------|
| `beadloom-e8s4.1` | Done | post-condition `_missing_domain_parent_edges` in `bootstrap.py`; 4 scenarios + 11 unit tests; green in a clean room over 6 files |
| `beadloom-e8s4.2` | ✓ done | `init` now takes a verdict on the graph it wrote, in both the `--yes` and interactive `--bootstrap` branches, using the Gate's own `has_errors` semantics. 15 tests. The divergence is CONSTRUCTED — `part_of` edges are stripped back out of `services.yml` after the real bootstrap wrote the real rules — so the case does not depend on `.1` still leaving a naturally-broken graph. API change: `gate._step_lint` → public `lint_step`. Commit `e52aa06`. |
| `beadloom-e8s4.3` | ✓ done | the three suite defects closed. All five assertions verified RED against the pre-fix source (`git archive af26750 src` imported via `PYTHONPATH`, the override confirmed by `gate.lint_step` being absent there): pre-fix 5 failed / 20 passed, post-fix 25 passed, no pre-existing test turned red. Coverage 97% / 93% / 91% on the changed modules. Commits `e870b0b`, `fee64db`. |
| `beadloom-e8s4.4` | ✓ done | REVIEW ISSUES: 0 critical, 2 major. Verified green independently: the #192 reproduction on a scratch adopter (`2 nodes, 1 edges`, `lint --strict` rc 0, `ci` rc 0) against the same fixture on pre-fix source (`2 nodes, 0 edges`, no `edges:` key); the deliverable is an invariant (`_missing_domain_parent_edges` runs over the whole node list after every edge producer); the edge uses `root_node["ref_id"]` as written; `rules_gen.py` diff is empty. |
| `beadloom-e8s4.5` | Pending | re-pointed: now blocked by `.8`. Doc surface named by the review, not to be guessed. |
| `beadloom-e8s4.6` | ✓ done | the wizard now takes the verdict (guarded on `mode in (bootstrap, both)` and skipped on the `edit` review answer, where the graph has just been handed to the user). The covering module is parametrised over the three BRANCHES instead of the two bindings: 14 cases → 33. Minor 4 closed — an unloadable `rules.yml` now prints the loader's complaint instead of the gate step's own name, and does not blame the bootstrap for a file the bootstrap does not rewrite. 21 new tests (19 unit + 2 scenarios); 13 of them verified RED against `git archive HEAD src` on PYTHONPATH. Minor 3 wording corrected in all three prose copies of the post-condition sentence (BRIEF, onboarding README, agent-prime SPEC); the fourth copy was this file's goal line and is replaced above. API change: `gate.RULES_CONFIG_ERROR`. |
| `beadloom-e8s4.7` | ✓ done | the branch count is now READ from `init`'s source, not written down: `tests/test_init_branches_that_reach_the_bootstrap.py` derives the callables that reach `bootstrap_project`, finds every call to one of them in the command body, and asserts each is followed by a reachable verdict. Demonstrated capable of failing on three mutant trees (a fourth branch with no verdict — 2 red; a fourth branch WITH one — 1 red, the coverage assertion; a renamed guard — 2 red), and red against the pre-`.6` source. The three cases `.6` declared vacuous at `[wizard]` now carry an anti-vacuity guard and are red there too (pre-`.6`: 13 red → 16 red). 12 new tests (11 unit + 1 scenario, the `edit` carve-out). 7367 → 7379 passed, `beadloom ci` rc 0. |
| `beadloom-e8s4.8` | ✓ done | REVIEW ISSUES: 0 critical, 1 major. Confirmed closed by measurement: the wizard verdict, the `why` in the `LintError` branch, and both wording findings. Verified the enumeration test against the REAL `init` mutated three ways. |
| `beadloom-e8s4.9` | ✓ done | the failure message distinguishes a rule the bootstrap authored from one already in `rules.yml`; the report request is dropped in the second case; the docstring premise corrected. The premise sweep found the SAME false statement in three documents (`cli-commands/DOC.md`, `services/mcp.md`, `onboarding/README.md`) and nowhere else in `src/` or `tests/`. 20 tests. Commit `9eac01f`. |
| `beadloom-e8s4.10` | ✓ done | audit rather than quota. `.9`'s negative assertions already existed and their red was re-derived independently against `9eac01f^` (9 failed / 54 passed). **`.9`'s claim that all 20 were red is overstated — 11 are guards that cannot fail.** Added 3 tests: one kills a mutant the whole suite survived; two make `.9`'s comment-only exclusion executable and are declared guards. Commit `28f1cd2`. |
| `beadloom-e8s4.11` | ✓ done | REVIEW ISSUES: 0 critical, 1 major — the withdrawal line on the unloadable-rules branch. Confirmed `.10`'s routed finding by running the wizard on five scratch projects. |
| `beadloom-e8s4.12` | ✓ done | the shared withdrawal now reads "The scaffold above was written, but the check that follows it did not pass." — no rule claim, no colon. One assertion pair + one acceptance scenario, both red before the fix. **The sweep found a FOURTH instance and reported it instead of widening the commit.** Commit `5bdd1b0`. |
| `beadloom-e8s4.13` | In Progress | fourth-pass review launched, with no path named |

## Notes

**Decisions**

| Date | Decision | Reason |
|------|----------|--------|
| 2026-08-31 | Fix (a): the bootstrap emits the edges | Option (b) — `generate_rules` drops `domain-needs-parent` when no `part_of` exists — ships every adopter one structural rule weaker than this project runs, with nothing that later restores it. |
| 2026-08-31 | Fix stated as an invariant over `bootstrap_project`, not a patch to `bootstrap.py:133-145` | Patching the one reported branch leaves the next branch free to forget the edge again. Owner confirmed the wider scope. |
| 2026-08-31 | `beadloom-e8s4` raised P1 → P0 | The ROADMAP ranked it P0 and the tracker did not; the ROADMAP is right — it is the adopter-facing blocker. |

**Open item raised by wave 1 — belongs to the epic, not to `.1`**

Two suite baselines count this repository's own planning documents and are one BDL-067
document behind: `tests/test_reference_leg_syntax.py` expects 33 scenario references and the
tree now holds 36 (the BRIEF's three acceptance criteria), and
`tests/test_bead77_kind_and_root_disagree.py` expects 198 TO-BE documents and the tree holds
199. Both pass in a clean room of HEAD plus `.1`'s six files, so neither is caused by the fix;
both fail on the working tree because `BRIEF.md` is there. The natural owner is `.3`.

**Open observation — candidate for `UX-Issues.md`**

`beadloom waves beadloom-e8s4.1 beadloom-e8s4.2` serialises the pair and names the reason
`shared_node: agent-prime` — a node **neither bead declared** (`.1` declares `onboarding`,
`.2` declares `onboarding, cli`). The verdict is conservative and therefore safe, but the output
does not let an operator tell a transitive expansion from a parse error. Confirm during the wave
before logging.

**Wave 1 aftermath — `mr2l.72` measured a third time**

The dev subagent on `.1` reported the tree red on two baseline tests it did not own and
correctly refused to edit them. Verified in the main loop: BDL-067's own `BRIEF.md` and
`ACTIVE.md` moved the TO-BE population 198 → 199 and the working-document count 56 → 57
(`tests/test_bead77_kind_and_root_disagree.py`), and the BRIEF's three acceptance-criteria
scenario references moved the PRD/BRIEF reference count 33 → 36
(`tests/test_reference_leg_syntax.py`). Bumped by the coordinator in `e83bc65` and recorded on
`beadloom-mr2l.72`. **Cost per feature is now three hand edits, not one** — the literals the
ROADMAP describes as moving 190 → 194 → 198 are three literals, not one.

The pre-commit hook also warned `mypy type errors in this commit` on a tests-only commit;
`uv run mypy src/` is clean over 225 files and `ruff check src/ tests/` passes. That is
`mr2l.82` — the commit-scoped hook type-checks a surface the project never declared typed.

**Wave 2 verified by the coordinator, not taken on report**

The subagent reported two measurements that read as a contradiction — one clean-room failure and
`beadloom ci` rc 0 on the tree — so both were re-measured in the main loop:

- Claim: `beadloom ci` rc 0 on the tree. Re-measured without a pipe: rc 0, no error-level lines, warnings only.
- Claim: `test_all_new_node_pairs_are_fresh` fails only in the clean room. Re-measured: it passes on the tree; the clean room has no index for it to compare against.
- Claim: 7341 passing. Re-measured: `7341 passed, 11 skipped, 1 xfailed`, none failed.

The first Gate run in the main loop was itself misread: `beadloom ci | tail` reports `tail`'s exit
code, not the Gate's. Re-run without the pipe before believing it — the coordinator playbook warns
about exactly this and it still happened once here.

**Wave 3 verified by the coordinator**

Re-measured in the main loop, without a pipe: `beadloom ci` rc 0; full suite
`7346 passed, 11 skipped, 1 xfailed`, none failed — the count the subagent reported.

**A false positive the Gate raised against this very document.** The coordinator's wave-2
verification was written as a two-column table, and `docs quality` read it as a decision table,
reporting `decision-reason: the decision carries no reason` against a row that records a
measurement rather than a decision. Rewritten as a list, and the Gate went quiet. Worth noting
before it is filed: a table of claims and their measurements is a shape this repository will
write again, and nothing distinguishes it from a decision table but the words in the header.

**Wave 4 — the review found what four green waves did not**

`_verdict_on_the_generated_graph` has two call sites, `--yes` and `--bootstrap`. The **default
interactive wizard** — plain `beadloom init`, the branch a human adopter meets first — calls
`bootstrap_project` through `interactive_init`, prints `Initialization complete!` and returns with
no verdict at all. The reviewer reproduced #192's exact shape there: wizard rc 0, `lint --strict`
rc 1, `ci` rc 1.

What hid it is worth more than the patch. The test module's own comment reads *"The two ways
`init` reaches the bootstrap"* — true of monkeypatch **bindings**, since the wizard shares the
`--yes` binding, and false of **branches**. Everyone downstream of that sentence, including this
coordinator, counted two and stopped.

**Independence was defeated, and only the reviewer could see it.** `review-brief` withheld 0
comments and was right — the authors' accounts were not in bead comments, they were in this file's
Results table, and the launch prompt named this file as required reading. The playbook prescribes
both halves. Logged as BDL-UX #212; practice changed by owner decision — review launch prompts no
longer name `ACTIVE.md`.

**Routing.** Major 1 + Minor 4 → `.6`/`.7`/`.8`. Major 2 + Minor 5 → named into `.5`'s notes.
Minor 3 (two nodes share one `ref_id` on `src/<project>/`, the loader keeps one, the rule goes
inert and `ci` stays green) → filed on its own as `beadloom-7c6k` / BDL-UX #214, by owner decision.

**Fix cycle — what closed and how it was measured**

Coordinator's own measurements on the tree, without a pipe: after `.6`, `7367 passed, 0 failed`,
Gate rc 0; after `.7`, `7379 passed, 0 failed`, Gate rc 0. Both match what the subagents reported.

`.7`'s deliverable is the part worth keeping. It does not add the third case — it derives the
bootstrap-reaching callables from the onboarding source, locates every call to them in `init`'s
body together with its guard path, and requires a reachable verdict after each. A fourth branch
added later fails this test rather than shipping. It was verified against three deliberately
mutated trees rather than only against the pre-fix one, which is the difference between a test
that passes and a test that would have caught this.

**A numbering collision, caught by a subagent and missed by the coordinator.** The new defect was
first filed as BDL-UX #211. That number belongs to the closed 1.x-description issue of 2026-08-27
and is cited four times in shipped documents. The coordinator had checked for a collision with
`grep -nE '^21[0-9]\. \['`, which cannot match a closed entry — those are written `211. ~~[` —
so the check returned "free" and was believed. Renumbered to #214. The mechanism, not the number,
is the finding: a duplicate-detection pattern that duplicates need not match. `mr2l.91` exists
because this log already carries two issues numbered 187.

**Re-review — the fix cycle closed its findings and produced one more**

Everything routed to `.6`/`.7` is closed, and the reviewer confirmed it by running the commands
rather than by reading the beads. The wizard now exits 1 over a graph that fails its own rules and
stays 0 over one that does not, so the check is a verdict rather than a permanent red.

**The new Major is the same species as the last one.** When the graph fails an evaluated rule,
`init` says *"This is a defect in Beadloom's bootstrap rather than in your project — please report
it"*. That holds only when the bootstrap authored `rules.yml`, and `bootstrap_project` writes that
file **only if it is absent**. On a re-init, or on a project whose rules came from an earlier
Beadloom or a hand edit, the failing rule is the adopter's own and Beadloom asks to be blamed for
it. The docstring justifying the non-zero rc carries the same false premise and reads as verified.

What makes it worth recording rather than just fixing: `.6` already knew this. It wrote the fact
down — *"`bootstrap_project` leaves an existing rules file alone, so the file that did not load is
usually the adopter's own edit"* — in the message immediately next door, and did not carry it
across to the message it invalidates. Two neighbouring sentences, one correct.

Routed to `.9`/`.10`/`.11`; Minor 3 (prose) added to `.5`'s named surface. `.5` re-pointed to `.11`.

**Second fix cycle — the audit was worth more than the tests it added**

Coordinator's measurements on the tree, without a pipe: after `.9`, `7399 passed, 0 failed`,
Gate rc 0; after `.10`, `7402 passed, 0 failed`, Gate rc 0. Both match the subagents' reports.

`.10` was re-scoped by the coordinator before launch, because `.9` had already written the
differential tests this bead was created to demand. Asking for them again would have produced
tests written to justify a bead — the exact failure this epic exists to remove. It was sent to
audit instead, and the audit is what paid:

- `.9`'s summary said all 20 of its assertions were red before the fix. **Eleven are guards that
  cannot fail.** The nine that can were re-derived independently against `9eac01f^`. The claim was
  not false in a way that changes the fix; it was imprecise in exactly the direction that this
  project keeps finding expensive.
- One mutant the entire suite survived is now killed — the withdrawal line on the
  unloadable-`rules.yml` path.
- Two of the three tests it added are **declared guards**, said so in the open rather than counted
  as coverage.
- It measured *"green in a clean room over 1 file — 75 passed over the three affected modules,
  scoped, not the full suite"*, which is the narrowest and most accurate claim any subagent has
  made in this epic. The full-suite number came from the coordinator.

It also routed a finding rather than fixing it: on the wizard + unloadable-rules path, the
withdrawal line says the graph "does not pass" rules that the next two lines say were never
evaluated. Passed to `.11` as a finding to judge, not as a verdict to adopt.

**Third fix cycle — and the finding that the sweep is the deliverable**

Coordinator's measurements on the tree, without a pipe: `7403 passed, 0 failed`, Gate rc 0.

`.12` was asked to fix the wording and then sweep the other user-facing strings this epic touched
against the branches that can actually reach them. It found a **fourth** instance of the class and
**reported it rather than fixing it**, which is what the bead asked for:
`application/gate.py:242-248` stamps `RULES_CONFIG_ERROR` on all three `LintError` raise sites in
`graph/linter.py`, two of which are index problems. Measured on a scratch adopter with a valid
`rules.yml` and no index: `beadloom ci --no-reindex` prints `lint FAIL: rules configuration error`
while the same run carries `index not found at ...`. The same prose sits in two documents, so the
wrong summary is *documented as the behaviour* — which is how it survived review.

Filed as `beadloom-uz8x` / BDL-UX #215, separately, on the precedent the owner set for #214.

**The pattern is the finding.** Three reviews found three instances of one class, and each was
found only after the previous had been fixed — a sweep by a bead that was told to sweep found the
fourth in one pass. That says the individual fix was never the deliverable. Recorded here rather
than left as an impression.

**The fourth review's prompt names no path.** The third reviewer declared that my prompt had been
convergent — it named the one path holding the only finding, and it could not claim it would have
reached that path unaided from a 25-file diff. So this one states the class and nothing about
where. The cost of the previous choice is on `beadloom-e8s4.11`.

**Fifth fix cycle — `.14`: the second writer, and a verdict judging a stale index**

Baseline measured on the tree before starting, without a pipe: `7403 passed, 0 failed`,
`beadloom ci` rc 0.

The reviewer's reproduction was re-run end to end on a scratch adopter (`orders-web`: flat
`src/index.ts`, `docs/payments.md`, `docs/billing.md`), first to confirm it, then to close it:

| command | before | after |
|---|---|---|
| `beadloom init --yes --mode both` | rc 0 | rc 0 |
| `beadloom lint --strict --no-reindex` (what `init` judged) | rc 0 | rc 0 |
| `beadloom lint --strict` (what the adopter sees) | **rc 1**, `domain-needs-parent` ×3 | rc 0 |
| `beadloom ci` | **lint FAIL: 3 error(s)** | rc 0 |

And the second reproduction, `beadloom init --import docs/` on an already-initialised project:
rc 0 then `lint --strict` **rc 1** before, rc 0 then rc 0 after.

Both causes are closed at the level the epic states them at. `import_docs` now holds the same
post-condition `bootstrap_project` was given in `.1` — every node it writes carries a `part_of`
edge to the graph's root, read off the root node as written — and `non_interactive_init`
re-indexes after **every** block that writes a graph file rather than inside the bootstrap block,
so the verdict can no longer judge an index older than the last file the command wrote.

**The sweep the bead asked for, reported rather than acted on.** Every writer into
`.beadloom/_graph/` was enumerated. Exactly two create nodes: `bootstrap_project` (has the
invariant since `.1`) and `import_docs` (has it now). The other four cannot produce an unparented
node, because none of them creates one: `generate_rules` writes `rules.yml` and no nodes;
`update_node_in_yaml` writes only `summary` and `source` on a node that already exists and cannot
change its `kind`; `_patch_docs_field` adds `docs:`; the `link` command adds `links:`. So the
class has no third instance today — and nothing in the suite would notice a third writer on the
day it is added, which is the gap `.15` exists to close.

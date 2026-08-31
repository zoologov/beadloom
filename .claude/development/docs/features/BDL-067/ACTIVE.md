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
- [ ] Wave 5 — `.5` tech-writer (re-pointed to depend on `.8`)
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
| `beadloom-e8s4.8` | Pending | blocked by `.7` |

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

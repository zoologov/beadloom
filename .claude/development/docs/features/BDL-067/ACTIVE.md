# ACTIVE: BDL-067 — A virgin `beadloom init` leaves the Gate red

> **Last updated:** 2026-08-31
> **Phase:** Development

---

## Current Bead

**Bead:** `beadloom-e8s4.1` — bootstrap post-condition: no domain node is written without a `part_of` edge
**Goal:** every node `bootstrap_project` writes with `kind: domain` carries at least one outgoing
`part_of` edge — to its classified parent where one exists, to the root service node otherwise.
**Done when:** `bootstrap_project` over `typescript_project` yields a graph with no `lint --strict`
errors, and the invariant holds for every preset the module can select.

## Progress

- [x] BRIEF.md written and approved (2026-08-31)
- [x] Beads created under `beadloom-e8s4`, dependencies wired
- [x] Wave shape decided by `beadloom waves` (exit 0): `.1` and `.2` serialised on `shared_node: agent-prime`
- [x] Branch `features/BDL-067` cut from `main`
- [x] Wave 1 — `.1` dev (closed; `lint --strict` rc 1 -> rc 0 and `ci` rc 1 -> rc 0 on a virgin adopter project)
- [x] Wave 2 — `.2` dev (closed 2026-08-31, commit `e52aa06`)
- [x] Wave 3 — `.3` test (subagent launched)
- [ ] Wave 4 — `.4` review
- [ ] Wave 5 — `.5` tech-writer
- [ ] Gate green, PR opened

## Results

| Bead | Status | Details |
|------|--------|---------|
| `beadloom-e8s4.1` | Done | post-condition `_missing_domain_parent_edges` in `bootstrap.py`; 4 scenarios + 11 unit tests; green in a clean room over 6 files |
| `beadloom-e8s4.2` | ✓ done | `init` now takes a verdict on the graph it wrote, in both the `--yes` and interactive `--bootstrap` branches, using the Gate's own `has_errors` semantics. 15 tests. The divergence is CONSTRUCTED — `part_of` edges are stripped back out of `services.yml` after the real bootstrap wrote the real rules — so the case does not depend on `.1` still leaving a naturally-broken graph. API change: `gate._step_lint` → public `lint_step`. Commit `e52aa06`. |
| `beadloom-e8s4.3` | In Progress | wave 3, test subagent launched |
| `beadloom-e8s4.4` | Pending | blocked by .3 |
| `beadloom-e8s4.5` | Pending | blocked by .4 |

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

| Claim | Coordinator's measurement |
|---|---|
| `beadloom ci` rc 0 on the tree | confirmed, rc 0, zero `::error` lines (warnings only) |
| `test_all_new_node_pairs_are_fresh` fails only in the clean room | confirmed, passes on the tree — the clean room has no index for it to compare against |
| 7341 passing | confirmed, `7341 passed, 11 skipped, 1 xfailed`, 0 failed |

The first Gate run in the main loop was itself misread: `beadloom ci | tail` reports `tail`'s exit
code, not the Gate's. Re-run without the pipe before believing it — the coordinator playbook warns
about exactly this and it still happened once here.

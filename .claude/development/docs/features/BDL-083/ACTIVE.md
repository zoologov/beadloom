# ACTIVE: BDL-083 — Debt to zero

> **Last updated:** 2026-10-18
> **Phase:** Development — S1 the gates that lie

---

## Current Bead

**Bead:** wave 4 of 6 — S1e `beadloom-ba9w.13` (the Gate's per-step exception boundary and `ERROR` status, D1; #318) and S1b `beadloom-q8x6` (liveness for `forbid_import` and `test_import_boundary`, D2; #328), concurrent; the coordinator runs the combined tree after both land
**Done when:** each entry's own `Command` red first then green, two-level verification per bead, committed by path under the landing lock, the combined tree green once

## Progress

- [x] Step 1: `/task-init` — axes derived (eight targets, 406 rows ruled in the RFC), PRD, RFC, CONTEXT and PLAN approved by the owner on 2026-10-18
- [x] Step 2: S1 beads created as one plan; `beadloom-ba9w.13` and `beadloom-jwfc` wired in as S1e and S1e2
- [ ] Step 3: S1 — the fixture landed (`14d89ecb`, 2026-10-18); the seven dev beads in the six waves `beadloom waves` derived: S1f → S1a → S1c → S1e + S1b → S1d → S1e2
- [ ] Step 4: S1 test, review, tech-writer, PR, merge on green
- [ ] Step 5: S2 beads created; S2 — the monorepo on GitLab
- [ ] Step 6: S3 beads created; S3 — the re-measurement; the S4–S7 sections put to the owner
- [ ] Step 7: S4–S7, one PR each
- [ ] Step 8: close-out — documents `Done`, ROADMAP re-ranked, the version MAJOR

## Results

| Bead | Role | Status | Note |
|---|---|---|---|
| `beadloom-483w` | S1g | done | `14d89ecb`; 48 files under `tests/`, 9 tests; green on the tree; the room had one failure of #311's class |
| `beadloom-7i09` | S1a | done | `32197286`; MAJOR move 2 measured (pre-push without `beadloom` on PATH rc 0 → 1 with a sentence); new `graph/lint_scope.py`, `services/commands/hook_templates.py`; room 14432 passed + 1 of #311's class, tree 14479 passed, `ci` rc 0 |
| `beadloom-q8x6` | S1b | ready | wave 4 |
| `beadloom-b23f` | S1c | done | `9780e302`; ownership by the files a claimed bead's commits changed, `unattributed` otherwise, the rule and base printed; `ci` JSON `ownership` and MCP `owners` one shape (`unowned` gone); room 14444 passed + 1 of #311's class, tree 14491 passed, `ci` rc 0 |
| `beadloom-fgu8` | S1d | ready | blocked by S1g |
| `beadloom-ba9w.13` | S1e | ready | wave 4 |
| `beadloom-jwfc` | S1e2 | ready | blocked by S1g |
| `beadloom-6xdt` | S1f | done | `ba8ce1f4`; MAJOR move 1 measured (rc 0 → 1 on a declared log the tree does not hold); new `application/gate_issue_log.py`; room 14412 passed + 1 of #311's class, tree 14459 passed, `ci` rc 0 |
| `beadloom-rupp` | S1T | blocked | blocked by S1a–S1f, S1e, S1e2 |
| `beadloom-pohj` | S1R | blocked | blocked by S1T |
| `beadloom-hfxv` | S1W | blocked | blocked by S1R |
| `beadloom-c5m5` | S1P | blocked | blocked by S1W |

## Notes

- The owner's rulings of 2026-10-18 are in PRD.md; D1–D9 in RFC.md. Behaviour rules agreed before code: D1 (the hook fails), D4 (the base), D5 (the exit code), D9 (the re-measurement protocol).
- S2 and S3 beads are created when their slice starts (ruling 6); S4–S7 are designed from S3's result.
- The adopter's project is never named; the fixture is "the monorepo fixture".
- The wave shape of 2026-10-18 over the seven S1 dev beads: six waves, twenty serialisations by `cli-commands` and `ci-gate`; only S1e and S1b share a wave. The plan run as `--parent beadloom-ba9w` also lists the sixteen older children (slices A–I), which are not S1; the plan is read over the seven ids.
- The fixture's `.beadloom/` is hand-written: `init --yes` wrote no node for `backend/` — filed as BDL-UX #351 (`beadloom-483w`), to be placed by S3d.
- Wave 1 notes (2026-10-18): the pre-commit scope check warns that `gate.py`, `gate_issue_log.py` and `issue_number.py` are outside BDL-083's declared axes — the RFC's eight `###` targets are not read as rows (the #316 shape); surface-drift warnings stand on `docs/guides/{testing,bdd-scenarios,parallel-waves}.md` (S1W); the declared surface grew 815 → 817 pairs.
- Wave 3 note (2026-10-18): a bead's `refs:` attribute nothing now — the declaration parser reads no file paths, so D3's clause about paths named in `refs:` has nothing to read; for S1R to rule on. `derive_gate_ownership` takes its base from `trunk_ref`; S1d moves it to `scope_base` (note on `beadloom-fgu8`).
- The pre-push Gate crashed on a non-blocking pipe on 2026-10-18 while filing #326–#350 (evidence on `beadloom-jwfc`); pushes from the agent's shell redirect the hook's output to a file until S1e2 lands.

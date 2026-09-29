# ACTIVE: BDL-075 — Release 7.0.0 with the documentation current

> **Last updated:** 2026-09-29
> **Phase:** Completed

---

## Current Bead

**Bead:** none — every bead of BDL-075 is closed, and the epic closes with this commit.

## Outcome

- **7.0.0 on PyPI**, published 2026-09-29 from `main` at `e02c347e` (PR #88, 9/9 checks green), GitHub release `v7.0.0`, publish run 36624707476 (tests 3.10–3.13, release gates, build, test-install, TestPyPI, PyPI all green).
- **Verified on the downloaded wheel** (`beadloom-7.0.0-py3-none-any.whl`, sha256 `22b2c9e284f5…`): the V1 harness, exit 0, 7 of 7 checks, on a project that is not this repository; the first attempt met PyPI's CDN lag (exit 3, the index did not yet serve 7.0.0 though `/pypi/beadloom/7.0.0/json` did) and passed on the next.
- **Documents:** README pair (12 defects, a section on tests bound to the graph), ROADMAP (findings corrected, ranking 1–11, federation deferred, the version line verified here), issue log (Open 133 → 79, structure repaired), PLAN and BRIEF templates without a status column, the `--sample-of` help naming the population.
- **Filed on the way:** `beadloom-phjj`, `beadloom-tu41`, `beadloom-s34t`.

**V1 and R closed (2026-09-29):** V1 `beadloom-adbg` — the harness fails on 6.0.0 from PyPI (7 of 7) and on three forged artifacts, passes on the built 7.0.0 wheel; every first-run step of both READMEs ran as written; suite 11 718 passed. R `beadloom-bz48` — first run CHANGES REQUIRED (1 major: ROADMAP behind the tracker after the coordinator's tracker changes; 5 minors) → F1 `beadloom-uk2e.1` `ace157ad`; the owner added F2 `beadloom-uk2e.2` `a5e54033` (the `--sample-of` help named the sample size, it is the population); second run OK with minors, fixed by the coordinator (PLAN's DAG and dependencies, ROADMAP's release sentence, `cli.md`'s sample sentence, CONTEXT's phase, the PRD's non-goal). Filed on the way: `beadloom-phjj`, `beadloom-tu41`, `beadloom-s34t`.

**Waves 1–3 closed (2026-09-29):** T1 `5e64acf6` (PLAN template), `beadloom-3nwz` `c2bc090d` (BRIEF template, added by the owner); R1 `12d33f0c` (7.0.0 in 7 checked places, `[7.0.0]`, no ignore triple needed; `beadloom-tu41` filed); D1 `4507481e` (README pair: 12 defects, a section on tests bound to the graph, a `readme-pair` row; 118 blocks, 0 findings); D2 `16fa318e` (ROADMAP: 27 findings, open work ranked 1–11 in the owner's order, federation deferred; `beadloom-txeq` closed); D3 `f8b65c6a` (issue log: Open 133 → 79, Closed 117 → 175, no number in two sections; `beadloom-s34t` filed). Tracker: the nine federation beads deferred, molecule `beadloom-9lcb` closed, `beadloom-cxal` P1 → P2.

## Progress

- [x] Docs folder, the Explore axes and the adopter-visible changes (`axes.md`, 2026-09-29)
- [x] PRD, RFC, CONTEXT and PLAN approved (2026-09-29); the PLAN template added to the scope by the owner
- [x] Beads created: epic `beadloom-uk2e` + 7 from one plan, `beadloom-10er` brought under it
- [ ] The release commit (R1, T1, D1–D3, V1, R)
- [ ] PR, merge, publish, verify on the downloaded wheel (P)

## Results

> The bead id is the FIRST cell of every row: the focus-document medium reads the first cell only (BDL-UX #272).

| Bead | Role | Status | Details |
|---|---|---|---|
| `beadloom-uk2e` | epic | ✓ done | BDL-075 parent |
| `beadloom-nxf7` | R1 dev | done | 7.0.0 on every current-version site and `[7.0.0]` in CHANGELOG; no ignore triple needed; `beadloom-tu41` filed |
| `beadloom-10er` | T1 dev | done | the PLAN template without a status column; BRIEF's twin filed as `beadloom-3nwz` |
| `beadloom-3nwz` | T1b dev | done | the BRIEF template without a status column |
| `beadloom-fdvz` | D1 tech-writer | done | the README pair: the audit's rows fixed and measured on 7.0.0, the section on tests bound to the graph; `readme-pair` 118 blocks, 0 findings |
| `beadloom-n5w5` | D2 tech-writer | done | ROADMAP.md: the audit's 27 rows and M1-M8 resolved (detail in the bead); open work ranked 1-11 in the owner's order; three shipped items moved to 'Shipped since v4.0.0'; federation deferred; every open P0/P1 bug named; `beadloom-txeq` closed |
| `beadloom-o2z4` | D3 tech-writer | done | BDL-UX-Issues.md: Open 133→79, Improvements 20→17, Excluded 7→6, Closed 117→175; no number both open and closed; `beadloom-s34t` filed |
| `beadloom-adbg` | V1 test | ✓ done | the built wheel; the README's steps |
| `beadloom-bz48` | R review | ✓ done | review |
| `beadloom-vgst` | P publish | ✓ done | publish and verify |

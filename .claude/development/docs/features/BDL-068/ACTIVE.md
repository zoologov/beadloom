# ACTIVE: BDL-068 — The flow's rules are advice; make them instruments

> **Last updated:** 2026-09-04
> **Phase:** Development — S1-S3 merged; S4 wave 1 landed, wave 2 in flight

---

## Current Bead

**Bead:** S4 wave 2 — `0mdo.32` alone (`beadloom waves` serialised it against all five remaining
beads), so it is its own gate owner. Wave 1 (`0mdo.27` + `0mdo.31`) landed: `9d73c99`, `5fd9636`.
Wave order from the graph, not chosen: `.32` → (`.33` + `67t1`, gate owner `67t1`) → `en0x` →
`gsal` → `nn4c`. Six waves for seven beads, because the slice is nearly one area of code —
`flow-guards` and `cli-commands` account for 14 of the 19 serialisation reasons.
**Goal of S4:** the guards' enforcement surface is narrower than their promise — derive each
guard's surface from its own matcher, compare it against what exists, report the gap.
**Branch:** `features/BDL-068` — **no suffix, deliberately**. BDL-UX #230: `declared_scope`
matches a branch segment that EQUALS a work-item key, so `features/BDL-068-S2S3` named no work
item and `review-brief`'s work-item channel read NOT INSPECTED for the whole of S2/S3. The fix is
filed; this name is the free mitigation and later slices keep it.

## Progress

- [x] PRD, RFC, CONTEXT, PLAN approved 2026-09-02
- [x] **S1 — `impact`, the `## Axes` section, `Explore`** — merged as PR #59 (`17eafb8`)
- [x] **S2 — the review's independence, reported rather than asserted** — merged in PR #60
- [x] **S3 — what we measure with** — merged in PR #60 (`97e0504`)
- [ ] S4 — the guards' enforcement surface
  - [x] `0mdo.27` — duties declared rather than inferred, checked in both directions. Green in a
    clean room over 12 files (8 316 passed, 1 pre-existing failure that is red at HEAD in the same
    room); `beadloom ci` rc 0 there, verdict taken in Darwin arm64 / CPython 3.13.7, 0 of 21
    declared rooms. Not a claim about the combined tree.
  - [x] `0mdo.31` — **#170**, all three pieces. The matcher names `Bash`; a shell edit resolves to
    the new `PathScope.UNDETERMINED`, matches no exclusion and carries its undetermined write set
    into `not_covered`, so a `pass` on a shell command can no longer read as coverage; and
    `guard --liveness` reports the binding's SURFACE beside the firings, derived from
    `.claude/settings.json` and the `tools:` grant of every emitted role adapter. Measured on this
    repository: 3 of 3 write paths bound, and 2 of 3 before the fix. Green in a clean room over 22
    files (8 510 passed; the 1 failure is a stated property of the room — no `.git`, so
    `sync-check` reports 402 pairs `no_baseline` and 0 stale). **As the wave's gate owner:** the
    combined tree is green — 8 542 passed, 0 failed, `beadloom ci` rc 0 foreground and unpiped.
    Every verdict taken in Darwin arm64 / CPython 3.13.7, 0 of the 21 declared rooms.
    Filed BDL-UX #235: the two rooms of this wave collided on one scratchpad path.
- [ ] S5 — the tracker adapters
- [ ] S6 — the flow's documents and roles

## What is in `main` now

Four commands, each of one shape — derive the answer, name the reason, name what was not reached:

| Command | Answers | Refuses to |
|---|---|---|
| `beadloom impact <path\|symbol>` | the axes a change ranges over, from the source; the seed derived under `reaches-an-effect-sink` and named | render a seedless target as an empty list — "every axis below the seed is unresolved, not empty" |
| `beadloom scope-check` | whether a commit touched a path outside the work item's declared axes, naming which axis | fire on a commit inside them |
| `beadloom mutation` | the score against the declared scope | turn an absence into a number — a missing counter is reported, not read as zero |
| `beadloom rooms` | the room census derived from `ci.yml` and `pyproject`, and which rooms this run entered | omit the reason a room was not entered |

Plus: the `Explore` role composed by `role-composer` and available as `subagent_type: explore`;
`## Axes` a required section of BRIEF and RFC, with an empty section a finding and a row without a
scope decision a finding; `review-brief` reporting reachability per channel and naming the launch
prompt as one nothing can inspect.

## Decisions taken at planning, not to be re-litigated per bead

- **Q1** — the axes are DERIVED by `beadloom impact`; the document records the derivation and the
  human's scope decision; the bead's `refs:` is generated from the document. A disagreement
  between the three is a finding.
- **Q2** — the commit-scope check compares against the WORK ITEM's axes, not the bead's.
- **Q3** — ANSWERED BY MEASUREMENT: the mutation job runs **nightly**. 54m55s over 3 989 mutants
  at 96.2%, against the ~16-28 runner-minute budget that withdrew `tests-windows`.
- **Q4** — External `bd` findings are answered by deriving our own call sites, not by a wrapper.
- **Q5** — `Explore` is a role file composed by `role-composer`, not a mode.
- **Beads are created per slice**, when the preceding slice's review closes.

## S4, as created

`beadloom-0mdo.12` is the slice and depends on every row below, so it cannot close while one is open.
Eight dev beads, then test → review → tech-writer. Created 2026-09-03 under the epic's rule that
beads are created per slice, once the preceding slice's review closes.

| Bead | What it is | P |
|---|---|---|
| `0mdo.27` | a duty declared for a role is carried by that role's composed core, checked in BOTH directions — the machine half | P1 |
| `67t1` / **#228** | the clean-room duty reaches roles only through the coordinator's typing — the duty half; depends on `.27` | P1 |
| `0mdo.31` | **#170**, the entry this slice is named after: the guard binds `Edit\|Write\|NotebookEdit` and a write through `Bash` fires nothing. Three pieces, and the third — report the SURFACE, not the firings — is the real one | P1 |
| `0mdo.32` | the residue of `mr2l.81`: the commit gate judges staged paths, so a neighbour's hunk inside a file the committer touched reads clean. Wire S1's `scope-check` into the hook | P1 |
| `0mdo.33` | the residue of `mr2l.60`: the refusal rule is a literal backslash, so on Windows every edit is MALFORMED and the stated reason is false there. `os.sep`/`os.altsep` + a shape gate | P2 |
| `gsal` / **#231** | the commit hook type-checks an undeclared surface (970 errors in 90 files), discards mypy's output, never blocks; a real `src/` error prints the same sentence | P1 |
| `en0x` / **#232** | `waves` plans from an AUTHORED `refs:` line, so two beads editing one document read as independent. Measured: `.21` and `.26` both edited `docs/services/cli.md`, 0 findings | P1 |
| `nn4c` / **#233** | the read-only guard test attributes by TIMING, and a `bd` export burst lands inside the measurement window and misses the control window. Least reliable exactly when the flow is most parallel | P1 |
| `0mdo.34` | test — the surface as a shape, never a spelling | P1 |
| `0mdo.35` | review | P1 |
| `0mdo.36` | tech-writer | P1 |

**`mr2l.81`, `.60`, `.82`, `.92` were closed 2026-08-31 in a tracker cleanup as UNFINISHED work,
not as done** — the close comment says so on each. `.82` and `.92` came back sharper as `gsal` and
`nn4c`; `.81` and `.60` are carried here as `.32` and `.33`. A closed bead whose work never
happened is the same false green this epic is about, one layer up in the tracker.

**`.32` is mostly wiring now, and that is S1 paying off.** `.81` had to design the mechanism it
needed; `beadloom scope-check` shipped it in S1, and CONTEXT Q1/Q2 already answered two of the four
questions `.81` said had to be settled before building. What is left is the exempt set (measured
against real commits BEFORE it goes live), warn-not-block, and `unjudged` for an unattributable commit.

## Standing conventions every launch prompt carries

These are prompt-level today, which is exactly what #228 is about. Until it lands they must be
typed into every bead's prompt:

- **"green in a clean room over N files" and "green on the tree" are different claims** — report
  them in different words (BDL-UX #181).
- **A verdict names the room it was taken in.** `beadloom rooms` says a local run is in 0 of the
  21 this project declares.
- **Check filenames before staging** — a new test file on an existing path deletes its scenarios
  and the suite goes green over the wreckage (BDL-UX #224, unfixed).
- **Checkpoint every few steps.** Nine agents across the two epics were cut off mid-work; the
  checkpoints made every resume cheap and their absence made one expensive.
- **`beadloom waves` before every wave**, and commit the tracker export first — it reports a path
  owned by no bead in the plan as a working-tree finding, correctly, twice so far.
- The wave's **gate owner** measures the combined tree; everyone else reports their own room only.

## Coordinator errors recorded, because the pattern outlived each instance

- **Pipe-masking, three times.** `beadloom ci | tail` and `beadloom waves | head` report the
  pipe's exit code. Measure without a pipe or read `PIPESTATUS`.
- **Backticks in commit messages, three times.** The shell executed them; twice the message was
  mangled and once it produced a phantom hook-bug diagnosis that cost two commands to disprove.
  Write commit messages through `python3` with a quoted heredoc, never inline.
- **UX numbering.** #216–#222 and then #223–#232 lived as bead titles while the log carried
  neither; the same gap produced a duplicate #211 earlier in this epic. Allocate in the log.
- **Branch naming** — see the Current Bead block.
- **A commit to `main`, caught within one command.** `git switch -c features/BDL-068` failed
  because the merged S1 branch still held that name; the compound command carried on and the
  commit landed on `main`. Recovered by moving it to a fresh branch and `git reset --hard
  origin/main`, and `main` never left `origin/main`. The lesson is the compound: a `switch -c`
  whose failure is not checked hands the next command a branch it did not choose.
- **Four CI rounds on PR #60**, each finding the same class one layer deeper, and none of them
  reproducible locally because every local measurement was taken in 0 of 21 declared rooms.

## Notes

The last finding of S3 is worth carrying forward as the slice's real deliverable: `.30`'s third
pass made the room a **substitutable input** (`tests/room_simulation.py` replaces `current_room`
at `pytest_configure`), so restoring the broken arrangement now reddens exactly `[Linux/3.10]`
and `[Linux/3.11]` from a developer machine, in one run. A verdict that prints its room is the
visible half; a room that can be fabricated is the half that catches the next one.

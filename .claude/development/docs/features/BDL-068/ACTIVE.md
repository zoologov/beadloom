# ACTIVE: BDL-068 — The flow's rules are advice; make them instruments

> **Last updated:** 2026-09-04
> **Phase:** Development — S1-S3 merged; S4 waves 1-2 landed, wave 3 in flight

---

## Current Bead

**Bead:** S4 wave 3 landed — `0mdo.33` (`4fce7d2`) + `67t1` (`a5bf5ae`, `204fc95`), gate owner
`67t1`, combined tree measured green. Wave 1 (`0mdo.27` + `0mdo.31`) landed: `9d73c99`,
`5fd9636`; wave 2 (`0mdo.32`) landed: `a198832`. Wave 4 is `en0x`, then `gsal`, then `nn4c`.
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
  - [x] `0mdo.32` — the residue of `mr2l.81`, and mostly not where the bead expected. The
    `scope-check` call had been in both hook templates since S1; what the hook DID with the
    answer was the hole. It read the command as `2>/dev/null` while the reason for having
    compared nothing went to stderr, so a clean run and a run that could attribute no work item
    were the same empty string on that stream and the gate printed the same nothing for both.
    `--porcelain` now leads stdout with the verdict, marked `# ` so a shell splits it from the
    findings on a shape rather than an agreement, and both templates print it whether or not
    anything fell outside. **The three open decisions, each measured before it was taken.** The
    exempt set is *the paths no node owns*, derived from graph ownership rather than authored as
    a list that could drift out of step with it — measured over this branch's eleven commits at
    `b7c9476..8b40417`: 52 paths, of which 11 have an owner in the graph and 41 have none, and 0
    findings on every commit. **Warn, not block**, because a zero false-positive rate over eleven
    commits is not enough when only two of them touched an owned path at all and one work item in
    64 carries an `## Axes` section. And an unattributable commit is `NOT CHECKED` with its
    reason, which is what makes BDL-UX #230's consequence audible: a branch named
    `features/BDL-068-S4` now prints why it judged nothing instead of printing nothing.
    Green in a clean room over 14 files (8 539 passed; the 1 failure is a stated property of the
    room — no `.git`, so 41 pairs read `unverified` rather than `ok`, and it is red at HEAD in an
    identically-built room). **As its own gate owner:** the tree is green — 8 570 passed, 0
    failed, `beadloom ci` rc 0 foreground and unpiped. Every verdict in Darwin arm64 / CPython
    3.13.7, 0 of the 21 declared rooms. Two of this bead's own defects were caught by the
    project's instruments rather than by review: the clean room found an inline code span that
    spilled `<key>, <scope>` onto the next line, and `docs-audit` read "41 no node owns" as a
    `node_count` claim. The second was fixed by rewording, not by `docs_audit.ignore`.
  - [x] `67t1` / **#228** — the clean-room duty, both halves. The DUTY half declares
    `<!-- beadloom:duty=clean-room roles=dev,explore,review,tech-writer,test -->` in the
    coordinator command every adopter composes, and `<!-- beadloom:carries=clean-room -->` in
    `roles/core/_rooms.md.txt` and its Russian twin, so one marker delivers to all five roles in
    both languages. It carries the two facts learned after the bead was written: the room's path
    is `room-<bead-id>` (#235) and the gate owner measures the combined tree while everyone else
    reports their own room. `config-check` reads it as `Duties: 1 declared, checked over 10
    composed artifact(s)`, 0 findings; removing the carriage marker gives rc 1 and five
    `undelivered` findings, one per role, which is the tree the check goes red on. The MACHINE
    half removes `media_for(wave_size)`: every wave states all four media and names its gate
    owner and one room per bead, whatever its width, and `not_applicable` is gone as a verdict a
    plan's shape can produce. The reason is in the module rather than in a bead comment — a plan
    is one slice of one epic, so its width is not a claim about solitude, and the working-tree
    check exists precisely to report paths owned by no bead in the plan. **The scratchpad is not
    a fifth medium, deliberately:** a medium there is one with a plan-time precondition a command
    can observe, and a session scratchpad path exists only inside a running agent session — the
    same reason the launch prompt is `not_inspected` rather than a finding. Its remedy ships
    instead, as `room_for`. Green in a clean room over 32 files (8 545 passed; the 1 failure is a
    stated property of the room — no `.git`, and it is red at pure HEAD in an identically-built
    room); `beadloom ci` rc 0 there. On the tree: 8 619 passed and 2 failed, both
    `TestSyncCheckNewPairs` requiring `sync-check` rc 0 while `0mdo.33`'s two doc pairs are stale.
    Every verdict in Darwin arm64 / CPython 3.13.7, 0 of the 21 declared rooms. Not a claim about
    the combined tree; that verdict follows below. A SECOND defect was found and fixed inside
    this bead rather than filed: declaring the first duty made `role_duties`' `not_inspected`
    list grow from two entries to seven, the five new ones being the vendored
    `templates/agentic_flow/agents/*.md.txt` snapshot, each under a reason saying the duties in
    it reach no role — false twice, because the marker is inspected in its composed form and the
    file is dropped verbatim into an adopter's roles directory by the plain scaffold path. The
    snapshot is now out of the subtraction base. **As this wave's gate owner:** the combined tree
    of `0mdo.33` + `67t1` is green — 8 622 passed, 0 failed, `beadloom ci` rc 0 foreground and
    unpiped, `sync-check PASS: 419 pair(s) fresh`. Darwin arm64 / CPython 3.13.7, 0 of the 21
    declared rooms, so it is a claim about this machine and about no CI leg. The tree measured is
    `9030722`, which carries `e0dd14f` as well — a commit from outside this wave that landed
    during the first attempt at this measurement, mid-collection, which is why the number above
    comes from a second run on a settled tree with `HEAD` verified unchanged before and after. A
    combined-tree verdict taken across a write is the same class as a clean room that cannot see
    the bead beside it: it looks exactly like a correct measurement.
  - [x] `0mdo.33` — **`mr2l.60`'s residue**, items 2, 3 and 5; its measurements stand and were not
    redone. The rule is now over the SEPARATOR rather than over one character: the refused set is
    every spelling `ntpath`/`posixpath` declare minus this platform's own (`os.sep`, `os.altsep`),
    so POSIX behaviour does not move by one character and Windows goes from *every edit target is
    `MALFORMED`* to a working guard. What the shape gate then owes there is three refusals it never
    made — a trailing dot, a trailing space and the 22 reserved device names, each of which the
    Win32 name layer silently REWRITES, which is the guard-and-writer divergence the module exists
    for; the characters Win32 forbids outright are deliberately left out, because such a write fails
    loudly and nothing diverges. **Item 5 without a leg:** the platform is a substitutable input
    (`PathFlavour`, the same shape S3 gave the room), so both platforms' rules are measured on one
    machine — no `xfail`, and what substitution cannot reach is a residual in the SPEC, including the
    new one it introduces (a REFUSED target is settled anywhere because the refusal is lexical; an
    ACCEPTED one is then resolved by whatever kernel is running). 7 acceptance scenarios seen red in
    two steps — the second with the flavour plumbed and the OLD rule, so 5 of 7 were seen to bite on
    the rule rather than on an import. Green in a clean room over 9 files (8 557 passed; the 1
    failure is the room's stated property — no `.git` — and is red at HEAD in an identically-built
    control room). Every verdict in Darwin arm64 / CPython 3.13.7, 0 of the 21 declared rooms; not a
    claim about the combined tree, which is `67t1`'s to make. Filed BDL-UX #236: a clean room's
    verdict is decided by which optional extras it installed, measured as 0, 1 and 82 mypy errors
    over one code base.
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

**#228 landed 2026-09-04.** The first two below are no longer prompt-level: the shipped
coordinator command declares the `clean-room` duty for all five roles, `roles/core/_rooms.md.txt`
and its Russian twin carry it, and `config-check` blocks on either half going missing. The room's
path carries the bead id (#235) and `beadloom waves` prints it per bead for every wave. The rest
are still carried by the prompt and by nothing else:

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

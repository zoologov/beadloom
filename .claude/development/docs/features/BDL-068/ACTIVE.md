# ACTIVE: BDL-068 — The flow's rules are advice; make them instruments

> **Last updated:** 2026-09-04
> **Phase:** Development — S1-S3 merged; S4 complete on the branch (dev, test, review and
> docs), unmerged; S5 next

---

## Current Bead

**Bead:** none — S4 is finished on the branch. `0mdo.36` (tech-writer) was the last of the
slice and closed the docs pass; `0mdo.12`, the slice bead, closes with it. The next claimable
work is S5 (`0mdo.13`), which depends on `0mdo.12` and on `0mdo.39` (#237).

**Where S4 ended.** Fifteen beads: eight dev beads over six waves, then the test bead
(`0mdo.34`), then review (`0mdo.35`), then the four fix beads its first pass produced
(`0mdo.41`, `.42`, `.43` with `.44`, `.45` with `.47` — the wave shapes `beadloom waves`
decided, not chosen), then this docs pass. Review `0mdo.35` closed at **0
critical, 0 major** — all four Majors closed by measurement — and explicitly did NOT arm the
re-plan rule, because the RFC arms it on a second ISSUES verdict on one slice and this was S4's
first. Ten Minors and three Nitpicks are open and unassigned; they are listed under
*Review findings left open* below, so the next session does not have to re-read the verdict to
find them.

**What is in the branch and not in `main`.** `features/BDL-068` carries S4 as 47 commits ahead
of `main` at the moment this was written. Nothing of S4 has been merged: S1 went in as PR #59
and S2 + S3 as PR #60, and S4 will be its own PR. `beadloom ci` is rc 0 on the branch,
measured in Darwin arm64 / CPython 3.13.7 and in 0 of the 21 rooms this project declares, so
it is a claim about this machine and about no CI leg.

Wave 6 landed: `nn4c`, its own gate owner, combined tree measured green. Wave 5 landed:
`gsal`, its own gate owner, combined tree measured green.
Wave 4 landed: `en0x` (`ded748d`), its own gate owner, combined tree measured
green. Wave 3 landed: `0mdo.33` (`4fce7d2`) + `67t1` (`a5bf5ae`, `204fc95`), gate owner `67t1`,
combined tree measured green. Wave 1 (`0mdo.27` + `0mdo.31`) landed: `9d73c99`,
`5fd9636`; wave 2 (`0mdo.32`) landed: `a198832`. Wave 6 is `nn4c`, the last of S4's dev waves.
Wave order from the graph, not chosen: `.32` → (`.33` + `67t1`, gate owner `67t1`) → `en0x` →
`gsal` → `nn4c`. Six waves for seven beads, because the slice is nearly one area of code —
`flow-guards` and `cli-commands` account for 14 of the 19 serialisation reasons.
**Goal of S4:** the guards' enforcement surface is narrower than their promise — derive each
guard's surface from its own matcher, compare it against what exists, report the gap.
**Branch:** `features/BDL-068` — **no suffix, deliberately**. BDL-UX #230: `declared_scope`
matches a branch segment that EQUALS a work-item key, so `features/BDL-068-S2S3` named no
work item and `review-brief`'s work-item channel read NOT INSPECTED for the whole of S2/S3.
The fix is filed; this name is the free mitigation and later slices keep it.

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
  - [x] `gsal` / **#231** — the commit hook's type-check leg, and the bead's own account of it
    needed one correction before anything could be fixed. **What is true:** the leg ran `mypy`
    over every staged `.py` under `src/` or `tests/`, while `pyproject` declares
    `packages = ["beadloom"]` and `ci.yml` runs `uv run mypy src/` — `uv run mypy tests/` is 970
    errors in 90 files and not one is a violation of a declared standard. **What is not:** the
    bead says the hook DISCARDS mypy's output via `2>/dev/null`. It does not — mypy writes its
    findings to stdout, verified by splitting the streams. What `2>/dev/null` hides is the
    diagnostics of a mypy that could not START, so the two indistinguishable states were "found
    errors" and "could not run", not "found errors" and "silent". The defect is real and its
    mechanism was misread, which is why the fix prints `2>&1` rather than merely re-enabling a
    stream that was never off. **MEASURED over all 24 commits of this branch** at
    `b7c9476..49c2ebe`, each against its own tree in a linked worktree: 7 staged Python at all,
    63 paths between them, 31 of the 63 inside the declared surface. The old leg warned on 4 of
    the 7 commits and all 4 warnings were false; a surface-scoped leg is clean on all 7, so its
    false-positive rate over this branch is zero. The measurement gives a second finding free:
    under the blocking template those same 4 commits would have been REFUSED, so block mode was
    unusable on this repository. **The surface is derived, never listed** — `beadloom-mr2l.82`
    listed it in the hook template, the mypy configuration then moved and the template did not,
    which is the whole argument for `beadloom typed-surface` answering the question at the moment
    the hook asks it. `[[tool.mypy.overrides]]` is outside the read by construction, and the
    declaration is parsed without a TOML parser for `rooms.py`'s reason: `tomllib` is 3.11+ and
    `tomli` is not a runtime dependency, so a parse would give a room-dependent answer from the
    module whose subject is what a check covers. **WARN IN WARN MODE, BLOCK IN BLOCK MODE, and
    `NOT CHECKED` never blocks in either.** The mode decides, because the population is now
    exactly a standard the project declares and CI already enforces — unlike `.32`'s axes block,
    which warns in both modes because one work item in 64 carries an `## Axes` section. A surface
    that could not be derived is a check that did not happen, and turning a missing `PATH` entry
    into a refused commit is how a gate comes to be answered with `--no-verify`. The verdict has
    three sentences and not two: `NOT CHECKED` with its reason, `NOTHING TO CHECK` for an empty
    typed population, and a count of the files actually handed to the checker. All four states
    are verified through a real `/bin/sh` running the real emitted template. Three existing tests
    went red and were UPDATED rather than weakened, and all three are the project's instruments
    working: the literal CLI command set, the AS-IS node population (111 → 112), and
    `test_cli_json_streams`, which caught this bead's own new test reading `result.output` where
    Click merges stderr in. Green in a clean room over 23 files (8 680 passed; the 1 failure is
    the room's stated property — no `.git`, so `sync-check` has no baseline — and it is red at
    pure HEAD in an identically-built control room), in Darwin arm64 / **CPython 3.12.12**, which
    is not the tree's interpreter. **As its own gate owner:** the combined tree is green — 8 719
    passed, 0 failed, `beadloom ci` rc 0 with every step PASS or WARN, `mypy` clean against all
    four declared target versions and `ruff` clean. Every tree verdict in Darwin arm64 / CPython
    3.13.7, 0 of the 21 declared rooms.
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
  - [x] `en0x` / **#232 + #234** — the planner's own scope input was AUTHORED while everything
    else this epic built is derived, and the printed remedy outran what its reason could tell.
    **The fix is not to stop reading the declaration** (CONTEXT Q1): the declaration still
    decides the shape, and what is added is the comparison against the derivation the work item
    recorded, composed at the services edge from the SAME read `scope-check` makes so the
    commit gate and the plan cannot disagree about one approval. Measured on the pair that
    produced the defect: `beadloom waves beadloom-0mdo.21 beadloom-0mdo.26` reported 1 wave, 2
    beads, 0 findings before and now reports `unguarded_axis` naming **`cli-commands`** among
    the nine approved nodes neither bead declares — `cli-commands` owns `docs/services/cli.md`,
    the document they collided in. The unit is Q2's: `0mdo.27` editing `cli-commands` outside
    its own refs stays correct and raises nothing. **Three verdicts are deliberately not
    findings** — a ref the table never names is the DERIVATION not reaching (#225, measured: no
    node attributed to any of 148 caller sites under `tests/`), an axis row naming no node is
    compared against nothing (the table-scale shape of `.32`'s 41-of-52 unowned paths), and a
    row nobody ruled on belongs to `axis-without-a-scope-decision`. **The gap is reported per
    WAVE and only where a wave holds a pair**, because the sentence it makes is about a
    pairwise verdict; per plan it would print 9 findings on every single-bead plan of this epic,
    and an always-red check is an ignored check. That is NOT `media_for(wave_size)`, which
    `67t1` removed — that suppressed a STATEMENT about a medium shared whatever the width.
    #234 measured on `beadloom-nn4c`, unchanged and unclaimed: the same correct reason now
    carries a remedy stating BOTH sub-cases and the fact that nothing here can tell them apart,
    so following it can no longer manufacture the authored scope #232 is filed against.
    Green in a clean room over 18 files (8 626 passed; the 1 failure is the room's stated
    property — no `.git`, so 420 pairs read `unverified` — and it is red at pure HEAD in an
    identically-built control room); `beadloom ci` rc 0 there, in Darwin arm64 / **CPython
    3.12.12**, which is not the tree's interpreter (#236's shape: a room's verdict is decided by
    what it installed). **As its own gate owner:** the combined tree at `ded748d` is green —
    8 657 passed, 0 failed, `beadloom ci` rc 0 foreground and unpiped, `HEAD` verified unchanged
    before and after, and `mypy` clean against all four declared target versions. Every verdict
    in Darwin arm64 / CPython 3.13.7, 0 of the 21 declared rooms. **A claim this bead made and
    then had to withdraw:** the combined-tree verdict was first reported as taken over a tree
    also carrying four uncommitted files from outside the bead. It was not. Those four are
    byte-identical to `HEAD` and their mtimes predate this bead's first command, so the launch
    context's `git status` snapshot was stale and was restated instead of re-derived — the
    bead's own defect, one layer up. The verdict itself is unaffected and both commits carry
    only this bead's files. Four existing tests went red and were UPDATED rather than the rule
    weakened —
    each now says what its declarations were held against — which is the same move `mr2l.80`
    made when the environment default stopped meaning clean.
  - [x] `nn4c` / **#233** — the read-only guard test attributed by TIMING, and the bead's
    account of the timing was itself half a step behind the tracker. **What is true:**
    `_moved_with_nothing_running` can only see a writer that is STILL WRITING when the
    control window opens, which is a concurrent `beadloom lint` and is not a `bd` export —
    so both observed failures named `.beads/issues.jsonl` and neither named `beadloom.db`.
    **What is sharper than the bead:** the export is not a burst inside its own invocation.
    It is **deferred**. Measured: four consecutive `bd update --priority` writes each left
    the export unmoved when sampled immediately afterwards, and it had been rewritten by the
    next sample with no `bd` command running in between; and `bd list`, the evaluation's only
    tracker call, moved neither digest nor mtime in 3 of 3 runs. A deferred flush is strictly
    worse for a control window than a synchronous one, because it lands at a moment nothing
    in the session marks — the window has nothing to overlap with by construction. **The fix
    attributes by FILE, and the partition is DERIVED rather than authored:**
    `TestTheTrackerExportIsOutsideTheGuardsReach` records the argv the evaluation hands the
    `bd` seam and holds it against `_READ_ONLY_BD_SUBCOMMANDS = {"list"}`, so giving a guard
    a mutating tracker call turns it red and invalidates the partition loudly. The export
    stays IN the comparison: a change there is detected, named, and charged to the process
    that can write it. **Three outcomes now reach the reader in three words** — `charged`
    (the guard's, red), `elsewhere` (another process's, decided by path, reported and not
    fatal) and `unattributable` (the repository is moving, skip). Collapsing the second into
    the third is what reported a neighbour's `bd comments add` as the guard's own write, and
    a wave makes that likelier rather than rarer. **A measurement this bead made and then
    threw away:** six live-test runs passed under a 0.3 s `bd update --claim` loop, and the
    loop wrote nothing — re-claiming an already-claimed bead is a no-op — so the burst path
    was exercised zero times and "six green runs under a burst loop" would have been evidence
    of nothing. The reporting step was extracted as `_report` and driven deterministically
    instead, including the anti-silencing case: a burst reported beside a guard write must
    still fail on the guard write. **Bite verified by mutation, not asserted:** a one-line
    append to `beadloom.db` at the top of `evaluate_guard` turned the live test red with the
    right sentence; source restored (`git diff src/` empty) and the two injected bytes
    truncated off the index (`PRAGMA integrity_check` ok before and after). The module goes
    from 36 tests to 52, and all 16 new ones were seen red first; no `src/` change. Green in
    a clean room over 3 files (8 696 passed; the 1
    failure is the room's stated property — no `.git`, so no freshness baseline — and it is
    red at pure HEAD in an identically-built control room), in Darwin arm64 / **CPython
    3.12.12**, which is not the tree's interpreter. The room does not measure the live path at
    all: `.beadloom/beadloom.db` is gitignored, so a `git archive` room has no index and the
    test skips there. **As its own gate owner:** the combined tree at `c39928c` is green —
    8 735 passed, 0 failed, `beadloom ci` rc 0, `HEAD` verified unchanged before and after,
    `mypy` clean against all four declared target versions and `ruff` clean. Every tree
    verdict in Darwin arm64 / CPython 3.13.7, 0 of the 21 declared rooms.
  - [x] `0mdo.41` / **#239 + #241** — the one place S4's eight instruments disagree, made
    visible rather than made the same. `.31` and `.27` landed in ONE wave answering "does a
    declared thing reach the role that must carry it?" of two different corpora — the
    artifacts on disk and the composition — and neither said which, so on a project holding
    no role file one reported the artifacts missing and the other reported a duty delivered
    to five roles at exit 0. **The divergence is kept**, because both questions are
    legitimate and each instrument has a reason for the one it asks: `scaffold_guard_hooks`
    merges on the command string, so only disk can say an upgraded project kept its narrower
    matcher, and `--fix` writes compositions, so only the composition can say what the next
    scaffold would deliver. What changed is that each names its corpus in the sentence it
    prints — a `read from:` line under the surface verdict, and `the COMPOSITION this flow
    would write, not the role files on disk` in the duty line, with the adapters on disk
    COUNTED beside it and never read. **#239 is one word and a `None`:**
    `BindingSurface.describe()` now has three sentences in `gsal`'s vocabulary — NOT CHECKED,
    NOTHING TO CHECK, or the fraction — and `covered` is `None` in both non-fraction states,
    so `0 of 0` cannot be printed or parsed out of `--liveness --json` either. The three
    reproductions the test bead measured all reach the middle sentence; the block-sequence
    `tools:` grant that produces the sharpest of them is deliberately NOT parsed, because a
    report whose population is empty for ANY reason must not print a fraction and widening
    the reader is a different defect. Exit codes unchanged throughout: an unscaffolded
    project is not in drift. 6 tests appended to `test_s4_the_instruments_agree.py` (not a
    second file — #224) and 3 acceptance scenarios in the two existing feature files, each
    seen red first; 7 hand-injected mutants at the new seams, all 7 red, one of them a
    finding about an assertion of mine that checked the empty case and not the counted one.
    Green in a clean room over 15 files at `room-beadloom-0mdo.41` (8 722 passed; the 1
    failure is the room's stated property — no `.git`, so no freshness baseline — and it is
    red at pure HEAD in an identically built control room, measured rather than asserted),
    `beadloom ci` rc 0 there. On the tree: 8 761 passed, `beadloom ci` rc 0 foreground and
    unpiped, `HEAD` verified unchanged either side. Every verdict Darwin arm64 / CPython
    3.13.7, 0 of the 21 declared rooms, so none of it is a claim about any CI leg.
  - [x] `0mdo.42` / **#240** — a rule stated as a shape, reached through a filter stated as a
    spelling. `beadloom-gsal` replaced the hook's hand-written typed surface with one derived
    from `pyproject`, and the hook still selected the files it would ask about with
    `grep -E '^(src|tests)/.*[.]py$'`. So the derivation was only ever asked about paths two
    directory names admitted, and on the FLAT layout — the package at the repository root —
    it admits none of the package. **The reproduction is sharper than the bead states, and the
    difference is the finding:** total silence needs a commit staging nothing under `src/` or
    `tests/` at all, and a flat project WITH a `tests/` directory stages test files the regex
    does admit — so the leg speaks, and says `NOTHING TO CHECK -- 0 of 2 staged Python file(s)
    are inside it, 2 outside` over a population the whole package is missing from. Silence is
    the half a reader might eventually notice. A confident sentence over the wrong denominator
    is the half nobody would. The same variable gates the ruff leg, which was equally blind.
    **The fix is one line and removes a list rather than adding one:** `staged_py` states which
    KIND of file the commit stages and never where code lives, and each leg narrows that
    population by its own declaration — the typed leg through `typed-surface --filter`, ruff
    through the configuration it reads for itself. `gsal`'s three sentences are unchanged and
    are now REACHABLE on every layout. His fourth-population decision (a commit staging no
    Python prints nothing, measured at 17 of this branch's first 24 commits) stands, and what
    changed is what it rests on: it used to mean "no Python under `src/` or `tests/`". The
    layout is now an ARGUMENT, the way `PathFlavour` made the platform one and
    `tests/room_simulation.py` made the CI room one — five layouts through the real emitted
    template and a real `/bin/sh`, of which this repository can show ONE, plus an
    undeclared-surface layout so the `NOT CHECKED` sentence is reached before it is read.
    20 red first, each layout for its own reason; 1 acceptance scenario on the existing feature
    file. 6 hand-injected mutants, 5 red first time and **one survived**: a `^src/` reintroduced
    into the ruff leg ALONE, because that assertion read the banner the leg prints before its
    filter rather than the files the checker was handed. The stub now names what it was handed
    and the mutant is red. Green in a clean room over 8 files at `room-beadloom-0mdo.42`
    (8 754 passed; the 1 failure is the room's stated property — no `.git`, so `sync-check` has
    no baseline — and it is red at pure HEAD in an identically built control room at
    `control-beadloom-0mdo.42`, measured rather than asserted), `beadloom ci` rc 0 there.
    That room is CPython 3.12.12 and the tree is 3.13.7, which is #236's shape.
    As the gate owner of a wave of one, on the tree: 8 793 passed, 0 failed;
    `beadloom ci` rc 0 foreground and unpiped; `HEAD` verified `e87bed7` either side.
    Every verdict Darwin arm64, 0 of the 21 declared rooms, so none of it is a claim about
    any CI leg.
  - [x] `0mdo.43` / **review Major 1** — the firing record held every agent shell command line
    verbatim, and the shipped `.gitignore` entry invited teams to commit it. Verified against the
    live record before and after, never against a fixture: the generation that rotated during
    this bead holds 1 999 firings of which 1 927 stored the line they fired on — 2.0 MB, 1 007
    bytes a record, 76 of those lines beginning with an environment assignment whose value the
    record kept. The 271 firings written since the change hold 0 command lines, 271 programs and
    42 derived write sets, at 580 bytes a record. **Reduction, not redaction**, per the bead's
    own argument: the context carries `command_name`, `command_writes` and `command_unreadable`
    and never the line, because redaction is a denylist and the next credential arrives as a
    positional argument or inside a heredoc. The reduction sits at the one door the context is
    built at, so `--context command=...` goes through it too — a shell caller and a hook write to
    one file, and a second door the first one's decision does not cover is this epic's own
    subject. Two defects were found on the way and fixed here: an environment prefix hid a
    declared writer from the derivation (`TZ=UTC touch a.py` named nothing), and the record's own
    cap comment still claimed ~200 bytes a record. All three misleading places moved, plus three
    more the change made stale: `firing.py`'s docstring, `guard-hooks/DOC.md`, the `ignore_block`
    entry's `why` — and `flow-guards/SPEC.md`, both domain READMEs. Green in a clean room over 14
    files at `room-beadloom-0mdo.43` (8 769 passed; the 1 failure is the room's stated property —
    no `.git`, so 41 pairs read `unverified` — and it is red at pure HEAD in an identically built
    room), `beadloom ci` rc 0 there, room CPython 3.12.12 against the tree's 3.13.7. **Not the
    gate owner**: `beadloom waves` names `0mdo.44` for this wave's combined tree, so nothing here
    is a claim about it. On the tree, `lint --strict`, `sync-check`, `docs audit` and `doctor` are
    each rc 0 and `mypy` is clean at all four declared target versions; the two failures in
    `test_a_commit_is_judged_against_the_declared_axes.py` are red at pure HEAD (`b740177`) in a
    worktree carrying no file of mine, so they belong to `0mdo.44`'s RFC axes change and not to
    this bead. Darwin arm64, 0 of the 21 declared rooms.
  - [x] `0mdo.44` / **review Majors 2 and 3** — the derivations were performed and never reached
    the documents. S4's twenty-eight `beadloom impact` runs existed as bead comments while the
    RFC's `## Axes` section held S1's three targets alone, so the section `scope-check` compares
    every commit against did not name the code S4 changed. The append is a UNION, per the RFC's
    own per-slice rule, with its own `Derived by` / `Measured on` line: 42 rows, 27 kept, 44
    derivation targets. The `yes`/`no` decision is a RULE and not a judgement — `yes` where the
    epic WRITES the node, `no` where it only READS it — derived from the 239 paths the epic
    changes resolving to thirty owning nodes, so a later slice applies the rule rather than a
    taste. Fourteen new `no` rows narrowed the approval as well as widening it, which is why
    `scope-check`'s findings on one pinned commit went 1 → 6 and not 1 → 0, and why `0mdo.47`
    followed. **Two defects found by using the tools, neither in scope and both filed:**
    `read_axes_section` takes a SECOND markdown table's header row as data, producing an approved
    node literally named `Node` (BDL-UX #244) — worked around here by keeping one table — and
    `scenario-coverage`'s reference matching is case-sensitive, which is a design question rather
    than obviously a defect. Also repaired in the same file, same class: the RFC's `## Open
    Questions` still read `Pending` for Q1, Q2, Q4 and Q5 in an Approved document while CONTEXT
    had carried all four answers since 2026-09-02, and CONTEXT's `## Current Phase` still named
    S1. `beadloom docs quality` reports 0 findings for BDL-068; `beadloom lint --strict` rc 0;
    `beadloom scope-check --since main` rc 0. No source file was touched.
  - [x] `0mdo.45` / **review Major 4** — five new domain cores under no mutation claim,
    and three older targets under a claim nothing measured. The older half was the larger
    one and it was not a delay: `[tool.mutmut] only_mutate` named `graph/rules/*` alone
    while `mutation.targets` named three, so `doc_quality.py` and `doc_shape.py` were
    unreachable by any run rather than awaiting one — and the job's
    `--only src/beadloom/graph/rules/` told the single command that reports the gap to
    print them as "not judged by this run". Three settings had to agree and one test
    checked one direction of one pair. **Declared: four of the five**, by measured mutant
    count — `role_duties.py` 324, `typed_surface.py` 241 (excluded), `shell_targets.py`
    146, `guards/surface.py` 136, `waves/derivation.py` 98. The line is where the I/O
    sits, not whether there is any: the four confine it to named collectors at the module
    edge, which is `doc_quality.py`'s shape, while `_resolve_path` in `typed_surface.py`
    decides its answer with `glob`/`is_dir`/`is_file`/`exists` interleaved with the
    logic. **Measured, then declared:** 1 711 mutants over the six file targets, 1 314
    killed, 4 timeout, 393 survived, 0 with no covering test — 77.03% in 9 min 34 s with
    six workers on Darwin arm64 / CPython 3.13.7. With S3's unchanged 96.19% over
    `graph/rules/` the whole declared scope is 5 155 of 5 700 = 90.44%. The job therefore
    runs the runner **twice and scores twice**: one aggregate floor would have let the
    rules slice fall from 96.19% to 94.1% before tripping, so the slice keeps its own
    0.95 and the whole scope is judged at 0.89 in a step marked `if: always()`. The pool
    is derived the same way S3's was — one coverage pass, 64 covering files, 43 new — and
    its two exclusions were measured in the room they fail in rather than reasoned about:
    a `git archive HEAD` room passed 42 of 43, and the actual `mutants/` copy then failed
    a 43rd that the cheaper room had passed. Filed BDL-UX #246: `beadloom ci` checks
    whether a mutant COULD run at a declared path and never whether one DID, and
    `beadloom mutation --only` prints "this run did not cover it" and "no run has ever
    covered it" as the same sentence — an adopter has no equivalent of the repository
    test that closes it here. **The workflow has now run on a GitHub runner** — run
    33851288658, 2026-09-04, success, the first in this project's history, and its own
    header had said that run was the outstanding verification. It measured two numbers
    that moved decisions: 1 h 29 min 18 s against 54 min 55 s on the macOS machine, a
    factor of 1.63, so `timeout-minutes` goes 180 -> 240 for a scope projected at ~110
    min; and 95.56% against 96.19% over identical mutants — 25 more survivors, which is
    the room — so S3's 0.95 floor was leaving 0.56 points of headroom rather than the
    ~1.2 it was set for, and the rules floor is recalibrated to 0.94 in the room the job
    actually enters. The run also printed the phantom verbatim on the day it was fixed:
    `Not judged by this run: doc_sync/doc_quality.py, doc_sync/doc_shape.py`. And the
    schedule is not punctual: zero runs existed 4 h 39 m after the `17 3 * * *` slot,
    and GitHub created the first cron run at 07:57 UTC.
  - [x] `0mdo.47` / **the other half of review Major 3** — two `scope-check` tests pinned a
    literal path list against a document the RFC obliges to grow every slice, so `0mdo.44`'s
    append went red on the one event that is guaranteed to happen and is never a defect. The
    replacement asserts MORE than the shape it replaced, 54 cases → 64, 96% over the modules under
    test: five cases against the LIVE table stated as relations (findings non-empty; a subset of
    the commit's own paths; every finding names an axis the document declares; every finding names
    the document that ruled), six against a pinned six-row excerpt whose commit, paths and index
    are all still real, and a guard holding the excerpt to the live document on
    `(axis, node, in_scope)` with a failure message addressed to whoever appends S5's rows.
    **The rejected alternative is the reusable sentence:** deriving the check's INPUT from the
    document is legitimate, and deriving its OUTPUT is `check_commit_scope`'s body written a
    second time — green while both copies are wrong the same way. A real mutation survivor was
    found and killed on the way: deleting `if node in scope.inside: continue` left the whole file
    green, because a kept node usually carries its own context, except where the section's context
    and the path owner's come from different reads. **What the bead's own diagnosis got wrong,
    recorded for S5:** "a larger approved set means fewer paths fall outside" is not what happened
    — `.44` narrowed more than it widened, and `scope-check`'s findings on one pinned commit went
    1 → 6. Green in a clean room over 1 file at `room-beadloom-0mdo.47` (8 628 passed; the 1
    failure is the room's stated property — a `git archive` room carries no doc-sync verification
    records). **As this wave's gate owner:** green on the tree — 8 819 passed, 0 failed, 337 s,
    Darwin arm64 / CPython 3.13.7, 0 of the 21 declared rooms. A first tree run had reported one
    failure that then passed in isolation and in the re-run: `.45` wrote `flow.yml`,
    `pyproject.toml` and a test file inside that 431 s window, so the population a long run
    measures is not a fixed tree while a neighbour is writing to it, and "the tree was red" would
    have been a true sentence about a tree that never existed as a whole.
  - [x] `0mdo.36` — tech-writer, this pass. `sync-check` was rc 0 before it started and the file
    and symbol pairs were all `ok`, so the drift it worked was the other kind: prose that stayed
    behind while a `reindex` reset the baseline under it. `docs/services/cli.md` carried the
    pre-`0mdo.43` ignore-block invitation, described `--liveness` with no surface report at all,
    stated the path rule as a literal backslash, said a wave of one prints `not_applicable` for
    three media, and did not mention the duty check or the declared-axes comparison. Those are
    repaired; the PRD's three broken scenario references are repointed at the scenarios the suite
    holds — the mapping `0mdo.44` named and deliberately left for someone with the standing to
    take it — and PLAN's slice statuses now come from the tracker rather than reading `Pending`
    for four shipped slices.
- [ ] S5 — the tracker adapters
- [ ] S6 — the flow's documents and roles

## What is in `main` now

Four commands, each of one shape — derive the answer, name the reason, name what was not
reached:

| Command | Answers | Refuses to |
|---|---|---|
| `beadloom impact <path\|symbol>` | the axes a change ranges over, from the source; the seed derived under `reaches-an-effect-sink` and named | render a seedless target as an empty list — "every axis below the seed is unresolved, not empty" |
| `beadloom scope-check` | whether a commit touched a path outside the work item's declared axes, naming which axis | fire on a commit inside them |
| `beadloom mutation` | the score against the declared scope | turn an absence into a number — a missing counter is reported, not read as zero |
| `beadloom rooms` | the room census derived from `ci.yml` and `pyproject`, and which rooms this run entered | omit the reason a room was not entered |

Plus: the `Explore` role composed by `role-composer` and available as `subagent_type:
explore`; `## Axes` a required section of BRIEF and RFC, with an empty section a finding and
a row without a scope decision a finding; `review-brief` reporting reachability per channel
and naming the launch prompt as one nothing can inspect.

## Decisions taken at planning, not to be re-litigated per bead

- **Q1** — the axes are DERIVED by `beadloom impact`; the document records the derivation and
  the
  human's scope decision; the bead's `refs:` is generated from the document. A disagreement
  between the three is a finding.
- **Q2** — the commit-scope check compares against the WORK ITEM's axes, not the bead's.
- **Q3** — ANSWERED BY MEASUREMENT: the mutation job runs **nightly**. 54m55s over 3 989 mutants
  at 96.2%, against the ~16-28 runner-minute budget that withdrew `tests-windows`.
- **Q4** — External `bd` findings are answered by deriving our own call sites, not by a wrapper.
- **Q5** — `Explore` is a role file composed by `role-composer`, not a mode.
- **Beads are created per slice**, when the preceding slice's review closes.

## S4, as created

`beadloom-0mdo.12` is the slice and depends on every row below, so it cannot close while one
is open. Eight dev beads, then test → review → tech-writer, created 2026-09-03 under the
epic's rule that beads are created per slice once the preceding slice's review closes — and
then the four fix beads the review's first pass produced, created 2026-09-04. Fifteen beads
over eight waves.

| Bead | What it is | P |
|---|---|---|
| `0mdo.27` | a duty declared for a role is carried by that role's composed core, checked in BOTH directions — the machine half | P1 |
| `67t1` / **#228** | the clean-room duty reaches roles only through the coordinator's typing — the duty half; depends on `.27` | P1 |
| `0mdo.31` | **#170**, the entry this slice is named after: the guard binds `Edit\|Write\|NotebookEdit` and a write through `Bash` fires nothing. Three pieces, and the third — report the SURFACE, not the firings — is the real one | P1 |
| `0mdo.32` | the residue of `mr2l.81`: the commit gate judges staged paths, so a neighbour's hunk inside a file the committer touched reads clean. Wire S1's `scope-check` into the hook | P1 |
| `0mdo.33` | the residue of `mr2l.60`: the refusal rule is a literal backslash, so on Windows every edit is MALFORMED and the stated reason is false there. `os.sep`/`os.altsep` + a shape gate | P2 |
| `gsal` / **#231** | the commit hook type-checks an undeclared surface (970 errors in 90 files), discards mypy's output, never blocks; a real `src/` error prints the same sentence | P1 |
| `en0x` / **#232 + #234** | `waves` plans from an AUTHORED `refs:` line, so two beads editing one document read as independent. Measured: `.21` and `.26` both edited `docs/services/cli.md`, 0 findings. Also #234: the printed remedy did not follow the cause as far as the reason did | P1 |
| `nn4c` / **#233** | the read-only guard test attributes by TIMING, and a `bd` export burst lands inside the measurement window and misses the control window. Least reliable exactly when the flow is most parallel | P1 |
| `0mdo.34` | test — the surface as a shape, never a spelling | P1 |
| `0mdo.41` / **#239 + #241** | two of the slice's instruments answer one question in opposite ways and neither says which it answered; and an empty write-path population prints as `0 of 0 ... bound` | P1 |
| `0mdo.42` / **#240** | the commit hook's typed leg is gated by a hand-written `^(src\|tests)/` regex and prints nothing at all on a flat-layout project | P1 |
| `0mdo.35` | review | P1 |
| `0mdo.43` / **review Major 1** | the firing record persists every agent shell command line verbatim, and the shipped ignore block invites teams to commit it | P0 |
| `0mdo.44` / **review Majors 2 + 3** | the derivations were performed and never reached the documents — S4's axes and its one behaviour-bearing criterion | P1 |
| `0mdo.45` / **review Major 4** | five new pure domain cores and no mutation claim over any of them | P1 |
| `0mdo.47` / **review Major 3** | two `scope-check` tests pin a literal path list against a document the RFC obliges to grow every slice | P1 |
| `0mdo.36` | tech-writer | P1 |

**`mr2l.81`, `.60`, `.82`, `.92` were closed 2026-08-31 in a tracker cleanup as UNFINISHED work,
not as done** — the close comment says so on each. `.82` and `.92` came back sharper as
`gsal` and `nn4c`; `.81` and `.60` are carried here as `.32` and `.33`. A closed bead whose
work never happened is the same false green this epic is about, one layer up in the tracker.

**`.32` is mostly wiring now, and that is S1 paying off.** `.81` had to design the mechanism it
needed; `beadloom scope-check` shipped it in S1, and CONTEXT Q1/Q2 already answered two of
the four questions `.81` said had to be settled before building. What is left is the exempt
set (measured against real commits BEFORE it goes live), warn-not-block, and `unjudged` for
an unattributable commit.

## What S5 and S6 inherited from S4, and why each was routed out

S4 closed nine BDL-UX entries: the six its dev beads were created for — #170 (`0mdo.31`), #228
(`67t1`), #231 (`gsal`), #232 and #234 (`en0x`), #233 (`nn4c`) — and three it both filed and
fixed, #239 and #241 (`0mdo.41`) and #240 (`0mdo.42`). It filed twelve new entries in all, #235
through #246. The nine that remain were routed OUT deliberately. This is the part a resumed
session is least able to reconstruct, because the
reasons live in bead descriptions and in the issue log and nowhere together.

**Inherited by S5** (`0mdo.13`, which depends on `0mdo.12` and on the bead below):

| Entry | Bead | Why it is not S4's |
|---|---|---|
| **#237** — `bd merge-slot acquire --wait` returns at once and its holder is indistinguishable from its claimant | `0mdo.39`, P0, open | It is a `bd` adapter defect, which is exactly S5's subject, and CONTEXT Q4 already decided the shape of the answer: derive our own call sites, never wrap `bd`. Fixing it inside S4 would have built the wrapper Q4 declines. |

**Inherited by S6** (`0mdo.14`, which depends on S5 and on the four beads below):

| Entry | Bead | Why it is not S4's |
|---|---|---|
| **#235** — the clean-room convention names a fixed directory, so two agents in one wave build one room and both call it clean | `0mdo.37`, P1, open | The free half shipped in S4: `beadloom waves` now prints `room-<bead-id>` per bead and the duty text carries it. What is left is a command that CREATES the room and refuses a directory it did not create empty, which is new surface rather than a correction. |
| **#236** — a clean room's verdict is decided by which optional extras it installed, and the convention never names them | `0mdo.38`, P1, open | Measured at 0, 1 and 82 mypy errors over one code base. The durable form is `beadloom rooms` reporting an extra-set dimension beside interpreter and platform, which is a change to S3's instrument and not to S4's guards. |
| **#238** — nothing compares the ignore block on disk against the block this version emits | `0mdo.40`, P2, open | The INSTANCE was fixed in S4: this repository's `.gitignore` now carries the shipped glob. The CLASS is a new `config-check` leg. Splitting them is what keeps a repository repair from reading as a product fix. |
| **#244** — a second markdown table in `## Axes` contributes its header row as an approved node named `Node` | `0mdo.46`, P1, open | Worked around in S4 by keeping one table, so no commit was judged against a phantom node. The parser fix touches `read_axes_section`, which S1 owns and which `0mdo.47`'s pinned excerpt now guards. |
| **#245** — the `unguarded_axis` remedy, followed literally, gives every bead one scope and collapses every wave to a wave of one | `0mdo.46`, P1, open | The VERDICT is correct and shipped; only the advice beside it is wrong. #244 must land first — #245 cannot be judged honestly while #244 injects a node nobody wrote. |

**Inherited by S6 with no bead of its own:**

- **#242** — a subagent's launch context carries a `git status` snapshot that is stale by
  construction, and `en0x` published a sentence from it and withdrew it (`f45dd62`). Recorded as
  a NOTE on `0mdo.14` rather than as a bead, because the answer is ours and not the harness's:
  the role protocol states that a tree fact is derived at the moment it is stated, and
  `0mdo.27`'s duty mechanism can carry that as a declared duty. It needs no separate DAG node.
- **#243** — a room that is refreshed rather than rebuilt manufactures a stale-doc failure
  shaped
  exactly like a defect. No bead: #235's proposed command — create the room, refuse a directory
  it did not create empty — closes #243 as well, so a second bead would be a second thing to keep
  in step. The workaround in use is to rebuild the room after any edit, never to re-copy.
- **#246** — a declared mutation target that no run ever covers passes every green Gate.
  `0mdo.45` closed the instance (`[tool.mutmut] only_mutate` now names every declared target and
  `tests/test_mutation_runner_scope.py` asserts both directions), and the CLASS — Beadloom
  recording the run it just judged, so the Gate can report a target whose last measurement is
  absent or stale — is routed to S6 with no bead yet. **This is the one gap in the routing:** an
  adopter has no equivalent of the repository test that closes it here, and nothing in the DAG
  currently holds that.

## Review findings left open, unassigned

`0mdo.35` closed at 0 critical and 0 major. Ten Minors and three Nitpicks stand, all author's
discretion and none blocking. The tech-writer pass (`0mdo.36`) closed the two that were
documentation defects and touched no code:

- **M-c** — ACTIVE.md carried no row for `.43`, `.44`, `.45` or `.47`, no Progress entry for
  `.44` or `.47`, and a Current Bead block five commits out of date. **Closed by this pass.**
- **Minor 9** — the PRD's acceptance boxes were all unticked after four slices, and PLAN's rows
  read `Pending` for nine shipped S1 beads and three shipped slices. **Closed by this pass**, on
  a measurement: 232 of 232 acceptance scenarios pass. Three references that named scenarios the
  suite does not hold were repointed at the same time.

The rest are code or test findings and stay open. A doc edit must not make one of them look
addressed, so each is named with what it still needs:

- **M-a** — `tests/test_a_commit_is_judged_against_the_declared_axes.py`'s pinned-row guard
  fires
  on an EDIT or a REMOVAL and not on an ADDITION that flips the pinned commit's answer, which is
  the one event S5 guarantees. Needs one more assertion: no live row names a pinned node with the
  opposite decision.
- **M-b** — `onboarding/ignore_block.py`'s rewritten `why` does not reach a project that already
  carries the block, whose `guard-firings.1.jsonl` may still hold command lines. This pass
  DOCUMENTED that limitation in `docs/domains/onboarding/components/ignore-block/DOC.md` and in
  `docs/services/cli.md`; the code half — `ensure_ignore_block` reporting a block whose entry text
  predates the change, or a release note — is untouched.
- **M-d** — the 25-mutant CI/local delta is labelled "the room" and not diagnosed. The two
  survivor sets are one set-difference apart, because the job already uploads `mutants/**/*.meta`
  for 14 days. If those 25 are mutants no CI run can kill, the honest instrument is a named
  exclusion rather than a lower floor.
- **Minor 4** — `application/typed_surface.py:172-177`: `declared_typed_surface` documents
  "Never
  raises" and raises (`NotImplementedError: Non-relative patterns are unsupported`, re-measured on
  3.13.7). It is in `_resolve_path`, the function cited as the reason `typed_surface.py` sits
  outside the mutation scope.
- **Minor 5** — `application/guards/shell_targets.py`: the `-t` family names a SOURCE file as a
  write target. `read_shell_command("cp -t /dest a b")` -> `('b',)`.
- **Minor 6** — `typed_surface.py:334` documents `None` and `[]` as different facts; the only
  caller does `if not values: continue`.
- **Minor 7** — `onboarding/role_duties.py:353` says "over merged declarations so one duty
  yields
  one verdict"; `declarations` is a flat list.
- **Minor 8** — `role_duties.py:171`: `prefix` is `""` in both tuple entries and concatenated to
  no effect.
- **Nitpicks** — `typed_surface.py:135` rebuilds `set(inside)` per candidate; `describe` at
  `:159-168` says "staged Python file(s)" about whatever it was handed; `waves/derivation.py` and
  `services/commands/typed_surface.py` place the `# beadloom:` annotation after the module
  docstring.

**One observation, not a finding.** `tests/test_db.py::test_no_resource_warning` passes and
emits `PytestUnraisableExceptionWarning: ResourceWarning: unclosed database` on a full-suite
run. It does not reproduce in isolation and the review checked that it is not `.47`'s. A test
named for the condition it detects, reporting that condition as a warning, is worth someone's
attention.

## Standing conventions every launch prompt carries

**#228 landed 2026-09-04.** The first two below are no longer prompt-level: the shipped
coordinator command declares the `clean-room` duty for all five roles,
`roles/core/_rooms.md.txt` and its Russian twin carry it, and `config-check` blocks on either
half going missing. The room's path carries the bead id (#235) and `beadloom waves` prints it
per bead for every wave. The rest are still carried by the prompt and by nothing else:

- **"green in a clean room over N files" and "green on the tree" are different claims** — report
  them in different words (BDL-UX #181).
- **A verdict names the room it was taken in.** `beadloom rooms` says a local run is in 0 of the
  21 this project declares.
- **Check filenames before staging** — a new test file on an existing path deletes its scenarios
  and the suite goes green over the wreckage (BDL-UX #224, unfixed).
- **Checkpoint every few steps.** Nine agents across the two epics were cut off mid-work; the
  checkpoints made every resume cheap and their absence made one expensive.
- **`beadloom waves` before every wave**, and commit the tracker export first — it reports a
  path
  owned by no bead in the plan as a working-tree finding, correctly, twice so far.
- The wave's **gate owner** measures the combined tree; everyone else reports their own room
  only.

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

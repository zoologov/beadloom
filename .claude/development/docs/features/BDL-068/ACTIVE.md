# ACTIVE: BDL-068 — The flow's rules are advice; make them instruments

> **Last updated:** 2026-09-08
> **Phase:** Development — S1-S3 merged; S4 complete on the branch (dev, test, review and
> docs), unmerged; S5 complete on the branch, its review OK on the second pass and its docs
> pass landed. S6 has started and runs in full: its axes bead `.72` closed, `.60` ran alone at
> the front by coordinator decision, and wave 2 — `.37` and `.68` — is complete.

---

## Current Bead

**Bead:** `beadloom-l9ee` — BDL-UX #260, the shared write and the condition an ADR needs. S6,
alone, and its own combined-tree gate owner. The bead is a DECISION the coordinator asked for
and the previous agent wrote; this run re-checked its measurements as evidence rather than
executing them as instructions, and corrected it on two points.

**THE 2.5% WAS THE RIGHT NUMBER ABOUT THE WRONG REGION.** The bead measured `ACTIVE.md`'s
bead-status table — 35 of 1427 lines, re-measured today and unchanged — and concluded that
composition removes 0% of the collisions. True of the table. It never asked where in the file
the collisions were. The `Progress` section is lines 64-1122: **1059 of 1427 lines, 74.2%**,
and it is a per-BEAD append, one sub-bullet per bead. Both `ACTIVE.md` collisions of this epic
are in it. So the writer unit is the bead, and one-writer-per-file has a shape here that the
table measurement hid. Not taken: it is `active-table`'s surface and this bead's derived axis
is `issue-numbers` alone.

**AND `beadloom-0mdo.66` HAS ANSWERED THE `LATERAL MOVE` OBJECTION, so the log migration is
declined on the bead's own standard.** The objection rested on one piece of evidence — commit
`27db92b`, two agents allocating one number — and `.66` closed that class. Re-measured: the log
took 17 commits at +248 / -4 with no repair commit, against `ACTIVE.md`'s 22 at +735 / -395.
Realised collisions across this epic are 3 in per-bead prose and 1 the log's number, now fixed,
so moving 241 entry bodies would have prevented **0 of 4** — the same test the bead used to
reject options 3 and 4, turned on its own recommendation. What protects a body meanwhile is the
ledger, not the layout: a claim is a separate file a lost write cannot take with it.

**WHICH IS WHERE THE DEFECT WAS, AND IT IS FIXED.** That protection reaches only entries at or
above the ledger's floor, and the verdict never said so. Measured: `240 entr(ies), 5 claim(s),
floor 262` then `No duplicate, unwritten or unclaimed number` — a clean list over 5 of 240,
because `_ledger_findings` skips every entry below the floor. Filed as **BDL-UX #267**, allocated
through the allocator it is about, and closed in the same commit:
`IssueNumberReport.entries_below_floor`, a `PARTLY CHECKED` clause on the Gate line, and the
unaccounted numbers named rather than counted. Coverage, not a finding — no tree reddens.

**NEITHER THE ADR DIRECTORY NOR THE `decision` DOC KIND SHIPS, on the bead's own condition.** A
decision record must be a doc-code pair so it can go stale, or it is the issue log in a
different folder. That pairing is `doc-sync` plus `graph` machinery and this bead's axis is
`issue-numbers`; shipping the directory without it is the regression the condition names. So
neither half ships, and the three decisions are recorded in `CONTEXT.md`'s table, which
`doc-quality` already judges for a reason that explains why.

**Previous bead:** `beadloom-0mdo.81` — BDL-UX #266, the clean room's missing `.git` cost the audit a
subject. S6, alone, and its own combined-tree gate owner. Every clean-room Gate run on this
repository had been rc 1 since `.63` landed, on one line of one document, and four beads
reported it as briefed and attributed rather than chased.

**THE ANSWER WAS WRONG, NOT THE QUESTION.** `version_subjects.py` derived the subject `git`
from `(project_root / ".git").exists()` and read the absent marker as a denial. An absent
`.git` cannot tell a project that never used git from an export of one, so the derivation now
records `git` as UNRESOLVED: it stays in the vocabulary, still wins the scanner's attribution
walk, and `compare_facts` routes its mentions to `AuditResult.unjudged` — a population apart
from `attributed`, because the two are exempt for different reasons. `attributed` is a subject
this project confirmed; `unjudged` is a subject this DIRECTORY could not confirm, and merging
them would hide a directory that cannot see its own environment behind a rule that works.

**Unresolved is not silence, and that is the half that keeps the repair from being the
workaround.** The `beadloom ci` docs-audit line names it (`COULD NOT JUDGE 5 version token(s)
naming git — unconfirmed here`), the human report gives the reason, and `--json` carries
`unjudged_versions`, `unresolved_version_subjects` and `summary.unjudged_version_count`.

**The declared list was not taken, and `.beadloom/config.yml` now says so where a reader would
reach for it.** A `docs_audit.subjects` entry for `git` is one line and is the thing `.63`'s
design removed; this project has shipped a second hand-written vocabulary twice already
(`mr2l.82`'s typed surface, and the `^(src\|tests)/` gate `.42` found in front of its
replacement). What changed here is what an absent source MEANS, not what the vocabulary holds:
the one name is the one that was already hard-coded, now behind `_ENVIRONMENT_SUBJECTS` whose
probe answers "yes" or "cannot tell".

**The room was weighed and declined, and the reason is that it fixes fewer directories.** A
marker written by `beadloom clean-room` would repair the rooms this command builds and no
other export — an sdist, a vendored copy, a `COPY` of tracked files into an image all reach the
same derivation, and an adopter never runs this command at all. A room that carried the real
`.git` would also stop being the room: `sync-check` would gain a baseline the room states it
does not have. The room's caveat was left alone on purpose too — the audit's own line reports
the declined token at the place the measurement happens, and a second sentence in the room's
prose would be an authored copy of a derived fact, which is the drift this epic exists to
remove.

**MEASURED IN BOTH PLACES, BEFORE AND AFTER.** Clean room at HEAD with **zero** carried files:
`beadloom ci` rc 1 with exactly one `::error`,
`active-table/DOC.md:227 doc-fact-stale '2.49.0' vs '3.0.2'`. After, over the carried set: rc 0,
zero errors, and the docs-audit line names the five tokens it declined. The tree before AND
after: rc 0, zero errors, `docs-audit PASS: 19 mention(s) fresh` both times, with `unjudged`
empty there because a working tree confirms `git`. The room's green was not bought with the
tree's blindness, and `TestTheDefectVerbatim` in `tests/test_unjudged_versions.py` pins both
directions: a `git` release in a `.git`-less directory is not stale, and this project's own
version in that same directory still is.

Closed as `a69aa06`. `bd close --suggest-next` named `.69` and `.14` as newly unblocked and
`bd ready --limit 0` lists neither, which is the tracker-answer shape this flow already
documents: the suggestion is a candidate list that does not re-check the other blockers.

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
- [x] **S5 — the tracker adapters, where `bd`'s behaviour meets ours**
  - [x] `0mdo.58` — S5's axes, derived at the slice's start.
  - [x] `0mdo.51` — **the slice's mechanism bead**: the derived `bd` call-site population,
    homed at node `bd-seam` per CONTEXT Q4 (derive our own call sites, never wrap `bd`).
    `invocations.py` holds one grammar over two channels — a text channel anchored on COMMAND
    POSITION, which returns 266 invocations and no prose where an unanchored sweep also reports
    `bd verifies` and `bd checks the`, and an AST channel that resolves module-level constants
    so `guard_probes`' most careful call reads as resolved. `assumptions.py` holds the measured
    table and four verdicts — `secured`, `unsecured`, `holds`, `unmeasured` — each pinned to bd
    1.0.4, with a test that fails when a different `bd` is installed. `population.py` holds four
    roots and the four regions the derivation cannot reach, named with their reasons. Findings:
    `bd ready` is unsecured on truncation at 40 sites and this flow calls it authoritative (its
    cap is 100, announced on stderr, measured 100 of 135); 48 sites are unmeasured and they are
    `bd swarm` and `bd gate`, the two commands the coordinator orchestrates every wave with; and
    every `bd list` call in this project's Python names both default filters, so #187 is
    answered at the consumer while 42 prose sites are not. Three python sites are unsettled and
    all three are owned — two by `.53` (#171), one by `.52` (#97). BDL-UX #253 needed a third
    suppression triple for one sentence-shape, which is the evidence it is a class. `.52` has
    since closed both of its own: the `close` site is fixed and the prose is answered by a
    shared fragment. The `bd ready` truncation sites are NOT swept and the reason is recorded
    under that bead.
  - [x] `0mdo.54` — **#207 + #210**, the two findings of this slice that are entirely ours.
    `application/active_table.py` became a PACKAGE of five modules, moved with `git mv`, one
    responsibility each: the id a row names, the markdown table, the state a Status cell
    states, the reconcile core, and what a reconcile may stage. **#210:** `undecorate` reduces
    a Markdown link to its text and deletes every code-span and emphasis character wherever it
    stands — only backtick and asterisk, because an underscore can appear in a tracker id and
    stripping it to read `_.22_` would corrupt `proj_x.22`. `resolve_row_bead_id` returns a
    `RowId(bead_id, shape, reason)` rather than a 2-tuple, because the shape IS part of the
    answer and a caller that parses the reason string to count is a second reader of one fact.
    Measured on this repository: 211 → 238 resolved, 118 → 91 unresolved reported as three
    named shapes, 0 rewritten in both runs. The 27 gained are BDL-067's whole table.
    `unlisted_beads` named the 79 beads no row of their epic's table carries and writes none of
    them — a report the S5 review then found contradicting the run's own row diagnosis, and
    which `0mdo.61` split in two below. **#207:** `--stage` re-stages only paths whose index entry differs from `HEAD` — what
    a commit actually contains — and names the rest under a fixed `  withheld: ` line; an
    unreadable scope stages nothing and says so, because an unknown scope is not an empty one.
    **The noise question was measured before it shipped:** `bd export` moved
    `.beads/issues.jsonl` in SIXTEEN of the sixteen commits on this branch, so the naive fix
    would print one line on every commit. Under `--stage` the export therefore runs only when
    the commit already carries it. **And the shell was executed, not just asserted** — the
    shipped `_HOOK_COHERENCE` block was extracted and run against a fake `beadloom` on `PATH`
    in both directions: two withheld lines printed, none was silent. One defect found in the
    report I was extending: `--check` reconciles a throwaway copy and every path it printed
    pointed inside a directory deleted before the report was shown. Red verified by mutation in
    both halves — `undecorate` reduced to `strip()` fails 19 of 53; the old staging answer fails
    7 of 77.
  - [x] `0mdo.53` — **#171 + #165**, the bead-creation path. `bd_seam/creation.py` is the one
    place a bead is created: `PlannedBead` names beads by key and holds `depends_on` as
    plan-local keys, `graph_plan` writes the document `bd create --graph` accepts, and
    `allocated_ids` / `created_id` read bd's JSON answers instead of scraping `--silent`
    stdout. The CONVENTION is enforced where the divergence is created — `graph_plan` refuses a
    plan whose title states a bead number, because at creation there is no id to agree with and
    the number is a promise nothing can check. It reads `title_references`, now public in
    `waves/media_checks.py`, so the writing half and the comparing half share ONE grammar.
    **Measured red then green on the derived report:** `allocated-id` 17 unsecured → 0 (15
    secured) and `intended-id` 11 unsecured → 0 (8 secured) over this repository, and all 12
    Python sites settled — `test_the_python_sites_nothing_settles_are_the_two_that_are_owned`
    becomes `test_no_python_call_site_of_ours_is_left_unsettled` and asserts ZERO, so no number
    has to be revised to keep it honest. **One thing I nearly got wrong and it is this epic's
    own subject:** the first version put the argv behind a `graph_argv()` helper, and the
    scaffold's creation site vanished from the population entirely — not unsecured, ABSENT,
    because `invocations` resolves a list literal handed to `run_bd` and cannot follow a call.
    The literal is spelled at the call site with the reason beside it and a test reddens if it
    is tidied back. `.52`'s backticked-mention limit hit for a THIRD time, in my own sentence
    explaining #171; rewritten to take the command out of command position rather than
    appending a flag to a mention. Green in a clean room over 22 files (8 976 passed, 57
    skipped, 1 xfailed, 1 failed — `test_all_new_node_pairs_are_fresh`, reproduced RED at HEAD
    in `room-head-baseline-53`, a room of the same shape, rather than inherited from `.52`).
    **As its own wave's gate owner**, green on the tree: 9 022 passed, 11 skipped, 1 xfailed;
    `beadloom ci` rc 0 read in the foreground without a pipe; `ruff` clean; `mypy --strict`
    clean over 269 files against all four declared interpreter targets. Every verdict taken in
    Darwin arm64 / CPython 3.13.7, 0 of the 21 declared rooms entered.
  - [x] `0mdo.52` — **#187 + #97**, the tracker's answers at our own call sites.
    `bd_seam/answers.py` is the run-time half of `.51`'s derivation: `coverage_of(argv, stderr)`
    reads bd's own truncation notice and the argv's population flags, and
    `confirmed_suggestion(close_stdout, ready)` splits `--suggest-next`'s candidates by what
    `bd ready` lists. Both notice forms were measured rather than quoted — `Showing 50 issues;
    more results matched…` from `bd list` against this repository (50 of 843) and `Showing 100
    of 120 ready issues.` from `bd ready` against a rig grown past the cap with
    `bd create --graph`. The coverage is `as-asked` and deliberately not `complete`, because
    `bd list --status open` names a population bd honours and every open bead is not every bead.
    The derivation learned a securing shape no flag can express: `unblocked-is-ready` is
    `secured` when the ARTIFACT that instructs the suggestion also names `bd ready`, judged in
    two passes so a confirmation written above the call counts too, and the verdict states that
    whether the two answers are actually COMPARED is not something a derivation of call forms
    can see. **Measured red then green on the same derivation:** 25 `unblocked-is-ready` and 2
    `complete-population` unsecured over this repository before, 0 and 0 after, across a
    population that grew 278 → 348 sites. The concrete defect is closed —
    `test_the_python_sites_nothing_settles_are_the_two_that_are_owned` replaces the three-site
    version, and the two that remain are `.53`'s. **#97 re-measured in twenty-three separate
    rigs: sixteen false positives, `bd ready` correct in all twenty-three.** Green in a clean
    room over 40 files, and **as its own wave's gate owner**, green on the tree: 8 980 passed,
    11 skipped, 1 xfailed, `beadloom ci` rc 0 read in the foreground without a pipe, `ruff`
    clean, `mypy --strict` clean over 268 files against all four declared interpreter versions.
    Every verdict taken in Darwin arm64 / CPython 3.13.7, 0 of the 21 declared rooms entered.
    BDL-UX #253 needed a FOURTH suppression triple for one sentence shape.
  - [x] `0mdo.39` — **#194 + #237**, the landing lock. A fifth shared medium, `landing-order`,
    stated in `waves/media.py` and checked in `media_checks.py` over a new `waves/landing.py`
    that derives every instruction of the lock in the composed flow artifacts and judges it by
    the FLAGS of the invocation, never by the prose around it. Three defects, each measured on
    bd 1.0.4 before it was encoded (`anonymous-holder`, `unguarded-release`, `queue-only-wait`),
    plus `unknown-form` for a subcommand the derivation has not measured. The fix itself is
    prose, because none of the call sites is Python: the shipped `coordinator.md.txt` and
    `CLAUDE.md.txt`, this repository's project layer, and a new SHARED role fragment
    `roles/core/_landing.md.txt` carrying the `landing-lock` duty that `config-check` now blocks
    on — the mechanism `0mdo.27` built in S4, applied to the rule that made #194 rot in prose
    for nine days. **Measured red then green on the same derivation:** 8 sites and 6 defective
    over the flow artifacts at HEAD, 18 sites and 0 defective after. Green in a clean room over
    28 files, and **as its own wave's gate owner**, green on the tree: 8 876 passed, 11 skipped,
    1 xfailed, `mypy --strict` clean over 262 files, `beadloom ci` rc 0 in the foreground
    without a pipe. Every verdict taken in Darwin arm64 / CPython 3.13.7, 0 of the 21 declared
    rooms. Filed BDL-UX #253.
  - [x] `0mdo.61` — **S5 review Major 1**, one run making two statements about one row. The
    reconcile filled `seen` only from rows that RESOLVED, so a row it could not read handed its
    bead to "no row in their epic's table" while the same run printed that row under
    `bead-and-text` or `more-than-one-bead`. A reader acting on the message adds a row that is
    already there — the class `row_ids.py`'s own docstring exists to remove, in the package that
    shipped the sentence. **Both fixes the reviewer offered were needed and only one of them is
    a choice:** carrying the id the shape already found is the MECHANISM either answer needs,
    and the question is what the run then says. Folding those beads into `seen` would leave 38
    of them in no number the run prints, which is this epic's own subject one level up, so the
    bead-keyed report is SPLIT: `beads_named_by_an_unresolved_row` (fix that cell) and
    `unlisted_beads` (add a row). **Measured before and after on this repository's real tables,
    `active-sync --check --json` at `27db92b`:** 79 carried by no row → 41 carried by no row and
    38 named by a row this run could not read, 41 + 38 = 79, and the row-keyed numbers do not
    move (329 read, 238 resolved, 91 unresolved, 0 rewritten). No bead left the report and none
    entered it. A range is deliberately not expanded: `beadloom-eeo.3..8` names `.3`, and `.4`
    through `.7` stay in "carried by no row" because the numbers between the endpoints are ids
    the table does not write. Four acceptance scenarios and 21 unit tests, red first. In a clean
    room over 11 files (`room-beadloom-0mdo.61`): 9 080 passed, 57 skipped, 1 xfailed, 1 failed
    — `test_all_new_node_pairs_are_fresh`, reproduced RED at HEAD in `room-head-baseline-61`, a
    room of the same shape, rather than inherited from `.53` and `.54`, which report the same
    failure. **As its own wave's gate owner**, green on the tree: 9 127 passed, 11 skipped, 1
    xfailed, `mypy --strict` clean over 274 files against all four declared interpreter targets,
    `beadloom ci` rc 0 in the foreground without a pipe. Darwin arm64 / CPython 3.13.7, 0 of the
    21 declared rooms.
  - [x] `0mdo.62` — **S5 review Major 3**, seven pure cores declared nowhere after six correct
    deferrals. A declared target with no run reports `mutation-target-unmeasured`; an UNDECLARED
    core reports nothing at all, so the epic that exists to stop an empty population reading as a
    passing one was shipping seven cores into exactly that state in its own configuration. **The
    STRONGER outcome was taken and no target is excluded on cost**, because the cost was measured
    rather than projected: the seven run in **36 min 35 s and score 83.64%** — 764 mutants, 639
    killed, 125 survived, 0 unrun. **The count is the wrong cost unit and that is the finding**:
    764 mutants is 13.4% more mutants and eight times the cost per mutant, because
    `invocations.py` and `assumptions.py` carry ten covering test files each where `creation.py`
    carries two. Affordable anyway — scaled by the 1.63 the runner measured, 60 min, taking the
    nightly to a projected 171. **Two settings the widening had left behind moved with it**: the
    aggregate floor was re-derived (89.98% → 89.23%, so 0.88 keeps 1.23 points of headroom where
    it had 2.00, and survives its own worst case at 88.99% if both macOS components fall the 0.63
    points the rules slice actually fell) and the timeout moved 240 → 340 by the method already
    in the file. A hypothesis was checked and REJECTED rather than reported: `test_bd_seam.py` is
    absent from the mutation pool but covers `client.py`, not the seven, and every real covering
    test is already in the pool. The three settings still agree — 36 passed across
    `test_mutation_runner_scope.py`, `test_mutation_ci_job.py` and `test_mutation_scope.py`. In a
    clean room over the 1 197 files `git archive HEAD` extracts (`room-beadloom-0mdo.62`; the
    8 624 the bead comment records is that room AFTER `uv sync`, counting the virtualenv, which
    is a count of a different thing than the sentence named — S5 review Nitpick 8); every
    verdict Darwin arm64 / CPython 3.13.7, 0 of the 21 declared rooms, so no number here is a
    claim about the nightly job.
  - [x] `0mdo.55` — **the test bead**, which cross-checked the six instruments this slice
    built against each other and found two of their claims wrong. Its declared scope is the
    union of what S5's dev beads touched, stated before the wave rather than derived after it.
  - [x] `0mdo.56` — **the S5 review**, ISSUES on the first pass (0 critical, 3 major) and
    **PASSED on the second** (0 critical, 0 major). The re-plan rule the owner armed fires on a
    second ISSUES verdict on one slice; this was S5's first, so it did not fire. The reviewer
    re-checked boundaries, cohesion, typing, error handling, doc freshness and the BDD
    scenarios at `f23f54d` and found them sound, and recorded that its own independence had
    been defeated before it ran: the launch prompt carried the slice's most distinctive
    conclusion in the authors' framing, and nothing in the flow counts that channel.
  - [x] `0mdo.57` — **the S5 docs pass.** `beadloom sync-check` read rc 0 and 0 stale before it
    started, which is the second instance of BDL-UX #163 recorded on `beadloom-9glj`: each
    wave's `reindex` legitimately moves the freshness baseline past sentences that have gone
    wrong. Grepping `docs/` for the symbols S5 changed found what the instrument could not —
    both language copies of the multi-agent guide and the parallel-waves guide still said a
    wave shares FOUR media where the code has five; the composed-core line counts (371/401)
    were six lines behind the shipped template (377/407); `SHARED_ROLE_FRAGMENTS` was still
    documented as `("_writing",)` in two places against the four that ship; three documents
    still named the roles as four after `explore` became the fifth; the mutation prose still
    said seven targets and 5 700 mutants against fourteen and 6 464; and three documents still
    pointed at `active_table.py` and `bd_seam.py` as single modules. The user-facing guides now
    carry the honest half as well: the merge slot orders commits and orders nothing else, and
    what keeps two agents out of one file is the disjoint scopes `beadloom waves` derived.
- [ ] S6 — the flow's documents and roles
  - [x] `.72` — S6's axes, derived at the slice's start (nineteen Python targets; the 862
    `beadloom <subcommand>` instructions in the flow's own documents recorded as `unresolved`)
  - [x] `.60` — BDL-UX #254, the verdict on a guard's own inability. Wave 1, alone and first.
    `unresolved` added as a sixth outcome; `is_unanswered` made the one predicate the liveness
    rule and the rotation summary both read; the emitted hook adapter's comment now enumerates
    the three codes an invocation through it can return. Verified by reproducing the wedge,
    applying the fix and reproducing the same state again.
  - [x] `.37` — BDL-UX **#235** and **#243**, one command. Wave 2, concurrent with `.68`.
    `beadloom clean-room <bead>` derives the room path from the bead through the existing
    `room_for`, creates the directory with an exclusive `mkdir` rather than entering one, and
    `--rebuild` replaces a room whose `.beadloom-room.json` names that same bead instead of
    refreshing it. 36 tests (11 scenarios, 16 CLI, 9 application), 97% / 100% on the two new
    modules. Green in a clean room over 16 carried files: 9 129 passed, the 1 failure the
    room's stated no-`.git` property. **Not the gate owner** — `.68` owns this wave's combined
    tree. Found by dogfooding and fixed: the invocation named `sys.executable`, which under a
    uv tool install is an interpreter with no pytest, so it now names the project's own
    `.venv`. Two adjacent findings recorded on the bead: the tracked-write guard reported a
    write nobody made (`rmtree` walks with `dir_fd`, fixed in `tests/tracked_write_guard.py`),
    and editing a shared domain README clears a neighbour's stale pairs on it.
  - [x] `.68` — BDL-UX **#213**, `decision-reason` against a claim-and-measurement table. Wave 2,
    concurrent with `.37`, and the **gate owner** for the wave. The reported cause was header
    vocabulary and the measured cause was not: a SECTION was read as one table, so the second
    table's rows were judged against the first table's column index and its header row was read
    as a row with a missing cell. `_tables()` now delimits a section into contiguous blocks, each
    led by its own header, which fixes `risk-mitigation` and `pending-in-approved` with it and
    needs no vocabulary at all. For the residual class — a measurement table that carries a
    `Reason` column of its own — `declares_decisions()` asks whether the DOCUMENT declares the
    table as decisions (a column naming the thing decided, or a section the shipped templates put
    a reason-carrying table under, derived by `shipped_decision_sections()`), and answers
    `not classified` where it does not. Measured on this repository's 259 planning documents:
    **389 rows read before, 324 judged after**, 58 rows in 12 named tables `not classified`, and
    7 rows that were never rows of any decision table gone from the population. No finding was
    removed from the present corpus, because the check reported none on it; the removed findings
    are the four on BDL-067's `ACTIVE.md` re-measured from `cd28e29c` — **4 before, 0 after, all
    four false**. 20 unit tests, 2 scenarios. Green in a clean room over 15 carried files:
    9 126 passed, the 1 failure the room's stated no-`.git` property. **As the wave's gate owner:**
    the combined tree is green — `beadloom ci` rc 0, taken in the foreground without a pipe, and
    the previously failing tree tests pass once `.37` landed. Every verdict taken in Darwin arm64
    / CPython 3.13.7, 0 of the 21 declared rooms; `mypy` clean against all four declared target
    versions, run under one interpreter.
  - [x] `.38` — BDL-UX **#236**, a room's extras. Wave 3, alone, and its own gate owner. The
    extras an environment installed are now a DIMENSION of the room: what this run has comes
    from the analysed project's distribution as the running interpreter holds it, what a leg
    installs comes from the install step its job declares, and the two are compared on what an
    environment SATISFIES rather than on what somebody typed — so a leg installing
    `dev,languages,tui,watch,graphql` also satisfies `all` and is one room, not two.
    Reproduced first, at `6c4d0a9` in one clean room over one code base: `mypy src/` gives
    **0 errors under `.[all,dev]` and 82 under `.[dev]`**, and under the second the whole `tui`
    suite leaves the run — three of its four modules skip and the fourth stops the collection.
    The dimension found a difference nobody had named on the machine that added it: this
    development environment carries `mutation`, which only `mutation.yml` installs, so it
    differs from every `tests` leg by an extra that was invisible before. **#256 is not
    absorbed and is now smaller**: its first half — a room resolving `beadloom` to the main
    tree — is already closed by `.37`'s `PYTHONPATH` invocation, verified in this bead's room;
    what remains is building the environment, and the cost of doing so was measured rather than
    assumed (`uv venv` 0.04 s, `uv pip install -e '.[all,dev]'` 3.6 s warm-cache, 160 MB
    apparent). 44 tests (5 scenarios, 39 unit). Green in a clean room over 13 carried files:
    9 206 passed, the 1 failure the room's stated no-`.git` property. **As its own gate owner:**
    the combined tree is green — 9 254 passed, `beadloom ci` rc 0 taken in the foreground
    without a pipe. Darwin arm64 / CPython 3.13.7, 0 of the 21 declared rooms; `mypy` clean
    against all four declared target versions, run under one interpreter.
  - [x] `.73` — BDL-UX **#255**, `impact` against a target it cannot read. Wave 4, concurrent
    with `.40`, `.48` and `.65`, and the **gate owner** for the wave. Found by `.72` while
    deriving S6's axes — by using the instrument for the job the slice exists to do. Reproduced
    at `c92dc78`: `beadloom impact .claude/CLAUDE.md` exited 1 with an unhandled `SyntaxError`
    out of `ast.parse` at `impact/axes.py:129`, while `beadloom impact CLAUDE.md` — a path this
    repository does not have — printed one sentence. The worse failure belonged to the more
    plausible request. The split is by what the command could not do: a file it could not READ
    is `unreadable-target` in the population that states limits, both source axes `unresolved`
    with that reason and exit 0; a path it could not FIND stays `NoSuchTargetError` at exit 1,
    and there is a test that the second line did not move. Two shapes reach that one
    `ast.parse` and both are verdicts — a suffix that is not `.py`, and a `.py` that does not
    parse, which has been reachable since the package was written. One unreadable file costs
    the answer that file and no other: a directory target holding a half-saved module still
    reports every other module's branches. 8 tests (3 scenarios, 5 unit). **The larger
    question is stated and left**: whether `impact` should derive anything FROM markdown or
    YAML needs a second derivation, and the recommendation on the record — in the SPEC and in
    CONTEXT — is that `beadloom docs audit` answers it, since it already reads non-Python
    artifacts and already verifies command mentions.

  - [x] `.65` — `beadloom docs audit` exited 1 under `LC_ALL=C` because
    `console_streams.tolerate_unencodable_output` read CPython's own C-locale `surrogateescape`
    as an operator's choice. Wave 4, concurrent with `.40`, `.48` and `.73`; **not the gate
    owner** — `.73` is. Found on `.64` while confirming the product was NOT at fault for a red
    locale leg, and it is a different class from that bead's: `.64` was about decoding `bd`,
    this is encoding to the console. Reproduced before the fix, streams separated and the exit
    code read from `$?` without a pipe: rc 1 after 1321 bytes of a partial report,
    `UnicodeEncodeError` on the `±` of the tolerance label at `rich/console.py`. `strict` and
    `surrogateescape` are now both relaxed as handlers nobody chose, and the operator's channel
    is `PYTHONIOENCODING` rather than the handler's NAME — so an explicit `:surrogateescape` is
    still honoured, which the name alone could not have granted. The direction was checked
    against the decode sites rather than made to match them: `bd_seam/client.py` and
    `guard_probes.py` choose `surrogateescape` because it is injective and no comparison can be
    given a wrong answer by a byte, and nothing at an encode site to a terminal compares
    anything. The module's docstring claim that the C locale already gets `backslashreplace` was
    false and is corrected in the module and in both documents. **No CI leg observes this and
    none will** — the `tests-locale` legs run `pytest` and `beadloom ci` runs under UTF-8 — so
    it reaches an adopter on a C-locale container, the shape of #240. 5 tests (3 in the C room,
    2 unit), each probing the room rather than assuming it. Verified in BOTH locale rooms: rc 0
    under `LC_ALL=C` and under `LC_ALL=en_US.ISO8859-1` **without the hyphen** — the spelling
    `ci.yml` publishes degrades to ASCII on Darwin and measures the C room twice (#249,
    confirmed independently here). Green in a clean room over 4 files: 9 212 passed, the 1
    failure the room's stated no-`.git` property, `beadloom ci` rc 0 with 0 errors there.
    Darwin arm64 / CPython 3.13.7, 0 of the 21 declared rooms; `mypy` clean against all four
    declared target versions, run under one interpreter. One instance of BDL-UX **#190**
    recorded rather than re-filed: `docs audit` read the interpreter version in this bead's own
    documents as a claim about the project's version and reddened the Gate, so the room is
    stated in a code block and the document says why.
  - [x] `.46` — BDL-UX **#244**, **#245** and **#250**. Wave 5, alone, and its own gate owner.
    **#244 is #213 one reader over, and the answer was reused rather than rewritten.** `.68`
    measured the cause of #213 as a section read as ONE table; the same sentence is true of
    `read_axes_section`, where a second table's header row became an approved node named `Node`
    whose `In scope` cell reads the literal words "In scope" as a yes. `.68`'s `_tables()` could
    not be imported from `axes_section.py` — it lives in `doc_quality.py`, which `doc_shape.py`
    imports, and `doc_shape.py` owns `table_cells` — so both halves moved into one component,
    `doc_sync/tables.py` (`markdown-tables`), and `_tables()` is now a one-line delegate.
    Measured on this repository's own RFC laid out in the shape its own rule describes — 74 rows
    in five per-slice tables: **78 rows read before, 4 of them header rows, all four approved and
    `Node` in the generated `refs:` line; 74 after**, identical to reading the one-table layout
    the tree carries. The phantom was absent from the tree only because the document had been
    hand-normalised into the shape the parser demands, which no artifact recorded.
    **#250 is larger than the entry says.** `approved` was `kept | targets`, and the entry names
    two nodes; measured, **six** of BDL-068's 39 approved nodes were approved by having been
    swept — `cli`, `doc-spaces`, `flow-composer`, `guard-hooks`, `intent-reader`,
    `typed-surface` — and only two of the six carry a `no` row. The other four are named by no
    row at all. `approved` is now `kept`, 39 drops to 33, and a fifth verdict
    `swept_no_scope_decision` carries the four, because calling them `not_derived` would state
    something false. The commit gate KEEPS `kept | targets`, and that is two questions rather
    than two answers: `scope_check`'s docstring records the measurement that chose it, a
    kept-row-only rule going red on all three of this branch's code commits.
    **#245's remedy was rewritten rather than answered with a selection step**, and the rejected
    alternative was rejected on a measurement: 22 of the 74 rows already name a bead in their
    `Why` cell, but a `Why` names a bead because an author explained who writes the node, and
    row 304 names `beadloom-mr2l.44` — a bead of another epic. Reading provenance as consent is
    #250 one level up. The remedy now says the nodes are the work item's UNION, sends the reader
    to `beadloom impact` over the files that bead changes, and states the consequence of the old
    sentence; the same correction went into `remedy_for` and into `beadloom axes --refs`'s own
    help. The collapse is now executable: three beads given the union produce 1+1+1 through the
    real planner, and the same three declaring what they occupy produce one wave of 3.
    `beadloom waves`'s `unguarded_axis` finding falls from 22 named nodes to 18.
    A refactor must not shrink a measured scope: 31 mutants left `doc_quality.py` and
    `doc_shape.py` and 26 arrived in `tables.py`, so it is the fifteenth declared mutation
    target in all three homes and the declared scope reads 6 459 against 6 464, the five being
    the deduplication itself. 30 tests (13 unit + 5 scenarios, plus a fixture and a node-count
    fact re-derived). Green in a clean room over 29 carried files: 9 268 passed, 59 skipped, the
    1 failure the room's stated no-`.git` property (46 pairs unverified, no sync baseline).
    **As this wave's gate owner, separately:** the combined tree is green — `beadloom ci` rc 0
    taken in the foreground without a pipe, `ruff check src/ tests/` rc 0, `mypy src/` rc 0
    against all four declared target versions, and the full suite 9 316 passed / 1 failed before
    the node-count fact was re-derived and green after. Darwin arm64 / CPython 3.13.7, 0 of the
    21 declared rooms entered. A third reader of the same boundary EXISTS and was left alone
    deliberately: `application/work_item_routing.py` reads the `/task-init` routing table with
    the same one-header-per-heading shape, guarded today by vocabulary rather than by boundary,
    so the class is present and the instance is not. Outside this bead's axes; recorded on the
    bead.
  - [x] `.50` — BDL-UX **#248** and **#249**, one instrument. S6, alone, and its own gate owner.
    **The census carries a locale dimension, and it is the CODEC rather than the name.**
    `current_room()` derives `codecs.lookup(locale.getpreferredencoding(False)).name` — the same
    two calls `ci.yml`'s own anti-vacuity step makes — and a leg's declared name is resolved
    through its codeset the way that step resolves it. Before this the two `tests-locale` legs
    answered "this run cannot describe the dimension `locale`" while the process genuinely was
    under an ASCII codec, so the sentence every verdict in two epics is qualified with — 0 of 21
    declared rooms — was measured over a vocabulary narrower than the 21 it names.
    **#249 is the same instrument read the other way.** Measured on this machine: the name
    `ci.yml` publishes, `en_US.ISO-8859-1`, gives preferred encoding `ascii`, and
    `en_US.ISO8859-1` — no hyphen — gives `iso8859-1`. macOS has no locale by the first
    spelling, so a developer reproducing the 8-bit leg ran the `C` room a second time under the
    other room's name. The room now carries `locale_asked` **only** when the locale asked for is
    not the one in force, so its presence is the finding: the room line every verdict prints
    reads `locale ascii (asked for en_US.ISO-8859-1, which did not apply here)`, and the leg's
    own reason says the name did not apply rather than reading as a locale nobody set. Under the
    spelling that DOES apply the leg's reason no longer mentions locale at all, which is the
    reproduction three bites needed. `ci.yml`'s matrix is unchanged and now says why: the
    hyphenated name is correct for the image `localedef` builds it on.
    **The 11 manufactured failures were re-measured, and the attribution moved.** Same tree, same
    command, one word different: `BEADLOOM_SIMULATED_ROOM=ubuntu-latest/3.13` gives 13 failures
    and `Linux/3.13` gives 3. The plugin's grammar takes what `platform.system()` RETURNS and
    `beadloom-0mdo.49` gave it a runner LABEL, which matches no leg at all and reddens every room
    assertion in the suite as an artefact of the invocation. Ten of the thirteen are that; one is
    #258's known clean-room red; the remaining three are one cause — `python_full` fabricated as
    `3.13.0` against `platform.python_version()` still answering the real build. Both fixed in
    `tests/room_simulation.py` and both verified red first by stashing it: a runner label is
    translated through `rooms.RUNNER_PLATFORMS` and a spelling in neither vocabulary raises
    `pytest.UsageError` instead of standing the run in a room that cannot exist. Suite-wide under
    a well-formed room the suite is now green, so the instrument is fit for the whole suite and
    was unfit for one spelling nothing rejected.
    **Not built, with the measurement that decided it:** a remedy naming the spelling that works
    here would have to read `locale -a`, which on glibc spells the codeset `en_US.iso88591` —
    `codecs.lookup` refuses it, so matching needs a normalisation this module would own, and a
    spelling is what it exists to stop comparing.
    41 tests (6 scenarios, 33 unit, 2 on the plugin's own vocabulary). Green in a clean room over
    8 carried files: 9 317 passed, 59 skipped, the 1 failure BDL-UX #258's known red — a second
    failure would have been the signal. **As its own gate owner, separately:** the combined tree
    is green — `beadloom ci` rc 0 taken in the foreground without a pipe, `ruff check src/ tests/`
    rc 0, `mypy src/` rc 0 against all four declared target versions, and the full suite green.
    Darwin arm64 / CPython 3.13.7, 0 of the 21 declared rooms entered. Three stale doc pairs left
    by `.68` and `.73` were repaired rather than re-baselined unread: `docs/domains/application/
    README.md` said `impact` reports "ten named kinds" where the code has eleven, and did not
    name `shipped_decision_sections`.

  - [x] `.59` — BDL-UX **#252**, the check first and the text second. S6, concurrent with `.63`
    and `.75`; **not the gate owner** — `.75` is.
    **The third direction of `role-duties`' graph.** #228 was a duty declared for a role that
    does not reach that role's core; this is a role that exists and does not reach the document
    that lists roles. `onboarding/role_map.py` (new node `role-map`) derives the population from
    `role_composer.ROLE_NAMES` — what the composer composes, not a directory listing, so
    `_landing`, `_rooms`, `_tracker`, `_writing` and their `.ru` siblings are fragments and not
    roles — and checks it against the composed `CLAUDE.md` in both directions: `unmapped` (a
    composed role no construct names), `partial` (a composed role omitted from a roster that
    names two others) and `unbacked` (a name a designation claims is a role and no core fragment
    ships).
    **A name is read as a role only inside a construct that designates one**, because a bare
    word search reads `test` in "Committing with failing tests" as the role — the
    keyword-proximity class filed three times. A DESIGNATION (`subagent_type: <names>`,
    `agents/<name>.md`, `agents/{<names>}.md`) claims each name is a role and its findings are
    `error`; an INFERRED roster (a `·` run, or a backticked run joined by `,` or `|`) is
    recognised only once it already names two composed roles, produces `warn` only, and never
    yields an `unbacked` name — otherwise an adopter's ``we deploy to `dev`, `test``` becomes a
    release-introduced red in their own prose.
    **Measured red on this tree before the text moved**, which is CONTEXT's no-check-that-cannot-
    fail rule discharged on the tree the check was built against: 6 rosters in the shipped
    `CLAUDE.md`, 1 finding — `explore` unmapped at `error`, naming all six sites. `Explore` was
    composed, named four times each by the `/coordinator` and `/task-init` templates, and named
    **zero** times in the map. After the fix: 16 designations, 6 of them rosters, 0 findings.
    The text moved in the SHIPPED template, so every adopter's composed copy carries it — the
    header pointer, section 0.0's map and both of its "two ways a role runs" bullets, the flow
    line, section 1's list, section 4's Agent Roles table, its step 4, its closing pointer and
    the footer. The two wave orders `dev → test → review → tech-writer` were deliberately NOT
    changed: `Explore` runs before a work item has a type, so it is not a wave, and both lines
    are reported in `not_judged` rather than as findings.
    **What the check does not judge, and says on every run:** 5 lines of the shipped map mention
    two or more roles in a shape no construct reads. Some should enumerate every role and some
    must not, and the derivation cannot tell them apart, so `config-check` names them.
    One instance of the same defect was found in this repository's own documents by the same
    derivation and fixed: `docs/domains/onboarding/README.md` spelled `ROLE_NAMES` as four names.
    The sweep that found it is a spelling-level pass over documents the check does not read, so
    it is a lower bound and not a derivation.
    Each guard was demonstrated red by mutating the decision it guards: allowing `,` to join a
    `subagent_type` run reddens 3, and lowering the roster threshold from two composed roles to
    one reddens 1. 18 tests (8 scenarios + 10 boundary guards). AS-IS document population 114 →
    115.
    Green in a clean room over 15 carried files: 9 336 passed, 58 skipped, the 1 failure BDL-UX
    #258's known red, confirmed red at HEAD in a control room built the same way. Darwin arm64 /
    CPython 3.13.7, 0 of the 21 declared rooms; `mypy src/` rc 0 against all four declared target
    versions, varying the version the checker is asked about and not the interpreter it runs
    under. **Not a claim about the combined tree** — `.75` owns that measurement.
    **BDL-UX #257 confirmed from this bead's side.** `beadloom waves` reported 0 serialisations
    for these three, and three documents no bead's code owns were shared in fact: this `ACTIVE.md`
    (all three), `docs/services/components/cli-commands/DOC.md` (node `cli-commands` owns both
    `setup.py` and `.75`'s `waves.py`) and `tests/test_bead77_kind_and_root_disagree.py`, whose
    hardcoded AS-IS document count both this bead and `.63` must raise because both add a node.
    `.beadloom/_graph/services.yml` is a fourth. None was compared by the plan.

   - [x] `.63` — BDL-UX **#253**, and the foreign-subject face of **#190**. S6, concurrent with
     `.59` and `.75`. A version is now attributed to the nearest subject NAME to its left inside
     its own clause, and only a version whose nearest name is this project's — or that has no
     name at all — is compared against this project's version. The vocabulary of names is DERIVED
     from what a project already declares (every distribution in `pyproject.toml` /
     `package.json` / `Cargo.toml`, the interpreter families implied by `requires-python` /
     `engines.node` / `rust-version`, `git` when the project is a git repository) and configured
     per NAME in `docs_audit.subjects` for what no manifest carries.
     **Measured over the right population, not over what tripped.** The seven suppressions were a
     set chosen by the defect, so the sweep counted every version token instead: 16 across the
     audit's 68-document surface, of which ONE is a claim about this project, and 700 across all
     400 markdown files in the repository. That second sweep is what decided the design. Reading
     any word beside a version as a subject unless it is a function word was measured and
     REJECTED — `Phase 3.0.0`, `Implemented 3.0.0`, `Release 2.1.0`, `dated 3.0.0` and
     `published 2.2.0` all put an ordinary English word beside this project's own version, so
     that rule turns a stale claim into silence. A derived-and-declared vocabulary fails LOUD
     instead: a name nobody declared still produces a finding.
     **Eight of the ten version triples retired**, counted and measured with a real `DocScanner`:
     `application/README.md`, `services/cli.md` (two sentences), `services/mcp.md`,
     `bd-seam/DOC.md` (five), `multi-agent-development.md`, its `.ru` counterpart,
     `parallel-waves.md` and `active-table/DOC.md`. One `docs_audit.subjects` entry — `bd` —
     replaced nine of them; `git` needed none. The 13 tokens are now reported as `bd x12, git x1`
     under `attributed_versions` rather than silenced. One sentence was rewritten and GAINED
     information: `bd-seam/DOC.md`'s `BD_MEASURED_VERSION` line now names `bd` beside the release
     the reader previously had to infer from the prefix.
     **The merge with #190 is PARTIAL, and the split is at the level of the fix.** Absorbed: every
     face where a name stands beside the number, including #190's fifth instance (`CPython
     3.13.7`, the room `.65` recorded). Not absorbed, and each keeps its triple with the reason:
     a version behind a preposition (`a JavaScript project at 0.4.1`), where the subject is
     present but not adjacent and walking past prepositions means calling `Release 2.1.0` a
     product; and a version MENTIONED rather than used (`v2.2.0`, the example token inside the
     sentence stating the rule). #190's fourth instance is neither — it is this project's own
     past version, which is #205.
     26 tests (6 scenarios + 20 unit), each verified red: four mutations of the implementation
     were applied and two of them initially killed NOTHING, so both assertions were repaired
     before the tests were called checks.
     Green in a clean room over 13 carried files (1 895 files total): 9 343 passed, 59 skipped,
     the 1 failure `test_bead15_s3b_coverage.py`'s declared no-`.git` exclusion, whose 45 pairs
     come back `unverified` for want of a baseline. Darwin arm64 / CPython 3.13.7, 0 of the 21
     declared rooms. **Not a claim about the combined tree** — `.75` owns that measurement.
     **BDL-UX #257 confirmed from this bead's side too**: this `ACTIVE.md` and
     `.claude/development/BDL-UX-Issues.md` were shared with `.59` in fact, and
     `.beadloom/sync-surface.json` records a pair count that grew by three across two beads, so
     it is left for the gate owner to re-record rather than staged here.

   - [x] `.77` — BDL-UX **#259**, the third reader of the markdown-table boundary. S6, concurrent
     with `beadloom-kqsv`; **not the gate owner** — `beadloom-kqsv` is.
     **The component fit, so there is no fourth parser.** `_routes_in` reads through
     `doc_sync.tables.table_blocks`, and `_routing_tables` selects every block whose OWN HEADER
     ROW leads with `Type` and `Flow`. Nothing was missing from `markdown-tables`: `doc-quality`
     and `axes-section` iterate every block and classify each by its own header, and selecting
     one by header is this reader's question rather than the component's.
     **The design changed once, on a measurement that says the entry's failure direction was
     backwards.** The first shape was "the FIRST matching table only" and it DROPPED A ROUTE
     THAT EXISTS TODAY — `test_a_project_layer_that_adds_a_type_is_policed_by_the_same_act` went
     red, because a project layer states its own routing table under its own heading, which is
     the capability `.5` built this derivation for. The rule is therefore the union, each
     table's rows judged against its own header: the rule `axes-section` already follows for a
     section holding one table per slice.
     **The phantom DELETES, so "under-reporting a route" was the wrong reading.**
     `shared_kinds` is an INTERSECTION over every route and is where BDL-UX #257's focus
     document comes from. Measured on the shipped command: with one real second table appended —
     the two rows `docs/guides/document-kinds.md` already carries — **7 routes read where 5
     exist**, two phantom types routed `simplified` with empty document sets, and `shared_kinds`
     falls from `{ACTIVE}` to `{}`. With a table stated BEFORE it quoting a routing row as an
     example, **6 where 5 exist**, a phantom `epic` with an empty document set, and
     `decision_line` at 43 instead of the routing table's own header. After the fix both read 5,
     `shared_kinds` `{ACTIVE}`, `decision_line` at the table.
     **Reachability of the guard the reader survived on, measured over this repository:** 456
     markdown documents, 5 122 table data rows, **27 admitted** by "second cell contains
     `simplified` or `full`, at least three cells". Ten are the routing table itself; the other
     **seventeen sit in fifteen other documents** and would be read as routes named `D4`,
     `BEAD-05`, `Q1`, `12.8.3` and `Local proxy`. A filter that rejects 99.5% of a corpus is
     sparse, not sound, and #213's measured cause was that vocabulary cannot decide this.
     **No route disappears**, measured over the composed commands this project ships: 21
     shapes — its own `flow.yml` plus two architectures x five stacks x two languages — 5 880
     lines, **105 routes before and 105 after**. The routing table lives in the core fragment,
     so no overlay moves it.
     **A recorded GAP closed and was deleted, per its own instruction.**
     `TestARoutingRowWhoseFlowCellIsUnreadableIsDroppedSilently` was `.5`'s: a row the table
     states and the reader cannot use was dropped in silence, and its docstring said to DELETE
     the class rather than repair it when it went red. It went red; deleted (412 -> 353 lines).
     Its stated reason for not repairing — a note per unreadable cell would fire on the
     `|---|---|` alignment row — stopped applying the moment the reader moved onto
     `table_blocks`, which drops a separator before any caller sees one. `Routing.notes` now
     names such a row with its line number.
     9 assertions were verified RED against the pre-fix reader (3 scenarios + 6 unit); the other
     25 are green in both directions and are labelled guards rather than checks in the module
     docstring. 34 tests total.
     **BDL-UX #266 filed rather than fixed** (`beadloom-0mdo.81`). `beadloom ci` in this bead's
     room returned rc 1 on ONE error in a file it did not carry —
     `active-table/DOC.md:227 doc-fact-stale: '2.49.0' vs '3.0.2'` — and it is **red at HEAD in
     a control room built the same way**: `version_subjects.py:140` derives the subject name
     `git` from `(project_root / ".git").exists()`, and a `git archive` room has no `.git`. The
     tree reports `No stale mentions found`. Every clean-room Gate run on this repository is
     rc 1 for a reason belonging to the instrument, which is BDL-UX #258's shape again.
     Green in a clean room over 9 carried files (1 255 files total): **9 508 passed, 59 skipped,
     1 xfailed, 0 failed** — `test_bead15_s3b_coverage.py` now SKIPS on the room's stated
     no-`.git` property rather than failing. `ruff check src/ tests/` rc 0 and `mypy src/` rc 0
     against all four declared target versions, varying the version the checker is asked about
     and not the interpreter it runs under. Darwin arm64 / CPython 3.13.7, extras
     `all+dev+graphql+languages+mutation+tui+watch`, **0 of the 21 declared rooms**.
     **Not a claim about the combined tree** — `beadloom-kqsv` owns that measurement.
     **BDL-UX #257 and #261 confirmed from this bead's side.** `beadloom waves` reported 1 wave
     of 2 with 0 serialisations, and this `ACTIVE.md` was shared in fact. The tree also carried
     `beadloom-kqsv`'s in-flight `waves/` edits throughout: a full working-tree run showed 10
     failures and one collection error, all of them in `waves`/`media` and none of them mine,
     which is exactly the reading the room exists to separate. `.beadloom/_graph/services.yml`
     was NOT touched by this bead.

   - [x] `.79` — BDL-UX **#264**, a population literal is a derivable fact with two homes. S6,
     concurrent with `.80` and `beadloom-vyjp`; **not the gate owner** — `beadloom-0mdo.80` is,
     per `beadloom waves`.
     **MEASURED BEFORE AND AFTER, over the whole suite and not over what the log names.**
     Planting one feature directory holding a BRIEF that states a scenario and an ACTIVE, plus
     one node SPEC, reddened **2 cases holding 4 literals** at `9d0c02a` — `to_be == 203`,
     `as_is == 116`, `working_documents == 58` and `len(found.references) == 50` — and reddens
     **0** after. `mr2l.72` recorded three because the BRIEF it added stated no scenario; the
     fourth only moves when the added document names one. A static scan agrees: 14 numeric
     literals remain in repository-reading test functions and none of them is a document or
     node population — 7 are exit codes, 1 is the graph schema version and 4 are counts of a
     DECLARATION (`site_files == 8`, the 2 `ai_agents` boundary rules, 1 landing-lock
     invocation, 1 top-level description) that no node-adding bead moves.
     **THE ANSWER SPLIT BY WHAT EACH CLAIM IS ABOUT, which is `0mdo.47`'s shape re-used.** The
     three doc-space counts became three relations, each in the class whose subject it is: the
     populations partition what the declared roots found (sum, already there), no two spaces
     hold the same document, and no declared space is empty. The kind-precedence class asked
     the precedence question directly instead of counting its consequence — no kind is declared
     by two spaces, and `space_of_kind` returns the space that declares it — which can still go
     red, on a future configuration of this repository that declares a kind twice.
     **THE FOURTH LITERAL NEEDED A PRODUCTION CHANGE, and a measurement is what said so.** The
     first replacement asserted the loader's references against a per-document parse and was
     **verified NOT red** against a loader that skips its first matched document, because that
     document is one of the 53 shipped PRDs and BRIEFs of 56 that state no scenario. An
     assertion that cannot fail is worse than the literal it replaced, so `ReferenceSet` gained
     `documents` — the third outcome of a glob, which the set reported by silence. It is a
     `scenario-binding` field and `scenario-coverage` does not read it; wiring it into the
     rule's reporting is `rule-engine`'s surface and outside these axes.
     **EVERY NEW ASSERTION VERIFIED RED BY BREAKING THE RELATION IT NAMES, never by moving a
     count.** Nine mutants: two buckets sharing a path, `classify` dropping its last document,
     the WORKING kind list withdrawn, `README` declared by TO-BE as well as AS-IS, the loader
     skipping its first match, the loader dropping the document that carries 33 references,
     `documents` reporting what was matched rather than what was read, the parser reading
     nothing, and a shipped PRD written as cp1251. Each named the intended case and the
     controls came back green.
     **WHICH HALF IS DERIVED, argued in the module rather than left to the next reader.**
     Deriving the check's INPUT from the corpus is legitimate; deriving its OUTPUT is the
     tautology `0mdo.47` rejected. The reference cases derive which documents ship and make no
     claim about parsing — the per-document expectation calls the same parser — so a parser bug
     is invisible there by construction and belongs to that file's synthetic cases. A floor
     case guards the failure mode that leaves: two empty sets agreeing.
     **Green in a clean room at `room-beadloom-0mdo.79` over 3 carried files: 9 535 passed, 60
     skipped, 1 xfailed, 0 failed.** `ruff check src/ tests/` rc 0 and `mypy src/` rc 0 against
     all four declared target versions, varying the version the checker is asked about and not
     the interpreter it runs under. Darwin arm64 / CPython 3.13.7, extras
     `all+dev+graphql+languages+mutation+tui+watch`, **0 of the 21 declared rooms**.
     **Not a claim about the combined tree** — `beadloom-0mdo.80` owns that measurement, and
     the tree carried `.80`'s in-flight graph split and `beadloom-vyjp`'s role cores throughout.
     **`beadloom ci` rc 1 in the room on one error that is not this bead's** —
     `active-table/DOC.md:227 doc-fact-stale '2.49.0' vs '3.0.2'`, a file this room did not
     carry. BDL-UX #266 / `beadloom-0mdo.81`: `version_subjects.py:140` derives the subject
     `git` from `.git` existing and a `git archive` room has none. Attributed, not chased.
     **A finding filed rather than fixed:**
     `test_bead15_s3b_coverage.py::test_all_nine_site_modules_exist_on_disk` asserts
     `len(site_files) == 8`. The name and the literal disagree, and `site-generation` is outside
     these axes.

   - [x] `.81` — BDL-UX **#266**, a clean room has no `.git`, so a version attributed to `git`
     loses its subject. S6, alone, and **its own combined-tree gate owner**.
     **THE RED WAS THE INSTRUMENT'S, AND EVERY ROOM HAD IT.** `beadloom ci` in a clean room at
     HEAD with **zero** carried files returned rc 1 with exactly one `::error` —
     `docs/domains/application/components/active-table/DOC.md:227 doc-fact-stale: version: doc
     says '2.49.0' but project state is '3.0.2'` — over 646 warnings; the same tree in the
     working directory returned rc 0 with `docs-audit PASS: 19 mention(s) fresh` over 196.
     Reproduced by `.77`, `.67`, `.79` and `beadloom-vyjp` in four separate rooms, each of which
     attributed it rather than chased it. That discipline is what made a permanent red readable
     instead of ignored, and it is also BDL-UX #258's shape arriving on the instrument.
     **THE FIX IS TO WHAT AN ABSENT SOURCE MEANS, NOT TO WHAT THE VOCABULARY HOLDS.**
     `(project_root / ".git").exists()` was read as a denial, and an absent `.git` cannot tell a
     project that never used git from an export of one. `git` now becomes UNRESOLVED: it stays
     in the vocabulary, still wins the attribution walk, and `compare_facts` routes its mentions
     to a new `AuditResult.unjudged` population kept apart from `attributed`, because one is a
     subject this project confirmed and the other is a subject this DIRECTORY could not. The one
     name in `_ENVIRONMENT_SUBJECTS` is the one that was already hard-coded at line 140; what
     grew is a probe whose absent case is "cannot tell".
     **UNRESOLVED IS NOT SILENCE.** The Gate line reads `COULD NOT JUDGE 5 version token(s)
     naming git — unconfirmed here`, the human report gives the reason, and `--json` carries
     `unjudged_versions`, `unresolved_version_subjects` and `summary.unjudged_version_count`.
     A repair that made the room green by making it blind would be the failure this whole epic
     exists to prevent, so `TestTheDefectVerbatim` pins both directions.
     **BOTH DECLINED OPTIONS ARE ON THE RECORD.** The `docs_audit.subjects` entry for `git` is
     one line and reintroduces the second hand-written vocabulary `.63` removed — declined, and
     `.beadloom/config.yml` says so where a reader would reach for it. The room-side repair
     fixes the rooms this command builds and no other export (an sdist, a vendored copy, an
     image layer of tracked files), and a room carrying a real `.git` would stop being the room
     it advertises, because `sync-check` would gain the baseline the room states it lacks. The
     room's caveat text was left alone for the same reason the fix went into the audit: the
     docs-audit line reports the declined token where the measurement is taken, and a second
     sentence in the room's prose would be an authored copy of a derived fact.
     3 acceptance scenarios and 17 unit assertions were verified RED before the fix; the first
     of them reproduces the defect at unit scale (`subject=None`, `status='stale'`, `'2.49.0'`
     against `'3.0.2'`).
     **Green in a clean room at `room-beadloom-0mdo.81` over 18 carried files: 9 596 passed, 59
     skipped, 1 xfailed, 0 failed**, and `beadloom ci` rc 0 there with **zero** errors — the
     verdict this bead exists to turn. `ruff check` rc 0 in the room, and `mypy src/` rc 0 in the
     room AND on the tree against all four declared target versions, varying the version the
     checker is asked about and not the interpreter it runs under — a difference in what is
     installed per interpreter is still measured only in CI. Darwin arm64 / CPython 3.13.7, extras
     `all+dev+graphql+languages+mutation+tui+watch`, **0 of the 21 declared rooms**.
     **As its own gate owner, separately:** the combined tree is green — `beadloom ci` rc 0 in
     the foreground without a pipe, zero errors, `docs-audit PASS: 19 mention(s) fresh` both
     before and after, so the tree lost no coverage for the room's green.

  - [x] `beadloom-l9ee` — **BDL-UX #260**, the shared write and the condition an ADR needs.
     A DECISION bead, re-checked as evidence rather than executed as instructions, and its own
     recommendation is corrected on two points. **Its numbers hold on today's tree:** 1427 lines
     and 35 table rows (2.5%); 58 `ACTIVE.md` files, 5646 lines, 4913 of prose (87.0%), counted
     with `doc_sync/tables.py`'s `cells_of`.
     **First correction — it measured the wrong region.** The table is 2.5% and composing it
     buys nothing, which is true and was read as a statement about the file. The `Progress`
     section is lines 64-1122 — **1059 of 1427 lines, 74.2%** — and it is a per-BEAD append,
     one sub-bullet per bead. Both `ACTIVE.md` collisions of this epic are in it: `.63` lost 43
     lines of its `Progress` entry into a neighbour's commit while correctly holding the merge
     slot (`4753c17`), and `.73` and `.65` each wrote a `Progress` bullet in wave 4. So the
     writer unit is the bead. **Not taken** — `active-table`'s surface, and this bead's derived
     axis is `issue-numbers` alone.
     **Second correction — `beadloom-0mdo.66` answered the `lateral move` objection, so the log
     migration is declined on the bead's own standard.** The objection rested on commit
     `27db92b` alone and `.66` closed that class. Re-measured on this branch: the log took 17
     commits at +248 / -4 with no repair commit, against `ACTIVE.md`'s 22 at +735 / -395.
     Realised collisions across this epic are 3 in per-bead prose and 1 the log's number, now
     fixed, so moving 241 entry bodies would have prevented **0 of 4** — the test the bead used
     against options 3 and 4, turned on its own recommendation. It avoids one commit rewriting
     every body and every cross-reference in a 3155-line file. What protects a body meanwhile is
     the ledger and not the layout: a claim is a separate file a lost write cannot take with it.
     **Which is where the defect was.** That protection reaches only entries at or above the
     floor and the verdict never said so: `240 entr(ies), 5 claim(s), floor 262` then `No
     duplicate, unwritten or unclaimed number` — a clean list over 5 of 240, because
     `_ledger_findings` skips every entry below the floor. Filed as **BDL-UX #267**, allocated
     through the allocator it is about, and closed in the same commit:
     `IssueNumberReport.entries_below_floor`, `PARTLY CHECKED` on the Gate line, and the
     unaccounted numbers named rather than counted. Coverage, not a finding — no tree reddens.
     Self-reference recorded and deliberately not exploited: quoting an unaccounted number in
     the log's prose silences its own report, so the entry leaves it unquoted.
     **Neither the ADR directory nor the `decision` doc kind ships**, on the bead's own
     condition — the pairing is `doc-sync` plus `graph` machinery, outside this axis, and the
     directory without it is the regression the condition names. The three decisions are in
     `CONTEXT.md`'s table, which `doc-quality` judges for a reason that explains why.
     2 acceptance scenarios and 12 assertions verified RED before the fix; two negative
     assertions are declared NOT VERIFIED RED in their docstrings, because the clause they
     forbid did not exist beforehand.
     **Green in a clean room at `room-beadloom-l9ee` over 18 carried files: 9 607 passed, 60
     skipped, 1 xfailed, 0 failed**, `beadloom ci` rc 0 there with **zero** errors, `ruff check`
     rc 0 and `mypy` rc 0 in the room. On the tree, `mypy src/` rc 0 against all four declared
     target versions — varying the version the checker is asked about, not the interpreter it
     runs under, so a difference in what is installed per interpreter is still measured only in
     CI. Darwin arm64 / CPython 3.13.7, extras `all+dev+graphql+languages+mutation+tui+watch`,
     **0 of the 21 declared rooms**.
     **As its own gate owner, separately:** the combined tree is green — `beadloom ci` rc 0 in
     the foreground without a pipe, zero `::error`, and `pytest` 9 654 passed / 0 failed once
     the four stale doc pairs this bead created were repaired.


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
| **#235** — the clean-room convention names a fixed directory, so two agents in one wave build one room and both call it clean | `0mdo.37`, P1, **done** | Closed with **#243**, which the same fix answers. `beadloom clean-room` derives the path from the bead and refuses a directory it did not create empty, so a neighbour's room cannot be entered and a room cannot be re-entered. The role cores still describe the by-hand convention and are a follow-up (`beadloom-vyjp`), because those templates are outside this bead's axes and inside `0mdo.59`'s and `0mdo.67`'s surface. |
| **#236** — a clean room's verdict is decided by which optional extras it installed, and the convention never names them | `0mdo.38`, P1, **done** | The durable form shipped: `extras` is a dimension of the room, derived from the project distribution's installed metadata for this run and from a job's install step for a leg, compared on what an environment SATISFIES rather than on what was typed. Re-measured at `6c4d0a9`: 0 mypy errors under `.[all,dev]` and 82 under `.[dev]`. **#256 is not absorbed**; its import-path half is already closed by `0mdo.37`'s invocation, verified here, and what remains for `0mdo.74` is building the environment rather than stating it. |
| **#238** — nothing compares the ignore block on disk against the block this version emits | `0mdo.40`, P2, open | The INSTANCE was fixed in S4: this repository's `.gitignore` now carries the shipped glob. The CLASS is a new `config-check` leg. Splitting them is what keeps a repository repair from reading as a product fix. |
| **#244** — a second markdown table in `## Axes` contributes its header row as an approved node named `Node` | `0mdo.46`, P1, **done** | Worked around in S4 by keeping one table, so no commit was judged against a phantom node. The parser fix touches `read_axes_section`, which S1 owns and which `0mdo.47`'s pinned excerpt now guards. |
| **#245** — the `unguarded_axis` remedy, followed literally, gives every bead one scope and collapses every wave to a wave of one | `0mdo.46`, P1, **done** | The VERDICT is correct and shipped; only the advice beside it is wrong. #244 must land first — #245 cannot be judged honestly while #244 injects a node nobody wrote. |

**Inherited by S6 with no bead of its own:**

- **#242** — a subagent's launch context carries a `git status` snapshot that is stale by
  construction, and `en0x` published a sentence from it and withdrew it (`f45dd62`). Recorded as
  a NOTE on `0mdo.14` rather than as a bead, because the answer is ours and not the harness's:
  the role protocol states that a tree fact is derived at the moment it is stated, and
  `0mdo.27`'s duty mechanism can carry that as a declared duty. It needs no separate DAG node.
- **#243** — a room that is refreshed rather than rebuilt manufactures a stale-doc failure
  shaped exactly like a defect. **Closed by `0mdo.37`**, and the prediction held: #235's command
  answers it, because an existing directory is refused rather than entered and `--rebuild`
  replaces the room instead of refreshing it. The workaround it replaces — rebuild after any
  edit, never re-copy — is now the only thing the command permits, so it is a property rather
  than a rule. No bead of its own was needed.
- **#246** — a declared mutation target that no run ever covers passes every green Gate.
  `0mdo.45` closed the instance (`[tool.mutmut] only_mutate` now names every declared target and
  `tests/test_mutation_runner_scope.py` asserts both directions), and the CLASS — Beadloom
  recording the run it just judged, so the Gate can report a target whose last measurement is
  absent or stale — is routed to S6 with no bead yet. **This is the one gap in the routing:** an
  adopter has no equivalent of the repository test that closes it here, and nothing in the DAG
  currently holds that.

## What S6 inherited, and the owner's decision that it runs in full

**OWNER DECISION, 2026-09-08: S6 is done in full. No split, no deferral to a follow-up epic.**
Recorded on `0mdo.14` and on the epic bead, and repeated here because a resumed session reads
this file and cannot reconstruct a decision that lives only in a bead comment. The coordinator
offered to ship S5 and then cut S6 into "the two P0/P1 that bite today" plus "the rest as a
separate epic", which would have closed BDL-068 roughly a week earlier. The owner declined it.
The offer is recorded as well as the answer, because a scope decision that records only its
outcome cannot be re-examined later.

**S6 holds fourteen beads**, plus test, review and tech-writer — about the size S4 was, and S4
took eight waves, a fix cycle after an ISSUES verdict and three rounds of CI.

- **Six planned from the start:** `mr2l.72`, `mr2l.91`, #191, #213, `beadloom-iur5`,
  `beadloom-ec1a`.
- **Eight routed in from S4 and S5 as they were found:** `.37` (#235), `.38` (#236), `.40`
  (#238), `.46` (#244 and #245), `.48` (#247), `.50` (#248), `.59` (#252), `.60` (#254).

**Two of them bite today and are not deferrable quietly.**

- `.60` / **#254 (P0)** — a guard that cannot evaluate itself blocks the write that would
  repair it. Met live on 2026-09-04: `.51` wedged mid-refactor and the session was
  unrecoverable from inside, and the owner cleared it with a heredoc in their own shell. Until
  it is fixed, any refactor that leaves a package momentarily unimportable kills an agent's
  session.
- `.48` / **#247** — the push Gate does not run the suite and never says so. It cost a red PR
  across six legs and roughly 55 runner-minutes.

**Why the slice doubled, and it is not scope creep.** S6 was planned as "cheapest and most
visible, and it blocks nothing — which is why it is last". Every one of the eight additions is
a MEASURED defect that S4 or S5 found while doing something else, and all eight are one family:
a check that is silent about what it did not check, which is this epic's own subject. The
slices did not swell — the boundary held, and these were routed OUT of S4 and S5 deliberately
rather than absorbed.

**What that commits the next session to.** S6 runs as a full slice: its own axes derived at its
start (the rule S4 paid for), its own wave plan from `beadloom waves`, then test → review →
tech-writer, then a PR. It is not a cleanup pass appended to S5.

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

### From `0mdo.56`, the S5 review

The second pass closed at 0 critical and 0 major and carried seven Minors and one Nitpick, plus
five of its own first-pass Minors that nobody was assigned. The docs pass (`0mdo.57`) closed the
four that were documentation defects and touched no code:

- **Minor 2** — this file's header contradicted itself: line 5 said S5's review had closed its
  first fix bead while line 11 said the second had landed. **Closed by this pass.**
- **Minor 3** — the deep `.54` entry still reported 79 unlisted beads in the present tense,
  thirteen lines below the corrected 41 + 38. **Closed by this pass**, anchored to `5846b20`
  with a pointer to the split.
- **Minor 4** — CONTEXT's three new decision rows were inserted above the 2026-09-04 axes row,
  so the table was no longer in date order at its tail. **Closed by this pass.**
- **Nitpick 8** — `.62`'s clean room was described as "`git archive HEAD`, 8 624 files". `git
  ls-files` is 1 197 and `git archive HEAD` extracts exactly those; 8 624 is that room after
  `uv sync`, counting the virtualenv. **Closed by this pass**, in an epic whose subject is
  measurements that do not say what they measured.

The rest are code, configuration or tracker findings and stay open. A doc edit must not make one
of them look addressed, so each is named with what it still needs:

- **Minor 1** — bead `beadloom-0mdo.60`: the retitle to #254 landed and the body did not, so the
  first line of its description still reads `BDL-UX #253` and points a reader at the LOW
  dependency-release entry rather than the HIGH guard one. It is the last pointer in the
  repository that says #253 and means the guard. Needs `bd update beadloom-0mdo.60` and a
  re-export of `.beads/issues.jsonl`, which is a tracker write and not a documentation edit.
- **Minor 5** — the long line the reviewer named in `.github/workflows/mutation.yml:271` is
  still ~130 columns inside an otherwise wrapped comment block. CONTEXT's own over-long line was
  rewrapped by this pass; the workflow's was not, because it is not a document.
- **Minor 6** — the seven per-file mutation scores exist only in `0mdo.62`'s bead comment. This
  pass carried them into `docs/services/cli.md`, where a reader of the mutation section now sees
  `staging.py` at 65.00% beside the aggregate. **The reviewer's actual recommendation is
  untouched**: the scores are still absent from the workflow's own floor-composition comment,
  which is where the three component figures live and where a person re-deriving the floor
  looks.
- **Minor 7** — the aggregate floor (`--min-score 0.88`) and the `timeout-minutes` are pinned by
  no test, on settings this epic has already left behind once. The reviewer's remedy is a bead in
  S6: assert that the component mutant counts named in the workflow comment sum to the declared
  scope's denominator (statically derivable in 17.3 s), and that `--min-score` keeps a stated
  margin under the composed aggregate. No such bead exists yet.
- **First-pass Minors 3-7**, none addressed and none assigned, all verified unchanged at
  `f23f54d`: `_UNBLOCKED_IS_READY` has no `applies_when` (`assumptions.py:298`); `_git_paths`
  decodes with `errors="replace"` and does not defeat `core.quotepath` (`staging.py:139`);
  `population._read`'s docstring promises a gap no caller counts (`:193`);
  `answers.coverage_of` and `AnswerCoverage.stated` have no production consumer. The reviewer
  would carry the fifth into S6 rather than leave it to discretion: `_ECHOED_TITLES` still
  carries `confirmed_by="dep tree"` (`assumptions.py:285`), a claim the test bead found false,
  so a rule reads `secured` on the strength of a check the bulk call form removes.

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

# S3f — waves, review-brief, active-sync, the branch binding, the test suite, external,
research

> **Bead:** `beadloom-3jlv` (BDL-083 S3f, RFC D9)
> **Measured on:** 2026-10-20
> **Version:** Beadloom 9.0.0, the S2 version. The worktree is `cdaf3f78` on `features/BDL-083`;
> `git diff 41245dc7 cdaf3f78 -- src` is empty, so the code is the code of `main` at `41245dc7`.
> **Machine:** macOS 27.0 (Darwin arm64), CPython 3.12.12, git 2.49.0, bd 1.0.4.
> **Environment:** a git worktree of `cdaf3f78` under the session scratchpad, `uv sync --frozen`
> with the CI extras (`dev languages tui watch graphql`). Three throwaway rooms beside it: a
> local clone of the worktree (to check out an exact `features/BDL-083` branch, which the main
> checkout holds), a copy of the monorepo fixture with its own `bd init`, and an empty project
> with its own `bd init`. Nothing was written to the main checkout's index or tracker; tracker
> reads in the worktree and the clone resolve to this repository's tracker, read-only.
> **Room limit:** every result below is true of this machine and these rooms. None of them is a
> statement about the combined tree of S3, which is S3b's to measure.

Outcomes: **closed** — the issue is gone; **live** — it still reproduces; **won't-fix
candidate** — a reason is put to the owner. Proposed bead titles are not created.

### #355

- **Command:** `beadloom waves beadloom-3jlv beadloom-mhi2` on a branch
  `features/BDL-083-S3f-probe`, then the same in a clone on `features/BDL-083`.
- **Where:** the worktree (suffixed branch); the scratch clone (exact branch, `BEADS_DIR` at
  this tracker).
- **Printed:** suffixed: `Declared axes: NOT COMPARED — the branch 'features/BDL-083-S3f-probe'
  names no work item among the planning documents` and `focus-document: unmeasured — the flow's
  routing and its planning documents were not read`. Exact: `Declared axes (BDL-083,
  .claude/development/docs/features/BDL-083/RFC.md): …` and `focus-document: passed`. The `NOT
  COMPARED` line names no branch shape it would accept.
- **Outcome:** live.
- **Evidence:** 2026-10-20, 9.0.0 at `cdaf3f78`: `waves` on `features/BDL-083-S3f-probe`
  printed `Declared axes: NOT COMPARED` and `focus-document: unmeasured`, and on
  `features/BDL-083` it compared both.
- **Bead:** `beadloom-bdnv` (#230, the same matching rule); its title should name #355 as well.

### #344

- **Command:** `beadloom review-brief beadloom-rrz5 --since origin/main` (the S3 review bead,
  which declares no `refs:`), and once with the default base.
- **Where:** the scratch clone on `features/BDL-083`.
- **Printed:** `217 changed file(s), 0 document(s), 0 bound scenario(s)`, `DECLARED SCOPE: none
  declared`, `SPECIFICATION — 0 document(s)`, 55 lines `OUTSIDE`; the same brief's REACHABLE
  section lists `the work item's documents: 6 item(s)` in the folder it did not use as the
  specification. With the default base the header reads `Base: … (the merge-base with …, the
  branch this one was cut from …)`.
- **Outcome:** live. The base half is fixed by S1 (D4); the scope and documents still come from
  the bead alone.
- **Evidence:** 2026-10-20, 9.0.0: `review-brief` for an epic's review bead printed `DECLARED
  SCOPE: none declared` and `0 document(s)` with 6 work-item documents listed as reachable, and
  the default base is now the merge-base.
- **Bead:** none. Proposed: "[BDL-UX #344] review-brief for a bead that declares no scope falls
  back to the work item's axes and documents and names the fallback in its header".

### #336

- **Command:** `beadloom scope-check` over a staged path of `markdown-tables` (bounded context
  `doc-sync`).
- **Where:** the scratch clone on branch `features/PROBE1`, with an RFC whose `## Axes` table
  keeps `wave-plan` and a second table under `## Axes of the nodes this item creates` keeps
  `markdown-tables`.
- **Printed:** `src/beadloom/doc_sync/tables.py: markdown-tables … why: outside every axis the
  work item declared — callers (application)`, exit 2. Nothing names the second heading as read
  or ignored.
- **Outcome:** live.
- **Evidence:** 2026-10-20, 9.0.0: a node kept by a second axes table under its own heading was
  reported outside the axes (exit 2), and the output named neither the heading it read nor the
  one it ignored.
- **Bead:** none. Proposed: "[BDL-UX #336] scope-check names the heading it read and the tables
  it ignored, and the templates say how a node the work item creates is declared in scope".

### #316

- **Command:** `beadloom scope-check --base origin/main`, `beadloom docs quality`, and
  `beadloom waves` (which reports the same reader).
- **Where:** the scratch clone on `features/BDL-083`. BDL-083's own RFC is the shape: `## Axes`
  followed by eight `###` subsections, one table each.
- **Printed:** scope-check: `55 staged path(s) a node owns, 162 no node owns` and 55 `why:
  outside every axis the work item declared — no axis keeps a node in scope — and outside the 0
  bounded context(s)`, exit 2, although the RFC's prose keeps `declared-scope`,
  `gate-ownership` and eleven more. A staged change to `declared_scope.py` and
  `gate_ownership.py` alone gave the same verdict for both. waves: `0 node(s) approved … 7 the
  derivation did not reach`. docs quality: 16 `NOT CLASSIFIED … judged by nothing` tables under
  the RFC and `axes.md`, and `empty-section: 0 finding(s) over 328 read`.
- **Outcome:** live. This is the reader behind the scope-check's outside-the-axes advisories on
  this branch.
- **Evidence:** 2026-10-20, 9.0.0: on BDL-083's own RFC, whose `## Axes` holds eight `###`
  subsections, scope-check against `origin/main` called all 55 owned paths outside and read 0
  approved nodes, and docs quality reported no empty section.
- **Bead:** none. Proposed: "[BDL-UX #316] a `## Axes` section reads the tables of its `###`
  subsections, and a section read as zero rows is an empty-section finding and a '0 axes read'
  line beside the scope-check verdict".

### #309

- **Command:** `uv run pytest tests/unit/graph/scenarios/test_scenario_binding.py`, then the
  reference-parser test under `uv run --with "gherkin-official==42.*"`.
- **Where:** the worktree.
- **Printed:** on the lock (gherkin-official 29.0.0, pytest-bdd 8.1.0): `30 passed`. Under
  42.0.1: `1 failed, 29 deselected`. The test still calls `TokenScanner(str(path))` (line 272).
- **Outcome:** live; green only because of the pin.
- **Evidence:** 2026-10-20, 9.0.0: the reference-parser self-check passed on gherkin-official
  29.0.0 and failed on 42.0.1, and still passes a path to `TokenScanner`.
- **Bead:** `beadloom-ba9w.3`.

### #308

- **Command:** `beadloom active-sync` (fix mode, the hook's form).
- **Where:** an empty project with its own `bd init` (prefix `pr`): an epic and two children,
  all closed; an ACTIVE.md with `Phase: Development`, `Last updated: 2026-10-01`, `**Bead:**
  pr-0jh.1` and one unticked Progress item.
- **Printed:** `updated 3 row(s)` (every row to `✓ done`); the header, the `Phase`, the Current
  Bead line and the unticked item were left as written.
- **Outcome:** live.
- **Evidence:** 2026-10-20, 9.0.0: with every bead of the work item closed, active-sync rewrote
  the three status cells and left `Phase: Development`, the Current Bead line and an unticked
  Progress item unchanged.
- **Bead:** `beadloom-cnty`.

### #302

- **Command:** `beadloom review-brief --help`, `beadloom waves --help`, and `beadloom waves
  --parent beadloom-ba9w` on `features/BDL-083-S3f-probe`.
- **Where:** the worktree.
- **Printed:** review-brief's options are `--since --release --json --project`, with no head
  ref. waves's are `--parent --json --project`, with no work-item key. With `--parent
  beadloom-ba9w` the plan still reads `Declared axes: NOT COMPARED — the branch … names no work
  item` and `focus-document: unmeasured`.
- **Outcome:** live (both cases).
- **Evidence:** 2026-10-20, 9.0.0: neither `review-brief` nor `waves` accepts its subject as an
  option, and `waves --parent` on a suffixed branch still left the declared axes uncompared.
- **Bead:** none (`beadloom-tmgp`, which recorded it, is closed). Proposed: "[BDL-UX #302]
  review-brief takes a head ref and waves takes a work-item key, and each prints the subject it
  used and where it came from".

### #299

- **Command:** `beadloom issue-number allocate --holder ""`, `--holder "   "`, then `beadloom
  issue-number check`.
- **Where:** a throwaway project whose `issue_log:` names `log/ISSUES.md` and `log/ledger`.
- **Printed:** `#4 allocated to ` and `#5 allocated to    `, both exit 0, the claims holding
  `**Holder:** ` empty. Before the entries were written, check named the holder of #4 and #5 as
  `> Allocated by beadloom issue-number allocate. The entry's text lives in the` (the next line
  of the file). After `4.` and `5.` were written: `No duplicate, unwritten or unclaimed
  number.`, exit 0.
- **Outcome:** live, with a second face: an empty holder line makes the reader take the
  following line as the holder.
- **Evidence:** 2026-10-20, 9.0.0: `allocate` accepted an empty and a whitespace-only holder
  (exit 0), and `check` then reported the ledger clean.
- **Bead:** `beadloom-l5jb`.

### #297

- **Command:** `beadloom review-brief beadloom-ba9w.24 --release`, then the brief without
  `--release`.
- **Where:** the worktree. `beadloom-ba9w.24` is an S2 fix bead; its review bead
  `beadloom-x94h` depends on it and carries `REVIEW PASSED: pass 2` (2026-10-20 05:35).
- **Printed:** `WITHHELD — bead comments on beadloom-ba9w.24: 4 item(s) stay withheld: no
  verdict is recorded on this bead`, exit 3. The REACHABLE section names four channels (bead
  comments, the work item's documents, commit bodies, the launch prompt) and not `bd show`.
- **Outcome:** live, both halves.
- **Evidence:** 2026-10-20, 9.0.0: `--release` on a fix bead kept 4 comments withheld while the
  review bead depending on it held `REVIEW PASSED`, and the brief does not name `bd show` as a
  channel.
- **Bead:** `beadloom-6rfz`.

### #286

- **Command:** `beadloom review-brief beadloom-ba9w.24` and `beadloom review-brief
  beadloom-rrz5`.
- **Where:** the worktree and the scratch clone.
- **Printed:** `the launch prompt: NOT INSPECTED — nothing in this process can see one, so: if
  your launch prompt carried anything about this change that you did not derive yourself … this
  withholding was defeated before it ran; say so in your verdict`.
- **Outcome:** closed. The entry's Expected is the brief stating the channel it does not cover,
  and it does. The "stronger form" (the launch prompt as an artifact the brief reads) is a
  proposal, not a defect, and needs a harness surface that does not exist.
- **Evidence:** 2026-10-20, 9.0.0: `review-brief` names the launch prompt as a channel it
  cannot inspect and tells the reviewer to declare what reached it.
- **Bead:** none.

### #275

- **Command:** `beadloom waves beadloom-mhi2` (a one-bead plan; the S3 review bead
  `beadloom-rrz5` depends on it).
- **Where:** the worktree, this repository's tracker (1325 beads).
- **Printed:** `every ready bead under beadloom-rrz5 is in this plan (0 of 1 bead(s) under
  beadloom-rrz5 are ready)` and `no bead under beadloom-rrz5 is in progress outside this plan`.
  The bead's work item is `beadloom-ba9w`. The strict xfail `FINDING BDL-068.S6-7` in
  `tests/unit/application/waves/test_the_populations_the_last_four_beads_report_over.py` still
  XFAILs.
- **Outcome:** live.
- **Evidence:** 2026-10-20, 9.0.0: a one-bead plan of `beadloom-mhi2` reported its population
  as the review bead `beadloom-rrz5`, 0 of 1 ready, instead of its epic `beadloom-ba9w`.
- **Bead:** none. Proposed: "[BDL-UX #275] a candidate work item has children: a one-bead plan
  is held against its epic, not against the bead that blocks on it".

### #272

- **Command:** `uv run pytest tests/test_the_flow_checks_an_arrangement_that_is_not_ours.py`
  (the two faces the entry measured `beadloom waves` on), with `-rxX`.
- **Where:** the worktree. A full `waves` reproduction needs a project with a differently
  arranged ACTIVE table and a tracker; the strict xfails pin exactly those verdicts.
- **Printed:** `XFAIL … test_a_bead_table_that_numbers_its_waves_first_still_names_its_beads -
  FINDING BDL-068.S6-5 (BDL-UX #272)` and `XFAIL …
  test_a_bead_named_only_by_a_second_table_is_reported`.
- **Outcome:** live.
- **Evidence:** 2026-10-20, 9.0.0: both strict xfails that pin the focus-document medium's
  first-cell population still fail as expected.
- **Bead:** none. Proposed: "[BDL-UX #272] the focus-document medium reads the bead table
  through active-sync's locator and reports a document with no bead table as a population it
  could not enter".

### #271

- **Command:** `beadloom issue-number allocate --holder beadloom-probe`, then `beadloom
  issue-number check`.
- **Where:** a throwaway project whose ledger holds `0003-the-clean-room-convention.md` and
  whose log's highest number is 2.
- **Printed:** `#3 allocated to beadloom-probe`, claim `0003.md` created beside
  `0003-the-clean-room-convention.md`; check: `1 claim(s)`, one `[unwritten-claim] #3 at
  0003.md`, and no word about the unread file.
- **Outcome:** live.
- **Evidence:** 2026-10-20, 9.0.0: with `0003-the-clean-room-convention.md` in the ledger,
  `allocate` handed out #3 again as `0003.md`, and `check` counted one claim and did not name
  the file it dropped.
- **Bead:** none. Proposed: "[BDL-UX #271] a ledger claim is the number at the start of the
  file name, and a ledger file that states no number is reported, never dropped".

### #269

- **Command:** `beadloom docs quality` and `beadloom scope-check --json` over an RFC whose `##
  Axes` table has the alignment row `|-|-|-|-|-|-|`.
- **Where:** the scratch clone on `features/PROBE1`.
- **Printed:** `RFC.md:8 (axis-without-a-scope-decision)`, where line 8 is the alignment row;
  scope-check `"undecided": 1` for one data row that decides `yes`. `doc_sync/tables.py:40`
  still reads `_SEPARATOR_CELL_RE = re.compile(r"^:?-{2,}:?$")`; both strict xfails `FINDING
  BDL-068.S6-2` XFAIL.
- **Outcome:** live.
- **Evidence:** 2026-10-20, 9.0.0: a valid one-hyphen alignment row was read as an axis row
  with no scope decision by docs quality and counted as one undecided row by scope-check.
- **Bead:** none. Proposed, shared with #268: "[BDL-UX #268, #269] one markdown table-row
  reader: active_table spends doc_sync.tables, whose separator accepts one hyphen
  (`^:?-+:?$`)".

### #268

- **Command:** `grep -rn 'split("|")' src/beadloom` and the strict xfail `FINDING
  BDL-068.S6-1`.
- **Where:** the worktree.
- **Printed:** row readers at `doc_sync/tables.py:57` and
  `application/active_table/table.py:33` (its own body and its own `is_separator_cells`); the
  other hits are `guards/surface.py` (tool matchers) and a site spec file. Three XFAILs: `|`,
  `||` and `|| a | b ||` read differently.
- **Outcome:** live.
- **Evidence:** 2026-10-20, 9.0.0: `active_table/table.py` still splits a table row with its
  own body, and the three disagreeing rows still XFAIL.
- **Bead:** none. Proposed: the bead shared with #269 above.

### #260

- **Command:** none (a design answer). Measured instead: what the shipped roles tell an agent
  to write, and who wrote this epic's ACTIVE.md.
- **Where:** the worktree.
- **Printed:** `.claude/agents/dev.md:94: - Update ACTIVE.md after each significant step.` and
  line 110 `Clear ACTIVE.md for the next bead`. The 24 commits on BDL-083's ACTIVE.md all carry
  `Bead: beadloom-ba9w` (the coordinator); this epic keeps one writer by the launch prompt, not
  by the flow.
- **Outcome:** live. The per-bead write the entry's correction names is still the shipped
  role's instruction.
- **Evidence:** 2026-10-20, 9.0.0: the composed dev role still instructs every developer to
  update ACTIVE.md, and only this epic's launch prompts route those writes to the coordinator.
- **Bead:** none. Proposed: "[BDL-UX #260] ACTIVE.md has one writer: role agents record
  progress on their bead and the coordinator writes the document".

### #257

- **Command:** `beadloom waves mo-r35.1 mo-r35.2`, the beads declaring `refs: shared-lib` and
  `refs: entities-metric`.
- **Where:** a copy of the monorepo fixture with its own `bd init`. Both nodes are `part_of:
  frontend`, which owns `docs/frontend/README.md`; no edge joins them.
- **Printed:** `1 wave(s) for 2 bead(s), 0 serialisation(s)`; `focus-document: unmeasured`; no
  line names `docs/frontend/README.md`.
- **Outcome:** live.
- **Evidence:** 2026-10-20, 9.0.0: two beads under one service node were planned into one wave
  with 0 serialisations, and no line named the service document both would edit.
- **Bead:** none (`beadloom-0mdo.75` is closed). Proposed, shared with #232: "[BDL-UX #257,
  #232] waves names the documents two beads share through a common ancestor node, as a medium
  line, without widening refs".

### #242

- **Command:** none (the harness's launch context). Measured on this bead's own launch.
- **Where:** the main checkout, read-only (`git rev-parse`, `git status`).
- **Printed:** the launch block: `cdaf3f78` at the top, two `.beads/` files modified. Live
  state during the run: HEAD `9f1b6fd2`, plus a modified ACTIVE.md and a neighbour's untracked
  evidence file. No role file carries a duty to derive a tree fact when it is stated (`grep -i
  "launch context\|git status"` over the role files: no hit).
- **Outcome:** live.
- **Evidence:** 2026-10-20: this bead's launch context named HEAD `cdaf3f78` while the tree had
  moved to `9f1b6fd2` within the run, and no composed role tells an agent to re-derive it.
- **Bead:** none. Proposed: "[BDL-UX #242] the role protocol carries a duty: a tree fact is
  derived when it is stated, never read from the launch context".

### #232

- **Command:** the same `beadloom waves` run as #257, after changing only the beads' `refs:`
  notes.
- **Where:** the monorepo fixture copy.
- **Printed:** with `refs: digest` / `refs: file-history` the plan serialised on
  `dependency_edge: application-digest -> file-history`. With `refs: shared-lib` / `refs:
  entities-metric` it reported 0 serialisations. The plan changed with the authored line alone.
- **Outcome:** live. The comparison against `## Axes` shipped; the scope itself is still the
  authored `refs:` line.
- **Evidence:** 2026-10-20, 9.0.0: rewriting two beads' `refs:` notes moved the plan from 1
  serialisation to 0 with no code change.
- **Bead:** none (`beadloom-en0x` is closed). Proposed: the bead shared with #257 above.

### #230

- **Command:** `beadloom review-brief beadloom-ba9w.24` on `features/BDL-083-S3f-probe`.
- **Where:** the worktree.
- **Printed:** `the work item's documents: NOT INSPECTED — the branch
  'features/BDL-083-S3f-probe' names no work item among the project's planning documents`.
- **Outcome:** live.
- **Evidence:** 2026-10-20, 9.0.0: on a branch named `features/BDL-083-S3f-probe` the brief's
  work-item channel read NOT INSPECTED.
- **Bead:** `beadloom-bdnv`.

### #229

- **Command:** `beadloom review-brief beadloom-rrz5 --since origin/main`; `git diff
  origin/main...HEAD -- .beads/issues.jsonl`.
- **Where:** the scratch clone on `features/BDL-083`.
- **Printed:** the change inventory lists `[unowned] .beads/issues.jsonl`; the diff adds 36
  records; REACHABLE names four channels and not the tracker export.
- **Outcome:** live.
- **Evidence:** 2026-10-20, 9.0.0: the brief listed `.beads/issues.jsonl` (36 added records) in
  the change it sends the reviewer to and did not name it as a channel.
- **Bead:** `beadloom-qil0`.

### #224

- **Command:** overwrite `tests/acceptance/features/version_subject.feature` with its first two
  scenarios, run its step tests, then `beadloom ci`.
- **Where:** the scratch clone (restored afterwards).
- **Printed:** before `9 passed`, after `2 passed`; the Gate: `none of 827 scenarios in 160
  files` (834 in the worktree), exit 0, 0 `::error`, no line naming the removed scenarios.
- **Outcome:** live.
- **Evidence:** 2026-10-20, 9.0.0: overwriting a feature file removed 7 scenarios, its tests
  went from 9 passed to 2 passed, and the Gate passed with the count down from 834 to 827 and
  nothing named.
- **Bead:** `beadloom-hdky`.

### #219

- **Command:** `beadloom review-brief beadloom-rrz5 --since origin/main`.
- **Where:** the scratch clone.
- **Printed:** `the commit bodies of the reviewed range: 52 item(s) — read over the range since
  origin/main; 52 of 52 carry a body`, with subjects and body-line counts; no body is withheld.
- **Outcome:** live. Option (b) shipped. No decision between (a), (b) and (c) is recorded on
  the bead.
- **Evidence:** 2026-10-20, 9.0.0: the brief reports 52 of 52 commit bodies as reachable and
  withholds none.
- **Bead:** `beadloom-tm76`. It needs the owner's ruling, and (b)-as-shipped is a candidate for
  closing it.

### #210

- **Command:** `beadloom active-sync`, `beadloom active-sync --stage`, `beadloom active-sync
  --check`, exit codes read without a pipe.
- **Where:** the throwaway bd project, an ACTIVE table of two rows that name no bead.
- **Printed:** `read 2 row(s) and resolved NONE against bd — nothing was compared`; fix mode
  exit 0, `--stage` exit 0, `--check` exit 1. The hook template keeps `grep '^  withheld: '`
  (`hook_templates.py:114`), which matched 0 lines.
- **Outcome:** live. The code-span half is fixed (`beadloom-0mdo.54`).
- **Evidence:** 2026-10-20, 9.0.0: an ACTIVE table that resolved no row exited 0 in fix and
  stage mode, and the hook's filter printed nothing.
- **Bead:** none. Proposed: "[BDL-UX #210] an active-sync run that resolved none of N rows
  reaches the pre-commit hook instead of exiting 0 unseen".

### #187

- **Command:** `bd list --json` and `bd list --all --json`; `beadloom bd-calls`.
- **Where:** the throwaway bd project (1 open, 3 closed); the worktree.
- **Printed:** `bd list --json` is a bare `list` of 1; `--all` is a `list` of 4. `bd-calls`:
  `315 bd call site(s)`, `13 complete-population secured`, 0 unsecured; every `bd list` site
  passes `--all` or `--status`.
- **Outcome:** won't-fix candidate. Our half is closed. The remaining half is bd 1.0.4's
  default, which is steveyegge/beads' to change.
- **Evidence:** 2026-10-20, 9.0.0 and bd 1.0.4: `bd list --json` still returns a bare list with
  closed beads omitted, and every Beadloom call site of `bd list` is secured.
- **Bead:** none. Reason for the owner: External, like #97. Archive our half as closed and move
  the upstream half to Excluded Issues.

### #185

- **Command:** `uv run pytest -p no:randomly
  tests/self_check/process/test_guards_parity.py::TestGuardsAreReadOnly::test_the_live_repo_index_is_byte_identical_after_a_real_evaluation`,
  five times.
- **Where:** the worktree.
- **Printed:** `1 passed` five times (13.9–14.9 s). The test now runs on the self-check
  snapshot rather than the live index, and compares `beadloom.db`, `beadloom.db-wal`,
  `beadloom.db-shm` and `.beads/issues.jsonl` with attribution by file and by timing.
- **Outcome:** closed. The condition the suspicion named, a byte comparison of the main `.db`
  alone over a live WAL index, is gone.
- **Evidence:** 2026-10-20, 9.0.0: the byte-identity test, now over the snapshot and including
  the `-wal`/`-shm` files, passed 5 of 5 runs.
- **Bead:** none.

### #168

- **Command:** `uv run pytest tests/unit/graph/scenarios/test_scenario_binding.py`;
  `pyproject.toml` `addopts`; the `pytest` steps of `.github/workflows/ci.yml`.
- **Where:** the worktree.
- **Printed:** `Using --randomly-seed=4097317977` in the header; `addopts` holds
  `--strict-markers --strict-config -ra` and no seed; CI runs `uv run pytest --cov=…` with no
  seed; `pytest-randomly>=3.15` is still in `dev`.
- **Outcome:** won't-fix candidate.
- **Evidence:** 2026-10-20, 9.0.0: no seed is pinned in CI or `addopts`, and every run prints
  its seed.
- **Bead:** none. Reason for the owner: a red run is replayable from the seed it prints. The
  shared-state channel that made seeds not reproduce (the live index) has been gone since
  BDL-074. Pinning one seed would remove the order-dependence search the plugin was added for
  (BDL-059 S1).

### #156

- **Command:** design-level. Checked: where the work is held.
- **Where:** the tracker and the BDL-083 PRD.
- **Printed:** `beadloom-ba9w.8` open, "Context rot (BDL-UX #156): the composed CLAUDE.md and
  the role files are split by function…". PRD goal 6 names "a short core and companions with an
  output-size contract per role (#156)".
- **Outcome:** live (research note, held).
- **Evidence:** 2026-10-20: #156 is held by `beadloom-ba9w.8` and by BDL-083 goal 6 (S6).
- **Bead:** `beadloom-ba9w.8`.

### #155

- **Command:** design-level. Checked: which of A–F shipped.
- **Where:** the worktree's `src/beadloom` and the tracker.
- **Printed:** A shipped as `beadloom waves` (graph-derived wave shape). C shipped as
  `review-brief` and `beadloom-mr2l.79` (closed, "the reviewer's input excludes the author's
  advocacy (#155 C)"). For B (skip declaration, convergence signal) and E (a machine-readable
  state companion), a search finds no implementation. D and F were not measured.
- **Outcome:** live (research note). Proposal to the owner: archive it as research with A and C
  named as shipped, and carry B, joined with #154 H, as one proposal under Improvements. A wave
  declaring what it did not do is the one item both notes rank highest, and nothing holds it.
- **Evidence:** 2026-10-20, 9.0.0: of #155's items, A (`waves`) and C (`review-brief`,
  `beadloom-mr2l.79`) are shipped, and B and E have no implementation.
- **Bead:** none. Proposed: "[BDL-UX #154 H, #155 B] a wave report states what it did not do
  and why, as a required field".

### #154

- **Command:** design-level. Checked: which of A–I shipped.
- **Where:** the worktree's `src/beadloom` and a `beadloom ci` run.
- **Printed:** C shipped in form: the Gate prints `not run by this gate: the test suite …`,
  `NOT CHECKED`, `PARTLY CHECKED`. I is partly there: `graph/rules/liveness.py` reports a rule
  that cannot match, and S1 D1 makes a gate that did not run a failure, but no mode applies a
  synthetic violation. F: no hit for `dangerously-skip-permissions` or `bypassPermissions` in
  `src/beadloom`, so nothing refuses a role file that relaxes permissions. H: see #155.
- **Outcome:** live (research note). Proposal to the owner: archive it as research with C and
  the rule half of I named as shipped, and carry F as its own proposal. F is the one item with
  a direct, checkable product form: `setup-agentic-flow` refuses and `config-check` flags a
  role file that grants bypass permissions.
- **Evidence:** 2026-10-20, 9.0.0: of #154's items, the "does not cover" notes and rule
  liveness are shipped, and no check reads a role file for a permission relaxation.
- **Bead:** none. Proposed: "[BDL-UX #154 F] config-check flags and setup-agentic-flow refuses
  a role file that grants bypass-style permissions".

### #96

- **Command:** a re-count of the self-audit's figures over `tests/` and `src/`.
- **Where:** the worktree.
- **Printed:** test LOC 261,016 against src LOC 117,989 (2.2:1); 10,939 test functions; 688
  `@pytest.mark.parametrize` (was ~4); 202 accesses to a private attribute on a name other than
  `self`/`cls`, plus 410 private names imported on one-line `from beadloom… import` lines;
  `tests/integration/tui/test_tui.py` 6,053 lines (was ~5,989).
- **Outcome:** live. (a) is largely answered; (b) and (c) are not.
- **Evidence:** 2026-10-20, 9.0.0: parametrize rose from ~4 to 688, while private-attribute
  coupling (202 accesses, 410 private imports) and the 6,053-line TUI test file remain.
- **Bead:** none. Proposed, for S5: "[BDL-UX #96] the tests assert through public surfaces: the
  410 private imports and 202 private-attribute accesses are replaced or ruled, and the
  6,053-line TUI test is reassessed".

## Summary

| Entry | Outcome | Bead |
|---|---|---|
| #355 | live | `beadloom-bdnv` (add #355 to its title) |
| #344 | live (the base half fixed by S1) | proposed |
| #336 | live | proposed |
| #316 | live | proposed |
| #309 | live | `beadloom-ba9w.3` |
| #308 | live | `beadloom-cnty` |
| #302 | live | proposed |
| #299 | live | `beadloom-l5jb` |
| #297 | live | `beadloom-6rfz` |
| #286 | closed | none |
| #275 | live | proposed |
| #272 | live | proposed |
| #271 | live | proposed |
| #269 | live | proposed (shared with #268) |
| #268 | live | proposed (shared with #269) |
| #260 | live | proposed |
| #257 | live | proposed (shared with #232) |
| #242 | live | proposed |
| #232 | live | proposed (shared with #257) |
| #230 | live | `beadloom-bdnv` |
| #229 | live | `beadloom-qil0` |
| #224 | live | `beadloom-hdky` |
| #219 | live, needs a ruling | `beadloom-tm76` |
| #210 | live (the code-span half fixed) | proposed |
| #187 | won't-fix candidate (External; our half closed) | none |
| #185 | closed | none |
| #168 | won't-fix candidate | none |
| #156 | live (research) | `beadloom-ba9w.8` |
| #155 | live (research; proposal to archive, B carried) | proposed (shared with #154 H) |
| #154 | live (research; proposal to archive, F carried) | proposed |
| #96 | live | proposed (S5) |

Totals: 2 closed, 27 live, 2 won't-fix candidates, 0 not reproducible, 0 not this area. Of the
27 live entries, 10 hold an existing open bead and 17 have a proposed title, which comes to 15
new beads because three proposals each hold a pair.

# S3a — the Gate, CI, hooks, rooms, scope-check, ownership and issue-log entries, re-measured

- **Date:** 2026-10-20
- **Bead:** `beadloom-k6f1`
- **Version:** Beadloom 9.0.0 as S2 ships it (`beadloom --version` prints `9.0.0`): a git
  worktree of `features/BDL-083` at `cdaf3f78428061e51479723f59d666d952bf774e`.
  `git diff --stat 41245dc7 cdaf3f78 -- src` prints nothing, so the code measured is that of
  `main` at `41245dc7`.
- **Machine:** macOS 27.0 (Darwin 27.0.0), arm64, CPython 3.12.12 from `uv sync --frozen` in
  the worktree with CI's extras (`dev`, `languages`, `tui`, `watch`, `graphql`), except where
  an entry names another set. bd 1.0.4, git 2.49.0.
- **Index and fixtures:** the worktree's own index, built inside it; the main checkout's index
  was not read or written. Fixtures are fresh committed copies of `tests/fixtures/monorepo`
  (`.fixture` names restored, `git init -b main`, `bd init --prefix fx` where needed).
- **Room:** one room, this machine. No Linux leg, no Windows checkout, no CI run and no other
  interpreter was entered. This agent's `gh api` calls for the repository's settings timed out
  (TLS handshake timeout), so no live repository setting was read. GitHub itself was reachable
  from this machine: S3d and the S3 review read `ci.yml` job logs with `gh run view`.
  (Corrected on 2026-10-20 by the S3 fix bead `beadloom-ba9w.27`.)
- **A limit of the measurement, stated once.** The session scratchpad is shared with the other
  measure agents and holds an older fixture repository at its top. One room for #334 was first
  built inside that foreign work tree; its `ci` read the refusal of S2e (`the git root is
  above the project root`) and was discarded. Every result below comes from rooms and
  fixtures outside any foreign `.git`.

### #357
- **Command:** `bd init`, `beadloom install-hooks`, `git push`, `beadloom doctor`
- **Where:** the monorepo fixture with `bd init --prefix fx` and a bare remote.
- **Printed:**
  ```
  git config core.hooksPath   -> <fixture>/.beads/hooks      (written by bd init)
  beadloom install-hooks      -> Installed pre-commit hook (mode: warn).
                                 Installed pre-push hook (Beadloom Gate, blocking).   rc 0
  ls .git/hooks               -> pre-commit pre-push   (grep -c beadloom .beads/hooks/* -> 0, 0)
  git push -u origin main     -> * [new branch] main -> main      rc 0, no Gate line
  beadloom doctor | grep hook -> nothing
  ```
  Control: `git config core.hooksPath .git/hooks`, the next `git push` prints
  `Running Beadloom Gate (beadloom ci)...` and the Gate's steps.
- **Outcome:** live.
- **Evidence:** 2026-10-20, 9.0.0 (S2): on the monorepo fixture after `bd init`,
  `install-hooks` exits 0 writing `.git/hooks` while `core.hooksPath` points at
  `.beads/hooks`, `git push` exits 0 with no Gate line, and `doctor` names nothing.
- **Bead:** `beadloom-ba9w.23`.

### #354
- **Command:** `bd merge-slot acquire --holder <bead>` in a second clone after `git pull` and
  `bd import`
- **Where:** the monorepo fixture with bd, a bare remote, `install-hooks`, and
  `core.hooksPath` reset to `.git/hooks` (without the reset nothing below runs, see #357).
- **Printed:**
  ```
  acquire --holder fx-8xu; commit with the export; git push    -> rc 1
  Landing lock: REFUSED -- the export this push lands (.beads/issues.jsonl at 0838b8f) holds the
  merge slot for fx-8xu, a bead this push carries.
  The landing sequence is acquire -> commit -> release -> ...:  bd merge-slot release --holder fx-8xu
  release; bd export; commit the export; git push               -> rc 0
  Landing lock: clean -- the export at c0f8490 shows the merge slot free
  second clone: git clone; bd init; bd import (2 issues); bd merge-slot acquire --holder fx-other
  ✓ Acquired merge slot: fx-merge-slot                           -> rc 0
  ```
- **Outcome:** closed; the check fires only where git runs the installed hooks (see #357).
- **Evidence:** 2026-10-20, 9.0.0 (S2): on the monorepo fixture a push whose export holds the
  slot for its own bead is refused (rc 1) naming the release; the ordered landing pushes with
  `Landing lock: clean`, and a second clone's `acquire` exits 0.
- **Bead:** none.

### #353
- **Command:** `beadloom sync-check` on a Windows checkout; `declared_pairs` compared between
  the two platforms
- **Where:** not reproducible here: no Windows room exists on this machine, and the Windows CI
  leg was withdrawn. Measured instead, in the worktree: the surface ledger and the
  simulated-separator tests.
- **Printed:**
  ```
  .beadloom/sync-surface.json -> {'declared_docs': 143, 'declared_pairs': 845, 'pairs': [845 entries], ...}
  sqlite3 beadloom.db "select count(*) from file_index where path like '%\%'"  -> 0
  pytest (the POSIX-index scenarios + the declared-surface tests) -> 104 passed
  ```
- **Outcome:** not reproducible here. The half that is platform-free is closed: the ledger now
  carries the pair list beside the count.
- **Evidence:** 2026-10-20, 9.0.0 (S2), Darwin only: `sync-surface.json` lists its 845 pairs,
  and the simulated-separator scenarios pass (104 tests); the Windows checkout itself was not
  entered.
- **Bead:** none; the separator half stays unmeasured until a Windows room exists.

### #335
- **Command:** `beadloom clean-room <bead> --carry ...`
- **Where:** the monorepo fixture with bd and a claimed bead, after
  `git mv backend/src/digest/sections.py backend/src/digest2/sections.py` and a neighbour's
  edit in `docs/architecture.md`.
- **Printed:**
  ```
  beadloom clean-room fx-zj2 --at <dir> --carry backend/src/digest/sections.py
      --carry backend/src/digest2/sections.py --no-environment                      rc 0
    carried from the working tree: backend/src/digest2/sections.py
    deleted in the room, because HEAD holds them and the working tree does not: backend/src/digest/sections.py
    the working tree differs from HEAD in 3 file(s) this room does not carry; ...
      modified  docs/architecture.md
    - a carried file is copied whole from the working tree, so an edit a neighbour made ...
  ```
- **Outcome:** closed; a shared file is still copied whole, and the room names that limit.
- **Evidence:** 2026-10-20, 9.0.0 (S2): on the monorepo fixture a carried path the tree no
  longer holds builds the room at rc 0 and is deleted there, and the files the room does not
  carry are named.
- **Bead:** none.

### #334
- **Command:** `beadloom config-check` and `beadloom ci` in a room and in a worktree of a clean
  HEAD
- **Where:** the monorepo fixture composed by `beadloom setup-agentic-flow` and committed; the
  checkout, a `git worktree` of HEAD, and a room built by `clean-room`.
- **Printed:**
  ```
  checkout: config-check rc 0;  worktree: config-check rc 0, ci rc 0;  room: config-check rc 0, ci rc 0
  ::notice::config-check PASS: agent-config in sync; compared .claude/CLAUDE.md against its
  composition from .beadloom/flow.yml, layers core, stack:python, with the project name 'h334'
  from .claude/CLAUDE.md, the heading its last composition wrote; no file declares the name ...
  ```
- **Outcome:** closed.
- **Evidence:** 2026-10-20, 9.0.0 (S2): on the composed monorepo fixture `config-check` exits 0
  in the checkout, a worktree and a room, `ci` exits 0 in the last two, and the verdict names
  what it compared and where the name came from.
- **Bead:** none.

### #333
- **Command:** `beadloom clean-room <bead> --at <scratchpad> --carry ...`
- **Where:** the monorepo fixture with bd, one edit carried in `backend/src/digest/sections.py`.
- **Printed:**
  ```
  rc 0;  measured project: backend/pyproject.toml (it owns 1 of the 1 carried file(s))
    environment: built by uv in 10.399s with extras none, installed from backend/uv.lock with `uv sync --frozen`
  Measure in the room, not in the tree:
    PYTHONPATH=<room>/backend/src <room>/backend/.venv/bin/python -m pytest <room>/backend/tests
  What this room cannot answer:
    - it carries no .git: ... a test or tool that reads git (a commit's hash, ...) fails or skips here
  the printed pytest line, run as printed -> 1 passed in 0.01s
  ```
- **Outcome:** closed.
- **Evidence:** 2026-10-20, 9.0.0 (S2): on the monorepo fixture the room builds its environment
  from `backend/uv.lock`, prints a hint for `backend/` that runs as printed (1 passed), and
  names the no-`.git` limit.
- **Bead:** none.

### #332
- **Command:** `beadloom rooms`, `beadloom ci`
- **Where:** the monorepo fixture (`backend/pyproject.toml`, `.gitlab-ci.yml`).
- **Printed:**
  ```
  Declared rooms: 2, entered by this run: 0
    [  ] image=python:3.12-slim python=3.12    .gitlab-ci.yml: backend-tests
    [  ] image=node:22-slim    .gitlab-ci.yml: frontend-tests
  ::notice::room Darwin arm64 · CPython 3.12.12 · ... — 0 of 2 declared room(s) entered by this run
  renamed to Jenkinsfile: rooms: not derived — ... declared in `Jenkinsfile`, which this census does not read
  ```
- **Outcome:** closed.
- **Evidence:** 2026-10-20, 9.0.0 (S2): on the monorepo fixture `rooms` reads 2 legs from
  `.gitlab-ci.yml` and `ci` prints `0 of 2`, and a pipeline in a file the census does not read
  is named as a skip.
- **Bead:** none.

### #331
- **Command:** `beadloom issue-number check`, `beadloom ci`
- **Where:** the monorepo fixture with `issue_log: {path: ISSUES.md, ledger: issues/}` declared
  and no such file.
- **Printed:**
  ```
  The declared issue log could not be read — no leg ran.            rc 1
  ::notice::issue-log FAIL: declared issue log missing
  ```
- **Outcome:** closed.
- **Evidence:** 2026-10-20, 9.0.0 (S2): with a declared log the tree does not hold,
  `issue-number check` exits 1, agreeing with the Gate's `issue-log FAIL`.
- **Bead:** none.

### #330
- **Command:** `beadloom ci` on a branch cut from a feature branch not yet merged to trunk
- **Where:** the monorepo fixture with bd: `main`; `features/W1` changes two frontend files;
  `features/W2` cut from it adds `features/W2/RFC.md` (axis `digest`) and edits
  `backend/src/digest/sections.py`, its commit carrying `Bead: fx-64f`.
- **Printed:**
  ```
  ::notice::scope-check PASS: 0 path(s) outside the axes W2 declares (...RFC.md); 1 judged, 1 owned
  by no node; against 5ec7d59 (the merge-base with features/W1, the branch this one was cut from;
  2 file(s) attributed to the parent branch)
  control, scope-check --base main: frontend/src/shared/lib/percent.ts and
  frontend/src/widgets/kpi-panel/ui/KpiPanel.ts reported outside every axis
  ```
- **Outcome:** closed.
- **Evidence:** 2026-10-20, 9.0.0 (S2): on a stacked branch of the monorepo fixture
  `scope-check` judges against the merge-base with the parent branch, prints that base and
  attributes the parent's 2 files to it (0 outside, where `--base main` reports both).
- **Bead:** none.

### #329
- **Command:** `beadloom ci` on a single-bead tree with the branch's older commits
- **Where:** the stacked fixture of #330; then a probe commit, bound to the same bead, that adds
  an FSD violation (`import '@/app/styles'` in a widget spec).
- **Printed:**
  ```
  ::notice::attributed by the files the commits carrying `Bead: <id>` changed, over 5ec7d59..HEAD
  ::notice::fx-64f owns no finding: its 1 commit(s) changed none of the files these findings are about
  ::notice::unattributed: 17 finding(s) no claimed bead's commits on 5ec7d59..HEAD explain
  probe: ::notice::owned by fx-64f: 2 finding(s), by the files its commits changed
  ```
- **Outcome:** closed.
- **Evidence:** 2026-10-20, 9.0.0 (S2): on the monorepo fixture a bead owns no finding about
  files its commits did not change, owns the 2 findings its own commit caused, and the summary
  prints the rule it attributed by.
- **Bead:** none.

### #327
- **Command:** `.git/hooks/pre-commit` (its ruff leg)
- **Where:** the monorepo fixture with the composed hooks; a staged edit under `backend/`;
  `git commit` under a PATH holding `beadloom`, `bd` and `uv` and no `ruff`.
- **Printed:**
  ```
  Running ruff check on the staged Python file(s)...
  error: Failed to spawn: `ruff`
    Caused by: No such file or directory (os error 2)
  Ruff: NOT CHECKED in backend/ -- ruff did not run (exit 2); its own words are above
  control, ruff on PATH: Ruff: 1 staged file(s) checked in backend/ -- clean
  ```
- **Outcome:** closed.
- **Evidence:** 2026-10-20, 9.0.0 (S2): with no ruff on PATH the composed pre-commit hook shows
  ruff's own error and prints `Ruff: NOT CHECKED in backend/ ... (exit 2)` instead of
  "violations", and runs in the Python project that owns the file.
- **Bead:** none.

### #326
- **Command:** `git push` with the composed pre-push hook; `git commit` with the composed
  pre-commit hook
- **Where:** the stacked fixture of #330 with `install-hooks` and `core.hooksPath` reset; a
  staged widget file importing `@/app/styles`.
- **Printed:**
  ```
  commit (mode warn):  Lint over this commit: 1 node(s) own 1 of 1 staged path(s) (widgets-kpi-panel);
                       1 error(s) ... ⛔ [ERROR] fsd-layers ... Layer violation: 'widgets-kpi-panel'
                       (layer 'widgets', index 2) depends on 'app-styles' (layer 'app', index 0)   rc 0
  commit (mode block): Error: architecture lint errors on the node(s) this commit touches — commit blocked  rc 1
  push, PATH without beadloom:
    Beadloom Gate did not run: 'beadloom' is not on the PATH this hook runs with, so this push was
    not judged and is refused.                                                          rc 1
  ```
- **Outcome:** closed. Two items of the entry's Expected are not built: a `guard architecture`
  on `PostToolUse` (`beadloom guard` registers `bead-claimed` and `working-branch` only), and a
  `review-brief` that requires a recorded tree run. Both are additions, not the defect.
- **Evidence:** 2026-10-20, 9.0.0 (S2): on the monorepo fixture the pre-push hook without
  `beadloom` on PATH refuses the push (rc 1) with a sentence, and the pre-commit hook lints the
  staged node and names the FSD violation (blocking in block mode).
- **Bead:** none.

### #325
- **Command:** `beadloom init`, `doctor`, `install-hooks`, `sync-check --since <ref>`,
  `diff --since`, `export`
- **Where:** the monorepo fixture copied into `sub/` of a git repository whose root is one
  level up; `beadloom reindex` run in `sub/`; `init --yes` in an empty sibling `sub2/`.
- **Printed:**
  ```
  init --yes            rc 1  Error: init refused — the git root is above the project root: ...   (nothing written)
  doctor                rc 1  [ERR] Project root refused: the git root is above the project root: ...
  sync-check --since    rc 1  Error: sync-check --since refused — the git root is above the project root: ...
  install-hooks         rc 1  Error: .git/hooks not found. Is this a git repository?
  diff --since HEAD     rc 1  12 added, 0 changed, 0 removed nodes; 11 added, 0 removed edges
  export                rc 0  commit_sha: null
  composed CLAUDE.md    "**The project root is the git root.**" (line 56)
  ```
- **Outcome:** live. The Expected is delivered. The residual S2e left to S3 remains:
  `diff --since` answers `12 added` over an empty side, the false-answer class the entry was
  filed on, and `install-hooks` asks "Is this a git repository?" inside one. `review-brief`
  was not run (it needs a review bead in a tracker inside the subfolder).
- **Evidence:** 2026-10-20, 9.0.0 (S2): one folder below its git root, `init`, `doctor` and
  `sync-check --since` refuse by name at rc 1, while `diff --since HEAD` reports every node
  added and `install-hooks` fails on `.git/hooks not found`.
- **Bead:** proposed: "[BDL-UX #325] diff --since, install-hooks and review-brief refuse a
  project root below the git root by name, as init, doctor and sync-check --since do".

### #321
- **Command:** `.github/workflows/ci.yml`; the repository's Actions settings
- **Where:** the workflow file in the worktree. The live settings are not reproducible here:
  every `gh api` read failed (`unexpected EOF`, TLS handshake timeout).
- **Printed:**
  ```
  ci.yml:42-44  permissions: {contents: write, pull-requests: write}   (workflow level, no job overrides)
  ci.yml:448     runs-on: [self-hosted, ai-techwriter]      (no `if:` with head.repo.full_name in the job)
  ci.yml:124   # The two check-runs are NOT yet part of main's live branch protection (7
  ```
- **Outcome:** live.
- **Evidence:** 2026-10-20, 9.0.0 (S2): `ci.yml` still grants `contents: write` and
  `pull-requests: write` at the workflow level, the self-hosted `ai-techwriter` job has no
  same-repository condition, and the stale "7 required contexts" comment stands at line 124.
- **Bead:** `beadloom-dlb6` (its review bead is `beadloom-6hh3`).

### #318
- **Command:** `beadloom ci`
- **Where:** three copies of the monorepo fixture whose `.beadloom/config.yml` raises inside
  steps (the shapes of #287).
- **Printed:**
  ```
  rc 1, 0 tracebacks, all eleven steps report:
  ::notice::reindex ERROR: crashed — ParserError: while parsing a flow sequence
  ::notice::docs-audit ERROR: ...; ::notice::scope-check ERROR: ...; ::notice::doctor PASS: ...
  ::error::reindex: the reindex step raised ParserError: ... (raised in parse_flow_sequence_entry,
  parser.py:483); ... the other steps' results in this run still stand
  ```
- **Outcome:** closed.
- **Evidence:** 2026-10-20, 9.0.0 (S2): an exception inside a Gate step reads `ERROR` with its
  class and the raising frame, every later step still reports, and `ci` exits 1 with no
  traceback.
- **Bead:** `beadloom-ba9w.13` (closed).

### #311
- **Command:** `beadloom clean-room <bead> --carry ...`
- **Where:** this repository's worktree; `beadloom clean-room beadloom-k6f1 --carry README.md`.
- **Printed:**
  ```
  environment: built by uv in 0.704s with extras dev+graphql+languages+mutation+tui+watch,
  installed from uv.lock with `uv sync --frozen`
  room: gherkin-official 29.0.0, pytest-bdd 8.1.0      uv.lock: 29.0.0, 8.1.0
  ```
- **Outcome:** closed.
- **Evidence:** 2026-10-20, 9.0.0 (S2): a room of this repository installs from `uv.lock` with
  `uv sync --frozen`, and its gherkin-official 29.0.0 and pytest-bdd 8.1.0 are the locked ones.
- **Bead:** `beadloom-ba9w.1` (closed).

### #310
- **Command:** `uv run pytest ...` after `uv sync --all-extras`
- **Where:** the worktree, synced with `--all-extras` (`fastembed` and `sqlite_vec` import), then
  re-synced with CI's extras as the control. Three files run: the `room_extras` scenario steps,
  `tests/self_check/process/test_room_dependent_assertions.py`,
  `tests/integration/application/rooms/test_room_extras.py`.
- **Printed:**
  ```
  --all-extras: 6 failed, 53 passed
    test_room_extras_steps.py::test_a_leg_installing_different_extras_is_not_entered_and_says_which
    AssertionError: ['extras: this run has all, dev, graphql, languages, mutation, tui, watch and the
    leg does not; os: the leg is ubuntu-latest (Linux) and this run is Darwin']
    test_room_dependent_assertions.py::...[Linux/3.10], [Linux/3.11], [Linux/3.12], [Linux/3.13], [Darwin/3.12]
  CI extras:    59 passed
  ```
- **Outcome:** live.
- **Evidence:** 2026-10-20, 9.0.0 (S2): with every extra installed the scenario "a leg
  installing different extras is not entered" fails and takes down 5 room-suite cases (6 of 59
  red), against 59 passed under CI's extras.
- **Bead:** `beadloom-ba9w.2`.

### #301
- **Command:** `beadloom docs audit`, and `beadloom ci` on a version-bump commit
- **Where:** the worktree with `__version__` set to `10.0.0` in `src/beadloom/__init__.py` (the
  version the audit reads), restored afterwards. This entry is docs-audit and overlaps S3b's
  area (#205, #190); it was assigned here and is measured here.
- **Printed:**
  ```
  baseline:  84 verified mention(s), No stale mentions found
  bumped:    66 stale mention(s) across 20 file(s)
  ::notice::docs-audit FAIL: 66 stale fact(s); ...                ci rc 1
  docs/guides/ci-setup.md:224        "Through 9.0.0 that push went through, ..."
  docs/guides/parallel-waves.md:315  "fixture with bd 1.0.4: after the 9.0.0 order (acquire, ..."
  docs/getting-started.md:415        "up to 9.0.0 Cursor received a 17-line pointer instead (BDL-083 S2h)"
  docs/services/cli.md:56, :435, :633  "where 9.0.0 exited 0 ...", "Under 9.0.0 that push ..."
  ```
  The `docs_audit.ignore` triples are still `{path, fact, value}` with no line.
- **Outcome:** live, and larger than when filed: the S2 documents added dated "through 9.0.0"
  sentences, and the next bump will flag them.
- **Evidence:** 2026-10-20, 9.0.0 (S2): a simulated bump to 10.0.0 turns `docs audit` to 66
  stale mentions in 20 files and `ci` to rc 1, most of them past-tense sentences about 9.0.0
  ("through 9.0.0", "where 9.0.0 exited 0").
- **Bead:** proposed: "[BDL-UX #301] a version beside a dated or attributed measurement reads
  as history: a bump to 10.0.0 flags 66 mentions, most of them past-tense 9.0.0 sentences".

### #300
- **Command:** `beadloom ci` on a detached HEAD, as `actions/checkout` leaves a pull request
- **Where:** the stacked fixture of #330, `git checkout --detach` at `features/W2`; the job's
  environment variables are set by hand. The CI run itself was read afterwards (S3 review, and
  `beadloom-ba9w.27`): PR #107, run 39382706135, gate job 118495243247 printed
  `scope-check PASS: 55 path(s) outside the axes BDL-083 declares ...; 55 judged, 161 owned by
  no node; against origin/main` (`gh run view --job 118495243247 --log`).
- **Printed:**
  ```
  no CI variable:                      scope-check SKIP: skipped — no branch is checked out, ...
  GITHUB_HEAD_REF=features/W2:         scope-check PASS: 0 path(s) outside the axes W2 declares ...;
                                       against 5ec7d59 (the merge-base with features/W1, ...)
  CI_MERGE_REQUEST_SOURCE_BRANCH_NAME: the same PASS line
  ```
- **Outcome:** closed.
- **Evidence:** 2026-10-20, 9.0.0 (S2): on a detached HEAD of the monorepo fixture,
  `scope-check` judges the work item named by `GITHUB_HEAD_REF` or by GitLab's
  `CI_MERGE_REQUEST_SOURCE_BRANCH_NAME`, where without them it skips.
- **Bead:** `beadloom-tsqz` (closed). Confirmed on CI by PR #107's gate job log, above.

### #287
- **Command:** `beadloom ci`
- **Where:** three copies of the monorepo fixture: `issue_log: path: [unclosed` appended; a
  config whose top level is a list; a config holding byte `0xe9`.
- **Printed:**
  ```
  unclosed: rc 1, 0 tracebacks; reindex, docs-audit, docs-quality, scope-check ERROR: crashed — ParserError
  list:     rc 1, 0 tracebacks; reindex ERROR: crashed — AttributeError: 'list' object has no attribute 'get'
            (raised in resolve_scan_paths, scan_paths.py:34)
  latin1:   rc 1, 0 tracebacks; reindex, docs-quality, scope-check ERROR: crashed — UnicodeDecodeError
  ::error::reindex: the reindex step raised ParserError: while parsing a flow sequence
    in "<unicode string>", line 15, column 9: ... — this is a defect in the checker, not a finding
    about the project
  in every shape: ::notice::sync-check PASS: 0 pair(s) fresh
  ```
- **Outcome:** live. The traceback is gone, which was the filed shape. The Expected is not met:
  a config that cannot be read is reported as a defect in the checker, `in "<unicode string>"`,
  in up to four steps, and not as one finding against `.beadloom/config.yml` with its line and
  the repair. `sync-check` reads `PASS` over 0 pairs after the reindex crashed.
- **Evidence:** 2026-10-20, 9.0.0 (S2): the three unreadable-config shapes give `ci` rc 1 with
  no traceback, each as `ERROR: crashed` in one to four steps and called "a defect in the
  checker", with no step naming `.beadloom/config.yml` as the file to repair.
- **Bead:** proposed: "[BDL-UX #287] an unreadable .beadloom/config.yml is one finding against
  the file (line, column, the repair), not a checker ERROR in four steps"; related
  `beadloom-ovam`.

### #280
- **Command:** `beadloom rooms`
- **Where:** the worktree, under `LC_ALL=C PYTHONUTF8=0 PYTHONCOERCECLOCALE=0`.
- **Printed:**
  ```
  This run is in: Darwin arm64 · CPython 3.12.12 · 10 cores · extras ... · locale ascii
  python -c "locale.getpreferredencoding(False), sys.getfilesystemencoding()"  -> US-ASCII utf-8
  grep -c getfilesystemencoding src/beadloom/application/rooms.py  -> 0
  ```
- **Outcome:** live.
- **Evidence:** 2026-10-20, 9.0.0 (S2): under the locale leg's knobs on Darwin, `rooms` reports
  `locale ascii` and nothing about the filesystem codec, which is `utf-8` in the same process.
- **Bead:** proposed: "[BDL-UX #280] the room census reports the filesystem codec beside the
  text codec (Darwin under LC_ALL=C: locale ascii, fs utf-8)".

### #276
- **Command:** `beadloom ci --format github`
- **Where:** the worktree, the same run in `--format rich` and `--format github`.
- **Printed:** the ownership block is the same eight lines in both formats, one `::notice::` per
  line on the GitHub surface:
  ```
  ::notice::attributed by the files the commits carrying `Bead: <id>` changed, over 8b375533..HEAD
  ::notice::beadloom-k6f1 owns no finding: no commit on 8b375533..HEAD carries `Bead: beadloom-k6f1`
  ::notice::unattributed: 695 finding(s) no claimed bead's commits on 8b375533..HEAD explain (19 about ...)
  ::notice::no finding of this run is owned by a bead claimed now (claimed: beadloom-3jlv, ...)
  ```
  The `unowned` verdict whose caveat was dropped no longer exists (S1c), and every qualifying
  line travels with the headline.
- **Outcome:** closed.
- **Evidence:** 2026-10-20, 9.0.0 (S2): on this repository `ci --format github` emits the
  ownership block line for line as the rich format prints it, one notice per line.
- **Bead:** none.

### #273
- **Command:** `beadloom clean-room <bead>`, then `beadloom ci` inside the room
- **Where:** a room of the composed monorepo fixture (#334), and the holder test in the
  worktree.
- **Printed:**
  ```
  room's own report: - it carries no .git: a freshness check inside it has no baseline, ...  (no number)
  ci in the room:    ::notice::sync-check WARN: 0 pair(s) fresh, 21 NOT VERIFIED (no baseline — index rebuilt)   rc 0
  pytest tests/test_the_room_and_the_claim_it_supports.py -> 8 passed, 1 xfailed
    XFAIL ...test_the_room_states_how_many_pairs_a_freshness_check_there_cannot_enter - FINDING BDL-068.S6-6
  ```
- **Outcome:** live.
- **Evidence:** 2026-10-20, 9.0.0 (S2): the room still states the cause ("no baseline") and no
  population, while `ci` inside it reads 0 of 21 pairs verified at rc 0; the strict xfail
  holding the finding still xfails.
- **Bead:** proposed: "[BDL-UX #273] clean-room states the population its freshness check cannot
  enter (0 of N pairs), not only the cause".

### #246
- **Command:** `beadloom ci`, `beadloom mutation --only`
- **Where:** the worktree.
- **Printed:**
  ```
  the Gate's steps: no mutation step line; src/beadloom/application/gate.py:974-985 calls
  check_mutation_scope only
  beadloom mutation --help: --stats, --target, --only ("printed as not judged by this run"), ...
  no option or file records the last run that measured a declared target
  ```
- **Outcome:** live: the half the 2026-09-29 re-measurement left open is unchanged.
- **Evidence:** 2026-10-20, 9.0.0 (S2): the Gate still asks only whether a declared mutation
  target could be mutated, and nothing records when one was last measured.
- **Bead:** proposed: "[BDL-UX #246] a declared mutation target no run has measured: record
  the last measured run per target and let the Gate report one absent or older than a stated
  age".

### #226
- **Command:** `beadloom ci` under `git push` (stdout a non-blocking pipe)
- **Where:** the worktree; `beadloom ci --format github --no-reindex` with stdout and stderr
  on a non-blocking pipe whose reader starts 5 seconds late; the composed pre-push hook read.
- **Printed:**
  ```
  rc=0 bytes=235510 secs=8.0
  BlockingIOError in output: False
  the same run to a regular pipe: 235510 bytes
  pre-push: the verdict is read from the `--tee` copy (the hook's comment cites BDL-UX #226);
  no "Gate failed (docs stale / lint / coverage / doctor)" sentence remains
  ```
- **Outcome:** closed.
- **Evidence:** 2026-10-20, 9.0.0 (S2): the Gate's 235510-byte report reaches a non-blocking
  pipe read 5 seconds late in full, at rc 0, with no `BlockingIOError`.
- **Bead:** `beadloom-jwfc` (closed).

### #199
- **Command:** `beadloom ci` (its `lint` line)
- **Where:** the monorepo fixture: the baseline; one added `require` rule over `kind: adr`, of
  which the graph holds none; one added `require` rule at `severity: warn` that real nodes
  violate.
- **Printed:**
  ```
  baseline:  lint PASS: 0 error(s), 2 warning(s), 1 statement(s) at info, backend-layers judged ...
  inert:     lint PASS: 0 error(s), 3 warning(s), 1 statement(s) at info, backend-layers judged ...
             ::warning::inert-probe: Rule 'inert-probe' cannot fire: its `for` kind 'adr' matches none of the 12 nodes
  warned:    lint PASS: 0 error(s), 6 warning(s), 1 statement(s) at info, backend-layers judged ...
  ```
- **Outcome:** live. The line counts `info` statements (S1 fix 1) and names the layer rules'
  reach, and a rule that cannot fire still adds one to `N warning(s)` with nothing on the line
  to tell it from a found warning.
- **Evidence:** 2026-10-20, 9.0.0 (S2): on the monorepo fixture a rule that cannot fire moves
  the Gate's lint line from `2 warning(s)` to `3 warning(s)`, the same shape a found warning
  gives, with no inert count on the line.
- **Bead:** proposed: "[BDL-UX #199] the Gate's lint line counts the rules that cannot fire
  apart from the warnings found".

### #198
- **Command:** `beadloom ci` in a tree that is not a git work tree
- **Where:** `git archive HEAD | tar -x` of this repository's worktree, no `git init`.
- **Printed:**
  ```
  ::notice::reindex PASS: reindexed
  ::notice::sync-check WARN: 0 pair(s) fresh, 845 NOT VERIFIED (no baseline — index rebuilt)
  ::notice::scope-check SKIP: skipped — no branch is checked out, ...
  ci rc 0
  ```
- **Outcome:** won't-fix candidate: unchanged, and the entry asks for a decision. For keeping
  WARN: a tree without git cannot be verified, and blocking punishes a checkout style. Against:
  the clean room has no `.git` by construction and is where verdicts are taken, at rc 0. #273
  holds the reporting half (the room names the population). The owner rules.
- **Evidence:** 2026-10-20, 9.0.0 (S2): over a `git archive` of this repository `ci` exits 0
  with `sync-check WARN: 0 pair(s) fresh, 845 NOT VERIFIED`.
- **Bead:** none until the owner rules.

### #178
- **Command:** the `ai-techwriter` GitHub Actions job
- **Where:** read in the code it runs, `src/beadloom/ai_agents/ai_techwriter/cli.py`, and not
  run: the job runs on a self-hosted runner, so it cannot be started from here. Its logs are
  readable: of the 10 `ai-techwriter` jobs of the `ci.yml` runs from 2026-10-11 to 2026-10-20, nine
  concluded `success` and one was skipped (job 117989950791 of run 39227020301); none of the nine
  printed `could not run (infra)` (`gh run view --job <id> --log`,
  read by `beadloom-ba9w.27`), so no log holds an `infra` verdict to measure.
- **Printed:**
  ```
  cli.py:273  if verdict == VERDICT_INFRA: _report_infra(...); return
  _report_infra docstring: "Surface an ``infra`` verdict WITHOUT blocking the PR (exit 0)."
  emits ::warning title=AI tech-writer::could not run (infra) — docs were NOT checked on this PR; ...
  and a best-effort PR/MR note; a flagged verdict raises Exit(1)
  ```
- **Outcome:** won't-fix candidate. The exit 0 is a recorded decision (annotation and PR note
  instead of a red), and no exit code gives an Actions job a `neutral` conclusion. The two
  honest moves are the owner's: exit 1 on `infra` so a human re-runs it, or drop
  `ai-techwriter` from the required set.
- **Evidence:** 2026-10-20, 9.0.0 (S2), read in the code and not run: an `infra` verdict of the
  tech-writer still exits 0 with a `::warning::` annotation, so the required check reports
  success over docs it did not check.
- **Bead:** none until the owner rules.

## Found while measuring, not filed

- **The merge slot reads as a claimed bead.** `ci`'s ownership block on this repository listed
  `beadloom-merge-slot owns no finding` among the claimed beads while a neighbour held the slot
  (the slot bead is then `in_progress`). A slot is not work (gate-ownership).
- **`clean-room --at` inside a foreign work tree** is built without a word, and `ci` inside it
  fails on S2e's refusal (`the git root is above the project root`), while the room's report
  says `it carries no .git` — true of the room, false of what git sees there.

## Summary

| Entry | Outcome | Bead |
|---|---|---|
| #357 | live | `beadloom-ba9w.23` |
| #354 | closed | none |
| #353 | not reproducible here (no Windows room); the ledger half closed | none |
| #335 | closed | none |
| #334 | closed | none |
| #333 | closed | none |
| #332 | closed | none |
| #331 | closed | none |
| #330 | closed | none |
| #329 | closed | none |
| #327 | closed | none |
| #326 | closed | none |
| #325 | live (the residual left to S3) | proposed: diff --since, install-hooks, review-brief refuse below the git root |
| #321 | live | `beadloom-dlb6` (review `beadloom-6hh3`) |
| #318 | closed | `beadloom-ba9w.13` (closed) |
| #311 | closed | `beadloom-ba9w.1` (closed) |
| #310 | live | `beadloom-ba9w.2` |
| #301 | live (overlaps S3b's #205) | proposed: a dated version sentence reads as history |
| #300 | closed | `beadloom-tsqz` (closed) |
| #287 | live | proposed: an unreadable config.yml is one finding against the file |
| #280 | live | proposed: the census reports the filesystem codec |
| #276 | closed | none |
| #273 | live | proposed: the room states the population its freshness check cannot enter |
| #246 | live | proposed: record the last measured run per mutation target |
| #226 | closed | `beadloom-jwfc` (closed) |
| #199 | live | proposed: the lint line counts rules that cannot fire apart from warnings |
| #198 | won't-fix candidate (owner ruling) | none |
| #178 | won't-fix candidate (owner ruling; read in code, job not run) | none |

Counts: 15 closed, 10 live, 2 won't-fix candidates, 1 not reproducible here, 0 not this area.

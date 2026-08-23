# ACTIVE: BDL-061 — Enforced agentic flow

> **Last updated:** 2026-08-23
> **Phase:** Development

---

## Current Bead

**Slice:** S2b — the false-green residue S2 measured and left open, on
`features/BDL-061-S2b`. S2 itself is complete (`.5`, `.33`, `.34`, `.37`, `.38`, `.40`, `.43`,
`.44`, plus `.6` verification, `.7` review and `.8` docs, all closed).
**Closed in S2b so far:** `.48` (rule liveness for all nine rule types), `.46` + `.47`
(*unverifiable is not clean* — one fix; the baseline moved out of the database), `.45`
(the same equation in `docs audit`: a declared fact nothing was checked for is now named,
never counted as fresh), `.49` (an exemption's `until:` is checkable and what it suppressed
is counted), `.54` (the Gate's lint line, filed and closed inside `.49`) and `.55` (the
documentation pass that turned the combined tree green).
**Open in S2b:** `.50` (annotations the extractor cannot see), `.51` (three modules past
1000 lines).
**S3 in progress** on `features/BDL-061-S3`: `.9` (dev), `.35`, `.10` (test) and `.11` (review)
are closed; `.57` — the P0 ship-blocker `.11` raised — is closed, so the eight blind spots `.10`
pinned as strict xfails and the clock defect `.11` measured are all fixed. `.12` (tech-writer)
is what remains before the S3 PR. Also outstanding and not part of any slice: `.39`, `.41`,
`.42`, `.58`.

## Progress

- [x] PRD → Approved (2026-08-22)
- [x] RFC → Approved (2026-08-22)
- [x] CONTEXT + PLAN → Approved (2026-08-22)
- [x] Epic `beadloom-mr2l` + 24 sub-beads created, linear `.1 → .24` chain wired
- [x] S1 `.1` dev — guard primitive shipped (2026-08-22): `application/guards/` +
      `beadloom guard` + logic-free Claude hook adapter + 2 guards; 68 tests, Gate green
- [x] S1 `.2` test — verdict matrix, exclusion validation, liveness widened to 248 tests
- [x] S1 `.3` review — NOT PASSING: 1 critical + 5 major + 7 minor; fix cycle opened as `.25`
- [x] S1 `.25` dev fix (2026-08-22) — C1 path traversal, M1 `excluded_everywhere`,
      m1 dead exclusion, M2 `on:` deleted, M4 `bd --limit 0`, M5 vacuous real-bd test;
      guard tests 242 → 280, Gate green on a clean DB
- [x] S1 `.26` test — independent re-verification: traversal matrix + F1–F6; guard tests
      280 → 335, no `src/` change
- [x] S1 `.27` dev fix-2 (2026-08-22) — accepted path shape + `error` outcome + a firing
      record for every named-guard invocation; F1, F2, F3, F4, F5, F6 closed, the whole-tree
      liveness flag judged and left out with a measured reason; guard tests 335 → 377
- [x] S1 `.28` test — adversarial re-verification (commit `d4bb618`, no `src/` or `docs/`
      change): F7 non-UTF-8 stdin still crashing on the warn code (F2 was closed for one
      spelling only), F8 six record-less invocations, F9 a subdirectory silently skipping at
      exit 0 with the firing written to a manufactured root, F10 strip-before-shape ordering;
      151 new tests, suite 5225 → 5376
- [x] S1 `.29` dev fix-3 (2026-08-22, commit `2a82dad`) — **structural**: one boundary per
      invocation (`run_invocation` = `_record(_answer(...))`, one return, `SystemExit` caught)
      in the new `application/guards/invocation.py`, project discovery by walking up for
      `.beadloom/` (`project_root.py`) and never manufactured, recording as one stated
      predicate with three reported exceptions; the strip deleted and the exclusion glob
      anchored; F7–F10 closed as consequences; 17 sabotages, all FAILED; guard tests 528 → 628,
      suite 5376 → 5476
- [x] S1 `.30` test — the boundary is present at runtime but **was not load-bearing** (commit
      `8bbd84c`, no `src/` change): an interrupt escaped as `BaseException` at exit 1 with no
      record, `--project` at a non-project skipped at exit 0 and manufactured a root, and the
      structural pins checked SPELLING — a `sys.exit(0)` inside `run_invocation` shipped
      628/628 green; 25 tests, suite 5476 → 5501
- [x] S1 `.31` dev fix-4 (2026-08-22, commit `213a615`) — the pin made as wide as its invariant
      (scope derived from the package, terminators recognised by measured effect, a
      recording-witness matrix run in a subprocess), the last-resort handler widened to
      `BaseException` with the Ctrl-C-now-blocks trade-off argued in the SPEC, and `--project`
      required to carry the marker; also: an empty guard name is no longer swallowed, a closed
      stdin states a cause, and the render step can no longer choose the exit code; all 25
      characterization tests rewritten to assert correct behaviour; 9 sabotages all FAILED;
      guard tests 653 → 713, suite 5501 → 5561
- [x] S1 `.3` re-review (2026-08-22) — code shippable, slice not: 0 critical, 4 major, 3 minor,
      and three of the majors are documents claiming enforcement the product does not deliver.
      Routed without a sixth dev cycle: N2 → `.32`, N1(c) → `.33` (S2), N1(a,b)/N3/N4 → `.4`
- [x] S1 `.32` test (2026-08-22, commit `fb19e22`) — the Click-validation pin made about its
      sentence (every parameter Click converts, measured through `make_context`), which found a
      validator nobody typed: `click.Path` defaults `readable=True`, so an unreadable
      `--project` was Click's usage exit with no verdict and no record. Fixed with
      `readable=False`; suite 5561 → 5574
- [x] S1 `.4` tech-writer (2026-08-22, commit `6b9ff2f`) — the three documentary majors closed:
      the exit-3 invariant QUALIFIED rather than deleted (it stands as the target, names the gap
      and its owner `.33`), the enforcement surface written down as a property of the binding in
      the SPEC and `guard-hooks/DOC.md` (#170), and `error` added to the CLI table in both
      READMEs; plus the bead's own scope — a flow-guards section in the agentic-flow guide and
      `guards:` documented in the flow-config SPEC
- [x] S1 `.36` dev hotfix (2026-08-22) — **CI red on PR #33 while the local suite was green,
      and the reason it was green is the finding.** Two defects, both a refusal closed for one
      environment: (1) the undecodable-payload refusal depended on the ambient locale — under
      `LC_ALL=C`/`PYTHONUTF8=1` Python enables UTF-8 Mode, `sys.stdin` gets `surrogateescape`,
      and the guard EVALUATED a surrogate-bearing path instead of refusing it (`WARN`, exit 1)
      — fixed by reading the payload as BYTES and decoding it inside the boundary with
      `errors='strict'`; (2) `Path.resolve()` raises `RuntimeError` on a symlink loop on
      3.10–3.12 and raises nothing on 3.13 (measured on real interpreters), so the
      `except (OSError, ValueError)` under a comment calling the case unreachable let a
      traceback out on three of the four supported versions — fixed by a handler as wide as its
      sentence (`Exception`, and not `BaseException`, with the reason). The locale is now a test
      DIMENSION (4 ambient decoders × the payload matrix) and the loop is asserted as a property
      with the exception INJECTED, so 3.13 coverage cannot go vacuous. Verified on a real 3.10:
      full suite 5442 passed, 0 guard failures. Suite 5574 → 5595
- [x] S2 `.37` dev (2026-08-22) — **the third instance of `.36`'s family, and the first caught
      before CI:** both subprocess probes ran with `text=True`, which decodes with
      `locale.getpreferredencoding(False)`, and both handlers enumerated classes that exclude
      `UnicodeDecodeError` (a `ValueError`), so on a non-UTF-8 image a branch name or a bead
      title with one non-ASCII byte raised past the handler and the boundary turned it into
      `error`/exit 2 — fail-closed but WRONG, where the designed answer is a skip that says why.
      Fixed with a stated codec (`encoding="utf-8"`, `errors="surrogateescape"` — the only
      handler of the three that is injective, so no comparison a guard makes can be given a
      wrong answer by a byte) and handlers as wide as their sentence. Found en route in the same
      call: `run_bd` caught `FileNotFoundError` ALONE, so a 60 s timeout and a real
      non-executable `bd` on PATH also blocked the edit at exit 2. The ambient-locale dimension
      is CONSTRUCTED, not arranged — patching `locale.getpreferredencoding` does not reach
      `TextIOWrapper` (measured) — while the undecodable-bytes half runs against the real `git`.
      The sweep of the other 17 subprocess call sites is a bead comment: `doc_sync/engine.py`,
      `graph/diff.py`, `infrastructure/git_activity.py` and `federation/export.py` carry the
      same pair, and the first two make `sync-check --since` and `diff --since` report changes
      that did not happen. Suite 5595 → 5633

- [x] S2 `.40` dev (2026-08-23) — **the Gate's own instrument was lying.** Four call sites where
      a comparison decoded its two sides by different rules: the current content with an explicit
      `encoding="utf-8"`, the at-ref / subprocess content with whatever the image says. All four
      of `.37`'s verdicts RE-MEASURED before any edit and all four held to the digit — an ambient
      `latin-1` made `sync-check --since` report drift in a file nobody touched and an ambient
      `ascii` raised out of a command that runs inside `beadloom ci`; `diff --since` (the review
      role's instrument) crashed or fabricated; the dashboard showed a contributor who does not
      exist; a federation export dropped its provenance while looking like an honest unknown.
      Fixed by decoding deliberately on BOTH sides through one shared definition per site, with
      each `errors=` chosen by direction of failure and stated in the code: `surrogateescape` for
      the sync digest (total + injective, so no doc can crash the Gate), `strict` for graph YAML
      (UTF-8 by definition — a refusal that names the file, never a fabricated diff), `replace`
      for author names (MEASURED: `surrogateescape` there makes sqlite3 raise
      `UnicodeEncodeError` inside `reindex`, turning a display defect into a Gate crash), and
      `surrogateescape` for git paths in the export (the rule `os.fsdecode` itself uses, so the
      toplevel comparison has the same rule on both sides). Handlers narrowed-by-analysis to
      `OSError` with the enumeration argued, including the redundant
      `(FileNotFoundError, OSError)` `.37` read as the tell — which was also narrow in the
      direction that matters (`PermissionError`). 10 sabotages, and 2 of them PASSED first time,
      exposing two of my own gaps (the at-ref decode error and the `PermissionError` row) that
      are now covered. 23 tests; isolated tree (HEAD + only my files): 5691 passed / 0 failed,
      clean-DB lint 0 violations, sync-check rc 0, doctor rc 0.
- [x] S2 `.34` dev (2026-08-23) — **an unknown key in a guard body is now a configuration
      error, and one not-recorded reason stopped quoting a name nobody typed.** (b) `_build_spec`
      dropped any key it did not read; `option:` for `options:` cost `working-branch` its
      declared trunk — MEASURED through the real binary on a project whose trunk is `develop`:
      an edit made directly ON `develop` answered `PASS ... (trunk is 'main')` at exit 0, and
      after the fix the same file is an ERROR the hook blocks (rc 2) while the corrected
      spelling BLOCKS the edit. Chosen as an **error** rather than a `warn` because the one
      mitigation (the verdict prints the trunk) rides the stream and exit code a harness
      discards, and because the feature is unreleased, so no published project can turn red;
      the same rule after release would need the `warn` route. Applied at both levels of the
      block (guard body + exclusion entry) from one helper, with the allowed set DERIVED from
      the `body.get` literals by an AST pin — an allowed key nobody reads is the deleted `on:`
      again. (a) `_record` routed the no-name case through the unregistered-name branch, so
      `beadloom guard` printed `'(no guard named)' is not a registered guard` — byte-identical
      to what `beadloom guard "(no guard named)"`, an invocation that DID name a guard,
      printed; `_record` now takes the invocation and routes on the name the caller typed, the
      docstring enumerates four exceptions instead of three, and the count is pinned to the
      number of branches. Carried from `.32`: an unreadable `--project` no longer surfaces
      `PermissionError: [Errno 13] ...` as the whole `why` — `locate_project_root` states the
      cause on both entry paths and keeps the errno as its parenthetical detail. 16 tests
      (11 RED first: 4 config + 7 boundary), 8 sabotages all reddening (1 caught by the
      `.31` B2 anchor). Suite 5748 passed / 0 failed, ruff + mypy clean, `beadloom ci` rc 0.
- [x] S2 `.43` dev (2026-08-23) — **a third of `lint --strict` could not fire, and the reference
      taught the mistake.** `forbid_import` matches `from:` against the SOURCE FILE PATH
      (`src/beadloom/tui/app.py`) and `to:` against the DOTTED IMPORT PATH with dots turned into
      slashes (`beadloom/infrastructure/db`) — two vocabularies, so the `src/`-prefixed `to:`
      globs in `rules.yml` matched nothing, ever. MEASURED reconciliation of the two reported
      counts: both are right at different scopes — repairing rule 1 alone surfaces 1
      (`tui/data_providers.py:284`), repairing rules 1+2 surfaces 7 (1 tui + 6 onboarding); the
      `**/x/**` and `beadloom/x/**` forms match identically here. CORRECTION to `.5`: only TWO
      of the four rules were dead — the two `ai_agents` rules already carry the correct dotted
      `to:` (it matches 11 of 221 indexed targets) and their `0` was truthful. Fixed: the tui
      crossing routed through `application/graph_reads` (which now also passes through
      `analyze_git_activity`); the 6 onboarding crossings BASELINED as `forbid_import.exempt`
      entries with a mandatory `reason` + `until` — the rule keeps full scope, proved by
      deleting one entry and watching `lint --strict` go red with 4 errors. PERMANENT, not a
      one-time correction: a rule whose `from:`/`to:` glob matches ZERO candidates in the whole
      index is now reported (`rule_type: rule_liveness`, always `warn`, remediation states both
      matching forms), and so is an exemption that suppresses nothing — the exit condition
      announcing itself. Found while verifying: a `to:` glob covering a package did NOT cover a
      bare import OF it, so the coordinator's own injected probe (`from beadloom.infrastructure
      import db`) fired under NO glob form; now it does. Standing rule 1 VERIFIED not assumed
      (isolated tree copy: probe + incremental reindex → caught; probe removed → back to 0).
      22 tests (16 red first, 6 guards green by design), 4 sabotages; final tree 5718 passed /
      0 failed / 11 skipped (a plain delta is not attributable — `.40` and `.33` landed their own
      test files mid-bead), clean-DB lint 0 violations / 12 rules, sync-check rc 0, doctor rc 0.
      NOT mine, blocking the Gate: `docs audit` reads "(BDL-061.33)" in `docs/services/cli.md:645`
      as an `mcp_tool_count` of 33 — arrived with commit 71e31eb, reproduced on a tree whose
      cli.md is byte-identical to HEAD.
- [x] S2 `.5` dev (2026-08-22) — **the three lying checks fixed, and each fix proved by a test
      that would have caught the false green.** #142: an incremental reindex now re-extracts
      imports for the code files it touched and rebuilds the DERIVED `depends_on` set, which is
      identified by a provenance marker (`extra.derived="imports"`) so a graph-declared edge is
      never collateral damage; an index predating the marker rebuilds once. Proved on the real
      graph, not a toy: an injected `tui → infrastructure` import is caught by the INCREMENTAL
      path with a violation set and an edge set byte-for-byte identical to a full rebuild, and
      both revert symmetrically. #146: sync pairs fall back to the files a node's `source`
      OWNS when annotations yield none (kind-independent — the real cause was never the node
      KIND, it was that pairing read only annotations), `check_sync` no longer short-circuits on
      an empty `sync_state`, and every node that still yields no pair is NAMED with the reason.
      Measured on this repo: 272 → 275 pairs, 4 nodes reported as not checked where the gate
      previously printed nothing. #147: `lint` without a reindex callback opens the index
      `mode=ro`/`query_only` and REFUSES a missing one — it used to print
      "0 violations, N rules evaluated" against a database it created in the same breath — and
      `beadloom ci --no-reindex` on a never-indexed project, previously a wholly green gate,
      now fails honestly. Timing recorded: full 755 ms; incremental +29 ms (1 file) / +42 ms
      (5 files) for the import refresh, paid for several times over by `build_sync_state`
      170 ms → 4 ms. **Found and NOT absorbed:** all four `forbid_import` rules in this repo's
      own `rules.yml` are dead — 0 of 1322 imports can match a `to:` glob written as
      `src/beadloom/…/**`, because the evaluator matches the DOTTED import path
      (`beadloom/tui/app`), which never carries `src/`. Filed for its own bead: repairing the
      globs surfaces 7 pre-existing violations immediately. Suite 5633 → 5649

- [x] S2 `.33` dev (2026-08-22) — **a guard that could not answer let the edit through.** The
      configuration/usage class exited 3, and a Claude Code PreToolUse hook reads 3 as "proceed",
      so an unparseable `guards:` block disabled every guard silently. The mapping now lives in
      the CLI, keyed on the harness the adapter already declares: through `--hook` that class
      exits 2 (the code that stops the edit), from a shell it still exits 3, where the distinction
      between "your configuration is broken" and Click's own usage exit is worth something. An
      unsupported harness blocks too — Beadloom cannot know the exit vocabulary of a tool it does
      not support, so it uses the code it knows stops work. 24 tests (10 red first), including the
      real emitted `.sh` driven through a real subprocess, and a derivation that re-runs every
      exit-3 row of the existing matrix under `--hook`, so a config-error path added later is
      covered on the day it is added.
- [x] S2 `.38` chore (2026-08-22) — **CI gains an environment DIMENSION: the locale is varied,
      never pinned.** One `tests-locale` job, the whole suite, python 3.13, rows `C` and
      `en_US.ISO-8859-1`. The bead's central measurement is that the obvious spelling would have
      shipped a leg that asserted nothing: bare `LC_ALL=C` reports `utf8_mode=1`, because PEP 540
      auto-enables UTF-8 Mode under a C locale — `PYTHONUTF8=0` + `PYTHONCOERCECLOCALE=0` are what
      make the leg real. Three independent locks keep it from going vacuous: an in-CI probe that
      fails the leg both when the image is back on UTF-8 and when glibc silently degrades the
      8-bit row to a second ASCII row; a test that parses that probe out of `ci.yml` and executes
      it; and a test forbidding any job in `ci.yml` from pinning a UTF-8 locale — the tempting
      "fix" the first time the leg goes red. Windows was measured and split off as `.39` for a
      stated reason: adding the leg would not un-vacuum the six `skipif(win32)` guard tests.
- [x] S2 `.44` dev (2026-08-23) — **`docs audit` read numbers out of identifiers (#169).** A line
      is now tokenized on whitespace and only a token whose whole core is a number is a candidate,
      so `(BDL-061.33)` is no longer an `mcp_tool_count` of 33 and `6,390` is read whole. The
      sweep the bead asked for found the silent half: three false-negative classes, filed as #173
      and bead `.45` rather than absorbed, two of them pinned as strict `xfail`s. It also RETIRED
      three `docs_audit.ignore` entries that matched nothing and added none.
- [x] S2 `.6` test (2026-08-22) — **all three standing rules re-derived adversarially, and the
      class they belong to measured.** Each verdict was reproduced through the CLI on a clean room
      instead of inherited from `.5`, including the two qualifications `.8` carries into the CLI
      reference: the read-only lint leaves `beadloom.db` byte-identical but does create the
      `-wal` / `-shm` sidecars, and it answers about the INDEX rather than the tree. Then the
      question the bead exists for: can a check still report green over work it did not do? Yes —
      **seven measured ways**, four of them P0, one of which is the whole gate green after a
      declared SPEC is deleted. 19 tests, 11 of them strict `xfail`s so the day someone fixes a
      gap the suite goes red rather than silent. The locale legs were also run for real on a Linux
      image: 100 ASCII and 76 8-bit locale-attributable failures, with 75 failing under both, so
      the 8-bit row's unique yield is now one test rather than a file — `.42`'s starting shape.
- [x] S2 `.7` review (2026-08-23) — **NOT PASSING: 1 critical, 4 major, 4 minor — and none of them
      argues against the merge.** The three rules were re-derived a third time in a fresh clean
      room and confirmed retirable on evidence. The critical is the one that matters most: a
      clean-database `beadloom ci` is structurally blind to doc staleness, because the rebuild
      adopts the tree as its own baseline — and seven of this slice's nine beads cite exactly that
      run as their gate evidence, a habit standing rule CLEAN-DB LINT taught. Reproduced under
      `main`'s own code, so it is pre-existing; filed as #175 / `.47`. The majors: eight measured
      findings with no owner outside a closed bead's comments (filed as `.48`–`.51` before S3
      opens), an honesty note in `rules.yml` claiming an exit condition the code does not enforce,
      an unchecked reason naming the wrong cause, and a doc asserting a branch protection that is
      not live. #174 was reproduced identically at `main` `7c5fa7d`, which is what makes deferring
      it legitimate rather than forgetting it.
- [x] S2 `.8` tech-writer (2026-08-23) — **the three standing rules deleted, with their two
      replacement sentences placed where a reader meets them.** CLEAN-DB LINT, COMPONENT BLINDNESS
      and LINT WRITES are gone from CONTEXT; the CLI reference now states which form of `lint`
      writes the index and what a `sync-check` count covers, and both documents carry the habit
      CLEAN-DB LINT left behind: a clean database is right for `lint` and vacuous for
      `sync-check`. PLAN's S2 criterion was corrected rather than satisfied — `.7` measured that
      the three rules were never in the shipped `CLAUDE.md`, so the criterion had been written
      against an assumption nobody checked. MAJOR 4 closed on both halves: the nine required
      contexts are stated as the scaffolded default rather than as this repository's live
      protection (`gh api` confirms seven), and every place that documents
      `beadloom setup-branch-protection` now names the sequencing constraint and the bead that
      retires it.

- [x] **S2 COMPLETE** — the three lying checks (#142, #146, #147) are fixed and their standing
      rules retired, `lint`'s DDD boundary rule fires for the first time (#172), the Gate's own
      instruments give the same answer under every ambient codec, and `docs audit` no longer reads
      a number out of an identifier (#169). **S2 fixed three NAMED checks and did not fix the
      class:** `.6` measured seven further false-greens and `.7` an eighth, filed as #173, #174,
      #175 and beads `.45`–`.51`. The slice ships with them open and named, which is the honest
      form of the claim.

**The two `tests-locale` legs are knowingly red, and that is the signal, not a failure of it.**
100 ASCII / 76 8-bit locale-attributable failures until `.42` lands. **The value is the delta
between legs, never any leg's colour** — a green leg today would mean the dimension found
nothing, and the only way to get one is to pin UTF-8, which `ci.yml`'s own tests forbid. The
legs are outside `ai-techwriter`'s `needs:` and outside `main`'s live required contexts, so they
can neither block a merge nor let a required check be skipped. The same legend is in `ci.yml`'s
header comment, where a reader of a red check will look first.

- [x] **S1 COMPLETE** — verified by the coordinator on the final tree: 5574 passed / 10 skipped,
      ruff and mypy --strict clean, `beadloom ci` rc 0 on a clean DB. The B2 sabotage
      (`sys.exit(0)` inside `run_invocation`), which shipped 628/628 green before `.31`, was
      re-run by the coordinator and reddens 9 tests through three independent mechanisms; the
      `click.Choice` sabotage reddens 3. Both restored byte-identical by sha256.

- [x] **S2b `.46` + `.47` — ONE fix, not two** (2026-08-23). The two P0s are the same sentence,
      *unverifiable is not clean*, and they diverge only in the verdict each state earns: a doc
      that is GONE is `missing` (a failure — exit 2, gate FAIL), a pair with NO BASELINE is
      `unverified` (reported by name, never counted fresh, gate step `WARN`, exit code
      unchanged so no green project turns red). **The load-bearing decision was where the
      baseline lives: not in the database.** `.beadloom/beadloom.db` is a derived cache —
      git-ignored, per-machine, dropped by every rebuild and absent on every fresh CI checkout
      — so a baseline kept there is destroyed by the act that most needs it. Freshness now
      rests on **git** (committed by construction; a pair records its baseline's provenance and
      a fabricated one is corroborated against `HEAD`), and the size of the declared surface on
      a **committed ledger** (`.beadloom/sync-surface.json`, written only by an explicit
      `sync-check --record-surface`). MEASURED in a clean room through the real CLI, by exit
      code: `#175` edit + `rm beadloom.db` + reindex → `sync-check` rc 2 and `ci` rc 1 (was
      rc 0 / rc 0); `#174` delete a declared SPEC → `ci` rc 1 with `::error … doc-missing`
      naming the file, and with a ledger present the same run prints `declared surface SHRANK
      283 → 276 pair(s)` — the signal that was silently discarded. Both probes reverted by
      reverse edit, `git status` clean, SPEC sha256 re-verified. Doctor's count was audited as
      the bead asked: it counted FINDINGS, so it rose 20 → 21 while a file was being deleted;
      it now reads `13 check(s): 0 error(s), 9 warning(s), 0 info` and prints *clean* only when
      every check is OK. Four of `.6`'s strict `xfail`s XPASSed and were un-xfailed. 5824
      passed, ruff + mypy --strict clean, Gate rc 0 on an INCREMENTAL index.

- [x] **S2b `.49` — an exit condition that can be checked, and a crossing that is counted**
      (2026-08-24). Review `.7` MAJOR 2: `rules.yml` promised that "an exemption that stops
      suppressing anything is itself reported"; only the DEAD half was true, and a wildcard
      exemption dated 1999 swallowed a real error-severity crossing at `0 violations`, exit 0,
      in silence. Outcome **(i)**, not (ii): (ii) would have written down that a mechanism this
      epic added is decoration. THE COUNT — `LintResult.suppressed` carries the crossings
      themselves, and the clause appears wherever a run can read as clean (`rich`, the piped
      `0 violations, N rules evaluated` line, `--format json` with a `suppressed` array, and the
      Gate). This repo now reads `12 rules, 0 violations, 6 crossings suppressed by an
      exemption`. THE DEADLINE — `until` is a DATE when it leads with `YYYY-MM-DD` and an EVENT
      otherwise; a passed date on an entry still suppressing something is a `warn` finding. It
      never enforces: a crossing that reappeared at `error` because a calendar day passed would
      redden a build with no commit behind it. `--fail-on-warn` is the lever. The guards half is
      fixed on the same grammar, imported rather than restated, so `flow.yml` and `rules.yml`
      cannot promise different things. All six of this repo's own exemptions retire on an EVENT,
      which is why the count — not the date — is the mechanism they rely on. 39 new tests, both
      surfaces in one file; the two strict `xfail`s that pinned this defect are live regression
      tests; six sabotages measured. Clean room = HEAD + these files: 5882 passed, Gate rc 0.

- [x] **S2b `.45` — the audit now reports what it did NOT verify** (2026-08-24). Same equation as
      `.46`/`.47`, in `docs audit`: a green `13 mention(s) fresh` was thirteen restatements of ONE
      of NINE declared facts, and nothing said so. Every declared fact now carries its own
      coverage — `verified`, `not_covered` (no document states it) or `unreadable` (the extractor
      cannot read a claim of that value, with the reason) — printed against the fact, summarised
      on the `beadloom ci` line, and never counted as passing. A mention hidden by a
      `docs_audit.ignore` rule is deliberately NOT coverage. The scan surface is published too:
      all 33 unread documents named with the pattern that skipped them. **The two parser blind
      spots were settled by measurement, in opposite directions.** The modifier class was a real
      defect and is fixed — both windows stop at a phrase separator, so `316 edges, one per
      import` is read and the `14` in `exposes 18 tools: 14 over the graph` is not; parentheses
      were EXCLUDED from the separator set because they cost the true verification in `MCP tools
      (18):`, and a lost true positive is the same silent false negative being fixed. Repo-wide:
      0 mentions gained, 5 lost, all five confirmed false positives — three more dead
      `docs_audit.ignore` entries retired, none added. The single-digit floor was re-measured and
      KEPT: removing it yields 14 extra mentions of which 13 are ordinals, table cells and
      category breakdowns, several of which would have failed the Gate. Trading a silent false
      negative for a loud false positive that then needs a suppression is the wrong trade, so the
      floor stays and `language_count` (value 1) is reported `unreadable` by name. MEASURED after
      the fix: **2 of 9 declared facts verified on this repo, 6 `not_covered`, 1 `unreadable`,
      all seven named.** Four sabotages each reddened the naming tests; all reverted clean.

- [x] **S2b `.55` — the documentation pass, and the wave's own blind spot** (2026-08-24). The
      combined tree was RED where every agent's clean room had been green: `beadloom ci` rc 1,
      286 pairs, 258 ok, **28 stale**, 4 unchecked, 6 `surface_drift`. All 28 stale pairs were
      ONE document — `docs/domains/onboarding/README.md`, 27 `symbols_changed` and one
      `hash_changed` — because `symbols_hash` is computed per `ref_id` over every symbol
      annotated to the node, so four new private helpers in
      `src/beadloom/services/commands/docs.py` (`.45`'s coverage rendering, the only file under
      the `onboarding` surface this slice touched) made every sibling pair of that node stale.
      The document was revised to the code rather than re-attested: what `docs audit` now
      reports, the three `services/commands/` modules that carry
      `# beadloom:domain=onboarding` sections, and one drift the slice exposed rather than
      caused — `_detect_rule_type` maps seven of the loader's nine rule keys, so
      `.beadloom/AGENTS.md` prints `**module-coverage** (unknown)` (BDL-UX #179). The six
      `surface_drift` entries all trace to a single added CLI flag, `sync-check
      --record-surface`, which is #166 measured again: one flag, six reference documents.
      `CHANGELOG.md`, `README.md` and `README.ru.md` carried nothing about this slice and now
      carry the one sentence — *unverifiable is not clean* — plus the architectural change an
      adopter must act on: `beadloom.db` is a derived cache, freshness rests on git provenance
      and the declared surface on the committed `.beadloom/sync-surface.json`. `docs/architecture.md`
      gained the baseline-provenance section, the `declared_docs` / `reference_state` /
      `foreign_edges` tables it never listed, `sync_state`'s two new columns and four verdicts,
      and the `docs audit` step missing from its Gate chain.
- [x] S3 `.9` dev (2026-08-23) — composition generalised to `compose(core, architecture,
      stack, project)` over three artifact kinds; the project layer lives in `.beadloom/flow/`;
      `config-check` verifies the composition RESULT and the flow manifest separates a stale
      artifact from a hand-edited one (which is reported and never rewritten). #177's open
      question answered by measurement: the `CLAUDE.md` body was checked by nothing — a file
      gutted to one line still printed `config-check PASS: agent-config in sync` — and the
      propagation loop was a TEST that rewrote the shipped template from the live file.
      Shipped core `CLAUDE.md` 440 → 376 lines, every removed line mapped to its replacement in
      PLAN. 24 new tests; nine sabotages each reddened a named test in a clean room.

## Results

| Bead | Status | Details |
|------|--------|---------|
| .1 | Done | Guard primitive: registry, verdict, CLI, hook adapter, liveness (68 tests) |
| .2 | Done | Verdict matrix, exclusion validation, liveness widened (248 tests) |
| .3 | Done | Review: 5 fix cycles, then 0 critical / 4 major — code shippable, doc majors routed to `.4` |
| .4 | Done | S1 docs: exit-3 invariant qualified (not deleted), enforcement surface written down, `error` in both READMEs |
| .25 | Done | S1 fix: traversal bypass, probe limit, liveness honesty, `on:` deleted |
| .26 | Done | S1 test: re-verification — F1 backslash bypass, F2 NUL crash, F3–F6 recorded |
| .27 | Done | S1 fix-2: path shape narrowed, `error` outcome, no invocation without a record |
| .28 | Done | S1 test: F2 closed for one spelling; six record-less invocations; silent subdirectory skip |
| .29 | Done | S1 fix-3: ONE boundary per invocation; discovery by walk-up; recording as one predicate |
| .30 | Done | S1 test: boundary not load-bearing — interrupt escape, `--project` bypass, pins check spelling |
| .31 | Done | S1 fix-4: pin as wide as its invariant; `--project` must name a project; interrupt handled |
| .32 | Done | S1 test: the Click-validation pin as wide as its sentence; `--project` `readable=False` |
| .36 | Done | S1 hotfix: the payload decoded as bytes (locale-independent); the resolve handler as wide as its sentence |
| .5 | Done | S2: #142 incremental import refresh, #146 source-owned sync pairs + unchecked accounting, #147 read-only lint that refuses a missing index |
| .33 | Done | S2: the exit-3 class was fail-open — through `--hook` a config error now exits 2 and blocks the edit |
| .34 | Done | S2: an unknown key in a guard body is a config error at both levels; the no-name record reason no longer quotes the placeholder; an unreadable `--project` states its cause |
| .37 | Done | S2: the probes decode with a stated codec, not the image's locale; handlers as wide as their sentence; sweep of every other subprocess call |
| .38 | Done | S2: `tests-locale` — the environment dimension in CI (locale varied, never pinned); three locks against a vacuous leg; `DEFAULT_STATUS_CHECK_CONTEXTS` 7 → 9 |
| .40 | Done | S2: the four call sites with a measured wrong ANSWER — both sides of a comparison now decoded by the same stated rule |
| .43 | Done | S2: two `forbid_import` rules could not match anything (`src/`-prefixed `to:`); glob liveness + named, expiring exemptions |
| .44 | Done | S2: docs-audit token boundary (#169) — a number inside a larger token is an identifier; sweep filed 3 silent FN classes as #173 / `.45` |
| .6 | Done | S2 test: the three rules re-derived adversarially + seven remaining false-greens measured, 11 of them strict `xfail`s; the locale legs run for real (100 / 76) |
| .7 | Done | S2 review: NOT PASSING — 1 critical (#175), 4 major, 4 minor; merge with #174 open argued from evidence, with the honesty condition now in `.8` |
| .8 | Done | S2 docs: the three standing rules deleted, replacements in the CLI reference, PLAN's S2 criterion corrected, MAJOR 4 + minors 1/3/4 closed |
| .35 | Pending | S3: no `.gitignore` entry for the firing record; carries n1 (our dogfood never ran the shipped artifact) |
| .39 | Pending | S2/S3 chore: a Windows CI leg — only after the six `skipif(win32)` guard tests are made meaningful |
| .41 | Pending | S3: three more ambient-decode sites, plus an MCP test runner with no timeout |
| .42 | Pending | S2/S3: the locale dimension's first run — 100 ASCII / 76 8-bit failures from text I/O without an explicit encoding (the title still carries `.38`'s superseded 97/73; the owner is correcting it) |
| .45 | Done | P1 (#173): docs-audit reports what it did NOT verify — per-fact coverage (`verified` / `not_covered` / `unreadable`), a published scan surface, clause-scoped matching; measured 2 of 9 declared facts verified on this repo |
| .46 | Done | P0 (#174, ONE fix with `.47`): a deleted doc is `missing`, not `ok`; the DECLARED surface outlives the file; the pair count is a committed ledger; doctor's count audited |
| .47 | Done | P0 (#175, ONE fix with `.46`): the baseline moved OUT of the database — git for freshness, a committed ledger for the surface; a rebuilt baseline is corroborated or reported `unverified`, never fresh |
| .48 | Done | P0 (#172): rule liveness for all NINE dispatched rule types (the bead said six, the SPEC said seven, the loader dispatches nine); `rules_inert` qualifies the summary line |
| .49 | Done | P0: outcome (i) — what an exemption suppressed is counted on every run, and an `until:` leading with an ISO date that has passed is a finding; the same grammar on `flow.yml` exclusions |
| .54 | Done | P2: the Gate's lint line now carries the suppressed count; measured that it needs no `rules_inert` clause (an inert rule always flips it to the warning branch). Filed and closed inside `.49` |
| .55 | Done | S2b docs: the 28-pair onboarding README revised to the code; *unverifiable is not clean* written once in both READMEs + CHANGELOG; the baseline-out-of-the-database change stated for adopters; 6 `surface_drift` re-attested after reading, stale 28 → 0 |
| .50 | Pending | P1: annotations the extractor cannot see — docstring annotation, directory source without a trailing slash, deny rules keyed on annotated symbols |
| .51 | Pending | P2: three modules past 1000 lines with many responsibilities each, self-flagged and owned by nobody |
| .9 | Done | S3 dev: `compose(core, architecture, stack, project)` for roles, commands AND `CLAUDE.md`; project layer in `.beadloom/flow/`; `config-check` verifies the composition result; #177, #139, #152, #132, #136, #137 closed |
| .10 | Done | S3 test: 71 passing + 9 `xfail(strict)` measured blind spots in the new `config-check`; the `#177` role leg closed and a structural guard against tests that write tracked files |
| .35 | Done | S3: the `.gitignore` block for generated `.beadloom/` state; this repo now runs the SHIPPED guard adapter rather than a local binding |
| .11 | Done | S3 review: NOT PASSING — 0 critical, 7 major, 8 minor. Reproduced `.10`'s clock defect and measured it WORSE than recorded: 0 findings / exit 0 → 9 ERROR / exit 1 on an untouched tree. Verdict accepted: fix that one first, ship the rest behind `.57` |
| .57 | Done | S3 dev (P0, ship-blocker): all NINE pins closed. The clock removed from the composition (`composer.py`'s assertion kept, `describe()`'s behaviour deleted); expiry and dead-declaration became `config-check` findings; three deletion paths (manifest, provenance stamp, scaffolded file) each reported; `unmanaged` → `sync-check`'s `unverified`; the project layer is named, not judged |
| .12 | Pending | S3 tech-writer: `services/mcp.md` + the `onboarding` README symbols cascade — 37 stale pairs measured at `fdbc1df`, before `.57` |
| .13–.16 | Pending | S4 BDD, mutation, doc shape + quality, shared writing standard |
| .17–.20 | Pending | S5 TO-BE / AS-IS / WORKING |
| .21–.24 | Pending | S6 waves from the graph (#155, #118, #133) |

## Notes

**Branch:** `features/BDL-061-S3` for the current slice (`features/BDL-061-S2b` for the one before) (S1 ran on `features/BDL-061`, S2 on
`features/BDL-061-S2`). Slice boundary is a PR boundary — each slice green on `main` before the
next begins, as BDL-060 ran.

**Ordering is load-bearing.** S1 first because it is the primitive; S2 second because S3's
acceptance criterion is deleting the rules S2's bugs forced into the prose, which cannot happen
earlier.

**Dogfooded under itself.** From S1 onward this epic's own beads run under the guards being
written. Friction is recorded as a finding, never worked around — the record is the point.

**Deferred from review `.3`, deliberately and named:** M3 (the harness owns event routing *and*
the guard list, so `.claude/settings.json` carries two decisions Beadloom cannot see) is S3
work — it is the same defect as M2 from the other end, and wiring it hastily under a fix cycle
would recreate the "capability with no consumer" shape that M2 exists to remove. The
re-review's minors, judged in `.4` and routed by what each one is:
`n1` (this repo registers the CLI command directly, so the emitted adapter has never run here)
and `n2` (no `.gitignore` entry for the firing record in scaffolded projects) are scaffolding
changes and go to S3 with M3, which reworks adapters; `n3` (the no-name invocation reports an
unregistered-name reason; an unknown key in a guard body is ignored) is source and belongs to
an S2 dev bead; `n4` (duplicated, mutually contradicting Progress and Results entries) was a
document defect and is fixed above. The first review's `m3` closed in `.31` as a consequence
of the marker requirement; `m4`'s remaining half (the read-only digest does not cover
`.beads/embeddeddolt/**`, and the `bd` probe bumps mtimes there) and `m6` (role files do not
say the coordinator owns the commit) and `m7` (no firing-record rotation) stay open for S2.
`N1(c)` — the exit-3 class is fail-open — is bead `.33` in S2. Until it lands, the documents
state the gap rather than lowering the promise.

**A wave's integration state is measured by nobody, and S2b is the proof (#181).** Four dev
beads ran across two waves in one shared working tree. A shared tree makes a full-suite run
meaningless for any single agent, so each verified in a clean room — `git archive HEAD` plus only
its own files — and each honestly reported green. The combined tree was `beadloom ci` rc 1 with 28
stale pairs. **None of the four reports was wrong.** The clean room is the correct technique for
attributing a result to one bead while neighbours are editing, and it is blind by construction to
any interaction between beads; nothing in the protocol runs the combined tree until the coordinator
does it at wave end. Two consequences the next slice inherits: the combined run belongs in
somebody's bead rather than in a coordinator's habit, and an agent's green needs a TYPE — "green in
a clean room over N files" is a different claim from "green on the tree", and reporting both with
the same word is what makes the discrepancy read as a contradiction. The cheapest mechanical
improvement is to give the run to whoever holds the merge slot, since somebody already holds a lock
at exactly the right moment. Related: #118 (parallel agents collide on the shared pre-commit hook)
— same root, that the wave shares one tree.

**Two friction findings this slice measured again rather than merely cited.** #167 at gate scale:
one stale document printed 28 `[stale]` lines that differ in no visible way, and `beadloom doctor`
printed 28 more of its own; the number a reader wants — how many DOCUMENTS need attention — had to
be derived by eye from `--json`, and one document reads exactly like twenty-eight. #166 again: a
single added CLI flag (`sync-check --record-surface`) drifted all six `watches:` reference
documents at once. `sync-update --all --yes` does now clear the reference-doc path — measured at the close of this
slice, one command printed `Re-baselined 7 reference doc(s)` and took `surface_drift` from 6 to 0
— so #166's second half is narrower than filed — but its first half stands: one fact known once still costs six
consequences to record, and the bulk form is exactly the operation #163 says should leave evidence
rather than become frictionless.

**Carried, not forgotten:** #160 (AsyncAPI wired to nothing) stays deferred with its plan in
ROADMAP; #158 and #161 are separate items this epic's mechanisms may later absorb; #91 closes
as verified with the caveat that it is the first believable result, since only #159 taught the
cycle rule to see nested imports.

**Owner-visible checkpoint:** after `.12` (end of S3) the core request is delivered — the flow
is enforced, stops lying, and is extensible. If a later slice proves to be an epic of its own,
that gets reported rather than absorbed; S5 and S6 are the likely candidates.

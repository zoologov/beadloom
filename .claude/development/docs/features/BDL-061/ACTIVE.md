# ACTIVE: BDL-061 — Enforced agentic flow

> **Last updated:** 2026-08-22
> **Phase:** Development

---

## Current Bead

**Bead:** none — `.36` (the S1 CI hotfix) is done; the branch is awaiting the owner's push and
a re-check of PR #33.
**Next:** S2 (`.5`–`.8`, plus `.33` and `.34` filed out of S1's review). S2 begins only after
S1 is green on `main`, per the slice-boundary-is-a-PR-boundary rule.

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

- [x] **S1 COMPLETE** — verified by the coordinator on the final tree: 5574 passed / 10 skipped,
      ruff and mypy --strict clean, `beadloom ci` rc 0 on a clean DB. The B2 sabotage
      (`sys.exit(0)` inside `run_invocation`), which shipped 628/628 green before `.31`, was
      re-run by the coordinator and reddens 9 tests through three independent mechanisms; the
      `click.Choice` sabotage reddens 3. Both restored byte-identical by sha256.

## Results

| Bead | Status | Details |
|------|--------|---------|
| .1 | Done | Guard primitive: registry, verdict, CLI, hook adapter, liveness (68 tests) |
| .2 | Done | Verdict matrix, exclusion validation, liveness widened (248 tests) |
| .3 | Done | Review: 5 fix cycles, then 0 critical / 4 major — code shippable, doc majors routed to `.4` |
| .25 | Done | S1 fix: traversal bypass, probe limit, liveness honesty, `on:` deleted |
| .26 | Done | S1 test: re-verification — F1 backslash bypass, F2 NUL crash, F3–F6 recorded |
| .27 | Done | S1 fix-2: path shape narrowed, `error` outcome, no invocation without a record |
| .28 | Done | S1 test: F2 closed for one spelling; six record-less invocations; silent subdirectory skip |
| .29 | Done | S1 fix-3: ONE boundary per invocation; discovery by walk-up; recording as one predicate |
| .30 | Done | S1 test: boundary not load-bearing — interrupt escape, `--project` bypass, pins check spelling |
| .31 | Done | S1 fix-4: pin as wide as its invariant; `--project` must name a project; interrupt handled |
| .32 | Done | S1 test: the Click-validation pin as wide as its sentence; `--project` `readable=False` |
| .36 | Done | S1 hotfix: the payload decoded as bytes (locale-independent); the resolve handler as wide as its sentence |
| .37 | Done | S2: the probes decode with a stated codec, not the image's locale; handlers as wide as their sentence; sweep of every other subprocess call |
| .4 | Done | S1 docs: exit-3 invariant qualified (not deleted), enforcement surface written down, `error` in both READMEs |
| .33 | Pending | S2: the exit-3 class is fail-open — a broken `flow.yml` disables every guard |
| .34 | Pending | S2: an unknown key in a guard body is silently ignored (`option:` → trunk `main`) |
| .35 | Pending | S3: no `.gitignore` entry for the firing record; carries n1 (our dogfood never ran the shipped artifact) |
| .5–.8 | Pending | S2 stop the lying checks (#142, #146, #147) |
| .9–.12 | Pending | S3 composition + project overlay (#139, #152, #132, #136, #137) |
| .13–.16 | Pending | S4 BDD, mutation, doc shape + quality, shared writing standard |
| .17–.20 | Pending | S5 TO-BE / AS-IS / WORKING |
| .21–.24 | Pending | S6 waves from the graph (#155, #118, #133) |

## Notes

**Branch:** `features/BDL-061`. Slice boundary is a PR boundary — each slice green on `main`
before the next begins, as BDL-060 ran.

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

**Carried, not forgotten:** #160 (AsyncAPI wired to nothing) stays deferred with its plan in
ROADMAP; #158 and #161 are separate items this epic's mechanisms may later absorb; #91 closes
as verified with the caveat that it is the first believable result, since only #159 taught the
cycle rule to see nested imports.

**Owner-visible checkpoint:** after `.12` (end of S3) the core request is delivered — the flow
is enforced, stops lying, and is extensible. If a later slice proves to be an epic of its own,
that gets reported rather than absorbed; S5 and S6 are the likely candidates.

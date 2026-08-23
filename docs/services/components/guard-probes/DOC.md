# Guard Probes (component)

Internal building block of the CLI service.

**Source:** `src/beadloom/services/guard_probes.py`

---

## Overview

The concrete, read-only probes that bind the flow guards to the real `bd` and
`git`. Guard checks are written against ports declared in
`application/guards/contract.py`; this is where those ports meet the actual
tools.

It lives in the **services** layer for one hard reason: the `bd` seam does, and
the application layer must not import services (`architecture-layers`, severity
`error`). Wiring the adapters at the CLI boundary keeps the dependency pointing
inward.

## Public surface

- `build_probes(project_root)` — the real probe set (`GuardProbes`).
- `BdWorkTracker` — `claimed_beads()` from
  `bd list --status in_progress --json --limit 0`, with the status re-checked
  client-side as belt-and-braces. Returns `None` (not an empty tuple) when the
  project has no `.beads/` directory, when `bd` is not installed, or when the
  call fails.
- `UNLIMITED` — the `--limit` value that lifts bd's 50-row page.
- `GitWorkspace` — `current_branch()` via `git branch --show-current`, which
  answers correctly on an unborn branch and prints nothing on a detached HEAD.
- `CLAIMED_STATUS` — the bd status token meaning "claimed and in progress".

## Invariants

- **Read-only.** `bd` is queried only when `.beads/` already exists, because
  invoking it in an unrelated repo could initialise state there — a guard must
  never change the project it inspects.
- **Unavailable is `None`, never a default.** Nothing here falls back to a value
  that would manufacture a green verdict; `None` makes the guard skip with a
  stated reason.
- **All of the evidence, not the first page.** `bd list` caps its answer at 50
  rows unless told otherwise (`--limit 0`). Reading one page and filtering
  client-side made a bead claimed beyond it invisible, so `bead-claimed` reported
  "no bead is in progress" while one was — a false warning, and a false BLOCK
  under the `strictness: { epic: block }` configuration the docs ship as the
  example.
- **Text is decoded by a stated codec, never by the image's locale.** `git` is
  run with `encoding="utf-8", errors="surrogateescape"`. `text=True` decodes with
  `locale.getpreferredencoding(False)`, which made the same repository answer
  differently depending on where the process ran: under a C-locale container the
  decode raised (and, being a `UnicodeDecodeError`, escaped the handler below),
  and under an 8-bit locale it returned a branch name nobody had checked out.
  `surrogateescape` rather than `strict` because it is the only one of the
  handlers that is injective — it round-trips to the exact bytes git holds, so
  `branch == trunk` stays truthful and a legal-but-not-UTF-8 branch name does not
  silently switch `working-branch` off. `strict` would answer `None` there and the
  guard would skip: an exemption nobody declared. (BDL-061.37)
- **The handler is as wide as the sentence it holds.** "A probe that cannot
  answer returns `None`" quantifies over every way the call can fail, so it
  catches `Exception` — not an enumeration of classes, which is how
  `UnicodeDecodeError` (a `ValueError`: neither an `OSError` nor a
  `subprocess.SubprocessError`) used to escape and reach the boundary as an
  `error` verdict at exit 2. Blocking the edit is not the designed answer for
  "the probe cannot answer"; a skip that says why is. Deliberately not
  `BaseException`: an interrupt is the process being stopped, not git declining.

## Collaborators

Used by `beadloom guard` (`services/commands/guard.py`), which passes the probe
set into `evaluate_guard`. Tests patch the command's `_probes` seam for stubbed
probes, and exercise these adapters against a real `git` repository and against a
real `bd` project built by the test (`bd init` in a temp dir, one bead claimed,
one left alone) — a stub proves the stub's contract, so the binary boundary gets
its own test.

# bd Seam (component)

Internal building block of the MCP server service.

**Source:** `src/beadloom/services/bd_seam/`

---

## Overview

The boundary between this project and the `bd` (beads) CLI, in two halves.

`client.py` is a single, thin, **mockable** seam. The MCP process-tools
(`task_init` / `complete_bead` / `checkpoint`) drive the beads issue tracker;
rather than scattering `subprocess` calls across the handlers, every `bd`
invocation funnels through `run_bd`. Tests patch `run_bd` (or
`bd_seam.client.subprocess.run`) so the tools run without a real `bd` binary.

`invocations.py`, `assumptions.py` and `population.py` derive the other half:
**where** this project reaches `bd` and **what each call form assumes about the
answer**. BDL-068's CONTEXT Q4 decided that shape — an External `bd` finding is
answered by deriving our own call sites, never by a wrapper, because a wrapper is
a second thing to keep in step with upstream and a derived population fails on a
call site added later. `beadloom bd-calls` prints the report.

`answers.py` is the run-time half of the same question: **which population an
answer that already came back covers**. The derivation judges a call FORM before
it runs; this reads bd's own notice off stderr, bd's own suggestion block off
stdout, and the argv we wrote. It re-implements no decision bd makes, which is
what keeps it on the right side of Q4.

## Public surface

- `run_bd(args, *, cwd=None)` — invoke `bd` with *args* (no leading `bd`) and
  capture its output; raises `BdUnavailableError` whenever `bd` does not answer.
- `BdResult` — frozen dataclass: `returncode`, `stdout`, `stderr`, plus an
  `ok` property (True iff `returncode == 0`).
- `BdUnavailableError` — raised when `bd` cannot be run **to completion**: not
  installed, not executable, wedged past the timeout, or answering in bytes this
  process cannot read. A non-zero *exit* is not that case — that is bd answering,
  and it comes back as a `BdResult`.
- `_BD_TIMEOUT_S` — the per-invocation timeout (60s).

### The derived call-site population

- `text_invocations(sources, *, channel=...)` / `python_invocations(sources)` —
  the one grammar, over `(label, text)` pairs. The text channel anchors on
  **command position**; the Python channel reads argv from the AST and resolves
  module-level string constants.
- `BdInvocation` — `source`, `line`, `channel`, `text`, `words`, `flags`,
  `unresolved_arguments`.
- `call_sites(invocations)` → `BdCallSite`, which adds `subcommand` and
  `assumptions`; `report_of(sites, unreached=...)` → `CallSiteReport`, which adds
  `measured_against`.
- `Assumption` — `name`, `verdict`, `detail`. The verdicts are `secured`,
  `unsecured`, `holds` and `unmeasured`.
- `lock_invocations(invocations)` — the bridge to `wave-plan`'s landing-lock
  judgement, so a `merge-slot` form is parsed once here and judged once there.
- `project_report(project_root)` — the whole population for a project, over four
  channels: the composed flow, the shipped templates, the installed package's
  Python, and `.git/hooks/`.
- `BD_MEASURED_VERSION` — the release every verdict was taken against, `1.0.4`.
- `population_flags(subcommand)` — the flags that widen a subcommand's answer to
  its whole population, or `None` when this derivation has not measured what
  population that subcommand's answer covers.

### The population an answer covers

- `coverage_of(argv, stderr)` → `AnswerCoverage` — `subcommand`, `coverage`,
  `shown`, `total`, `widening_flags`, plus `as_asked` and a `stated` sentence.
  The coverages are `as-asked`, `filtered`, `truncated` and `unchecked`.
- `ready_ids(stdout)` — the ids in a `bd ready --json` answer, or `None` when
  that answer cannot be read at all.
- `suggested_beads(stdout)` — the ids `--suggest-next` named, read from bd's own
  `Newly unblocked:` block.
- `confirmed_suggestion(close_stdout, ready)` → `ConfirmedSuggestion` —
  `candidates`, `confirmed`, `still_blocked`, `compared`, and a `stated`
  sentence. `ready=None` means the confirmation could not be made.
- `COVERAGE`, `COVERAGE_AS_ASKED`, `COVERAGE_FILTERED`, `COVERAGE_TRUNCATED`,
  `COVERAGE_UNCHECKED`, `NOT_COMPARED`, `NOTHING_TO_CHECK`, `READY_COMMAND`.

## Invariants

- **A verdict names the release it was measured on.** Every entry in the
  assumption table was taken on bd 1.0.4 with the streams read separately and the
  exit codes read without a pipe, and `BD_MEASURED_VERSION` records it.
  `tests/test_bd_call_sites.py::test_the_recorded_release_is_the_one_installed`
  fails when a different `bd` is installed, naming what has to be re-measured.
  That is not ceremony: three premises BDL-068 S5 inherited were re-measured and
  destroyed — BDL-UX #194 and #237 (`bd merge-slot` grants no exclusion; it does,
  and 32 concurrent acquires produced exactly one winner per round) and
  `beadloom-l2f2` (`bd import -i` does not exist; it does, as a documented legacy
  alias, and imported 137 issues at exit 0). An External defect a later `bd` fixes
  must fail loudly rather than quietly guard nothing.
- **A withdrawal is a measurement too, and one shape is not enough.** BDL-UX #97
  was withdrawn in this module and the withdrawal was wrong. It rested on one
  dependency shape — a target with two blockers, one closed — where
  `--suggest-next` was silent while the target was blocked and spoke when it
  became ready. Both directions of the OUTCOME; one shape.
- **The mechanism has been characterised three times and no characterisation
  survived the next measurement.** The correction to the withdrawal above
  concluded `--suggest-next` is silent in every shape where exactly one blocker
  had just closed; that reading rested on ten cells sharing ONE rig.
  `beadloom-0mdo.52` re-measured twenty-three shapes in twenty-three separate
  `bd init` rigs, which is the axis the shared rig could not hold constant, and
  that shape names a still-blocked bead. Sixteen of the twenty-three are false
  positives, on no shape rule any of the three sessions found. So this component
  records the OBSERVATION and never the mechanism: on bd 1.0.4 `--suggest-next`
  names beads that are still blocked, and `bd ready` was correct in all
  twenty-three. `unblocked-is-ready` is therefore `unsecured` on the call form
  alone, and `bd ready` is what settles it.
- **An assumption no flag can reach is settled by the ARTIFACT, not by the
  line.** `unblocked-is-ready` is `secured` when the artifact that instructs
  `--suggest-next` also names `bd ready`, because the artifact is what a reader
  reads: a subagent runs from `.claude/agents/<role>.md` alone, so a mitigation
  that lives in `CLAUDE.md` never reaches it. Three of the four role cores were
  in exactly that state before `beadloom-0mdo.52`, and the shared `_tracker`
  fragment now composes the rule into every role. `call_sites` therefore runs two
  passes — collect which subcommands each source names, then judge — because a
  single pass could only secure a confirmation written ABOVE the call, which is a
  fact about ordering rather than about what the artifact tells its reader. The
  verdict states its own limit: that the two answers are actually COMPARED is not
  something a derivation of call forms can see.
- **An answer that came back states the population it covers.** `as-asked` is
  deliberately not called `complete` — `bd list --status open` names a population
  and bd honours it, and every open bead is not every bead. bd's own notice
  outranks the call form: passing `--all` is an intention, and a silent stderr is
  what makes it a measurement. `ready_ids` returns `None` for an unreadable
  answer and `()` for an empty queue, because collapsing the two turns a failed
  confirmation into "every candidate is still blocked".
- **An unjudged site never reads as a clean one.** A subcommand outside the
  measured table carries `unmeasured-subcommand`, and a subcommand measured to
  carry no breakable assumption carries none — those are different facts, and
  today 48 of this repository's 348 sites are the first kind (`bd swarm` 26,
  `bd gate` 22).
- **The unreached region is part of the answer.** `beadloom-0mdo.58` measured the
  reach before the population existed: a Python sweep sees about a twentieth of
  the subject. `population.UNREACHED` names four regions with their reasons —
  the coordinator's launch prompt, `.claude/development/` (which QUOTES call forms
  as evidence and instructs nobody), a `bd` a person types, and string literals in
  this project's Python, whose emitted scripts are read where they run instead.
- **The grammar reads command position, not the word `bd`.** Measured over this
  repository's 65 instructing artifacts, the anchored sweep returns 266
  invocations and no prose; the unanchored one also reports `bd verifies`,
  `bd checks the`, `bd is available` and `a bd comment with`.

- **Text is decoded by a stated codec, never by the image's locale** (BDL-061.37).
  `bd` is run with `encoding="utf-8", errors="surrogateescape"`. `text=True`
  decodes with `locale.getpreferredencoding(False)`, so on a container whose
  locale is not UTF-8 a bead title with one non-ASCII byte either raised or came
  back as a different title — neither visible on a UTF-8 machine. UTF-8 is bd's
  own contract here rather than a guess: bd speaks JSON, and JSON is UTF-8 by
  definition (RFC 8259 §8.1). `surrogateescape` rather than `strict` because what
  callers *decide* with is machine tokens (ids, statuses, structure) while the
  non-ASCII part is display text: `strict` would let one stray byte in one bead's
  title report bd unavailable and skip `bead-claimed` for the whole project — a
  gate switched off by display text. `surrogateescape` is injective, so every
  token still decodes to a distinct string; the cost is that such a title reaches
  the reader with `\udcff`-style escapes in it.
- **One name for "bd did not answer".** The handler is as wide as that sentence
  (`Exception`, deliberately not `BaseException`), because every caller already
  has a right response to it — the MCP tools return a structured error, the guard
  probe returns `None` so the guard skips with a reason. It previously caught
  `FileNotFoundError` alone, so a 60-second timeout, a non-executable `bd` on
  PATH and an undecodable answer escaped the seam *and* the probe and reached the
  guard boundary as `error`/exit 2 — a blocked edit for a reason that was not the
  real one. Nothing is swallowed: the message names the underlying class and the
  original exception is chained.

## Collaborators

The single funnel for the MCP process-tools (`task_init` / `complete_bead` /
`checkpoint`) that drive the beads tracker. Tests patch `run_bd` (or the
module-level `subprocess.run`) to run the tools without a real `bd` binary.

> Component doc (BDL-051; the population added by BDL-068 S5,
> `beadloom-0mdo.51`, and the answer's coverage by `beadloom-0mdo.52`). Public
> surface verified against `src/beadloom/services/bd_seam/`.

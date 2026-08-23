# bd Seam (component)

Internal building block of the MCP server service.

**Source:** `src/beadloom/services/bd_seam.py`

---

## Overview

A single, thin, **mockable** seam over the `bd` (beads) CLI. The MCP
process-tools (`task_init` / `complete_bead` / `checkpoint`) drive the beads
issue tracker; rather than scattering `subprocess` calls across the handlers,
every `bd` invocation funnels through `run_bd`. Tests patch `run_bd` (or the
module-level `subprocess.run`) so the tools run without a real `bd` binary.

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

## Invariants

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

> Component doc (BDL-051). Public surface verified against `bd_seam.py`.

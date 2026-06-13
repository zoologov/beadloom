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
  capture its output; raises `BdUnavailableError` when the `bd` binary is not
  installed / not on PATH.
- `BdResult` — frozen dataclass: `returncode`, `stdout`, `stderr`, plus an
  `ok` property (True iff `returncode == 0`).
- `BdUnavailableError` — raised when `bd` is unavailable.
- `_BD_TIMEOUT_S` — the per-invocation timeout (60s).

## Collaborators

The single funnel for the MCP process-tools (`task_init` / `complete_bead` /
`checkpoint`) that drive the beads tracker. Tests patch `run_bd` (or the
module-level `subprocess.run`) to run the tools without a real `bd` binary.

> Component doc (BDL-051). Public surface verified against `bd_seam.py`.

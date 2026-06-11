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

> Component doc skeleton (BDL-051 S3b / BEAD-14). Tech-writer (BEAD-13) fills prose.

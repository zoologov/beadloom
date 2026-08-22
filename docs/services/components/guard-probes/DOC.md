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
- `BdWorkTracker` — `claimed_beads()` from `bd list --json`, filtered to
  `in_progress`. Returns `None` (not an empty tuple) when the project has no
  `.beads/` directory, when `bd` is not installed, or when the call fails.
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

## Collaborators

Used by `beadloom guard` (`services/commands/guard.py`), which passes the probe
set into `evaluate_guard`. Tests patch the command's `_probes` seam for stubbed
probes, and exercise these adapters against a real `git` repository and the real
`bd` binary.

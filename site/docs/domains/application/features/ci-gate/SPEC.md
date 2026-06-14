<!-- beadloom:badge-start -->
> ✅ **fresh**
> 
> last synced 2026-06-14T12:30:18.610981+00:00 · coverage 100% (`ci-gate`)
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

# CI Gate

The unified `beadloom ci` gate for the application domain.

**Source:** `src/beadloom/application/gate.py`

---

## Specification

### Purpose

Compose Beadloom's individual checkers — reindex, `lint --strict`, `sync-check`,
`config-check` (AgentConfigAsCode), `doctor` (graph integrity), and (when hub
exports are supplied) `federate --fail-on` — into ONE `GateResult` with a single
`ok` verdict. This is the single convergence point that makes CI the only true
enforcement, identical for any author (Cursor / Claude Code / human).

### Contract

- **Input:** the project root (and optional federation hub exports).
- **Output:** a `GateResult` aggregating every checker; `beadloom ci` exits
  non-zero unless every gate passes.
- **Invariants:** the gate runs every checker (no short-circuit hiding later
  failures) and reports each sub-result honestly.

> Skeleton (BDL-051 S3b / BEAD-14). The tech-writer pass (BEAD-13) fills prose.

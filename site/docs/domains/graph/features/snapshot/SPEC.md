<!-- beadloom:badge-start -->
> ✅ **fresh**
> 
> last synced 2026-06-14T18:52:29.106245+00:00 · coverage 100% (`snapshot`)
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

# Snapshot

Architecture snapshot store for the graph domain.

**Source:** `src/beadloom/graph/snapshot.py`

---

## Specification

### Purpose

Persist point-in-time snapshots of the architecture graph and compare them over
time. `snapshot save` records the current node/edge state; `snapshot compare`
diffs two saved states so drift can be reviewed independently of git history.

### Contract

- **Input:** the live indexed graph (nodes + edges).
- **Output:** named, stored snapshots; a structured diff between any two.
- **Invariants:** snapshots are immutable once saved; comparison is
  order-independent and deterministic.

> Skeleton (BDL-051 S3b / BEAD-14). The tech-writer pass (BEAD-13) fills prose.

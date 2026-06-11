<!-- beadloom:badge-start -->
> ✅ **fresh**
> 
> last synced 2026-06-11T14:19:08.709748+00:00 · coverage 100% (`sync-check`)
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

# Sync Check

The doc-code synchronization engine for the doc-sync domain.

**Source:** `src/beadloom/doc_sync/engine.py`

---

## Specification

### Purpose

Track whether each documentation file is still in sync with the code it
describes. The engine pairs a node's `docs:` entries with the source files
attributed to that node, computes a freshness signal from the code
`symbols_hash` (plus git state), and reports each pair as `ok` or stale.
`mark_synced` re-baselines a pair once its doc has been brought up to date.

### Contract

- **Input:** the graph (node ↔ doc ↔ source associations) and the code index.
- **Output:** a per-pair sync verdict; `sync-check` exits non-zero on staleness.
- **Invariants:** baselining is explicit (`mark_synced` / `sync-update`); the
  engine never silently marks a stale doc fresh.

> Skeleton (BDL-051 S3b / BEAD-14). The tech-writer pass (BEAD-13) fills prose.

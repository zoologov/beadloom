<!-- beadloom:badge-start -->
> ✅ **fresh**
> 
> last synced 2026-06-13T22:42:55.793320+00:00 · coverage 100% (`context-builder`)
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

# Context Builder (component)

Internal building block of the context-oracle domain.

**Source:** `src/beadloom/context_oracle/builder.py`

---

## Overview

Assembles a context bundle for a node via a bounded BFS subgraph traversal of
the graph, gathering the node, its neighbors, the attributed code symbols, and
the relevant docs into one structured bundle. This is the machinery behind
`ctx` / `prime` — the read-only context surface AI agents consume.

> Component doc skeleton (BDL-051 S3b / BEAD-14). Tech-writer (BEAD-13) fills prose.

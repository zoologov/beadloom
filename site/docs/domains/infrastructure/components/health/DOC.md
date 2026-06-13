<!-- beadloom:badge-start -->
> ✅ **fresh**
> 
> last synced 2026-06-13T22:42:55.793320+00:00 · coverage 100% (`health`)
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

# Health (component)

Internal building block of the infrastructure domain.

**Source:** `src/beadloom/infrastructure/health.py`

---

## Overview

Computes and persists health snapshots (node/edge/doc/coverage counts and lint
state), derives trends across snapshots, and renders the Rich health dashboard
shown by `beadloom status`. The honest, point-in-time picture of project
health that the rest of the tooling reports against.

> Component doc skeleton (BDL-051 S3b / BEAD-14). Tech-writer (BEAD-13) fills prose.

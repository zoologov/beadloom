<!-- beadloom:badge-start -->
> ✅ **fresh**
> 
> last synced 2026-06-13T22:42:55.793320+00:00 · coverage 100% (`git-activity`)
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

# Git Activity (component)

Internal building block of the infrastructure domain.

**Source:** `src/beadloom/infrastructure/git_activity.py`

---

## Overview

Parses `git log` to compute per-node activity metrics — commit counts,
contributors, and an activity classification — by mapping each changed file to
its closest source directory (node). Feeds the health dashboard and the
landscape with an honest "where is the work happening" signal.

> Component doc skeleton (BDL-051 S3b / BEAD-14). Tech-writer (BEAD-13) fills prose.

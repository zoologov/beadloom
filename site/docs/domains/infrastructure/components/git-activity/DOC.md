<!-- beadloom:badge-start -->
> ✅ **fresh**
> 
> last synced 2026-06-14T12:30:18.610981+00:00 · coverage 100% (`git-activity`)
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

## Public surface

- `analyze_git_activity(project_root, source_dirs)` — run `git log` over ~90
  days, parse it, map each changed file to its owning node by longest
  source-prefix match, and return `{ref_id: GitActivity}`.
- `GitActivity` — frozen dataclass: `commits_30d`, `commits_90d`,
  `last_commit_date`, `top_contributors`, `activity_level`
  (`hot` >20/30d, `warm` 5–20, `cold` 1–4, `dormant` 0/90d).

## Collaborators

Run by `reindex` (application layer), which stores the result in `nodes.extra`.
That `activity` then surfaces in the context bundle (`builder`), the debt
report, the metrics dashboard, and the landscape. Reads git via subprocess
only; no network.

> Component doc (BDL-051). Public surface verified against `git_activity.py`.

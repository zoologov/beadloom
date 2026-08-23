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

## Invariants

- `git log` output is decoded with a stated codec (`utf-8`), never the image's
  locale: it carries author NAMES, and MEASURED on a repo authored by
  "Иван Петров" an ambient `latin-1` produced `Ð\x98Ð²Ð°Ð½ ...` — a contributor
  who does not exist, shown in the dashboard as a real person — while an ambient
  `ascii` raised `UnicodeDecodeError` past the handler.
- `errors="replace"`, chosen by direction of failure: a name reaches sqlite
  through `reindex`'s `UPDATE nodes SET extra = ?`, and sqlite3 encodes
  parameters as strict UTF-8, so the injective `surrogateescape` alternative
  would turn a display defect into a `reindex` crash inside `beadloom ci`
  (MEASURED). The stated cost: two authors differing only in a byte that is not
  UTF-8 render as one — a display loss only, never a gate or an exit code.
- Git being unavailable — missing, not executable, wedged past the 30 s timeout —
  degrades to `{}` ("no activity"), never to an exception at the caller.

## Collaborators

Run by `reindex` (application layer), which stores the result in `nodes.extra`.
That `activity` then surfaces in the context bundle (`builder`), the debt
report, the metrics dashboard, and the landscape. Reads git via subprocess
only; no network.

> Component doc (BDL-051). Public surface verified against `git_activity.py`.

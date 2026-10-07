# Git Activity (component)

Internal building block of the infrastructure domain.

**Source:** `src/beadloom/infrastructure/git_activity.py`

---

## Overview

Parses `git log --numstat` to compute per-node activity — changed lines, commit counts,
contributors and an activity level — by mapping each changed file to its closest source
directory (node). Feeds the node card, `ctx`, the debt report, the TUI and the landscape with
a "where is the work happening" signal.

Since BDL-078 (owner's ruling 6) the measure is **changed lines** (added + deleted), not
commits. On a squash-merged history a ten-commit branch and a one-line fix are each one
commit, so a commit count describes the merge habit rather than the work: before the change,
85 of this repository's 130 nodes read `cold`. The levels are **relative to the project**
rather than fixed thresholds.

## Levels

| Level | Rule |
|-------|------|
| `hot` | changed in the last 30 days, in the top tenth of its population by changed lines |
| `warm` | changed in the last 30 days, in the next three tenths |
| `cool` | changed in the last 30 days, the rest |
| `quiet` | no change in 30 days, some in 90 |
| `dormant` | no change in 90 days |

The population is decided per kind of node: a **box** (a node another node is `part_of`) is
ranked among boxes, every other node among the rest (`beadloom-btkd.1`). A box holds its
parts' lines, so in one population with the leaves it outranked them: on this repository seven
of the ten `hot` were boxes. The edges of the rule:

- **Ties** share the higher level: a node's rank is the number of nodes with strictly more
  lines, so equal counts never split across a cut.
- **Small projects:** both cuts round up (`ceil(n/10)`, `ceil(4n/10)`), so the busiest changed
  node is always `hot`. With one changed node it is `hot`; with two, the other is `cool`.
- **A change of zero lines** (a binary file, a pure move) is a change, so the node is not
  `quiet`, and it is never above `cool`.
- **Renames** are detected (`-M`). Edited lines count at the path the file now has, and the
  commit counts for both paths' nodes.
- **Windows** are exact instants (`now - 30 days`, `now - 90 days`) on the committer date.

Because the levels are relative, a node's level can change when the rest of the project
changes, with no change to the node itself.

## Roll-up

Given the `part_of` containers, a node's counts are its own files' plus every node it
contains. Each file is attributed to exactly one node (the most specific source), so the
roll-up never counts a line twice, and one commit touching two parts is one commit of the box.
A container with no source passes the roll-up on to its own containers and gets no entry.

## Machine-written files

A file a machine wrote counts neither its lines nor its commit:

- a dependency lock file, by file name (`LOCK_FILES`, 20 names: `package-lock.json`,
  `yarn.lock`, `pnpm-lock.yaml`, `uv.lock`, `poetry.lock`, `Cargo.lock`, `go.sum`,
  `Gemfile.lock`, `composer.lock`, `Package.resolved`, `gradle.lockfile` and others);
- a file git's attributes mark `linguist-generated` (set or `true`) or `binary` (set), read
  with `git check-attr` from `.gitattributes` as the working tree holds it;
- a file matching one of the project's own patterns, declared under `activity.exclude` in
  `.beadloom/config.yml` (read by `application.activity_settings`; see
  [Getting Started](../../../../getting-started.md#configuration)).

A commit that touched only such files is no commit of the node. A binary file that no
attribute marks is still a change of zero lines: git detected it, nobody declared it generated.

**The pattern grammar differs from `.gitignore`.** A pattern without a `/` matches the file
name in any folder. A pattern with a `/` matches the whole path from the project root, and
`*` crosses directories, so `src/*.py` also matches `src/a/b.py`. In `.gitignore`, `*` stops at
`/`. Matching is `fnmatch`, case-sensitive.

## Shallow history

Activity is measured on the history the clone holds (`beadloom-btkd.9`). Git shows the first
commit of a shallow clone as adding every file, so on a clone one commit deep every node read
"1 commit" and its changed lines were the size of its files. `read_git_history()` tells the
cases apart: a full history is measured; a shallow clone whose first commits landed before the
90-day window opened holds every change the window needs and is measured; any other shallow
clone records no activity, as without git. `activity_history_note()` gives the one sentence
the reindex and the Gate print for a shallow history.

## Public surface

- `analyze_git_activity(project_root, source_dirs, containers=None, *, now=None, excluded=(),
  history=Unread.UNREAD)` -> `dict[str, GitActivity]` — reads `git log --numstat` over 90 days, maps
  each changed file to the most specific node whose source it lies under, rolls boxes up and
  ranks the levels. "Lies under" is [`NodeSource.holds`](../node-source/DOC.md), by path
  component: a commit to `src/ledger_archive/` does not count toward a node sourced at
  `src/ledger/`. `containers` maps `ref_id` to the nodes it is `part_of`; `now` is the instant
  the windows end at; `excluded` holds the project's patterns. `history` takes what
  `read_git_history()` answered for the same `now`, `None` included, when the caller has read
  it already (the full reindex does, `beadloom-btkd.18`); it is read here when omitted or
  `Unread.UNREAD`. `None` cannot mean "not read", because it is `read_git_history()`'s own
  answer when git cannot say. Returns
  `{}` without git or on a shallow clone that does not reach back 90 days.
- `GitActivity` — frozen dataclass: `commits_30d`, `commits_90d`, `last_commit_date`,
  `top_contributors` (top 3 by commit count), `activity_level` (one of `ACTIVITY_LEVELS`),
  `lines_30d`, `lines_90d`.
- `rank_activity_levels(changed_30d, *, changed_90d, nodes=(), boxes=())` -> `dict[str, str]`
  — the ranking alone, over the nodes' changed lines.
- `Unread` — enum with the one member `UNREAD`, what a caller passes when it did not read the
  history (public since `beadloom-btkd.20`).
- `GitHistory(shallow, commits=0, reaches_window=True)` — `measurable`, and `describe()`
  (`history: full` or `history: shallow (N commits)`).
- `read_git_history(project_root, *, now=None)` -> `GitHistory | None` — `None` when git cannot
  say.
- `activity_history_note(history)` -> `str` — `""` for a full history or `None`; otherwise
  `measured on history: shallow (N commits), which reaches back 90 days` or `not measured on
  history: shallow (N commits), which does not reach back 90 days; check out the full history
  (actions/checkout fetch-depth: 0)`.
- `ACTIVITY_LEVELS` (`hot`, `warm`, `cool`, `quiet`, `dormant`), `RECENT_DAYS` (30),
  `HISTORY_DAYS` (90), `LOCK_FILES`.
- `NO_CHANGE_WORDS` (`quiet`: `no change in 30 days`, `dormant`: `no change in 90 days`) and
  `count_in_words(count, noun)` (`1 line`, `0 lines`, `2 commits`) — the one wording `ctx`, the
  TUI and the card read, re-exported by `application.graph_reads` for the TUI
  (`beadloom-btkd.18`).

## Invariants

- `git log` output is decoded with a stated codec (`utf-8`), never the image's
  locale: it carries author NAMES, and MEASURED on a repo authored by
  "Иван Петров" an ambient `latin-1` produced `Ð\x98Ð²Ð°Ð½ ...` — a contributor
  who does not exist, shown in the dashboard as a real person — while an ambient
  `ascii` raised `UnicodeDecodeError` past the handler. Every git call goes through one
  runner, so the codec is stated once.
- `errors="replace"`, chosen by direction of failure: a name reaches sqlite
  through `reindex`'s `UPDATE nodes SET extra = ?`, and sqlite3 encodes
  parameters as strict UTF-8, so the injective `surrogateescape` alternative
  would turn a display defect into a `reindex` crash inside `beadloom ci`
  (MEASURED). The stated cost: two authors differing only in a byte that is not
  UTF-8 render as one — a display loss only, never a gate or an exit code.
- Git being unavailable — missing, not executable, wedged past the 30 s timeout —
  degrades to `{}` ("no activity"), never to an exception at the caller. Without
  `git check-attr`'s answer no file is taken for generated, and every change counts.

## Collaborators

Run by `reindex` (application layer), which stores the result in `nodes.extra`.
That `activity` then surfaces in the context bundle (`builder`, `ctx`), the node card of the
portal (`lines_30d`, `commits_30d`, `level` in the data file), the debt report (which counts
`dormant` nodes), the TUI and the landscape. Reads git via subprocess only; no network.

> Component doc (BDL-051). Public surface verified against `git_activity.py` (BDL-078).

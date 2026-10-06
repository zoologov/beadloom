"""Git history analysis: per-node changed lines, commits, contributors and activity level.

Provides per-node activity metrics by parsing ``git log --numstat`` output and
mapping each changed file to its closest source directory (node).

BDL-078 F-activity (owner's ruling 6). A commit count describes the merge habit,
not the work: on a squash-merged history a ten-commit branch and a one-line fix
are each one commit. So the measure is **changed lines** (added + deleted), and
the levels are **relative to the project** rather than fixed thresholds:

- among the nodes with a change in the last 30 days, ranked by changed lines,
  the top tenth is ``hot``, the next three tenths ``warm``, the rest ``cool``;
- no change in 30 days but some in 90 is ``quiet``; none in 90 is ``dormant``.

How the edges of that rule are decided:

- **Ties** share the higher level: a node's rank is the number of nodes with
  strictly more lines, so equal counts never split across a cut.
- **Small projects:** both cuts round up (``ceil(n/10)`` and ``ceil(4n/10)``), so
  the busiest changed node is always ``hot``; with one changed node it is ``hot``,
  with two the other is ``cool``.
- **A change of zero lines** — a binary file, a pure move — is a change (the node
  is not ``quiet``), and is never above ``cool``.
- **Binary files** count as a change of zero lines: ``numstat`` gives no line
  count for them, and a size in bytes is not a line.
- **Renames** are detected (``-M``) and their edited lines are counted at the
  path the file now has; the commit counts for both paths' nodes. A move is not
  authorship, so a reorganisation of directories does not read as the busiest
  work of the month.
- **Windows** are exact instants (``now - 30 days``, ``now - 90 days``) on the
  committer date, the date a change landed on the branch and the one ``--since``
  filters on.

A **box rolls up its descendants**: given the ``part_of`` containers, a node's
counts are its own files' plus every node it contains. Each file is attributed
to exactly one node (the most specific source), so the roll-up never counts a
line twice; one commit touching two parts is one commit of the box.

BDL-078 ``beadloom-btkd.1`` (the owner, after F-activity) refined two things:

- **Boxes rank among boxes, leaves among leaves.** A box — a node another node
  is ``part_of`` — holds its parts' lines, so in one population with the leaves
  it outranks them (7 of one project's 10 ``hot`` nodes were boxes). Each
  population takes the same tenths on its own.
- **A file a machine wrote is not change**: neither its lines nor its commit
  count. That is a dependency lock file (:data:`LOCK_FILES`, by file name), a
  file git's attributes mark ``linguist-generated`` or ``binary``, and a file
  matching a pattern the project declares (*excluded*). A pattern without a
  ``/`` matches a file name anywhere; a pattern with one matches the whole path
  from the project root, ``*`` crossing directories. A binary file that no
  attribute marks is still a change of zero lines, as above: git detected it,
  nobody declared it generated.

BDL-078 ``beadloom-btkd.9`` (T's finding F1): **activity is measured on the
history the clone holds.** Git shows the first commit of a shallow clone as
adding every file, so on a clone one commit deep every node read "1 commit" and
its changed lines were the size of its files. A shallow clone whose first
commits landed inside the 90-day window cannot say what changed in it, so no
activity is recorded, as without git, and :func:`activity_history_note` says
why; a shallow clone that reaches back past the window holds every change the
window needs, and is measured. :func:`read_git_history` tells the two apart.
"""

# beadloom:domain=infrastructure
# beadloom:component=git-activity

from __future__ import annotations

import subprocess
from collections import Counter
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from fnmatch import fnmatchcase
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from beadloom.infrastructure.node_source import NodeSource

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping
    from pathlib import Path


#: The activity levels, busiest first.
ACTIVITY_LEVELS = ("hot", "warm", "cool", "quiet", "dormant")

#: The recent window and the history window, in days.
RECENT_DAYS = 30
HISTORY_DAYS = 90

#: The cumulative shares of the changed nodes that are ``hot`` and ``hot`` or ``warm``,
#: in tenths: the top tenth, then the next three tenths.
_HOT_TENTHS = 1
_WARM_TENTHS = 4
_TENTHS = 10

#: Dependency lock files, by file name: a package manager writes them, nobody authors them.
LOCK_FILES = frozenset(
    {
        # JavaScript
        "package-lock.json",
        "npm-shrinkwrap.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "bun.lock",
        "bun.lockb",
        # Python
        "uv.lock",
        "poetry.lock",
        "Pipfile.lock",
        "pdm.lock",
        # Rust, Go, Ruby, PHP
        "Cargo.lock",
        "go.sum",
        "Gemfile.lock",
        "composer.lock",
        # Swift, Objective-C, Dart, Elixir
        "Package.resolved",
        "Podfile.lock",
        "pubspec.lock",
        "mix.lock",
        # JVM, .NET
        "gradle.lockfile",
        "packages.lock.json",
    }
)

#: The git attributes that mark a file machine-written, and the values that set them.
_GENERATED_ATTRIBUTES: dict[str, frozenset[str]] = {
    "linguist-generated": frozenset({"set", "true"}),
    "binary": frozenset({"set"}),
}

#: How many contributors a node records.
_TOP_CONTRIBUTORS = 3

#: Field and record separators in the ``git log`` format: neither can occur in a
#: hash, a date or an author name.
_RECORD = "\x1e"
_FIELD = "\x1f"


@dataclass(frozen=True)
class GitActivity:
    """Git activity metrics for a single graph node (its descendants rolled up)."""

    commits_30d: int
    commits_90d: int
    last_commit_date: str  # ISO 8601 date
    top_contributors: list[str]  # top 3 by commit count
    activity_level: str  # one of ACTIVITY_LEVELS
    lines_30d: int = 0  # changed lines (added + deleted) in 30 days
    lines_90d: int = 0  # changed lines (added + deleted) in 90 days


@dataclass(frozen=True)
class GitHistory:
    """How much of the project's history the clone holds.

    ``shallow`` is git's own answer. A shallow clone also records how many
    commits it holds and whether the commits it was cut at landed before the
    history window opened (``reaches_window``): only then does it hold every
    change the window needs. A full history reaches every window.
    """

    shallow: bool
    commits: int = 0
    reaches_window: bool = True

    @property
    def measurable(self) -> bool:
        """Whether activity can be measured on this history."""
        return not self.shallow or self.reaches_window

    def describe(self) -> str:
        """``history: full``, or ``history: shallow (N commits)``."""
        if not self.shallow:
            return "history: full"
        noun = "commit" if self.commits == 1 else "commits"
        return f"history: shallow ({self.commits} {noun})"


def activity_history_note(history: GitHistory | None) -> str:
    """What activity was measured on, for a shallow history; ``""`` for any other.

    The one wording the reindex and the Gate both print, so the two cannot
    describe one clone differently.
    """
    if history is None or not history.shallow:
        return ""
    if history.reaches_window:
        return f"measured on {history.describe()}, which reaches back {HISTORY_DAYS} days"
    return (
        f"not measured on {history.describe()}, which does not reach back {HISTORY_DAYS} "
        "days; check out the full history (actions/checkout fetch-depth: 0)"
    )


def rank_activity_levels(
    changed_30d: Mapping[str, int],
    *,
    changed_90d: Collection[str],
    nodes: Iterable[str] = (),
    boxes: Collection[str] = (),
) -> dict[str, str]:
    """The level of every node, relative to the project.

    *changed_30d* maps each node with a change in the last 30 days to its changed
    lines; *changed_90d* names the nodes with a change in 90 days; *nodes* names
    any further node, which is ``dormant`` unless one of the two says otherwise.
    *boxes* names the nodes that contain others: they are ranked among
    themselves, every other node among the rest. The rule and its edges are in
    the module docstring.
    """
    levels: dict[str, str] = {}
    for ref_id in {*nodes, *changed_90d}:
        levels[ref_id] = "quiet" if ref_id in changed_90d else "dormant"
    for is_box in (True, False):
        population = {
            ref_id: lines for ref_id, lines in changed_30d.items() if (ref_id in boxes) is is_box
        }
        levels.update(_rank_changed(population))
    return levels


def _rank_changed(changed_30d: Mapping[str, int]) -> dict[str, str]:
    """``hot``, ``warm`` or ``cool`` for each node of one population, by its lines."""
    population = len(changed_30d)
    hot_cut = -(-population * _HOT_TENTHS // _TENTHS)
    warm_cut = -(-population * _WARM_TENTHS // _TENTHS)
    ordered = sorted(changed_30d.values(), reverse=True)

    levels: dict[str, str] = {}
    for ref_id, lines in changed_30d.items():
        rank = _count_above(ordered, lines)
        if lines > 0 and rank < hot_cut:
            levels[ref_id] = "hot"
        elif lines > 0 and rank < warm_cut:
            levels[ref_id] = "warm"
        else:
            levels[ref_id] = "cool"
    return levels


def _count_above(descending: list[int], value: int) -> int:
    """How many entries of *descending* are strictly greater than *value*."""
    count = 0
    for entry in descending:
        if entry <= value:
            break
        count += 1
    return count


def _map_file_to_node(
    file_path: str,
    source_dirs: dict[str, str],
) -> str | None:
    """Map a file path to the closest matching node ref_id.

    Among the nodes whose source *file_path* lies under — by the one rule
    :class:`~beadloom.infrastructure.node_source.NodeSource` holds, which this
    function wrote for itself until BDL-069 `beadloom-rqma.4` — returns the one with
    the longest source (most specific). The ranking is this function's own.
    """
    best_match: str | None = None
    best_len = 0

    for ref_id, src_dir in source_dirs.items():
        under = NodeSource(src_dir)
        if under.holds(file_path) and len(under.path) > best_len:
            best_match = ref_id
            best_len = len(under.path)

    return best_match


@dataclass(frozen=True)
class _FileChange:
    """One file a commit changed: its path now, its path before a rename, its lines."""

    path: str
    lines: int
    old_path: str = ""


@dataclass(frozen=True)
class _CommitInfo:
    """Parsed information from a single git commit."""

    commit_hash: str
    landed: datetime
    author: str
    changes: tuple[_FileChange, ...]


def _parse_date(text: str) -> datetime | None:
    # Python 3.10's ``fromisoformat`` does not read a "Z" suffix.
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _parse_numstat(body: str) -> tuple[_FileChange, ...]:
    """Read the NUL-separated ``--numstat -z`` entries of one commit.

    An entry is ``added<TAB>deleted<TAB>path``; a rename leaves the path empty
    and gives the old and new paths as the next two fields. A binary file reads
    ``-`` for both counts and changes zero lines.
    """
    tokens = [token.lstrip("\n") for token in body.split("\0")]
    changes: list[_FileChange] = []
    i = 0
    while i < len(tokens):
        parts = tokens[i].split("\t", 2)
        i += 1
        if len(parts) != 3:
            continue
        added, deleted, path = parts
        lines = int(added) + int(deleted) if added.isdigit() and deleted.isdigit() else 0
        if path:
            changes.append(_FileChange(path=path, lines=lines))
        elif i + 1 < len(tokens):
            changes.append(_FileChange(path=tokens[i + 1], lines=lines, old_path=tokens[i]))
            i += 2
    return tuple(changes)


def _parse_git_log(output: str) -> list[_CommitInfo]:
    """Parse the output of :data:`_GIT_LOG_FORMAT` with ``--numstat -z``.

    Each commit opens with the record separator, then the hash, the committer
    date and the author name separated by the field separator, then a NUL, then
    its ``numstat`` entries. A record that does not read so is skipped.
    """
    commits: list[_CommitInfo] = []
    for record in output.split(_RECORD):
        header, _, body = record.partition("\0")
        fields = header.split(_FIELD)
        if len(fields) != 3:
            continue
        commit_hash, date, author = fields
        landed = _parse_date(date.strip())
        if landed is None:
            continue
        commits.append(
            _CommitInfo(
                commit_hash=commit_hash.strip(),
                landed=landed,
                author=author,
                changes=_parse_numstat(body),
            )
        )
    return commits


#: Hash, committer date, author name — the committer date being the one ``--since`` reads.
_GIT_LOG_FORMAT = f"--format={_RECORD}%H{_FIELD}%cI{_FIELD}%aN"


def _git_output(project_root: Path, *args: str, stdin: str | None = None) -> str | None:
    """What ``git <args>`` prints in *project_root*, or ``None`` when git cannot say."""
    # The codec is stated, not inherited: this output is author NAMES and file
    # paths, and ``text=True`` would decode them with
    # ``locale.getpreferredencoding(False)``. MEASURED on a repo authored by
    # "Иван Петров": an ambient latin-1 yields "Ð\x98Ð²Ð°Ð½ ..." -- a contributor
    # who does not exist, shown in the dashboard as a real person -- and an
    # ambient ascii raises ``UnicodeDecodeError``, which is a ``ValueError`` and
    # so escaped the handler below. A path written to git's input is encoded
    # with the same codec.
    #
    # ``errors="replace"`` rather than ``surrogateescape``, and the reason is the
    # direction of failure rather than fidelity: a name reaches sqlite through
    # ``reindex``'s ``UPDATE nodes SET extra = ?``, and sqlite3 encodes
    # parameters as strict UTF-8 -- MEASURED, a lone surrogate raises
    # ``UnicodeEncodeError`` there, turning a display defect into a ``reindex``
    # crash inside ``beadloom ci``. The cost is stated and bounded: ``replace``
    # is not injective, so two authors differing only in a byte that is not UTF-8
    # render as one. That loss touches names which are already not UTF-8, only
    # their display, and never a gate, a verdict or an exit code.
    try:
        result = subprocess.run(  # noqa: S603
            ["git", *args],  # noqa: S607
            cwd=str(project_root),
            input=stdin,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        # OSError covers git-missing (FileNotFoundError), permission denied,
        # and an invalid cwd (NotADirectoryError); SubprocessError covers
        # TimeoutExpired (reachable: timeout=30 above) and other subprocess
        # failures. With the codec stated above, no decode error can reach here,
        # so this enumeration is complete rather than merely plausible. Git
        # being unavailable for any of these reasons degrades gracefully to
        # "no activity".
        return None
    return result.stdout if result.returncode == 0 else None


def _read_history(project_root: Path, since: datetime) -> list[_CommitInfo] | None:
    """The commits that landed after *since*, or ``None`` when git cannot say.

    ``-M`` states rename detection rather than inheriting ``diff.renames``;
    ``-z`` leaves paths unquoted, whatever ``core.quotePath`` says.
    """
    output = _git_output(
        project_root,
        "log",
        _GIT_LOG_FORMAT,
        "--numstat",
        "-z",
        "-M",
        f"--since={since.isoformat()}",
    )
    return None if output is None else _parse_git_log(output)


def _boundary_dates(project_root: Path) -> list[datetime]:
    """When each commit a shallow clone was cut at landed; none when git cannot say.

    Git lists those commits, whose parents the clone lacks, in its ``shallow``
    file (``git rev-parse --git-path shallow`` names where it is).
    """
    where = _git_output(project_root, "rev-parse", "--git-path", "shallow")
    if where is None:
        return []
    try:
        hashes = (project_root / where.strip()).read_text(encoding="ascii").split()
    except (OSError, ValueError):
        return []
    if not hashes:
        return []
    dates = _git_output(project_root, "log", "--no-walk", "--format=%cI", *hashes)
    if dates is None:
        return []
    return [landed for line in dates.splitlines() if (landed := _parse_date(line.strip()))]


def read_git_history(project_root: Path, *, now: datetime | None = None) -> GitHistory | None:
    """How much history the clone at *project_root* holds; ``None`` when git cannot say.

    A shallow clone reaches the window ending at *now* (the current time when
    omitted) when every commit it was cut at landed before the window opened.
    """
    answer = _git_output(project_root, "rev-parse", "--is-shallow-repository")
    if answer is None:
        return None
    if answer.strip() != "true":
        return GitHistory(shallow=False)
    counted = (_git_output(project_root, "rev-list", "--count", "HEAD") or "").strip()
    history_since = (now or datetime.now(tz=timezone.utc)) - timedelta(days=HISTORY_DAYS)
    starts = _boundary_dates(project_root)
    return GitHistory(
        shallow=True,
        commits=int(counted) if counted.isdigit() else 0,
        reaches_window=bool(starts) and all(start < history_since for start in starts),
    )


def _matches_declared(path: str, patterns: Collection[str]) -> bool:
    """Whether *path* matches a pattern: by file name without a ``/``, by path with one."""
    name = PurePosixPath(path).name
    return any(fnmatchcase(path if "/" in pattern else name, pattern) for pattern in patterns)


def _marked_by_attributes(project_root: Path, paths: Collection[str]) -> set[str]:
    """The *paths* git's attributes mark generated or binary; none when git cannot say.

    ``git check-attr`` reads ``.gitattributes`` as the working tree holds it, so a
    file is judged by what the project declares now, not when it was committed.

    The codec is stated both ways, UTF-8 with ``replace``, for the reason
    ``_git_output`` gives: the paths are the ones ``_read_history`` decoded, and
    no ambient codec has a say.
    """
    if not paths:
        return set()
    output = _git_output(
        project_root,
        "check-attr",
        "-z",
        "--stdin",
        *_GENERATED_ATTRIBUTES,
        stdin="".join(f"{path}\0" for path in paths),
    )
    if output is None:
        # The same degradation as ``_read_history``: without git's answer no
        # file is taken for generated, and every change counts.
        return set()
    # ``-z`` output is ``path NUL attribute NUL value NUL`` per attribute asked.
    fields = output.split("\0")
    marked: set[str] = set()
    for index in range(0, len(fields) - 2, 3):
        path, attribute, value = fields[index : index + 3]
        if value in _GENERATED_ATTRIBUTES.get(attribute, frozenset()):
            marked.add(path)
    return marked


def _machine_written(
    project_root: Path, commits: list[_CommitInfo], excluded: Collection[str]
) -> set[str]:
    """The changed paths that are not authored: lock files, marked files, declared patterns."""
    paths = {change.path for commit in commits for change in commit.changes}
    by_name = {
        path
        for path in paths
        if PurePosixPath(path).name in LOCK_FILES or _matches_declared(path, excluded)
    }
    return by_name | _marked_by_attributes(project_root, paths - by_name)


def _authored_only(
    project_root: Path, commits: list[_CommitInfo], excluded: Collection[str]
) -> list[_CommitInfo]:
    """*commits* without their machine-written changes; a commit of only those changes none."""
    machine = _machine_written(project_root, commits, excluded)
    if not machine:
        return commits
    return [
        replace(commit, changes=tuple(c for c in commit.changes if c.path not in machine))
        for commit in commits
    ]


@dataclass
class _Tally:
    """One node's commits (by hash) and changed lines in the two windows."""

    commits: dict[str, _CommitInfo] = field(default_factory=dict)
    lines_30d: int = 0
    lines_90d: int = 0

    def absorb(self, other: _Tally) -> None:
        self.commits.update(other.commits)
        self.lines_30d += other.lines_30d
        self.lines_90d += other.lines_90d


def _own_tallies(
    commits: list[_CommitInfo],
    source_dirs: dict[str, str],
    recent_since: datetime,
) -> dict[str, _Tally]:
    """Each node's tally over the files attributed to it, its descendants not included."""
    tallies = {ref_id: _Tally() for ref_id in source_dirs}
    owners: dict[str, str | None] = {}

    def owner(path: str) -> str | None:
        if path not in owners:
            owners[path] = _map_file_to_node(path, source_dirs)
        return owners[path]

    for commit in commits:
        recent = commit.landed >= recent_since
        for change in commit.changes:
            for path in (change.path, change.old_path):
                ref_id = owner(path) if path else None
                if ref_id is not None:
                    tallies[ref_id].commits[commit.commit_hash] = commit
            ref_id = owner(change.path)
            if ref_id is None:
                continue
            tallies[ref_id].lines_90d += change.lines
            if recent:
                tallies[ref_id].lines_30d += change.lines
    return tallies


def _ancestors(ref_id: str, containers: Mapping[str, Collection[str]]) -> set[str]:
    """Every node that contains *ref_id*, directly or not; never *ref_id* itself."""
    found: set[str] = set()
    frontier = list(containers.get(ref_id, ()))
    while frontier:
        current = frontier.pop()
        if current == ref_id or current in found:
            continue
        found.add(current)
        frontier.extend(containers.get(current, ()))
    return found


def _roll_up(
    own: dict[str, _Tally],
    containers: Mapping[str, Collection[str]],
) -> dict[str, _Tally]:
    """Each node's tally with every node it contains added in."""
    rolled = {
        ref_id: _Tally(dict(t.commits), t.lines_30d, t.lines_90d) for ref_id, t in own.items()
    }
    for ref_id, tally in own.items():
        for ancestor in _ancestors(ref_id, containers):
            if ancestor in rolled:
                rolled[ancestor].absorb(tally)
    return rolled


def _activity_of(tally: _Tally, recent_since: datetime, level: str) -> GitActivity:
    commits = tally.commits.values()
    authors = Counter(commit.author for commit in commits)
    last = max((commit.landed for commit in commits), default=None)
    return GitActivity(
        commits_30d=sum(1 for commit in commits if commit.landed >= recent_since),
        commits_90d=len(tally.commits),
        last_commit_date=last.date().isoformat() if last else "",
        top_contributors=[name for name, _ in authors.most_common(_TOP_CONTRIBUTORS)],
        activity_level=level,
        lines_30d=tally.lines_30d,
        lines_90d=tally.lines_90d,
    )


def analyze_git_activity(
    project_root: Path,
    source_dirs: dict[str, str],
    containers: Mapping[str, Collection[str]] | None = None,
    *,
    now: datetime | None = None,
    excluded: Collection[str] = (),
) -> dict[str, GitActivity]:
    """Analyze git history for each node's source directory.

    Parameters
    ----------
    project_root:
        Root of the project (where ``.git/`` lives).
    source_dirs:
        Mapping of ``ref_id -> source_path`` (relative to project root).
    containers:
        Mapping of ``ref_id -> the nodes it is part_of``. A node's activity
        includes every node it contains; without it each node counts only the
        files attributed to it. A container with no source passes the roll-up on
        to its own containers and gets no entry.
    now:
        The instant the windows end at; the current time when omitted.
    excluded:
        The project's own patterns of machine-written files, beside the lock
        files and the files git's attributes mark; see the module docstring.

    Returns
    -------
    dict[str, GitActivity]
        Mapping of ``ref_id -> GitActivity`` for each node in *source_dirs*.
        Returns empty dict if not a git repo, git is unavailable, or the clone
        is shallow and does not reach back over the history window
        (:func:`read_git_history`).
    """
    if not source_dirs:
        return {}

    now = now or datetime.now(tz=timezone.utc)
    recent_since = now - timedelta(days=RECENT_DAYS)
    history_since = now - timedelta(days=HISTORY_DAYS)

    clone = read_git_history(project_root, now=now)
    if clone is not None and not clone.measurable:
        return {}
    history = _read_history(project_root, history_since)
    if history is None:
        return {}
    # ``--since`` already filters; the instant is applied here too, so the window
    # is the one stated rather than whatever git's date parsing made of it.
    commits = _authored_only(
        project_root, [commit for commit in history if commit.landed >= history_since], excluded
    )

    containers = containers or {}
    rolled = _roll_up(_own_tallies(commits, source_dirs, recent_since), containers)
    levels = rank_activity_levels(
        {
            ref_id: tally.lines_30d
            for ref_id, tally in rolled.items()
            if any(commit.landed >= recent_since for commit in tally.commits.values())
        },
        changed_90d={ref_id for ref_id, tally in rolled.items() if tally.commits},
        nodes=rolled,
        boxes={box for held_by in containers.values() for box in held_by},
    )
    return {
        ref_id: _activity_of(tally, recent_since, levels[ref_id])
        for ref_id, tally in rolled.items()
    }

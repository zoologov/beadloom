"""Git history analysis: commit activity, contributors, and activity classification.

Provides per-node activity metrics by parsing ``git log`` output and mapping
changed files to their closest source directory (node).
"""

# beadloom:domain=infrastructure

from __future__ import annotations

import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


@dataclass(frozen=True)
class GitActivity:
    """Git activity metrics for a single graph node."""

    commits_30d: int
    commits_90d: int
    last_commit_date: str  # ISO 8601
    top_contributors: list[str]  # top 3 by commit count
    activity_level: str  # hot | warm | cold | dormant


def _classify_activity(commits_30d: int, commits_90d: int) -> str:
    """Classify activity level based on commit counts.

    | Level   | Criteria                    |
    |---------|-----------------------------|
    | hot     | >20 commits in 30 days      |
    | warm    | 5-20 commits in 30 days     |
    | cold    | 1-4 commits in 30 days      |
    | dormant | 0 commits in 90 days        |
    """
    if commits_30d > 20:
        return "hot"
    if commits_30d >= 5:
        return "warm"
    if commits_30d >= 1:
        return "cold"
    if commits_90d == 0:
        return "dormant"
    # Has 90d commits but 0 in 30d — still cold (some recent-ish activity)
    return "cold"


def _map_file_to_node(
    file_path: str,
    source_dirs: dict[str, str],
) -> str | None:
    """Map a file path to the closest matching node ref_id.

    Checks whether the file path starts with any of the source directory
    prefixes. Returns the ref_id of the longest matching prefix (most specific).
    """
    best_match: str | None = None
    best_len = 0

    normalized = str(PurePosixPath(file_path))

    for ref_id, src_dir in source_dirs.items():
        prefix = str(PurePosixPath(src_dir))
        # Ensure prefix match is at a directory boundary
        is_match = normalized == prefix or normalized.startswith(prefix + "/")
        if is_match and len(prefix) > best_len:
            best_match = ref_id
            best_len = len(prefix)

    return best_match


@dataclass
class _CommitInfo:
    """Parsed information from a single git commit."""

    commit_hash: str
    date: str  # ISO 8601
    author: str
    files: list[str]


def _parse_git_log(output: str) -> list[_CommitInfo]:
    """Parse ``git log --format="%H %aI %aN" --name-only`` output.

    The format produces blocks like::

        <hash> <date> <author>
        <empty line>
        file1
        file2
        <empty line>

    Returns a list of parsed commits.
    """
    commits: list[_CommitInfo] = []
    if not output.strip():
        return commits

    lines = output.strip().split("\n")
    i = 0
    while i < len(lines):
        header = lines[i].strip()
        if not header:
            i += 1
            continue

        # Parse header: "<hash> <date> <author>"
        parts = header.split(" ", 2)
        if len(parts) < 3:
            i += 1
            continue

        commit_hash = parts[0]
        date = parts[1]
        author = parts[2]

        i += 1

        # Skip empty line after header
        if i < len(lines) and lines[i].strip() == "":
            i += 1

        # Collect file paths until next empty line or end
        files: list[str] = []
        while i < len(lines) and lines[i].strip() != "":
            file_path = lines[i].strip()
            # Check if this looks like a new commit header (contains ISO date pattern)
            if " " in file_path and len(file_path.split(" ", 2)) >= 3:
                test_date = file_path.split(" ", 2)[1]
                if "T" in test_date and ("+" in test_date or "Z" in test_date):
                    break
            files.append(file_path)
            i += 1

        commits.append(
            _CommitInfo(
                commit_hash=commit_hash,
                date=date,
                author=author,
                files=files,
            )
        )

    return commits


def _is_within_days(date_str: str, days: int) -> bool:
    """Check if an ISO 8601 date is within the given number of days from now."""
    now = datetime.now(tz=timezone.utc)
    try:
        commit_date = datetime.fromisoformat(date_str)
    except ValueError:
        return False

    delta = now - commit_date
    return delta.days <= days


def analyze_git_activity(
    project_root: Path,
    source_dirs: dict[str, str],
) -> dict[str, GitActivity]:
    """Analyze git history for each node's source directory.

    Parameters
    ----------
    project_root:
        Root of the project (where ``.git/`` lives).
    source_dirs:
        Mapping of ``ref_id -> source_path`` (relative to project root).

    Returns
    -------
    dict[str, GitActivity]
        Mapping of ``ref_id -> GitActivity`` for each node.
        Returns empty dict if not a git repo or git is unavailable.
    """
    if not source_dirs:
        return {}

    # Run git log: single invocation covering 90 days
    try:
        result = subprocess.run(
            ["git", "log", "--format=%H %aI %aN", "--name-only", "--since=90 days ago"],  # noqa: S607
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {}

    if result.returncode != 0:
        return {}

    # Parse the git log output
    commits = _parse_git_log(result.stdout)

    # Build per-node commit data
    # For each node, track: set of commit hashes in 30d/90d, contributors, last date
    node_commits_30d: dict[str, set[str]] = {ref_id: set() for ref_id in source_dirs}
    node_commits_90d: dict[str, set[str]] = {ref_id: set() for ref_id in source_dirs}
    node_contributors: dict[str, Counter[str]] = {ref_id: Counter() for ref_id in source_dirs}
    node_last_date: dict[str, str] = {ref_id: "" for ref_id in source_dirs}

    for commit in commits:
        # Determine which nodes this commit touches
        touched_nodes: set[str] = set()
        for file_path in commit.files:
            node = _map_file_to_node(file_path, source_dirs)
            if node is not None:
                touched_nodes.add(node)

        for ref_id in touched_nodes:
            # 90-day bucket (all commits from git log are within 90d)
            node_commits_90d[ref_id].add(commit.commit_hash)

            # 30-day bucket
            if _is_within_days(commit.date, 30):
                node_commits_30d[ref_id].add(commit.commit_hash)

            # Contributors: count unique commits per author for this node
            node_contributors[ref_id][commit.author] += 1

            # Track most recent commit date
            if not node_last_date[ref_id] or commit.date > node_last_date[ref_id]:
                node_last_date[ref_id] = commit.date

    # Build results
    results: dict[str, GitActivity] = {}
    for ref_id in source_dirs:
        c30 = len(node_commits_30d[ref_id])
        c90 = len(node_commits_90d[ref_id])

        # Top 3 contributors by commit count
        top = [name for name, _count in node_contributors[ref_id].most_common(3)]

        # Extract date part from ISO 8601
        last_date = node_last_date[ref_id]
        if last_date:
            try:
                parsed = datetime.fromisoformat(last_date)
                last_date = parsed.date().isoformat()
            except ValueError:
                pass

        results[ref_id] = GitActivity(
            commits_30d=c30,
            commits_90d=c90,
            last_commit_date=last_date,
            top_contributors=top,
            activity_level=_classify_activity(c30, c90),
        )

    return results

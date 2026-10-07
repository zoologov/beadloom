"""A project with dated commits over 200 days, and shallow clones of it.

BDL-078 ``beadloom-btkd.9``. Activity is measured on the history a clone holds,
so a test of a shallow history needs a project whose commits fall on both sides
of the 90-day window, and a real ``git clone --depth``: a clone of a local PATH
ignores ``--depth``, so the clone goes over ``file://``.

==========  ===================  ================================================
days ago    file                 what a clone of that depth starts from
==========  ===================  ================================================
200         ``src/web/web.py``   the first commit: the graph, both nodes' files
150         ``src/web/web.py``   depth 3: its first commit lies before the window
45          ``src/api/api.py``   depth 2: its first commit lies inside the window
5           ``src/web/web.py``   depth 1: the clone's one commit
==========  ===================  ================================================

So on the full history ``web`` changed 12 lines in 30 days and ``api`` is quiet.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from tests.support.squash_merged_repo import commit_lines, init_repo, run_git

if TYPE_CHECKING:
    from pathlib import Path

#: ``ref_id -> source`` for the project's nodes.
SOURCES: dict[str, str] = {"web": "src/web", "api": "src/api"}

#: Lines the most recent commit adds to ``web``: its changed lines in 30 days.
WEB_LINES_30D = 12

#: The first commit's age, in days.
FIRST_COMMIT_DAYS = 200

#: The commits after the first, oldest first: (days ago, file, lines).
LATER_COMMITS = (
    (150, "src/web/web.py", 40),
    (45, "src/api/api.py", 7),
    (5, "src/web/web.py", WEB_LINES_30D),
)

_GRAPH = "nodes:\n" + "".join(
    f'  - ref_id: {ref_id}\n    kind: feature\n    summary: "{ref_id}"\n    source: {source}\n'
    for ref_id, source in SOURCES.items()
)


def build_dated_project(root: Path, *, now: datetime | None = None) -> Path:
    """Write the project the module docstring describes under *root*, graph committed."""
    now = now or datetime.now(tz=timezone.utc)
    init_repo(root)
    (root / ".beadloom" / "_graph").mkdir(parents=True)
    (root / ".beadloom" / "_graph" / "nodes.yml").write_text(_GRAPH, encoding="utf-8")
    (root / ".beadloom" / "config.yml").write_text("scan_paths:\n- src\n", encoding="utf-8")
    (root / "docs").mkdir()
    (root / "docs" / "README.md").write_text("# Docs\n", encoding="utf-8")
    (root / "src" / "api").mkdir(parents=True)
    (root / "src" / "api" / "api.py").write_text("x = 1\n", encoding="utf-8")
    first = now - timedelta(days=FIRST_COMMIT_DAYS)
    commit_lines(root, "src/web/web.py", 300, when=first, message="first")
    for days_ago, path, lines in LATER_COMMITS:
        commit_lines(root, path, lines, when=now - timedelta(days=days_ago))
    return root


def shallow_clone(origin: Path, clone: Path, depth: int) -> Path:
    """Clone *origin* into *clone* holding only its *depth* most recent commits."""
    run_git(origin.parent, "clone", "-q", "--depth", str(depth), f"file://{origin}", str(clone))
    return clone

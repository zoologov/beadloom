"""Copy this repository's working tree into a directory of its own, history included.

Why this exists (BDL-074 A2)
----------------------------
Self-checks assert on this repository's own graph. They used to reindex the
shared ``.beadloom/beadloom.db`` in place and read it (``live_repo_reindexed``),
so any other writer of that file could rebuild it underneath them — which is the
``beadloom-qq6m`` flake (``database disk image is malformed``, ``disk I/O
error``). The session fixture in ``tests/conftest.py`` calls
:func:`build_snapshot` once and reindexes the copy, and every self-check reads
that copy instead.

What the copy holds, stated as a list somebody can check
--------------------------------------------------------
* the WORKING-TREE content of every file git tracks, plus every untracked file
  git would not ignore — the set a ``reindex`` on the tree walks, so a
  concurrent edit or a new module is what the self-checks judge;
* never an index file (``.beadloom/**/*.db`` and its sidecars): the copy builds
  its own;
* the git history, through ``git clone --shared --no-checkout``: the clone's
  objects are read from this repository's object store (immutable, so a reader
  cannot race a writer), its refs and its git index are its own. ``sync-check``
  corroborates a freshly built index against ``HEAD``; without history every
  pair would read ``no_baseline`` and the freshness checks would be green about
  nothing.

Where the root is not the top of a git work tree — a clean room built by
``beadloom clean-room`` (no ``.git``) or mutmut's ``mutants/`` copy (inside this
checkout and ignored by it) — the tree is walked instead, skipping environments,
caches and index files, and the copy has no history.

Limits, stated
--------------
* The clone's ``origin/*`` refs are this repository's LOCAL branches, not its
  remote-tracking ones.
* Hooks are not copied: ``.git/hooks`` is not part of a clone.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

#: Directories a walk never enters: environments, caches and build output, which
#: git ignores in a checkout and which a room or a mutmut copy may still hold.
_WALK_SKIPPED_DIRS = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        ".tox",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "node_modules",
        "htmlcov",
        "mutants",
    }
)

#: An index file is never copied: the snapshot builds its own.
_INDEX_SUFFIXES = (".db", ".db-wal", ".db-shm", ".db-journal")
_INDEX_DIR = ".beadloom"


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[bytes] | None:
    """Run git in *root* with no inherited ``GIT_*`` redirection; ``None`` if it cannot run.

    A hook exports ``GIT_DIR`` / ``GIT_INDEX_FILE``, which would point every call
    here at the repository that ran the hook instead of at *root*.
    """
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    try:
        return subprocess.run(  # noqa: S603
            ["git", *args],  # noqa: S607
            cwd=root,
            capture_output=True,
            check=False,
            env=env,
        )
    except OSError:
        return None


def _is_work_tree_top(root: Path) -> bool:
    result = _git(root, "rev-parse", "--show-toplevel")
    if result is None or result.returncode != 0:
        return False
    top = result.stdout.decode("utf-8", "surrogateescape").strip()
    return Path(top).resolve() == root.resolve()


def _is_index_file(rel: str) -> bool:
    return rel.split("/", 1)[0] == _INDEX_DIR and rel.endswith(_INDEX_SUFFIXES)


def _listed_by_git(root: Path) -> list[str]:
    result = _git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    if result is None or result.returncode != 0:
        return []
    names = result.stdout.decode("utf-8", "surrogateescape").split("\0")
    # `--cached` names an unmerged path once per stage, so the order-keeping dedup.
    return list(dict.fromkeys(name for name in names if name))


def _walked(root: Path) -> list[str]:
    found: list[str] = []
    for current, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in _WALK_SKIPPED_DIRS)
        base = Path(current).relative_to(root)
        found.extend((base / name).as_posix() for name in sorted(files))
    return found


def working_tree_files(root: Path) -> list[str]:
    """The root-relative files a snapshot of *root* copies, in a stable order."""
    listed = _listed_by_git(root) if _is_work_tree_top(root) else _walked(root)
    return [
        rel
        for rel in listed
        if not _is_index_file(rel) and ((root / rel).is_file() or (root / rel).is_symlink())
    ]


def build_snapshot(root: Path, dest: Path) -> list[str]:
    """Copy *root*'s working tree into *dest* (which must not exist); return what was copied."""
    with_history = _is_work_tree_top(root)
    if with_history:
        cloned = _git(
            root.parent, "clone", "--quiet", "--shared", "--no-checkout", str(root), str(dest)
        )
        if cloned is None or cloned.returncode != 0:
            detail = b"" if cloned is None else cloned.stderr
            msg = f"could not clone {root} into {dest}: {detail.decode('utf-8', 'replace')}"
            raise RuntimeError(msg)
    else:
        dest.mkdir(parents=True)
    files = working_tree_files(root)
    for rel in files:
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / rel, target, follow_symlinks=False)
    if with_history:
        # `--no-checkout` leaves the clone's git index empty; filling it from HEAD
        # is what makes git read the copied tree as edits against HEAD.
        _git(dest, "reset", "--quiet")
    return files

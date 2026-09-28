"""Where this repository's root is — found one way, from any depth.

A test that counts its own parents (``Path(__file__).resolve().parents[3]``)
names the root correctly only at the depth it was written at, and a file moved
one folder deeper reads the wrong directory without failing. This module walks
up from its own location to the nearest ``pyproject.toml`` instead.

"Nearest" is the property that keeps it right in all three rooms the suite runs
in: the checkout; a clean room, which is a copy with no ``.git`` (so a git
lookup would find nothing); and mutmut's ``mutants/`` copy, which sits INSIDE
the checkout and carries its own ``pyproject.toml``, so the root found there is
the copy — the same answer ``parents[N]`` gave, because the tests run from the
copy too.

The search starts from this file and never from the working directory: every
test runs in an empty directory (``tests/conftest.py``).

One arrangement has no root, and importing this module there raises:
``tests/integration/graph/scenarios/test_bead14_s4_binding.py`` copies ``tests/acceptance/`` (with
this package beside it) into a temporary directory and runs it. So what the
acceptance tree imports reads this project's files through
:data:`tests.support.package_under_test.SHIPPED_FROM`, the checkout the package
under test ships from, and never through this module.
"""

from __future__ import annotations

from pathlib import Path

#: The file whose directory is the repository root.
MANIFEST = "pyproject.toml"


class RepositoryRootNotFoundError(LookupError):
    """No directory above a path holds the manifest."""


def repository_root(start: Path, *, stop_at: Path | None = None) -> Path:
    """The nearest directory at or above *start* that holds ``pyproject.toml``.

    *stop_at* bounds the walk (inclusive), so a caller can ask about a tree it
    built without the answer escaping into whatever lies above it.
    """
    start = start.resolve()
    bound = stop_at.resolve() if stop_at is not None else None
    for candidate in (start, *start.parents):
        if (candidate / MANIFEST).is_file():
            return candidate
        if candidate == bound:
            break
    raise RepositoryRootNotFoundError(f"no {MANIFEST} at or above {start}")


#: This repository's root: the checkout, a clean room, or mutmut's copy.
REPO_ROOT: Path = repository_root(Path(__file__))

#: The suite's own root, under the repository root.
TESTS_ROOT: Path = REPO_ROOT / "tests"

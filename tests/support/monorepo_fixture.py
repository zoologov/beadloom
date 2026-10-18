"""The monorepo fixture, copied out of this repository and committed as an adopter's checkout.

BDL-083 S1g (``beadloom-483w``). The first outside adopter's layout, anonymised: a Python
backend under ``backend/`` with its own ``pyproject.toml`` and ``uv.lock``, a Feature-Sliced
frontend under ``frontend/`` with spec files beside the code, a GitLab pipeline, and the
``.beadloom/`` the adopter wrote after ``init``. It is the surface the S1 to S4 beads of
BDL-083 measure on, so every one of them gets it the same way: from :func:`monorepo_checkout`.

A fixture file named like one of this repository's tests is stored under
:data:`~tests.support.adopter_portals.STORED_SUFFIX` and takes its name back on copy, as the
portal fixtures do.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

from tests.support.adopter_portals import STORED_SUFFIX
from tests.support.committed_project import commit_project
from tests.support.repository_root import TESTS_ROOT

if TYPE_CHECKING:
    from pathlib import Path

#: Where the fixture lives in this repository.
MONOREPO = TESTS_ROOT / "fixtures" / "monorepo"

#: The checkout's directory name: the root service's ``ref_id``, as an adopter's clone is named.
CHECKOUT_NAME = "metrics-desk"


def monorepo_checkout(workdir: Path) -> Path:
    """Copy the monorepo fixture under *workdir*, commit it, and return the checkout's root.

    The stored file names are restored first, so the commit holds the names the adopter's
    stacks use, and the root is the git root, as it is in the adopter's repository.
    """
    root = workdir / CHECKOUT_NAME
    shutil.copytree(MONOREPO, root)
    for stored in sorted(root.rglob(f"*{STORED_SUFFIX}")):
        stored.rename(stored.with_name(stored.name.removesuffix(STORED_SUFFIX)))
    commit_project(root)
    return root

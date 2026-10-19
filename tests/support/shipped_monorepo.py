"""The monorepo fixture's checkout, taken in a way a copied acceptance suite can still take it.

BDL-083 S2f (``beadloom-27br``). :func:`tests.support.monorepo_fixture.monorepo_checkout` is
the checkout every BDL-083 slice measures on, and its module finds this repository's root
when it is imported, through ``repository_root`` and ``adopter_portals``. The acceptance
suite is also run copied away from the repository
(``tests/integration/graph/scenarios/test_bead14_s4_binding.py``), where there is no root to
find, so a step module that imports it fails to collect there. This module builds the same
checkout from :data:`~tests.support.package_under_test.SHIPPED_FROM`, the checkout the
package under test ships from, which both arrangements have.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

from tests.support.committed_project import commit_project
from tests.support.package_under_test import SHIPPED_FROM

if TYPE_CHECKING:
    from pathlib import Path

#: The suffix a fixture file named like one of this repository's tests is stored under:
#: ``tests.support.adopter_portals.STORED_SUFFIX``, spelled again because that module finds
#: this repository's root when it is imported.
_STORED_SUFFIX = ".fixture"

#: The checkout's directory name, as :data:`tests.support.monorepo_fixture.CHECKOUT_NAME`.
_CHECKOUT_NAME = "metrics-desk"


def shipped_monorepo_checkout(workdir: Path) -> Path:
    """Copy the monorepo fixture under *workdir*, commit it, and return the checkout's root."""
    root = workdir / _CHECKOUT_NAME
    shutil.copytree(SHIPPED_FROM / "tests" / "fixtures" / "monorepo", root)
    for stored in sorted(root.rglob(f"*{_STORED_SUFFIX}")):
        stored.rename(stored.with_name(stored.name.removesuffix(_STORED_SUFFIX)))
    commit_project(root)
    return root


#: The folder of the git repository the fixture is placed in by
#: :func:`shipped_monorepo_below_its_git_root`: the repository's root, one level above the project.
_REPOSITORY_NAME = "monorepo"


def shipped_monorepo_below_its_git_root(workdir: Path) -> Path:
    """Copy the monorepo fixture one folder below a git root, commit it there, return the project.

    BDL-083 S2e (``beadloom-7pd6``), BDL-UX #325: the layout Beadloom refuses by name. The
    project's ``.beadloom/`` sits in ``<workdir>/monorepo/metrics-desk`` and the repository's
    ``.git`` in ``<workdir>/monorepo``, so git answers in paths relative to a root the project
    does not stand at.
    """
    repository = workdir / _REPOSITORY_NAME
    root = repository / _CHECKOUT_NAME
    shutil.copytree(SHIPPED_FROM / "tests" / "fixtures" / "monorepo", root)
    for stored in sorted(root.rglob(f"*{_STORED_SUFFIX}")):
        stored.rename(stored.with_name(stored.name.removesuffix(_STORED_SUFFIX)))
    commit_project(repository)
    return root

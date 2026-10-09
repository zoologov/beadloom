"""An adopter fixture copied, committed and given ``beadloom init --yes``, and nothing else.

BDL-080 S3T (PRD goal 4): "``init`` on the fixture needs no hand edit for ``lint --strict``
to judge its layers". :func:`tests.support.adopter_portals.adopt` declares the portal's
identity and reindexes after ``init``, which is what an adopter building a portal does;
this is the shorter path, where the next command after ``init`` is the one under test.
"""

from __future__ import annotations

import shutil
import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from click.testing import CliRunner

from beadloom.services.cli import main
from tests.support.adopter_portals import FIXTURES_BY_STACK, STORED_SUFFIX
from tests.support.committed_project import commit_project

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class InitialisedFixture:
    """A fixture's copy at *root* after ``init``: its exit code and its output."""

    stack: str
    root: Path
    init_exit: int
    init_output: str

    def query(self, sql: str) -> list[tuple[Any, ...]]:
        """The rows *sql* selects from the index ``init`` wrote."""
        with sqlite3.connect(self.root / ".beadloom" / "beadloom.db") as conn:
            return list(conn.execute(sql))

    def sources(self) -> dict[str, str]:
        """Each node's source folder, without its trailing slash, by ref_id."""
        return {
            ref: (source or "").rstrip("/")
            for ref, source in self.query("SELECT ref_id, source FROM nodes")
        }


def initialise_fixture(stack: str, workdir: Path) -> InitialisedFixture:
    """Copy the fixture of *stack* under *workdir*, commit it and run ``init --yes`` on it.

    The copy is named after the fixture's project, as an adopter's checkout is, and the
    project is passed as an absolute path.
    """
    fixture = FIXTURES_BY_STACK[stack]
    root = workdir / fixture.project
    shutil.copytree(fixture.source, root)
    for stored in sorted(root.rglob(f"*{STORED_SUFFIX}")):
        stored.rename(stored.with_name(stored.name.removesuffix(STORED_SUFFIX)))
    commit_project(root, origin=fixture.origin)
    result = CliRunner().invoke(main, ["init", "--yes", "--project", str(root.resolve())])
    return InitialisedFixture(stack, root, result.exit_code, result.output)

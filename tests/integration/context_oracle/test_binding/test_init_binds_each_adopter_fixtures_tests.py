"""After ``init``, each adopter fixture's tests bind to the node they test (``beadloom-76mk``).

Observed by BDL-076 ``beadloom-ujzb.17`` on the Python fixture: its tests sit
directly under ``tests/`` and bound to no node. They now bind by the module each
names. The other five fixtures bind by the mirror of a build tool's test tree or
beside the code, and those bindings are stated here as they were before the
change, so a change to any of them is a failure of this file.

Each expectation is written from the fixture's files, independently of the
product: the source directory of the node a test file is expected to bind to.
Only ``init --yes`` runs — no git, no portal build — because the binding is what
is under test.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

import pytest
import yaml
from click.testing import CliRunner

from beadloom.infrastructure.db import open_db
from beadloom.services.cli import main
from tests.support.adopter_portals import FIXTURES_BY_STACK, STORED_SUFFIX

if TYPE_CHECKING:
    from pathlib import Path

_LEDGER = "src/main/java/org/example/ledger"
_ORCHARD = "src/main/kotlin/org/example/orchard"

#: Each stack's test files, and the source directory of the node each binds to.
EXPECTED: dict[str, dict[str, str]] = {
    "python": {
        "tests/test_invoice.py": "src/parceldesk/billing",
        "tests/test_routes.py": "src/parceldesk/api",
    },
    "go": {"internal/catalog/catalog_test.go": "internal/catalog"},
    "typescript": {
        "src/accounts/session/session.test.ts": "src/accounts/session",
        "src/notes/model/note.test.ts": "src/notes/model",
    },
    "java": {
        "src/test/java/org/example/ledger/service/LedgerServiceTest.java": f"{_LEDGER}/service",
    },
    "kotlin": {
        "src/test/kotlin/org/example/orchard/planner/RoutePlannerTest.kt": f"{_ORCHARD}/planner",
    },
    "swift": {"Tests/BeaconCoreTests/ReadingTests.swift": "Sources/BeaconCore"},
}


def _initialised(stack: str, workdir: Path) -> tuple[Path, str]:
    """A copy of *stack*'s fixture with its stored names restored, after ``init --yes``."""
    root = workdir / stack
    shutil.copytree(FIXTURES_BY_STACK[stack].source, root)
    for stored in sorted(root.rglob(f"*{STORED_SUFFIX}")):
        stored.rename(stored.with_name(stored.name.removesuffix(STORED_SUFFIX)))
    result = CliRunner().invoke(main, ["init", "--yes", "--project", str(root)])
    assert result.exit_code == 0, result.output
    return root, result.output


def _sources(root: Path) -> dict[str, str]:
    """Each node's ref_id and its source directory, read from the graph files init wrote."""
    found: dict[str, str] = {}
    for graph_file in sorted((root / ".beadloom" / "_graph").glob("*.yml")):
        loaded = yaml.safe_load(graph_file.read_text(encoding="utf-8")) or {}
        for node in loaded.get("nodes") or []:
            found[str(node["ref_id"])] = str(node.get("source") or "").rstrip("/")
    return found


def _bound(root: Path) -> dict[str, str | None]:
    """Each indexed test file and the source directory of the node it binds to."""
    sources = _sources(root)
    conn = open_db(root / ".beadloom" / "beadloom.db")
    try:
        rows = conn.execute("SELECT path, ref_id FROM test_files ORDER BY path").fetchall()
    finally:
        conn.close()
    return {str(path): None if ref is None else sources[str(ref)] for path, ref in rows}


@pytest.mark.parametrize("stack", sorted(EXPECTED))
def test_each_test_file_binds_to_the_node_it_tests(stack: str, tmp_path: Path) -> None:
    root, _ = _initialised(stack, tmp_path)
    assert _bound(root) == EXPECTED[stack]


@pytest.mark.parametrize("stack", sorted(EXPECTED))
def test_init_names_no_test_file_as_unbound(stack: str, tmp_path: Path) -> None:
    _, output = _initialised(stack, tmp_path)
    assert "bound to no node" not in output, output

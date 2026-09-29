"""The context bundle states the unplaced sentence against the layout the index recorded.

BDL-074 G2: a project that declares ``test/`` as its test root is told its files
are not under ``test/unit/`` or ``test/integration/`` — not the default folders it
does not have. The sentence is stated by the builder, where the index is open.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.reindex import reindex
from beadloom.context_oracle.builder import build_context
from beadloom.infrastructure.db import open_db
from tests.support.adopter_test_layouts import jest_project, python_with_a_test_root

if TYPE_CHECKING:
    from pathlib import Path


def _bundle(root: Path) -> dict[str, object]:
    reindex(root)
    conn = open_db(root / ".beadloom" / "beadloom.db")
    try:
        return build_context(conn, ["billing"], depth=0, max_nodes=5, max_chunks=5)
    finally:
        conn.close()


class TestTheUnplacedSentence:
    def test_names_the_declared_root_and_tests_beside_the_code(self, tmp_path: Path) -> None:
        bundle = _bundle(python_with_a_test_root(tmp_path, mirrored=False))
        assert bundle["test_unplaced"] == (
            "2 of 2 test file(s) are unplaced (not under test/integration/ or test/unit/, "
            "nor inside a node's source) and bind to no node"
        )

    def test_is_none_when_every_file_is_placed(self, tmp_path: Path) -> None:
        assert _bundle(python_with_a_test_root(tmp_path, mirrored=True))["test_unplaced"] is None


class TestWhichFilesCountAsTests:
    """``beadloom-2mj3.15``: the bundle says what a test file is read by, every time."""

    def test_stated_when_every_file_is_placed(self, tmp_path: Path) -> None:
        bundle = _bundle(python_with_a_test_root(tmp_path, mirrored=True))
        assert str(bundle["test_recognition"]).startswith(
            "a test file is read when its path matches a pattern of go_test (*_test.go), "
        )
        assert str(bundle["test_recognition"]).endswith(
            "under the root test or beside a node's code"
        )

    def test_names_the_jest_folder_convention_it_reads(self, tmp_path: Path) -> None:
        bundle = _bundle(jest_project(tmp_path, "src/{p}/__tests__/{p}.ts"))
        assert "__tests__/**/*.[jt]s" in str(bundle["test_recognition"])

"""On every claimed stack's fixture an incremental reindex resolves imports as a fresh one does.

Two causes of an index whose imports depended on how it was built were fixed on synthetic
projects: an import was resolved against the previous run's file list, and an importer that
did not change was never resolved again when its target vanished; and a manifest
(``go.mod``, ``go.work``, ``Package.swift``) that changed alone re-resolved nothing. The
cases here hold the same property on the six adopter fixtures, as an adopter's project is
laid out: after ``init``, the tree is edited and indexed incrementally, and every row of
``code_imports`` and every ``depends_on`` edge is compared with a fresh index of a copy of
the edited tree.

Each edit is chosen so that it changes what an untouched file's import resolves to:

* every stack loses the module another one imports, while the importer stays as it is;
* on Go and Swift, only the manifest changes: the module path in ``go.mod``, or the path of
  a target in ``Package.swift``.
"""

from __future__ import annotations

import shutil
import sqlite3
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from beadloom.services.cli import main
from tests.support.adopter_portals import FIXTURES_BY_STACK, STORED_SUFFIX

if TYPE_CHECKING:
    from pathlib import Path

#: The manifest edit per stack that has a manifest: the file, its text before and after.
_MANIFEST_EDITS: dict[str, tuple[str, str, str]] = {
    "go": ("go.mod", "module example.org/tidewater", "module example.org/riptide"),
    "swift": (
        "Package.swift",
        '.target(name: "BeaconCore")',
        '.target(name: "BeaconCore", path: "Sources/BeaconReadings")',
    ),
}

#: Index files, which a copy for a fresh index leaves behind.
_INDEX_FILES = ("beadloom.db", "beadloom.db-wal", "beadloom.db-shm", "beadloom.db-journal")


def _beadloom(root: Path, *args: str) -> None:
    result = CliRunner().invoke(main, [*args, "--project", str(root)])
    assert result.exit_code == 0, result.output


def _initialised(stack: str, workdir: Path) -> Path:
    """A copy of *stack*'s fixture with its stored names restored, indexed by ``init --yes``."""
    root = workdir / stack
    shutil.copytree(FIXTURES_BY_STACK[stack].source, root)
    for stored in sorted(root.rglob(f"*{STORED_SUFFIX}")):
        stored.rename(stored.with_name(stored.name.removesuffix(STORED_SUFFIX)))
    _beadloom(root, "init", "--yes")
    return root


def _resolved(root: Path) -> tuple[list[tuple[object, ...]], list[tuple[object, ...]]]:
    """Every stored import with what it resolved to, and every ``depends_on`` edge, sorted."""
    with sqlite3.connect(root / ".beadloom" / "beadloom.db") as conn:
        imports = conn.execute(
            "SELECT file_path, line_number, import_path, resolved_ref_id FROM code_imports"
        ).fetchall()
        edges = conn.execute(
            "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'depends_on'"
        ).fetchall()
    return sorted(imports, key=repr), sorted(edges, key=repr)


def _fresh_copy(root: Path, workdir: Path) -> Path:
    """A copy of *root* without its index, indexed from nothing."""
    fresh = workdir / f"{root.name}-fresh"
    shutil.copytree(root, fresh, ignore=shutil.ignore_patterns(*_INDEX_FILES))
    _beadloom(fresh, "reindex", "--full")
    return fresh


@pytest.mark.parametrize("stack", list(FIXTURES_BY_STACK))
def test_an_importer_left_as_it_was_resolves_as_a_fresh_index_does_once_its_target_is_gone(
    stack: str, tmp_path: Path
) -> None:
    root = _initialised(stack, tmp_path)
    _importer, imported = FIXTURES_BY_STACK[stack].imports[0]
    shutil.rmtree(root / imported)

    _beadloom(root, "reindex")

    assert _resolved(root) == _resolved(_fresh_copy(root, tmp_path))


@pytest.mark.parametrize("stack", list(_MANIFEST_EDITS))
def test_a_manifest_changed_alone_resolves_every_import_as_a_fresh_index_does(
    stack: str, tmp_path: Path
) -> None:
    root = _initialised(stack, tmp_path)
    name, before, after = _MANIFEST_EDITS[stack]
    manifest = root / name
    text = manifest.read_text(encoding="utf-8")
    if before not in text:
        raise LookupError(f"{name} of the {stack} fixture no longer holds {before!r}")
    manifest.write_text(text.replace(before, after), encoding="utf-8")

    _beadloom(root, "reindex")

    assert _resolved(root) == _resolved(_fresh_copy(root, tmp_path))

"""A tsconfig and the ``imports.aliases:`` block are inputs of every JS/TS import they map.

BDL-080 S3a (``beadloom-cwzc``). Neither is a source file, so an incremental reindex that
re-read only the source files that changed would keep an aliased import's old answer after
either was edited (the class ``beadloom-jcng`` closed for ``go.mod`` and
``Package.swift``). The scenarios of ``an_aliased_or_platform_import_names_its_file``
hold the answers against a fresh index; these cases hold the cost side: a run where
nothing changed is still ``nothing_changed``, and a project with no JavaScript import
never reads a tsconfig.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.application.reindex import incremental_reindex, reindex
from beadloom.graph.import_manifests import manifests_changed
from beadloom.infrastructure.db import open_db

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

pytest.importorskip("tree_sitter_typescript")


def _project(root: Path, config: str, files: dict[str, str]) -> Path:
    graph = root / ".beadloom" / "_graph"
    graph.mkdir(parents=True)
    (graph / "graph.yml").write_text(
        "nodes:\n"
        "  - ref_id: web\n    kind: service\n    summary: The app.\n    source: ''\n"
        "  - ref_id: ui\n    kind: component\n    summary: The ui.\n    source: src/ui/\n"
        "edges:\n  - src: ui\n    dst: web\n    kind: part_of\n",
        encoding="utf-8",
    )
    (root / ".beadloom" / "config.yml").write_text(config, encoding="utf-8")
    for rel_path, text in files.items():
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


_TSCONFIG = '{ "compilerOptions": { "paths": { "@/*": ["./src/*"] } } }\n'
_SCRIPT = {
    "tsconfig.json": _TSCONFIG,
    "src/app/main.ts": "import { b } from '@/ui/button';\nimport { c } from '#ui/card';\n",
    "src/ui/button.ts": "export const b = 1;\n",
    "src/ui/card.ts": "export const c = 1;\n",
}
_ALIASES = "scan_paths:\n- src\nimports:\n  aliases:\n    '#ui': src/ui\n"


def test_a_script_project_where_nothing_changed_is_nothing_changed(tmp_path: Path) -> None:
    root = _project(tmp_path / "web", _ALIASES, _SCRIPT)
    reindex(root)
    assert incremental_reindex(root).nothing_changed is True


def test_a_tsconfig_edited_alone_is_a_change(tmp_path: Path) -> None:
    root = _project(tmp_path / "web", _ALIASES, _SCRIPT)
    reindex(root)
    (root / "tsconfig.json").write_text(_TSCONFIG.replace("./src/*", "./lib/*"), "utf-8")
    assert incremental_reindex(root).nothing_changed is False


def test_the_aliases_edited_alone_are_a_change(tmp_path: Path) -> None:
    root = _project(tmp_path / "web", _ALIASES, _SCRIPT)
    reindex(root)
    (root / ".beadloom" / "config.yml").write_text(_ALIASES.replace("src/ui", "src"), "utf-8")
    assert incremental_reindex(root).nothing_changed is False


def test_a_project_with_no_script_import_reads_no_tsconfig(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _project(
        tmp_path / "py",
        "scan_paths:\n- src\n",
        {"tsconfig.json": _TSCONFIG, "src/ui/a.py": "import os\n"},
    )
    reindex(root)

    def _walked(*_args: object) -> None:
        raise AssertionError("a project with no JavaScript import read its tsconfig")

    monkeypatch.setattr("beadloom.graph.import_manifests.TsConfigs", _walked)
    assert incremental_reindex(root).nothing_changed is True


def test_the_readers_share_one_walk_of_the_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # BDL-080 S3f (beadloom-af99.14), the S3 review's minor 5: the tsconfig reader and the
    # Expo module reader each walked the project, so a run of a project with JavaScript
    # imports listed its root twice before deciding nothing had changed.
    root = _project(tmp_path / "web", _ALIASES, _SCRIPT)
    reindex(root)
    conn = open_db(root / ".beadloom" / "beadloom.db")
    listed: list[Path] = []
    original = type(root).iterdir

    def _counting(self: Path) -> Iterator[Path]:  # a spy on the walk
        listed.append(self)
        return original(self)

    monkeypatch.setattr(type(root), "iterdir", _counting)
    try:
        manifests_changed(root, conn, aliases=(("#ui", "src/ui"),))
    finally:
        conn.close()

    assert listed.count(root) == 1

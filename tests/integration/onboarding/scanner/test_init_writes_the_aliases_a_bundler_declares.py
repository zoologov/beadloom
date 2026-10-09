"""``init`` writes the aliases ``babel.config.js`` / ``vite.config.*`` declare, and says so.

BDL-080 S3a (``beadloom-cwzc``), RFC D5 (b). The scan is a text scan, not an evaluation,
so ``init`` writes what it found under ``imports.aliases:`` and prints where it came from
for the user to confirm. A project without either file gets the config it got before.
The project is an Expo-like app whose name and files are invented.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("tree_sitter_typescript")

_BABEL = """\
module.exports = function (api) {
  return {
    plugins: [['module-resolver', { alias: { '@shared': './src/shared', '^re/(.+)': '\\\\1' } }]],
  };
};
"""

_FILES = {
    "package.json": '{"name": "harbourline", "main": "expo-router/entry"}\n',
    "babel.config.js": _BABEL,
    "src/shared/api/index.ts": "export const api = 1;\n",
    "src/entities/boat/model.ts": "import { api } from '@shared/api';\nexport const boat = api;\n",
}


def _project(root: Path, files: dict[str, str]) -> Path:
    for rel_path, text in files.items():
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def _config(root: Path) -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(
        (root / ".beadloom" / "config.yml").read_text(encoding="utf-8")
    )
    return loaded


def _init(root: Path) -> str:
    result = CliRunner().invoke(main, ["init", "--yes", "--project", str(root)])
    assert result.exit_code == 0, result.output
    return result.output


def test_init_writes_the_aliases_it_read_and_says_it_read_them_as_text(tmp_path: Path) -> None:
    root = _project(tmp_path, _FILES)
    output = _init(root)
    assert _config(root)["imports"] == {"aliases": {"@shared": "src/shared"}}
    assert "Import aliases: 1 read from babel.config.js by a text scan" in output
    assert "@shared -> src/shared" in output
    assert "not written: ^re/(.+) (a regular expression)" in output


def test_the_written_alias_resolves_the_import_init_indexed(tmp_path: Path) -> None:
    root = _project(tmp_path, _FILES)
    _init(root)
    with sqlite3.connect(root / ".beadloom" / "beadloom.db") as conn:
        row = conn.execute(
            "SELECT resolved_ref_id FROM code_imports WHERE import_path = '@shared/api'"
        ).fetchone()
    assert row is not None
    assert row[0] is not None


def test_a_project_with_no_bundler_config_gets_no_imports_block_and_no_line(
    tmp_path: Path,
) -> None:
    files = {k: v for k, v in _FILES.items() if k != "babel.config.js"}
    root = _project(tmp_path, files)
    output = _init(root)
    assert "imports" not in _config(root)
    assert "Import aliases" not in output

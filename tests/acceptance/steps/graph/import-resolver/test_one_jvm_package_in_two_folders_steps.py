"""Step implementations for `graph/import-resolver/one_jvm_package_in_two_folders.feature`.

BDL-076, the re-review's finding m5, fixed by ``beadloom-ujzb.24``. The real ``beadloom
init --yes`` and ``beadloom reindex`` run through the CLI on a Kotlin project written to
disk, in which two folders declare one package. What init writes is read from its YAML,
what reindex resolved from the index.

**FAKES PROVE FAKES.** The imported class lives in the folder read SECOND, so the edge
the old reading drew (to the folder read first) and the correct one differ.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("tree_sitter_kotlin")

scenarios("../../../graph/import-resolver/one_jvm_package_in_two_folders.feature")


@pytest.fixture
def state() -> dict[str, Any]:
    return {}


@given(
    parsers.parse(
        'a Kotlin project where "src/main/kotlin/a" and "src/main/kotlin/b" both declare '
        '"org.ex.shared" and "c" imports "{import_path}"'
    )
)
def _project(tmp_path: Path, state: dict[str, Any], import_path: str) -> None:
    root = tmp_path / "ktsplit"
    used = "B" if import_path.endswith(".B") else "Any"
    files = {
        "build.gradle.kts": "\n",
        "src/main/kotlin/a/A.kt": "package org.ex.shared\n\nclass A\n",
        "src/main/kotlin/b/B.kt": "package org.ex.shared\n\nclass B\n",
        "src/main/kotlin/c/C.kt": (
            f"package org.ex.c\n\nimport {import_path}\n\nclass C(val b: {used})\n"
        ),
    }
    for rel_path, text in files.items():
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    state["root"] = root


def _run(state: dict[str, Any], *args: str) -> None:
    result = CliRunner().invoke(main, [*args, "--project", str(state["root"])])
    assert result.exit_code == 0, result.output


@when("beadloom init is run without prompts")
def _init(state: dict[str, Any]) -> None:
    _run(state, "init", "--yes")


@when("beadloom reindex is run")
def _reindex(state: dict[str, Any]) -> None:
    _run(state, "reindex")


def _pairs(text: str) -> set[tuple[str, str]]:
    items = {part.strip().strip('"') for part in text.split(",")}
    return {(src, dst) for src, dst in (item.split(" -> ") for item in items)}


def _init_edges(root: Path) -> set[tuple[str, str]]:
    edges: set[tuple[str, str]] = set()
    for path in sorted((root / ".beadloom" / "_graph").glob("*.yml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        edges |= {
            (str(edge["src"]), str(edge["dst"]))
            for edge in data.get("edges") or []
            if edge.get("kind") == "depends_on"
        }
    return edges


def _query(root: Path, sql: str, *params: str) -> list[tuple[Any, ...]]:
    with sqlite3.connect(root / ".beadloom" / "beadloom.db") as conn:
        return [tuple(row) for row in conn.execute(sql, params).fetchall()]


@then(parsers.parse("the graph init writes has exactly the depends_on edges {edges}"))
def _init_has(state: dict[str, Any], edges: str) -> None:
    assert _init_edges(state["root"]) == _pairs(edges)


@then("the graph init writes has no depends_on edge")
def _init_has_none(state: dict[str, Any]) -> None:
    assert _init_edges(state["root"]) == set()


@then(parsers.parse("the index holds exactly the depends_on edges {edges}"))
def _index_has(state: dict[str, Any], edges: str) -> None:
    rows = _query(
        state["root"], "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'depends_on'"
    )
    assert {(str(src), str(dst)) for src, dst in rows} == _pairs(edges)


def _resolved(state: dict[str, Any], import_path: str, path: str) -> list[tuple[Any, ...]]:
    return _query(
        state["root"],
        "SELECT resolved_ref_id FROM code_imports WHERE file_path = ? AND import_path = ?",
        path,
        import_path,
    )


@then(parsers.parse('the import "{import_path}" of "{path}" is resolved to "{ref_id}"'))
def _resolved_to(state: dict[str, Any], import_path: str, path: str, ref_id: str) -> None:
    assert _resolved(state, import_path, path) == [(ref_id,)]


@then(parsers.parse('the import "{import_path}" of "{path}" is not resolved'))
def _not_resolved(state: dict[str, Any], import_path: str, path: str) -> None:
    assert _resolved(state, import_path, path) == [(None,)]

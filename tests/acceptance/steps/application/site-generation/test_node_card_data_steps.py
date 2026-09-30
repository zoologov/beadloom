"""Step implementations for `application/site-generation/node_card_data.feature`.

BDL-076 A1 (`beadloom-o2ua`). Against a real project directory, the real
reindex, the real linter and the real site generator: the project is written on
disk, indexed once, and the site is generated from it with `generate_site`, the
node's source. The scenario reads `public/architecture.data.json`, the artifact
`docs site` publishes, because that file is the whole of what the viewer sees.

The module is named ``test_*`` so default pytest collection picks the scenarios
up — the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.site.generate import generate_site
from tests.support.tiered_project import ZONED_POOL_TESTS, write_zoned_import_project

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../application/site-generation/node_card_data.feature")

#: The site's published copy of the architecture view, under the site root.
_VIEW_DATA = "public/architecture.data.json"

#: A fixed instant for the one wall-clock read `generate_site` makes.
_NOW = "2026-09-30T00:00:00+00:00"


def _split(listing: str) -> list[str]:
    return [item.strip() for item in listing.split(",")]


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    return {"root": tmp_path / "shop", "site": tmp_path / "site"}


@given(
    "a project whose storage pool imports the catalogue above it, "
    "with tests bound to the pool"
)
def _zoned_project(world: dict[str, Any]) -> None:
    world["project"] = write_zoned_import_project(world["root"], tests=ZONED_POOL_TESTS)


@when("the site is generated for the project")
def _generate(world: dict[str, Any]) -> None:
    project = world["project"]
    conn = sqlite3.connect(project / ".beadloom" / "beadloom.db")
    conn.row_factory = sqlite3.Row
    try:
        generate_site(conn, world["site"], project_root=project, now_ts=_NOW)
    finally:
        conn.close()
    data = json.loads((world["site"] / _VIEW_DATA).read_text(encoding="utf-8"))
    world["data"] = data
    world["nodes"] = {str(node["id"]): node for node in data["nodes"]}


@then(parsers.parse("the data file declares schema version {version:d}"))
def _schema_version(world: dict[str, Any], version: int) -> None:
    assert world["data"]["schema_version"] == version


@then(parsers.parse('the node "{ref}" links to its page "{url}"'))
def _page_url(world: dict[str, Any], ref: str, url: str) -> None:
    assert world["nodes"][ref]["url"] == url
    assert (world["site"] / f"{url.lstrip('/')}.md").is_file(), "the url names no page"


@then(
    parsers.parse(
        'the node "{ref}" is held by {files:d} test files with {tests:d} tests, '
        'all placed "{placement}"'
    )
)
def _bound_tests(
    world: dict[str, Any], ref: str, files: int, tests: int, placement: str
) -> None:
    bound = world["nodes"][ref]["tests"]
    assert bound["files"] == sorted(ZONED_POOL_TESTS)
    assert len(bound["files"]) == files
    assert bound["count"] == tests
    assert bound["placement"] == {placement: files}


@then(
    parsers.parse(
        'the node "{ref}" carries an "{severity}" finding of the rule "{rule}" naming "{word}"'
    )
)
def _finding(world: dict[str, Any], ref: str, severity: str, rule: str, word: str) -> None:
    findings = world["nodes"][ref]["findings"]
    matching = [f for f in findings if f["rule"] == rule and f["severity"] == severity]
    assert matching, f"no {severity} finding of {rule}: {findings}"
    assert any(word in f["message"] for f in matching), matching


@then(parsers.parse('the node "{ref}" is not lint clean'))
def _not_clean(world: dict[str, Any], ref: str) -> None:
    assert world["nodes"][ref]["lint_clean"] is False


@then(parsers.parse('the data file declares the layers "{names}" in that order'))
def _layer_names(world: dict[str, Any], names: str) -> None:
    layers = world["data"]["layers"]
    assert [layer["name"] for layer in layers] == _split(names)
    assert [layer["rank"] for layer in layers] == list(range(len(layers)))


@then(parsers.parse('the declared layers carry the tags "{tags}"'))
def _layer_tags(world: dict[str, Any], tags: str) -> None:
    assert [layer["tag"] for layer in world["data"]["layers"]] == _split(tags)

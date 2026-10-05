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
import subprocess
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.reindex import reindex
from beadloom.application.site.generate import generate_site
from tests.support.tiered_project import ZONED_POOL_TESTS, write_zoned_import_project

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../application/site-generation/node_card_data.feature")

#: The site's published copy of the architecture view, under the site root.
_VIEW_DATA = "public/architecture.data.json"

#: A fixed instant for the one wall-clock read `generate_site` makes.
_NOW = "2026-09-30T00:00:00+00:00"

#: The one person who commits to the scenario's repository. The name is unusual
#: enough that finding it anywhere in the data file can only mean it leaked.
_AUTHOR = "Ada Quillfeather"
_AUTHOR_EMAIL = "ada@example.invalid"

#: The data files the site publishes, one per screen, under ``public/``.
_DATA_FILES = ("architecture.data.json", "dashboard.data.json", "landscape.data.json")

#: The activity keys the node card shows (BDL-076 R1 finding M2; ``lines_30d`` since
#: BDL-078 F-activity).
_CARD_ACTIVITY_KEYS = {"commits_30d", "lines_30d", "level"}


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


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(  # noqa: S603 - fixed git arguments written by this step
        ["git", *args],  # noqa: S607 - the scenario drives the git on PATH, as the generator does
        cwd=cwd,
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout.strip()


@given(parsers.parse('the project is a git repository whose origin is "{remote}"'))
def _git_repository(world: dict[str, Any], remote: str) -> None:
    project = world["project"]
    _git(project, "init", "-q")
    _git(project, "remote", "add", "origin", remote)
    _git(project, "add", "-A")
    identity = ("-c", f"user.name={_AUTHOR}", "-c", f"user.email={_AUTHOR_EMAIL}")
    _git(project, *identity, "commit", "-q", "-m", "the shop")
    world["ref"] = _git(project, "rev-parse", "HEAD")
    # Reindexed after the commit, so the recorded activity names the author.
    reindex(project)


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
    assert bound["file_count"] == files
    assert bound["count"] == tests
    assert bound["placement"] == {placement: files}


@then(
    parsers.parse(
        'the node "{ref}" lists no test file and counts {files:d} test files with {tests:d} tests'
    )
)
def _counted_not_listed(world: dict[str, Any], ref: str, files: int, tests: int) -> None:
    bound = world["nodes"][ref]["tests"]
    assert bound is not None, f"the binding does not cover {ref}"
    assert bound["files"] == []
    assert bound["file_count"] == files
    assert bound["count"] == tests


@then("every test file of the project is listed at exactly one node")
def _listed_once(world: dict[str, Any]) -> None:
    listed = [
        path
        for node in world["nodes"].values()
        if node["tests"] is not None
        for path in node["tests"]["files"]
    ]
    assert sorted(listed) == sorted(ZONED_POOL_TESTS)


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


@then(parsers.parse('the node "{ref}" links its source to "{link}"'))
def _source_link(world: dict[str, Any], ref: str, link: str) -> None:
    node = world["nodes"][ref]
    expected = link.replace("{ref}", world["ref"])
    assert node["source_url"] == expected
    assert quote(node["source"], safe="/") in node["source_url"]


@then(parsers.parse('the node "{ref}" has no source link'))
def _no_source_link(world: dict[str, Any], ref: str) -> None:
    node = world["nodes"][ref]
    assert node["source"], "the scenario needs a node with a source"
    assert node["source_url"] == ""


def _files_containing(site: Path, needle: str) -> list[str]:
    """Every generated file under *site* that holds *needle*, by its site path.

    Every file is read, not only the architecture view: the site publishes a data
    file per screen and a page per node, and a leak into any of them is published
    (BDL-076 re-review finding m4). The scan states what it covered, so an empty
    answer cannot come from a site that was not generated.
    """
    files = sorted(path for path in site.rglob("*") if path.is_file())
    data_files = {path.name for path in files if path.parent == site / "public"}
    assert set(_DATA_FILES) <= data_files, f"the site wrote {sorted(data_files)}"
    assert any(path.suffix == ".md" for path in files), "the site wrote no page"
    marker = needle.encode("utf-8")
    return [str(path.relative_to(site)) for path in files if marker in path.read_bytes()]


@then("no generated file names the project's commit author")
def _no_author(world: dict[str, Any]) -> None:
    for trace in (_AUTHOR, _AUTHOR_EMAIL):
        assert _files_containing(world["site"], trace) == [], trace


@then(parsers.parse('no generated file contains "{secret}"'))
def _no_secret(world: dict[str, Any], secret: str) -> None:
    assert _files_containing(world["site"], secret) == []


@then(parsers.parse('the node "{ref}" carries only the activity the card shows'))
def _card_activity(world: dict[str, Any], ref: str) -> None:
    activity = world["nodes"][ref]["activity"]
    assert activity is not None, "the reindex recorded no activity for the node"
    assert set(activity) == _CARD_ACTIVITY_KEYS

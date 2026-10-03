"""Step implementations for `application/site-generation/project_links_on_the_portal.feature`.

BDL-076 (`beadloom-ujzb.11`). A small JavaScript project, initialised by the real
`beadloom init`, indexed by the real reindex and given its portal by the real
generator. The scenarios read the pages `docs site` leaves in the output
directory, and check every internal link in them against the files there, as
`vitepress build` does.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.services.cli import main
from tests.support.committed_project import commit_project
from tests.support.site_links import dead_links

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../application/site-generation/project_links_on_the_portal.feature")

#: The project directory; ``init`` names the root service after it.
_PROJECT = "acme"

_MODULE = "src/api/handler.js"


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    root = tmp_path / _PROJECT
    return {"root": root, "site": root / "site", "repo_url": ""}


def _beadloom(*args: str) -> None:
    result = CliRunner().invoke(main, list(args), catch_exceptions=False)
    assert result.exit_code == 0, result.output


def _page(world: dict[str, Any], rel: str) -> str:
    page: Path = world["site"] / rel
    return page.read_text(encoding="utf-8")


def _link_targets(body: str, text: str) -> list[str]:
    return re.findall(rf"\[{re.escape(text)}\]\(([^)]*)\)", body)


@given(parsers.parse('a project whose README opens with "{paragraph}"'))
def _project(world: dict[str, Any], paragraph: str) -> None:
    root: Path = world["root"]
    (root / "src" / "api").mkdir(parents=True)
    (root / "package.json").write_text(
        '{ "name": "acme", "version": "0.1.0", "type": "module" }\n', encoding="utf-8"
    )
    (root / "README.md").write_text(f"# Acme\n\n{paragraph}\n", encoding="utf-8")
    (root / _MODULE).write_text("export function handle() {\n  return 1;\n}\n", encoding="utf-8")


@given(parsers.parse('the project declares the repository "{url}"'))
def _repository(world: dict[str, Any], url: str) -> None:
    world["repo_url"] = url


@given(parsers.parse('the project\'s document "{rel}" links "{first}" and "{second}"'))
def _document(world: dict[str, Any], rel: str, first: str, second: str) -> None:
    doc: Path = world["root"] / rel
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(f"# Guide\n\nSee {first} and {second}.\n", encoding="utf-8")


@given("the project is committed to git")
def _committed(world: dict[str, Any]) -> None:
    # A repository path is linked at the commit the site is generated from
    # (BDL-076 B4, `beadloom-ujzb.8`); a project outside git has none.
    world["ref"] = commit_project(world["root"])


@when("the project is initialised and its site is generated")
def _generate(world: dict[str, Any]) -> None:
    root = str(world["root"])
    _beadloom("init", "--yes", "--project", root)
    if world["repo_url"]:
        config: Path = world["root"] / ".beadloom" / "config.yml"
        block = f"site:\n  repo_url: {world['repo_url']}\n"
        config.write_text(config.read_text(encoding="utf-8") + block, encoding="utf-8")
    _beadloom("reindex", "--project", root)
    _beadloom("docs", "site", "--project", root)


@then(parsers.parse('the root service\'s page reads "{sentence}"'))
def _reads(world: dict[str, Any], sentence: str) -> None:
    body = _page(world, f"services/{_PROJECT}.md")
    assert sentence in body, body


@then(parsers.parse('the root service\'s page links "{text}" to "{url}"'))
def _links(world: dict[str, Any], text: str, url: str) -> None:
    body = _page(world, f"services/{_PROJECT}.md")
    expected = url.replace("{commit}", world.get("ref", ""))
    assert _link_targets(body, text) == [expected], body


@then(parsers.parse('the published guide links "{text}" to "{url}"'))
def _guide_links(world: dict[str, Any], text: str, url: str) -> None:
    body = _page(world, "docs/guide.md")
    assert _link_targets(body, text) == [url], body


@then(parsers.parse('the published guide reads "{text}" as plain text'))
def _guide_text(world: dict[str, Any], text: str) -> None:
    body = _page(world, "docs/guide.md")
    assert f" {text}." in body, body
    assert _link_targets(body, text) == [], body


@then("no page of the portal holds a dead link")
def _no_dead_link(world: dict[str, Any]) -> None:
    assert dead_links(world["site"]) == []

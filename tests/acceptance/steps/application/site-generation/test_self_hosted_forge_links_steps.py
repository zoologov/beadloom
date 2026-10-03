"""Step implementations for `application/site-generation/self_hosted_forge_links.feature`.

BDL-076 B4 (`beadloom-ujzb.8`). A small JavaScript project, committed to git,
initialised by the real `beadloom init`, indexed by the real reindex and given
its portal by the real `docs site`. The scenarios read what `docs site` leaves in
the output directory: the data file the node card reads, the About page and the
module that gives the portal its repository link.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.services.cli import main
from tests.support.committed_project import commit_project

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../application/site-generation/self_hosted_forge_links.feature")

_PROJECT = "orders"
_MODULE = "src/api/handler.js"
_README = "# Orders\n\nTakes orders. See [license](LICENSE).\n\n![the flow](art/flow.png)\n"


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    root = tmp_path / _PROJECT
    return {"root": root, "site": root / "site", "block": "", "ref": ""}


def _beadloom(*args: str) -> Any:
    return CliRunner().invoke(main, list(args), catch_exceptions=False)


def _page(world: dict[str, Any], rel: str) -> str:
    page: Path = world["site"] / rel
    return page.read_text(encoding="utf-8")


def _at_commit(world: dict[str, Any], url: str) -> str:
    return url.replace("{commit}", world["ref"])


@given("a JavaScript service whose README links its licence and draws its flow diagram")
def _project(world: dict[str, Any]) -> None:
    root: Path = world["root"]
    (root / "src" / "api").mkdir(parents=True)
    (root / "art").mkdir()
    (root / "package.json").write_text(
        '{ "name": "orders", "version": "0.1.0", "type": "module" }\n', encoding="utf-8"
    )
    (root / "README.md").write_text(_README, encoding="utf-8")
    (root / "LICENSE").write_text("MIT\n", encoding="utf-8")
    (root / "art" / "flow.png").write_bytes(b"\x89PNG\r\n")
    (root / _MODULE).write_text("export function handle() {\n  return 1;\n}\n", encoding="utf-8")


@given(parsers.parse('the project is committed to git with the origin "{remote}"'))
def _committed(world: dict[str, Any], remote: str) -> None:
    world["ref"] = commit_project(world["root"], origin=remote)


@given(parsers.parse('the project declares its repository "{url}" on the forge "{kind}"'))
def _declared_forge(world: dict[str, Any], url: str, kind: str) -> None:
    host = url.split("/")[2]
    world["block"] = f"site:\n  repo_url: {url}\n  forges:\n    {host}: {kind}\n"


@given(parsers.parse('the project declares its repository "{url}" and no forge'))
def _declared_no_forge(world: dict[str, Any], url: str) -> None:
    world["block"] = f"site:\n  repo_url: {url}\n"


@given(parsers.parse('the project declares the forge "{kind}" for "{host}" and no repository'))
def _declared_forge_only(world: dict[str, Any], kind: str, host: str) -> None:
    world["block"] = f"site:\n  forges:\n    {host}: {kind}\n"


@when("the project is initialised and its site is generated")
def _generate(world: dict[str, Any]) -> None:
    root = str(world["root"])
    init = _beadloom("init", "--yes", "--project", root)
    assert init.exit_code == 0, init.output
    config: Path = world["root"] / ".beadloom" / "config.yml"
    config.write_text(config.read_text(encoding="utf-8") + world["block"], encoding="utf-8")
    reindex = _beadloom("reindex", "--project", root)
    assert reindex.exit_code == 0, reindex.output
    world["result"] = _beadloom("docs", "site", "--project", root)


def _generated(world: dict[str, Any]) -> None:
    result = world["result"]
    assert result.exit_code == 0, result.output


def _sourced_nodes(world: dict[str, Any]) -> list[dict[str, Any]]:
    _generated(world)
    data = json.loads(_page(world, "public/architecture.data.json"))
    nodes = [node for node in data["nodes"] if node.get("source")]
    assert nodes, "the scenario needs a node with a source"
    return nodes


@then(parsers.parse('every node\'s source links to "{template}"'))
def _source_links(world: dict[str, Any], template: str) -> None:
    for node in _sourced_nodes(world):
        source = quote(str(node["source"]).strip("/"), safe="/")
        expected = _at_commit(world, template).replace("<source>", source)
        assert node["source_url"] == expected, node


@then("no node's source has a link")
def _no_source_links(world: dict[str, Any]) -> None:
    assert [node["source_url"] for node in _sourced_nodes(world) if node["source_url"]] == []


@then(parsers.parse('the About page links "{text}" to "{url}"'))
def _about_links(world: dict[str, Any], text: str, url: str) -> None:
    _generated(world)
    body = _page(world, "index.md")
    targets = re.findall(rf"(?<!!)\[{re.escape(text)}\]\(([^)]*)\)", body)
    assert targets == [_at_commit(world, url)], body


@then(parsers.parse('the About page draws "{alt}" from "{url}"'))
def _about_draws(world: dict[str, Any], alt: str, url: str) -> None:
    _generated(world)
    body = _page(world, "index.md")
    sources = re.findall(rf"!\[{re.escape(alt)}\]\(([^)]*)\)", body)
    assert sources == [_at_commit(world, url)], body


@then(parsers.parse('the About page reads "{text}" as plain text'))
def _about_text(world: dict[str, Any], text: str) -> None:
    _generated(world)
    body = _page(world, "index.md")
    assert f"See {text}." in body, body


@then(parsers.parse('the About page reads "{alt}" in place of the image'))
def _about_alt(world: dict[str, Any], alt: str) -> None:
    _generated(world)
    body = _page(world, "index.md")
    assert alt in body, body
    assert f"![{alt}]" not in body, body


@then(parsers.parse('the portal\'s repository link carries the "{icon}" icon'))
def _icon(world: dict[str, Any], icon: str) -> None:
    _generated(world)
    module = _page(world, ".vitepress/site.generated.mjs")
    match = re.search(r"export const site = (\{.*\});", module)
    assert match is not None, module
    assert json.loads(match.group(1))["repoIcon"] == icon


@then(parsers.parse('the site is refused naming "{where}" and "{word}"'))
def _refused(world: dict[str, Any], where: str, word: str) -> None:
    result = world["result"]
    assert result.exit_code != 0, result.output
    assert where in result.output, result.output
    assert word in result.output, result.output
    assert not (world["site"] / "index.md").exists(), "a refused site writes nothing"


@then(parsers.parse('config-check refuses the project naming "{where}"'))
def _config_check(world: dict[str, Any], where: str) -> None:
    result = _beadloom("config-check", "--project", str(world["root"]))
    assert result.exit_code == 1, result.output
    assert where in result.output, result.output

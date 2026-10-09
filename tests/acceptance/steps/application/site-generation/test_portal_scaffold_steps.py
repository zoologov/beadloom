"""Step implementations for `application/site-generation/portal_scaffold.feature`.

BDL-076 B1 (`beadloom-dfwt`). Against a real project directory, the real
reindex and the real generator with the scaffold the installed package ships:
the scenario reads the files `docs site` leaves in the output directory, which is
the whole of what an adopter builds from.
"""

from __future__ import annotations

import json
import re
import sqlite3
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.site.generate import SiteResult, generate_site
from beadloom.application.site.scaffold import read_marker
from beadloom.application.site.site_config import SiteConfigError
from tests.support.adopter_portals import without_the_footer_link
from tests.support.scaffold_node_ids import node_ids_named, scaffold_node_ids
from tests.support.tiered_project import write_zoned_import_project

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../application/site-generation/portal_scaffold.feature")

_NOW = "2026-09-30T00:00:00+00:00"

#: The directory the project is written to; the default title is its name.
_PROJECT_DIR = "acme-orders"

_CONFIG = ".vitepress/config.mjs"
_IDENTITY = ".vitepress/site.generated.mjs"
_STYLESHEET = ".vitepress/theme/widgets/diagram-viewer/ui/diagram-viewer.css"

#: This repository's identity, as the portal used to carry it.
_OUR_IDENTITY = ("zoologov", "/beadloom/", 'title: "Beadloom"')

_OUR_GUIDE = "# The orders team's guide\n"
_OUR_STYLE = ".beadloom-diagram { outline: 2px solid teal; }\n"
_HAND_EDIT = "// the orders team changed this by hand\n"


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    return {"root": tmp_path / _PROJECT_DIR, "site": tmp_path / _PROJECT_DIR / "site"}


def _project(world: dict[str, Any], site_block: str) -> None:
    project = write_zoned_import_project(world["root"])
    config = project / ".beadloom" / "config.yml"
    # The block is read by the generator from the file, so no second reindex.
    config.write_text(config.read_text(encoding="utf-8") + site_block, encoding="utf-8")
    world["project"] = project


def _generate(world: dict[str, Any]) -> SiteResult:
    project = world["project"]
    conn = sqlite3.connect(project / ".beadloom" / "beadloom.db")
    conn.row_factory = sqlite3.Row
    try:
        return generate_site(conn, world["site"], project_root=project, now_ts=_NOW)
    finally:
        conn.close()


def _identity(world: dict[str, Any]) -> dict[str, Any]:
    module = (world["site"] / _IDENTITY).read_text(encoding="utf-8")
    match = re.search(r"export const site = (\{.*\});", module)
    assert match is not None, module
    value: dict[str, Any] = json.loads(match.group(1))
    return value


@given(
    parsers.parse('a project that declares the site "{title}" at "{base}" linking "{url}"')
)
def _declared(world: dict[str, Any], title: str, base: str, url: str) -> None:
    _project(world, f"site:\n  title: {title}\n  base: {base}\n  repo_url: {url}\n")


@given("a project that declares no site")
def _undeclared(world: dict[str, Any]) -> None:
    _project(world, "")


@given(parsers.parse('a project whose site block misspells "{key}" as "{typo}"'))
def _misspelled(world: dict[str, Any], key: str, typo: str) -> None:
    assert key != typo
    _project(world, f"site:\n  {typo}: /orders/\n")


@given("the site has been generated once")
def _generated_once(world: dict[str, Any]) -> None:
    _generate(world)


@given("the portal's VitePress config has been edited by hand")
def _edit_config(world: dict[str, Any]) -> None:
    config = world["site"] / _CONFIG
    edited = config.read_text(encoding="utf-8") + _HAND_EDIT
    config.write_text(edited, encoding="utf-8")
    world["edited"] = edited


@given(
    parsers.parse(
        'the project keeps its own "{page}" and its own theme stylesheet under .beadloom/site/'
    )
)
def _overrides(world: dict[str, Any], page: str) -> None:
    overrides = world["project"] / ".beadloom" / "site"
    (overrides / page).parent.mkdir(parents=True, exist_ok=True)
    (overrides / page).write_text(_OUR_GUIDE, encoding="utf-8")
    style = overrides / _STYLESHEET
    style.parent.mkdir(parents=True, exist_ok=True)
    style.write_text(_OUR_STYLE, encoding="utf-8")


@given("the project records AI tech-writer runs")
def _ai_runs(world: dict[str, Any]) -> None:
    store = world["project"] / ".beadloom" / "ai_techwriter_runs.json"
    store.write_text(
        json.dumps([{"ts": _NOW, "docs_refreshed": ["docs/a.md"], "input_tokens": 10}]),
        encoding="utf-8",
    )


@when("the site is generated for the project")
def _generate_step(world: dict[str, Any]) -> None:
    world["result"] = _generate(world)


@when("the site is generated for the project, expecting a refusal")
def _generate_refused(world: dict[str, Any]) -> None:
    with pytest.raises(SiteConfigError) as caught:
        _generate(world)
    world["refusal"] = caught.value


@then(
    "the portal holds the scaffold: the VitePress config, the theme, package.json "
    "and the browser tests"
)
def _scaffold_written(world: dict[str, Any]) -> None:
    site = world["site"]
    for rel in (
        _CONFIG,
        ".vitepress/theme/index.js",
        ".vitepress/theme/widgets/graph-viewer/ui/GraphViewer.vue",
        "package.json",
        "package-lock.json",
        "e2e/playwright.config.js",
    ):
        assert (site / rel).is_file(), rel


@then(parsers.parse('the portal\'s identity is "{title}" at "{base}" linking "{url}"'))
def _identity_declared(world: dict[str, Any], title: str, base: str, url: str) -> None:
    identity = _identity(world)
    assert (identity["title"], identity["base"], identity["repoUrl"]) == (title, base, url)


@then(
    "the portal's identity is named after the project directory at \"/\" "
    "with no repository link"
)
def _identity_default(world: dict[str, Any]) -> None:
    identity = _identity(world)
    assert (identity["title"], identity["base"], identity["repoUrl"]) == (_PROJECT_DIR, "/", "")


@then("no file of the portal names this repository")
def _no_leak(world: dict[str, Any]) -> None:
    leaks = []
    for path in world["site"].rglob("*"):
        if not path.is_file():
            continue
        # The footer's link to Beadloom's repository is the one mention allowed (BDL-080 S4d).
        text = without_the_footer_link(path.read_text(encoding="utf-8", errors="replace"))
        leaks.extend((path.name, token) for token in _OUR_IDENTITY if token in text)
    assert leaks == []


def _portal_files(world: dict[str, Any]) -> dict[str, str]:
    return {
        path.relative_to(world["site"]).as_posix(): path.read_text(
            encoding="utf-8", errors="replace"
        )
        for path in sorted(world["site"].rglob("*"))
        if path.is_file()
    }


@then("no scaffold file of the portal carries a beadloom annotation")
def _no_annotation(world: dict[str, Any]) -> None:
    marked = {
        rel: marker
        for rel, text in _portal_files(world).items()
        if (marker := read_marker(text)) is not None
    }
    assert marked, "the portal holds no file the scaffold wrote"
    assert sorted(rel for rel, marker in marked.items() if "beadloom:" in marker.body) == []


@then("no file of the portal names a node this repository's graph binds to the scaffold")
def _no_node_of_ours(world: dict[str, Any]) -> None:
    ids = scaffold_node_ids()
    assert ids, "this repository's graph binds no node to the scaffold"
    named = {
        rel: refs
        for rel, text in _portal_files(world).items()
        if (refs := node_ids_named(text, ids))
    }
    assert named == {}


@then("the hand edit in the VitePress config is still on disk")
def _edit_kept(world: dict[str, Any]) -> None:
    assert (world["site"] / _CONFIG).read_text(encoding="utf-8") == world["edited"]


@then(
    parsers.parse(
        "the generation reports the VitePress config as kept, "
        'with "{override}" as where the edit belongs'
    )
)
def _edit_reported(world: dict[str, Any], override: str) -> None:
    kept = {entry.path: entry for entry in world["result"].scaffold.kept}
    assert _CONFIG in kept
    assert override in kept[_CONFIG].remediation


@then(parsers.parse('the portal\'s "{page}" is the project\'s own'))
def _page_is_ours(world: dict[str, Any], page: str) -> None:
    assert (world["site"] / page).read_text(encoding="utf-8") == _OUR_GUIDE


@then("the portal's theme stylesheet is the project's own")
def _style_is_ours(world: dict[str, Any]) -> None:
    assert (world["site"] / _STYLESHEET).read_text(encoding="utf-8") == _OUR_STYLE


@then(parsers.parse('the refusal names "{where}"'))
def _refusal_names(world: dict[str, Any], where: str) -> None:
    refusal = world["refusal"]
    assert [entry.where for entry in refusal.refusals] == [where]


@then("nothing was written")
def _nothing_written(world: dict[str, Any]) -> None:
    assert not world["site"].exists()


def _dashboard(world: dict[str, Any]) -> str:
    return (world["site"] / "dashboard.md").read_text(encoding="utf-8")


@then("the dashboard page does not mount the AI tech-writer panel")
def _no_panel(world: dict[str, Any]) -> None:
    assert "<AiTechwriterActivity" not in _dashboard(world)


@then("the dashboard page mounts the AI tech-writer panel")
def _panel(world: dict[str, Any]) -> None:
    assert "<AiTechwriterActivity />" in _dashboard(world)

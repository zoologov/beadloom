"""Step implementations for `site-generation/a_moved_node_page_is_retired_on_upgrade.feature`.

BDL-081 R2 (`beadloom-ehts`), RFC D4. Against a real project directory, the real
reindex and the real command: the portal is first given the page 8.0.0 wrote for a
`kind: site` node, in 8.0.0's words and at 8.0.0's path, and `beadloom docs site`
then rewrites it, so the scenario reads the page tree and the line an adopter sees.

The module is named ``test_*`` so default pytest collection picks the scenarios up.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.reindex import reindex
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../application/site-generation/a_moved_node_page_is_retired_on_upgrade.feature")

PORTAL = "atlas-portal"
ROOT = "atlas"

_GRAPH = f"""\
nodes:
  - ref_id: {ROOT}
    kind: service
    summary: The atlas product.
  - ref_id: {PORTAL}
    kind: site
    summary: The atlas portal.
edges:
  - src: {PORTAL}
    dst: {ROOT}
    kind: part_of
"""

#: The page 8.0.0's `docs site` wrote for the portal node, as it wrote it.
_PAGE_8_0_0 = f"""\
---
title: {PORTAL}
kind: site
---

# {PORTAL}

**Kind:** site

The atlas portal.

## Public symbols

_None indexed._

## Relationships

- **part_of**: [{ROOT}](../services/{ROOT}.md)

## Documentation

_No linked documents._

## Graph

<ClientOnly>
  <ArchitectureMap focus="{PORTAL}" :depth="1" height="60vh" />
</ClientOnly>
"""

_OWN_PAGE = "# The atlas team's notes on its portal\n"


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    return {"root": tmp_path / ROOT, "site": tmp_path / ROOT / "site"}


@given(parsers.parse('a project whose portal node is declared with the kind "{kind}"'))
def _project(world: dict[str, Any], kind: str) -> None:
    graph_dir = world["root"] / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "atlas.yml").write_text(_GRAPH.replace("kind: site", f"kind: {kind}"), "utf-8")
    reindex(world["root"])


@given(
    parsers.parse('a portal 8.0.0 wrote for it, with the portal node\'s page under "{section}"')
)
def _old_portal(world: dict[str, Any], section: str) -> None:
    page = world["site"] / section / f"{PORTAL}.md"
    page.parent.mkdir(parents=True)
    page.write_text(_PAGE_8_0_0, encoding="utf-8")


@given(parsers.parse('the project provides its own "{rel}" under .beadloom/site/'))
def _override(world: dict[str, Any], rel: str) -> None:
    own = world["root"] / ".beadloom" / "site" / rel
    own.parent.mkdir(parents=True)
    own.write_text(_OWN_PAGE, encoding="utf-8")


@when("docs site rewrites the portal")
def _rewrite(world: dict[str, Any]) -> None:
    args = ["docs", "site", "--project", str(world["root"]), "--out", str(world["site"])]
    result = CliRunner().invoke(main, args, catch_exceptions=False)
    assert result.exit_code == 0, result.output
    world["output"] = result.output


@then(parsers.parse('the portal node\'s page is "{page}" and there is none under "{other}"'))
def _moved(world: dict[str, Any], page: str, other: str) -> None:
    site: Path = world["site"]
    assert (site / page).is_file()
    assert not (site / other / f"{PORTAL}.md").exists()


@then(
    parsers.parse(
        'the portal node\'s page is "{page}" and the project\'s own page stays under "{other}"'
    )
)
def _kept(world: dict[str, Any], page: str, other: str) -> None:
    site: Path = world["site"]
    assert (site / page).is_file()
    assert (site / other / f"{PORTAL}.md").read_text(encoding="utf-8") == _OWN_PAGE


@then(parsers.parse("the scaffold line counts {count:d} moved pages retired"))
def _line(world: dict[str, Any], count: int) -> None:
    lines = [line for line in world["output"].splitlines() if line.startswith("Scaffold (")]
    assert len(lines) == 1, world["output"]
    assert f"empty folders retired, {count} moved pages retired, " in lines[0]

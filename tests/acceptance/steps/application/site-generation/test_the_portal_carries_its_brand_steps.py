"""Step implementations for `application/site-generation/the_portal_carries_its_brand.feature`.

BDL-080 S4d (`beadloom-af99.7`), and S4e (`beadloom-af99.9`): the favicon follows the
logo and a logo drawn in `currentColor` takes the text's colour. Against a real
project directory, the real reindex and the real generator with the scaffold the
installed package ships: the scenarios read what `docs site` leaves in the output
directory, and run the real `config-check` command over the project.
"""

from __future__ import annotations

import json
import re
import sqlite3
from importlib.resources import files
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.site.generate import SiteResult, generate_site
from beadloom.application.site.scaffold import read_marker
from beadloom.application.site.site_config import SiteConfigError
from beadloom.services.cli import main
from tests.support.tiered_project import write_zoned_import_project

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../application/site-generation/the_portal_carries_its_brand.feature")

_NOW = "2026-10-09T00:00:00+00:00"
_PROJECT_DIR = "acme-orders"
_IDENTITY = ".vitepress/site.generated.mjs"
_CONFIG = ".vitepress/config.mjs"
#: Beadloom's icon as the package ships it, the footer's and the only mark.
_BEADLOOM_ICON = ("site_scaffold", "public", "brand", "beadloom-icon.svg")
#: Where the package keeps Beadloom's favicon, the SVG and its two PNGs.
_FAVICON_DIR = "site_favicon"

#: A logo of the project's own, in each kind the portal takes; the bytes are compared.
_LOGOS = {
    ".svg": b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8"><rect/></svg>\n',
    ".png": b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR",
    ".jpg": b"\xff\xd8\xff\xe0",
}


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    return {"root": tmp_path / _PROJECT_DIR, "site": tmp_path / _PROJECT_DIR / "site"}


def _project(world: dict[str, Any], lines: list[str]) -> Path:
    project = write_zoned_import_project(world["root"])
    config = project / ".beadloom" / "config.yml"
    block = "site:\n" + "".join(f"  {line}\n" for line in lines)
    config.write_text(config.read_text(encoding="utf-8") + block, encoding="utf-8")
    world["project"] = project
    return project


def _hold(project: Path, rel: str) -> bytes:
    path = project / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    body = _LOGOS[path.suffix]
    path.write_bytes(body)
    return body


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


def _config_check(world: dict[str, Any]) -> Any:
    return CliRunner().invoke(main, ["config-check", "--project", str(world["project"])])


@given(parsers.parse('a project that holds the file "{rel}" and declares it as its logo'))
def _declares_its_logo(world: dict[str, Any], rel: str) -> None:
    project = _project(world, [f"logo: {rel}"])
    world["logo"] = _hold(project, rel)


@given(
    parsers.parse('a project that holds Beadloom\'s icon at "{rel}" and declares it as its logo')
)
def _declares_beadloom_icon(world: dict[str, Any], rel: str) -> None:
    project = _project(world, [f"logo: {rel}"])
    path = project / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    icon = files("beadloom")
    for part in _BEADLOOM_ICON:
        icon = icon.joinpath(part)
    path.write_bytes(icon.read_bytes())


@given(parsers.parse('a project that holds the file "{rel}" and declares the logo "{logo}"'))
def _declares_a_logo(world: dict[str, Any], rel: str, logo: str) -> None:
    project = _project(world, [f"logo: {logo}"])
    _hold(project, rel)


@given(parsers.parse('a project that declares the site block "{line}" and "{other}"'))
def _declares_two(world: dict[str, Any], line: str, other: str) -> None:
    _project(world, [line, other])


@given(parsers.re(r'a project that declares the site block "(?P<line>[^"]+)"$'))
def _declares_one(world: dict[str, Any], line: str) -> None:
    _project(world, [line])


@when("the site is generated for the project")
def _generate_step(world: dict[str, Any]) -> None:
    world["result"] = _generate(world)


@when("the site is generated for the project, expecting a refusal")
def _generate_refused(world: dict[str, Any]) -> None:
    with pytest.raises(SiteConfigError) as caught:
        _generate(world)
    world["refusal"] = caught.value


@then(parsers.parse('the portal holds the project\'s logo at "{rel}", byte for byte'))
def _logo_copied(world: dict[str, Any], rel: str) -> None:
    assert (world["site"] / rel).read_bytes() == world["logo"]
    assert world["site"] / rel in world["result"].written


@then(parsers.parse('the portal\'s identity names the logo "{path}"'))
def _logo_named(world: dict[str, Any], path: str) -> None:
    assert _identity(world)["logo"] == path


@then("the portal's identity names no logo")
def _no_logo(world: dict[str, Any]) -> None:
    assert _identity(world)["logo"] == ""
    assert not list((world["site"] / "public").glob("logo.*"))


@then(parsers.parse("the portal's identity switches the footer {state}"))
def _footer(world: dict[str, Any], state: str) -> None:
    assert _identity(world)["poweredBy"] is (state == "on")


@then(parsers.parse('the portal holds the brand file "{rel}"'))
def _brand_file(world: dict[str, Any], rel: str) -> None:
    shipped = files("beadloom").joinpath("site_scaffold", rel).read_text(encoding="utf-8")
    marker = read_marker((world["site"] / rel).read_text(encoding="utf-8"))
    assert marker is not None and marker.intact
    assert marker.body == shipped


@then(parsers.parse('the portal holds no file "{rel}"'))
def _no_file(world: dict[str, Any], rel: str) -> None:
    assert not (world["site"] / rel).exists(), rel


@then("the portal's VitePress config takes its favicons from the portal's identity")
def _favicon_from_identity(world: dict[str, Any]) -> None:
    config = (world["site"] / _CONFIG).read_text(encoding="utf-8")
    # The browser case (`e2e/brand.spec.js`) follows the links; this reads the config.
    assert 'rel: "icon"' in config, config
    assert "site.favicons" in config, config
    assert "brand/beadloom-" not in config, "the config names no brand file of its own"


@then(parsers.parse('the portal\'s identity names the favicons "{listed}"'))
def _favicons(world: dict[str, Any], listed: str) -> None:
    expected = []
    # "<href> <type> [<sizes> [<media>]]": a media query holds spaces, so it is the rest.
    for item in listed.split(", "):
        href, kind, *rest = item.split(" ", 3)
        icon = {"href": href, "type": kind}
        if rest:
            icon["sizes"] = rest[0]
        if len(rest) > 1:
            icon["media"] = rest[1]
        expected.append(icon)
    assert _identity(world)["favicons"] == expected


@then(parsers.parse('the portal holds Beadloom\'s favicon "{rel}", byte for byte'))
def _beadloom_favicon(world: dict[str, Any], rel: str) -> None:
    name = rel.rsplit("/", 1)[-1]
    shipped = files("beadloom").joinpath(_FAVICON_DIR, name).read_bytes()
    assert (world["site"] / rel).read_bytes() == shipped
    assert world["site"] / rel in world["result"].written


@then(parsers.parse("the portal's identity draws the logo {how}"))
def _logo_drawn(world: dict[str, Any], how: str) -> None:
    assert _identity(world)["logoMonochrome"] is (how == "in the text's colour")


@then(parsers.re(r'the portal\'s repository link carries the "(?P<icon>[^"]+)" icon'))
def _icon(world: dict[str, Any], icon: str) -> None:
    assert _identity(world)["repoIcon"] == icon


@then('the portal\'s repository link carries the "" icon')
def _no_icon(world: dict[str, Any]) -> None:
    identity = _identity(world)
    assert (identity["repoUrl"], identity["repoIcon"]) == ("", "")


@then(parsers.parse('config-check passes the project naming "{where}"'))
def _config_check_names(world: dict[str, Any], where: str) -> None:
    result = _config_check(world)
    assert result.exit_code == 0, result.output
    assert where in result.output, result.output


@then(parsers.parse('the refusal names "{where}" and "{word}"'))
def _refused(world: dict[str, Any], where: str, word: str) -> None:
    refusal = world["refusal"]
    assert [found.where for found in refusal.refusals] == [where], refusal.refusals
    assert word in str(refusal), str(refusal)
    assert not (world["site"] / "index.md").exists(), "a refused site writes nothing"


@then(parsers.parse('config-check refuses the project naming "{where}"'))
def _config_check_refuses(world: dict[str, Any], where: str) -> None:
    result = _config_check(world)
    assert result.exit_code == 1, result.output
    assert where in result.output, result.output

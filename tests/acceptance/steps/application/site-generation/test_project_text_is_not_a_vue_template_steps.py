"""Steps for `application/site-generation/project_text_is_not_a_vue_template.feature`.

BDL-076 (`beadloom-ujzb.12`). A small JavaScript project, initialised by the real
`beadloom init`, indexed by the real reindex and given its portal by the real
generator. The scenarios read the pages `docs site` leaves in the output
directory. Whether VitePress then builds them is the slow adopter case's
question (`test_an_adopter_builds_its_portal_from_docs_site.py`); these read what
the generator hands it.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.services.cli import main
from tests.support.committed_project import commit_project

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../application/site-generation/project_text_is_not_a_vue_template.feature")

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


def _unescape(text: str) -> str:
    """A Gherkin string's ``\\n`` and ``\\"`` as the characters they name."""
    return text.replace("\\n", "\n").replace('\\"', '"')


#: An empty comment: it renders nothing, and between two braces Vue reads no interpolation.
_BREAK = "<!---->"


def _held_where_vue_does_not_read(body: str, text: str) -> tuple[int, int]:
    """How often *body* shows *text*, and how often Vue does not read it there.

    Vue reads ``{{`` only where the two braces meet in the page, and nothing inside
    an element carrying ``v-pre``. Text whose braces an empty comment separates is
    shown as written and never read (``beadloom-ujzb.21``).
    """
    shown = body.replace(_BREAK, "").count(text)
    broken = body.count(text[:1] + _BREAK + text[1:])
    inert = re.findall(rf"<(\w+) v-pre>{re.escape(text)}</\1>", body)
    return shown, broken + len(inert)


@given(parsers.parse('a project whose README opens with "{paragraph}"'))
def _project(world: dict[str, Any], paragraph: str) -> None:
    root: Path = world["root"]
    (root / "src" / "api").mkdir(parents=True)
    (root / "package.json").write_text(
        '{ "name": "acme", "version": "0.1.0", "type": "module" }\n', encoding="utf-8"
    )
    (root / "README.md").write_text(f"# Acme\n\n{_unescape(paragraph)}\n", encoding="utf-8")
    (root / _MODULE).write_text("export function handle() {\n  return 1;\n}\n", encoding="utf-8")


@given(parsers.parse('the project declares the repository "{url}"'))
def _repository(world: dict[str, Any], url: str) -> None:
    world["repo_url"] = url


@given(parsers.parse('the project\'s document "{rel}" reads "{text}"'))
def _document(world: dict[str, Any], rel: str, text: str) -> None:
    doc: Path = world["root"] / rel
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(f"# Guide\n\n{_unescape(text)}\n", encoding="utf-8")


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


@then(parsers.parse('the About page holds "{text}" twice, each where Vue does not read it'))
def _about_holds(world: dict[str, Any], text: str) -> None:
    body = _page(world, "index.md")
    assert _held_where_vue_does_not_read(body, text) == (2, 2), body


@then(
    parsers.parse('the root service\'s page holds "{text}" twice, each where Vue does not read it')
)
def _service_holds(world: dict[str, Any], text: str) -> None:
    body = _page(world, f"services/{_PROJECT}.md")
    assert _held_where_vue_does_not_read(body, text) == (2, 2), body


@then(parsers.parse('the published guide shows "{tag}" as text'))
def _shows_as_text(world: dict[str, Any], tag: str) -> None:
    body = _page(world, "docs/guide.md")
    assert "&lt;" + tag[1:] in body, body
    assert tag not in body, body


@then(parsers.parse('the published guide keeps "{markup}" as HTML'))
def _keeps_html(world: dict[str, Any], markup: str) -> None:
    body = _page(world, "docs/guide.md")
    assert markup in body, body


@then(parsers.parse('the published guide links "{text}" in HTML to "{url}"'))
def _links_in_html(world: dict[str, Any], text: str, url: str) -> None:
    body = _page(world, "docs/guide.md")
    expected = url.replace("{commit}", world.get("ref", ""))
    assert re.findall(rf'<a href="([^"]*)"[^>]*>{re.escape(text)}</a>', body) == [expected], body


@then(parsers.parse('the published guide reads "{alt}" in place of the image'))
def _image_as_text(world: dict[str, Any], alt: str) -> None:
    body = _page(world, "docs/guide.md")
    assert "<img" not in body, body
    assert alt in body, body


@then(parsers.parse('the published guide holds "{text}" in {count:d} blocks Vue skips'))
def _held_in_skipped_blocks(world: dict[str, Any], text: str, count: int) -> None:
    """Each block a ``<div v-pre>`` wraps, which Vue leaves as written, holds *text* once."""
    body = _page(world, "docs/guide.md")
    blocks = re.findall(r"<div v-pre>(.*?)</div>", body, re.DOTALL)
    assert [block.count(text) for block in blocks] == [1] * count, body
    assert body.count(text) == count, body


@then(parsers.parse('the published guide holds no "{text}"'))
def _holds_no(world: dict[str, Any], text: str) -> None:
    body = _page(world, "docs/guide.md")
    assert text not in body, body



# -- the re-review of R2's fixes (``beadloom-ujzb.23``) ---------------------------------


@given(parsers.parse('the project\'s document "{rel}" opens with the front matter "{block}"'))
def _document_with_front_matter(world: dict[str, Any], rel: str, block: str) -> None:
    doc: Path = world["root"] / rel
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(f"---\n{_unescape(block)}\n---\n\n# Setup\n", encoding="utf-8")
    world["front_matter"] = _unescape(block)


@then(parsers.parse('the published guide links to "{url}" with text Vue does not read'))
def _links_with_inert_text(world: dict[str, Any], url: str) -> None:
    """The address is the link's text with its brace pair broken; the destination keeps it."""
    body = _page(world, "docs/guide.md")
    shown = url.replace("{{", "{" + _BREAK + "{")
    assert f"[{shown}](<{url}>)" in body, body


@then(parsers.parse('the published guide shows "{text}" with no attribute read from it'))
def _attrs_read_none(world: dict[str, Any], text: str) -> None:
    """A backslash before the brace makes it an escape, which the plugin never reads."""
    body = _page(world, "docs/guide.md")
    assert "\\" + text in body, body


@then(parsers.parse('the published "{rel}" opens with its badge'))
def _opens_with_badge(world: dict[str, Any], rel: str) -> None:
    assert _page(world, rel).startswith("<!-- beadloom:badge-start -->"), _page(world, rel)


@then(parsers.parse('the published "{rel}" holds its front matter below the badge, as Markdown'))
def _front_matter_below_badge(world: dict[str, Any], rel: str) -> None:
    body = _page(world, rel)
    below = body.split("<!-- beadloom:badge-end -->", 1)[1]
    assert below.startswith(f"\n\n---\n{world['front_matter']}\n---\n"), body

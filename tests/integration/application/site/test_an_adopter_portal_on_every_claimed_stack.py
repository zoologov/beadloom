"""An adopter on each claimed stack builds its portal and sees its own architecture.

BDL-076 B3 (``beadloom-hmqn``). The PRD claims the portal for Python, Go, JS/TS,
Java, Kotlin and Swift. Each stack's fixture (``tests/fixtures/site/<stack>/``) is
copied, committed with an ``origin``, initialised with ``beadloom init``, given
its portal identity, and built with ``npm ci`` and ``vitepress build``.

A build that passes is half the claim. The other half is what the adopter sees:
the modules as nodes, the imports between them as ``depends_on`` edges and no
edge the code does not have, a page per node, and nothing of this repository.
The expected modules and imports are read from each fixture's code and written
in :mod:`tests.support.adopter_portals`, never taken from the product.

Where the product does not meet an expectation today, the test is a strict
``xfail`` naming the bead that holds the defect, so it fails the day the defect
is fixed and the mark is still there.

Marked ``slow``: six portal builds, about three minutes on a warm npm cache. The
advisory CI job ``site-adopters`` runs it.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import pytest

from tests.support.adopter_portals import FIXTURES_BY_STACK, this_repositorys_identity

if TYPE_CHECKING:
    from collections.abc import Callable

    from tests.support.adopter_portals import BuiltPortal

pytestmark = pytest.mark.slow

#: The defects B3 found, each filed under the epic; the reason names the bead.
_JVM_LAYOUT = (
    "beadloom-ujzb.15: init on a Maven or Gradle layout makes nodes of src/main and "
    "src/main/<language>, not of the packages, and draws no depends_on edge"
)
_SWIFTPM_LAYOUT = "beadloom-ujzb.16: init on a Swift Package Manager layout finds no node at all"


def _stacks(xfails: dict[str, str] | None = None) -> list[Any]:
    """Every claimed stack as a parameter, the named ones as strict xfails."""
    marks = xfails or {}
    return [
        pytest.param(
            stack,
            marks=[pytest.mark.xfail(reason=marks[stack], strict=True)] if stack in marks else [],
        )
        for stack in FIXTURES_BY_STACK
    ]


def _built(adopter_portals: Callable[[str], BuiltPortal], stack: str) -> BuiltPortal:
    """The stack's portal, required to have built: every other test reads its output."""
    portal = adopter_portals(stack)
    failed = portal.failed_step()
    assert failed is None, failed
    return portal


def _owner(portal: BuiltPortal, directory: str) -> str | None:
    """The node whose source is *directory* in the published data file, if any."""
    for node in portal.data()["nodes"]:
        if str(node.get("source") or "").rstrip("/") == directory:
            return str(node["id"])
    return None


def _depends_on(portal: BuiltPortal) -> set[tuple[str, str]]:
    return {(e["src"], e["dst"]) for e in portal.data()["edges"] if e["kind"] == "depends_on"}


def _under(path: str, directory: str) -> bool:
    return directory == "" or path == directory or path.startswith(f"{directory}/")


@pytest.mark.parametrize("stack", _stacks())
def test_the_portal_builds_from_docs_site(
    adopter_portals: Callable[[str], BuiltPortal], stack: str
) -> None:
    portal = adopter_portals(stack)

    assert portal.failed_step() is None, portal.failed_step()
    assert (portal.dist / "index.html").is_file()


@pytest.mark.parametrize(
    "stack", _stacks({"java": _JVM_LAYOUT, "kotlin": _JVM_LAYOUT, "swift": _SWIFTPM_LAYOUT})
)
def test_every_module_of_the_project_is_a_node(
    adopter_portals: Callable[[str], BuiltPortal], stack: str
) -> None:
    portal = _built(adopter_portals, stack)

    missing = [module for module in portal.fixture.modules if _owner(portal, module) is None]

    assert missing == []


@pytest.mark.parametrize(
    "stack",
    _stacks(
        {
            "java": _JVM_LAYOUT,
            "kotlin": _JVM_LAYOUT,
            "swift": _SWIFTPM_LAYOUT,
        }
    ),
)
def test_every_import_between_modules_is_a_depends_on_edge(
    adopter_portals: Callable[[str], BuiltPortal], stack: str
) -> None:
    portal = _built(adopter_portals, stack)
    edges = _depends_on(portal)

    missing = [
        (importer, imported)
        for importer, imported in portal.fixture.imports
        if (_owner(portal, importer), _owner(portal, imported)) not in edges
    ]

    assert missing == []


@pytest.mark.parametrize("stack", _stacks())
def test_no_depends_on_edge_joins_modules_the_code_does_not_join(
    adopter_portals: Callable[[str], BuiltPortal], stack: str
) -> None:
    """Each edge is backed by an import from a module under its source to one under its target."""
    portal = _built(adopter_portals, stack)
    sources = {n["id"]: str(n.get("source") or "").rstrip("/") for n in portal.data()["nodes"]}

    unbacked = sorted(
        (src, dst)
        for src, dst in _depends_on(portal)
        if not any(
            _under(importer, sources[src]) and _under(imported, sources[dst])
            for importer, imported in portal.fixture.imports
        )
    )

    assert unbacked == []


@pytest.mark.parametrize("stack", _stacks())
def test_every_node_has_its_page_in_the_built_portal(
    adopter_portals: Callable[[str], BuiltPortal], stack: str
) -> None:
    portal = _built(adopter_portals, stack)

    missing = [
        node["id"]
        for node in portal.data()["nodes"]
        if not (portal.dist / f"{str(node['url']).strip('/')}.html").is_file()
    ]

    assert missing == []


@pytest.mark.parametrize("stack", _stacks())
def test_the_data_file_carries_the_declared_layers(
    adopter_portals: Callable[[str], BuiltPortal], stack: str
) -> None:
    portal = _built(adopter_portals, stack)

    layers = [layer["name"] for layer in portal.data().get("layers") or []]

    assert layers == list(portal.fixture.layers)


@pytest.mark.parametrize("stack", ["go", "typescript"])
def test_the_declared_warn_rule_finds_the_dependency_it_names(
    adopter_portals: Callable[[str], BuiltPortal], stack: str
) -> None:
    """Each of these fixtures declares one warn rule over a dependency its code has."""
    portal = _built(adopter_portals, stack)
    (rule,) = portal.fixture.rules

    found = [
        node["id"]
        for node in portal.data()["nodes"]
        for finding in node.get("findings") or []
        if finding["rule"] == rule["name"] and finding["severity"] == "warn"
    ]

    assert len(found) == 1


@pytest.mark.parametrize("stack", _stacks())
def test_init_keeps_the_portal_output_out_of_git(
    adopter_portals: Callable[[str], BuiltPortal], stack: str
) -> None:
    portal = _built(adopter_portals, stack)

    lines = (portal.root / ".gitignore").read_text(encoding="utf-8").splitlines()

    assert "/site/" in lines


@pytest.mark.parametrize("stack", _stacks())
def test_the_portal_carries_the_projects_title_base_and_repository(
    adopter_portals: Callable[[str], BuiltPortal], stack: str
) -> None:
    portal = _built(adopter_portals, stack)
    fixture = portal.fixture

    index = (portal.dist / "index.html").read_text(encoding="utf-8")

    assert f"<title>{fixture.title}" in index
    assert re.search(rf'(src|href)="{re.escape(fixture.base)}assets/', index)
    assert fixture.repo_url in index


@pytest.mark.parametrize("stack", _stacks())
def test_no_text_of_this_repository_reaches_the_portal(
    adopter_portals: Callable[[str], BuiltPortal], stack: str
) -> None:
    portal = _built(adopter_portals, stack)
    ours = this_repositorys_identity()

    leaks = sorted(
        (str(path.relative_to(portal.dist)), token)
        for path in portal.dist.rglob("*")
        if path.suffix in {".html", ".js", ".json", ".css"}
        for token in ours
        if token in path.read_text(encoding="utf-8", errors="replace")
    )

    assert leaks == []


@pytest.mark.parametrize("stack", _stacks())
def test_each_source_link_goes_to_the_projects_forge_at_the_generated_commit(
    adopter_portals: Callable[[str], BuiltPortal], stack: str
) -> None:
    portal = _built(adopter_portals, stack)
    fixture = portal.fixture
    with_source = [n for n in portal.data()["nodes"] if n.get("source")]

    wrong = [
        (node["id"], node.get("source_url"))
        for node in with_source
        if node.get("source_url")
        != fixture.tree_route.format(
            url=fixture.repo_url, ref=portal.commit, path=str(node["source"]).rstrip("/")
        )
    ]

    assert wrong == []


def test_a_self_hosted_gitlab_serves_the_readmes_file_link_and_image_at_the_commit(
    adopter_portals: Callable[[str], BuiltPortal],
) -> None:
    """The Java fixture declares its own GitLab host under ``site.forges`` (``ujzb.8``)."""
    portal = _built(adopter_portals, "java")
    repo, commit = portal.fixture.repo_url, portal.commit

    about = (portal.dist / "index.html").read_text(encoding="utf-8")

    assert f'href="{repo}/-/blob/{commit}/LICENSE"' in about
    assert f'src="{repo}/-/raw/{commit}/images/ledger.png"' in about


def test_a_helm_value_in_the_readme_and_the_docs_reads_as_written(
    adopter_portals: Callable[[str], BuiltPortal],
) -> None:
    """The Go fixture's README and runbook quote Helm's ``{{ .Values.x }}`` (``ujzb.12``)."""
    portal = _built(adopter_portals, "go")

    about = (portal.dist / "index.html").read_text(encoding="utf-8")
    operations = (portal.dist / "docs" / "operations.html").read_text(encoding="utf-8")

    assert "{{ .Values.image.tag }}" in about
    assert "{{ .Values.replicaCount }}" in about
    assert "{{ .Values.image.tag }}" in operations

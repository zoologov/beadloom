"""The adopter fixtures, one per claimed stack, and the portal each one builds.

BDL-076 B3 (``beadloom-hmqn``). The PRD claims the portal works for an adopter on
Python, Go, JS/TS, Java, Kotlin and Swift. Each of those is a small project under
``tests/fixtures/site/<stack>/``: a few modules with real imports between them, a
README, a ``docs/`` folder and tests in the stack's own convention. Nothing in a
fixture names this repository. A fixture file named like one of this repository's
own tests is stored under :data:`STORED_SUFFIX` and takes its name back on copy.

:func:`build_portal` does to a copy what an adopter does: commit it to git with an
``origin``, run ``beadloom init``, declare the portal's identity (and, where the
fixture has them, its layers and rules), ``reindex``, ``docs site``, ``npm ci``
and ``vitepress build``. It records every step's exit code and output rather than
raising, so a test names the step that failed.

Each :class:`AdopterFixture` states, independently of the product, what an
adopter would expect the graph to show: which source directories are modules, and
which module imports which. A test compares the published data file with that.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import yaml
from click.testing import CliRunner

from beadloom.services.cli import main
from tests.support.committed_project import commit_project
from tests.support.repository_root import REPO_ROOT, TESTS_ROOT

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

#: Where the fixtures live.
FIXTURES = TESTS_ROOT / "fixtures" / "site"

#: The suffix a fixture file is stored under when its own name would make it one of
#: this repository's tests: the Python fixture's ``tests/test_*.py``. It is removed
#: when the fixture is copied, so the adopter's project holds the name its stack uses.
STORED_SUFFIX = ".fixture"

#: The oldest Node the scaffold's ``engines.node`` accepts.
NODE_MAJOR = 22

#: A forge's route to a path at a commit, written from the forge's published URL
#: form and not read from the product's table.
GITHUB_TREE = "{url}/tree/{ref}/{path}"
GITLAB_TREE = "{url}/-/tree/{ref}/{path}"
GITEA_TREE = "{url}/src/commit/{ref}/{path}"
BITBUCKET_TREE = "{url}/src/{ref}/{path}"


@dataclass(frozen=True)
class AdopterFixture:
    """One claimed stack's fixture, with what an adopter expects its portal to show.

    ``modules`` are the source directories an adopter reads as the project's
    modules, and ``imports`` the pairs of them one imports from the other, each
    read from the fixture's code. ``tags`` maps a source directory to the tags the
    adopter declares on its node after ``init``; ``layers`` names the layer rule's
    layers top to bottom, each tagged ``tier-<name>``; ``rules`` are further rules
    the adopter adds, as ``rules.yml`` writes them.
    """

    stack: str
    project: str
    title: str
    base: str
    repo_url: str
    origin: str
    tree_route: str
    modules: tuple[str, ...]
    imports: tuple[tuple[str, str], ...]
    forges: Mapping[str, str] = field(default_factory=dict)
    layers: tuple[str, ...] = ()
    tags: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    rules: tuple[Mapping[str, Any], ...] = ()

    @property
    def source(self) -> Path:
        """The fixture's directory in this repository."""
        return FIXTURES / self.stack


_LEDGER = "src/main/java/org/example/ledger"
_ORCHARD = "src/main/kotlin/org/example/orchard"

PYTHON = AdopterFixture(
    stack="python",
    project="parcel-desk",
    title="Parcel Desk",
    base="/parcel-desk/",
    repo_url="https://github.com/parcel-works/parcel-desk",
    origin="git@github.com:parcel-works/parcel-desk.git",
    tree_route=GITHUB_TREE,
    modules=("src/parceldesk/api", "src/parceldesk/billing", "src/parceldesk/storage"),
    imports=(
        ("src/parceldesk/api", "src/parceldesk/billing"),
        ("src/parceldesk/api", "src/parceldesk/storage"),
        ("src/parceldesk/billing", "src/parceldesk/storage"),
    ),
)

#: The Go fixture's one warn-level rule: the entry point wires the store itself
#: rather than through the catalogue, and the team keeps that flagged.
_ENTRY_WIRES_STORAGE: Mapping[str, Any] = {
    "name": "entry-wires-storage-through-the-catalog",
    "description": "The entry point reaches storage through the catalogue",
    "severity": "warn",
    "deny": {"from": {"tag": "tier-entry"}, "to": {"tag": "tier-storage"}},
}

GO = AdopterFixture(
    stack="go",
    project="tidewater",
    title="Tidewater",
    base="/tidewater/",
    repo_url="https://gitlab.com/harbour-works/tidewater",
    origin="git@gitlab.com:harbour-works/tidewater.git",
    tree_route=GITLAB_TREE,
    modules=(
        "cmd/tidewater",
        "internal/api",
        "internal/billing",
        "internal/catalog",
        "internal/storage",
    ),
    imports=(
        ("cmd/tidewater", "internal/api"),
        ("cmd/tidewater", "internal/catalog"),
        ("cmd/tidewater", "internal/storage"),
        ("internal/api", "internal/billing"),
        ("internal/api", "internal/catalog"),
        ("internal/billing", "internal/catalog"),
        ("internal/catalog", "internal/storage"),
    ),
    layers=("entry", "transport", "domain", "storage"),
    tags={
        "cmd/tidewater": ("tier-entry",),
        "internal/api": ("tier-transport",),
        "internal/billing": ("tier-domain",),
        "internal/catalog": ("tier-domain",),
        "internal/storage": ("tier-storage",),
    },
    rules=(_ENTRY_WIRES_STORAGE,),
)

#: The TypeScript fixture's one warn-level rule: the digest still reads the note
#: store directly, and the team keeps that read flagged until it moves onto the API.
_DIRECT_STORE_READ: Mapping[str, Any] = {
    "name": "reports-read-through-the-api",
    "description": "Reports read notes through the API; the direct store read is retiring",
    "severity": "warn",
    "deny": {"from": {"tag": "legacy-store-reader"}, "to": {"tag": "tier-data"}},
}

TYPESCRIPT = AdopterFixture(
    stack="typescript",
    project="lantern-notes",
    title="Lantern Notes",
    base="/lantern-notes/",
    repo_url="https://github.com/lantern-team/lantern-notes",
    origin="https://github.com/lantern-team/lantern-notes.git",
    tree_route=GITHUB_TREE,
    modules=(
        "src/accounts/session",
        "src/accounts/users",
        "src/notes/api",
        "src/notes/model",
        "src/notes/store",
        "src/reports/digest",
    ),
    imports=(
        ("src/accounts/session", "src/accounts/users"),
        ("src/notes/api", "src/accounts/session"),
        ("src/notes/api", "src/notes/model"),
        ("src/notes/api", "src/notes/store"),
        ("src/notes/model", "src/notes/store"),
        ("src/notes/store", "src/notes/model"),
        ("src/reports/digest", "src/notes/store"),
    ),
    layers=("interface", "data", "core"),
    tags={
        "src/accounts": ("tier-data",),
        "src/notes/api": ("tier-interface",),
        "src/notes/model": ("tier-core",),
        "src/notes/store": ("tier-data",),
        "src/reports/digest": ("tier-interface", "legacy-store-reader"),
    },
    rules=(_DIRECT_STORE_READ,),
)

#: The self-hosted forge case (BDL-076 B4, ``beadloom-ujzb.8``): a GitLab on the
#: team's own host, a group and a subgroup, an ``origin`` in the SSH form with a port.
JAVA = AdopterFixture(
    stack="java",
    project="quarry-ledger",
    title="Quarry Ledger",
    base="/quarry-ledger/",
    repo_url="https://git.quarry.example/finance/platform/quarry-ledger",
    origin="ssh://git@git.quarry.example:2222/finance/platform/quarry-ledger.git",
    forges={"git.quarry.example": "gitlab"},
    tree_route=GITLAB_TREE,
    modules=(f"{_LEDGER}/model", f"{_LEDGER}/repository", f"{_LEDGER}/service", f"{_LEDGER}/web"),
    imports=(
        (f"{_LEDGER}/repository", f"{_LEDGER}/model"),
        (f"{_LEDGER}/service", f"{_LEDGER}/model"),
        (f"{_LEDGER}/service", f"{_LEDGER}/repository"),
        (f"{_LEDGER}/web", f"{_LEDGER}/service"),
    ),
)

KOTLIN = AdopterFixture(
    stack="kotlin",
    project="orchard-routes",
    title="Orchard Routes",
    base="/orchard-routes/",
    repo_url="https://codeberg.org/orchard-crew/orchard-routes",
    origin="https://codeberg.org/orchard-crew/orchard-routes.git",
    tree_route=GITEA_TREE,
    modules=(f"{_ORCHARD}/geo", f"{_ORCHARD}/planner", f"{_ORCHARD}/routing"),
    imports=(
        (f"{_ORCHARD}/planner", f"{_ORCHARD}/geo"),
        (f"{_ORCHARD}/routing", f"{_ORCHARD}/geo"),
        (f"{_ORCHARD}/routing", f"{_ORCHARD}/planner"),
    ),
)

SWIFT = AdopterFixture(
    stack="swift",
    project="beacon-kit",
    title="Beacon Kit",
    base="/beacon-kit/",
    repo_url="https://bitbucket.org/trail-beacons/beacon-kit",
    origin="git@bitbucket.org:trail-beacons/beacon-kit.git",
    tree_route=BITBUCKET_TREE,
    modules=("Sources/BeaconApp", "Sources/BeaconCore", "Sources/BeaconNetwork"),
    imports=(
        ("Sources/BeaconApp", "Sources/BeaconCore"),
        ("Sources/BeaconApp", "Sources/BeaconNetwork"),
        ("Sources/BeaconNetwork", "Sources/BeaconCore"),
    ),
)

#: Every claimed stack, in the PRD's order.
FIXTURES_BY_STACK: Mapping[str, AdopterFixture] = {
    fixture.stack: fixture for fixture in (PYTHON, GO, TYPESCRIPT, JAVA, KOTLIN, SWIFT)
}


@dataclass
class Step:
    """One step of a portal build: its exit code, its output and its wall time."""

    returncode: int
    output: str
    seconds: float


@dataclass
class BuiltPortal:
    """A fixture copied, committed, initialised and built, with every step's record."""

    fixture: AdopterFixture
    root: Path
    commit: str
    steps: dict[str, Step] = field(default_factory=dict)

    @property
    def site(self) -> Path:
        """The portal's directory, as ``docs site`` writes it."""
        return self.root / "site"

    @property
    def dist(self) -> Path:
        """The built portal."""
        return self.site / ".vitepress" / "dist"

    def data(self) -> dict[str, Any]:
        """The architecture data file the built portal serves."""
        text = (self.dist / "architecture.data.json").read_text(encoding="utf-8")
        loaded: dict[str, Any] = json.loads(text)
        return loaded

    def failed_step(self) -> str | None:
        """The first step that did not exit 0, with its output; ``None`` when all did."""
        for name, step in self.steps.items():
            if step.returncode != 0:
                return f"{name} exited {step.returncode}:\n{step.output[-4000:]}"
        return None


def node_major(node: str) -> int:
    """The major version of the ``node`` executable at *node*."""
    version = subprocess.run(  # noqa: S603 - the node on PATH, asked its version
        [node, "--version"], check=True, capture_output=True, encoding="utf-8"
    ).stdout.strip()
    return int(version.lstrip("v").split(".")[0])


def _beadloom(*args: str) -> Step:
    started = time.monotonic()
    result = CliRunner().invoke(main, list(args))
    output = result.output
    if result.exception is not None and not isinstance(result.exception, SystemExit):
        output += f"\n{type(result.exception).__name__}: {result.exception}"
    return Step(result.exit_code, output, time.monotonic() - started)


def _run(command: list[str], cwd: Path) -> Step:
    started = time.monotonic()
    done = subprocess.run(  # noqa: S603 - a fixed npm command in the fixture's portal
        command, cwd=cwd, capture_output=True, encoding="utf-8", check=False
    )
    return Step(done.returncode, done.stdout + done.stderr, time.monotonic() - started)


def _by_source(nodes: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(node.get("source") or "").rstrip("/"): node for node in nodes}


def _declare(root: Path, fixture: AdopterFixture) -> None:
    """What the adopter writes after ``init``: the portal's identity, tags, layers, rules."""
    site: dict[str, Any] = {"title": fixture.title, "base": fixture.base}
    site["repo_url"] = fixture.repo_url
    if fixture.forges:
        site["forges"] = dict(fixture.forges)
    config = root / ".beadloom" / "config.yml"
    config.write_text(
        config.read_text(encoding="utf-8") + yaml.safe_dump({"site": site}, sort_keys=False),
        encoding="utf-8",
    )
    if fixture.tags:
        graph = root / ".beadloom" / "_graph" / "services.yml"
        declared = yaml.safe_load(graph.read_text(encoding="utf-8"))
        nodes = _by_source(declared["nodes"])
        for source, tags in fixture.tags.items():
            assert source in nodes, f"{fixture.stack}: init wrote no node for {source}/"
            nodes[source]["tags"] = list(tags)
        graph.write_text(yaml.safe_dump(declared, sort_keys=False), encoding="utf-8")
    added: list[dict[str, Any]] = [dict(rule) for rule in fixture.rules]
    if fixture.layers:
        added.insert(0, _layer_rule(fixture))
    if added:
        rules_file = root / ".beadloom" / "_graph" / "rules.yml"
        rules = yaml.safe_load(rules_file.read_text(encoding="utf-8"))
        rules["rules"] = added + list(rules.get("rules") or [])
        rules_file.write_text(yaml.safe_dump(rules, sort_keys=False), encoding="utf-8")


def _layer_rule(fixture: AdopterFixture) -> dict[str, Any]:
    return {
        "name": "project-layers",
        "description": f"{fixture.title}'s layers import downward",
        "severity": "error",
        "layers": [{"name": name, "tag": f"tier-{name}"} for name in fixture.layers],
        "enforce": "top-down",
        "allow_skip": True,
        "edge_kind": "depends_on",
    }


def build_portal(fixture: AdopterFixture, workdir: Path, npm: str) -> BuiltPortal:
    """Do to a copy of *fixture* under *workdir* what an adopter does, step by step.

    A step that fails stops the build; the record says which one and why.
    """
    root = workdir / fixture.project
    shutil.copytree(fixture.source, root)
    for stored in sorted(root.rglob(f"*{STORED_SUFFIX}")):
        stored.rename(stored.with_name(stored.name.removesuffix(STORED_SUFFIX)))
    commit = commit_project(root, origin=fixture.origin)
    built = BuiltPortal(fixture, root, commit)
    project = ("--project", str(root))
    built.steps["init"] = _beadloom("init", "--yes", *project)
    if built.steps["init"].returncode != 0:
        return built
    _declare(root, fixture)
    built.steps["reindex"] = _beadloom("reindex", *project)
    built.steps["docs site"] = _beadloom("docs", "site", *project)
    if built.failed_step() is not None:
        return built
    built.steps["npm ci"] = _run([npm, "ci", "--no-audit", "--no-fund"], built.site)
    if built.steps["npm ci"].returncode == 0:
        built.steps["vitepress build"] = _run([npm, "run", "docs:build"], built.site)
    return built


def this_repositorys_identity() -> tuple[str, ...]:
    """The text that names this repository's portal, read from its own ``site:`` block.

    The title as a page title, the description, the base path, the repository
    address and its owner: none of it may reach an adopter's portal.
    """
    config = yaml.safe_load((REPO_ROOT / ".beadloom" / "config.yml").read_text(encoding="utf-8"))
    site = config["site"]
    repo_url = str(site["repo_url"]).rstrip("/")
    owner = repo_url.split("/")[-2]
    return (
        f"<title>{site['title']}",
        str(site["description"]),
        str(site["base"]),
        repo_url.split("://", 1)[1],
        f"{owner}.github.io",
        f"/{owner}/",
    )

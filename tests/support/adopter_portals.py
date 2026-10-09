"""The adopter fixtures, one per claimed stack, and the portal each one builds.

BDL-076 B3 (``beadloom-hmqn``). The PRD claims the portal works for an adopter on
Python, Go, JS/TS, Java, Kotlin and Swift; BDL-080 S3d (``beadloom-chdx``) adds two
Feature-Sliced frontends, Vue 3 + TypeScript and React Native + TypeScript. Each of
those is a small project under ``tests/fixtures/site/<stack>/``: a few modules with real
imports between them, a README, a ``docs/`` folder and tests in the stack's own
convention. Nothing in a fixture names this repository. A fixture file named like one
of this repository's own tests is stored under :data:`STORED_SUFFIX` and takes its name
back on copy.

:func:`build_portal` does to a copy what an adopter does: commit it to git with an
``origin``, run ``beadloom init``, declare the portal's identity (and, where the
fixture has them, its layers and rules), ``reindex``, ``docs site``, ``npm ci``
and ``vitepress build``. On a Feature-Sliced fixture ``init`` writes the layers
itself, and the adopter declares only the identity. It records every step's exit
code and output rather than raising, so a test names the step that failed.

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

#: The logo an adopter adds after ``init``: a lantern of its own, nothing of Beadloom's.
ADOPTER_LOGO = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" role="img" '
    'aria-label="Lantern Notes"><rect x="7" y="4" width="10" height="16" rx="3" '
    'fill="#e9a23b"/></svg>\n'
)

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
    the adopter adds, as ``rules.yml`` writes them. ``logo`` is the path of a logo
    the adopter adds and declares as ``site.logo`` (BDL-080 S4d), and
    ``powered_by`` is ``site.powered_by``, declared only when it is ``False``.

    BDL-080 S3d: ``layers_by_init`` says that ``init`` writes the layer rule and the
    tags itself (the FSD preset), so the adopter declares no layer rule and ``layers``
    are the ones the portal is expected to serve from it. ``init_exit`` is the exit code
    ``init`` is expected to end with: 1 where the fixture's code breaks the rules
    ``init`` writes beside it on purpose, which ``init`` reports as findings about the
    code (S3c, ``beadloom-5t8d``) and which the portal is expected to draw.
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
    logo: str = ""
    powered_by: bool = True
    layers_by_init: bool = False
    init_exit: int = 0

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
    # The one fixture with a nav logo of its own; the others show none (BDL-080 S4d).
    logo="art/lantern-notes.svg",
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
    # The one fixture that switches the "Powered by Beadloom" footer off (BDL-080 S4d).
    powered_by=False,
    modules=("Sources/BeaconApp", "Sources/BeaconCore", "Sources/BeaconNetwork"),
    imports=(
        ("Sources/BeaconApp", "Sources/BeaconCore"),
        ("Sources/BeaconApp", "Sources/BeaconNetwork"),
        ("Sources/BeaconNetwork", "Sources/BeaconCore"),
    ),
)

#: The six layers of Feature-Sliced Design, top to bottom: what ``init`` writes for both
#: FSD fixtures, read from the methodology and not from the product's preset.
FSD_LAYERS = ("app", "pages", "widgets", "features", "entities", "shared")

#: A Vite + Vue 3 + TypeScript + Pinia storefront in the FSD layout under ``src/``, with
#: two folders from before the move beside the layers (BDL-080 S3d, RFC D6). Its code
#: breaks the rules ``init`` writes twice on purpose (a cross-import inside ``features``
#: and a deep import past ``entities/product``'s index), so ``init`` exits 1 and names them.
VUE_FSD = AdopterFixture(
    stack="vue-fsd",
    project="heron-market",
    title="Heron Market",
    base="/heron-market/",
    repo_url="https://github.com/heron-prints/heron-market",
    origin="https://github.com/heron-prints/heron-market.git",
    tree_route=GITHUB_TREE,
    modules=(
        "src/app",
        "src/app/providers",
        "src/app/styles",
        "src/pages/catalog",
        "src/pages/checkout",
        "src/widgets/product-grid",
        "src/widgets/site-header",
        "src/features/add-to-cart",
        "src/features/apply-coupon",
        "src/entities/cart",
        "src/entities/product",
        "src/shared",
        "src/shared/api",
        "src/shared/config",
        "src/shared/lib",
        "src/shared/ui",
        "src/components",
        "src/stores",
    ),
    # A container's import of its own segment (``src/app/index.ts`` re-exporting
    # ``./providers/setup``) is inside it, and no pair here.
    imports=(
        ("src/app/providers", "src/pages/catalog"),
        ("src/app/providers", "src/pages/checkout"),
        ("src/pages/catalog", "src/widgets/product-grid"),
        ("src/pages/catalog", "src/widgets/site-header"),
        ("src/pages/checkout", "src/entities/cart"),
        ("src/pages/checkout", "src/features/apply-coupon"),
        ("src/pages/checkout", "src/widgets/site-header"),
        ("src/widgets/product-grid", "src/entities/product"),
        ("src/widgets/product-grid", "src/features/add-to-cart"),
        ("src/widgets/site-header", "src/entities/cart"),
        ("src/widgets/site-header", "src/shared/ui"),
        ("src/features/add-to-cart", "src/entities/cart"),
        ("src/features/add-to-cart", "src/shared/ui"),
        ("src/features/apply-coupon", "src/entities/cart"),
        ("src/features/apply-coupon", "src/features/add-to-cart"),
        ("src/features/apply-coupon", "src/shared/lib"),
        ("src/features/apply-coupon", "src/shared/ui"),
        ("src/entities/cart", "src/shared/lib"),
        ("src/entities/product", "src/shared/api"),
        ("src/entities/product", "src/shared/lib"),
        ("src/shared/api", "src/shared/config"),
        ("src/components", "src/shared/ui"),
        ("src/stores", "src/entities/product"),
    ),
    layers=FSD_LAYERS,
    layers_by_init=True,
    init_exit=1,
)

_HAPTICS = "modules/trail-haptics"

#: An Expo + React Native + TypeScript app: Expo Router's ``app/`` at the root, the FSD
#: layers under ``src/``, ``.tsx`` beside ``.jsx`` and ``.js``, platform suffixes, a Babel
#: ``module-resolver`` alias and one local Expo module with a Swift and a Kotlin side
#: (BDL-080 S3d, RFC D6). Its code passes the error rules ``init`` writes and breaks one
#: warn rule (a ``hooks/`` folder in a slice), so ``init`` exits 0.
RN_FSD = AdopterFixture(
    stack="rn-fsd",
    project="moss-trail",
    title="Moss Trail",
    base="/moss-trail/",
    repo_url="https://gitlab.com/moss-outdoors/moss-trail",
    origin="git@gitlab.com:moss-outdoors/moss-trail.git",
    tree_route=GITLAB_TREE,
    modules=(
        "app",
        "src/app",
        "src/app/providers",
        "src/pages/home",
        "src/pages/trail",
        "src/widgets/trail-list",
        "src/features/start-hike",
        "src/entities/trail",
        "src/shared",
        "src/shared/api",
        "src/shared/config",
        "src/shared/lib",
        "src/shared/ui",
        "src/screens",
        _HAPTICS,
        f"{_HAPTICS}/ios",
        f"{_HAPTICS}/android",
    ),
    imports=(
        ("app", "src/app"),
        ("app", "src/pages/home"),
        ("app", "src/pages/trail"),
        ("src/app/providers", "src/shared/api"),
        ("src/pages/home", "src/widgets/trail-list"),
        ("src/pages/trail", "src/entities/trail"),
        ("src/pages/trail", "src/features/start-hike"),
        ("src/widgets/trail-list", "src/entities/trail"),
        ("src/widgets/trail-list", "src/shared/ui"),
        ("src/features/start-hike", _HAPTICS),
        ("src/features/start-hike", "src/entities/trail"),
        ("src/features/start-hike", "src/shared/ui"),
        ("src/entities/trail", "src/shared/api"),
        ("src/entities/trail", "src/shared/lib"),
        ("src/entities/trail", "src/shared/ui"),
        ("src/shared/api", "src/shared/config"),
        ("src/screens", "src/entities/trail"),
    ),
    layers=FSD_LAYERS,
    layers_by_init=True,
)

#: The six stacks BDL-076 claimed, in the PRD's order: the fixtures every baseline measured
#: before BDL-080 S3d added the two FSD frontends was taken on.
SIX_STACKS: tuple[str, ...] = ("python", "go", "typescript", "java", "kotlin", "swift")

#: Every claimed stack, in the PRD's order, then the two FSD frontends (BDL-080 S3d).
FIXTURES_BY_STACK: Mapping[str, AdopterFixture] = {
    fixture.stack: fixture
    for fixture in (PYTHON, GO, TYPESCRIPT, JAVA, KOTLIN, SWIFT, VUE_FSD, RN_FSD)
}

#: The environment variable that names the one part of the slow tests a run takes
#: (``beadloom-m6k7.7``): the ``site-adopters`` job runs each part in a leg of its own.
SLOW_PART_ENV = "BEADLOOM_SLOW_PART"
#: The part of the slow tests that build a project of their own, not a stack's fixture.
PROJECTS_PART = "projects"
#: Every part: each claimed stack's slow tests, then the ones that build no stack's fixture.
SLOW_PARTS: tuple[str, ...] = (*FIXTURES_BY_STACK, PROJECTS_PART)


@dataclass
class Step:
    """One step of a portal build: its exit code, its output and its wall time.

    ``expected`` is the exit code the step is expected to end with: 0 for every step
    but an ``init`` whose fixture breaks the rules it writes (BDL-080 S3d).
    """

    returncode: int
    output: str
    seconds: float
    expected: int = 0


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
        """The first step that did not exit as expected, with its output; ``None`` when all did."""
        for name, step in self.steps.items():
            if step.returncode != step.expected:
                return (
                    f"{name} exited {step.returncode}, expected {step.expected}:\n"
                    f"{step.output[-4000:]}"
                )
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
    if fixture.logo:
        logo = root / fixture.logo
        logo.parent.mkdir(parents=True, exist_ok=True)
        logo.write_text(ADOPTER_LOGO, encoding="utf-8")
        site["logo"] = fixture.logo
    if not fixture.powered_by:
        site["powered_by"] = False
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
    if fixture.layers and not fixture.layers_by_init:
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


def adopt(fixture: AdopterFixture, workdir: Path) -> BuiltPortal:
    """The beadloom half of :func:`build_portal`: copy, commit, init, declare, reindex, docs site.

    Apart from the npm half so that the product code these steps run can be traced
    on its own (``tests/support/slow_test_trace.py``), and the ``site-adopters``
    workflow's paths filter held to it.
    """
    root = workdir / fixture.project
    shutil.copytree(fixture.source, root)
    for stored in sorted(root.rglob(f"*{STORED_SUFFIX}")):
        stored.rename(stored.with_name(stored.name.removesuffix(STORED_SUFFIX)))
    commit = commit_project(root, origin=fixture.origin)
    built = BuiltPortal(fixture, root, commit)
    project = ("--project", str(root))
    built.steps["init"] = _beadloom("init", "--yes", *project)
    built.steps["init"].expected = fixture.init_exit
    if built.failed_step() is not None:
        return built
    _declare(root, fixture)
    built.steps["reindex"] = _beadloom("reindex", *project)
    built.steps["docs site"] = _beadloom("docs", "site", *project)
    return built


def build_portal(fixture: AdopterFixture, workdir: Path, npm: str) -> BuiltPortal:
    """Do to a copy of *fixture* under *workdir* what an adopter does, step by step.

    A step that fails stops the build; the record says which one and why.
    """
    built = adopt(fixture, workdir)
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

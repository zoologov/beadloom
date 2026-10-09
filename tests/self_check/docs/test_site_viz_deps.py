"""Guard the site viz dev/runtime dependency contract (BDL-060 S4 ext, BDL-077 E1).

The interactive maps (LandscapeMap / ArchitectureMap) render with Cytoscape and
are laid out by elkjs, called directly in a Web Worker of the theme's own
(``shared/elk``). Until BDL-077 E1 the layout came through ``cytoscape-elk``,
which ran a nested elkjs 0.9.3 of its own on the page's main thread and needed
``web-worker`` declared for the VitePress dev server; both are gone.

These are the cheap structural guards that catch a regression in that wiring
WITHOUT needing node (``docs:build``, the dev-server boot and the browser cases
under ``site/e2e/`` drive the behaviour):

1. Every runtime dependency the viz needs is declared (``cytoscape``, ``elkjs``),
   ``cytoscape-elk`` is not, the lockfile holds exactly one elkjs, the pinned one,
   and the theme loads elkjs from its worker alone, so that one is the one that runs.
2. The layout runs in a worker Vite bundles: the worker module loads elkjs's own
   worker script, and the client names it the way Vite recognises.
3. Every relative import in the committed theme points at a file that exists
   (a broken relative import is a build/runtime crash, not a Python failure).

BDL-076 A2 moved the theme into Feature-Sliced Design layers, so the structural
guards below name the slice that now holds each piece of wiring. Each one FAILS
rather than skips when its file is missing, because a skipped guard over a moved
file reads exactly like a passing one.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

import pytest

from tests.support.repository_root import REPO_ROOT as _REPO_ROOT

if TYPE_CHECKING:
    from pathlib import Path

# BDL-076 B1 (`beadloom-dfwt`): the scaffold is package data, laid out as it sits
# in a portal; `site/` is the copy `docs site` writes, absent from a fresh checkout.
_SITE = _REPO_ROOT / "src" / "beadloom" / "site_scaffold"
_THEME = _SITE / ".vitepress" / "theme"

# The deps the Cytoscape + ELK viz needs at runtime.
_REQUIRED_VIZ_DEPS = ("cytoscape", "elkjs")
# The adapter that ran a nested elkjs of its own on the main thread (`beadloom-f2we`).
_RETIRED_VIZ_DEPS = ("cytoscape-elk",)
# A module specifier that names elkjs or a file of it, in either kind of quote.
_ELKJS_SPECIFIER = re.compile(r"""["'](elkjs(?:/[^"']*)?)["']""")


def _package_json() -> dict[str, object]:
    path = _SITE / "package.json"
    if not path.exists():
        pytest.skip("the scaffold's package.json is absent in this checkout")
    return json.loads(path.read_text(encoding="utf-8"))


def _declared() -> dict[str, object]:
    pkg = _package_json()
    deps: dict[str, object] = {}
    for section in ("dependencies", "devDependencies"):
        block = pkg.get(section)
        if isinstance(block, dict):
            deps.update(block)
    return deps


def test_viz_deps_declared() -> None:
    """Every runtime dependency of the viz is declared, and the retired adapter is not."""
    deps = _declared()
    missing = [d for d in _REQUIRED_VIZ_DEPS if d not in deps]
    assert not missing, (
        f"the scaffold's package.json is missing viz deps {missing}; "
        "this is the class of gap that crashed the dev server while docs:build "
        "stayed green (BDL-060 S4)."
    )
    retired = [d for d in _RETIRED_VIZ_DEPS if d in deps]
    assert not retired, f"{retired} is declared again; the viewer calls elkjs directly"


def test_the_lock_holds_one_elkjs_the_pinned_one() -> None:
    """No package brings an elkjs of its own: the layout the viewer runs is the pinned one."""
    lock = json.loads((_SITE / "package-lock.json").read_text(encoding="utf-8"))
    elkjs = {
        path: entry.get("version")
        for path, entry in lock["packages"].items()
        if path.split("node_modules/")[-1] == "elkjs"
    }
    assert elkjs == {"node_modules/elkjs": _declared()["elkjs"]}


def test_the_layout_runs_in_a_worker_vite_bundles() -> None:
    """The worker loads elkjs's worker script; the client names it the way Vite bundles it."""
    worker = _read("shared/elk/elk.worker.js")
    assert 'import "elkjs/lib/elk-worker.min.js";' in worker
    client = _read("shared/elk/layOut.js")
    assert 'new Worker(new URL("./elk.worker.js", import.meta.url), { type: "module" })' in client


def test_the_theme_reaches_elkjs_only_through_its_worker() -> None:
    """The one elkjs the lock holds is the one that runs: no other module loads a build of it."""
    importers = {
        path.relative_to(_THEME).as_posix(): specifiers
        for path in _theme_sources()
        if (specifiers := _ELKJS_SPECIFIER.findall(path.read_text(encoding="utf-8")))
    }

    assert importers == {"shared/elk/elk.worker.js": ["elkjs/lib/elk-worker.min.js"]}


def _local_imports(source: str) -> list[str]:
    """Relative ``import``/``export ... from "./..."`` specifiers in a JS/Vue source."""
    return re.findall(r"""(?:import|export)\s+[^;]*?from\s+["'](\.[^"']+)["']""", source)


def _theme_sources() -> list[Path]:
    return sorted(
        path for path in _THEME.rglob("*") if path.suffix in {".js", ".vue"} and path.is_file()
    )


def _read(relative: str) -> str:
    path = _THEME / relative
    assert path.exists(), f"{relative} is missing from the theme"
    return path.read_text(encoding="utf-8")


def test_the_theme_has_sources() -> None:
    """The guards below read the theme; an empty theme would make them vacuous."""
    assert len(_theme_sources()) > 30


@pytest.mark.parametrize("path", _theme_sources(), ids=lambda p: str(p.relative_to(_THEME)))
def test_every_relative_import_in_the_theme_resolves(path: Path) -> None:
    """Each relative import of a theme file points at a real file."""
    for spec in _local_imports(path.read_text(encoding="utf-8")):
        resolved = (path.parent / spec).resolve()
        assert resolved.exists(), (
            f"{path.relative_to(_THEME)} imports {spec!r} which does not resolve to a file "
            f"({resolved}); a broken import is a dev/runtime crash."
        )


def test_the_vitepress_entry_hands_over_the_app_layer() -> None:
    """VitePress looks for `theme/index.js`; it re-exports the `app` layer."""
    assert 'export { default } from "./app/index.js"' in _read("index.js")


def test_architecture_component_registered_in_theme() -> None:
    """ArchitectureMap is registered globally so the generated page can mount it."""
    source = _read("app/index.js")
    assert 'import { ArchitectureMap } from "../pages/architecture/index.js"' in source
    assert "ArchitectureMap," in source
    assert "app.component(name, component)" in source


def test_the_layout_hands_each_node_its_lane() -> None:
    """ELK partitioning is on, and each node's lane reaches ELK as its partition.

    A node's lane is the rank of its layer among siblings of one rule (BDL-080
    S1c), and a box that holds a scoped rule's layer boxes stacks them with lane
    edges, since ELK reads no partition of a node inside a box.
    """
    layout = _read("shared/elk/graph.js")
    assert '"elk.partitioning.activate": "true"' in layout
    assert '"elk.direction": "DOWN"' in layout
    assert "layoutOptions: laneOf(node)" in layout
    assert '"elk.partitioning.partition"' in layout
    assert "root.edges.push(...laneEdgesOf(nodes, taken))" in layout
    elements = _read("widgets/graph-viewer/lib/elements.js")
    assert "data.partition = lanes.get(node.id)" in elements
    canvas = _read("widgets/graph-viewer/model/canvasLayout.js")
    assert 'partition: node.data("partition")' in canvas
    assert "stack: node.data(STACK_LANES) === true" in canvas


def test_the_layout_answers_in_root_coordinates() -> None:
    """Every box and every edge section comes back absolute, not relative to its container."""
    layout = _read("shared/elk/graph.js")
    assert '"elk.json.shapeCoords": "ROOT"' in layout
    assert '"elk.json.edgeCoords": "ROOT"' in layout


def test_no_css_variable_reaches_cytoscape() -> None:
    """Cytoscape rejects `var(...)` and draws its fallback grey; the stylesheet has none."""
    code = re.sub(r"//[^\n]*", "", _read("widgets/graph-viewer/lib/stylesheet.js"))
    assert "var(" not in code
    assert "tokens.text1" in code


def test_violation_edges_have_their_own_style() -> None:
    """A depends_on the layer rule judged against the layers is drawn as a violation."""
    kinds = _read("entities/graph-edge/model/edgeKinds.js")
    assert 'edge.kind === "depends_on" && edge.violation === true' in kinds
    assert "[VIOLATION_KEY]: {" in kinds
    assert 'edge[styleKey = "violation"]' in _read("widgets/graph-viewer/lib/stylesheet.js")


def test_the_viewer_renders_a_legend_derived_from_the_data() -> None:
    """The legend lists the layers, a node in no layer and the drawn edge kinds, off the data."""
    viewer = _read("widgets/graph-viewer/ui/GraphViewer.vue")
    assert '<LayerLegend :layers="layers" :unlayered="unlayered" />' in viewer
    assert "hasUnlayeredNode(" in viewer
    assert '<EdgeLegend :keys="legendKeys"' in viewer
    assert "legendKeysOf(" in viewer


def test_closing_the_card_clears_the_selection() -> None:
    """Closing the card clears the selection (no highlight left behind)."""
    viewer = _read("widgets/graph-viewer/ui/GraphViewer.vue")
    assert "function clearSelection()" in viewer
    assert 'state.focus = "";' in viewer
    # The card is a widget of its own since BDL-076 A3; the page composes it.
    assert "emit('close')" in _read("widgets/node-card/ui/NodeCard.vue")
    assert '@close="close"' in _read("pages/architecture/ui/ArchitectureMap.vue")


def test_full_screen_covers_the_viewers_whole_space() -> None:
    """The element that goes full screen is the viewer's root, with a CSS fallback."""
    assert "requestFullscreen" in _read("features/fullscreen/model/useFullscreen.js")
    viewer = _read("widgets/graph-viewer/ui/GraphViewer.vue")
    assert "useFullscreen(root" in viewer


def test_filters_hide_rather_than_remove_and_keep_containers() -> None:
    """Filters HIDE nodes, keep the containers of shown nodes, and re-fit to what shows."""
    canvas = _read("widgets/graph-viewer/model/useGraphCanvas.js")
    # A class, set only where it changes (`setClass`): the node stays in the graph, not drawn.
    assert 'setClass(node, "is-hidden"' in canvas
    assert 'display: "none"' in _read("widgets/graph-viewer/lib/stylesheet.js")
    assert "withAncestors(" in _read("features/filter-graph/lib/visibleIds.js")
    navigation = _read("features/navigate-graph/model/useGraphNavigation.js")
    assert 'cy.elements(":visible")' in navigation


def test_landscape_protocol_card_only_for_real_contracts() -> None:
    """A plain dependency gets a Dependency entry with NO Protocol field;
    only a real amqp/graphql contract shows the protocol card (never 'unknown').

    Since BDL-076 A4 the landscape card lists a service's contracts, and the
    declared-protocol test lives in the landscape-data entity.
    """
    src = _read("pages/landscape/ui/LandscapeCard.vue")
    assert 'v-if="isDeclaredContract(contract)"' in src
    assert "amqp" in src and "graphql" in src
    # The simpler Dependency branch exists.
    assert "Dependency" in src
    # The old unconditional 'unknown' protocol fallback is gone.
    assert 'contract.protocol || "unknown"' not in src
    contracts = _read("entities/landscape-data/model/contracts.js")
    assert 'DECLARED_PROTOCOLS = Object.freeze(["amqp", "graphql"])' in contracts

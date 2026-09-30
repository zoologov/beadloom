"""Each browser test of this repository's site binds to the slice it drives.

BDL-076 R1 finding m5. The Playwright specs under ``site/e2e`` bound to
``vitepress-site`` through its ``tests:`` prefix, so every slice of the viewer
carried a count of 0 tests and the impact mode marked each one "no bound tests"
while the specs exercised it. A spec binds to one node, so each slice declares
the spec that drives it in its own ``tests:`` list — the binding beadloom
already has, and the most specific declaration wins over the site's prefix. A
slice no spec drives keeps a count of 0, which is then true.

The table below is the decision, one row per spec. A spec added under
``site/e2e`` without a row fails here, so a new spec is placed on purpose rather
than falling back to the site node. The configuration and graph are read from
``REPO_ROOT``, never from the index.
"""

from __future__ import annotations

import pytest

from beadloom.context_oracle.test_binding import PLACEMENT_OVERRIDE, bind_test_file
from beadloom.context_oracle.test_layout import load_test_layout
from beadloom.infrastructure.scan_paths import resolve_scan_paths
from beadloom.onboarding.graph_files import each_graph_file
from tests.support.repository_root import REPO_ROOT

#: The browser tests' folder, relative to the repository root.
_E2E = "site/e2e"

#: Each spec and the slice whose behaviour it drives.
SPEC_SLICE = {
    "card.spec.js": "site-node-card",
    "colours.spec.js": "site-graph-viewer",
    "data-version.spec.js": "site-architecture-data",
    "diagram-links.spec.js": "site-diagram-viewer",
    "edges.spec.js": "site-graph-edge",
    "filters.spec.js": "site-filter-graph",
    "fullscreen.spec.js": "site-fullscreen",
    "graph-viewer-instances.spec.js": "site-graph-viewer",
    "impact.spec.js": "site-impact-view",
    "landscape.spec.js": "site-landscape-page",
    "layers.spec.js": "site-layer",
    "navigation.spec.js": "site-navigate-graph",
    "neighbourhood.spec.js": "site-select-neighbourhood",
    "node-page.spec.js": "site-architecture-page",
    "node-status.spec.js": "site-graph-node",
    "shell-command.spec.js": "site-shared",
    "url-state.spec.js": "site-url-state",
}


def _node_sources_and_overrides() -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Every node's ``source`` and every ``tests:`` entry, read from the graph files."""
    sources: list[tuple[str, str]] = []
    overrides: list[tuple[str, str]] = []
    for _path, data in each_graph_file(REPO_ROOT / ".beadloom" / "_graph"):
        for node in data.get("nodes") or []:
            ref_id = str(node.get("ref_id", ""))
            if node.get("source"):
                sources.append((ref_id, str(node["source"])))
            overrides.extend((ref_id, str(entry)) for entry in node.get("tests") or [])
    return sources, overrides


def test_every_spec_on_disk_has_a_slice() -> None:
    specs = {path.name for path in (REPO_ROOT / _E2E).glob("*.spec.js")}

    assert specs == set(SPEC_SLICE)


@pytest.mark.parametrize(("spec", "slice_ref"), sorted(SPEC_SLICE.items()))
def test_the_spec_binds_to_its_slice_by_declaration(spec: str, slice_ref: str) -> None:
    layout, _ = load_test_layout(REPO_ROOT)
    sources, overrides = _node_sources_and_overrides()

    binding = bind_test_file(
        f"{_E2E}/{spec}",
        code_files=(),
        scan_paths=resolve_scan_paths(REPO_ROOT),
        node_sources=sources,
        overrides=overrides,
        layout=layout,
    )

    assert (binding.ref_id, binding.placement) == (slice_ref, PLACEMENT_OVERRIDE)

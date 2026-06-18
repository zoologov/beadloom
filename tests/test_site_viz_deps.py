"""Guard the site viz dev/runtime dependency contract (BDL-060 S4 ext).

The interactive maps (LandscapeMap / ArchitectureMap) render with Cytoscape +
`cytoscape-elk`, and `cytoscape-elk` pulls in `elkjs`, whose layout runs in a
**web worker**. A prior slice shipped a viz that built fine (`docs:build` green)
yet crashed under the VitePress **dev** server because the worker dependency
(`web-worker`) was not declared — `docs:build` alone masked it.

These are the cheap structural guards that catch that class WITHOUT needing node
(the full `docs:build` + dev-server boot are run in the slice's VERIFY step):

1. Every runtime dependency the viz worker path needs is declared in
   ``site/package.json`` (``cytoscape`` / ``cytoscape-elk`` / ``elkjs`` /
   ``web-worker``) — the exact gap the dev-only crash slipped through.
2. The committed Vue components reference only theme/composable modules that
   actually exist (a broken relative import is a build/runtime crash, not a
   Python failure) — the architecture view reuses the SAME Cytoscape+ELK stack.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SITE = _REPO_ROOT / "site"
_THEME = _SITE / ".vitepress" / "theme"

# The deps the Cytoscape+ELK viz needs at runtime — INCLUDING `web-worker`, the
# elkjs worker shim whose absence was the dev-only crash `docs:build` masked.
_REQUIRED_VIZ_DEPS = ("cytoscape", "cytoscape-elk", "elkjs", "web-worker")


def _package_json() -> dict[str, object]:
    path = _SITE / "package.json"
    if not path.exists():
        pytest.skip("site/package.json absent in this checkout")
    return json.loads(path.read_text(encoding="utf-8"))


def test_viz_worker_deps_declared() -> None:
    """Every Cytoscape+ELK worker-path dependency is declared (incl. web-worker)."""
    pkg = _package_json()
    deps = {}
    for section in ("dependencies", "devDependencies"):
        block = pkg.get(section)
        if isinstance(block, dict):
            deps.update(block)
    missing = [d for d in _REQUIRED_VIZ_DEPS if d not in deps]
    assert not missing, (
        f"site/package.json is missing viz worker deps {missing}; "
        "this is the class of gap that crashed the dev server while docs:build "
        "stayed green (BDL-060 S4)."
    )


def _local_imports(source: str) -> list[str]:
    """Relative ``import ... from "./..."`` specifiers in a JS/Vue source."""
    return re.findall(r"""import\s+[^;]*?from\s+["'](\.[^"']+)["']""", source)


@pytest.mark.parametrize("component", ["ArchitectureMap.vue", "LandscapeMap.vue"])
def test_viz_component_local_imports_resolve(component: str) -> None:
    """The viz component's relative theme/composable imports point at real files."""
    path = _THEME / "components" / component
    if not path.exists():
        pytest.skip(f"{component} absent in this checkout")
    source = path.read_text(encoding="utf-8")
    for spec in _local_imports(source):
        resolved = (path.parent / spec).resolve()
        assert resolved.exists(), (
            f"{component} imports {spec!r} which does not resolve to a file "
            f"({resolved}); a broken import is a dev/runtime crash."
        )


def test_architecture_component_registered_in_theme() -> None:
    """ArchitectureMap is registered globally so the generated page can mount it."""
    index = _THEME / "index.js"
    if not index.exists():
        pytest.skip("theme/index.js absent in this checkout")
    source = index.read_text(encoding="utf-8")
    assert "ArchitectureMap" in source
    assert 'app.component("ArchitectureMap"' in source

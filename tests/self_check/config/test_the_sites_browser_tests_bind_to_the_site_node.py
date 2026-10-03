"""This repository's site theme is scanned, and its future browser tests bind to its node.

BDL-076 A0 (`beadloom-kcwz`). The theme under ``site/.vitepress/theme`` joined the
scan paths, and ``.beadloom/config.yml`` declares where the Playwright tests of
A5 will live before any of them exists. A declaration nothing reads is the
failure this module guards: the day A5 writes ``site/e2e/viewer.spec.js``, that
file must be read as a test and bound to ``vitepress-site``, not counted
unplaced. The product behaviour — roots, patterns, the ``tests:`` override — is
judged over projects on disk elsewhere; this module holds the claims about this
repository.

BDL-076 B1 (``beadloom-dfwt``) moved the theme and the browser tests with the rest
of the scaffold into the package, ``src/beadloom/site_scaffold/``: the theme is
scanned because ``src`` is, and ``site/`` is the output ``docs site`` writes. The
claims below follow the files; none of them was loosened.

It reads the tracked configuration and graph through ``REPO_ROOT``, never the
index. It carries the ``self_check`` marker by its folder (see
``tests/conftest.py``).
"""

from __future__ import annotations

from beadloom.context_oracle.test_binding import PLACEMENT_OVERRIDE, bind_test_file
from beadloom.context_oracle.test_layout import load_test_layout
from beadloom.infrastructure.scan_paths import resolve_scan_paths
from beadloom.onboarding.graph_files import each_graph_file
from tests.support.repository_root import REPO_ROOT

#: The node that owns the site theme.
_SITE_NODE = "vitepress-site"
#: The theme, where the package ships it.
_THEME = "src/beadloom/site_scaffold/.vitepress/theme"
#: The browser tests' root, where the package ships them.
_E2E_ROOT = "src/beadloom/site_scaffold/e2e"
#: A browser test as A5 will name it; it does not have to exist.
_BROWSER_TEST = f"{_E2E_ROOT}/viewer.spec.js"


def _node_sources_and_overrides() -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Every node's ``source`` and every ``tests:`` prefix, read from the graph files."""
    sources: list[tuple[str, str]] = []
    overrides: list[tuple[str, str]] = []
    for _path, data in each_graph_file(REPO_ROOT / ".beadloom" / "_graph"):
        for node in data.get("nodes") or []:
            ref_id = str(node.get("ref_id", ""))
            if node.get("source"):
                sources.append((ref_id, str(node["source"])))
            overrides.extend((ref_id, str(prefix)) for prefix in node.get("tests") or [])
    return sources, overrides


def test_the_site_theme_is_a_scan_path() -> None:
    """The theme sits under a scan path, so its files are read for symbols and imports."""
    scan_paths = resolve_scan_paths(REPO_ROOT)
    assert any(_THEME.startswith(f"{path.rstrip('/')}/") for path in scan_paths), scan_paths


def test_a_playwright_spec_under_site_e2e_is_read_as_a_test() -> None:
    layout, problems = load_test_layout(REPO_ROOT)

    assert problems == []
    assert _E2E_ROOT in layout.roots
    assert layout.framework_of(_BROWSER_TEST) == "playwright"


def test_a_playwright_spec_under_site_e2e_binds_to_the_site_node() -> None:
    layout, _ = load_test_layout(REPO_ROOT)
    sources, overrides = _node_sources_and_overrides()

    binding = bind_test_file(
        _BROWSER_TEST,
        code_files=(),
        scan_paths=resolve_scan_paths(REPO_ROOT),
        node_sources=sources,
        overrides=overrides,
        layout=layout,
    )

    assert (binding.ref_id, binding.placement) == (_SITE_NODE, PLACEMENT_OVERRIDE)

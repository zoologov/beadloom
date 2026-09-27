"""Self-checks of this repository's documents and published site (BDL-074 A3).

Moved out of ``tests/test_site_generator.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import pytest

from tests.support.repository_root import REPO_ROOT
from tests.support.site_links import (
    dead_links,
)


def test_committed_site_tree_has_no_dead_links() -> None:
    """The committed dogfood ``site/`` tree (if present) has no dead links.

    Validates the real generated output `npm run docs:build` consumes, so the
    VitePress dead-link regression is caught without needing node. Skipped on a
    checkout where the dogfood site has not been generated.
    """
    repo_root = REPO_ROOT
    site = repo_root / "site"
    if not (site / "index.md").exists():
        pytest.skip("dogfood site/ not generated in this checkout")
    assert not dead_links(site), f"dead internal links in committed site/: {dead_links(site)}"

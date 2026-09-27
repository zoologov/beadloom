"""Self-checks of this repository's documents and published site (BDL-074 A3).

Moved out of ``tests/test_site_viz_data_guards.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_site_viz_data_guards import (
    _iter_data_links,
    _link_target_exists,
)


@pytest.mark.parametrize("payload", ["architecture.data.json", "landscape.data.json"])
def test_committed_site_viz_data_has_no_dead_links(payload: str) -> None:
    """The real dogfood payload, against the real generated tree.

    Skipped on a checkout where the site has not been generated (``site/`` is
    gitignored), mirroring the markdown guard's contract.
    """
    site = Path(__file__).resolve().parents[3] / "site"
    data_path = site / "public" / payload
    if not (site / "index.md").exists() or not data_path.exists():
        pytest.skip(f"dogfood site/{payload} not generated in this checkout")

    data = json.loads(data_path.read_text("utf-8"))
    dead = [
        (owner, url) for owner, url in _iter_data_links(data) if not _link_target_exists(site, url)
    ]

    assert dead == [], f"dead links in site/public/{payload}: {dead}"


def test_committed_architecture_data_is_referentially_closed() -> None:
    """The real payload's ids all resolve — the pop-up is never empty in the wild.

    The synthetic guards above run on a corpus built to be well-formed. This one
    runs on Beadloom's own graph, where node selection and edge selection are
    separate queries that can drift apart (the builder emits an edge to an id it
    did not include, rather than dropping it).
    """
    site = Path(__file__).resolve().parents[3] / "site"
    data_path = site / "public" / "architecture.data.json"
    if not data_path.exists():
        pytest.skip("dogfood site/public/architecture.data.json not generated")

    data = json.loads(data_path.read_text("utf-8"))
    ids = {n["id"] for n in data["nodes"]}

    dangling = [
        (e["src"], e["dst"], e["kind"])
        for e in data["edges"]
        if e["src"] not in ids or e["dst"] not in ids
    ]
    orphaned = [n["id"] for n in data["nodes"] if n["parent"] and n["parent"] not in ids]
    unknown = sorted(
        {
            ref
            for node in data["nodes"]
            for key in ("depends_on", "depended_on_by")
            for ref in node.get(key, [])
            if ref not in ids
        }
    )

    assert dangling == [], f"edges to ids absent from nodes: {dangling}"
    assert orphaned == [], f"parents absent from nodes: {orphaned}"
    assert unknown == [], f"dependency refs absent from nodes: {unknown}"


def test_committed_landscape_data_is_referentially_closed() -> None:
    """Same closure check for the real landscape payload."""
    site = Path(__file__).resolve().parents[3] / "site"
    data_path = site / "public" / "landscape.data.json"
    if not data_path.exists():
        pytest.skip("dogfood site/public/landscape.data.json not generated")

    data = json.loads(data_path.read_text("utf-8"))
    ids = {n["id"] for n in data["nodes"]}
    known = {c["contract_key"] for c in data["contracts"]}

    dangling = [
        (e["src"], e["dst"]) for e in data["edges"] if e["src"] not in ids or e["dst"] not in ids
    ]
    unresolved = sorted(
        {e["contract_key"] for e in data["edges"] if e.get("contract_key") not in known}
    )
    unknown = sorted(
        {
            participant
            for contract in data["contracts"]
            for key in ("producers", "consumers")
            for participant in contract.get(key, [])
            if participant not in ids
        }
    )

    assert dangling == [], f"edges to ids absent from nodes: {dangling}"
    assert unresolved == [], f"edge contract_keys with no contract: {unresolved}"
    assert unknown == [], f"contract participants absent from nodes: {unknown}"

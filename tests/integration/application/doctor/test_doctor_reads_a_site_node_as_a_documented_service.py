"""`doctor` judges a node declared `kind: site` as the service it is read as.

BDL-080 PRD goal 1, *done when*: "``lint``, ``docs generate`` and ``doctor`` treat it
as one". ``lint`` is held by the graph-loader scenario (a rule written for services
judges the portal) and ``docs generate`` by the doc-generator case (a service
skeleton for a site node). This module takes the path a user takes end to end —
the graph declares the portal ``kind: site``, ``docs generate`` writes its
skeleton, the project is reindexed, ``doctor`` runs — and reads what ``doctor``
reports about the portal: documented, by the page under ``docs/services/``, and no
error anywhere.

The project is ``atlas`` with its portal ``atlas-portal``, not this repository,
whose portal is declared ``kind: service`` directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
import yaml

from beadloom.application.doctor import Check, Severity, run_checks
from beadloom.application.reindex import reindex
from beadloom.infrastructure.db import open_db
from beadloom.onboarding.doc_generator import generate_skeletons

if TYPE_CHECKING:
    from pathlib import Path

ROOT = "atlas"
PORTAL = "atlas-portal"


def _a_project_whose_portal_is_declared(root: Path, kind: str) -> Path:
    nodes: list[dict[str, Any]] = [
        {"ref_id": ROOT, "kind": "service", "summary": "The atlas product."},
        {"ref_id": PORTAL, "kind": kind, "summary": "The atlas portal."},
    ]
    edges = [{"src": PORTAL, "dst": ROOT, "kind": "part_of"}]
    graph_dir = root / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "atlas.yml").write_text(
        yaml.safe_dump({"nodes": nodes, "edges": edges}), encoding="utf-8"
    )
    return root


def _doctor_after_docs_generate(root: Path) -> list[Check]:
    generate_skeletons(root)
    reindex(root)
    conn = open_db(root / ".beadloom" / "beadloom.db")
    try:
        return run_checks(conn, project_root=root)
    finally:
        conn.close()


def _about_the_portal(checks: list[Check]) -> list[str]:
    return [
        c.description for c in checks if c.name == "nodes_without_docs" and PORTAL in c.description
    ]


@pytest.mark.parametrize("kind", ["site", "service"])
def test_doctor_finds_the_portal_documented_by_its_service_skeleton(
    tmp_path: Path, kind: str
) -> None:
    """A site node and a service node get one answer: documented, by a services page."""
    root = _a_project_whose_portal_is_declared(tmp_path / kind, kind)

    checks = _doctor_after_docs_generate(root)

    assert _about_the_portal(checks) == []
    assert (root / "docs" / "services" / f"{PORTAL}.md").is_file()


def test_doctor_reports_no_error_on_a_project_with_a_site_node(tmp_path: Path) -> None:
    root = _a_project_whose_portal_is_declared(tmp_path / "site", "site")

    checks = _doctor_after_docs_generate(root)

    assert [c.description for c in checks if c.severity == Severity.ERROR] == []

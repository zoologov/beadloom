"""This repository's portal shows its own site as a service, by its own layer rule.

BDL-080 PRD goals 1 and 2, measured on this repository rather than on a fixture.
The product's behaviour is held by the scenarios over made-up projects (``atlas``
with ``atlas-portal``, the ``tier-*``/``ui-*`` graph); this module holds the claims
the PRD makes about THIS portal, which no made-up project can make:

- goal 1, *done when*: "the own portal shows the site as a service box with its
  page under ``services/``" — the graph declares ``vitepress-site`` a service,
  part of ``beadloom``, consuming the data ``beadloom`` produces; the generated
  portal writes its page under ``services/``, links it there from the nav, and
  both data files group it with the services.
- goal 2, *done when*: "this portal's site slices are coloured by the FSD rule" —
  the data file carries every ``layers`` rule ``rules.yml`` declares, the FSD rule
  over ``vitepress-site``, and every slice of the site is placed by that rule at
  the rank of the layer its own tag names.

The portal is generated once for the module from the session's snapshot of the
tree (``self_check_snapshot``), into a directory of its own. Generating records a
metrics point in the project it reads, so the snapshot's history file is put back
as it was found. It carries the ``self_check`` marker by its folder.
"""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING, Any

import pytest
import yaml

from beadloom.application.site.generate import generate_site
from beadloom.onboarding.graph_files import each_graph_file
from tests.support.repository_root import REPO_ROOT

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

#: The portal's node in this repository's graph.
SITE = "vitepress-site"
#: The product the portal is part of, and whose data it consumes.
PRODUCT = "beadloom"
#: The rule that stratifies the portal's slices, and its tag prefix.
FSD_RULE = "site-fsd-layers"
FSD_TAG_PREFIX = "fsd-"
#: The rule that stratifies the backend, by name in `rules.yml`.
DDD_RULE = "architecture-layers"

#: A fixed instant for the one wall-clock read `generate_site` makes.
_NOW = "2026-10-08T00:00:00+00:00"
#: The generated VitePress module the nav is written into.
_NAV_MODULE = ".vitepress/config.generated.mjs"
#: Where `generate_site` appends a metrics point, in the project it reads.
_HISTORY = ".beadloom/metrics_history.json"


@pytest.fixture(scope="module")
def portal(self_check_snapshot: Path, tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    """This repository's portal, generated from the snapshot into a directory of its own."""
    out = tmp_path_factory.mktemp("own-portal") / "site"
    history = self_check_snapshot / _HISTORY
    kept = history.read_bytes() if history.is_file() else None
    conn = sqlite3.connect(self_check_snapshot / ".beadloom" / "beadloom.db")
    conn.row_factory = sqlite3.Row
    try:
        generate_site(conn, out, project_root=self_check_snapshot, now_ts=_NOW)
    finally:
        conn.close()
        if kept is None:
            history.unlink(missing_ok=True)
        else:
            history.write_bytes(kept)
    yield out


def _data(portal: Path, name: str) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads((portal / "public" / name).read_text(encoding="utf-8"))
    return loaded


def _nodes(portal: Path, name: str) -> dict[str, dict[str, Any]]:
    return {str(node["id"]): node for node in _data(portal, name)["nodes"]}


def _graph_nodes_and_edges() -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Every node and edge this repository's graph files declare, read from the files."""
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    for _path, data in each_graph_file(REPO_ROOT / ".beadloom" / "_graph"):
        for node in data.get("nodes") or []:
            nodes[str(node.get("ref_id", ""))] = node
        edges.extend(edge for edge in data.get("edges") or [] if isinstance(edge, dict))
    return nodes, edges


def _declared_layer_rules() -> dict[str, list[str]]:
    """Each `layers` rule `rules.yml` declares, by name, with its tags top to bottom."""
    rules = yaml.safe_load((REPO_ROOT / ".beadloom/_graph/rules.yml").read_text(encoding="utf-8"))
    return {
        str(rule["name"]): [str(layer["tag"]) for layer in rule["layers"]]
        for rule in rules["rules"]
        if "layers" in rule
    }


class TestTheGraphDeclaresTheSiteAService:
    """Goal 1: the declaration the portal is drawn from."""

    def test_the_site_is_declared_a_service_tagged_as_one(self) -> None:
        nodes, _ = _graph_nodes_and_edges()

        site = nodes[SITE]

        assert (site["kind"], site.get("tags")) == ("service", ["layer-service"])

    def test_the_site_is_part_of_the_product(self) -> None:
        _, edges = _graph_nodes_and_edges()

        parents = {e["dst"] for e in edges if e["src"] == SITE and e["kind"] == "part_of"}

        assert parents == {PRODUCT}

    def test_the_product_produces_the_contract_the_site_consumes(self) -> None:
        """The data files are a declared contract: one key, a producer and a consumer."""
        _, edges = _graph_nodes_and_edges()

        def contracts(src: str, dst: str, kind: str) -> set[tuple[str, str]]:
            return {
                (e["contract"]["protocol"], e["contract"]["message_type"])
                for e in edges
                if (e["src"], e["dst"], e["kind"]) == (src, dst, kind) and e.get("contract")
            }

        produced = contracts(PRODUCT, SITE, "produces")
        consumed = contracts(SITE, PRODUCT, "consumes")

        assert produced
        assert produced == consumed


class TestThePortalPlacesTheSiteWithTheServices:
    """Goal 1, done when: a service box with its page under `services/`."""

    def test_the_sites_page_is_under_services_and_none_under_other(self, portal: Path) -> None:
        assert (portal / "services" / f"{SITE}.md").is_file()
        assert not (portal / "other" / f"{SITE}.md").exists()

    def test_the_nav_links_the_site_under_services(self, portal: Path) -> None:
        nav = (portal / _NAV_MODULE).read_text(encoding="utf-8")

        assert f'link: "/services/{SITE}"' in nav
        assert f'link: "/other/{SITE}"' not in nav

    @pytest.mark.parametrize("data_file", ["architecture.data.json", "landscape.data.json"])
    def test_a_data_file_groups_the_site_with_the_services(
        self, portal: Path, data_file: str
    ) -> None:
        assert _nodes(portal, data_file)[SITE]["group"] == "services"

    def test_the_architecture_data_file_draws_the_site_as_a_service_box(
        self, portal: Path
    ) -> None:
        """A box: a service the slices are part of, placed by the backend's rule."""
        nodes = _nodes(portal, "architecture.data.json")

        site = nodes[SITE]
        parts = [node for node in nodes.values() if node.get("parent") == SITE]

        assert (site["kind"], site["parent"]) == ("service", PRODUCT)
        assert (site["layer_rule"], site["layer_rule_rank"]) == (DDD_RULE, 0)
        assert len(parts) >= 2, f"{len(parts)} part(s) of {SITE}: not a box"


class TestThePortalDrawsEveryLayerRule:
    """Goal 2, done when: the site slices are coloured by the FSD rule."""

    def test_the_data_file_carries_every_layer_rule_rules_yml_declares(self, portal: Path) -> None:
        declared = _declared_layer_rules()

        drawn = {
            rule["name"]: [
                layer["tag"] for layer in sorted(rule["layers"], key=lambda x: x["rank"])
            ]
            for rule in _data(portal, "architecture.data.json")["layer_rules"]
        }

        assert len(declared) >= 2, f"{len(declared)} layers rule(s) in rules.yml"
        assert drawn == declared

    def test_each_rule_is_drawn_over_the_container_it_stratifies(self, portal: Path) -> None:
        rules = _data(portal, "architecture.data.json")["layer_rules"]

        scopes = {rule["name"]: rule["scope"] for rule in rules}

        assert scopes == {DDD_RULE: PRODUCT, FSD_RULE: SITE}

    def test_the_fsd_rules_layers_carry_their_names_as_tokens(self, portal: Path) -> None:
        (fsd,) = [
            r
            for r in _data(portal, "architecture.data.json")["layer_rules"]
            if r["name"] == FSD_RULE
        ]

        tokens = [layer["token"] for layer in sorted(fsd["layers"], key=lambda x: x["rank"])]

        assert tokens == ["app", "pages", "widgets", "features", "entities", "shared"]

    def test_every_slice_of_the_site_is_placed_by_the_fsd_rule_at_its_own_tags_rank(
        self, portal: Path
    ) -> None:
        data = _data(portal, "architecture.data.json")
        (fsd,) = [r for r in data["layer_rules"] if r["name"] == FSD_RULE]
        rank_of_tag = {layer["tag"]: layer["rank"] for layer in fsd["layers"]}
        slices = [n for n in data["nodes"] if n.get("parent") == SITE]

        placed = {n["id"]: (n.get("layer_rule"), n.get("layer_rule_rank")) for n in slices}
        by_own_tag = {
            n["id"]: (FSD_RULE, rank_of_tag[tag])
            for n in slices
            for tag in n.get("tags") or []
            if tag in rank_of_tag
        }

        assert len(slices) >= 6, f"{len(slices)} slice(s) of {SITE}"
        assert placed == by_own_tag

    def test_the_fsd_rule_places_a_slice_in_each_of_its_six_layers(self, portal: Path) -> None:
        """Six layers drawn in six tones need a slice in each to be seen."""
        data = _data(portal, "architecture.data.json")

        ranks = {n["layer_rule_rank"] for n in data["nodes"] if n.get("layer_rule") == FSD_RULE}

        assert ranks == set(range(6))

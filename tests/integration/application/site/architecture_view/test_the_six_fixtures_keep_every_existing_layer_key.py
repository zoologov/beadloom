"""Every adopter fixture's data file keeps its existing layer keys; only new keys are added.

BDL-080 S1b (``beadloom-kgh6``), RFC D2: the data file grows ``layer_rules`` and
each node ``layer_rule`` / ``layer_rule_rank``, and schema 2 stays — so no key a
viewer already reads may change its value on a project that declares one layer
rule or none. Each stack's fixture is adopted as an adopter adopts it (copy,
commit, ``init``, the declarations of :mod:`tests.support.adopter_portals`,
``reindex``, ``docs site``; no npm), and its data file is compared against the
values below.

**The values were MEASURED, not written from the product.** They are the data
files' layer keys as the code before this bead (``7f262f5f``) wrote them,
generated from the same six fixtures on 2026-10-08. The full data files were
compared too, with the commit and the build instant normalised and the three
new keys removed: identical for all six. The two FSD fixtures BDL-080 S3d
(``beadloom-chdx``) added came after and have no measurement before this bead.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest

from tests.support.adopter_portals import FIXTURES_BY_STACK, SIX_STACKS, adopt

if TYPE_CHECKING:
    from pathlib import Path

#: The top-level and node keys of schema 2 before this bead, as measured.
OLD_TOP_KEYS = {
    "beadloom_version",
    "edges",
    "generated_at",
    "layer_order",
    "layers",
    "nodes",
    "schema_version",
    "scope",
}
OLD_NODE_KEYS = {
    "activity",
    "debt",
    "depended_on_by",
    "depends_on",
    "doc_links",
    "doc_status",
    "docs",
    "findings",
    "group",
    "id",
    "kind",
    "label",
    "layer",
    "layer_rank",
    "lifecycle",
    "lint_clean",
    "parent",
    "public_symbols",
    "source",
    "source_url",
    "summary",
    "symbols",
    "tags",
    "tests",
    "url",
    "used_by",
    "uses",
}


def _layers(*names: str) -> list[dict[str, object]]:
    return [
        {"name": name, "rank": rank, "tag": f"tier-{name}", "token": f"tier-{name}"}
        for rank, name in enumerate(names)
    ]


#: Per stack: ``layers``, ``layer_order``, each node's ``(layer, layer_rank)`` and
#: each judged ``depends_on`` edge's ``violation``, as measured before this bead.
MEASURED: dict[str, dict[str, Any]] = {
    "go": {
        "layers": _layers("entry", "transport", "domain", "storage"),
        "layer_order": "top-down",
        "nodes": {
            "api": ("tier-transport", 1),
            "billing": ("tier-domain", 2),
            "catalog": ("tier-domain", 2),
            "storage": ("tier-storage", 3),
            "tidewater": ("", None),
            "tidewater-service": ("tier-entry", 0),
        },
        "violations": {
            ("api", "billing"): False,
            ("api", "catalog"): False,
            ("billing", "catalog"): True,
            ("catalog", "storage"): False,
            ("tidewater-service", "api"): False,
            ("tidewater-service", "catalog"): False,
            ("tidewater-service", "storage"): False,
        },
    },
    "typescript": {
        "layers": _layers("interface", "data", "core"),
        "layer_order": "top-down",
        "nodes": {
            "accounts": ("tier-data", 1),
            "accounts-session": ("", 1),
            "accounts-users": ("", 1),
            "lantern-notes": ("", None),
            "notes": ("", None),
            "notes-api": ("tier-interface", 0),
            "notes-model": ("tier-core", 2),
            "notes-store": ("tier-data", 1),
            "reports": ("", None),
            "reports-digest": ("tier-interface", 0),
        },
        "violations": {
            ("accounts-session", "accounts-users"): False,
            ("notes-api", "accounts-session"): False,
            ("notes-api", "notes-model"): False,
            ("notes-api", "notes-store"): False,
            ("notes-model", "notes-store"): True,
            ("notes-store", "notes-model"): False,
            ("reports-digest", "notes-store"): False,
        },
    },
    "python": {
        "layers": [],
        "layer_order": "",
        "nodes": dict.fromkeys(
            (
                "parcel-desk",
                "parceldesk",
                "parceldesk-api",
                "parceldesk-billing",
                "parceldesk-storage",
            ),
            ("", None),
        ),
        "violations": {},
    },
    "java": {
        "layers": [],
        "layer_order": "",
        "nodes": dict.fromkeys(
            ("model", "quarry-ledger", "repository", "service", "web"), ("", None)
        ),
        "violations": {},
    },
    "kotlin": {
        "layers": [],
        "layer_order": "",
        "nodes": dict.fromkeys(("geo", "orchard-routes", "planner", "routing"), ("", None)),
        "violations": {},
    },
    "swift": {
        "layers": [],
        "layer_order": "",
        "nodes": dict.fromkeys(
            ("BeaconApp", "BeaconCore", "BeaconNetwork", "beacon-kit"), ("", None)
        ),
        "violations": {},
    },
}


def _data_file(stack: str, workdir: Path) -> dict[str, Any]:
    built = adopt(FIXTURES_BY_STACK[stack], workdir)
    assert built.failed_step() is None, built.failed_step()
    (path,) = built.root.rglob("public/architecture.data.json")
    return dict(json.loads(path.read_text(encoding="utf-8")))


def test_every_stack_is_measured() -> None:
    assert set(MEASURED) == set(SIX_STACKS)


@pytest.mark.parametrize("stack", sorted(SIX_STACKS))
def test_the_existing_layer_keys_are_unchanged_and_only_new_keys_are_added(
    stack: str, tmp_path: Path
) -> None:
    data = _data_file(stack, tmp_path)
    measured = MEASURED[stack]

    # BDL-080 S4a (`beadloom-5pxv`) adds `lint`, lint's reach over the project, and S4c
    # (`beadloom-e1xo`) `source_ref`, the revision the source links name.
    assert set(data) == OLD_TOP_KEYS | {"layer_rules", "lint", "source_ref"}
    assert data["schema_version"] == 2
    for node in data["nodes"]:
        assert set(node) == OLD_NODE_KEYS | {"layer_rule", "layer_rule_rank"}, node["id"]

    assert data["layers"] == measured["layers"]
    assert data["layer_order"] == measured["layer_order"]
    assert {n["id"]: (n["layer"], n["layer_rank"]) for n in data["nodes"]} == measured["nodes"]
    assert {
        (e["src"], e["dst"]): e["violation"] for e in data["edges"] if "violation" in e
    } == measured["violations"]


@pytest.mark.parametrize("stack", sorted(SIX_STACKS))
def test_with_one_rule_or_none_the_new_keys_repeat_the_first_rules_answer(
    stack: str, tmp_path: Path
) -> None:
    data = _data_file(stack, tmp_path)
    rules = data["layer_rules"]

    assert [rule["name"] for rule in rules] == (["project-layers"] if data["layers"] else [])
    for node in data["nodes"]:
        placed = node["layer_rank"] is not None
        assert node["layer_rule"] == ("project-layers" if placed else ""), node["id"]
        assert node["layer_rule_rank"] == node["layer_rank"], node["id"]
    for rule in rules:
        assert [layer["tag"] for layer in rule["layers"]] == [
            layer["tag"] for layer in data["layers"]
        ]
        assert [layer["token"] for layer in rule["layers"]] == [
            layer["name"] for layer in data["layers"]
        ]

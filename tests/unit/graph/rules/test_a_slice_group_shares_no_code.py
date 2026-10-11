"""``slice_shape``: a slice group shares no code (BDL-082 S1b).

feature-sliced.design, *Slice groups*: "Closely related slices can be structurally grouped
in a folder, but they should exercise the same isolation rules as other slices — there
should be no code sharing in that folder." A group has no node of its own (RFC D2): it is
read from the slices' sources, a folder between a sliced layer's folder and the slices in
it that no node claims. A code file at its top is a finding.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from beadloom.graph.rules.slices import evaluate_slice_shape_rules
from beadloom.graph.rules.types import SliceShapeRule
from tests.support.in_memory_graph import open_graph

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

RULE = SliceShapeRule(
    name="fsd-slice-shape", description="", tags=("fsd-features", "fsd-entities")
)


def _graph(root: Path, nodes: dict[str, str], *files: str) -> sqlite3.Connection:
    for rel in files:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x\n", encoding="utf-8")
    conn = open_graph()
    for ref_id, source in nodes.items():
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source, extra) VALUES (?, ?, ?, ?, ?)",
            (ref_id, "component", ref_id, source, json.dumps({"tags": ["fsd-features"]})),
        )
    return conn


_GROUPED = {
    "features-auth-login": "src/features/auth/login/",
    "features-auth-register": "src/features/auth/register/",
    "features-cart": "src/features/cart/",
}
_FILES = (
    "src/features/auth/login/index.ts",
    "src/features/auth/register/index.ts",
    "src/features/cart/index.ts",
)


def test_a_group_holding_only_its_slices_is_in_shape(tmp_path: Path) -> None:
    conn = _graph(tmp_path, _GROUPED, *_FILES, "src/features/auth/README.md")

    assert evaluate_slice_shape_rules(conn, [RULE], project_root=tmp_path) == []


def test_a_code_file_at_the_top_of_a_group_is_a_finding(tmp_path: Path) -> None:
    conn = _graph(tmp_path, _GROUPED, *_FILES, "src/features/auth/shared.ts")

    (finding,) = evaluate_slice_shape_rules(conn, [RULE], project_root=tmp_path)

    assert finding.file_path == "src/features/auth/shared.ts"
    assert finding.from_ref_id is None
    assert "'src/features/auth/'" in finding.message
    assert "'shared.ts'" in finding.message
    assert "a group shares no code" in finding.message
    assert "features-auth-login, features-auth-register" in finding.message
    assert finding.remediation is not None


def test_a_group_of_one_slice_is_still_a_group(tmp_path: Path) -> None:
    conn = _graph(
        tmp_path,
        {"features-auth-login": "src/features/auth/login/"},
        "src/features/auth/login/index.ts",
        "src/features/auth/index.ts",
    )

    (finding,) = evaluate_slice_shape_rules(conn, [RULE], project_root=tmp_path)

    assert "'index.ts'" in finding.message
    assert "a group shares no code" in finding.message


def test_the_layer_folder_is_no_group(tmp_path: Path) -> None:
    # A file at the top of `features/` is beside every slice of the layer, not in a group.
    conn = _graph(tmp_path, _GROUPED, *_FILES, "src/features/registry.ts")

    assert evaluate_slice_shape_rules(conn, [RULE], project_root=tmp_path) == []


def test_slices_under_no_layer_folder_name_no_group(tmp_path: Path) -> None:
    # Without a layer folder above them the rule cannot tell a group from a layer.
    conn = _graph(
        tmp_path,
        {"web-a": "web/parts/a/", "web-b": "web/parts/b/"},
        "web/parts/a/index.ts",
        "web/parts/b/index.ts",
        "web/parts/glue.ts",
    )

    assert evaluate_slice_shape_rules(conn, [RULE], project_root=tmp_path) == []

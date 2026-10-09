"""``slice_shape``: a slice's top holds its segments and its index (BDL-080 S3c).

FSD gives a slice its shape, not a size: the standard segments ``ui model lib api config``
and a public API in ``index``. A folder of another name at a slice's top, or a code file
beside the segments that is not its index, is a finding.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rules import evaluate_all
from beadloom.graph.rules.liveness import inert_rules
from beadloom.graph.rules.loader import load_rules
from beadloom.graph.rules.slices import evaluate_slice_shape_rules
from beadloom.graph.rules.types import DEFAULT_SLICE_SEGMENTS, SliceShapeRule
from tests.support.in_memory_graph import open_graph

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

RULE = SliceShapeRule(name="fsd-slice-shape", description="", tags=("fsd-features",))


def _graph(root: Path, *files: str) -> sqlite3.Connection:
    for rel in files:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x\n", encoding="utf-8")
    conn = open_graph()
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source, extra) VALUES (?, ?, ?, ?, ?)",
        (
            "features-cart",
            "component",
            "cart",
            "src/features/cart/",
            json.dumps({"tags": ["fsd-features"]}),
        ),
    )
    return conn


def _messages(conn: sqlite3.Connection, root: Path) -> list[str]:
    return [v.message for v in evaluate_slice_shape_rules(conn, [RULE], project_root=root)]


def test_the_standard_segments_are_ui_model_lib_api_config() -> None:
    assert DEFAULT_SLICE_SEGMENTS == ("ui", "model", "lib", "api", "config")


def test_a_slice_of_segments_and_an_index_is_in_shape(tmp_path: Path) -> None:
    conn = _graph(
        tmp_path,
        "src/features/cart/index.ts",
        "src/features/cart/model/cart.ts",
        "src/features/cart/ui/Cart.vue",
        "src/features/cart/README.md",
    )

    assert _messages(conn, tmp_path) == []


def test_a_folder_that_is_no_segment_is_a_finding(tmp_path: Path) -> None:
    conn = _graph(tmp_path, "src/features/cart/index.ts", "src/features/cart/helpers/format.ts")

    (message,) = _messages(conn, tmp_path)

    assert "'features-cart'" in message
    assert "'helpers/'" in message
    assert "ui, model, lib, api, config" in message


def test_a_code_file_beside_the_segments_is_a_finding(tmp_path: Path) -> None:
    conn = _graph(tmp_path, "src/features/cart/index.ts", "src/features/cart/Cart.tsx")

    (message,) = _messages(conn, tmp_path)

    assert "'Cart.tsx'" in message


def test_the_segments_a_rule_declares_replace_the_standard_ones(tmp_path: Path) -> None:
    conn = _graph(tmp_path, "src/features/cart/index.ts", "src/features/cart/helpers/f.ts")
    rule = SliceShapeRule(
        name="fsd-slice-shape", description="", tags=("fsd-features",), segments=("helpers",)
    )

    assert evaluate_slice_shape_rules(conn, [rule], project_root=tmp_path) == []


def test_evaluate_all_runs_the_rule_at_its_severity(tmp_path: Path) -> None:
    conn = _graph(tmp_path, "src/features/cart/index.ts", "src/features/cart/helpers/f.ts")
    rule = SliceShapeRule(
        name="fsd-slice-shape", description="", tags=("fsd-features",), severity="warn"
    )

    (finding,) = [
        v
        for v in evaluate_all(conn, [rule], project_root=tmp_path)
        if v.rule_type == "slice_shape"
    ]

    assert finding.severity == "warn"
    assert finding.from_ref_id == "features-cart"
    assert finding.remediation is not None


def test_a_rule_whose_slices_are_not_on_disk_cannot_fire(tmp_path: Path) -> None:
    conn = _graph(tmp_path)

    ((_, reason),) = inert_rules(conn, [RULE], project_root=tmp_path)

    assert "no slice" in reason


class TestTheLoaderReadsTheRule:
    def _file(self, tmp_path: Path, block: str) -> Path:
        path = tmp_path / "rules.yml"
        path.write_text(
            "version: 3\nrules:\n  - name: fsd-slice-shape\n    slice_shape:\n" + block,
            encoding="utf-8",
        )
        return path

    def test_the_segments_default_to_the_standard_ones(self, tmp_path: Path) -> None:
        (rule,) = load_rules(self._file(tmp_path, "      tags: [fsd-features]\n"))

        assert rule == SliceShapeRule(
            name="fsd-slice-shape", description="", tags=("fsd-features",)
        )

    def test_declared_segments_are_read(self, tmp_path: Path) -> None:
        (rule,) = load_rules(
            self._file(tmp_path, "      tags: [fsd-features]\n      segments: [ui, hooks]\n")
        )

        assert isinstance(rule, SliceShapeRule)
        assert rule.segments == ("ui", "hooks")

    def test_an_empty_segment_list_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(
            ValueError,
            match=re.escape(
                "Rule 'fsd-slice-shape': 'slice_shape.segments' must be a non-empty list "
                "of folder names"
            ),
        ):
            load_rules(self._file(tmp_path, "      tags: [fsd-features]\n      segments: []\n"))

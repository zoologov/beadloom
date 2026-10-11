"""``slice_shape``: a segment is named by its purpose, not its essence (BDL-082 S1b).

feature-sliced.design, *Slices and segments*: "You can also create custom segments … Make
sure that the name of these segments describes the purpose of the content, not its
essence. For example, components, hooks, and types are bad segment names". 9.0.0 read
``segments:`` as an allow-list, so the purposeful ``analytics/`` and the discouraged
``components/`` got one identical warning (axes.md, gap 4). The rule is now the
specification's deny-list: ``discouraged:`` (Steiger's ``segments-by-purpose`` names by
default) is a finding, ``segments:`` the known-good set, and any other name is fine.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rules.loader import load_rules
from beadloom.graph.rules.slices import evaluate_slice_shape_rules
from beadloom.graph.rules.types import (
    DEFAULT_DISCOURAGED_SEGMENTS,
    DEFAULT_SLICE_SEGMENTS,
    SliceShapeRule,
)
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
            "features-x",
            "component",
            "x",
            "src/features/x/",
            json.dumps({"tags": ["fsd-features"]}),
        ),
    )
    return conn


def _messages(conn: sqlite3.Connection, root: Path, rule: SliceShapeRule = RULE) -> list[str]:
    return [v.message for v in evaluate_slice_shape_rules(conn, [rule], project_root=root)]


def test_the_default_is_the_steiger_plugins_list_of_bad_names() -> None:
    # @feature-sliced/steiger-plugin 0.8.0, rule `segments-by-purpose`, BAD_NAMES: the
    # generic, React, Vue, Redux and Angular lists, 69 names.
    assert len(DEFAULT_DISCOURAGED_SEGMENTS) == 69
    assert len(set(DEFAULT_DISCOURAGED_SEGMENTS)) == 69
    for name in ("components", "hooks", "types", "utils", "helpers", "store", "composables"):
        assert name in DEFAULT_DISCOURAGED_SEGMENTS
    assert not set(DEFAULT_SLICE_SEGMENTS) & set(DEFAULT_DISCOURAGED_SEGMENTS)


def test_a_purposeful_custom_segment_is_fine(tmp_path: Path) -> None:
    conn = _graph(tmp_path, "src/features/x/index.ts", "src/features/x/analytics/track.ts")

    assert _messages(conn, tmp_path) == []


@pytest.mark.parametrize("folder", ["components", "hooks", "types"])
def test_a_discouraged_name_is_a_finding(tmp_path: Path, folder: str) -> None:
    conn = _graph(tmp_path, "src/features/x/index.ts", f"src/features/x/{folder}/a.ts")

    (finding,) = evaluate_slice_shape_rules(conn, [RULE], project_root=tmp_path)

    assert finding.from_ref_id == "features-x"
    assert f"'{folder}/'" in finding.message
    assert "name by purpose, not essence" in finding.message
    assert "one of the 69 names this rule discourages" in finding.message
    assert finding.remediation is not None


def test_the_cross_import_folder_is_a_known_folder_of_a_slice(tmp_path: Path) -> None:
    conn = _graph(tmp_path, "src/features/x/index.ts", "src/features/x/@x/y.ts")

    assert _messages(conn, tmp_path) == []


def test_a_name_the_rule_lists_as_a_segment_is_known_good_even_if_discouraged(
    tmp_path: Path,
) -> None:
    conn = _graph(tmp_path, "src/features/x/index.ts", "src/features/x/hooks/a.ts")
    rule = SliceShapeRule(
        name="fsd-slice-shape",
        description="",
        tags=("fsd-features",),
        segments=(*DEFAULT_SLICE_SEGMENTS, "hooks"),
    )

    assert _messages(conn, tmp_path, rule) == []


def test_the_rules_own_list_replaces_the_default(tmp_path: Path) -> None:
    conn = _graph(
        tmp_path,
        "src/features/x/index.ts",
        "src/features/x/components/a.ts",
        "src/features/x/misc/a.ts",
    )
    rule = SliceShapeRule(
        name="fsd-slice-shape", description="", tags=("fsd-features",), discouraged=("misc",)
    )

    (message,) = _messages(conn, tmp_path, rule)

    assert "'misc/'" in message
    assert "one of the 1 names this rule discourages" not in message
    assert "the name this rule discourages" in message


class TestTheLoaderReadsDiscouraged:
    def _file(self, tmp_path: Path, rule_type: str, block: str) -> Path:
        path = tmp_path / "rules.yml"
        path.write_text(
            f"version: 3\nrules:\n  - name: fsd-x\n    {rule_type}:\n" + block,
            encoding="utf-8",
        )
        return path

    def test_it_defaults_to_the_steiger_list(self, tmp_path: Path) -> None:
        (rule,) = load_rules(self._file(tmp_path, "slice_shape", "      tags: [fsd-features]\n"))

        assert isinstance(rule, SliceShapeRule)
        assert rule.discouraged == DEFAULT_DISCOURAGED_SEGMENTS

    def test_a_declared_list_is_read(self, tmp_path: Path) -> None:
        (rule,) = load_rules(
            self._file(
                tmp_path,
                "slice_shape",
                "      tags: [fsd-features]\n      discouraged: [components, ' misc ']\n",
            )
        )

        assert isinstance(rule, SliceShapeRule)
        assert rule.discouraged == ("components", "misc")

    def test_an_empty_list_discourages_nothing(self, tmp_path: Path) -> None:
        (rule,) = load_rules(
            self._file(
                tmp_path, "slice_shape", "      tags: [fsd-features]\n      discouraged: []\n"
            )
        )

        assert isinstance(rule, SliceShapeRule)
        assert rule.discouraged == ()

    @pytest.mark.parametrize("value", ["components", "[components, '']", "[1, 2]", "{a: b}"])
    def test_a_value_that_is_no_list_of_names_is_refused(self, tmp_path: Path, value: str) -> None:
        with pytest.raises(
            ValueError,
            match=re.escape(
                "Rule 'fsd-x': 'slice_shape.discouraged' must be a list of folder names, "
                "each a non-empty string"
            ),
        ):
            load_rules(
                self._file(
                    tmp_path,
                    "slice_shape",
                    f"      tags: [fsd-features]\n      discouraged: {value}\n",
                )
            )

    @pytest.mark.parametrize(
        ("rule_type", "block"),
        [
            ("slice_public_api", "      tags: [fsd-features]\n"),
            ("check", "      for: { kind: component }\n      max_symbols: 3\n"),
            ("module_coverage", "      exempt: []\n"),
        ],
    )
    def test_it_is_refused_on_another_rule_type(
        self, tmp_path: Path, rule_type: str, block: str
    ) -> None:
        with pytest.raises(
            ValueError,
            match=re.escape(
                f"Rule 'fsd-x': 'discouraged' is not a key of '{rule_type}'; it is a key "
                f"of 'slice_shape'"
            ),
        ):
            load_rules(self._file(tmp_path, rule_type, block + "      discouraged: [x]\n"))

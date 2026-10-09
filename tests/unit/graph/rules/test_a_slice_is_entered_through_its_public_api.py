"""``slice_public_api``: an import into another slice lands on its ``index`` (BDL-080 S3c).

Feature-Sliced Design enters a slice through its public API, the ``index`` at its top;
Steiger calls reaching past it a public-API sidestep. ``fnmatch`` cannot say "past the
index" over import paths, so the rule reads the resolved imports instead: the index
records which slice an import reached, and the rule locates the file it named inside
that slice's folder. A file that is not the slice's ``index`` is a finding.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rules import evaluate_all
from beadloom.graph.rules.liveness import inert_rules
from beadloom.graph.rules.loader import load_rules
from beadloom.graph.rules.slices import evaluate_slice_public_api_rules
from beadloom.graph.rules.types import SlicePublicApiRule
from tests.support.in_memory_graph import open_graph

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

SLICE_TAGS = ("fsd-pages", "fsd-widgets", "fsd-features", "fsd-entities")
RULE = SlicePublicApiRule(name="fsd-public-api", description="", tags=SLICE_TAGS)


def _write(root: Path, *paths: str) -> None:
    for rel in paths:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("export const x = 1\n", encoding="utf-8")


def _graph(root: Path) -> sqlite3.Connection:
    """Three slices, a legacy folder, and the files they hold."""
    _write(
        root,
        "src/features/auth/index.ts",
        "src/features/auth/model/session.ts",
        "src/features/auth/ui/LoginForm.vue",
        "src/widgets/header/index.ts",
        "src/widgets/header/ui/Header.ts",
        "src/entities/user/model/user.ts",
        "src/components/Old.ts",
    )
    conn = open_graph()
    for ref_id, source, tags in (
        ("web", "", []),
        ("features-auth", "src/features/auth/", ["fsd-features"]),
        ("widgets-header", "src/widgets/header/", ["fsd-widgets"]),
        ("entities-user", "src/entities/user/", ["fsd-entities"]),
        ("components", "src/components/", ["fsd-legacy"]),
    ):
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source, extra) VALUES (?, ?, ?, ?, ?)",
            (ref_id, "component", ref_id, source, json.dumps({"tags": tags})),
        )
    return conn


def _import(conn: sqlite3.Connection, importer: str, specifier: str, resolved: str) -> None:
    conn.execute(
        "INSERT INTO code_imports (file_path, line_number, import_path, resolved_ref_id, "
        "file_hash) VALUES (?, ?, ?, ?, 'h')",
        (importer, 3, specifier, resolved),
    )


def _findings(conn: sqlite3.Connection, root: Path) -> list[tuple[str | None, str | None]]:
    return [
        (v.file_path, v.to_ref_id)
        for v in evaluate_slice_public_api_rules(conn, [RULE], project_root=root)
    ]


@pytest.mark.parametrize(
    "specifier",
    ["@/features/auth", "@/features/auth/index", "../../../features/auth", "@features/auth"],
)
def test_an_import_of_the_slice_itself_lands_on_its_index(tmp_path: Path, specifier: str) -> None:
    conn = _graph(tmp_path)
    _import(conn, "src/widgets/header/ui/Header.ts", specifier, "features-auth")

    assert _findings(conn, tmp_path) == []


@pytest.mark.parametrize(
    "specifier",
    [
        "@/features/auth/model/session",
        "../../../features/auth/model/session",
        "@features/auth/ui/LoginForm.vue",
    ],
)
def test_an_import_past_the_index_is_a_finding(tmp_path: Path, specifier: str) -> None:
    conn = _graph(tmp_path)
    _import(conn, "src/widgets/header/ui/Header.ts", specifier, "features-auth")

    assert _findings(conn, tmp_path) == [("src/widgets/header/ui/Header.ts", "features-auth")]


def test_the_finding_names_the_file_it_reached_and_the_index_it_skipped(
    tmp_path: Path,
) -> None:
    conn = _graph(tmp_path)
    _import(
        conn, "src/widgets/header/ui/Header.ts", "@/features/auth/model/session", "features-auth"
    )

    (finding,) = evaluate_slice_public_api_rules(conn, [RULE], project_root=tmp_path)

    assert finding.rule_type == "slice_public_api"
    assert finding.severity == "error"
    assert finding.from_ref_id == "widgets-header"
    assert finding.line_number == 3
    assert "'@/features/auth/model/session'" in finding.message
    assert "src/features/auth/model/session.ts" in finding.message
    assert "src/features/auth/index" in finding.message


def test_an_import_inside_the_slice_is_its_own_business(tmp_path: Path) -> None:
    conn = _graph(tmp_path)
    _import(conn, "src/features/auth/ui/LoginForm.vue", "../model/session", "features-auth")

    assert _findings(conn, tmp_path) == []


def test_a_legacy_folder_reaching_past_an_index_is_a_finding_too(tmp_path: Path) -> None:
    conn = _graph(tmp_path)
    _import(conn, "src/components/Old.ts", "@/features/auth/model/session", "features-auth")

    assert _findings(conn, tmp_path) == [("src/components/Old.ts", "features-auth")]


def test_a_slice_without_an_index_has_no_public_api_to_enter(tmp_path: Path) -> None:
    conn = _graph(tmp_path)
    _import(conn, "src/widgets/header/ui/Header.ts", "@/entities/user", "entities-user")

    (finding,) = evaluate_slice_public_api_rules(conn, [RULE], project_root=tmp_path)

    assert finding.to_ref_id == "entities-user"
    assert "has no index" in finding.message


def test_an_import_into_a_node_that_is_no_slice_is_not_judged(tmp_path: Path) -> None:
    conn = _graph(tmp_path)
    _import(conn, "src/widgets/header/ui/Header.ts", "@/components/Old", "components")

    assert _findings(conn, tmp_path) == []


def test_evaluate_all_runs_the_rule_and_hints_the_fix(tmp_path: Path) -> None:
    conn = _graph(tmp_path)
    _import(
        conn, "src/widgets/header/ui/Header.ts", "@/features/auth/model/session", "features-auth"
    )

    found = [
        v
        for v in evaluate_all(conn, [RULE], project_root=tmp_path)
        if v.rule_type == "slice_public_api"
    ]

    assert len(found) == 1
    assert found[0].remediation is not None
    assert "index" in found[0].remediation


def test_a_rule_whose_tags_no_node_carries_cannot_fire(tmp_path: Path) -> None:
    conn = _graph(tmp_path)
    rule = SlicePublicApiRule(name="fsd-public-api", description="", tags=("fsd-nothing",))

    ((_, reason),) = inert_rules(conn, [rule], project_root=tmp_path)

    assert "fsd-nothing" in reason


class TestTheLoaderReadsTheRule:
    def _file(self, tmp_path: Path, block: str) -> Path:
        path = tmp_path / "rules.yml"
        path.write_text(
            "version: 3\nrules:\n  - name: fsd-public-api\n    slice_public_api:\n" + block,
            encoding="utf-8",
        )
        return path

    def test_the_tags_are_read(self, tmp_path: Path) -> None:
        (rule,) = load_rules(self._file(tmp_path, "      tags: [fsd-features, fsd-entities]\n"))

        assert rule == SlicePublicApiRule(
            name="fsd-public-api", description="", tags=("fsd-features", "fsd-entities")
        )

    @pytest.mark.parametrize(
        "block", ["      tags: []\n", "      tags: fsd-x\n", "      other: 1\n"]
    )
    def test_a_rule_naming_no_tag_list_is_refused(self, tmp_path: Path, block: str) -> None:
        with pytest.raises(
            ValueError,
            match=re.escape(
                "Rule 'fsd-public-api': 'slice_public_api.tags' must be a non-empty list of "
                "tags, the tags a slice carries"
            ),
        ):
            load_rules(self._file(tmp_path, block))

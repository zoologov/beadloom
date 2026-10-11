"""A slice rule's finding names what it judged, in the words a reader acts on.

BDL-082 S1 (RFC D1, D4, D5). The rule files hold which import or folder is a finding; these
cases hold what the finding says about it, at the points a rule file does not reach: an
``@x`` API reached from outside every slice, a rule that discourages one name, the segments a
code file at a slice's top sits beside, the two entries of ``shared/ui``, a segment with no
index, an import resolved to a node with no folder, an entry at a slice's or a group's top
that is skipped without ending the scan, and the reason a rule with nothing to judge is inert.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from beadloom.graph.rules.slices import (
    evaluate_slice_public_api_rules,
    evaluate_slice_shape_rules,
    slice_rule_inert_reason,
)
from beadloom.graph.rules.types import SlicePublicApiRule, SliceShapeRule
from tests.support.in_memory_graph import add_edge, open_graph

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

API = SlicePublicApiRule(
    name="fsd-public-api",
    description="An import lands on the public API",
    tags=("fsd-pages", "fsd-entities", "fsd-shared"),
)
SHAPE = SliceShapeRule(
    name="fsd-slice-shape", description="A slice holds its segments", tags=("fsd-features",)
)


def _graph(root: Path, nodes: dict[str, tuple[str, str]], *files: str) -> sqlite3.Connection:
    """*files* on disk and *nodes*, each ``ref -> (source, tag)``."""
    for rel in files:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("export const x = 1\n", encoding="utf-8")
    conn = open_graph()
    for ref_id, (source, tag) in nodes.items():
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source, extra) VALUES (?, ?, ?, ?, ?)",
            (ref_id, "component", ref_id, source, json.dumps({"tags": [tag]})),
        )
    return conn


def _import(conn: sqlite3.Connection, importer: str, specifier: str, resolved: str) -> None:
    conn.execute(
        "INSERT INTO code_imports (file_path, line_number, import_path, resolved_ref_id, "
        "file_hash) VALUES (?, 1, ?, ?, 'h')",
        (importer, specifier, resolved),
    )


def test_an_api_reached_from_outside_every_slice_says_so(tmp_path: Path) -> None:
    conn = _graph(
        tmp_path,
        {"entities-song": ("src/entities/song/", "fsd-entities")},
        "src/entities/song/index.ts",
        "src/entities/song/@x/artist.ts",
        "src/main.ts",
    )
    _import(conn, "src/main.ts", "@/entities/song/@x/artist", "entities-song")

    [finding] = evaluate_slice_public_api_rules(conn, [API], project_root=tmp_path)

    assert "from outside every slice:" in finding.message


def test_past_the_entries_of_shared_ui_the_finding_names_both_kinds_of_entry(
    tmp_path: Path,
) -> None:
    conn = _graph(
        tmp_path,
        {
            "shared": ("src/shared/", "fsd-shared"),
            "shared-ui": ("src/shared/ui/", "fsd-shared"),
            "pages-home": ("src/pages/home/", "fsd-pages"),
        },
        "src/shared/ui/button/index.ts",
        "src/shared/ui/button/Button.ts",
        "src/pages/home/index.ts",
        "src/pages/home/ui/page.ts",
    )
    add_edge(conn, "shared-ui", "shared", "part_of")
    _import(conn, "src/pages/home/ui/page.ts", "@/shared/ui/button/Button", "shared-ui")

    [finding] = evaluate_slice_public_api_rules(conn, [API], project_root=tmp_path)

    assert (
        "(src/shared/ui/index, or a per-component index src/shared/ui/<component>/index)"
        in finding.message
    )


def test_a_rule_discouraging_one_name_says_the_name_it_discourages(tmp_path: Path) -> None:
    rule = SliceShapeRule(
        name="fsd-slice-shape", description="", tags=("fsd-features",), discouraged=("hooks",)
    )
    conn = _graph(
        tmp_path,
        {"features-cart": ("src/features/cart/", "fsd-features")},
        "src/features/cart/index.ts",
        "src/features/cart/hooks/use-cart.ts",
    )

    [finding] = evaluate_slice_shape_rules(conn, [rule], project_root=tmp_path)

    assert "'hooks/' at its top, the name this rule discourages:" in finding.message


def test_a_code_file_at_a_slices_top_is_named_beside_the_segments_it_should_be_in(
    tmp_path: Path,
) -> None:
    conn = _graph(
        tmp_path,
        {"features-cart": ("src/features/cart/", "fsd-features")},
        "src/features/cart/index.ts",
        "src/features/cart/helpers.ts",
    )

    [finding] = evaluate_slice_shape_rules(conn, [SHAPE], project_root=tmp_path)

    assert "beside its segments (ui, model, lib, api, config)" in finding.message


def test_a_hidden_entry_at_a_slices_top_is_skipped_and_the_scan_goes_on(tmp_path: Path) -> None:
    conn = _graph(
        tmp_path,
        {"features-cart": ("src/features/cart/", "fsd-features")},
        "src/features/cart/index.ts",
        "src/features/cart/.eslintrc.cjs",
        "src/features/cart/components/item.ts",
    )

    findings = evaluate_slice_shape_rules(conn, [SHAPE], project_root=tmp_path)

    assert [f.message.split(" at its top")[0] for f in findings] == [
        "Slice 'features-cart' holds the folder 'components/'"
    ]


def test_a_hidden_entry_at_a_groups_top_is_skipped_and_the_scan_goes_on(tmp_path: Path) -> None:
    conn = _graph(
        tmp_path,
        {"features-auth-login": ("src/features/auth/login/", "fsd-features")},
        "src/features/auth/login/index.ts",
        "src/features/auth/.eslintrc.cjs",
        "src/features/auth/README.md",
        "src/features/auth/shared.ts",
    )

    findings = evaluate_slice_shape_rules(conn, [SHAPE], project_root=tmp_path)

    assert [f.file_path for f in findings] == ["src/features/auth/shared.ts"]


def test_a_finding_carries_its_rules_description(tmp_path: Path) -> None:
    conn = _graph(
        tmp_path,
        {
            "features-cart": ("src/features/cart/", "fsd-features"),
            "entities-song": ("src/entities/song/", "fsd-entities"),
        },
        "src/features/cart/index.ts",
        "src/features/cart/helpers.ts",
        "src/entities/song/index.ts",
        "src/entities/song/model/song.ts",
    )
    _import(conn, "src/features/cart/index.ts", "@/entities/song/model/song", "entities-song")

    found = [
        *evaluate_slice_shape_rules(conn, [SHAPE], project_root=tmp_path),
        *evaluate_slice_public_api_rules(conn, [API], project_root=tmp_path),
    ]

    assert [(f.rule_name, f.rule_description) for f in found] == [
        ("fsd-slice-shape", "A slice holds its segments"),
        ("fsd-public-api", "An import lands on the public API"),
    ]


def test_a_segment_with_no_index_is_named_as_having_none_and_the_importer_as_its_source(
    tmp_path: Path,
) -> None:
    conn = _graph(
        tmp_path,
        {
            "shared": ("src/shared/", "fsd-shared"),
            "shared-config": ("src/shared/config/", "fsd-shared"),
            "pages-home": ("src/pages/home/", "fsd-pages"),
        },
        "src/shared/config/env.ts",
        "src/pages/home/index.ts",
        "src/pages/home/ui/page.ts",
    )
    add_edge(conn, "shared-config", "shared", "part_of")
    _import(conn, "src/pages/home/ui/page.ts", "@/shared/config/env", "shared-config")

    [finding] = evaluate_slice_public_api_rules(conn, [API], project_root=tmp_path)

    assert finding.from_ref_id == "pages-home"
    assert "into segment 'shared-config', which has no index" in finding.message


def test_an_import_resolved_to_a_node_with_no_folder_is_not_judged(tmp_path: Path) -> None:
    conn = _graph(
        tmp_path,
        {"pages-home": ("src/pages/home/", "fsd-pages")},
        "src/pages/home/index.ts",
        "src/pages/home/ui/page.ts",
    )
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source, extra) VALUES (?, ?, ?, ?, ?)",
        ("web", "service", "web", "", json.dumps({"tags": ["fsd-entities"]})),
    )
    _import(conn, "src/pages/home/ui/page.ts", "web", "web")

    assert evaluate_slice_public_api_rules(conn, [API], project_root=tmp_path) == []


def test_a_rule_whose_tags_no_node_carries_names_every_tag(tmp_path: Path) -> None:
    conn = _graph(tmp_path, {})

    reason = slice_rule_inert_reason(API, conn, tmp_path)

    assert reason == "no node carries any of its tags (fsd-pages, fsd-entities, fsd-shared)"


def test_a_rule_whose_carriers_have_no_folder_says_so(tmp_path: Path) -> None:
    conn = _graph(tmp_path, {})
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source, extra) VALUES (?, ?, ?, ?, ?)",
        (
            "pages-gone",
            "component",
            "gone",
            "src/pages/gone/",
            json.dumps({"tags": ["fsd-pages"]}),
        ),
    )

    reason = slice_rule_inert_reason(API, conn, tmp_path)

    assert reason is not None
    assert reason.endswith("has a source folder on disk")


def test_a_rule_reads_its_carriers_folders_under_the_root_it_is_handed(tmp_path: Path) -> None:
    conn = _graph(
        tmp_path, {"pages-home": ("src/pages/home/", "fsd-pages")}, "src/pages/home/index.ts"
    )

    assert slice_rule_inert_reason(API, conn, tmp_path) is None

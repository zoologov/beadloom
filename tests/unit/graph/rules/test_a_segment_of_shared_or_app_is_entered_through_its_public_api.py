"""``slice_public_api`` over the unsliced layers: a segment has a public API too (BDL-082 S1b).

feature-sliced.design, *Slices and segments*: "Every slice (and segment on layers that
don't have slices) must contain a public API definition." *Public API*, on large bundles in
Shared: for ``shared/ui`` and ``shared/lib``, "have a separate index file for each component
or library", imported as ``@/shared/ui/button``. *Layers*: the segments of ``app`` and of
``shared`` import each other freely.

So when the rule carries ``fsd-shared`` and ``fsd-app``: a segment is entered through its
index; in ``shared/ui`` and ``shared/lib`` a per-component index is an entry too, and not a
node; and two segments of one unsliced layer are not judged against each other. 9.0.0 read
a segment as a slice: the per-component index was "no index", and one segment reaching
another was a finding (axes.md, gap 5).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rules.slices import evaluate_slice_public_api_rules
from beadloom.graph.rules.types import SlicePublicApiRule
from tests.support.in_memory_graph import open_graph

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

RULE = SlicePublicApiRule(
    name="fsd-public-api",
    description="",
    tags=("fsd-pages", "fsd-features", "fsd-shared", "fsd-app"),
)


def _write(root: Path, *paths: str) -> None:
    for rel in paths:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("export const x = 1\n", encoding="utf-8")


def _graph(root: Path) -> sqlite3.Connection:
    """The axes probe ``p45-segments``, with the nodes ``init`` writes for it."""
    _write(
        root,
        "src/shared/ui/button/index.ts",
        "src/shared/ui/button/Button.ts",
        "src/shared/ui/text-field/index.ts",
        "src/shared/ui/text-field/text-field.ts",
        "src/shared/ui/loose.ts",
        "src/shared/lib/dates/index.ts",
        "src/shared/i18n/index.ts",
        "src/shared/routes/index.ts",
        "src/shared/routes/paths.ts",
        "src/shared/api/client.ts",
        "src/shared/top.ts",
        "src/app/store/index.ts",
        "src/app/store/slice.ts",
        "src/app/entrypoint/index.ts",
        "src/app/ui/frame/index.ts",
        "src/pages/home/index.ts",
        "src/pages/home/ui/home.ts",
    )
    conn = open_graph()
    nodes = (
        ("shared", "src/shared/", "fsd-shared", None),
        ("shared-ui", "src/shared/ui/", "fsd-shared", "shared"),
        ("shared-lib", "src/shared/lib/", "fsd-shared", "shared"),
        ("shared-i18n", "src/shared/i18n/", "fsd-shared", "shared"),
        ("shared-routes", "src/shared/routes/", "fsd-shared", "shared"),
        ("shared-api", "src/shared/api/", "fsd-shared", "shared"),
        ("app", "src/app/", "fsd-app", None),
        ("app-store", "src/app/store/", "fsd-app", "app"),
        ("app-entrypoint", "src/app/entrypoint/", "fsd-app", "app"),
        ("app-ui", "src/app/ui/", "fsd-app", "app"),
        ("pages-home", "src/pages/home/", "fsd-pages", None),
    )
    for ref_id, source, tag, container in nodes:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source, extra) VALUES (?, ?, ?, ?, ?)",
            (ref_id, "component", ref_id, source, json.dumps({"tags": [tag]})),
        )
        if container is not None:
            conn.execute(
                "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, 'part_of')",
                (ref_id, container),
            )
    return conn


def _import(conn: sqlite3.Connection, importer: str, specifier: str, resolved: str) -> None:
    conn.execute(
        "INSERT INTO code_imports (file_path, line_number, import_path, resolved_ref_id, "
        "file_hash) VALUES (?, ?, ?, ?, 'h')",
        (importer, 2, specifier, resolved),
    )


def _findings(conn: sqlite3.Connection, root: Path) -> list[tuple[str | None, str | None]]:
    return [
        (v.file_path, v.to_ref_id)
        for v in evaluate_slice_public_api_rules(conn, [RULE], project_root=root)
    ]


@pytest.mark.parametrize(
    ("specifier", "segment"),
    [
        ("@/shared/ui/button", "shared-ui"),
        ("@/shared/ui/button/index", "shared-ui"),
        ("../../../shared/ui/text-field", "shared-ui"),
        ("@/shared/lib/dates", "shared-lib"),
        ("@/shared/i18n", "shared-i18n"),
        ("@/shared/routes", "shared-routes"),
        ("@/app/store", "app-store"),
    ],
)
def test_an_import_through_a_public_api_entry_is_clean(
    tmp_path: Path, specifier: str, segment: str
) -> None:
    conn = _graph(tmp_path)
    _import(conn, "src/pages/home/ui/home.ts", specifier, segment)

    assert _findings(conn, tmp_path) == []


@pytest.mark.parametrize(
    ("specifier", "segment", "reached"),
    [
        (
            "@/shared/ui/text-field/text-field",
            "shared-ui",
            "src/shared/ui/text-field/text-field.ts",
        ),
        ("@/shared/ui/button/Button", "shared-ui", "src/shared/ui/button/Button.ts"),
        ("@/shared/routes/paths", "shared-routes", "src/shared/routes/paths.ts"),
        ("@/app/store/slice", "app-store", "src/app/store/slice.ts"),
    ],
)
def test_an_import_past_the_entries_is_a_finding(
    tmp_path: Path, specifier: str, segment: str, reached: str
) -> None:
    # The two sidesteps the axes probe measured (text-field, routes/paths) are the first
    # and the third: Steiger reports both, and 9.0.0 reported neither as init wrote it.
    conn = _graph(tmp_path)
    _import(conn, "src/pages/home/ui/home.ts", specifier, segment)

    (finding,) = evaluate_slice_public_api_rules(conn, [RULE], project_root=tmp_path)

    assert finding.to_ref_id == segment
    assert f"segment '{segment}'" in finding.message
    assert reached in finding.message


def test_the_finding_in_shared_ui_names_the_per_component_entries(tmp_path: Path) -> None:
    conn = _graph(tmp_path)
    _import(conn, "src/pages/home/ui/home.ts", "@/shared/ui/button/Button", "shared-ui")

    (finding,) = evaluate_slice_public_api_rules(conn, [RULE], project_root=tmp_path)

    assert "src/shared/ui/<component>/index" in finding.message


def test_a_per_component_index_is_an_entry_only_in_shared(tmp_path: Path) -> None:
    # `app/ui/frame/index` is a folder's index inside a segment of app, not an entry.
    conn = _graph(tmp_path)
    _import(conn, "src/pages/home/ui/home.ts", "@/app/ui/frame", "app-ui")

    assert _findings(conn, tmp_path) == [("src/pages/home/ui/home.ts", "app-ui")]


def test_a_loose_file_of_shared_ui_is_past_every_entry(tmp_path: Path) -> None:
    conn = _graph(tmp_path)
    _import(conn, "src/pages/home/ui/home.ts", "@/shared/ui/loose", "shared-ui")

    assert _findings(conn, tmp_path) == [("src/pages/home/ui/home.ts", "shared-ui")]


def test_a_segment_without_an_index_has_no_public_api_to_enter(tmp_path: Path) -> None:
    conn = _graph(tmp_path)
    _import(conn, "src/pages/home/ui/home.ts", "@/shared/api", "shared-api")

    (finding,) = evaluate_slice_public_api_rules(conn, [RULE], project_root=tmp_path)

    assert "segment 'shared-api'" in finding.message
    assert "has no index" in finding.message


@pytest.mark.parametrize(
    ("importer", "specifier", "segment"),
    [
        ("src/shared/routes/paths.ts", "../ui/button/Button", "shared-ui"),
        ("src/shared/i18n/index.ts", "@/shared/api/client", "shared-api"),
        ("src/shared/top.ts", "./routes/paths", "shared-routes"),
        ("src/app/entrypoint/index.ts", "@/app/store/slice", "app-store"),
    ],
)
def test_segments_of_one_unsliced_layer_import_each_other_freely(
    tmp_path: Path, importer: str, specifier: str, segment: str
) -> None:
    conn = _graph(tmp_path)
    _import(conn, importer, specifier, segment)

    assert _findings(conn, tmp_path) == []


def test_an_import_into_the_layer_container_itself_is_not_judged(tmp_path: Path) -> None:
    # `shared` is the layer, not a segment: FSD gives it no public API of its own.
    conn = _graph(tmp_path)
    _import(conn, "src/pages/home/ui/home.ts", "@/shared/top", "shared")

    assert _findings(conn, tmp_path) == []

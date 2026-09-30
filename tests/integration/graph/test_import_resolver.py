"""Relative JS/TS imports resolved against files on disk and nodes in an index (BDL-076 J1).

Measured by A0 (`beadloom-kcwz`): every relative JS/TS specifier was skipped on
purpose, so a JS/TS project got no ``depends_on`` edge between its own modules.
These tests hold the three answers a relative specifier can now get: the node
that owns the file it names, no node for a file no node owns, and no node for a
specifier that names no file — the last two recorded, never dropped.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.context_oracle.code_indexer import clear_cache
from beadloom.graph.import_resolver import (
    index_imports,
    reindex_file_imports,
    resolve_import_to_node,
    resolve_relative_import,
)
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


def _ts_available() -> bool:
    try:
        import tree_sitter_typescript  # noqa: F401
    except ImportError:
        return False
    return True


@pytest.fixture(autouse=True)
def _clear_lang_cache() -> None:
    clear_cache()


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    c = open_db(tmp_path / "index.db")
    create_schema(c)
    for ref_id, source in (
        ("app", "src/app/"),
        ("shared", "src/shared/"),
        ("dates", "src/shared/dates.ts"),
    ):
        c.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, 'domain', '', ?)",
            (ref_id, source),
        )
    c.commit()
    return c


def _write(root: Path, rel_path: str, text: str = "export const x = 1;\n") -> None:
    path = root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class TestResolveRelativeImport:
    def test_the_most_specific_owner_of_the_named_file(
        self, tmp_path: Path, conn: sqlite3.Connection
    ) -> None:
        _write(tmp_path, "src/shared/dates.ts")
        _write(tmp_path, "src/shared/money.ts")
        importer = "src/app/main.ts"
        assert resolve_relative_import("../shared/dates", importer, tmp_path, conn) == "dates"
        assert resolve_relative_import("../shared/money", importer, tmp_path, conn) == "shared"

    def test_an_extension_is_preferred_in_the_stated_order(
        self, tmp_path: Path, conn: sqlite3.Connection
    ) -> None:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES "
            "('js-twin', 'feature', '', 'src/shared/util.js')"
        )
        _write(tmp_path, "src/shared/util.ts")
        _write(tmp_path, "src/shared/util.js")
        assert (
            resolve_relative_import("../shared/util", "src/app/a.ts", tmp_path, conn) == "shared"
        )

    def test_a_file_beats_a_folder_index(self, tmp_path: Path, conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES "
            "('folder', 'feature', '', 'src/shared/lib/')"
        )
        _write(tmp_path, "src/shared/lib.js")
        _write(tmp_path, "src/shared/lib/index.js")
        assert resolve_relative_import("../shared/lib", "src/app/a.js", tmp_path, conn) == "shared"

    def test_a_folder_is_entered_through_its_index(
        self, tmp_path: Path, conn: sqlite3.Connection
    ) -> None:
        _write(tmp_path, "src/shared/store/index.mjs")
        assert resolve_relative_import("../shared/store", "src/app/a.js", tmp_path, conn) == (
            "shared"
        )

    def test_a_js_specifier_names_its_typescript_source(
        self, tmp_path: Path, conn: sqlite3.Connection
    ) -> None:
        _write(tmp_path, "src/shared/dates.ts")
        assert resolve_relative_import("../shared/dates.js", "src/app/a.ts", tmp_path, conn) == (
            "dates"
        )

    def test_a_vue_component(self, tmp_path: Path, conn: sqlite3.Connection) -> None:
        _write(tmp_path, "src/shared/Button.vue", "<template><b/></template>\n")
        assert resolve_relative_import("../shared/Button.vue", "src/app/a.js", tmp_path, conn) == (
            "shared"
        )

    def test_a_specifier_that_names_no_file(
        self, tmp_path: Path, conn: sqlite3.Connection
    ) -> None:
        assert resolve_relative_import("./missing", "src/app/a.ts", tmp_path, conn) is None

    def test_a_file_no_node_owns(self, tmp_path: Path, conn: sqlite3.Connection) -> None:
        _write(tmp_path, "src/other/x.ts")
        assert resolve_relative_import("../other/x", "src/app/a.ts", tmp_path, conn) is None


def _imports(conn: sqlite3.Connection) -> set[tuple[str, str, str | None]]:
    rows = conn.execute(
        "SELECT file_path, import_path, resolved_ref_id FROM code_imports"
    ).fetchall()
    return {(str(r[0]), str(r[1]), r[2]) for r in rows}


def _depends_on(conn: sqlite3.Connection) -> set[tuple[str, str]]:
    rows = conn.execute(
        "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'depends_on'"
    ).fetchall()
    return {(str(r[0]), str(r[1])) for r in rows}


@pytest.mark.skipif(not _ts_available(), reason="tree-sitter-typescript not installed")
class TestIndexRecordsRelativeImports:
    def _project(self, root: Path) -> None:
        (root / ".beadloom").mkdir()
        (root / ".beadloom" / "config.yml").write_text("scan_paths:\n- src\n", encoding="utf-8")
        _write(
            root,
            "src/app/main.ts",
            "import { d } from '../shared/dates';\n"
            "import { gone } from './missing';\n"
            "import lodash from 'lodash';\n",
        )
        _write(root, "src/shared/dates.ts")

    def test_resolved_unresolved_and_bare_are_all_recorded(
        self, tmp_path: Path, conn: sqlite3.Connection
    ) -> None:
        self._project(tmp_path)
        index_imports(tmp_path, conn)
        assert _imports(conn) == {
            ("src/app/main.ts", "../shared/dates", "dates"),
            ("src/app/main.ts", "./missing", None),
            ("src/app/main.ts", "lodash", None),
        }
        assert _depends_on(conn) == {("app", "dates")}

    def test_an_incremental_reindex_resolves_the_same_way(
        self, tmp_path: Path, conn: sqlite3.Connection
    ) -> None:
        self._project(tmp_path)
        index_imports(tmp_path, conn)
        _write(tmp_path, "src/app/main.ts", "import { m } from '../shared/money';\n")
        _write(tmp_path, "src/shared/money.ts")
        reindex_file_imports(
            tmp_path, conn, touched=["src/app/main.ts", "src/shared/money.ts"], removed=[]
        )
        assert _imports(conn) == {("src/app/main.ts", "../shared/money", "shared")}
        assert _depends_on(conn) == {("app", "shared")}


class TestTheWalkUpStopsAtTheScanRoot:
    """BDL-076 J2: an import no file answers is not claimed by a node at or above a scan path.

    A0 measured the defect on this repository: with ``site/.vitepress/theme`` as a
    scan path, ``typing`` became ``site/.vitepress/theme/typing`` and walked up to
    ``site/``, the source of ``vitepress-site``.
    """

    def _node(self, conn: sqlite3.Connection, ref_id: str, source: str) -> None:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, 'domain', '', ?)",
            (ref_id, source),
        )

    def test_a_node_above_the_scan_path_is_not_reached(
        self, tmp_path: Path, conn: sqlite3.Connection
    ) -> None:
        self._node(conn, "site", "web/")
        assert resolve_import_to_node("typing", tmp_path, conn, scan_paths=["web/theme"]) is None

    def test_a_node_whose_source_is_the_scan_root_is_not_reached(
        self, tmp_path: Path, conn: sqlite3.Connection
    ) -> None:
        self._node(conn, "everything", "lib/")
        assert resolve_import_to_node("typing", tmp_path, conn, scan_paths=["lib"]) is None

    def test_a_trailing_slash_on_the_scan_path_is_the_same_scan_root(
        self, tmp_path: Path, conn: sqlite3.Connection
    ) -> None:
        self._node(conn, "everything", "lib/")
        assert resolve_import_to_node("typing", tmp_path, conn, scan_paths=["lib/"]) is None

    def test_a_package_below_the_scan_root_still_resolves(
        self, tmp_path: Path, conn: sqlite3.Connection
    ) -> None:
        self._node(conn, "billing", "lib/billing/")
        assert resolve_import_to_node(
            "billing.invoices.render", tmp_path, conn, scan_paths=["lib"]
        ) == ("billing")


@pytest.mark.skipif(not _ts_available(), reason="tree-sitter-typescript not installed")
class TestAnImportIsReadOnlyThroughScanPathsOfItsLanguage:
    """BDL-076 J2: a Python import is never prefixed with a JavaScript-only scan path."""

    def test_a_python_import_does_not_reach_a_folder_under_a_js_scan_path(
        self, tmp_path: Path, conn: sqlite3.Connection
    ) -> None:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES "
            "('widgets', 'feature', '', 'web/theme/widgets/')"
        )
        (tmp_path / ".beadloom").mkdir()
        (tmp_path / ".beadloom" / "config.yml").write_text(
            "scan_paths:\n- src\n- web/theme\n", encoding="utf-8"
        )
        _write(tmp_path, "src/app/main.py", "import widgets.card\n")
        _write(tmp_path, "web/theme/widgets/card.js", "export const card = 1;\n")
        _write(tmp_path, "web/theme/main.js", "import { card } from 'widgets/card';\n")
        index_imports(tmp_path, conn)
        assert ("src/app/main.py", "widgets.card", None) in _imports(conn)

    def test_the_languages_each_scan_path_holds(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import scan_path_languages

        _write(tmp_path, "src/a.py", "x = 1\n")
        _write(tmp_path, "src/b.ts")
        _write(tmp_path, "web/theme/c.vue", "<template/>\n")
        _write(tmp_path, "web/theme/d.jsx")
        files = [
            tmp_path / p for p in ("src/a.py", "src/b.ts", "web/theme/c.vue", "web/theme/d.jsx")
        ]
        assert scan_path_languages(tmp_path, ["src", "web/theme/"], files) == {
            "src": frozenset({".py", ".ts"}),
            "web/theme/": frozenset({".ts"}),
        }


def _go_available() -> bool:
    try:
        import tree_sitter_go  # noqa: F401
    except ImportError:
        return False
    return True


#: A Go service on the standard layout (BDL-076 B5): the entry point is named after
#: the module, which is what drew every internal import onto it before B5.
_GO_SERVICE: dict[str, str] = {
    "go.mod": "module example.org/quay\n\ngo 1.22\n",
    "cmd/quay/main.go": (
        'package main\n\nimport (\n\t"fmt"\n\t"net/http"\n\n'
        '\t"example.org/quay/internal/berths"\n\t"github.com/google/uuid"\n)\n'
    ),
    "internal/berths/berths.go": (
        'package berths\n\nimport "example.org/quay/internal/berths/store"\n'
    ),
    "internal/berths/store/store.go": 'package store\n\nimport "encoding/json"\n',
    "internal/ledger/ledger.go": (
        'package ledger\n\nimport (\n\t"example.org/quay/internal/berths"\n'
        '\t"github.com/acme/quay/internal/berths"\n)\n'
    ),
}


@pytest.mark.skipif(not _go_available(), reason="tree-sitter-go not installed")
class TestGoImportsResolveThroughTheirModule:
    """BDL-076 B5: a Go import reaches the node owning the package its module path names.

    Measured by B3 on the Go adopter fixture: every Go import was recorded with no
    node, because the ``go.mod`` module prefix was never stripped.
    """

    @pytest.fixture
    def go_conn(self, tmp_path: Path) -> sqlite3.Connection:
        c = open_db(tmp_path / "index.db")
        create_schema(c)
        for ref_id, source in (
            ("quay", "cmd/quay/"),
            ("berths", "internal/berths/"),
            ("store", "internal/berths/store/"),
            ("ledger", "internal/ledger/"),
            ("net", "net/"),
        ):
            c.execute(
                "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, 'service', '', ?)",
                (ref_id, source),
            )
        c.commit()
        (tmp_path / ".beadloom").mkdir()
        (tmp_path / ".beadloom" / "config.yml").write_text(
            "scan_paths:\n- cmd\n- internal\n", encoding="utf-8"
        )
        for rel_path, text in _GO_SERVICE.items():
            _write(tmp_path, rel_path, text)
        return c

    def test_each_import_is_recorded_with_the_node_owning_its_package(
        self, tmp_path: Path, go_conn: sqlite3.Connection
    ) -> None:
        index_imports(tmp_path, go_conn)
        assert _imports(go_conn) == {
            ("cmd/quay/main.go", "net/http", None),
            ("cmd/quay/main.go", "example.org/quay/internal/berths", "berths"),
            ("cmd/quay/main.go", "github.com/google/uuid", None),
            ("internal/berths/berths.go", "example.org/quay/internal/berths/store", "store"),
            ("internal/berths/store/store.go", "encoding/json", None),
            ("internal/ledger/ledger.go", "example.org/quay/internal/berths", "berths"),
            ("internal/ledger/ledger.go", "github.com/acme/quay/internal/berths", None),
        }

    def test_the_edges_are_exactly_the_package_imports(
        self, tmp_path: Path, go_conn: sqlite3.Connection
    ) -> None:
        index_imports(tmp_path, go_conn)
        assert _depends_on(go_conn) == {
            ("quay", "berths"),
            ("berths", "store"),
            ("ledger", "berths"),
        }

    def test_an_incremental_reindex_resolves_the_same_way(
        self, tmp_path: Path, go_conn: sqlite3.Connection
    ) -> None:
        index_imports(tmp_path, go_conn)
        _write(
            tmp_path,
            "internal/ledger/ledger.go",
            'package ledger\n\nimport "example.org/quay/internal/berths/store"\n',
        )
        reindex_file_imports(tmp_path, go_conn, touched=["internal/ledger/ledger.go"], removed=[])
        assert ("ledger", "store") in _depends_on(go_conn)
        assert ("ledger", "berths") not in _depends_on(go_conn)

    def test_an_import_of_a_package_the_tree_does_not_hold_names_no_node(
        self, tmp_path: Path, go_conn: sqlite3.Connection
    ) -> None:
        _write(
            tmp_path,
            "internal/ledger/ledger.go",
            'package ledger\n\nimport "example.org/quay/internal/gone"\n',
        )
        index_imports(tmp_path, go_conn)
        assert ("internal/ledger/ledger.go", "example.org/quay/internal/gone", None) in _imports(
            go_conn
        )

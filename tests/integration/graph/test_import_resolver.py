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


def _jvm_available() -> bool:
    try:
        import tree_sitter_java  # noqa: F401
        import tree_sitter_kotlin  # noqa: F401
    except ImportError:
        return False
    return True


#: One Gradle module keeping Java and Kotlin in separate roots (BDL-076 B6).
_MIXED_MODULE: dict[str, str] = {
    "src/main/java/org/acme/mill/legacy/Grinder.java": (
        "package org.acme.mill.legacy;\n\nimport org.acme.mill.fresh.Sifter;\n\n"
        "public class Grinder { Sifter sifter; }\n"
    ),
    "src/main/kotlin/org/acme/mill/fresh/Sifter.kt": (
        "package org.acme.mill.fresh\n\nclass Sifter\n"
    ),
    "src/main/kotlin/org/acme/mill/fresh/Sieve.kt": (
        "package org.acme.mill.fresh\n\nimport org.acme.mill.legacy.Grinder\n\nclass Sieve\n"
    ),
}


@pytest.mark.skipif(not _jvm_available(), reason="tree-sitter-java or -kotlin not installed")
class TestJavaAndKotlinShareOnePackageNamespace:
    """BDL-076 B6: a Kotlin import of a Java package resolves across the module's two roots.

    An import was read only through the scan paths holding its own language, and
    ``.java`` and ``.kt`` were two languages, so a Kotlin file in
    ``src/main/kotlin`` never reached a Java package in ``src/main/java``.
    """

    def test_each_language_reaches_the_other_roots_packages(self, tmp_path: Path) -> None:
        c = open_db(tmp_path / "index.db")
        create_schema(c)
        for ref_id, source in (
            ("legacy", "src/main/java/org/acme/mill/legacy/"),
            ("fresh", "src/main/kotlin/org/acme/mill/fresh/"),
        ):
            c.execute(
                "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, 'domain', '', ?)",
                (ref_id, source),
            )
        c.commit()
        (tmp_path / ".beadloom").mkdir()
        (tmp_path / ".beadloom" / "config.yml").write_text(
            "scan_paths:\n- src/main/java\n- src/main/kotlin\n", encoding="utf-8"
        )
        for rel_path, text in _MIXED_MODULE.items():
            _write(tmp_path, rel_path, text)

        index_imports(tmp_path, c)

        assert _depends_on(c) == {("legacy", "fresh"), ("fresh", "legacy")}


#: Kotlin's recommended layout: the root package `org.example` omitted from the folders
#: (R2 finding 6). The package path names no folder; only the declarations do.
_KOTLIN_CONVENTION: dict[str, str] = {
    "src/main/kotlin/app/Main.kt": (
        "package org.example.app\n\n"
        "import org.example.network.Socket\n"
        "import org.example.storage.*\n"
        "import io.ktor.server.routing.get\n\n"
        "fun main() { Socket() }\n"
    ),
    "src/main/kotlin/network/Socket.kt": "package org.example.network\n\nclass Socket\n",
    "src/main/kotlin/storage/Store.kt": "package org.example.storage\n\nclass Store\n",
}


@pytest.mark.skipif(not _jvm_available(), reason="tree-sitter-java or -kotlin not installed")
class TestAKotlinImportIsReadByItsDeclaredPackage:
    """R2 finding 6: reindex reads a JVM import's package from the files' declarations.

    The dotted path was read as a folder under the scan paths, and on Kotlin's
    recommended layout no such folder exists, so no import resolved.
    """

    def _project(self, root: Path) -> sqlite3.Connection:
        c = open_db(root / "index.db")
        create_schema(c)
        for ref_id in ("app", "network", "storage"):
            c.execute(
                "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, 'domain', '', ?)",
                (ref_id, f"src/main/kotlin/{ref_id}/"),
            )
        c.commit()
        (root / ".beadloom").mkdir()
        (root / ".beadloom" / "config.yml").write_text(
            "scan_paths:\n- src/main/kotlin\n", encoding="utf-8"
        )
        for rel_path, text in _KOTLIN_CONVENTION.items():
            _write(root, rel_path, text)
        return c

    def test_a_full_index_resolves_each_import_to_its_package(self, tmp_path: Path) -> None:
        c = self._project(tmp_path)

        index_imports(tmp_path, c)

        edges, imports = _depends_on(c), _imports(c)
        c.close()
        assert edges == {("app", "network"), ("app", "storage")}
        assert ("src/main/kotlin/app/Main.kt", "io.ktor.server.routing.get", None) in imports

    def test_an_incremental_reindex_resolves_it_too(self, tmp_path: Path) -> None:
        c = self._project(tmp_path)

        reindex_file_imports(tmp_path, c, touched=["src/main/kotlin/app/Main.kt"], removed=[])

        edges = _depends_on(c)
        c.close()
        assert edges == {("app", "network"), ("app", "storage")}


#: One package declared in two folders of Kotlin's recommended layout, a third folder
#: holding both under one node (the re-review's finding m5).
_ONE_PACKAGE_TWO_FOLDERS: dict[str, str] = {
    "src/main/kotlin/a/A.kt": "package org.ex.shared\n\nclass A\n",
    "src/main/kotlin/b/B.kt": "package org.ex.shared\n\nclass B\n",
    "src/main/kotlin/util/x/Ux.kt": "package org.ex.util\n\nfun ux() = 1\n",
    "src/main/kotlin/util/y/Uy.kt": "package org.ex.util\n\nfun uy() = 2\n",
    "src/main/kotlin/c/C.kt": (
        "package org.ex.c\n\n"
        "import org.ex.shared.B\n"
        "import org.ex.shared.*\n"
        "import org.ex.util.uy\n\n"
        "class C(val b: B)\n"
    ),
}


@pytest.mark.skipif(not _jvm_available(), reason="tree-sitter-java or -kotlin not installed")
class TestAPackageDeclaredInTwoFoldersIsNotGivenToTheFirst:
    """The re-review's finding m5 (``beadloom-ujzb.24``): no false edge to the folder read first.

    ``org.ex.shared.B`` resolved to ``a``, the first folder declaring the package,
    while ``B`` is in ``b``.
    """

    def _project(self, root: Path) -> sqlite3.Connection:
        c = open_db(root / "index.db")
        create_schema(c)
        for ref_id in ("a", "b", "c", "util"):
            c.execute(
                "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, 'domain', '', ?)",
                (ref_id, f"src/main/kotlin/{ref_id}/"),
            )
        c.commit()
        (root / ".beadloom").mkdir()
        (root / ".beadloom" / "config.yml").write_text(
            "scan_paths:\n- src/main/kotlin\n", encoding="utf-8"
        )
        for rel_path, text in _ONE_PACKAGE_TWO_FOLDERS.items():
            _write(root, rel_path, text)
        return c

    def test_each_import_reaches_the_folder_of_its_class_or_no_node(
        self, tmp_path: Path
    ) -> None:
        c = self._project(tmp_path)

        index_imports(tmp_path, c)

        edges, imports = _depends_on(c), _imports(c)
        c.close()
        # The class import reaches b; the wildcard reaches a and b, two nodes, so
        # none; the function reaches util/x and util/y, which one node owns.
        assert ("src/main/kotlin/c/C.kt", "org.ex.shared.B", "b") in imports
        assert ("src/main/kotlin/c/C.kt", "org.ex.shared", None) in imports
        assert ("src/main/kotlin/c/C.kt", "org.ex.util.uy", "util") in imports
        assert edges == {("c", "b"), ("c", "util")}

    def test_an_incremental_reindex_resolves_the_same_way(self, tmp_path: Path) -> None:
        c = self._project(tmp_path)

        reindex_file_imports(tmp_path, c, touched=["src/main/kotlin/c/C.kt"], removed=[])

        edges = _depends_on(c)
        c.close()
        assert edges == {("c", "b"), ("c", "util")}


def _swift_available() -> bool:
    try:
        import tree_sitter_swift  # noqa: F401
    except ImportError:
        return False
    return True


#: A Swift package at the root with a target outside `Sources/`, and a local package
#: below it (BDL-076 B7). Each target is its own scan path, as `init` writes them.
_SWIFT_PACKAGES: dict[str, str] = {
    "Package.swift": (
        "import PackageDescription\n"
        'let package = Package(name: "Harbor", targets: [\n'
        '    .target(name: "Engine", path: "Engine"),\n'
        '    .executableTarget(name: "Harbor", dependencies: ["Engine", "Moor"]),\n'
        '    .binaryTarget(name: "Crypto", path: "Crypto.xcframework"),\n'
        "])\n"
    ),
    "Engine/Engine.swift": "import Foundation\n\npublic struct Engine {}\n",
    "Sources/Harbor/main.swift": "import Engine\nimport Moor\nimport Logging\nimport Crypto\n",
    "Packages/Docks/Package.swift": (
        "import PackageDescription\n"
        'let package = Package(name: "Docks", targets: [.target(name: "Moor")])\n'
    ),
    "Packages/Docks/Sources/Moor/Moor.swift": "import Engine\n\npublic struct Moor {}\n",
}


@pytest.mark.skipif(not _swift_available(), reason="tree-sitter-swift not installed")
class TestSwiftImportsResolveThroughTheirManifest:
    """BDL-076 B7: a Swift import reaches the node owning the target its manifest declares.

    A Swift ``import`` names a module, not a folder: read as a dotted folder path
    under each scan path it names nothing once every target is its own scan path,
    and nothing at all for a target whose ``path:`` is not ``Sources/<name>``.
    """

    @pytest.fixture
    def swift_conn(self, tmp_path: Path) -> sqlite3.Connection:
        c = open_db(tmp_path / "index.db")
        create_schema(c)
        for ref_id, source in (
            ("Engine", "Engine/"),
            ("Harbor", "Sources/Harbor/"),
            ("Moor", "Packages/Docks/Sources/Moor/"),
        ):
            c.execute(
                "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, 'domain', '', ?)",
                (ref_id, source),
            )
        c.commit()
        (tmp_path / ".beadloom").mkdir()
        (tmp_path / ".beadloom" / "config.yml").write_text(
            "scan_paths:\n- Engine\n- Packages/Docks/Sources/Moor\n- Sources/Harbor\n",
            encoding="utf-8",
        )
        for rel_path, text in _SWIFT_PACKAGES.items():
            _write(tmp_path, rel_path, text)
        return c

    def test_each_import_is_recorded_with_the_node_owning_its_target(
        self, tmp_path: Path, swift_conn: sqlite3.Connection
    ) -> None:
        index_imports(tmp_path, swift_conn)
        assert _imports(swift_conn) == {
            ("Sources/Harbor/main.swift", "Engine", "Engine"),
            ("Sources/Harbor/main.swift", "Moor", "Moor"),
            ("Sources/Harbor/main.swift", "Logging", None),
            ("Sources/Harbor/main.swift", "Crypto", None),
            ("Packages/Docks/Sources/Moor/Moor.swift", "Engine", "Engine"),
        }

    def test_the_edges_are_exactly_the_target_imports(
        self, tmp_path: Path, swift_conn: sqlite3.Connection
    ) -> None:
        index_imports(tmp_path, swift_conn)
        assert _depends_on(swift_conn) == {
            ("Harbor", "Engine"),
            ("Harbor", "Moor"),
            ("Moor", "Engine"),
        }

    def test_an_incremental_reindex_resolves_the_same_way(
        self, tmp_path: Path, swift_conn: sqlite3.Connection
    ) -> None:
        index_imports(tmp_path, swift_conn)
        _write(tmp_path, "Sources/Harbor/main.swift", "import Moor\n")
        reindex_file_imports(
            tmp_path, swift_conn, touched=["Sources/Harbor/main.swift"], removed=[]
        )
        assert _depends_on(swift_conn) == {("Harbor", "Moor"), ("Moor", "Engine")}

    def test_without_a_manifest_an_import_is_read_as_before(self, tmp_path: Path) -> None:
        """No ``Package.swift``: a module folder under the scan path, as B3 measured it."""
        c = open_db(tmp_path / "index.db")
        create_schema(c)
        for ref_id, source in (("Core", "Sources/Core/"), ("App", "Sources/App/")):
            c.execute(
                "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, 'domain', '', ?)",
                (ref_id, source),
            )
        c.commit()
        (tmp_path / ".beadloom").mkdir()
        (tmp_path / ".beadloom" / "config.yml").write_text(
            "scan_paths:\n- Sources\n", encoding="utf-8"
        )
        _write(tmp_path, "Sources/Core/Core.swift", "public struct Core {}\n")
        _write(tmp_path, "Sources/App/main.swift", "import Core\n")

        index_imports(tmp_path, c)

        assert _depends_on(c) == {("App", "Core")}

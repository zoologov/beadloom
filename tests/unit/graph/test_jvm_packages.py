"""The package a Java or Kotlin file declares, and the folder an import's package is in.

BDL-076 R2 finding 6 (``beadloom-fht7``), fixed by ``beadloom-ujzb.19``. Kotlin's
coding conventions recommend omitting the common root package from the folders, so a
folder path does not spell the package (``package org.example.network`` in
``src/main/kotlin/network/``). These tests hold the two readings on their own: the
declaration read from a file's text, and an import mapped to the folder of the
package it names through those declarations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.graph.jvm_packages import JvmPackages, declared_package, read_jvm_packages

if TYPE_CHECKING:
    from pathlib import Path


class TestTheDeclaredPackage:
    def test_a_kotlin_declaration(self) -> None:
        assert declared_package("package org.example.network\n\nclass Socket\n") == (
            "org.example.network"
        )

    def test_a_java_declaration(self) -> None:
        assert declared_package("package org.acme.core;\n\npublic class A {}\n") == (
            "org.acme.core"
        )

    def test_after_a_licence_comment_and_file_annotations(self) -> None:
        text = (
            "/*\n * package not.this.one\n */\n"
            "// package nor.this\n"
            '@file:JvmName("Sockets")\n'
            "package org.example.network // trailing\n"
        )
        assert declared_package(text) == "org.example.network"

    def test_backquoted_segments_are_read_without_their_quotes(self) -> None:
        assert declared_package("package org.`fun`.net\n") == "org.fun.net"

    def test_no_declaration_is_the_default_package(self) -> None:
        assert declared_package("class Main\n\nfun main() {}\n") is None
        assert declared_package("") is None

    def test_a_package_word_after_the_first_declaration_is_not_read(self) -> None:
        assert declared_package("import a.b\nclass X {\n  val package = 1\n}\n") is None
        assert declared_package('import a.b\nval s = """\npackage not.a.decl\n"""\n') is None


class TestAnImportNamesTheFolderOfItsPackage:
    def _packages(self) -> JvmPackages:
        return JvmPackages(
            (
                ("org.example.app", "src/main/kotlin/app/Main.kt"),
                ("org.example.network", "src/main/kotlin/network/Socket.kt"),
                ("org.example.network.tcp", "src/main/kotlin/network/tcp/Conn.kt"),
            )
        )

    def test_a_class_a_member_and_a_wildcard(self) -> None:
        packages = self._packages()

        assert packages.directory("org.example.network.Socket") == "src/main/kotlin/network"
        assert packages.directory("org.example.network.Socket.open") == ("src/main/kotlin/network")
        assert packages.directory("org.example.network.*") == "src/main/kotlin/network"

    def test_the_deepest_declared_package_wins(self) -> None:
        assert self._packages().directory("org.example.network.tcp.Conn") == (
            "src/main/kotlin/network/tcp"
        )

    def test_a_package_the_project_does_not_declare_names_nothing(self) -> None:
        packages = self._packages()

        assert packages.directory("org.example.Missing") is None
        assert packages.directory("network.Socket") is None
        assert packages.directory("kotlin.math.abs") is None
        assert packages.package("kotlin.math.abs") is None

    def test_an_empty_set_is_false(self) -> None:
        assert not JvmPackages(())
        assert self._packages()


class TestAPackageDeclaredInTwoFolders:
    """The re-review's finding m5 (``beadloom-ujzb.22``), fixed by ``beadloom-ujzb.24``.

    Until this fix the folder read first kept the package, so an import of a class in
    the second folder resolved to the first: a false edge.
    """

    def _packages(self) -> JvmPackages:
        return JvmPackages(
            (
                ("org.ex.shared", "src/main/kotlin/a/A.kt"),
                ("org.ex.shared", "src/main/kotlin/a/Helpers.kt"),
                ("org.ex.shared", "src/main/kotlin/b/B.kt"),
                ("org.ex.shared", "lib/src/main/java/org/ex/shared/B.java"),
            )
        )

    def test_an_imported_class_reaches_the_folder_holding_it(self) -> None:
        packages = self._packages()

        assert packages.directory("org.ex.shared.A") == "src/main/kotlin/a"
        assert packages.directory("org.ex.shared.A.Companion") == "src/main/kotlin/a"

    def test_the_package_is_still_the_projects(self) -> None:
        assert self._packages().package("org.ex.shared.Anything") == "org.ex.shared"

    def test_a_class_two_folders_hold_reaches_both_and_names_no_one(self) -> None:
        packages = self._packages()

        assert packages.folders("org.ex.shared.B") == (
            "lib/src/main/java/org/ex/shared",
            "src/main/kotlin/b",
        )
        assert packages.directory("org.ex.shared.B") is None

    def test_a_wildcard_or_a_class_no_file_is_named_after_reaches_every_folder(self) -> None:
        packages = self._packages()
        every = ("lib/src/main/java/org/ex/shared", "src/main/kotlin/a", "src/main/kotlin/b")

        assert packages.folders("org.ex.shared.*") == every
        assert packages.folders("org.ex.shared.helperFunction") == every
        assert packages.directory("org.ex.shared.*") is None
        assert packages.directory("org.ex.shared.helperFunction") is None

    def test_a_package_in_one_folder_is_that_folder_whatever_it_names(self) -> None:
        packages = JvmPackages((("org.ex.one", "src/main/kotlin/one/Util.kt"),))

        assert packages.folders("org.ex.one.helper") == ("src/main/kotlin/one",)
        assert packages.directory("org.ex.one.*") == "src/main/kotlin/one"


class TestReadFromTheFiles:
    def test_each_files_folder_under_its_declared_package(self, tmp_path: Path) -> None:
        files = {
            "src/main/kotlin/app/Main.kt": "package org.example.app\n",
            "src/main/kotlin/network/Socket.kt": "package org.example.network\n",
            "src/main/kotlin/Loose.kt": "fun loose() = 1\n",
            "src/main/java/org/acme/A.java": "package org.acme;\n",
        }
        for rel_path, text in files.items():
            path = tmp_path / rel_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

        packages = read_jvm_packages(tmp_path, sorted(tmp_path / f for f in files))

        assert packages.directory("org.example.network.Socket") == "src/main/kotlin/network"
        assert packages.directory("org.example.app.main") == "src/main/kotlin/app"
        assert packages.directory("org.acme.A") == "src/main/java/org/acme"

    def test_an_unreadable_file_is_skipped(self, tmp_path: Path) -> None:
        (tmp_path / "Bad.kt").write_bytes(b"\xff\xfepackage x\n")

        assert not read_jvm_packages(tmp_path, [tmp_path / "Bad.kt", tmp_path / "Gone.kt"])

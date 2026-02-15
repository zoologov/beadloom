"""Tests for Kotlin language support (BEAD-13)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.context_oracle.code_indexer import clear_cache, extract_symbols, get_lang_config

if TYPE_CHECKING:
    from pathlib import Path


def _kotlin_available() -> bool:
    try:
        import tree_sitter_kotlin  # noqa: F401

        return True
    except ImportError:
        return False


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    clear_cache()


# ---------------------------------------------------------------------------
# Symbol extraction tests
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _kotlin_available(), reason="tree-sitter-kotlin not installed")
class TestKotlinSymbols:
    def test_extract_class(self, tmp_path: Path) -> None:
        kt = tmp_path / "Model.kt"
        kt.write_text('class User {\n    val name: String = ""\n}\n')
        symbols = extract_symbols(kt)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "User"
        assert symbols[0]["kind"] == "class"

    def test_extract_function(self, tmp_path: Path) -> None:
        kt = tmp_path / "main.kt"
        kt.write_text('fun main(args: Array<String>) {\n    println("Hello")\n}\n')
        symbols = extract_symbols(kt)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "main"
        assert symbols[0]["kind"] == "function"

    def test_extract_data_class(self, tmp_path: Path) -> None:
        kt = tmp_path / "Data.kt"
        kt.write_text("data class Point(val x: Int, val y: Int)\n")
        symbols = extract_symbols(kt)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "Point"
        assert symbols[0]["kind"] == "class"

    def test_extract_object(self, tmp_path: Path) -> None:
        kt = tmp_path / "Singleton.kt"
        kt.write_text("object Database {\n    fun connect() {}\n}\n")
        symbols = extract_symbols(kt)
        assert any(s["symbol_name"] == "Database" for s in symbols)
        db = next(s for s in symbols if s["symbol_name"] == "Database")
        assert db["kind"] == "class"

    def test_extract_interface(self, tmp_path: Path) -> None:
        kt = tmp_path / "Drawable.kt"
        kt.write_text("interface Drawable {\n    fun draw()\n}\n")
        symbols = extract_symbols(kt)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "Drawable"
        # interface is parsed as class_declaration -> kind "class"
        assert symbols[0]["kind"] == "class"

    def test_annotation_propagation(self, tmp_path: Path) -> None:
        kt = tmp_path / "annotated.kt"
        kt.write_text("// beadloom:domain=auth\nclass AuthService {\n}\n")
        symbols = extract_symbols(kt)
        assert symbols[0]["annotations"].get("domain") == "auth"

    def test_module_annotation_applies_to_all(self, tmp_path: Path) -> None:
        kt = tmp_path / "module.kt"
        kt.write_text("// beadloom:domain=api\n\nfun handler() {}\n\nfun processor() {}\n")
        symbols = extract_symbols(kt)
        handler = next(s for s in symbols if s["symbol_name"] == "handler")
        processor = next(s for s in symbols if s["symbol_name"] == "processor")
        assert handler["annotations"] == {"domain": "api"}
        assert processor["annotations"] == {"domain": "api"}

    def test_block_comment_annotation(self, tmp_path: Path) -> None:
        kt = tmp_path / "block.kt"
        kt.write_text("/* beadloom:domain=auth */\nclass AuthService {}\n")
        symbols = extract_symbols(kt)
        assert symbols[0]["annotations"].get("domain") == "auth"

    def test_kts_extension(self, tmp_path: Path) -> None:
        kts = tmp_path / "build.gradle.kts"
        kts.write_text("fun configure() {}\n")
        symbols = extract_symbols(kts)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "configure"

    def test_empty_file(self, tmp_path: Path) -> None:
        kt = tmp_path / "empty.kt"
        kt.write_text("")
        symbols = extract_symbols(kt)
        assert symbols == []

    def test_multiple_symbols(self, tmp_path: Path) -> None:
        kt = tmp_path / "multi.kt"
        kt.write_text("class Foo {}\n\nfun bar() {}\n\nobject Baz {}\n")
        symbols = extract_symbols(kt)
        names = {s["symbol_name"] for s in symbols}
        assert names == {"Foo", "bar", "Baz"}


# ---------------------------------------------------------------------------
# Import extraction tests
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _kotlin_available(), reason="tree-sitter-kotlin not installed")
class TestKotlinImports:
    def test_extract_imports(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import extract_imports

        kt = tmp_path / "test.kt"
        kt.write_text(
            "import com.example.service.UserService\n"
            "import kotlin.collections.List\n\n"
            "fun main() {}\n"
        )
        imports = extract_imports(kt)
        paths = [i.import_path for i in imports]
        assert "com.example.service.UserService" in paths
        # kotlin.* should be skipped
        assert not any(p.startswith("kotlin.") for p in paths)

    def test_skip_java_stdlib(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import extract_imports

        kt = tmp_path / "test.kt"
        kt.write_text("import java.util.List\nimport com.myapp.Model\n\nclass Foo {}\n")
        imports = extract_imports(kt)
        paths = [i.import_path for i in imports]
        assert not any(p.startswith("java.") for p in paths)
        assert "com.myapp.Model" in paths

    def test_skip_android_stdlib(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import extract_imports

        kt = tmp_path / "test.kt"
        kt.write_text("import android.os.Bundle\nimport com.myapp.Activity\n\nclass Main {}\n")
        imports = extract_imports(kt)
        paths = [i.import_path for i in imports]
        assert not any(p.startswith("android.") for p in paths)
        assert "com.myapp.Activity" in paths

    def test_skip_kotlinx_stdlib(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import extract_imports

        kt = tmp_path / "test.kt"
        kt.write_text(
            "import kotlinx.coroutines.launch\nimport com.myapp.Service\n\nfun main() {}\n"
        )
        imports = extract_imports(kt)
        paths = [i.import_path for i in imports]
        assert not any(p.startswith("kotlinx.") for p in paths)
        assert "com.myapp.Service" in paths

    def test_import_line_numbers(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import extract_imports

        kt = tmp_path / "test.kt"
        kt.write_text("import com.example.First\nimport com.example.Second\n\nfun main() {}\n")
        imports = extract_imports(kt)
        assert len(imports) == 2
        assert imports[0].line_number == 1
        assert imports[1].line_number == 2

    def test_no_imports(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import extract_imports

        kt = tmp_path / "test.kt"
        kt.write_text("fun main() {}\n")
        imports = extract_imports(kt)
        assert imports == []

    def test_kts_imports(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import extract_imports

        kts = tmp_path / "build.gradle.kts"
        kts.write_text("import com.example.BuildConfig\n\nfun configure() {}\n")
        imports = extract_imports(kts)
        paths = [i.import_path for i in imports]
        assert "com.example.BuildConfig" in paths


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------


class TestKotlinRegistration:
    def test_kt_in_code_extensions(self) -> None:
        from beadloom.infrastructure.reindex import _CODE_EXTENSIONS

        assert ".kt" in _CODE_EXTENSIONS
        assert ".kts" in _CODE_EXTENSIONS

    def test_lang_config_available(self) -> None:
        if not _kotlin_available():
            pytest.skip("tree-sitter-kotlin not installed")
        config = get_lang_config(".kt")
        assert config is not None
        assert config.symbol_types  # non-empty

    def test_kts_lang_config_available(self) -> None:
        if not _kotlin_available():
            pytest.skip("tree-sitter-kotlin not installed")
        config = get_lang_config(".kts")
        assert config is not None
        assert config.symbol_types  # non-empty

    def test_lang_config_comment_types(self) -> None:
        if not _kotlin_available():
            pytest.skip("tree-sitter-kotlin not installed")
        config = get_lang_config(".kt")
        assert config is not None
        assert "line_comment" in config.comment_types
        assert "block_comment" in config.comment_types

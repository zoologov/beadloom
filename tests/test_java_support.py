"""Tests for Java language support (BEAD-14)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.context_oracle.code_indexer import clear_cache, extract_symbols, get_lang_config

if TYPE_CHECKING:
    from pathlib import Path


def _java_available() -> bool:
    try:
        import tree_sitter_java  # noqa: F401

        return True
    except ImportError:
        return False


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    clear_cache()


# ---------------------------------------------------------------------------
# Symbol extraction tests
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _java_available(), reason="tree-sitter-java not installed")
class TestJavaSymbols:
    def test_extract_class(self, tmp_path: Path) -> None:
        java = tmp_path / "User.java"
        java.write_text('public class User {\n    private String name = "";\n}\n')
        symbols = extract_symbols(java)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "User"
        assert symbols[0]["kind"] == "class"

    def test_extract_interface(self, tmp_path: Path) -> None:
        java = tmp_path / "UserRepository.java"
        java.write_text("public interface UserRepository {\n    void findAll();\n}\n")
        symbols = extract_symbols(java)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "UserRepository"
        assert symbols[0]["kind"] == "type"

    def test_extract_enum(self, tmp_path: Path) -> None:
        java = tmp_path / "Status.java"
        java.write_text("public enum Status {\n    ACTIVE, INACTIVE\n}\n")
        symbols = extract_symbols(java)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "Status"
        assert symbols[0]["kind"] == "class"

    def test_extract_record(self, tmp_path: Path) -> None:
        java = tmp_path / "Point.java"
        java.write_text("public record Point(int x, int y) {}\n")
        symbols = extract_symbols(java)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "Point"
        assert symbols[0]["kind"] == "class"

    def test_extract_annotation_type(self, tmp_path: Path) -> None:
        java = tmp_path / "MyAnnotation.java"
        java.write_text("public @interface MyAnnotation {\n    String value();\n}\n")
        symbols = extract_symbols(java)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "MyAnnotation"
        assert symbols[0]["kind"] == "type"

    def test_extract_annotations_on_class(self, tmp_path: Path) -> None:
        java = tmp_path / "Controller.java"
        java.write_text(
            "@RestController\n"
            "@Service\n"
            "public class UserController {\n"
            "    public void getUser() {}\n"
            "}\n"
        )
        symbols = extract_symbols(java)
        # The class_declaration includes the annotations as modifiers,
        # so the top-level child is the class_declaration itself.
        cls = next(s for s in symbols if s["symbol_name"] == "UserController")
        assert cls["kind"] == "class"

    def test_annotation_propagation(self, tmp_path: Path) -> None:
        java = tmp_path / "annotated.java"
        java.write_text("// beadloom:domain=auth\npublic class AuthService {\n}\n")
        symbols = extract_symbols(java)
        assert symbols[0]["annotations"].get("domain") == "auth"

    def test_module_annotation_applies_to_all(self, tmp_path: Path) -> None:
        java = tmp_path / "module.java"
        java.write_text(
            "// beadloom:domain=api\n\npublic class Handler {\n}\n\nclass Processor {\n}\n"
        )
        symbols = extract_symbols(java)
        handler = next(s for s in symbols if s["symbol_name"] == "Handler")
        processor = next(s for s in symbols if s["symbol_name"] == "Processor")
        assert handler["annotations"] == {"domain": "api"}
        assert processor["annotations"] == {"domain": "api"}

    def test_block_comment_annotation(self, tmp_path: Path) -> None:
        java = tmp_path / "block.java"
        java.write_text("/* beadloom:domain=auth */\npublic class AuthService {}\n")
        symbols = extract_symbols(java)
        assert symbols[0]["annotations"].get("domain") == "auth"

    def test_multiple_symbols(self, tmp_path: Path) -> None:
        java = tmp_path / "multi.java"
        java.write_text("public class Foo {}\n\ninterface Bar {}\n\nenum Baz { A, B }\n")
        symbols = extract_symbols(java)
        names = {s["symbol_name"] for s in symbols}
        assert names == {"Foo", "Bar", "Baz"}

    def test_empty_file(self, tmp_path: Path) -> None:
        java = tmp_path / "empty.java"
        java.write_text("")
        symbols = extract_symbols(java)
        assert symbols == []


# ---------------------------------------------------------------------------
# Import extraction tests
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _java_available(), reason="tree-sitter-java not installed")
class TestJavaImports:
    def test_extract_imports(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import extract_imports

        java = tmp_path / "Test.java"
        java.write_text(
            "import com.example.service.UserService;\n"
            "import java.util.List;\n\n"
            "public class Test {}\n"
        )
        imports = extract_imports(java)
        paths = [i.import_path for i in imports]
        assert "com.example.service.UserService" in paths
        # java.* should be skipped
        assert not any(p.startswith("java.") for p in paths)

    def test_skip_java_stdlib(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import extract_imports

        java = tmp_path / "Test.java"
        java.write_text(
            "import java.util.List;\n"
            "import javax.persistence.Entity;\n"
            "import com.myapp.Model;\n\n"
            "public class Test {}\n"
        )
        imports = extract_imports(java)
        paths = [i.import_path for i in imports]
        assert not any(p.startswith("java.") for p in paths)
        assert not any(p.startswith("javax.") for p in paths)
        assert "com.myapp.Model" in paths

    def test_skip_android_imports(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import extract_imports

        java = tmp_path / "Test.java"
        java.write_text(
            "import android.os.Bundle;\nimport com.myapp.Activity;\n\npublic class Test {}\n"
        )
        imports = extract_imports(java)
        paths = [i.import_path for i in imports]
        assert not any(p.startswith("android.") for p in paths)
        assert "com.myapp.Activity" in paths

    def test_skip_sun_imports(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import extract_imports

        java = tmp_path / "Test.java"
        java.write_text(
            "import sun.misc.Unsafe;\n"
            "import com.sun.net.httpserver.HttpServer;\n"
            "import com.myapp.Server;\n\n"
            "public class Test {}\n"
        )
        imports = extract_imports(java)
        paths = [i.import_path for i in imports]
        assert not any(p.startswith("sun.") for p in paths)
        assert not any(p.startswith("com.sun.") for p in paths)
        assert "com.myapp.Server" in paths

    def test_import_line_numbers(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import extract_imports

        java = tmp_path / "Test.java"
        java.write_text(
            "import com.example.First;\nimport com.example.Second;\n\npublic class Test {}\n"
        )
        imports = extract_imports(java)
        assert len(imports) == 2
        assert imports[0].line_number == 1
        assert imports[1].line_number == 2

    def test_no_imports(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import extract_imports

        java = tmp_path / "Test.java"
        java.write_text("public class Test {}\n")
        imports = extract_imports(java)
        assert imports == []

    def test_wildcard_imports(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import extract_imports

        java = tmp_path / "Test.java"
        java.write_text(
            "import com.example.utils.*;\nimport java.util.*;\n\npublic class Test {}\n"
        )
        imports = extract_imports(java)
        paths = [i.import_path for i in imports]
        assert "com.example.utils.*" in paths
        # java.util.* should be skipped
        assert not any(p.startswith("java.") for p in paths)

    def test_static_imports(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import extract_imports

        java = tmp_path / "Test.java"
        java.write_text(
            "import static com.example.Constants.MAX_SIZE;\n"
            "import static java.lang.Math.PI;\n\n"
            "public class Test {}\n"
        )
        imports = extract_imports(java)
        paths = [i.import_path for i in imports]
        # Static import of com.example.Constants should be extracted
        assert any("com.example.Constants" in p for p in paths)
        # java.lang.* should be skipped
        assert not any(p.startswith("java.") for p in paths)


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------


class TestJavaRegistration:
    def test_java_in_code_extensions(self) -> None:
        from beadloom.infrastructure.reindex import _CODE_EXTENSIONS

        assert ".java" in _CODE_EXTENSIONS

    def test_java_in_extension_loaders(self) -> None:
        from beadloom.context_oracle.code_indexer import _EXTENSION_LOADERS

        assert ".java" in _EXTENSION_LOADERS

    def test_lang_config_available(self) -> None:
        if not _java_available():
            pytest.skip("tree-sitter-java not installed")
        config = get_lang_config(".java")
        assert config is not None
        assert config.symbol_types  # non-empty

    def test_lang_config_comment_types(self) -> None:
        if not _java_available():
            pytest.skip("tree-sitter-java not installed")
        config = get_lang_config(".java")
        assert config is not None
        assert "line_comment" in config.comment_types
        assert "block_comment" in config.comment_types

    def test_lang_config_symbol_types(self) -> None:
        if not _java_available():
            pytest.skip("tree-sitter-java not installed")
        config = get_lang_config(".java")
        assert config is not None
        assert "class_declaration" in config.symbol_types
        assert "interface_declaration" in config.symbol_types
        assert "enum_declaration" in config.symbol_types
        assert "record_declaration" in config.symbol_types
        assert "method_declaration" in config.symbol_types
        assert "annotation_type_declaration" in config.symbol_types

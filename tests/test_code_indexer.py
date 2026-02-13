"""Tests for beadloom.code_indexer — tree-sitter symbol extraction + annotations."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.context_oracle.code_indexer import (
    clear_cache,
    extract_symbols,
    get_lang_config,
    parse_annotations,
    supported_extensions,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(autouse=True)
def _clear_lang_cache() -> None:
    """Clear language cache before each test to avoid cross-test pollution."""
    clear_cache()


# --- parse_annotations ---


class TestParseAnnotations:
    def test_single_annotation(self) -> None:
        line = "# beadloom:feature=PROJ-123"
        result = parse_annotations(line)
        assert result == {"feature": "PROJ-123"}

    def test_multiple_annotations(self) -> None:
        line = "# beadloom:feature=PROJ-123 domain=routing entity=Track"
        result = parse_annotations(line)
        assert result == {"feature": "PROJ-123", "domain": "routing", "entity": "Track"}

    def test_no_annotation(self) -> None:
        line = "# just a regular comment"
        result = parse_annotations(line)
        assert result == {}

    def test_empty_string(self) -> None:
        assert parse_annotations("") == {}

    def test_annotation_with_service(self) -> None:
        line = "# beadloom:service=api-gw"
        result = parse_annotations(line)
        assert result == {"service": "api-gw"}

    def test_annotation_with_adr(self) -> None:
        line = "# beadloom:adr=ADR-015"
        result = parse_annotations(line)
        assert result == {"adr": "ADR-015"}


# --- extract_symbols ---


class TestExtractSymbols:
    def test_extract_function(self, tmp_path: Path) -> None:
        py = tmp_path / "module.py"
        py.write_text("def hello():\n    pass\n")
        symbols = extract_symbols(py)
        assert len(symbols) == 1
        assert symbols[0]["symbol_name"] == "hello"
        assert symbols[0]["kind"] == "function"
        assert symbols[0]["line_start"] == 1
        assert symbols[0]["line_end"] == 2

    def test_extract_class(self, tmp_path: Path) -> None:
        py = tmp_path / "models.py"
        py.write_text("class User:\n    name: str\n    age: int\n")
        symbols = extract_symbols(py)
        assert len(symbols) == 1
        assert symbols[0]["symbol_name"] == "User"
        assert symbols[0]["kind"] == "class"

    def test_extract_multiple(self, tmp_path: Path) -> None:
        py = tmp_path / "multi.py"
        py.write_text("class Foo:\n    pass\n\ndef bar():\n    pass\n\ndef baz():\n    pass\n")
        symbols = extract_symbols(py)
        names = {s["symbol_name"] for s in symbols}
        assert names == {"Foo", "bar", "baz"}

    def test_method_inside_class(self, tmp_path: Path) -> None:
        """Methods are NOT top-level symbols — only top-level defs are extracted."""
        py = tmp_path / "cls.py"
        py.write_text("class A:\n    def method(self):\n        pass\n")
        symbols = extract_symbols(py)
        # Only class A, not method
        assert len(symbols) == 1
        assert symbols[0]["symbol_name"] == "A"

    def test_annotation_attached_to_symbol(self, tmp_path: Path) -> None:
        py = tmp_path / "annotated.py"
        py.write_text("# beadloom:feature=PROJ-1 domain=routing\ndef list_tracks():\n    pass\n")
        symbols = extract_symbols(py)
        assert len(symbols) == 1
        assert symbols[0]["annotations"] == {"feature": "PROJ-1", "domain": "routing"}

    def test_annotation_only_applies_to_next_symbol(self, tmp_path: Path) -> None:
        """Non-module annotation between symbols only applies to the next one."""
        py = tmp_path / "two.py"
        py.write_text(
            "def first():\n    pass\n\n"
            "# beadloom:feature=F1\n"
            "def second():\n    pass\n\n"
            "def third():\n    pass\n"
        )
        symbols = extract_symbols(py)
        first = next(s for s in symbols if s["symbol_name"] == "first")
        second = next(s for s in symbols if s["symbol_name"] == "second")
        third = next(s for s in symbols if s["symbol_name"] == "third")
        assert first["annotations"] == {}
        assert second["annotations"] == {"feature": "F1"}
        assert third["annotations"] == {}

    def test_module_level_annotation_applies_to_all_symbols(
        self,
        tmp_path: Path,
    ) -> None:
        """Module-level annotation at top applies to every symbol in the file."""
        # Arrange
        py = tmp_path / "mod_ann.py"
        py.write_text(
            "# beadloom:domain=context-oracle\n"
            "\n"
            "import os\n"
            "\n"
            "def handler():\n"
            "    pass\n"
            "\n"
            "def processor():\n"
            "    pass\n"
        )

        # Act
        symbols = extract_symbols(py)

        # Assert
        handler = next(s for s in symbols if s["symbol_name"] == "handler")
        processor = next(s for s in symbols if s["symbol_name"] == "processor")
        assert handler["annotations"] == {"domain": "context-oracle"}
        assert processor["annotations"] == {"domain": "context-oracle"}

    def test_module_annotation_with_symbol_specific_override(
        self,
        tmp_path: Path,
    ) -> None:
        """Symbol-specific annotation merges with module-level annotation."""
        # Arrange
        py = tmp_path / "merge.py"
        py.write_text(
            "# beadloom:domain=context-oracle\n"
            "\n"
            "import os\n"
            "\n"
            "# beadloom:feature=PROJ-42\n"
            "def handler():\n"
            "    pass\n"
        )

        # Act
        symbols = extract_symbols(py)

        # Assert
        handler = symbols[0]
        assert handler["annotations"] == {
            "domain": "context-oracle",
            "feature": "PROJ-42",
        }

    def test_module_annotation_symbol_specific_overrides_key(
        self,
        tmp_path: Path,
    ) -> None:
        """Symbol-specific annotation overrides same key from module annotation."""
        # Arrange
        py = tmp_path / "override.py"
        py.write_text(
            "# beadloom:domain=global-default\n"
            "\n"
            "import os\n"
            "\n"
            "# beadloom:domain=special\n"
            "def handler():\n"
            "    pass\n"
        )

        # Act
        symbols = extract_symbols(py)

        # Assert
        handler = symbols[0]
        assert handler["annotations"] == {"domain": "special"}

    def test_module_annotation_after_symbol_not_applied(
        self,
        tmp_path: Path,
    ) -> None:
        """Annotation after first symbol does NOT become module-level."""
        # Arrange
        py = tmp_path / "late_ann.py"
        py.write_text(
            "def first():\n"
            "    pass\n"
            "\n"
            "# beadloom:domain=late\n"
            "def second():\n"
            "    pass\n"
            "\n"
            "def third():\n"
            "    pass\n"
        )

        # Act
        symbols = extract_symbols(py)

        # Assert
        first = next(s for s in symbols if s["symbol_name"] == "first")
        second = next(s for s in symbols if s["symbol_name"] == "second")
        third = next(s for s in symbols if s["symbol_name"] == "third")
        assert first["annotations"] == {}
        assert second["annotations"] == {"domain": "late"}
        assert third["annotations"] == {}

    def test_file_hash(self, tmp_path: Path) -> None:
        import hashlib

        content = "def foo():\n    pass\n"
        py = tmp_path / "h.py"
        py.write_text(content)
        symbols = extract_symbols(py)
        expected = hashlib.sha256(content.encode()).hexdigest()
        assert symbols[0]["file_hash"] == expected

    def test_empty_file(self, tmp_path: Path) -> None:
        py = tmp_path / "empty.py"
        py.write_text("")
        symbols = extract_symbols(py)
        assert symbols == []

    def test_async_function(self, tmp_path: Path) -> None:
        py = tmp_path / "async_mod.py"
        py.write_text("async def handler():\n    pass\n")
        symbols = extract_symbols(py)
        assert len(symbols) == 1
        assert symbols[0]["symbol_name"] == "handler"
        assert symbols[0]["kind"] == "function"

    def test_decorated_function(self, tmp_path: Path) -> None:
        py = tmp_path / "deco.py"
        py.write_text("@app.route('/foo')\ndef foo_handler():\n    pass\n")
        symbols = extract_symbols(py)
        assert len(symbols) == 1
        assert symbols[0]["symbol_name"] == "foo_handler"


# --- get_lang_config / supported_extensions ---


class TestGetLangConfig:
    def test_python_available(self) -> None:
        config = get_lang_config(".py")
        assert config is not None
        assert "function_definition" in config.symbol_types

    def test_unknown_extension_returns_none(self) -> None:
        config = get_lang_config(".xyz")
        assert config is None

    def test_caching(self) -> None:
        """Second call returns cached result."""
        first = get_lang_config(".py")
        second = get_lang_config(".py")
        assert first is second

    def test_supported_extensions_includes_python(self) -> None:
        exts = supported_extensions()
        assert ".py" in exts


# --- Multi-language extract_symbols ---


def _ts_available() -> bool:
    try:
        import tree_sitter_typescript  # noqa: F401

        return True
    except ImportError:
        return False


def _go_available() -> bool:
    try:
        import tree_sitter_go  # noqa: F401

        return True
    except ImportError:
        return False


def _rust_available() -> bool:
    try:
        import tree_sitter_rust  # noqa: F401

        return True
    except ImportError:
        return False


class TestExtractSymbolsTypeScript:
    """Tests for TypeScript symbol extraction."""

    @pytest.mark.skipif(not _ts_available(), reason="tree-sitter-typescript not installed")
    def test_function_declaration(self, tmp_path: Path) -> None:
        ts_file = tmp_path / "app.ts"
        ts_file.write_text("function greet(name: string): string {\n  return name;\n}\n")
        symbols = extract_symbols(ts_file)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "greet"
        assert symbols[0]["kind"] == "function"

    @pytest.mark.skipif(not _ts_available(), reason="tree-sitter-typescript not installed")
    def test_class_declaration(self, tmp_path: Path) -> None:
        ts_file = tmp_path / "model.ts"
        ts_file.write_text(
            "class User {\n"
            "  name: string;\n"
            "  constructor(name: string) {\n"
            "    this.name = name;\n"
            "  }\n"
            "}\n"
        )
        symbols = extract_symbols(ts_file)
        assert len(symbols) >= 1
        assert any(s["symbol_name"] == "User" and s["kind"] == "class" for s in symbols)

    @pytest.mark.skipif(not _ts_available(), reason="tree-sitter-typescript not installed")
    def test_interface_declaration(self, tmp_path: Path) -> None:
        ts_file = tmp_path / "types.ts"
        ts_file.write_text("interface Config {\n  host: string;\n  port: number;\n}\n")
        symbols = extract_symbols(ts_file)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "Config"
        assert symbols[0]["kind"] == "type"

    @pytest.mark.skipif(not _ts_available(), reason="tree-sitter-typescript not installed")
    def test_type_alias(self, tmp_path: Path) -> None:
        ts_file = tmp_path / "alias.ts"
        ts_file.write_text("type ID = string | number;\n")
        symbols = extract_symbols(ts_file)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "ID"
        assert symbols[0]["kind"] == "type"

    @pytest.mark.skipif(not _ts_available(), reason="tree-sitter-typescript not installed")
    def test_export_unwrapping(self, tmp_path: Path) -> None:
        """Exported declarations should be unwrapped to find the actual definition."""
        ts_file = tmp_path / "exported.ts"
        ts_file.write_text("export function handler(): void {}\n")
        symbols = extract_symbols(ts_file)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "handler"
        assert symbols[0]["kind"] == "function"

    @pytest.mark.skipif(not _ts_available(), reason="tree-sitter-typescript not installed")
    def test_annotation_in_typescript(self, tmp_path: Path) -> None:
        """Beadloom annotations should work in TypeScript comments."""
        ts_file = tmp_path / "annotated.ts"
        ts_file.write_text("// beadloom:feature=AUTH-1\nfunction login(): void {}\n")
        symbols = extract_symbols(ts_file)
        assert len(symbols) >= 1
        assert symbols[0]["annotations"] == {"feature": "AUTH-1"}

    @pytest.mark.skipif(not _ts_available(), reason="tree-sitter-typescript not installed")
    def test_js_uses_typescript_parser(self, tmp_path: Path) -> None:
        """JavaScript files should use the TypeScript parser."""
        js_file = tmp_path / "app.js"
        js_file.write_text("function main() {}\n")
        symbols = extract_symbols(js_file)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "main"

    @pytest.mark.skipif(not _ts_available(), reason="tree-sitter-typescript not installed")
    def test_tsx_file(self, tmp_path: Path) -> None:
        """TSX files should use the TSX parser."""
        tsx_file = tmp_path / "component.tsx"
        tsx_file.write_text("function App(): JSX.Element {\n  return <div>Hello</div>;\n}\n")
        symbols = extract_symbols(tsx_file)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "App"


class TestExtractSymbolsGo:
    """Tests for Go symbol extraction."""

    @pytest.mark.skipif(not _go_available(), reason="tree-sitter-go not installed")
    def test_function_declaration(self, tmp_path: Path) -> None:
        go_file = tmp_path / "main.go"
        go_file.write_text('package main\n\nfunc Hello() string {\n\treturn "hello"\n}\n')
        symbols = extract_symbols(go_file)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "Hello"
        assert symbols[0]["kind"] == "function"

    @pytest.mark.skipif(not _go_available(), reason="tree-sitter-go not installed")
    def test_method_declaration(self, tmp_path: Path) -> None:
        go_file = tmp_path / "server.go"
        go_file.write_text("package main\n\ntype Server struct{}\n\nfunc (s *Server) Start() {}\n")
        symbols = extract_symbols(go_file)
        methods = [s for s in symbols if s["symbol_name"] == "Start"]
        assert len(methods) >= 1
        assert methods[0]["kind"] == "function"

    @pytest.mark.skipif(not _go_available(), reason="tree-sitter-go not installed")
    def test_type_declaration_struct(self, tmp_path: Path) -> None:
        go_file = tmp_path / "types.go"
        go_file.write_text("package main\n\ntype Config struct {\n\tHost string\n\tPort int\n}\n")
        symbols = extract_symbols(go_file)
        assert any(s["symbol_name"] == "Config" and s["kind"] == "type" for s in symbols)

    @pytest.mark.skipif(not _go_available(), reason="tree-sitter-go not installed")
    def test_annotation_in_go(self, tmp_path: Path) -> None:
        """Beadloom annotations should work in Go comments."""
        go_file = tmp_path / "annotated.go"
        go_file.write_text("package main\n\n// beadloom:domain=api\nfunc ServeHTTP() {}\n")
        symbols = extract_symbols(go_file)
        assert len(symbols) >= 1
        assert symbols[0]["annotations"] == {"domain": "api"}


class TestExtractSymbolsRust:
    """Tests for Rust symbol extraction."""

    @pytest.mark.skipif(not _rust_available(), reason="tree-sitter-rust not installed")
    def test_function_item(self, tmp_path: Path) -> None:
        rs_file = tmp_path / "lib.rs"
        rs_file.write_text('fn greet(name: &str) -> String {\n    format!("Hello, {}", name)\n}\n')
        symbols = extract_symbols(rs_file)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "greet"
        assert symbols[0]["kind"] == "function"

    @pytest.mark.skipif(not _rust_available(), reason="tree-sitter-rust not installed")
    def test_struct_item(self, tmp_path: Path) -> None:
        rs_file = tmp_path / "model.rs"
        rs_file.write_text("struct User {\n    name: String,\n    age: u32,\n}\n")
        symbols = extract_symbols(rs_file)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "User"
        assert symbols[0]["kind"] == "class"

    @pytest.mark.skipif(not _rust_available(), reason="tree-sitter-rust not installed")
    def test_enum_item(self, tmp_path: Path) -> None:
        rs_file = tmp_path / "enums.rs"
        rs_file.write_text("enum Color {\n    Red,\n    Green,\n    Blue,\n}\n")
        symbols = extract_symbols(rs_file)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "Color"
        assert symbols[0]["kind"] == "type"

    @pytest.mark.skipif(not _rust_available(), reason="tree-sitter-rust not installed")
    def test_trait_item(self, tmp_path: Path) -> None:
        rs_file = tmp_path / "traits.rs"
        rs_file.write_text("trait Drawable {\n    fn draw(&self);\n}\n")
        symbols = extract_symbols(rs_file)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "Drawable"
        assert symbols[0]["kind"] == "type"

    @pytest.mark.skipif(not _rust_available(), reason="tree-sitter-rust not installed")
    def test_annotation_in_rust(self, tmp_path: Path) -> None:
        """Beadloom annotations should work in Rust line comments."""
        rs_file = tmp_path / "annotated.rs"
        rs_file.write_text("// beadloom:domain=auth\nfn authenticate() {}\n")
        symbols = extract_symbols(rs_file)
        assert len(symbols) >= 1
        assert symbols[0]["annotations"] == {"domain": "auth"}

    @pytest.mark.skipif(not _rust_available(), reason="tree-sitter-rust not installed")
    def test_multiple_symbols(self, tmp_path: Path) -> None:
        rs_file = tmp_path / "multi.rs"
        rs_file.write_text(
            "fn foo() {}\n\nstruct Bar {\n    x: i32,\n}\n\nenum Baz {\n    A,\n    B,\n}\n"
        )
        symbols = extract_symbols(rs_file)
        names = {s["symbol_name"] for s in symbols}
        assert names == {"foo", "Bar", "Baz"}


class TestExtractSymbolsUnsupported:
    """Tests for unsupported file extensions."""

    def test_csv_returns_empty(self, tmp_path: Path) -> None:
        f = tmp_path / "data.csv"
        f.write_text("a,b,c\n1,2,3\n")
        symbols = extract_symbols(f)
        assert symbols == []

    def test_txt_returns_empty(self, tmp_path: Path) -> None:
        f = tmp_path / "notes.txt"
        f.write_text("hello world\n")
        symbols = extract_symbols(f)
        assert symbols == []

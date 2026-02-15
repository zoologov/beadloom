"""Tests for Swift language support (BEAD-15)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.context_oracle.code_indexer import clear_cache, extract_symbols, get_lang_config

if TYPE_CHECKING:
    from pathlib import Path


def _swift_available() -> bool:
    try:
        import tree_sitter_swift  # noqa: F401

        return True
    except ImportError:
        return False


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    clear_cache()


# ---------------------------------------------------------------------------
# Symbol extraction tests
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _swift_available(), reason="tree-sitter-swift not installed")
class TestSwiftSymbols:
    def test_extract_class(self, tmp_path: Path) -> None:
        swift = tmp_path / "User.swift"
        swift.write_text('class User {\n    var name: String = ""\n}\n')
        symbols = extract_symbols(swift)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "User"
        assert symbols[0]["kind"] == "class"

    def test_extract_struct(self, tmp_path: Path) -> None:
        swift = tmp_path / "Point.swift"
        swift.write_text("struct Point {\n    var x: Int\n    var y: Int\n}\n")
        symbols = extract_symbols(swift)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "Point"
        assert symbols[0]["kind"] == "class"

    def test_extract_protocol(self, tmp_path: Path) -> None:
        swift = tmp_path / "Drawable.swift"
        swift.write_text("protocol Drawable {\n    func draw()\n}\n")
        symbols = extract_symbols(swift)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "Drawable"
        assert symbols[0]["kind"] == "type"

    def test_extract_function(self, tmp_path: Path) -> None:
        swift = tmp_path / "main.swift"
        swift.write_text('func main() {\n    print("Hello")\n}\n')
        symbols = extract_symbols(swift)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "main"
        assert symbols[0]["kind"] == "function"

    def test_extract_enum(self, tmp_path: Path) -> None:
        swift = tmp_path / "Status.swift"
        swift.write_text("enum Status {\n    case active\n    case inactive\n}\n")
        symbols = extract_symbols(swift)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "Status"
        assert symbols[0]["kind"] == "class"

    def test_annotation_propagation(self, tmp_path: Path) -> None:
        swift = tmp_path / "annotated.swift"
        swift.write_text("// beadloom:domain=auth\nclass AuthService {\n}\n")
        symbols = extract_symbols(swift)
        assert symbols[0]["annotations"].get("domain") == "auth"

    def test_module_annotation_applies_to_all(self, tmp_path: Path) -> None:
        swift = tmp_path / "module.swift"
        swift.write_text("// beadloom:domain=api\n\nfunc handler() {}\n\nfunc processor() {}\n")
        symbols = extract_symbols(swift)
        handler = next(s for s in symbols if s["symbol_name"] == "handler")
        processor = next(s for s in symbols if s["symbol_name"] == "processor")
        assert handler["annotations"] == {"domain": "api"}
        assert processor["annotations"] == {"domain": "api"}

    def test_multiline_comment_annotation(self, tmp_path: Path) -> None:
        swift = tmp_path / "block.swift"
        swift.write_text("/* beadloom:domain=auth */\nclass AuthService {}\n")
        symbols = extract_symbols(swift)
        assert symbols[0]["annotations"].get("domain") == "auth"

    def test_multiple_symbols(self, tmp_path: Path) -> None:
        swift = tmp_path / "multi.swift"
        swift.write_text("class Foo {}\n\nfunc bar() {}\n\nprotocol Baz {}\n\nenum Qux {}\n")
        symbols = extract_symbols(swift)
        names = {s["symbol_name"] for s in symbols}
        assert names == {"Foo", "bar", "Baz", "Qux"}

    def test_empty_file(self, tmp_path: Path) -> None:
        swift = tmp_path / "empty.swift"
        swift.write_text("")
        symbols = extract_symbols(swift)
        assert symbols == []


# ---------------------------------------------------------------------------
# Import extraction tests
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _swift_available(), reason="tree-sitter-swift not installed")
class TestSwiftImports:
    def test_extract_imports(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import extract_imports

        swift = tmp_path / "test.swift"
        swift.write_text("import MyFramework\nimport Foundation\n\nfunc main() {}\n")
        imports = extract_imports(swift)
        paths = [i.import_path for i in imports]
        assert "MyFramework" in paths
        # Foundation should be skipped
        assert "Foundation" not in paths

    def test_skip_apple_frameworks(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import extract_imports

        swift = tmp_path / "test.swift"
        swift.write_text(
            "import UIKit\n"
            "import SwiftUI\n"
            "import Combine\n"
            "import CoreData\n"
            "import CoreGraphics\n"
            "import MapKit\n"
            "import AVFoundation\n"
            "import MyLibrary\n\n"
            "class Foo {}\n"
        )
        imports = extract_imports(swift)
        paths = [i.import_path for i in imports]
        assert "UIKit" not in paths
        assert "SwiftUI" not in paths
        assert "Combine" not in paths
        assert "CoreData" not in paths
        assert "CoreGraphics" not in paths
        assert "MapKit" not in paths
        assert "AVFoundation" not in paths
        assert "MyLibrary" in paths

    def test_keep_third_party_imports(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import extract_imports

        swift = tmp_path / "test.swift"
        swift.write_text(
            "import Alamofire\nimport SnapKit\nimport Foundation\n\nclass Networking {}\n"
        )
        imports = extract_imports(swift)
        paths = [i.import_path for i in imports]
        assert "Alamofire" in paths
        assert "SnapKit" in paths
        assert "Foundation" not in paths

    def test_import_line_numbers(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import extract_imports

        swift = tmp_path / "test.swift"
        swift.write_text("import MyFirst\nimport MySecond\n\nfunc main() {}\n")
        imports = extract_imports(swift)
        assert len(imports) == 2
        assert imports[0].line_number == 1
        assert imports[1].line_number == 2

    def test_no_imports(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import extract_imports

        swift = tmp_path / "test.swift"
        swift.write_text("func main() {}\n")
        imports = extract_imports(swift)
        assert imports == []

    def test_submodule_imports(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import extract_imports

        swift = tmp_path / "test.swift"
        swift.write_text(
            "import MyFramework.SubModule\nimport Foundation.NSObject\n\nclass Foo {}\n"
        )
        imports = extract_imports(swift)
        paths = [i.import_path for i in imports]
        assert "MyFramework.SubModule" in paths
        # Foundation.NSObject should be skipped (root is Foundation)
        assert not any(p.startswith("Foundation") for p in paths)


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------


class TestSwiftRegistration:
    def test_swift_in_code_extensions(self) -> None:
        from beadloom.infrastructure.reindex import _CODE_EXTENSIONS

        assert ".swift" in _CODE_EXTENSIONS

    def test_swift_in_extension_loaders(self) -> None:
        from beadloom.context_oracle.code_indexer import _EXTENSION_LOADERS

        assert ".swift" in _EXTENSION_LOADERS

    def test_lang_config_available(self) -> None:
        if not _swift_available():
            pytest.skip("tree-sitter-swift not installed")
        config = get_lang_config(".swift")
        assert config is not None
        assert config.symbol_types  # non-empty

    def test_lang_config_comment_types(self) -> None:
        if not _swift_available():
            pytest.skip("tree-sitter-swift not installed")
        config = get_lang_config(".swift")
        assert config is not None
        assert "comment" in config.comment_types
        assert "multiline_comment" in config.comment_types

    def test_lang_config_symbol_types(self) -> None:
        if not _swift_available():
            pytest.skip("tree-sitter-swift not installed")
        config = get_lang_config(".swift")
        assert config is not None
        assert "class_declaration" in config.symbol_types
        assert "protocol_declaration" in config.symbol_types
        assert "function_declaration" in config.symbol_types

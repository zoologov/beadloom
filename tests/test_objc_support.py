"""Tests for Objective-C language support (BEAD-17)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.context_oracle.code_indexer import clear_cache, extract_symbols, get_lang_config

if TYPE_CHECKING:
    from pathlib import Path


def _objc_available() -> bool:
    try:
        import tree_sitter_objc  # noqa: F401

        return True
    except ImportError:
        return False


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    clear_cache()


# ---------------------------------------------------------------------------
# Symbol extraction tests
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _objc_available(), reason="tree-sitter-objc not installed")
class TestObjcSymbols:
    def test_extract_class_interface(self, tmp_path: Path) -> None:
        m = tmp_path / "MyClass.m"
        m.write_text("@interface MyClass : NSObject\n- (void)doSomething;\n@end\n")
        symbols = extract_symbols(m)
        assert len(symbols) >= 1
        cls = next(s for s in symbols if s["symbol_name"] == "MyClass")
        assert cls["kind"] == "class"

    def test_extract_class_implementation(self, tmp_path: Path) -> None:
        m = tmp_path / "MyClass.m"
        m.write_text("@implementation MyClass\n- (void)doSomething {\n}\n@end\n")
        symbols = extract_symbols(m)
        assert len(symbols) >= 1
        cls = next(s for s in symbols if s["symbol_name"] == "MyClass")
        assert cls["kind"] == "class"

    def test_extract_protocol(self, tmp_path: Path) -> None:
        m = tmp_path / "MyProtocol.m"
        m.write_text("@protocol MyProtocol\n- (void)requiredMethod;\n@end\n")
        symbols = extract_symbols(m)
        assert len(symbols) >= 1
        proto = next(s for s in symbols if s["symbol_name"] == "MyProtocol")
        assert proto["kind"] == "type"

    def test_extract_function(self, tmp_path: Path) -> None:
        m = tmp_path / "utils.m"
        m.write_text("void freeFunction(int x) {\n    return;\n}\n")
        symbols = extract_symbols(m)
        assert len(symbols) >= 1
        func = next(s for s in symbols if s["symbol_name"] == "freeFunction")
        assert func["kind"] == "function"

    def test_extract_multiple_symbols(self, tmp_path: Path) -> None:
        m = tmp_path / "multi.m"
        m.write_text(
            "@interface Foo : NSObject\n@end\n\n"
            "@implementation Foo\n@end\n\n"
            "@protocol Bar\n@end\n\n"
            "void baz(void) {}\n"
        )
        symbols = extract_symbols(m)
        names = {s["symbol_name"] for s in symbols}
        assert "Foo" in names
        assert "Bar" in names
        assert "baz" in names

    def test_annotation_propagation(self, tmp_path: Path) -> None:
        m = tmp_path / "annotated.m"
        m.write_text("// beadloom:domain=networking\n@interface NetworkClient : NSObject\n@end\n")
        symbols = extract_symbols(m)
        assert symbols[0]["annotations"].get("domain") == "networking"

    def test_module_annotation_applies_to_all(self, tmp_path: Path) -> None:
        m = tmp_path / "module.m"
        m.write_text(
            "// beadloom:domain=api\n\n"
            "@interface Handler : NSObject\n@end\n\n"
            "@protocol Processor\n@end\n"
        )
        symbols = extract_symbols(m)
        handler = next(s for s in symbols if s["symbol_name"] == "Handler")
        processor = next(s for s in symbols if s["symbol_name"] == "Processor")
        assert handler["annotations"] == {"domain": "api"}
        assert processor["annotations"] == {"domain": "api"}

    def test_empty_file(self, tmp_path: Path) -> None:
        m = tmp_path / "empty.m"
        m.write_text("")
        symbols = extract_symbols(m)
        assert symbols == []

    def test_mm_extension(self, tmp_path: Path) -> None:
        """Objective-C++ (.mm) files should also be supported."""
        mm = tmp_path / "MyClass.mm"
        mm.write_text("@interface MyClass : NSObject\n@end\n")
        symbols = extract_symbols(mm)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "MyClass"

    def test_line_numbers(self, tmp_path: Path) -> None:
        m = tmp_path / "lines.m"
        m.write_text("// comment\n\n@interface Foo : NSObject\n@end\n")
        symbols = extract_symbols(m)
        assert len(symbols) >= 1
        # @interface starts on line 3
        assert symbols[0]["line_start"] == 3


# ---------------------------------------------------------------------------
# Import extraction tests
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _objc_available(), reason="tree-sitter-objc not installed")
class TestObjcImports:
    def test_extract_quoted_import(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import extract_imports

        m = tmp_path / "test.m"
        m.write_text('#import "MyHeader.h"\n\n@interface Foo : NSObject\n@end\n')
        imports = extract_imports(m)
        paths = [i.import_path for i in imports]
        assert "MyHeader.h" in paths

    def test_skip_system_framework_angle_import(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import extract_imports

        m = tmp_path / "test.m"
        m.write_text(
            "#import <Foundation/Foundation.h>\n"
            "#import <UIKit/UIKit.h>\n"
            '#import "MyHeader.h"\n'
            "\n@interface Foo : NSObject\n@end\n"
        )
        imports = extract_imports(m)
        paths = [i.import_path for i in imports]
        assert "Foundation/Foundation.h" not in paths
        assert "UIKit/UIKit.h" not in paths
        assert "MyHeader.h" in paths

    def test_extract_module_import(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import extract_imports

        m = tmp_path / "test.m"
        m.write_text("@import MyModule;\n\n@interface Foo : NSObject\n@end\n")
        imports = extract_imports(m)
        paths = [i.import_path for i in imports]
        assert "MyModule" in paths

    def test_skip_system_module_import(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import extract_imports

        m = tmp_path / "test.m"
        m.write_text(
            "@import CoreData;\n"
            "@import Foundation;\n"
            "@import MyCustomLib;\n"
            "\n@interface Foo : NSObject\n@end\n"
        )
        imports = extract_imports(m)
        paths = [i.import_path for i in imports]
        assert "CoreData" not in paths
        assert "Foundation" not in paths
        assert "MyCustomLib" in paths

    def test_import_line_numbers(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import extract_imports

        m = tmp_path / "test.m"
        m.write_text('#import "First.h"\n#import "Second.h"\n\n@interface Foo : NSObject\n@end\n')
        imports = extract_imports(m)
        assert len(imports) == 2
        assert imports[0].line_number == 1
        assert imports[1].line_number == 2

    def test_no_imports(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import extract_imports

        m = tmp_path / "test.m"
        m.write_text("@interface Foo : NSObject\n@end\n")
        imports = extract_imports(m)
        assert imports == []

    def test_mixed_imports(self, tmp_path: Path) -> None:
        """Test a mix of system angle-bracket, quoted, and module imports."""
        from beadloom.graph.import_resolver import extract_imports

        m = tmp_path / "test.m"
        m.write_text(
            "#import <Foundation/Foundation.h>\n"
            '#import "MyHeader.h"\n'
            '#import "OtherHeader.h"\n'
            "@import CoreData;\n"
            "@import CustomFramework;\n"
            "\n@interface Foo : NSObject\n@end\n"
        )
        imports = extract_imports(m)
        paths = [i.import_path for i in imports]
        assert "MyHeader.h" in paths
        assert "OtherHeader.h" in paths
        assert "CustomFramework" in paths
        # System imports should be filtered
        assert "Foundation/Foundation.h" not in paths
        assert "CoreData" not in paths

    def test_mm_imports(self, tmp_path: Path) -> None:
        """Objective-C++ (.mm) files should also have imports extracted."""
        from beadloom.graph.import_resolver import extract_imports

        mm = tmp_path / "test.mm"
        mm.write_text('#import "MyHeader.h"\n\n@interface Foo : NSObject\n@end\n')
        imports = extract_imports(mm)
        paths = [i.import_path for i in imports]
        assert "MyHeader.h" in paths

    def test_system_framework_filtering(self, tmp_path: Path) -> None:
        """Comprehensive test for system framework filtering."""
        from beadloom.graph.import_resolver import extract_imports

        frameworks = [
            "Foundation",
            "UIKit",
            "AppKit",
            "CoreData",
            "CoreGraphics",
            "CoreFoundation",
            "CoreLocation",
            "WebKit",
            "AVFoundation",
            "Metal",
            "MetalKit",
            "Security",
            "StoreKit",
        ]
        import_lines = [f"#import <{fw}/{fw}.h>\n" for fw in frameworks]
        m = tmp_path / "test.m"
        suffix = '#import "MyCustom.h"\n\n@interface Foo : NSObject\n@end\n'
        content = "".join(import_lines) + suffix
        m.write_text(content)
        imports = extract_imports(m)
        paths = [i.import_path for i in imports]
        # All system frameworks should be filtered
        for fw in frameworks:
            assert f"{fw}/{fw}.h" not in paths
        # Custom import should remain
        assert "MyCustom.h" in paths


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------


class TestObjcRegistration:
    def test_m_in_code_extensions(self) -> None:
        from beadloom.infrastructure.reindex import _CODE_EXTENSIONS

        assert ".m" in _CODE_EXTENSIONS

    def test_mm_in_code_extensions(self) -> None:
        from beadloom.infrastructure.reindex import _CODE_EXTENSIONS

        assert ".mm" in _CODE_EXTENSIONS

    def test_m_in_extension_loaders(self) -> None:
        from beadloom.context_oracle.code_indexer import _EXTENSION_LOADERS

        assert ".m" in _EXTENSION_LOADERS

    def test_mm_in_extension_loaders(self) -> None:
        from beadloom.context_oracle.code_indexer import _EXTENSION_LOADERS

        assert ".mm" in _EXTENSION_LOADERS

    def test_lang_config_available(self) -> None:
        if not _objc_available():
            pytest.skip("tree-sitter-objc not installed")
        config = get_lang_config(".m")
        assert config is not None
        assert config.symbol_types  # non-empty

    def test_lang_config_comment_types(self) -> None:
        if not _objc_available():
            pytest.skip("tree-sitter-objc not installed")
        config = get_lang_config(".m")
        assert config is not None
        assert "comment" in config.comment_types

    def test_lang_config_symbol_types(self) -> None:
        if not _objc_available():
            pytest.skip("tree-sitter-objc not installed")
        config = get_lang_config(".m")
        assert config is not None
        assert "class_interface" in config.symbol_types
        assert "class_implementation" in config.symbol_types
        assert "protocol_declaration" in config.symbol_types
        assert "function_definition" in config.symbol_types

    def test_mm_shares_config_with_m(self) -> None:
        if not _objc_available():
            pytest.skip("tree-sitter-objc not installed")
        m_config = get_lang_config(".m")
        mm_config = get_lang_config(".mm")
        assert m_config is not None
        assert mm_config is not None
        # They should use the same language and symbol types
        assert m_config.symbol_types == mm_config.symbol_types

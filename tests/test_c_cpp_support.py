"""Tests for C and C++ language support (BEAD-16)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.context_oracle.code_indexer import clear_cache, extract_symbols, get_lang_config

if TYPE_CHECKING:
    from pathlib import Path


def _c_available() -> bool:
    try:
        import tree_sitter_c  # noqa: F401

        return True
    except ImportError:
        return False


def _cpp_available() -> bool:
    try:
        import tree_sitter_cpp  # noqa: F401

        return True
    except ImportError:
        return False


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    clear_cache()


# ---------------------------------------------------------------------------
# C symbol extraction tests
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _c_available(), reason="tree-sitter-c not installed")
class TestCSymbols:
    def test_extract_function(self, tmp_path: Path) -> None:
        src = tmp_path / "main.c"
        src.write_text('void greet(const char* name) {\n    printf("Hello");\n}\n')
        symbols = extract_symbols(src)
        assert len(symbols) >= 1
        func = next(s for s in symbols if s["symbol_name"] == "greet")
        assert func["kind"] == "function"

    def test_extract_struct(self, tmp_path: Path) -> None:
        src = tmp_path / "point.c"
        src.write_text("struct Point {\n    int x;\n    int y;\n};\n")
        symbols = extract_symbols(src)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "Point"
        assert symbols[0]["kind"] == "class"

    def test_extract_enum(self, tmp_path: Path) -> None:
        src = tmp_path / "colors.c"
        src.write_text("enum Color { RED, GREEN, BLUE };\n")
        symbols = extract_symbols(src)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "Color"
        assert symbols[0]["kind"] == "class"

    def test_extract_typedef(self, tmp_path: Path) -> None:
        src = tmp_path / "types.c"
        src.write_text("typedef int MyInt;\n")
        symbols = extract_symbols(src)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "MyInt"
        assert symbols[0]["kind"] == "type"

    def test_multiple_symbols(self, tmp_path: Path) -> None:
        src = tmp_path / "multi.c"
        src.write_text(
            "struct Point { int x; int y; };\n\n"
            "enum Color { RED, GREEN };\n\n"
            "void greet() {}\n\n"
            "int main() { return 0; }\n"
        )
        symbols = extract_symbols(src)
        names = {s["symbol_name"] for s in symbols}
        assert names == {"Point", "Color", "greet", "main"}

    def test_annotation_propagation(self, tmp_path: Path) -> None:
        src = tmp_path / "annotated.c"
        src.write_text("// beadloom:domain=core\nvoid process() {}\n")
        symbols = extract_symbols(src)
        assert symbols[0]["annotations"].get("domain") == "core"

    def test_module_annotation_applies_to_all(self, tmp_path: Path) -> None:
        src = tmp_path / "module.c"
        src.write_text("// beadloom:domain=io\n\nvoid read_file() {}\n\nvoid write_file() {}\n")
        symbols = extract_symbols(src)
        reader = next(s for s in symbols if s["symbol_name"] == "read_file")
        writer = next(s for s in symbols if s["symbol_name"] == "write_file")
        assert reader["annotations"] == {"domain": "io"}
        assert writer["annotations"] == {"domain": "io"}

    def test_empty_file(self, tmp_path: Path) -> None:
        src = tmp_path / "empty.c"
        src.write_text("")
        symbols = extract_symbols(src)
        assert symbols == []

    def test_header_file(self, tmp_path: Path) -> None:
        """C headers (.h) should be parsed with C grammar."""
        src = tmp_path / "header.h"
        src.write_text("struct Config {\n    int value;\n};\n\nvoid init();\n")
        symbols = extract_symbols(src)
        names = {s["symbol_name"] for s in symbols}
        assert "Config" in names


# ---------------------------------------------------------------------------
# C++ symbol extraction tests
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _cpp_available(), reason="tree-sitter-cpp not installed")
class TestCppSymbols:
    def test_extract_function(self, tmp_path: Path) -> None:
        src = tmp_path / "main.cpp"
        src.write_text("void greet() {}\n")
        symbols = extract_symbols(src)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "greet"
        assert symbols[0]["kind"] == "function"

    def test_extract_class(self, tmp_path: Path) -> None:
        src = tmp_path / "user.cpp"
        src.write_text("class User {\npublic:\n    void method();\n};\n")
        symbols = extract_symbols(src)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "User"
        assert symbols[0]["kind"] == "class"

    def test_extract_struct(self, tmp_path: Path) -> None:
        src = tmp_path / "point.cpp"
        src.write_text("struct Point {\n    int x;\n    int y;\n};\n")
        symbols = extract_symbols(src)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "Point"
        assert symbols[0]["kind"] == "class"

    def test_extract_enum(self, tmp_path: Path) -> None:
        src = tmp_path / "colors.cpp"
        src.write_text("enum Color { RED, GREEN, BLUE };\n")
        symbols = extract_symbols(src)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "Color"
        assert symbols[0]["kind"] == "class"

    def test_extract_namespace(self, tmp_path: Path) -> None:
        src = tmp_path / "ns.cpp"
        src.write_text("namespace MyNamespace {\n    class Foo {};\n}\n")
        symbols = extract_symbols(src)
        assert len(symbols) >= 1
        ns = next(s for s in symbols if s["symbol_name"] == "MyNamespace")
        assert ns["kind"] == "class"

    def test_extract_typedef(self, tmp_path: Path) -> None:
        src = tmp_path / "types.cpp"
        src.write_text("typedef int MyInt;\n")
        symbols = extract_symbols(src)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "MyInt"
        assert symbols[0]["kind"] == "type"

    def test_multiple_symbols(self, tmp_path: Path) -> None:
        src = tmp_path / "multi.cpp"
        src.write_text(
            "class Foo {};\n\nstruct Bar { int x; };\n\nvoid baz() {}\n\nenum Qux { A, B };\n"
        )
        symbols = extract_symbols(src)
        names = {s["symbol_name"] for s in symbols}
        assert names == {"Foo", "Bar", "baz", "Qux"}

    def test_annotation_propagation(self, tmp_path: Path) -> None:
        src = tmp_path / "annotated.cpp"
        src.write_text("// beadloom:domain=engine\nclass Engine {};\n")
        symbols = extract_symbols(src)
        assert symbols[0]["annotations"].get("domain") == "engine"

    def test_hpp_header_file(self, tmp_path: Path) -> None:
        """C++ headers (.hpp) should be parsed with C++ grammar."""
        src = tmp_path / "header.hpp"
        src.write_text("class Config {\npublic:\n    int value;\n};\n")
        symbols = extract_symbols(src)
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "Config"
        assert symbols[0]["kind"] == "class"

    def test_empty_file(self, tmp_path: Path) -> None:
        src = tmp_path / "empty.cpp"
        src.write_text("")
        symbols = extract_symbols(src)
        assert symbols == []


# ---------------------------------------------------------------------------
# C/C++ import extraction tests
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _c_available(), reason="tree-sitter-c not installed")
class TestCImports:
    def test_extract_local_include(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import extract_imports

        src = tmp_path / "main.c"
        src.write_text('#include "myheader.h"\n\nvoid main() {}\n')
        imports = extract_imports(src)
        paths = [i.import_path for i in imports]
        assert "myheader.h" in paths

    def test_skip_system_headers(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import extract_imports

        src = tmp_path / "main.c"
        src.write_text(
            "#include <stdio.h>\n"
            "#include <stdlib.h>\n"
            "#include <string.h>\n"
            '#include "mylib.h"\n\n'
            "void main() {}\n"
        )
        imports = extract_imports(src)
        paths = [i.import_path for i in imports]
        assert "stdio.h" not in paths
        assert "stdlib.h" not in paths
        assert "string.h" not in paths
        assert "mylib.h" in paths

    def test_system_angle_bracket_includes(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import extract_imports

        src = tmp_path / "test.c"
        src.write_text("#include <math.h>\n#include <assert.h>\n\nint main() { return 0; }\n")
        imports = extract_imports(src)
        paths = [i.import_path for i in imports]
        assert "math.h" not in paths
        assert "assert.h" not in paths

    def test_import_line_numbers(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import extract_imports

        src = tmp_path / "main.c"
        src.write_text('#include "first.h"\n#include "second.h"\n\nvoid main() {}\n')
        imports = extract_imports(src)
        assert len(imports) == 2
        assert imports[0].line_number == 1
        assert imports[1].line_number == 2

    def test_no_includes(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import extract_imports

        src = tmp_path / "main.c"
        src.write_text("void main() {}\n")
        imports = extract_imports(src)
        assert imports == []

    def test_h_file_imports(self, tmp_path: Path) -> None:
        """Header files (.h) should also have imports extracted."""
        from beadloom.graph.import_resolver import extract_imports

        src = tmp_path / "header.h"
        src.write_text('#include "types.h"\n\nstruct Foo { int x; };\n')
        imports = extract_imports(src)
        paths = [i.import_path for i in imports]
        assert "types.h" in paths


@pytest.mark.skipif(not _cpp_available(), reason="tree-sitter-cpp not installed")
class TestCppImports:
    def test_extract_local_include(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import extract_imports

        src = tmp_path / "main.cpp"
        src.write_text('#include "myclass.h"\n\nclass Foo {};\n')
        imports = extract_imports(src)
        paths = [i.import_path for i in imports]
        assert "myclass.h" in paths

    def test_skip_cpp_system_headers(self, tmp_path: Path) -> None:
        from beadloom.graph.import_resolver import extract_imports

        src = tmp_path / "main.cpp"
        src.write_text(
            "#include <iostream>\n"
            "#include <vector>\n"
            "#include <string>\n"
            "#include <memory>\n"
            '#include "mylib.h"\n\n'
            "class Foo {};\n"
        )
        imports = extract_imports(src)
        paths = [i.import_path for i in imports]
        assert "iostream" not in paths
        assert "vector" not in paths
        assert "string" not in paths
        assert "memory" not in paths
        assert "mylib.h" in paths

    def test_skip_c_compat_headers(self, tmp_path: Path) -> None:
        """C++ C-compatibility headers like cstdlib should be filtered."""
        from beadloom.graph.import_resolver import extract_imports

        src = tmp_path / "main.cpp"
        src.write_text(
            '#include <cstdlib>\n#include <cstring>\n#include "myutil.h"\n\nvoid func() {}\n'
        )
        imports = extract_imports(src)
        paths = [i.import_path for i in imports]
        assert "cstdlib" not in paths
        assert "cstring" not in paths
        assert "myutil.h" in paths

    def test_hpp_imports(self, tmp_path: Path) -> None:
        """C++ headers (.hpp) should have imports extracted."""
        from beadloom.graph.import_resolver import extract_imports

        src = tmp_path / "header.hpp"
        src.write_text('#include "base.hpp"\n\nclass Derived {};\n')
        imports = extract_imports(src)
        paths = [i.import_path for i in imports]
        assert "base.hpp" in paths


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------


class TestCCppRegistration:
    def test_c_in_code_extensions(self) -> None:
        from beadloom.infrastructure.reindex import _CODE_EXTENSIONS

        assert ".c" in _CODE_EXTENSIONS
        assert ".h" in _CODE_EXTENSIONS

    def test_cpp_in_code_extensions(self) -> None:
        from beadloom.infrastructure.reindex import _CODE_EXTENSIONS

        assert ".cpp" in _CODE_EXTENSIONS
        assert ".hpp" in _CODE_EXTENSIONS

    def test_c_in_extension_loaders(self) -> None:
        from beadloom.context_oracle.code_indexer import _EXTENSION_LOADERS

        assert ".c" in _EXTENSION_LOADERS
        assert ".h" in _EXTENSION_LOADERS

    def test_cpp_in_extension_loaders(self) -> None:
        from beadloom.context_oracle.code_indexer import _EXTENSION_LOADERS

        assert ".cpp" in _EXTENSION_LOADERS
        assert ".hpp" in _EXTENSION_LOADERS

    def test_c_lang_config_available(self) -> None:
        if not _c_available():
            pytest.skip("tree-sitter-c not installed")
        config = get_lang_config(".c")
        assert config is not None
        assert config.symbol_types

    def test_cpp_lang_config_available(self) -> None:
        if not _cpp_available():
            pytest.skip("tree-sitter-cpp not installed")
        config = get_lang_config(".cpp")
        assert config is not None
        assert config.symbol_types

    def test_c_comment_types(self) -> None:
        if not _c_available():
            pytest.skip("tree-sitter-c not installed")
        config = get_lang_config(".c")
        assert config is not None
        assert "comment" in config.comment_types

    def test_cpp_comment_types(self) -> None:
        if not _cpp_available():
            pytest.skip("tree-sitter-cpp not installed")
        config = get_lang_config(".cpp")
        assert config is not None
        assert "comment" in config.comment_types

    def test_h_uses_c_grammar(self) -> None:
        """Verify .h files use the C grammar loader."""
        from beadloom.context_oracle.code_indexer import _EXTENSION_LOADERS

        assert _EXTENSION_LOADERS[".h"] is _EXTENSION_LOADERS[".c"]

    def test_hpp_uses_cpp_grammar(self) -> None:
        """Verify .hpp files use the C++ grammar loader."""
        from beadloom.context_oracle.code_indexer import _EXTENSION_LOADERS

        assert _EXTENSION_LOADERS[".hpp"] is _EXTENSION_LOADERS[".cpp"]

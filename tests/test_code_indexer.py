"""Tests for beadloom.code_indexer — tree-sitter symbol extraction + annotations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.code_indexer import extract_symbols, parse_annotations

if TYPE_CHECKING:
    from pathlib import Path


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
        py.write_text(
            "class Foo:\n    pass\n\n"
            "def bar():\n    pass\n\n"
            "def baz():\n    pass\n"
        )
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
        py.write_text(
            "# beadloom:feature=PROJ-1 domain=routing\n"
            "def list_tracks():\n"
            "    pass\n"
        )
        symbols = extract_symbols(py)
        assert len(symbols) == 1
        assert symbols[0]["annotations"] == {"feature": "PROJ-1", "domain": "routing"}

    def test_annotation_only_applies_to_next_symbol(self, tmp_path: Path) -> None:
        py = tmp_path / "two.py"
        py.write_text(
            "# beadloom:feature=F1\n"
            "def first():\n    pass\n\n"
            "def second():\n    pass\n"
        )
        symbols = extract_symbols(py)
        first = next(s for s in symbols if s["symbol_name"] == "first")
        second = next(s for s in symbols if s["symbol_name"] == "second")
        assert first["annotations"] == {"feature": "F1"}
        assert second["annotations"] == {}

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

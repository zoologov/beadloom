"""Exported bindings of a JS/TS module are symbols (BDL-076 J3, ``beadloom-tmxa``).

A0 (``beadloom-kcwz``) measured that of this repository's theme only the exported
FUNCTIONS were read: every ``export const`` — the token tables ``LAYER_COLORS``,
``ELK_OPTIONS``, ``EDGE_LEGEND`` the viewer work changes most — and every
``export default {...}`` gave no symbol. A binding's kind is the kind of the
value it holds: a function or a class where the value is one, else ``variable``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.context_oracle.code_indexer import clear_cache, extract_symbols

if TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("tree_sitter_typescript")


@pytest.fixture(autouse=True)
def _clear_lang_cache() -> None:
    clear_cache()


def _symbols(tmp_path: Path, text: str, name: str = "mod.js") -> list[tuple[str, str, int, int]]:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return [
        (str(s["symbol_name"]), str(s["kind"]), int(s["line_start"]), int(s["line_end"]))
        for s in extract_symbols(path)
    ]


class TestExportedBindings:
    def test_export_const_let_and_var_are_variables(self, tmp_path: Path) -> None:
        text = "export const A = 1\nexport let b = 'x'\nexport var c = {}\n"
        assert _symbols(tmp_path, text) == [
            ("A", "variable", 1, 1),
            ("b", "variable", 2, 2),
            ("c", "variable", 3, 3),
        ]

    def test_a_binding_holding_a_function_is_a_function(self, tmp_path: Path) -> None:
        text = "export const f = (x) => x\nexport const g = function () {}\n"
        assert _symbols(tmp_path, text) == [("f", "function", 1, 1), ("g", "function", 2, 2)]

    def test_a_binding_holding_a_class_is_a_class(self, tmp_path: Path) -> None:
        assert _symbols(tmp_path, "export const K = class {}\n") == [("K", "class", 1, 1)]

    def test_every_declarator_of_one_statement_is_a_symbol(self, tmp_path: Path) -> None:
        text = "export const a = 1,\n  b = () => 2\n"
        assert _symbols(tmp_path, text) == [("a", "variable", 1, 1), ("b", "function", 2, 2)]

    def test_a_multiline_table_spans_its_lines(self, tmp_path: Path) -> None:
        text = "export const COLORS = {\n  a: 'red',\n  b: 'blue',\n}\n"
        assert _symbols(tmp_path, text) == [("COLORS", "variable", 1, 4)]

    def test_a_typed_binding_in_typescript_is_read(self, tmp_path: Path) -> None:
        assert _symbols(tmp_path, "export const t: number = 3\n", "mod.ts") == [
            ("t", "variable", 1, 1)
        ]

    def test_a_destructuring_export_names_no_single_symbol(self, tmp_path: Path) -> None:
        assert _symbols(tmp_path, "export const { a, b } = obj\n") == []

    def test_an_unexported_binding_is_not_a_symbol(self, tmp_path: Path) -> None:
        assert _symbols(tmp_path, "const hidden = 1\nlet other = () => 2\n") == []

    def test_an_annotation_above_an_export_const_attaches_to_it(self, tmp_path: Path) -> None:
        path = tmp_path / "mod.js"
        path.write_text("// beadloom:component=theme\nexport const A = 1\n", encoding="utf-8")
        (symbol,) = extract_symbols(path)
        assert symbol["annotations"] == {"component": "theme"}


class TestDefaultExport:
    @pytest.mark.parametrize(
        ("text", "kind"),
        [
            ("export default { name: 'x' }\n", "variable"),
            ("export default useCounter\n", "variable"),
            ("export default function () {}\n", "function"),
            ("export default async () => 1\n", "function"),
            ("export default class {}\n", "class"),
        ],
    )
    def test_an_anonymous_default_export_is_named_default(
        self, tmp_path: Path, text: str, kind: str
    ) -> None:
        assert _symbols(tmp_path, text) == [("default", kind, 1, 1)]

    def test_a_named_default_declaration_keeps_its_name(self, tmp_path: Path) -> None:
        assert _symbols(tmp_path, "export default function named() {}\n") == [
            ("named", "function", 1, 1)
        ]

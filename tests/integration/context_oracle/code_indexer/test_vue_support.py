"""Vue single-file components: script blocks found, parsed and placed (BDL-076 J3).

``beadloom-tmxa``. A0 (``beadloom-kcwz``) measured that a ``.vue`` file was only
hashed: 0 symbols from all ten components of this repository's theme, because no
parser was registered for the extension. These tests pin the repair: the
``<script>`` and ``<script setup>`` blocks are found with their place in the file,
parsed by the existing JS/TS grammar, and every symbol keeps its ``.vue`` line.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import pytest

from beadloom.context_oracle import code_indexer
from beadloom.context_oracle.code_indexer import (
    check_parser_availability,
    clear_cache,
    extract_symbols,
    supported_extensions,
)
from beadloom.context_oracle.vue_sfc import ScriptBlock, script_blocks

if TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("tree_sitter_typescript")


@pytest.fixture(autouse=True)
def _clear_lang_cache() -> None:
    clear_cache()


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def _by_name(symbols: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    return {str(s["symbol_name"]): s for s in symbols}


# --- finding the blocks ---


class TestScriptBlocks:
    def test_a_component_without_a_script_has_no_block(self) -> None:
        assert script_blocks("<template><p>scripts</p></template>\n") == ()

    def test_a_setup_block_in_typescript_is_read_as_typescript(self) -> None:
        source = (
            '<template>\n  <p/>\n</template>\n\n<script setup lang="ts">\nconst a = 1\n</script>\n'
        )
        assert script_blocks(source) == (
            ScriptBlock(text="\nconst a = 1\n", line_offset=4, extension=".ts"),
        )

    def test_a_block_without_lang_is_javascript(self) -> None:
        (block,) = script_blocks("<script>\nexport default {}\n</script>\n")
        assert block.extension == ".js"
        assert block.line_offset == 0

    @pytest.mark.parametrize(
        ("attributes", "extension"),
        [
            ("lang='ts'", ".ts"),
            ("lang=ts", ".ts"),
            ('setup lang="tsx"', ".tsx"),
            ('lang="jsx"', ".jsx"),
            ('lang="js"', ".js"),
            ('lang="coffee"', ".js"),
        ],
    )
    def test_the_lang_attribute_chooses_the_grammar(self, attributes: str, extension: str) -> None:
        (block,) = script_blocks(f"<script {attributes}>\nconst a = 1\n</script>\n")
        assert block.extension == extension

    def test_both_blocks_are_found_in_file_order(self) -> None:
        source = (
            '<script lang="ts">\nexport const A = 1\n</script>\n\n'
            "<script setup>\nfunction f() {}\n</script>\n"
        )
        first, second = script_blocks(source)
        assert (first.extension, first.line_offset) == (".ts", 0)
        assert (second.extension, second.line_offset) == (".js", 4)

    def test_a_block_whose_code_starts_on_the_tag_line_keeps_that_line(self) -> None:
        (block,) = script_blocks("<template/>\n<script>export const A = 1</script>\n")
        assert block.line_offset == 1
        assert block.file_line(0) == 2

    def test_a_tag_that_only_starts_with_script_is_not_a_script_block(self) -> None:
        assert script_blocks("<script-docs>\nconst a = 1\n</script-docs>\n") == ()


# --- symbols of a component ---

COUNTER = """\
<template>
  <button @click="reset">{{ count }}</button>
</template>

<script setup lang="ts">
// beadloom:component=components
import { ref } from 'vue'

const count = ref(0)

function reset(): void {
  count.value = 0
}
</script>

<style scoped>
button { color: red; }
</style>
"""

BOTH = """\
<script lang="ts">
// beadloom:component=components
export const PAGE_SIZE = 20
export default { inheritAttrs: false }
</script>

<script setup lang="ts">
function pages(total: number): number {
  return Math.ceil(total / PAGE_SIZE)
}
</script>
"""


class TestComponentSymbols:
    def test_the_script_setup_symbols_keep_their_line_in_the_file(self, tmp_path: Path) -> None:
        symbols = _by_name(extract_symbols(_write(tmp_path, "Counter.vue", COUNTER)))
        assert (symbols["reset"]["kind"], symbols["reset"]["line_start"]) == ("function", 11)
        assert symbols["reset"]["line_end"] == 13

    def test_the_component_is_a_symbol_named_after_its_file(self, tmp_path: Path) -> None:
        symbols = _by_name(extract_symbols(_write(tmp_path, "Counter.vue", COUNTER)))
        assert symbols["Counter"]["kind"] == "component"
        assert (symbols["Counter"]["line_start"], symbols["Counter"]["line_end"]) == (1, 18)

    def test_an_annotation_in_the_script_binds_the_component_and_its_symbols(
        self, tmp_path: Path
    ) -> None:
        symbols = _by_name(extract_symbols(_write(tmp_path, "Counter.vue", COUNTER)))
        for name in ("Counter", "reset"):
            assert symbols[name]["annotations"] == {"component": "components"}

    def test_the_file_hash_is_the_hash_of_the_whole_component(self, tmp_path: Path) -> None:
        symbols = extract_symbols(_write(tmp_path, "Counter.vue", COUNTER))
        expected = hashlib.sha256(COUNTER.encode()).hexdigest()
        assert {s["file_hash"] for s in symbols} == {expected}

    def test_the_first_blocks_annotation_covers_the_second_block(self, tmp_path: Path) -> None:
        symbols = _by_name(extract_symbols(_write(tmp_path, "Both.vue", BOTH)))
        assert symbols["PAGE_SIZE"]["line_start"] == 3
        assert symbols["pages"]["line_start"] == 8
        assert symbols["pages"]["annotations"] == {"component": "components"}

    def test_the_default_export_of_a_component_is_the_component_itself(
        self, tmp_path: Path
    ) -> None:
        symbols = _by_name(extract_symbols(_write(tmp_path, "Both.vue", BOTH)))
        assert "default" not in symbols
        assert set(symbols) == {"Both", "PAGE_SIZE", "pages"}

    def test_a_component_without_a_script_is_still_a_component(self, tmp_path: Path) -> None:
        symbols = extract_symbols(
            _write(tmp_path, "Badge.vue", "<template>\n  <b/>\n</template>\n")
        )
        assert [(s["symbol_name"], s["kind"], s["annotations"]) for s in symbols] == [
            ("Badge", "component", {})
        ]

    def test_an_empty_component_has_no_symbol(self, tmp_path: Path) -> None:
        assert extract_symbols(_write(tmp_path, "Empty.vue", "\n")) == []


class TestVueIsParseable:
    def test_vue_is_a_supported_extension(self) -> None:
        assert ".vue" in supported_extensions()

    def test_vue_has_a_parser_when_the_script_grammar_is_installed(self) -> None:
        assert check_parser_availability([".vue"]) == {".vue": True}

    def test_without_the_script_grammar_vue_is_neither_supported_nor_read(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _missing() -> code_indexer.LangConfig:
            raise ImportError

        monkeypatch.setitem(code_indexer._EXTENSION_LOADERS, ".js", _missing)
        assert ".vue" not in supported_extensions()
        assert check_parser_availability([".vue"]) == {".vue": False}
        assert extract_symbols(_write(tmp_path, "Counter.vue", COUNTER)) == []

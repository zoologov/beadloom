"""Unit tests for relative JS/TS specifiers in ``graph/import_resolver`` (BDL-076 J1).

The resolution ORDER is pure path arithmetic and is tested here without an
index. What a candidate resolves to once it exists on disk is in the integration
mirror of this file, because that needs the nodes table.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.context_oracle.code_indexer import clear_cache
from beadloom.graph.import_resolver import (
    extract_imports,
    is_relative_specifier,
    relative_import_candidates,
)

if TYPE_CHECKING:
    from pathlib import Path

_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue")
_PLATFORMS = (".ios", ".android", ".native", ".web")


@pytest.fixture(autouse=True)
def _clear_lang_cache() -> None:
    clear_cache()


class TestIsRelativeSpecifier:
    @pytest.mark.parametrize("specifier", ["./x", "../y/z", ".", "..", "./", "../"])
    def test_relative(self, specifier: str) -> None:
        assert is_relative_specifier(specifier)

    @pytest.mark.parametrize("specifier", ["vue", "@/shared/x", "~/x", ".hidden", "..x", "/abs"])
    def test_not_relative(self, specifier: str) -> None:
        assert not is_relative_specifier(specifier)


class TestRelativeImportCandidates:
    def test_extensionless_tries_each_extension_then_each_index(self) -> None:
        # Each extension is tried with React Native's platform suffixes first
        # (BDL-080 `beadloom-cwzc`): `dates.ios.ts` before `dates.ts`.
        candidates = relative_import_candidates("../shared/dates", "src/app/main.ts")
        assert candidates == [
            "src/shared/dates",
            *(
                f"src/shared/dates{platform}{ext}"
                for ext in _EXTENSIONS
                for platform in (*_PLATFORMS, "")
            ),
            *(
                f"src/shared/dates/index{platform}{ext}"
                for ext in _EXTENSIONS
                for platform in (*_PLATFORMS, "")
            ),
        ]

    def test_written_js_extension_tries_the_file_then_its_typescript_source(self) -> None:
        candidates = relative_import_candidates("./carrier.js", "src/tracking/track.ts")
        assert candidates[:3] == [
            "src/tracking/carrier.js",
            "src/tracking/carrier.ts",
            "src/tracking/carrier.tsx",
        ]

    def test_written_jsx_extension_tries_the_tsx_source(self) -> None:
        candidates = relative_import_candidates("./Card.jsx", "src/ui/index.js")
        assert candidates[:2] == ["src/ui/Card.jsx", "src/ui/Card.tsx"]

    def test_written_vue_extension_is_tried_as_written_first(self) -> None:
        candidates = relative_import_candidates("./components/X.vue", "theme/index.js")
        assert candidates[0] == "theme/components/X.vue"

    def test_dot_names_the_importers_own_folder(self) -> None:
        candidates = relative_import_candidates(".", "src/ui/card/view.js")
        assert candidates[0] == "src/ui/card"
        assert "src/ui/card/index.js" in candidates

    def test_importer_at_the_project_root(self) -> None:
        candidates = relative_import_candidates("./util", "main.ts")
        assert candidates[:2] == ["util", "util.ios.ts"]
        assert "util.ts" in candidates
        assert "util/index.ts" in candidates

    def test_a_specifier_that_leaves_the_project_names_nothing(self) -> None:
        assert relative_import_candidates("../../outside", "src/main.ts") == []


def _ts_available() -> bool:
    try:
        import tree_sitter_typescript  # noqa: F401
    except ImportError:
        return False
    return True


@pytest.mark.skipif(not _ts_available(), reason="tree-sitter-typescript not installed")
class TestExtractKeepsRelativeSpecifiers:
    def test_relative_import_is_kept(self, tmp_path: Path) -> None:
        ts = tmp_path / "app.ts"
        ts.write_text("import './relative';\nimport { A } from '../parent';\n")
        assert [imp.import_path for imp in extract_imports(ts)] == ["./relative", "../parent"]

    def test_re_export_names_its_source(self, tmp_path: Path) -> None:
        js = tmp_path / "index.js"
        js.write_text(
            "export { Card } from './card';\n"
            "export * from '../shared';\n"
            "export const LOCAL = 'not-a-source';\n"
            "export function f() { return 1; }\n"
        )
        assert [imp.import_path for imp in extract_imports(js)] == ["./card", "../shared"]


@pytest.mark.skipif(not _ts_available(), reason="tree-sitter-typescript not installed")
class TestExtractDynamicImports:
    """BDL-076 J2: `import('...')` is a call expression, not an import statement."""

    def test_a_literal_specifier_is_read_at_its_line(self, tmp_path: Path) -> None:
        js = tmp_path / "lazy.js"
        js.write_text("const a = 1;\nconst m = await import('./chart.js');\n")
        imports = extract_imports(js)
        assert [(imp.import_path, imp.line_number) for imp in imports] == [("./chart.js", 2)]

    def test_a_template_literal_without_substitution_is_a_literal(self, tmp_path: Path) -> None:
        js = tmp_path / "lazy.js"
        js.write_text("import(`./chart.js`);\n")
        assert [imp.import_path for imp in extract_imports(js)] == ["./chart.js"]

    @pytest.mark.parametrize(
        "source",
        ["import(name);\n", "import(`./t${a}`);\n", "foo.import('y');\n", "import('./' + a);\n"],
    )
    def test_a_computed_specifier_names_nothing(self, tmp_path: Path, source: str) -> None:
        js = tmp_path / "lazy.js"
        js.write_text(source)
        assert extract_imports(js) == []


@pytest.mark.skipif(not _ts_available(), reason="tree-sitter-typescript not installed")
class TestExtractVueImports:
    """BDL-076 J2: a component's imports come from its script blocks, at file lines."""

    def test_both_blocks_are_read_at_their_lines(self, tmp_path: Path) -> None:
        vue = tmp_path / "Counter.vue"
        vue.write_text(
            '<script lang="ts">\n'
            "import type { Props } from './types';\n"
            "</script>\n"
            "<template><b/></template>\n"
            "<script setup>\n"
            "import { ref } from 'vue';\n"
            "const Chart = () => import('../charts/bar');\n"
            "</script>\n"
            "<style>.b { color: red; }</style>\n"
        )
        imports = extract_imports(vue)
        assert [(imp.import_path, imp.line_number) for imp in imports] == [
            ("./types", 2),
            ("vue", 6),
            ("../charts/bar", 7),
        ]
        assert {imp.file_path for imp in imports} == {str(vue)}

    def test_a_template_only_component_has_no_imports(self, tmp_path: Path) -> None:
        vue = tmp_path / "Badge.vue"
        vue.write_text("<template><b>import x from './y'</b></template>\n")
        assert extract_imports(vue) == []


@pytest.mark.skipif(not _ts_available(), reason="tree-sitter-typescript not installed")
class TestExtractModuleScripts:
    """BDL-080 `beadloom-cwzc`, closing `beadloom-zd4m`: `.mjs`/`.cjs` are parsed as JavaScript."""

    def test_an_mjs_module_s_imports_are_read(self, tmp_path: Path) -> None:
        mjs = tmp_path / "config.mjs"
        mjs.write_text("import { a } from './a.js';\nexport { b } from '@shared/b';\n")
        assert [imp.import_path for imp in extract_imports(mjs)] == ["./a.js", "@shared/b"]

    def test_a_cjs_module_s_dynamic_import_is_read(self, tmp_path: Path) -> None:
        cjs = tmp_path / "loader.cjs"
        cjs.write_text("module.exports = () => import('./lazy.mjs');\n")
        assert [imp.import_path for imp in extract_imports(cjs)] == ["./lazy.mjs"]

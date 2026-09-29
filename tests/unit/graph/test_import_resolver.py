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
        candidates = relative_import_candidates("../shared/dates", "src/app/main.ts")
        assert candidates == [
            "src/shared/dates",
            *(f"src/shared/dates{ext}" for ext in _EXTENSIONS),
            *(f"src/shared/dates/index{ext}" for ext in _EXTENSIONS),
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
        assert candidates[:2] == ["util", "util.ts"]
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

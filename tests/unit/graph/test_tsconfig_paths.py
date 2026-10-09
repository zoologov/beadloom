"""Unit tests for ``graph/tsconfig_paths``: what a project's tsconfig maps a specifier to.

BDL-080 S3a (``beadloom-cwzc``), RFC D5 (a). Each case writes the config files a project
holds and asks which project-relative paths a non-relative specifier is mapped to. Whether
one of them is a file, and which node owns it, is the resolver's question and is asked by
the scenarios of ``an_aliased_or_platform_import_names_its_file.feature``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.graph.tsconfig_paths import TsConfigs, read_jsonc

if TYPE_CHECKING:
    from pathlib import Path


def _write(root: Path, files: dict[str, str]) -> None:
    for rel_path, text in files.items():
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


class TestReadJsonc:
    def test_line_and_block_comments_and_trailing_commas_are_tolerated(self) -> None:
        text = '{\n  // a line\n  "a": [1, 2,], /* a block */\n  "b": {"c": 3,},\n}\n'
        assert read_jsonc(text) == {"a": [1, 2], "b": {"c": 3}}

    def test_comment_markers_inside_a_string_are_text(self) -> None:
        text = '{"url": "http://example.org/*x*/", "glob": "src/**/*"}'
        assert read_jsonc(text) == {"url": "http://example.org/*x*/", "glob": "src/**/*"}

    def test_an_escaped_quote_does_not_end_the_string(self) -> None:
        assert read_jsonc('{"a": "say \\"hi\\" // not a comment"}') == {
            "a": 'say "hi" // not a comment'
        }

    @pytest.mark.parametrize("text", ["", "{", "not json", '{"a": }'])
    def test_text_that_is_no_json_reads_as_nothing(self, text: str) -> None:
        assert read_jsonc(text) is None


class TestPaths:
    def test_a_wildcard_key_maps_the_rest_of_the_specifier(self, tmp_path: Path) -> None:
        _write(tmp_path, {"tsconfig.json": '{"compilerOptions": {"paths": {"@/*": ["./src/*"]}}}'})
        configs = TsConfigs(tmp_path)
        assert configs.mapped("@/shared/api", "src/app/main.ts") == ("src/shared/api",)

    def test_the_longest_prefix_wins_and_an_exact_key_beats_every_pattern(
        self, tmp_path: Path
    ) -> None:
        _write(
            tmp_path,
            {
                "tsconfig.json": (
                    '{"compilerOptions": {"paths": {'
                    '"@/*": ["./src/*"], "@/shared/*": ["./shared/*"], "@/env": ["./env.ts"]'
                    "}}}"
                )
            },
        )
        configs = TsConfigs(tmp_path)
        assert configs.mapped("@/shared/api", "main.ts") == ("shared/api",)
        assert configs.mapped("@/env", "main.ts") == ("env.ts",)
        assert configs.mapped("@/pages/home", "main.ts") == ("src/pages/home",)

    def test_every_target_of_a_key_is_kept_in_order(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            {"tsconfig.json": '{"compilerOptions": {"paths": {"#/*": ["./src/*", "./gen/*"]}}}'},
        )
        assert TsConfigs(tmp_path).mapped("#/a", "main.ts") == ("src/a", "gen/a")

    def test_targets_are_read_from_base_url_when_it_is_set(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            {
                "tsconfig.json": (
                    '{"compilerOptions": {"baseUrl": "./src", "paths": {"@/*": ["*"]}}}'
                )
            },
        )
        assert TsConfigs(tmp_path).mapped("@/a/b", "src/main.ts") == ("src/a/b",)

    def test_targets_are_read_from_the_config_folder_without_base_url(
        self, tmp_path: Path
    ) -> None:
        _write(
            tmp_path, {"web/tsconfig.json": '{"compilerOptions": {"paths": {"@/*": ["./src/*"]}}}'}
        )
        assert TsConfigs(tmp_path).mapped("@/a", "web/src/main.ts") == ("web/src/a",)

    def test_a_specifier_no_key_matches_maps_to_nothing(self, tmp_path: Path) -> None:
        _write(tmp_path, {"tsconfig.json": '{"compilerOptions": {"paths": {"@/*": ["./src/*"]}}}'})
        assert TsConfigs(tmp_path).mapped("vue", "src/main.ts") == ()

    def test_a_target_that_leaves_the_project_is_dropped(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            {
                "tsconfig.json": (
                    '{"compilerOptions": {"paths": {"@/*": ["../outside/*", "./src/*"]}}}'
                )
            },
        )
        assert TsConfigs(tmp_path).mapped("@/a", "src/main.ts") == ("src/a",)


class TestWhichConfigGoverns:
    def test_the_nearest_folder_holding_a_config_governs_an_importer(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            {
                "tsconfig.json": '{"compilerOptions": {"paths": {"@/*": ["./root/*"]}}}',
                "apps/web/tsconfig.json": '{"compilerOptions": {"paths": {"@/*": ["./src/*"]}}}',
            },
        )
        configs = TsConfigs(tmp_path)
        assert configs.mapped("@/a", "apps/web/src/main.ts") == ("apps/web/src/a",)
        assert configs.mapped("@/a", "apps/api/main.ts") == ("root/a",)

    def test_every_config_of_that_folder_is_read_as_create_vue_splits_them(
        self, tmp_path: Path
    ) -> None:
        _write(
            tmp_path,
            {
                "tsconfig.json": '{"files": [], "references": [{"path": "./tsconfig.app.json"}]}',
                "tsconfig.app.json": (
                    '{\n  // app\n  "compilerOptions": {"paths": {"@/*": ["./src/*"],},},\n}'
                ),
                "tsconfig.node.json": '{"include": ["vite.config.*"]}',
            },
        )
        assert TsConfigs(tmp_path).mapped("@/a", "src/main.ts") == ("src/a",)

    def test_a_jsconfig_is_read_as_a_tsconfig_is(self, tmp_path: Path) -> None:
        _write(tmp_path, {"jsconfig.json": '{"compilerOptions": {"paths": {"~/*": ["./lib/*"]}}}'})
        assert TsConfigs(tmp_path).mapped("~/a", "lib/main.js") == ("lib/a",)

    def test_a_relative_extends_is_inherited_from_the_file_it_names(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            {
                "config/tsconfig.base.json": (
                    '{"compilerOptions": {"paths": {"@shared/*": ["../shared/*"]}}}'
                ),
                "tsconfig.json": '{"extends": "./config/tsconfig.base", "compilerOptions": {}}',
            },
        )
        assert TsConfigs(tmp_path).mapped("@shared/a", "src/main.ts") == ("shared/a",)

    def test_a_package_extends_is_not_read_and_the_config_still_is(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            {
                "tsconfig.json": (
                    '{"extends": "expo/tsconfig.base",'
                    ' "compilerOptions": {"paths": {"@/*": ["./*"]}}}'
                )
            },
        )
        assert TsConfigs(tmp_path).mapped("@/components/X", "app/index.tsx") == ("components/X",)

    def test_an_extends_cycle_ends(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            {
                "tsconfig.json": '{"extends": "./tsconfig.b.json"}',
                "tsconfig.b.json": (
                    '{"extends": "./tsconfig.json",'
                    ' "compilerOptions": {"paths": {"@/*": ["./s/*"]}}}'
                ),
            },
        )
        assert TsConfigs(tmp_path).mapped("@/a", "s/main.ts") == ("s/a",)


class TestBaseUrl:
    def test_a_bare_specifier_is_read_under_base_url(self, tmp_path: Path) -> None:
        _write(tmp_path, {"tsconfig.json": '{"compilerOptions": {"baseUrl": "."}}'})
        configs = TsConfigs(tmp_path)
        assert configs.under_base_url("src/shared/config", "src/main.ts") == ("src/shared/config",)

    def test_without_base_url_nothing_is_read_under_it(self, tmp_path: Path) -> None:
        _write(tmp_path, {"tsconfig.json": '{"compilerOptions": {"paths": {"@/*": ["./src/*"]}}}'})
        assert TsConfigs(tmp_path).under_base_url("src/a", "src/main.ts") == ()


class TestManifests:
    def test_every_config_an_answer_rests_on_is_listed_by_path_with_its_text(
        self, tmp_path: Path
    ) -> None:
        base = '{"compilerOptions": {"baseUrl": "."}}'
        app = '{"extends": "./config/base.json"}'
        _write(
            tmp_path,
            {
                "config/base.json": base,
                "tsconfig.json": app,
                "node_modules/pkg/tsconfig.json": "{}",
                ".cache/tsconfig.json": "{}",
            },
        )
        assert TsConfigs(tmp_path).manifests == (
            ("config/base.json", base),
            ("tsconfig.json", app),
        )

    def test_a_project_with_no_config_has_none(self, tmp_path: Path) -> None:
        assert TsConfigs(tmp_path).manifests == ()
        assert TsConfigs(tmp_path).mapped("@/a", "src/main.ts") == ()

"""Unit tests for ``graph/js_specifiers``: the files a JS/TS specifier may name, in order.

BDL-080 S3a (``beadloom-cwzc``), RFC D5 (b) and (c). Pure path arithmetic: the platform
suffixes React Native's bundler tries, and the aliases a project declares under
``imports.aliases:``. Whether a candidate exists is the resolver's question.
"""

from __future__ import annotations

import pytest

from beadloom.graph.js_specifiers import (
    PLATFORM_SUFFIXES,
    aliased_targets,
    module_file_candidates,
)


class TestPlatformSuffixes:
    def test_the_suffixes_are_the_four_react_native_names(self) -> None:
        assert PLATFORM_SUFFIXES == (".ios", ".android", ".native", ".web")

    def test_each_suffix_is_tried_before_the_plain_extension(self) -> None:
        candidates = module_file_candidates("src/ui/Button")
        assert candidates.index("src/ui/Button.ios.tsx") < candidates.index("src/ui/Button.tsx")
        assert candidates.index("src/ui/Button.web.ts") < candidates.index("src/ui/Button.ts")
        position = candidates.index("src/ui/Button.ts")
        assert candidates[position - 4 : position + 1] == [
            "src/ui/Button.ios.ts",
            "src/ui/Button.android.ts",
            "src/ui/Button.native.ts",
            "src/ui/Button.web.ts",
            "src/ui/Button.ts",
        ]

    def test_an_index_is_tried_with_the_suffixes_too(self) -> None:
        candidates = module_file_candidates("src/ui")
        assert candidates.index("src/ui/index.native.ts") < candidates.index("src/ui/index.ts")

    def test_the_path_as_written_is_still_tried_first(self) -> None:
        assert module_file_candidates("src/logo.svg")[0] == "src/logo.svg"


class TestAliasedTargets:
    _ALIASES = (("@shared", "src/shared"), ("@", "src"), ("~", "src"))

    @pytest.mark.parametrize(
        ("specifier", "expected"),
        [
            ("@shared/api", ("src/shared/api",)),
            ("@shared", ("src/shared",)),
            ("@/pages/home", ("src/pages/home",)),
            ("~/a", ("src/a",)),
        ],
    )
    def test_an_alias_maps_itself_and_what_follows_its_slash(
        self, specifier: str, expected: tuple[str, ...]
    ) -> None:
        assert aliased_targets(specifier, self._ALIASES) == expected

    @pytest.mark.parametrize("specifier", ["@sharedx/a", "@vue/runtime", "vue", "~x"])
    def test_a_specifier_that_only_starts_with_an_alias_maps_to_nothing(
        self, specifier: str
    ) -> None:
        assert aliased_targets(specifier, self._ALIASES) == ()

    def test_the_longest_alias_wins_whatever_order_they_are_declared_in(self) -> None:
        aliases = (("@", "src"), ("@/shared", "packages/shared"))
        assert aliased_targets("@/shared/api", aliases) == ("packages/shared/api",)

    def test_an_alias_of_the_project_root_maps_to_the_rest(self) -> None:
        assert aliased_targets("@/components/X", (("@", ""),)) == ("components/X",)

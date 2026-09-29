"""Self-checks of this repository's manifest, CI workflows and configuration (BDL-074 A3).

Moved out of ``tests/test_s2_move_regression.py``;
the product tests of the same code stay there.
The live rows of that module's ``TestCiConfigsModulePath`` -- the same
assertion over this repository's own ``ci.yml`` and ``.gitlab-ci.yml`` -- moved
into the class of that name here in BDL-074 F3, under their ids; the bodies are
in :mod:`tests.support.ci_pipeline_properties`.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.support import ci_pipeline_properties as properties
from tests.support.ci_workflows import GH_CI, GL_CI

if TYPE_CHECKING:
    from pathlib import Path

#: This repository's own two pipelines.
_LIVE_CONFIGS = (GH_CI, GL_CI)


class TestCiConfigsModulePath:
    @pytest.mark.parametrize("cfg", _LIVE_CONFIGS, ids=lambda p: p.name)
    def test_references_new_module_not_tools(self, cfg: Path) -> None:
        properties.references_new_module_not_tools(cfg)

    @pytest.mark.parametrize("cfg", _LIVE_CONFIGS, ids=lambda p: p.name)
    def test_is_valid_yaml(self, cfg: Path) -> None:
        properties.ci_config_is_valid_yaml(cfg)

    @pytest.mark.parametrize(
        "marker",
        [
            "--target pr-branch",
            "merge-base",
            "--since",
            "AI_TW_PAT",
        ],
    )
    def test_root_github_ci_keeps_bdl049_050_markers(self, marker: str) -> None:
        text = GH_CI.read_text(encoding="utf-8")
        assert marker in text

    def test_root_github_ci_keeps_loop_guard_and_verdict(self) -> None:
        text = GH_CI.read_text(encoding="utf-8")
        # loop-guard: the workflow must not re-trigger itself on its own push.
        assert "loop-guard" in text or "loop guard" in text.lower()
        # verdict classification survives (ok/flagged/infra).
        assert "verdict" in text.lower()

    @pytest.mark.parametrize(
        "marker",
        ["--target pr-branch", "merge-base", "--since", "AI_TW_PAT"],
    )
    def test_gitlab_ci_keeps_bdl049_050_markers(self, marker: str) -> None:
        text = GL_CI.read_text(encoding="utf-8")
        assert marker in text


class TestCiConfigNoRetiredToolsPath:
    """REGRESSION pin for the BUG documented on beadloom-mukc.5: after the S2
    move, repo-root ``tools/`` no longer exists, so the CI lint/type steps that
    pass ``tools/`` to ruff + mypy fail hard (ruff E902 / mypy can't-read-file).
    These tests pin that the retired path is dropped from the CI invocations.

    Fixed in S2 (the coordinator dropped ``tools/`` from both CI invocations);
    these are now live assertions that the retired path stays gone.
    """

    def test_github_ci_does_not_lint_retired_tools_path(self) -> None:
        text = GH_CI.read_text(encoding="utf-8")
        assert "ruff check src/ tests/ tools/" not in text
        assert "mypy src/ tools/" not in text

    def test_gitlab_ci_does_not_lint_retired_tools_path(self) -> None:
        text = GL_CI.read_text(encoding="utf-8")
        assert "ruff check src/ tests/ tools/" not in text
        assert "mypy src/ tools/" not in text

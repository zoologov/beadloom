"""Self-checks of this repository's manifest, CI workflows and configuration (BDL-074 A3).

Moved out of ``tests/test_ci_pr_trigger.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import yaml

from tests.support.ci_workflows import (
    GH_CI,
    GH_TEMPLATE,
    GITHUB_FILES,
    GITLAB_FILES,
    PAT_FALLBACK_CHECKOUT,
    PAT_FALLBACK_GH_TOKEN,
)


def test_live_and_template_github_share_trigger_model() -> None:
    """The vendored GitHub template mirrors the live workflow's trigger model."""
    live = yaml.safe_load(GH_CI.read_text(encoding="utf-8"))
    tmpl = yaml.safe_load(GH_TEMPLATE.read_text(encoding="utf-8"))
    live_on = live.get("on", live.get(True))
    tmpl_on = tmpl.get("on", tmpl.get(True))
    assert "pull_request" in live_on and "pull_request" in tmpl_on
    assert "push" not in live_on and "push" not in tmpl_on


def test_live_and_template_gitlab_share_trigger_model() -> None:
    """The vendored GitLab template mirrors the live pipeline's MR trigger model."""
    for path in GITLAB_FILES:
        text = path.read_text(encoding="utf-8")
        assert '$CI_PIPELINE_SOURCE == "merge_request_event"' in text
        assert "--target pr-branch" in text


def test_live_github_pat_wiring_mirrored_in_template() -> None:
    """The vendored GitHub template mirrors the live PAT||token wiring so a
    scaffolded repo auto-gates the agent's commit the same way."""
    for path in GITHUB_FILES:
        text = path.read_text(encoding="utf-8")
        assert PAT_FALLBACK_CHECKOUT in text
        assert PAT_FALLBACK_GH_TOKEN in text

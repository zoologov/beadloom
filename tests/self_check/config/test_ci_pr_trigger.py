"""Self-checks of this repository's manifest, CI workflows and configuration (BDL-074 A3).

Moved out of ``tests/test_ci_pr_trigger.py``;
the product tests of the same code stay there.
The live rows of that module's properties -- the same assertion over this
repository's own ``ci.yml`` and ``.gitlab-ci.yml`` -- moved here in BDL-074 F3
under their ids; the body each runs is in :mod:`tests.support.ci_pipeline_properties`.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import yaml

from tests.support import ci_pipeline_properties as properties
from tests.support.ci_pipeline_properties import held_to
from tests.support.ci_workflows import (
    GH_CI,
    GH_TEMPLATE,
    GITHUB_FILES,
    GITLAB_FILES,
    GL_CI,
    PAT_FALLBACK_CHECKOUT,
    PAT_FALLBACK_GH_TOKEN,
)

#: The rows the properties below run over: this repository's own pipelines.
GITHUB_LIVE = (GH_CI,)
GITLAB_LIVE = (GL_CI,)
ALL_LIVE = GITHUB_LIVE + GITLAB_LIVE

test_ci_config_is_valid_yaml = held_to(properties.ci_config_is_valid_yaml, ALL_LIVE)
test_github_triggers_on_pull_request_not_push_main = held_to(
    properties.github_triggers_on_pull_request_not_push_main, GITHUB_LIVE
)
test_github_has_cancel_in_progress_concurrency = held_to(
    properties.github_has_cancel_in_progress_concurrency, GITHUB_LIVE
)
test_github_uses_merge_base_since_and_pr_branch_target = held_to(
    properties.github_uses_merge_base_since_and_pr_branch_target, GITHUB_LIVE
)
test_github_checks_out_pr_head_branch = held_to(
    properties.github_checks_out_pr_head_branch, GITHUB_LIVE
)
test_gitlab_triggers_on_merge_request_event = held_to(
    properties.gitlab_triggers_on_merge_request_event, GITLAB_LIVE
)
test_gitlab_uses_merge_base_since_and_pr_branch_target = held_to(
    properties.gitlab_uses_merge_base_since_and_pr_branch_target, GITLAB_LIVE
)
test_loop_guard_present = held_to(properties.loop_guard_present, ALL_LIVE)
test_inline_shell_parses_with_bash_n = held_to(
    properties.inline_shell_parses_with_bash_n, ALL_LIVE
)
test_github_loop_guard_sets_skip_flag_before_work = held_to(
    properties.github_loop_guard_sets_skip_flag_before_work, GITHUB_LIVE
)
test_github_every_post_guard_step_is_gated_on_skip = held_to(
    properties.github_every_post_guard_step_is_gated_on_skip, GITHUB_LIVE
)
test_github_pr_path_and_dispatch_path_are_mutually_exclusive = held_to(
    properties.github_pr_path_and_dispatch_path_are_mutually_exclusive, GITHUB_LIVE
)
test_github_dispatch_path_keeps_branch_pr_target = held_to(
    properties.github_dispatch_path_keeps_branch_pr_target, GITHUB_LIVE
)
test_github_grants_contents_and_pull_request_write = held_to(
    properties.github_grants_contents_and_pull_request_write, GITHUB_LIVE
)
test_github_checkout_uses_pat_with_token_fallback = held_to(
    properties.github_checkout_uses_pat_with_token_fallback, GITHUB_LIVE
)
test_github_pr_path_gh_token_uses_pat_with_token_fallback = held_to(
    properties.github_pr_path_gh_token_uses_pat_with_token_fallback, GITHUB_LIVE
)
test_github_dispatch_path_does_not_use_pat = held_to(
    properties.github_dispatch_path_does_not_use_pat, GITHUB_LIVE
)
test_gitlab_pr_path_uses_pat_with_job_token_fallback = held_to(
    properties.gitlab_pr_path_uses_pat_with_job_token_fallback, GITLAB_LIVE
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

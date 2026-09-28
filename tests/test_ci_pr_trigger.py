# beadloom:feature=onboarding
"""BDL-049 BEAD-02: CI configs fire on PR (not push:main), use merge-base
``--since``, carry the loop-guard, and publish via ``--target pr-branch``.

These are static, network-free checks over the four artifacts the feature
touches: the live GitHub workflow + GitLab pipeline, and the two vendored
templates scaffolded into adopter repos. Each must (a) parse as YAML and
(b) encode the trunk-based / merge_request_event trigger model so a scaffolded
repo gets the same trunk-based behaviour as Beadloom itself.

This module holds the product half: every property over the two templates the
package ships. The same properties over this repository's own pipelines are
self-checks, in ``tests/self_check/config/test_ci_pr_trigger.py``, and both run
the one body each property has in :mod:`tests.support.ci_pipeline_properties`
(BDL-074 F3).
"""

from __future__ import annotations

from tests.support import ci_pipeline_properties as properties
from tests.support.ci_pipeline_properties import held_to
from tests.support.ci_workflows import GH_TEMPLATE, GL_TEMPLATE

#: The rows the properties below run over: the templates an adopter receives.
GITHUB_TEMPLATES = (GH_TEMPLATE,)
GITLAB_TEMPLATES = (GL_TEMPLATE,)
ALL_TEMPLATES = GITHUB_TEMPLATES + GITLAB_TEMPLATES

test_ci_config_is_valid_yaml = held_to(properties.ci_config_is_valid_yaml, ALL_TEMPLATES)
test_github_triggers_on_pull_request_not_push_main = held_to(
    properties.github_triggers_on_pull_request_not_push_main, GITHUB_TEMPLATES
)
test_github_has_cancel_in_progress_concurrency = held_to(
    properties.github_has_cancel_in_progress_concurrency, GITHUB_TEMPLATES
)
test_github_uses_merge_base_since_and_pr_branch_target = held_to(
    properties.github_uses_merge_base_since_and_pr_branch_target, GITHUB_TEMPLATES
)
test_github_checks_out_pr_head_branch = held_to(
    properties.github_checks_out_pr_head_branch, GITHUB_TEMPLATES
)
test_gitlab_triggers_on_merge_request_event = held_to(
    properties.gitlab_triggers_on_merge_request_event, GITLAB_TEMPLATES
)
test_gitlab_uses_merge_base_since_and_pr_branch_target = held_to(
    properties.gitlab_uses_merge_base_since_and_pr_branch_target, GITLAB_TEMPLATES
)
test_loop_guard_present = held_to(properties.loop_guard_present, ALL_TEMPLATES)
test_inline_shell_parses_with_bash_n = held_to(
    properties.inline_shell_parses_with_bash_n, ALL_TEMPLATES
)
test_github_loop_guard_sets_skip_flag_before_work = held_to(
    properties.github_loop_guard_sets_skip_flag_before_work, GITHUB_TEMPLATES
)
test_github_every_post_guard_step_is_gated_on_skip = held_to(
    properties.github_every_post_guard_step_is_gated_on_skip, GITHUB_TEMPLATES
)
test_github_pr_path_and_dispatch_path_are_mutually_exclusive = held_to(
    properties.github_pr_path_and_dispatch_path_are_mutually_exclusive, GITHUB_TEMPLATES
)
test_github_dispatch_path_keeps_branch_pr_target = held_to(
    properties.github_dispatch_path_keeps_branch_pr_target, GITHUB_TEMPLATES
)
test_github_grants_contents_and_pull_request_write = held_to(
    properties.github_grants_contents_and_pull_request_write, GITHUB_TEMPLATES
)
test_github_checkout_uses_pat_with_token_fallback = held_to(
    properties.github_checkout_uses_pat_with_token_fallback, GITHUB_TEMPLATES
)
test_github_pr_path_gh_token_uses_pat_with_token_fallback = held_to(
    properties.github_pr_path_gh_token_uses_pat_with_token_fallback, GITHUB_TEMPLATES
)
test_github_dispatch_path_does_not_use_pat = held_to(
    properties.github_dispatch_path_does_not_use_pat, GITHUB_TEMPLATES
)
test_gitlab_pr_path_uses_pat_with_job_token_fallback = held_to(
    properties.gitlab_pr_path_uses_pat_with_job_token_fallback, GITLAB_TEMPLATES
)


def test_template_github_documents_pat_secret_for_adopters() -> None:
    """The vendored GitHub template tells adopters to create the AI_TW_PAT secret
    (and that without it the agent's commit won't auto-trigger the check)."""
    text = GH_TEMPLATE.read_text(encoding="utf-8")
    assert "AI_TW_PAT" in text
    # Adopter guidance present (a comment explaining the secret).
    assert "beadloom-gate" in text


def test_template_gitlab_documents_pat_variable_for_adopters() -> None:
    """The vendored GitLab template tells adopters to create the access-token
    CI/CD variable for auto-pipeline-trigger on the agent's commit."""
    text = GL_TEMPLATE.read_text(encoding="utf-8")
    assert "AI_TW_PAT" in text

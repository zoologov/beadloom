# beadloom:feature=onboarding
"""BDL-049 BEAD-02: CI configs fire on PR (not push:main), use merge-base
``--since``, carry the loop-guard, and publish via ``--target pr-branch``.

These are static, network-free checks over the four artifacts the feature
touches: the live GitHub workflow + GitLab pipeline, and the two vendored
templates scaffolded into adopter repos. Each must (a) parse as YAML and
(b) encode the trunk-based / merge_request_event trigger model so a scaffolded
repo gets the same trunk-based behaviour as Beadloom itself.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

GH_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ai-techwriter.yml"
GL_PIPELINE = REPO_ROOT / ".gitlab-ci.yml"
TEMPLATES = REPO_ROOT / "src" / "beadloom" / "onboarding" / "templates" / "ai_techwriter"
GH_TEMPLATE = TEMPLATES / "github-workflow.yml"
GL_TEMPLATE = TEMPLATES / "gitlab-ci-job.yml"

GITHUB_FILES = (GH_WORKFLOW, GH_TEMPLATE)
GITLAB_FILES = (GL_PIPELINE, GL_TEMPLATE)
ALL_FILES = GITHUB_FILES + GITLAB_FILES


@pytest.mark.parametrize("path", ALL_FILES, ids=lambda p: p.name)
def test_ci_config_is_valid_yaml(path: Path) -> None:
    """Every CI artifact parses (no tabs / indentation breakage)."""
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)


@pytest.mark.parametrize("path", GITHUB_FILES, ids=lambda p: p.name)
def test_github_triggers_on_pull_request_not_push_main(path: Path) -> None:
    """on: pull_request -> main/master; push:main removed; dispatch kept."""
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    # YAML 1.1 parses the bare key ``on`` as boolean True.
    on = doc.get("on", doc.get(True))
    assert "pull_request" in on
    pr = on["pull_request"]
    assert set(pr["types"]) >= {"opened", "synchronize", "reopened"}
    assert pr["branches"] == ["main", "master"]
    assert "workflow_dispatch" in on
    assert "push" not in on


@pytest.mark.parametrize("path", GITHUB_FILES, ids=lambda p: p.name)
def test_github_has_cancel_in_progress_concurrency(path: Path) -> None:
    """G8: cancel-in-progress, keyed per PR."""
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    concurrency = doc["concurrency"]
    assert concurrency["cancel-in-progress"] is True
    assert "pull_request.number" in concurrency["group"]


@pytest.mark.parametrize("path", GITHUB_FILES, ids=lambda p: p.name)
def test_github_uses_merge_base_since_and_pr_branch_target(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert "git merge-base" in text
    assert "--target pr-branch" in text
    # Fallback to the base SHA when merge-base cannot resolve.
    assert "pull_request.base.sha" in text
    # PR URL wired so the publisher can comment / record it.
    assert "PR_URL:" in text
    assert "pull_request.html_url" in text


@pytest.mark.parametrize("path", GITHUB_FILES, ids=lambda p: p.name)
def test_github_checks_out_pr_head_branch(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert "pull_request.head.ref" in text
    assert "fetch-depth: 0" in text


@pytest.mark.parametrize("path", GITLAB_FILES, ids=lambda p: p.name)
def test_gitlab_triggers_on_merge_request_event(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert '$CI_PIPELINE_SOURCE == "merge_request_event"' in text
    # The old push-to-main gate is gone for the ai-techwriter job.
    assert '$CI_COMMIT_BRANCH == "main"' not in text


@pytest.mark.parametrize("path", GITLAB_FILES, ids=lambda p: p.name)
def test_gitlab_uses_merge_base_since_and_pr_branch_target(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert "git merge-base" in text
    assert "CI_MERGE_REQUEST_TARGET_BRANCH_NAME" in text
    assert "--platform gitlab --target pr-branch" in text
    # Env the BEAD-01 publisher reads to resolve + comment on the MR.
    assert "CI_MERGE_REQUEST_IID" in text
    assert "CI_MERGE_REQUEST_PROJECT_URL" in text


@pytest.mark.parametrize("path", ALL_FILES, ids=lambda p: p.name)
def test_loop_guard_present(path: Path) -> None:
    """Belt-and-suspenders loop-guard: author + [skip ai-techwriter] subject."""
    text = path.read_text(encoding="utf-8")
    assert "beadloom-ai-techwriter" in text
    assert "skip ai-techwriter" in text
    assert "git log -1" in text


def _inline_shell_blocks(doc: object) -> list[str]:
    """Collect every inline shell snippet from a parsed CI doc (run:/script:)."""
    blocks: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "run" and isinstance(value, str):
                    blocks.append(value)
                elif key == "script" and isinstance(value, list):
                    blocks.append("\n".join(str(s) for s in value))
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(doc)
    return blocks


@pytest.mark.parametrize("path", ALL_FILES, ids=lambda p: p.name)
def test_inline_shell_parses_with_bash_n(path: Path) -> None:
    """Every inline run:/script: block is syntactically valid bash."""
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    blocks = _inline_shell_blocks(doc)
    assert blocks, f"no inline shell found in {path.name}"
    for block in blocks:
        result = subprocess.run(
            ["bash", "-n"],  # noqa: S607 - bash resolved on PATH in CI/dev
            input=block,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, f"{path.name}:\n{block}\n{result.stderr}"


def test_live_and_template_github_share_trigger_model() -> None:
    """The vendored GitHub template mirrors the live workflow's trigger model."""
    live = yaml.safe_load(GH_WORKFLOW.read_text(encoding="utf-8"))
    tmpl = yaml.safe_load(GH_TEMPLATE.read_text(encoding="utf-8"))
    live_on = live.get("on", live.get(True))
    tmpl_on = tmpl.get("on", tmpl.get(True))
    assert "pull_request" in live_on and "pull_request" in tmpl_on
    assert "push" not in live_on and "push" not in tmpl_on


# --------------------------------------------------------------------------- #
# BDL-049 hardening: AI_TW_SKIP gating + structural loop-guard guarantees
# --------------------------------------------------------------------------- #


def _gh_steps(path: Path) -> list[dict[str, object]]:
    """The ordered step list of the single ai-techwriter job in a GH workflow."""
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    jobs = doc["jobs"]
    job = jobs["ai-techwriter"]
    steps = job["steps"]
    assert isinstance(steps, list)
    return [s for s in steps if isinstance(s, dict)]


@pytest.mark.parametrize("path", GITHUB_FILES, ids=lambda p: p.name)
def test_github_loop_guard_sets_skip_flag_before_work(path: Path) -> None:
    """The loop-guard runs as an EARLY step and sets AI_TW_SKIP in the env file.

    It must come before the install/harness steps so it can short-circuit the
    agent's own ``synchronize`` re-trigger.
    """
    steps = _gh_steps(path)
    guard_idx = next(
        i
        for i, s in enumerate(steps)
        if isinstance(s.get("run"), str) and "AI_TW_SKIP=1" in s["run"]
    )
    # The guard reads the head commit author + subject (belt-and-suspenders).
    guard = steps[guard_idx]["run"]
    assert isinstance(guard, str)
    assert "git log -1" in guard
    assert "beadloom-ai-techwriter" in guard
    assert "[skip ai-techwriter]" in guard
    assert "GITHUB_ENV" in guard
    # The harness step (the model + commit) comes AFTER the guard.
    harness_idx = next(
        i
        for i, s in enumerate(steps)
        if isinstance(s.get("run"), str) and "tools.ai_techwriter" in s["run"]
    )
    assert guard_idx < harness_idx


@pytest.mark.parametrize("path", GITHUB_FILES, ids=lambda p: p.name)
def test_github_every_post_guard_step_is_gated_on_skip(path: Path) -> None:
    """Every step that does work (after the guard) is gated by AI_TW_SKIP != '1'.

    Without the gate the agent's own refresh push would still install + run the
    model on the next ``synchronize`` (the loop). Each working step's ``if:``
    must reference the skip flag.
    """
    steps = _gh_steps(path)
    guard_idx = next(
        i
        for i, s in enumerate(steps)
        if isinstance(s.get("run"), str) and "AI_TW_SKIP=1" in s["run"]
    )
    post_guard = steps[guard_idx + 1 :]
    assert post_guard, "there must be work steps after the guard"
    for step in post_guard:
        cond = step.get("if")
        assert isinstance(cond, str), f"missing if-gate on step {step.get('name')}"
        assert "AI_TW_SKIP" in cond, f"step {step.get('name')} not gated on AI_TW_SKIP"


@pytest.mark.parametrize("path", GITHUB_FILES, ids=lambda p: p.name)
def test_github_pr_path_and_dispatch_path_are_mutually_exclusive(path: Path) -> None:
    """The pr-branch harness step is PR-only; the branch-pr step is dispatch-only.

    So a single trigger never runs both publish targets.
    """
    steps = _gh_steps(path)
    pr_step = next(
        s
        for s in steps
        if isinstance(s.get("run"), str) and "--target pr-branch" in s["run"]
    )
    dispatch_step = next(
        s
        for s in steps
        if isinstance(s.get("run"), str) and "--target branch-pr" in s["run"]
    )
    assert "pull_request" in str(pr_step.get("if"))
    assert "workflow_dispatch" in str(dispatch_step.get("if"))


@pytest.mark.parametrize("path", GITHUB_FILES, ids=lambda p: p.name)
def test_github_dispatch_path_keeps_branch_pr_target(path: Path) -> None:
    """workflow_dispatch (no PR context) keeps the original branch-PR publish."""
    text = path.read_text(encoding="utf-8")
    assert "--target branch-pr" in text


def test_live_and_template_gitlab_share_trigger_model() -> None:
    """The vendored GitLab template mirrors the live pipeline's MR trigger model."""
    for path in GITLAB_FILES:
        text = path.read_text(encoding="utf-8")
        assert '$CI_PIPELINE_SOURCE == "merge_request_event"' in text
        assert "--target pr-branch" in text


@pytest.mark.parametrize("path", GITHUB_FILES, ids=lambda p: p.name)
def test_github_grants_contents_and_pull_request_write(path: Path) -> None:
    """The pr-branch publisher needs contents:write (push) + pull-requests:write
    (comment) — both must be granted."""
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    perms = doc["permissions"]
    assert perms["contents"] == "write"
    assert perms["pull-requests"] == "write"


# --------------------------------------------------------------------------- #
# BDL-049 BEAD-09: GITHUB_TOKEN non-recursion fix — the agent's PR-path push
# must authenticate with a PAT (secrets.AI_TW_PAT) so it TRIGGERS beadloom-gate,
# with a fallback to the default token so PAT-less repos still work (variant-C).
# --------------------------------------------------------------------------- #

#: The fallback expression the checkout token + GH_TOKEN must use on the PR path.
PAT_FALLBACK_CHECKOUT = "secrets.AI_TW_PAT || github.token"
PAT_FALLBACK_GH_TOKEN = "secrets.AI_TW_PAT || secrets.GITHUB_TOKEN"  # noqa: S105 - GH expression, not a secret


@pytest.mark.parametrize("path", GITHUB_FILES, ids=lambda p: p.name)
def test_github_checkout_uses_pat_with_token_fallback(path: Path) -> None:
    """``actions/checkout`` persists the credential ``git push`` uses; it must be
    the PAT (so the agent's push triggers ``beadloom-gate``) with a fallback to
    the default token (variant-C: PAT-less repos still check out + work)."""
    steps = _gh_steps(path)
    checkout = next(
        s for s in steps if str(s.get("uses", "")).startswith("actions/checkout")
    )
    with_block = checkout.get("with")
    assert isinstance(with_block, dict), "checkout must declare a with: block"
    token = str(with_block.get("token", ""))
    assert PAT_FALLBACK_CHECKOUT in token, token


@pytest.mark.parametrize("path", GITHUB_FILES, ids=lambda p: p.name)
def test_github_pr_path_gh_token_uses_pat_with_token_fallback(path: Path) -> None:
    """The pr-branch harness step's ``GH_TOKEN`` must use the PAT (so ``gh`` push
    + ``gh pr comment`` authenticate as the PAT) with a fallback to GITHUB_TOKEN."""
    steps = _gh_steps(path)
    pr_step = next(
        s
        for s in steps
        if isinstance(s.get("run"), str) and "--target pr-branch" in s["run"]
    )
    env = pr_step.get("env")
    assert isinstance(env, dict)
    gh_token = str(env.get("GH_TOKEN", ""))
    assert PAT_FALLBACK_GH_TOKEN in gh_token, gh_token


@pytest.mark.parametrize("path", GITHUB_FILES, ids=lambda p: p.name)
def test_github_dispatch_path_does_not_use_pat(path: Path) -> None:
    """The workflow_dispatch (branch-pr) path has no PR to re-gate, so it stays
    on the default token — the PAT wiring is PR-path-only."""
    steps = _gh_steps(path)
    dispatch_step = next(
        s
        for s in steps
        if isinstance(s.get("run"), str) and "--target branch-pr" in s["run"]
    )
    env = dispatch_step.get("env")
    assert isinstance(env, dict)
    gh_token = str(env.get("GH_TOKEN", ""))
    assert "AI_TW_PAT" not in gh_token, gh_token
    assert "secrets.GITHUB_TOKEN" in gh_token


@pytest.mark.parametrize("path", GITLAB_FILES, ids=lambda p: p.name)
def test_gitlab_pr_path_uses_pat_with_job_token_fallback(path: Path) -> None:
    """GitLab mirror: CI_JOB_TOKEN pushes also do not trigger pipelines, so the
    MR pr-branch push/comment authenticates with an access-token CI/CD variable
    (AI_TW_PAT) with a fallback to CI_JOB_TOKEN / the default."""
    text = path.read_text(encoding="utf-8")
    assert "AI_TW_PAT" in text
    # The fallback to the job token keeps PAT-less projects working.
    assert "CI_JOB_TOKEN" in text


def test_live_github_pat_wiring_mirrored_in_template() -> None:
    """The vendored GitHub template mirrors the live PAT||token wiring so a
    scaffolded repo auto-gates the agent's commit the same way."""
    for path in GITHUB_FILES:
        text = path.read_text(encoding="utf-8")
        assert PAT_FALLBACK_CHECKOUT in text
        assert PAT_FALLBACK_GH_TOKEN in text


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
